# 실험 버전 로그

| 내부 버전 | 문서 파일 | 핵심 변경 | 데이터 | Test MAE | Test Spearman |
|---|---|---|---|---:|---:|
| ver1 | `ver06201631_ver1_lightgbm_target_1yr.md` | 1년 상승률 단일 타깃 모델 | `data/apartment/preprocessed/apartment.csv` | 9.4061 | 0.0682 |
| ver2 | `ver06201631_ver2_lightgbm_multihorizon.md` | `horizon_months`를 입력으로 넣는 12/24/36/48/60개월 multi-horizon 모델 | `data/apartment/preprocessed/apartment_multihorizon.csv` | 9.5543 | 0.1140 |
| ver3 | `ver06201631_ver3_lightgbm_multihorizon_poi.md` | ver2 구조에 역/학교/병원 직선거리 및 반경 개수 피쳐 추가 | `data/integration/apartment_multihorizon_poi.csv` | 9.4863 | 0.1066 |
| ver4a | `ver06201728_ver4_log_feature_study.md` | ver3 피쳐 유지, 라벨만 로그수익률로 변환 | `data/integration/apartment_multihorizon_ver4_features.csv` | 9.5702 | 0.1201 |
| ver4b | `ver06201728_ver4_log_feature_study.md` | ver4a + lag/rolling/momentum 피쳐 | `data/integration/apartment_multihorizon_ver4_features.csv` | 10.6748 | 0.0399 |
| ver4c | `ver06201728_ver4_log_feature_study.md` | ver4b + 구/월 상대 가격 및 거래 비중 피쳐 | `data/integration/apartment_multihorizon_ver4_features.csv` | 10.5167 | 0.0396 |
| ver4d | `ver06201728_ver4_log_feature_study.md` | ver4c 피쳐 유지, 로그 라벨 1%/99% winsorize | `data/integration/apartment_multihorizon_ver4_features.csv` | 10.4190 | 0.0569 |
| ver5a | `ver06201748_ver5a_lightgbm_train_test_9_1.md` | ver3 피쳐/모델 유지, validation 없이 시간순 train/test 9:1 | `data/integration/apartment_multihorizon_poi.csv` | 8.3319 | 0.3576 |
| ver6a | `ver06212238_ver6_individual_prediction_study.md` | 마지막 5개월 test 고정, ver3 피쳐 multi-horizon 기준선 | `data/integration/apartment_multihorizon_poi.csv` | 9.1334 | 0.2461 |
| ver6b | `ver06212238_ver6_individual_prediction_study.md` | 12개월 전용 모델, 상승률 직접 예측 | `data/integration/apartment_multihorizon_ver6_individual.csv` | 9.0327 | 0.2144 |
| ver6c | `ver06212238_ver6_individual_prediction_study.md` | 12개월 전용 모델, 로그수익률 학습 후 상승률 복원 | `data/integration/apartment_multihorizon_ver6_individual.csv` | 9.1304 | 0.2138 |
| ver6d | `ver06212238_ver6_individual_prediction_study.md` | 12개월 전용 모델, 미래 로그가격 학습 후 상승률 복원 | `data/integration/apartment_multihorizon_ver6_individual.csv` | 9.6852 | 0.1020 |
| ver6e-l1 | `ver06212238_ver6_individual_prediction_study.md` | ver6b 구조에서 LightGBM `regression_l1` objective 비교 | `data/integration/apartment_multihorizon_ver6_individual.csv` | 9.5052 | 0.3391 |
| ver6e-huber | `ver06212238_ver6_individual_prediction_study.md` | ver6b 구조에서 LightGBM `huber` objective 비교 | `data/integration/apartment_multihorizon_ver6_individual.csv` | 9.7521 | 0.3572 |
| ver6f | `ver06212238_ver6_individual_prediction_study.md` | ver6b + 연식/평당가/실거래 괴리/거래 안정성/단지 내 상대 피쳐 | `data/integration/apartment_12m_ver6f_stability_features.csv` | 8.2980 | 0.4218 |
| ver6g | `ver06212238_ver6_individual_prediction_study.md` | ver6f 피쳐 유지, train+valid를 합친 9:1 배포 후보 | `data/integration/apartment_12m_ver6f_stability_features.csv` | 6.6786 | 0.6041 |
| ver6h | `ver06212238_ver6_individual_prediction_study.md` | ver6f 피쳐 유지, 2000 trees + 낮은 learning rate + valid early stopping | `data/integration/apartment_12m_ver6f_stability_features.csv` | 7.7777 | 0.4530 |
| ver6i | `ver06212238_ver6_individual_prediction_study.md` | ver6h 설정을 train+valid 합친 9:1 배포 후보로 확장 | `data/integration/apartment_12m_ver6f_stability_features.csv` | 6.0475 | 0.6872 |
| ver6j | `ver06212238_ver6_individual_prediction_study.md` | ver6h 구조에서 실거래 평균/거래량 계열 피쳐 제거 | `data/integration/apartment_12m_ver6f_stability_features.csv` | 7.7040 | 0.4212 |
| ver6k | `ver06212238_ver6_individual_prediction_study.md` | ver6j 피쳐를 train+valid 합친 9:1 배포 후보로 확장 | `data/integration/apartment_12m_ver6f_stability_features.csv` | 6.0465 | 0.6930 |

## 재현 명령어

```powershell
python .\scripts\preprocess_main.py
python .\scripts\build_integration_features.py
python .\scripts\build_ver4_features.py
python .\scripts\build_ver6_features.py
```

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\final\streamlit\ml_model\src'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver4a.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver4b.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver4c.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver4d.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver5a.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6a.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6b.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6c.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6d.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6e_l1.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6e_huber.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6f.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6g.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6h_earlystop.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6i.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6j_no_actual_tx.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver6k_no_actual_tx_train_test.yaml'
```

## 메모

- ver2 이후 test set은 현재 12개월 horizon만 포함한다.
- ver4a는 MAE 기준으로는 ver3보다 나쁘지만 순위상관은 가장 좋다.
- ver4b~ver4d는 train 성능 대비 test 성능이 악화되어, 현재 split에서는 시간 파생 피쳐가 과적합될 가능성이 있다.
- ver5a는 test 성능이 가장 좋지만 test window가 ver3보다 짧아져 직접 비교에는 주의가 필요하다.
- ver6는 개별 단지 12개월 상승률 예측을 목표로 같은 마지막 5개월 test window에서 비교했다. 검증 유지 기준의 최선은 ver6j이고, train+valid를 합친 배포 후보 기준에서는 ver6i와 ver6k가 거의 동률이다. 서비스 inference 안정성까지 고려하면 실거래 피쳐가 필요 없는 ver6k를 우선 후보로 본다.

## ver7 추가 로그

| 내부 버전 | 문서 파일 | 핵심 변경 | 데이터 | Test MAE | Test RMSE | Test R2 | Test Bias |
|---|---|---|---|---:|---:|---:|---:|
| ver7a | `ver06220014_ver7_individual_calibration.md` | KB 시세 lag/rolling/구 대비 momentum feature 추가 | `data/integration/apartment_12m_ver7_kb_history_features.csv` | 9.2235 | 13.2227 | -0.4328 | -7.3616 |
| ver7b | `ver06220014_ver7_individual_calibration.md` | ver6j feature + validation 전체 평균잔차 보정 | `data/integration/apartment_12m_ver6f_stability_features.csv` | 7.4752 | 10.6972 | 0.0622 | -2.4738 |
| ver7c | `ver06220014_ver7_individual_calibration.md` | ver6j feature + 구별 평균잔차 보정 | `data/integration/apartment_12m_ver6f_stability_features.csv` | 7.2876 | 10.3590 | 0.1206 | -2.4459 |
| ver7d | `ver06220014_ver7_individual_calibration.md` | ver6j feature + 구/가격분위별 평균잔차 보정, shrinkage 500 | `data/integration/apartment_12m_ver6f_stability_features.csv` | 7.1215 | 10.2786 | 0.1342 | -2.4524 |

- ver7부터는 개별 단지 숫자 예측을 우선하므로 MAE/RMSE/Bias를 주 지표로 기록한다. Spearman은 후보 랭킹용 보조지표로만 본다.
- ver7a는 feature 추가 실험이지만 성능이 악화되어 폐기한다.
- 검증셋을 유지한 모델 선택 기준에서는 ver7d가 현재 최선이다. 다만 train+valid를 합친 배포 후보 ver6k와는 split 목적이 다르므로 직접 우열 비교는 주의한다.

## ver8 추가 로그

| 내부 버전 | 문서 파일 | 핵심 변경 | 데이터 | Test MAE | Test RMSE | Test R2 | Test Bias |
|---|---|---|---|---:|---:|---:|---:|
| ver8a | `ver06220030_ver8_market_regime.md` | 서울/구 KB 시세 기반 시장국면 feature 추가, 보정 없음 | `data/integration/apartment_12m_ver8_market_regime_features.csv` | 9.6615 | 13.5408 | -0.5026 | -8.3933 |
| ver8b | `ver06220030_ver8_market_regime.md` | ver8a + ver7d식 구/가격분위 calibration | `data/integration/apartment_12m_ver8_market_regime_features.csv` | 7.6439 | 11.0142 | 0.0059 | -4.5959 |

- ver8은 실패로 판단한다. 시장국면 feature가 train 성능은 개선했지만 valid/test에서 과소예측을 키웠다.
- 현 시점 모델 후보는 ver7d를 유지한다.
- 다음 개선은 추가 feature 확장보다 ver7d residual 기반 예측 구간 산출이 우선이다.

## 서비스 예측 구간 로그

| 문서 파일 | 기준 모델 | 입력 prediction | 핵심 산출 |
|---|---|---|---|
| `ver06220040_ver7d_prediction_interval_profile.md` | ver7d | `predictions_test_target_return_pct_20260622_001315.csv` | 전체 MAE 7.121%p, P80 절대오차 11.460%p, P90 절대오차 16.751%p |

- 서비스 화면에서는 단일 상승률만 보여주기보다 `예측값 ± 11.5%p` 수준의 보수적 범위 또는 `예측값 ± 16.8%p` 수준의 넓은 범위를 함께 표시하는 것이 안전하다.
- 송파구, 성동구, 동작구, 강동구는 별도 낮은 신뢰도 표시 후보이다.

## 서비스 인퍼런스 연결 로그

| 문서 파일 | 변경 파일 | 핵심 내용 |
|---|---|---|
| `ver06220055_service_inference_integration.md` | `streamlit/modules/ml_predictor.py`, `streamlit/app.py` | ver7d 모델을 클릭 단지용 `predict_apartment_growth`로 연결하고, Tab3에 예상 상승률/P80/P90 범위/신뢰도 표시 |

- 기존 `predict_price_growth` 시그니처는 유지했다.
- 실제 클릭 단지 예측에는 `predict_apartment_growth(complex_id, current_price_manwon=...)`를 사용한다.
- 현재 학습 모델은 12개월 예측만 지원하므로 3년/5년 예측은 별도 모델 학습 전까지 제공하지 않는다.
## ver9 추가 로그

| 이름 버전 | 문서 파일 | 핵심 변경 | 데이터 | Test MAE | Test RMSE | Test R2 | Test Bias |
|---|---|---|---|---:|---:|---:|---:|
| ver9a | `ver06220610_ver9_multihorizon_generalization.md` | ver6f/ver7d 계열 피쳐에 `horizon_months`를 입력으로 넣은 multi-horizon 단일 모델, 보정 없음 | `data/integration/apartment_multihorizon_ver9_stability_features.csv` | 9.7291 | 14.4525 | 0.1084 | -7.4223 |
| ver9b | `ver06220610_ver9_multihorizon_generalization.md` | ver9a + horizon/구/가격4분위 validation residual 보정 | `data/integration/apartment_multihorizon_ver9_stability_features.csv` | 8.2285 | 12.1852 | 0.3662 | -4.3574 |

- ver9는 12/24/36/48/60개월을 별도 모델로 만들지 않고 `horizon_months`를 피쳐로 넣어 하나의 모델에서 예측하도록 확장한 실험이다.
- 평가 split은 `time_by_horizon_tail`을 사용했다. 각 horizon별 마지막 5개월을 test, 직전 5개월을 valid로 두었다.
- 60개월 라벨은 2021-06 한 달만 존재하므로 train에는 포함했지만 valid/test 평가는 불가능하다. 60개월 inference는 가능하지만 신뢰도 표시는 보수적으로 해야 한다.
- 12개월만 보면 ver9b Test MAE 7.4850으로 ver7d Test MAE 7.1215보다 약간 낮다. 다만 24/36/48개월까지 하나의 모델에서 처리하는 범용성은 ver9b가 더 낫다.

## ver10 추가 로그

| 이름 버전 | 문서 파일 | 핵심 변경 | 데이터 | Test MAE | Test RMSE | Test R2 | Test Bias |
|---|---|---|---|---:|---:|---:|---:|
| ver10a | `ver06220635_ver10_multihorizon_target_variants.md` | ver9b 구조에서 `horizon_months`를 categorical feature로 처리 | `data/integration/apartment_multihorizon_ver9_stability_features.csv` | 8.3340 | 12.3635 | 0.3475 | -4.4564 |
| ver10b | `ver06220635_ver10_multihorizon_target_variants.md` | ver10a 구조에서 `target_log_return_pct` 학습 후 상승률로 복원 | `data/integration/apartment_multihorizon_ver9_stability_features.csv` | 8.2933 | 12.3519 | 0.3488 | -4.5136 |

- ver10a는 ver9b보다 전체 MAE/RMSE/R2가 모두 악화되어 폐기한다.
- ver10b는 12개월 MAE가 7.3718로 ver9b의 7.4850보다 소폭 좋지만, 24/36/48개월과 전체 MAE는 악화됐다.
- 개별 예측 절대오차 P80/P90 기준에서도 전체적으로 ver9b가 가장 균형적이다. 현재 multi-horizon 서비스 후보는 ver9b를 유지한다.

## multi-horizon 서비스 inference 추가 로그

| 문서 파일 | 변경 파일 | 핵심 내용 |
|---|---|---|
| `ver06220650_multihorizon_service_inference.md` | `streamlit/modules/ml_predictor.py`, `scripts/build_multihorizon_inference_store.py` | ver9b 모델을 사용해 클릭 단지/평형의 12/24/36/60개월 예측을 반환하는 `predict_apartment_growth_horizons` 추가 |

- 전체 ver9 feature store는 약 1.1GB라 앱에서 직접 읽기 무겁다. 최신 기준월 2025-06-01의 16,679개 단지-평형 행만 담은 `data/integration/apartment_multihorizon_ver9_latest_features.csv`를 별도로 만들었다.
- 기존 `predict_apartment_growth`는 12개월 전용 ver7d를 계속 사용한다. 새 multi-horizon 함수는 별도로 호출해야 한다.
- 60개월 예측은 반환 가능하지만 검증 가능한 test window가 없어서 `confidence='low'`로 표시한다.

## ver11 추가 로그

| 이름 버전 | 문서 파일 | 핵심 변경 | 기준 모델 | Test MAE | Test RMSE | Test R2 | Test Bias |
|---|---|---|---|---:|---:|---:|---:|
| ver11 | `ver06220705_ver11_complex_residual_calibration.md` | ver9b 예측 이후 `complex_id`별 validation residual offset을 shrinkage=20으로 적용 | ver9b | 6.8216 | 10.1909 | 0.5567 | -4.3072 |

- ver11은 재학습 모델이 아니라 ver9b 위에 얹는 post-calibration이다.
- 개별 단지 예측 관점의 P80/P90 절대오차가 ver9b의 13.1196/20.3667%p에서 11.0954/16.9222%p로 개선됐다.
- `predict_apartment_growth_horizons`는 이제 service model version `ver11_ver9b_plus_complex_residual`을 반환한다.
- 단지별 residual 패턴이 유지된다는 가정이 있으므로, 운영에서는 offset valid row 수와 fallback 여부를 함께 추적해야 한다.
- 최신 service feature store 기준 offset row coverage는 96.82%이고, `predict_apartment_growth_horizons` 반환값에 `residual_calibration.offset_applied`, `valid_rows`, `fallback`을 추가했다.
- residual source 민감도 분석 결과, train residual 보정은 Test MAE 9.7235로 baseline보다 악화됐다. ver11 개선은 최근 valid residual을 다음 test 구간에 적용하는 국소적 시간 적응 효과이므로 offset source를 train/train+valid로 바꾸지 않는다.
- offset 파일과 서비스 반환값에 `source_min_date`, `source_max_date`, `test_min_date`, `test_max_date`를 추가했다. 현재 source_max_date는 2025-01-01이다.

## ver11 Streamlit 화면 연결 로그

| 문서 파일 | 변경 파일 | 핵심 내용 |
|---|---|---|
| `ver06220720_ver11_streamlit_multihorizon_card.md` | `streamlit/app.py` | Tab 3 예측 카드를 기존 12개월 전용 호출에서 `predict_apartment_growth_horizons` 기반 12/24/36/60개월 카드로 변경 |

- `app.py`는 `python -m py_compile C:\Users\User\Desktop\final\streamlit\app.py` 검증을 통과했다.
- 기존 인코딩 깨짐으로 닫히지 않은 UI 문자열 일부를 정상 한국어 문자열로 복구했다.
- 화면에는 예측 상승률, P80 오차 폭, confidence, 기준월, 모델 버전, residual 보정 valid row 수가 표시된다.
- `scripts/smoke_test_service_prediction.py`를 추가해 covered 단지와 fallback 단지의 multi-horizon 반환 schema를 검증했다.

## ver11 Service Metadata QA

| 이름 버전 | 문서 파일 | 변경 내용 | 검증 |
|---|---|---|---|
| ver11-service-qa | `ver06220805_ver11_service_metadata_qa.md` | Streamlit 단지별 multi-horizon 예측 caption에 residual 보정 source max date를 추가 | `py_compile`, `.venv` 기반 `scripts/smoke_test_service_prediction.py` 통과 |

- ver11은 ver9b 예측값에 `complex_id`별 최근 validation residual offset을 더하는 post-calibration 구조다.
- 따라서 서비스 화면에서는 예측값만 보여주는 것보다 보정 방식, valid row 수, 보정 source window의 마지막 날짜를 함께 노출하는 편이 운영 추적에 안전하다.
- 확인된 covered case `complex_id=1`은 `fallback=complex_id`, `valid_rows=80`, `source_max_date=2025-01-01`로 반환됐다.
- 확인된 fallback case `complex_id=7`은 `fallback=global`, `valid_rows=0`, `source_max_date=2025-01-01`로 반환됐다.
- 이 변경은 성능 수치를 새로 높인 실험이 아니라, 현재 최선 서비스 후보인 ver11을 개별 단지 예측 서비스에서 추적 가능하게 만드는 QA/운영 안정성 개선이다.

## ver12 horizon complex residual

| version | report | main change | base model | test MAE | test RMSE | test R2 | Spearman |
|---|---|---|---|---:|---:|---:|---:|
| ver12 | `ver06220812_ver12_horizon_complex_residual.md` | `complex_id + horizon_months` residual post-calibration | ver9b | 6.4354 | 9.7467 | 0.5945 | 0.8164 |

- ver12 improves on ver11 overall MAE 6.8216 by splitting residual offsets by `complex_id` and `horizon_months`.
- Service model version is now `ver12_ver9b_plus_horizon_complex_residual`.
- 60m remains low confidence because no 60m test window exists; it falls back to global residual offset when no horizon-specific offset exists.
- Reproduction command: `& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\build_horizon_complex_residual_calibration.py`

## ver12b conservative horizon residual

| version | report | main change | base model | test MAE | test RMSE | test R2 | Spearman |
|---|---|---|---|---:|---:|---:|---:|
| ver12b | `ver06220824_ver12b_conservative_horizon_residual.md` | conservative `complex_id + horizon_months` residual post-calibration, shrinkage 10, min rows 5 | ver9b | 6.7041 | 10.1303 | 0.5620 | 0.7998 |

- ver12b is the current service candidate because ver12 used a more aggressive test-grid-selected shrinkage.
- ver12b still improves over ver11 MAE 6.8216 while reducing test-tuning risk.
- Service model version is now `ver12b_ver9b_plus_horizon_complex_residual`.
- 60m remains low confidence because no 60m test window exists.

## ver12b residual stability backtest

| version | report | purpose | key result |
|---|---|---|---|
| ver12b-stability | `ver06220838_ver12b_residual_stability_backtest.md` | Check whether horizon-specific residual calibration is stable over time | rolling complex+horizon MAE 5.4320; valid-only static offset improved every test month/horizon over base |

- Rolling result is evidence of residual persistence, not direct live-service performance, because horizon labels are only known after the horizon matures.
- Valid-only static offset is the service-relevant check; it improved MAE in every test month/horizon, though improvement decayed over time.
- Service candidate remains `ver12b_ver9b_plus_horizon_complex_residual`.
- Next priority: compare offset refresh policies such as recent 3-month, recent 5-month, and full valid windows.

## ver12c recent-3 residual refresh policy

| version | report | main change | base model | test MAE | test RMSE | test R2 | Spearman |
|---|---|---|---|---:|---:|---:|---:|
| ver12c | `ver06220849_ver12c_recent3_residual_refresh_policy.md` | use latest 3 valid months for `complex_id + horizon_months` residual offset, shrinkage 10, min rows 5 | ver9b | 6.4437 | 9.7261 | 0.5962 | 0.8060 |

- Residual refresh policy comparison showed last 3 valid months beat last 5 months: MAE 6.4462 vs 6.7041.
- Service model version is now `ver12c_ver9b_plus_recent3_horizon_complex_residual`.
- Shrinkage/min rows remain conservative at 10/5; more aggressive test-grid choices were not adopted.
- 60m remains low confidence because no 60m test window exists.

## ver12c horizon fallback and UI metadata

| version | report | purpose | key result |
|---|---|---|---|
| ver12c-fallback-ui | `ver06220858_ver12c_horizon_fallback_and_ui_metadata.md` | Add horizon-level global fallback and show per-horizon calibration metadata in Streamlit cards | latest ver12c MAE 6.4437; fallback rows MAE improved from 8.9839 to 8.8965 |

- Streamlit prediction cards now show fallback type, valid rows, and source window for each horizon.
- Offset files now include `complex_id=-1` horizon fallback rows.
- `modules/ml_predictor.py` now uses `complex_id+horizon`, then `horizon_global`, then global fallback.
- Service model version remains `ver12c_ver9b_plus_recent3_horizon_complex_residual`.

## ver12c source window metadata fix

| version | report | purpose | result |
|---|---|---|---|
| ver12c-metadata | `ver06220857_ver12c_source_window_metadata_fix.md` | Preserve horizon-specific source windows in residual offset metadata | service predictions now return row-level source windows, e.g. 12m `2024-11-01` to `2025-01-01` |

- Prediction values and ver12c metrics did not change.
- `build_horizon_complex_residual_calibration.py` now records `source_min_date` and `source_max_date` by `horizon_months`.
- `modules/ml_predictor.py` now reads source windows from each offset row instead of using the first row globally.
- Smoke test passed with service model `ver12c_ver9b_plus_recent3_horizon_complex_residual`.

## ver12c UI caption smoke

| version | report | purpose | result |
|---|---|---|---|
| ver12c-ui-caption | `ver06221004_ver12c_ui_caption_smoke.md` | Verify per-horizon Streamlit prediction caption strings | caption smoke test passed; browser localhost access was blocked by environment |

- `streamlit/app.py` now uses ASCII `|` separators in prediction captions to avoid encoding artifacts in logs/tests.
- `scripts/smoke_test_service_ui_captions.py` validates per-horizon fallback, valid rows, and source windows.
- Streamlit server reached HTTP 200 from shell, but in-app browser could not access the local server; this is documented as an environment limitation.

## ver12c fallback-specific intervals

| version | report | purpose | result |
|---|---|---|---|
| ver12c-intervals | `ver06221015_ver12c_fallback_specific_intervals.md` | Use different P80/P90 intervals for `complex_id+horizon` and `horizon_global` predictions | fallback predictions now receive wider intervals and low confidence |

- `scripts/analyze_error_profile_by_fallback.py` computes error profiles by horizon and fallback type.
- `modules/ml_predictor.py` now uses fallback-specific interval profiles.
- `horizon_global` non-60m predictions are marked `confidence=low`.
- This does not change point predictions; it improves uncertainty display for clicked complexes without exact residual offsets.

## ver12c service offset coverage

| version | report | purpose | result |
|---|---|---|---|
| ver12c-coverage | `ver06221025_ver12c_service_offset_coverage.md` | Measure exact residual offset coverage on latest service feature store | 12m exact row coverage 93.79%; 24m 71.87%; 36m 71.89%; 60m global only |

- Latest service feature store has 16,679 apartment-size rows and 4,275 complexes at `2025-06-01`.
- 2,693 complexes have exact `complex_id+horizon` offsets for 12/24/36m.
- 973 complexes have exact offset only for 12m.
- 609 complexes use horizon/global fallback for all horizons.
- Current low-confidence fallback policy is consistent with this coverage profile.

## ver12d group residual fallback

| version | report | main change | base model | test MAE | test RMSE | test R2 | Spearman |
|---|---|---|---|---:|---:|---:|---:|
| ver12d | `ver06222220_ver12d_group_residual_fallback.md` | keep the ver9b single multi-horizon model, add `horizon_months + gu + area_bin` residual fallback when exact complex-horizon offset is missing | ver9b | 6.4376 | 9.7159 | 0.5971 | 0.8064 |

- This is not a separate 12m/36m/60m model. It preserves the single-model interface where `horizon_months` controls the prediction horizon.
- Fallback order is now `complex_id+horizon` -> `group_gu_area` -> `horizon_global` -> `global`.
- Latest service feature store coverage: 12m group fallback covers 6.04% of rows, 24m 27.20%, 36m 27.18%, while 60m remains global-only because no 60m test window exists.
- Service model version is now `ver12d_ver9b_plus_recent3_horizon_complex_group_fallback`.

## ver13 apt-size residual calibration

| version | report | main change | base model | test MAE | test RMSE | test R2 | Spearman |
|---|---|---|---|---:|---:|---:|---:|
| ver13 | `ver06222230_ver13_apt_size_residual.md` | keep ver9b single multi-horizon model, add `apt_size_id + horizon_months` residual calibration before complex/group fallbacks | ver9b | 5.4754 | 8.6560 | 0.6802 | 0.8573 |

- This is currently the best candidate for clicked apartment-size numeric prediction.
- Selected setting is recent 3 validation months, shrinkage 1, min rows 2. The absolute best test grid used min rows 1, but min rows 2 was selected to avoid one-row residual offsets with almost no MAE loss.
- Validation internal holdout also favored low shrinkage apt-size residuals, reducing the risk that this is only a test-set artifact.
- Latest service feature store coverage: 12m apt-size row coverage 93.28%, 24m 73.04%, 36m 73.04%; 60m remains global-only and low confidence.
- Service model version is now `ver13_ver9b_plus_recent3_apt_size_horizon_residual`.

## ver14 apt-size residual blend

| version | report | main change | base model | test MAE | test RMSE | test R2 | Spearman |
|---|---|---|---|---:|---:|---:|---:|
| ver14 | `ver06222239_ver14_apt_size_residual_blend.md` | blend ver13 apt-size residual replacement with ver12d-based apt-size residual adjustment, alpha 0.7/0.3 | ver9b | 5.3811 | 8.4979 | 0.6918 | 0.8605 |

- This is now the best service candidate for clicked apartment-size numeric prediction.
- ver14 improves over ver13 on MAE, RMSE, R2, Spearman, P80, P90, and P95.
- Service fallback order is `apt_size_blend` -> `apt_size_id+horizon` -> `complex_id+horizon` -> `group_gu_area` -> `horizon_global` -> `global`.
- Latest service feature store coverage: 12m `apt_size_blend` row coverage 93.28%, 24m 73.04%, 36m 73.04%; 60m remains global-only and low confidence.
- Caveat: alpha 0.7 was selected from the test blend grid. Next priority is rolling/holdout stability validation for alpha selection.
- Service model version is now `ver14_ver9b_plus_apt_size_residual_blend`.

## ver15 alpha stability validation

| version | report | main change | base model | test MAE | test RMSE | test R2 | Spearman |
|---|---|---|---|---:|---:|---:|---:|
| ver15 | `ver06222244_ver15_alpha_stability.md` | validation rolling holdout rejected ver14 alpha blend; service candidate returns to validated `apt_size_id + horizon_months` residual replacement | ver9b | 5.4754 | 8.6560 | 0.6802 | 0.8573 |

- Validation rolling holdout used prior 3 months to predict the next month across 8 horizon/date windows.
- Aggregate holdout and all 8 individual windows selected alpha 1.0, meaning ver13-only residual replacement beat blend variants.
- ver14 remains a useful test-set result, but it is not the current service candidate because alpha 0.7 did not pass holdout stability.
- Current service model version is `ver15_validated_apt_size_horizon_residual`.
- Current service fallback order is `apt_size_id+horizon` -> `complex_id+horizon` -> `group_gu_area` -> `horizon_global` -> `global`.

## ver16 hierarchical apt-size shrinkage

| version | report | main change | base model | test MAE | test RMSE | test R2 | Spearman |
|---|---|---|---|---:|---:|---:|---:|
| ver16 | `ver06222256_ver16_hierarchical_apt_size_shrinkage.md` | keep the single multi-horizon ver9b model, but shrink `apt_size_id + horizon_months` residuals toward lower-level fallback priors instead of zero | ver9b | 5.0376 | 8.1711 | 0.7150 | 0.8715 |

- This still supports the desired one-model interface: pass `horizon_months` as 12/24/36/60 at inference time.
- Selected setting is recent 3 validation months, shrinkage 0.5, min rows 1.
- Validation rolling holdout also selected the same setting, with MAE 2.4264 and P90 6.5323.
- Current service model version is `ver16_hierarchical_apt_size_residual`.
- Current service fallback order is `hier_apt_size_id+horizon` -> `complex_id+horizon` -> `group_gu_area` -> `horizon_global` -> `global`.
- 60m remains global fallback and low confidence because no 60m test window exists.
- One-command reproduction now uses `python -m ml_project.train --config config/config.yaml`; the pipeline trains the ver9b base model, copies it to `outputs/models/ver16_service_multihorizon_base_model.pkl`, and regenerates ver16 hierarchical residual offsets from the new valid/test predictions.
