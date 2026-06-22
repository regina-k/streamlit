# 모델 실험 버전별 성능 요약

이 문서는 제출용 최종 정리본이다. 목적은 사용자가 클릭한 아파트 단지/평형에 대해 12/24/36/60개월 예상 상승률을 안정적으로 제공하는 모델을 선정하고, 버전별 개선 과정을 한눈에 확인하는 것이다.

## 최종 결론

현재 최종 후보는 `ver16_hierarchical_apt_size_residual`이다.

- 기본 모델: 단일 multi-horizon LightGBM
- 입력 horizon: `horizon_months`에 12, 24, 36, 60을 입력
- 서비스 함수: `predict_apartment_growth_horizons`
- 서비스 모델 경로: `streamlit/ml_model/outputs/models/ver16_service_multihorizon_base_model.pkl`
- residual offset 경로: `streamlit/ml_model/outputs/calibration/ver16_hierarchical_apt_size_offsets.csv`
- 재현 명령어: `python -m ml_project.train --config config/config.yaml`

ver16은 12/24/36/60개월별 모델을 따로 두지 않고, 하나의 모델에 horizon 값을 넣어 예측하는 구조를 유지한다. 그 위에 단지-평형-horizon 단위 residual 보정을 적용한다.

## 핵심 성능 추이

아래 표는 서비스 후보로 의미가 큰 milestone만 모은 것이다. MAE는 상승률 percentage point 기준이며, 낮을수록 좋다.

| 순서 | 버전 | 역할 | Test MAE | Test RMSE | Test R2 | Spearman | 채택 여부 |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | ver1 | 구 단위 1년 상승률 baseline | 9.4061 |  |  | 0.0682 | 폐기 |
| 2 | ver3 | multi-horizon + POI feature 초기형 | 9.4863 |  |  | 0.1066 | 폐기 |
| 3 | ver7d | 12개월 전용 개별 단지 후보 | 7.1215 | 10.2786 | 0.1342 |  | 참고 |
| 4 | ver9b | 단일 multi-horizon LightGBM 기준 모델 | 8.2285 | 12.1852 | 0.3662 |  | base 채택 |
| 5 | ver11 | complex residual post-calibration | 6.8216 | 10.1909 | 0.5567 |  | 개선 |
| 6 | ver12d | complex/group/horizon fallback 보정 | 6.4376 | 9.7159 | 0.5971 | 0.8064 | 개선 |
| 7 | ver13 | apt_size_id + horizon residual 보정 | 5.4754 | 8.6560 | 0.6802 | 0.8573 | 개선 |
| 8 | ver14 | ver13 + adjustment blend | 5.3811 | 8.4979 | 0.6918 | 0.8605 | test상 개선, holdout 미통과 |
| 9 | ver15 | ver14 blend 안정성 검증 후 ver13 방식 복귀 | 5.4754 | 8.6560 | 0.6802 | 0.8573 | 안정 후보 |
| 10 | ver16 | hierarchical apt-size residual shrinkage | 5.0376 | 8.1711 | 0.7150 | 0.8715 | 최종 후보 |

ver14는 test MAE만 보면 ver15보다 낮지만, alpha 선택이 test grid에 의존했고 validation rolling holdout에서 안정성이 확인되지 않아 서비스 후보에서 제외했다. ver16은 test와 validation holdout 양쪽에서 개선되었기 때문에 최종 후보로 선택했다.

## 채택 경로 기준 개선 폭

탐색 중 실패한 실험을 제외하고, 실제 서비스 후보로 이어진 채택 경로만 보면 MAE는 `8.2285`에서 `5.0376`으로 감소했다. 이는 약 `38.8%` 개선이다.

| 순서 | 채택 버전 | Test MAE | 직전 채택 버전 대비 개선 | ver9b 대비 누적 개선 |
|---:|---|---:|---:|---:|
| 1 | ver9b | 8.2285 |  | 0.0% |
| 2 | ver11 | 6.8216 | 17.1% | 17.1% |
| 3 | ver12d | 6.4376 | 5.6% | 21.8% |
| 4 | ver13 | 5.4754 | 14.9% | 33.5% |
| 5 | ver16 | 5.0376 | 8.0% | 38.8% |

## 그래프용 데이터

나중에 그래프를 그릴 때 아래 CSV 블록을 그대로 사용할 수 있다.

```csv
version_order,version,stage,test_mae,test_rmse,test_r2,spearman,is_service_candidate,is_adopted
1,ver1,gu_level_baseline,9.4061,,,0.0682,false,false
2,ver3,multihorizon_poi_initial,9.4863,,,0.1066,false,false
3,ver7d,individual_12m_candidate,7.1215,10.2786,0.1342,,false,false
4,ver9b,single_multihorizon_base,8.2285,12.1852,0.3662,,true,true
5,ver11,complex_residual,6.8216,10.1909,0.5567,,true,true
6,ver12d,complex_group_horizon_fallback,6.4376,9.7159,0.5971,0.8064,true,true
7,ver13,apt_size_horizon_residual,5.4754,8.6560,0.6802,0.8573,true,true
8,ver14,apt_size_residual_blend,5.3811,8.4979,0.6918,0.8605,true,false
9,ver15,validated_apt_size_residual,5.4754,8.6560,0.6802,0.8573,true,true
10,ver16,hierarchical_apt_size_shrinkage,5.0376,8.1711,0.7150,0.8715,true,true
```

채택 경로만 그릴 때는 아래 데이터를 사용한다.

```csv
adopted_order,version,test_mae,cumulative_improvement_pct
1,ver9b,8.2285,0.0
2,ver11,6.8216,17.1
3,ver12d,6.4376,21.8
4,ver13,5.4754,33.5
5,ver16,5.0376,38.8
```

## 전체 실험 해석

초기 ver1~ver5는 데이터 구조와 split 전략을 정리하는 단계였다. 이 구간에서는 구 단위 데이터, POI feature, 9:1 train/test split 등을 비교했다. 일부 수치는 좋아 보였지만 test window나 문제 정의가 달라 최종 서비스 후보로 직접 비교하기 어렵다.

ver6~ver8은 개별 단지 예측을 잘하기 위한 12개월 전용 후보군이었다. ver6k처럼 낮은 MAE를 보인 실험도 있었지만 train+valid 9:1 분포 후보이거나 12개월 전용 구조였기 때문에, 1년/3년/5년을 하나의 인터페이스에서 제공하려는 서비스 목적에는 맞지 않았다.

ver9부터는 최종 서비스 요구에 맞게 단일 multi-horizon 구조를 확정했다. 핵심은 모델을 12개월/36개월/60개월별로 분리하지 않고, `horizon_months`를 feature로 넣어 하나의 모델에서 horizon별 상승률을 예측하는 것이다.

ver11~ver16은 base 모델을 바꾸기보다 residual post-calibration을 고도화한 구간이다. 사용자가 클릭한 특정 단지/평형의 숫자 예측을 잘해야 하므로, 평균적인 ranking보다 개별 row의 오차를 줄이는 방향으로 실험했다.

## 최종 모델 구조

ver16은 두 단계로 구성된다.

1. Base model: ver9b single multi-horizon LightGBM
2. Post-calibration: hierarchical apt-size residual shrinkage

Base LightGBM의 주요 설정:

| 항목 | 값 |
|---|---|
| objective | regression |
| n_estimators | 1200 |
| learning_rate | 0.03 |
| num_leaves | 63 |
| subsample | 0.9 |
| colsample_bytree | 0.9 |
| min_child_samples | 80 |
| reg_lambda | 1.0 |
| split | horizon별 마지막 5개월 test, 직전 5개월 valid |
| calibration | horizon + gu + price quantile grouped residual |

사용 feature set:

| feature set | 의미 |
|---|---|
| horizon | 예측 기간. `horizon_months` |
| kb_market | KB 매매시세, 전세시세, 전세가율, 시세갭 |
| apartment_meta | 구, 좌표, 세대수, 준공월, 면적, 용적률, 건폐율 등 단지/평형 정보 |
| poi_accessibility | 역/학교/병원까지의 거리와 반경 내 개수 |
| individual_stability_without_actual_tx | 연식, 평당가, 단지 내 순위, 구 대비 프리미엄 등 서비스 시점에 안정적으로 계산 가능한 파생 feature |

실거래 평균/거래량 계열은 서비스 시점에 안정적으로 입력되기 어렵다고 판단하여 최종 후보에서는 제외했다.

## ver16 보정 방식

기존 ver13/ver15는 `apt_size_id + horizon_months` residual 평균을 0 방향으로 shrinkage했다. ver16은 더 안정적인 prior를 사용한다.

```text
residual_offset = prior_mean + weight * (raw_mean - prior_mean)
weight = valid_rows / (valid_rows + shrinkage)
```

여기서 `prior_mean`은 같은 단지-평형-horizon residual이 없을 때 사용하던 하위 fallback 보정값이다.

Fallback 순서:

```text
hier_apt_size_id+horizon
-> complex_id+horizon
-> group_gu_area
-> horizon_global
-> global
```

선택된 보정 설정:

| 항목 | 값 |
|---|---:|
| source_months | 3 |
| shrinkage | 0.5 |
| min_rows | 1 |

## ver16 상세 성능

| 지표 | 값 |
|---|---:|
| Test MAE | 5.0376 |
| Test RMSE | 8.1711 |
| Test R2 | 0.7150 |
| Test Spearman | 0.8715 |
| P80 absolute error | 8.6336 |
| P90 absolute error | 13.6911 |

Horizon별 test 성능:

| horizon | MAE | RMSE | P80 | P90 |
|---:|---:|---:|---:|---:|
| 12m | 4.8955 | 7.7892 | 8.2674 | 12.8447 |
| 24m | 4.9194 | 8.1016 | 8.5971 | 13.8572 |
| 36m | 6.0684 | 9.7123 | 10.4556 | 16.8060 |
| 48m | 4.3172 | 6.9706 | 7.5701 | 11.8045 |

Validation rolling holdout:

| source_months | shrinkage | min_rows | MAE | RMSE | R2 | Spearman | P90 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 0.5 | 1 | 2.4264 | 4.2110 | 0.9067 | 0.9546 | 6.5323 |

## 서비스 적용 상태

최신 service feature store 기준 coverage:

| horizon | 주요 fallback | row coverage | complex coverage |
|---:|---|---:|---:|
| 12m | hier_apt_size_id+horizon | 95.29% | 96.37% |
| 24m | hier_apt_size_id+horizon | 73.04% | 67.58% |
| 36m | hier_apt_size_id+horizon | 73.04% | 67.58% |
| 60m | global | 100.00% | 100.00% |

60개월은 예측값을 반환할 수 있지만, 아직 60개월 뒤 실현값이 충분히 없어 test 검증이 불가능하다. 따라서 서비스에서는 low confidence로 표시한다.

## 재현 명령어

아래 한 줄 pipeline으로 base 학습과 ver16 보정까지 재현된다.

```powershell
cd C:\Users\User\Desktop\final\streamlit\ml_model
$env:PYTHONPATH="src"
python -m ml_project.train --config config/config.yaml
```

이 명령은 다음 산출물을 생성한다.

```text
outputs/models/ver16_service_multihorizon_base_model.pkl
outputs/calibration/ver16_hierarchical_apt_size_offsets.csv
outputs/calibration/ver16_hierarchical_apt_size_shrinkage_grid.json
outputs/pipeline_ver16_hierarchical_apt_size_residual_<timestamp>.json
```

## 최종 판단

ver16은 현재까지의 실험 중 개별 단지/평형 상승률 예측 목적에 가장 적합하다. ver14의 test MAE가 일시적으로 더 낮았지만 holdout 안정성 검증을 통과하지 못했고, ver16은 test와 validation holdout 양쪽에서 개선을 보였다. 따라서 제출 및 서비스 연결 기준 최종 모델은 `ver16_hierarchical_apt_size_residual`로 정리한다.
