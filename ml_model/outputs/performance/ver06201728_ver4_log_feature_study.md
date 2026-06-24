# ver06201728_ver4_log_feature_study

## 1. 실험 개요

ver4는 라벨 변환과 고도화 피쳐 엔지니어링을 분리해서 검증한 실험이다. 모든 평가는 모델 예측값을 다시 `target_return_pct` 단위로 복원한 뒤 계산했다.

공통 데이터:

- `C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_ver4_features.csv`
- 행 수: 2,026,935
- 컬럼 수: 77
- 기존 ver3 피쳐 + 로그 라벨 + lag/rolling/momentum + 구/월 상대 피쳐

공통 split:

| Split | 행 수 | 포함 horizon |
|---|---:|---|
| Train | 1,665,765 | 12, 24, 36, 48, 60 |
| Valid | 217,414 | 12, 24 |
| Test | 143,756 | 12 |

## 2. Variant 정의

| Variant | Config | 변경 내용 | Feature 수 | Target |
|---|---|---|---:|---|
| ver4a | `config_ver4a.yaml` | ver3 피쳐 유지, 라벨만 로그수익률로 변경 | 44 | `target_log_return_pct` |
| ver4b | `config_ver4b.yaml` | ver4a + 가격/전세/거래량 lag 및 rolling 피쳐 | 61 | `target_log_return_pct` |
| ver4c | `config_ver4c.yaml` | ver4b + 구/월 상대 가격 및 거래 비중 피쳐 | 65 | `target_log_return_pct` |
| ver4d | `config_ver4d.yaml` | ver4c 피쳐 유지, 로그 라벨 1%/99% winsorize | 65 | `target_log_return_pct_winsor` |

라벨 변환:

```text
target_log_return_pct = log(future_sale_price_manwon / kb_sale_price_manwon) * 100
prediction_return_pct = (exp(prediction / 100) - 1) * 100
```

## 3. 전체 성능

| Variant | Train MAE | Valid MAE | Test MAE | Test RMSE | Test R2 | Test MAPE | Test Spearman |
|---|---:|---:|---:|---:|---:|---:|---:|
| ver3 기준 | 5.0728 | 7.4745 | 9.4863 | 13.5380 | -0.5218 | 139.5792 | 0.1066 |
| ver4a | 5.0333 | 7.6047 | 9.5702 | 13.6710 | -0.5519 | 128.8776 | 0.1201 |
| ver4b | 3.8418 | 7.7136 | 10.6748 | 14.9889 | -0.8655 | 154.1443 | 0.0399 |
| ver4c | 3.8363 | 7.7240 | 10.5167 | 14.7348 | -0.8028 | 174.7133 | 0.0396 |
| ver4d | 3.8922 | 7.7162 | 10.4190 | 14.6286 | -0.7769 | 167.0673 | 0.0569 |

## 4. 산출물

| Variant | Model | Metrics |
|---|---|---|
| ver4a | `outputs/models/apartment_return_lightgbm_ver4a_log_label_target_log_return_pct_20260620_172808.pkl` | `outputs/metrics_target_log_return_pct_20260620_172808.json` |
| ver4b | `outputs/models/apartment_return_lightgbm_ver4b_log_time_features_target_log_return_pct_20260620_173104.pkl` | `outputs/metrics_target_log_return_pct_20260620_173104.json` |
| ver4c | `outputs/models/apartment_return_lightgbm_ver4c_log_time_relative_target_log_return_pct_20260620_173411.pkl` | `outputs/metrics_target_log_return_pct_20260620_173411.json` |
| ver4d | `outputs/models/apartment_return_lightgbm_ver4d_winsor_log_time_relative_target_log_return_pct_winsor_20260620_173731.pkl` | `outputs/metrics_target_log_return_pct_winsor_20260620_173731.json` |

## 5. 해석

- 라벨만 로그수익률로 바꾼 ver4a는 MAE는 ver3보다 소폭 악화됐지만 Spearman은 가장 좋았다.
- time lag/rolling 피쳐를 넣은 ver4b는 train 성능이 크게 좋아졌지만 test 성능은 나빠졌다. 현재 시계열 split에서는 국면 과적합 신호가 강하다.
- 상대 피쳐를 추가한 ver4c는 ver4b보다 MAE가 약간 회복됐지만 충분하지 않다.
- winsorized 라벨 ver4d는 ver4c보다 소폭 낫지만 ver3/ver4a보다 좋지 않다.

## 6. 다음 방향

- 단순 lag/rolling 피쳐를 그대로 넣기보다, horizon별/시장국면별 검증 구조를 먼저 보강해야 한다.
- ver4a는 순위 예측 가능성이 좋아졌으므로 top-k 평균 실제 수익률 같은 랭킹 metric을 추가해 볼 가치가 있다.
- ver5 후보는 `ver3 피쳐 + log label + ranking metric` 또는 `horizon별 별도 모델`이다.
