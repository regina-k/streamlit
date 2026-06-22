# ver06201748_ver5a_lightgbm_train_test_9_1

## 1. 실험 개요

- 버전: ver5a
- 목적: ver3 피쳐와 LightGBM 파라미터를 유지하고, validation set 없이 시간순 train/test 9:1 분리만 적용했을 때 성능 변화를 확인한다.
- 입력 데이터: `C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_poi.csv`
- Config: `C:/Users/User/Desktop/final/streamlit/ml_model/config/config_ver5a.yaml`
- 모델 파일: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/models/apartment_return_lightgbm_ver5a_train_test_9_1_target_return_pct_20260620_174820.pkl`
- Metric 파일: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/metrics_target_return_pct_20260620_174820.json`
- 타깃: `target_return_pct`
- 모델: LightGBM Regressor

## 2. ver3 대비 변경점

| 항목 | ver3 | ver5a |
|---|---|---|
| 피쳐 | ver3 POI 포함 44개 | 동일 |
| 모델 파라미터 | LightGBM 300 trees | 동일 |
| split | train/valid/test 7:2:1 | train/test 9:1 |
| valid set | 있음 | 없음 |
| test 기간 | 2024-12 ~ 2025-06 추정 구간 | 2025-02 ~ 2025-06 |
| test horizon | 12개월 | 12개월 |

주의: ver5a는 train 데이터가 늘었지만 test 기간도 ver3보다 짧아졌다. 따라서 성능 개선을 모델 개선으로만 해석하면 안 된다.

## 3. 데이터 분리

| Split | 행 수 | 포함 horizon |
|---|---:|---|
| Train | 1,907,228 | 12, 24, 36, 48, 60 |
| Valid | 0 | 없음 |
| Test | 119,707 | 12 |

월 기준으로는 전체 49개월 중 앞 44개월을 train, 마지막 5개월을 test로 사용했다.

## 4. 사용 피쳐

ver3와 동일한 44개 feature를 사용했다.

- horizon: `horizon_months`
- 가격/거래: `kb_sale_price_manwon`, `kb_jeonse_price_manwon`, `kb_jeonse_ratio_pct`, `kb_price_gap_manwon`, `actual_sale_avg_manwon`, `actual_jeonse_avg_manwon`, `actual_jeonse_ratio_pct`, `actual_sale_count`, `actual_jeonse_count`, `actual_monthly_rent_count`
- 단지 메타: `gu`, `lat`, `lon`, `households_total`, `built_yyyymm`, `property_type`, 면적/세대/용적률/건폐율 컬럼
- 입지: 역/학교/병원 최근접 거리, 반경 내 개수, 병원 의사 수 합계

## 5. 성능

| Split | MAE | RMSE | R2 | MAPE | Spearman |
|---|---:|---:|---:|---:|---:|
| Train | 5.3853 | 7.6646 | 0.6237 | 115.4584 | 0.7383 |
| Test | 8.3319 | 12.0146 | -0.1829 | 126.4563 | 0.3576 |

## 6. ver3 대비

| 버전 | Split 구조 | Test rows | Test MAE | Test RMSE | Test R2 | Test Spearman |
|---|---|---:|---:|---:|---:|---:|
| ver3 | 7:2:1 | 143,756 | 9.4863 | 13.5380 | -0.5218 | 0.1066 |
| ver5a | 9:1 | 119,707 | 8.3319 | 12.0146 | -0.1829 | 0.3576 |

## 7. 해석

- validation 기간을 train에 포함하자 test MAE와 Spearman이 모두 크게 개선됐다.
- 다만 test 기간이 마지막 7개월 수준에서 마지막 5개월로 줄었으므로, 동일 test window 비교는 아니다.
- LightGBM 자체에는 validation set이 필수는 아니며, 현재 코드도 early stopping을 쓰지 않기 때문에 valid set은 학습에는 쓰이지 않았다.
- ver5a는 최종 모델 후보라기보다 “데이터를 더 많이 학습하면 최근 12개월 horizon 성능이 개선되는가”를 보는 진단 실험으로 해석하는 것이 안전하다.

## 8. 다음 제안

- 동일한 마지막 5개월 test window를 고정하고 ver3 방식의 train/valid/test와 ver5a를 다시 비교한다.
- early stopping을 도입할 계획이면 validation set을 다시 둬야 한다.
- 최종 제출용 성능은 test를 모델 선택에 반복 사용하지 않도록 별도 holdout 정책을 정해야 한다.
