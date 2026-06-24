# ver10 multi-horizon target variants

## 목적

ver9b는 하나의 모델에서 `horizon_months`를 입력받는 범용 구조를 만들었지만, 24/36개월 test bias가 여전히 컸다. ver10에서는 개별 단지 예측 오차를 줄이기 위해 다음 두 변형을 분리해 검증했다.

- ver10a: `horizon_months`를 연속 숫자가 아니라 categorical feature로 처리
- ver10b: ver10a 구조에서 target을 `target_log_return_pct`로 바꾸고, 예측 시 `target_return_pct`로 복원

## 공통 조건

- 데이터: `C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_ver9_stability_features.csv`
- split: `time_by_horizon_tail`
- train/valid/test: 1,041,652 / 262,890 / 265,404 rows
- test horizon: 12/24/36/48개월
- 60개월은 라벨 월이 2021-06 한 달뿐이라 train-only로 포함
- feature set: ver9b와 동일한 55개 피쳐
- calibration: `horizon_months + gu + kb_sale_price_manwon 4분위` validation residual 보정

## 성능 비교

| 버전 | 변경점 | Target | Test MAE | Test RMSE | Test R2 | Test Spearman | Test Bias |
|---|---|---|---:|---:|---:|---:|---:|
| ver9b | baseline 범용 모델 | `target_return_pct` | 8.2285 | 12.1852 | 0.3662 | 0.6695 | -4.3574 |
| ver10a | horizon categorical | `target_return_pct` | 8.3340 | 12.3635 | 0.3475 | 0.6616 | -4.4564 |
| ver10b | horizon categorical + log target | `target_log_return_pct` | 8.2933 | 12.3519 | 0.3488 | 0.6658 | -4.5136 |

## Horizon별 Test MAE

| 버전 | 12m | 24m | 36m | 48m |
|---|---:|---:|---:|---:|
| ver9b | 7.4850 | 9.0966 | 9.6844 | 6.9111 |
| ver10a | 7.5837 | 9.1223 | 9.9678 | 6.9277 |
| ver10b | 7.3718 | 9.2202 | 9.9586 | 6.9486 |

## 개별 예측 오차 분포

Test 절대오차 분위수다. 서비스에서 단지 하나를 클릭했을 때의 체감 리스크를 보기 위한 지표다.

| 버전 | P50 | P80 | P90 | P95 |
|---|---:|---:|---:|---:|
| ver9b | 5.0435 | 13.1196 | 20.3667 | 27.3161 |
| ver10a | 5.0777 | 13.3957 | 20.7078 | 27.7638 |
| ver10b | 4.9931 | 13.1676 | 20.6853 | 27.7931 |

Horizon별 P80 절대오차:

| 버전 | 12m | 24m | 36m | 48m |
|---|---:|---:|---:|---:|
| ver9b | 12.1115 | 14.7233 | 16.1445 | 10.9940 |
| ver10a | 12.3473 | 14.8608 | 16.7666 | 11.0705 |
| ver10b | 11.7649 | 14.9660 | 16.6816 | 11.0585 |

## 판단

ver10a는 ver9b보다 모든 주요 지표가 나빠졌다. `horizon_months`를 categorical로 두는 것만으로는 장기 horizon bias가 개선되지 않았다.

ver10b는 12개월 MAE와 P80 절대오차는 소폭 개선했다. 하지만 24/36/48개월 MAE, 전체 MAE, R2, P90/P95는 ver9b보다 나빠졌다. 따라서 현재 서비스 후보는 여전히 ver9b다.

실무적으로는 12개월 전용 최고 성능이 필요하면 ver7d 또는 ver10b 계열을 더 파고들 수 있고, 12/24/36/48/60개월을 한 모델에서 처리하는 범용 서비스가 목표라면 ver9b를 기준선으로 유지하는 것이 낫다.

## 산출물

- ver10a config: `C:/Users/User/Desktop/final/streamlit/ml_model/config/config_ver10a_multihorizon_categorical_horizon.yaml`
- ver10a model: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/models/apartment_return_lightgbm_ver10a_multihorizon_categorical_horizon_target_return_pct_20260622_062237.pkl`
- ver10a metrics: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/metrics_target_return_pct_20260622_062237.json`
- ver10b config: `C:/Users/User/Desktop/final/streamlit/ml_model/config/config_ver10b_multihorizon_log_target.yaml`
- ver10b model: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/models/apartment_return_lightgbm_ver10b_multihorizon_log_target_target_log_return_pct_20260622_062953.pkl`
- ver10b metrics: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/metrics_target_log_return_pct_20260622_062953.json`

