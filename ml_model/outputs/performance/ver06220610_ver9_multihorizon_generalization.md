# ver9 multi-horizon generalization

## 목적

ver6f/ver7d 계열의 단지별 안정성 피쳐를 유지하되, 12개월 전용 모델 대신 `horizon_months`를 입력 피쳐로 넣어 12/24/36/48/60개월 상승률을 하나의 모델에서 예측할 수 있는지 검증했다.

## 데이터

- 학습 데이터: `C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_ver9_stability_features.csv`
- 생성 스크립트: `C:/Users/User/Desktop/final/scripts/build_ver9_multihorizon_features.py`
- 원천 데이터: `C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_ver6_individual.csv`
- 행 수: 전체 2,026,935행, 단지-평형-월 유니크 패널 845,440행
- 라벨 수: 12m 845,412행, 24m 578,570행, 36m 387,338행, 48m 200,306행, 60m 15,309행

60개월 라벨은 현재 원천 기간상 2021-06 한 달만 존재한다. 따라서 모델 학습에는 포함했지만 valid/test 성능 평가는 12/24/36/48개월만 수행했다.

## 가공 방식

ver6f 안정성 피쳐를 multi-horizon 데이터에 확장했다. 단, 같은 `complex_id`, `area_serial_no`, `date`가 horizon별로 반복되므로 rolling/count/rank 피쳐를 horizon 행에서 직접 계산하지 않았다. 먼저 단지-평형-월 유니크 패널에서 피쳐를 계산한 뒤, `complex_id`, `area_serial_no`, `date` 기준으로 multi-horizon 행에 병합했다.

재현 명령어:

```powershell
python .\scripts\build_ver9_multihorizon_features.py
```

## Split

- strategy: `time_by_horizon_tail`
- 각 horizon별 마지막 5개월: test
- 그 직전 5개월: valid
- 나머지: train
- 60개월처럼 날짜 수가 부족한 horizon은 `short_horizon_train_only: true`로 train에만 포함
- 최종 행 수: train 1,041,652 / valid 262,890 / test 265,404

이 split은 일반 시간 split보다 multi-horizon 평가에 적합하다. 일반 시간 split은 test 구간이 사실상 12개월 horizon 위주로만 구성되는 문제가 있었다.

## Feature Set

총 55개 피쳐를 사용했다.

- `horizon_months`: 예측 horizon 개월 수
- KB 가격 피쳐: `kb_sale_price_manwon`, `kb_jeonse_price_manwon`, `kb_jeonse_ratio_pct`, `kb_price_gap_manwon`
- 단지/평형 메타: `gu`, 좌표, 세대수, 준공년월, 면적, 주택유형, 용적률, 건폐율 등
- POI 접근성: 지하철, 학교, 병원 거리 및 반경 내 개수/의사 수
- 안정성 피쳐: 건물 나이, 평당가, 단지 내 가격/면적 분위, 구 내 가격 프리미엄 등

실거래 평균가/거래건수 계열은 서비스 inference 시점의 안정성을 고려해 제외했다.

## Experiments

| 버전 | config | 보정 | Test MAE | Test RMSE | Test R2 | Test Spearman | Test Bias |
|---|---|---|---:|---:|---:|---:|---:|
| ver9a | `config_ver9a_multihorizon_stability.yaml` | 없음 | 9.7291 | 14.4525 | 0.1084 | 0.5681 | -7.4223 |
| ver9b | `config_ver9b_multihorizon_calibrated.yaml` | horizon + gu + 가격4분위 residual 보정 | 8.2285 | 12.1852 | 0.3662 | 0.6695 | -4.3574 |

## Horizon별 Test 성능

| 버전 | Horizon | Rows | MAE | RMSE | R2 | Spearman | Bias |
|---|---:|---:|---:|---:|---:|---:|---:|
| ver9a | 12 | 82,571 | 8.2486 | 12.2768 | -0.2092 | 0.2902 | -4.9677 |
| ver9a | 24 | 60,953 | 11.7907 | 16.9889 | -0.1368 | 0.5894 | -11.0649 |
| ver9a | 36 | 60,952 | 12.0259 | 17.5720 | 0.0214 | 0.6481 | -11.1557 |
| ver9a | 48 | 60,928 | 7.3754 | 10.3909 | 0.5815 | 0.7703 | -3.3700 |
| ver9b | 12 | 82,571 | 7.4850 | 10.9072 | 0.0456 | 0.4417 | -2.5459 |
| ver9b | 24 | 60,953 | 9.0966 | 13.3915 | 0.2936 | 0.6710 | -5.9284 |
| ver9b | 36 | 60,952 | 9.6844 | 14.5823 | 0.3261 | 0.7134 | -7.0504 |
| ver9b | 48 | 60,928 | 6.9111 | 9.6653 | 0.6379 | 0.8031 | -2.5465 |

## 판단

ver9b는 하나의 모델로 horizon을 입력받는 구조가 가능하다는 것을 보여준다. 특히 valid 성능은 안정적이고, test에서도 ver9a 대비 모든 horizon에서 개선됐다.

다만 단일 12개월 검증 기준의 기존 최선인 ver7d test MAE 7.1215보다는 12개월 MAE가 7.4850으로 약 0.36%p 낮다. 성능만 보면 ver7d가 아직 우위지만, 24/36/48개월까지 하나의 모델에서 처리하는 범용성을 고려하면 ver9b는 서비스 후보로 볼 수 있다.

60개월은 학습에 들어갔지만 검증 가능한 test window가 없다. 5년 예측값은 제공할 수 있어도 신뢰도 표시는 보수적으로 해야 한다.

## 산출물

- ver9a model: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/models/apartment_return_lightgbm_ver9a_multihorizon_stability_target_return_pct_20260622_055959.pkl`
- ver9a metrics: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/metrics_target_return_pct_20260622_055959.json`
- ver9b model: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/models/apartment_return_lightgbm_ver9b_multihorizon_calibrated_target_return_pct_20260622_060733.pkl`
- ver9b metrics: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/metrics_target_return_pct_20260622_060733.json`

