# ver06201631_ver3_lightgbm_multihorizon_poi

## 1. 실험 개요

- 버전: ver3
- 목적: ver2의 multi-horizon 구조를 유지하되, `additional` 위치 데이터를 결합한 입지 피쳐가 성능을 개선하는지 확인한다.
- 입력 데이터: `C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_poi.csv`
- 원천 데이터: `data/apartment/preprocessed/apartment_multihorizon.csv` + `data/additional/preprocessed/{school,station,hospital}.csv`
- 타깃: `target_return_pct`
- 사용 horizon: 12, 24, 36, 48, 60개월
- 모델: LightGBM Regressor
- Primary metric: MAE
- Config: `C:/Users/User/Desktop/final/streamlit/ml_model/config/config_ver3.yaml`
- 모델 파일: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/models/apartment_return_lightgbm_ver3_multihorizon_poi_target_return_pct_20260620_170507.pkl`
- Metric 파일: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/metrics_target_return_pct_20260620_170507.json`

## 2. ver3 변경점

- `data/integration` 폴더를 만들고 기존 multi-horizon 학습 데이터에 입지 피쳐를 병합했다.
- 입지 피쳐는 단지/면적 좌표 고유 조합 27,902개에 대해 계산한 뒤 전체 월별 행에 붙였다.
- `streamlit/ml_model/src/ml_project/preprocessing.py`가 기존 `feature_columns` 방식과 함께 `feature_sets`, `active_feature_sets`를 지원하도록 확장했다.
- ver3 config는 `horizon`, `price_market`, `apartment_meta`, `poi_accessibility` 피쳐 세트를 사용한다.

## 3. 데이터 규모

| 항목 | 값 |
|---|---:|
| 전체 행 수 | 2,026,935 |
| 전체 컬럼 수 | 54 |
| 고유 단지/면적 좌표 | 27,902 |
| 좌표 불일치 키 | 0 |
| 추가 입지 피쳐 수 | 18 |

## 4. 데이터 분리

시간 순서를 유지한 7:2:1 비율 분리이다.

| Split | 행 수 | 포함 horizon |
|---|---:|---|
| Train | 1,665,765 | 12, 24, 36, 48, 60 |
| Valid | 217,414 | 12, 24 |
| Test | 143,756 | 12 |

주의: 현재 기간 구조상 test set은 12개월 horizon만 평가된다. 36/48/60개월 horizon의 out-of-time 성능은 아직 검증되지 않았다.

## 5. 사용 컬럼

총 44개 feature를 사용했다.

| 컬럼 | 의미 | 처리 |
|---|---|---|
| `horizon_months` | 몇 개월 뒤 상승률을 예측할지 나타내는 예측 기간 | 숫자 |
| `kb_sale_price_manwon` | 현재 월 KB 매매시세, 만원 | 숫자 |
| `kb_jeonse_price_manwon` | 현재 월 KB 전세시세, 만원 | 숫자 |
| `kb_jeonse_ratio_pct` | KB 시세 기준 전세가율, % | 숫자 |
| `kb_price_gap_manwon` | KB 매매시세와 KB 전세시세의 차이, 만원 | 숫자 |
| `actual_sale_avg_manwon` | 현재 월 실거래 매매 평균가, 만원 | 숫자 |
| `actual_jeonse_avg_manwon` | 현재 월 실거래 전세 평균가, 만원 | 숫자 |
| `actual_jeonse_ratio_pct` | 실거래 평균 기준 전세가율, % | 숫자 |
| `actual_sale_count` | 현재 월 매매 실거래 건수 | 숫자 |
| `actual_jeonse_count` | 현재 월 전세 실거래 건수 | 숫자 |
| `actual_monthly_rent_count` | 현재 월 월세 실거래 건수 | 숫자 |
| `gu` | 서울 자치구명 | 범주형 |
| `lat` | 단지 위도 | 숫자 |
| `lon` | 단지 경도 | 숫자 |
| `households_total` | 단지 전체 세대수 | 숫자 |
| `built_yyyymm` | 준공년월 원천 값 | 숫자 |
| `property_type` | 원천 물건종류 코드 | 범주형 |
| `supply_area_pyeong` | 공급면적, 평 | 숫자 |
| `exclusive_area_pyeong` | 전용면적, 평 | 숫자 |
| `contract_area_pyeong` | 계약면적, 평 | 숫자 |
| `supply_area_m2` | 공급면적, 제곱미터 | 숫자 |
| `exclusive_area_m2` | 전용면적, 제곱미터 | 숫자 |
| `housing_type` | 주택형 원천 값 | 범주형 |
| `households_by_size` | 해당 면적/평형 세대수 | 숫자 |
| `floor_area_ratio` | 용적률 | 숫자 |
| `building_coverage_ratio` | 건폐율 | 숫자 |
| `nearest_station_m` | 가장 가까운 도시철도역까지 직선거리, 미터 | 숫자 |
| `station_count_500m` | 반경 500m 이내 도시철도역 수 | 숫자 |
| `station_count_1000m` | 반경 1000m 이내 도시철도역 수 | 숫자 |
| `nearest_school_m` | 가장 가까운 초중고 학교까지 직선거리, 미터 | 숫자 |
| `school_count_1000m` | 반경 1000m 이내 초중고 학교 수 | 숫자 |
| `nearest_elementary_school_m` | 가장 가까운 초등학교까지 직선거리, 미터 | 숫자 |
| `elementary_school_count_1000m` | 반경 1000m 이내 초등학교 수 | 숫자 |
| `nearest_middle_school_m` | 가장 가까운 중학교까지 직선거리, 미터 | 숫자 |
| `middle_school_count_1000m` | 반경 1000m 이내 중학교 수 | 숫자 |
| `nearest_high_school_m` | 가장 가까운 고등학교까지 직선거리, 미터 | 숫자 |
| `high_school_count_1000m` | 반경 1000m 이내 고등학교 수 | 숫자 |
| `nearest_hospital_m` | 가장 가까운 종합병원/상급종합병원까지 직선거리, 미터 | 숫자 |
| `hospital_count_3000m` | 반경 3000m 이내 종합병원/상급종합병원 수 | 숫자 |
| `hospital_count_5000m` | 반경 5000m 이내 종합병원/상급종합병원 수 | 숫자 |
| `hospital_doctor_sum_3000m` | 반경 3000m 이내 병원 의사 수 합계 | 숫자 |
| `hospital_doctor_sum_5000m` | 반경 5000m 이내 병원 의사 수 합계 | 숫자 |
| `nearest_tertiary_hospital_m` | 가장 가까운 상급종합병원까지 직선거리, 미터 | 숫자 |
| `tertiary_hospital_count_5000m` | 반경 5000m 이내 상급종합병원 수 | 숫자 |

## 6. 모델 설정

```yaml
model:
  type: lightgbm
  params:
    objective: regression
    n_estimators: 300
    learning_rate: 0.05
    num_leaves: 63
    subsample: 0.9
    colsample_bytree: 0.9
    min_child_samples: 50
    reg_alpha: 0.0
    reg_lambda: 1.0
    n_jobs: -1
```

## 7. 전체 Metric

| Split | MAE | RMSE | R2 | MAPE | Spearman |
|---|---:|---:|---:|---:|---:|
| Train | 5.0728 | 7.1873 | 0.6639 | 110.1779 | 0.7595 |
| Valid | 7.4745 | 11.4246 | 0.0532 | 124.2490 | 0.4796 |
| Test | 9.4863 | 13.5380 | -0.5218 | 139.5792 | 0.1066 |

## 8. Horizon별 Metric

### Train

| Horizon | Rows | MAE | RMSE | R2 | Spearman |
|---:|---:|---:|---:|---:|---:|
| 12 | 532,031 | 3.9960 | 5.5928 | 0.4144 | 0.5908 |
| 24 | 530,781 | 5.3854 | 7.6696 | 0.6071 | 0.7632 |
| 36 | 387,338 | 5.8562 | 8.2394 | 0.6894 | 0.8183 |
| 48 | 200,306 | 5.4453 | 7.2697 | 0.7822 | 0.8738 |
| 60 | 15,309 | 6.9628 | 9.2327 | 0.7399 | 0.8589 |

### Valid

| Horizon | Rows | MAE | RMSE | R2 | Spearman |
|---:|---:|---:|---:|---:|---:|
| 12 | 169,625 | 5.9983 | 9.1920 | -0.1022 | 0.4127 |
| 24 | 47,789 | 12.7140 | 17.1434 | -0.0573 | 0.6951 |

### Test

| Horizon | Rows | MAE | RMSE | R2 | Spearman |
|---:|---:|---:|---:|---:|---:|
| 12 | 143,756 | 9.4863 | 13.5380 | -0.5218 | 0.1066 |

## 9. ver2 대비 해석

| 버전 | Test MAE | Test RMSE | Test R2 | Test Spearman | 사용 피쳐 |
|---|---:|---:|---:|---:|---|
| ver2 | 9.5543 | 13.5895 | -0.5334 | 0.1140 | 가격/거래/단지 메타 |
| ver3 | 9.4863 | 13.5380 | -0.5218 | 0.1066 | ver2 + 역/학교/병원 입지 |

- MAE와 RMSE는 ver3가 아주 소폭 개선되었다.
- Spearman 순위상관은 ver2보다 약간 낮아졌다.
- 입지 피쳐가 큰 폭의 개선을 만들지는 못했지만, 가격 오차 기준으로는 방향이 나쁘지 않다.
- test가 12개월 horizon만 포함하기 때문에, 장기 horizon에서 입지 피쳐가 더 유효한지는 현재 split만으로 판단하기 어렵다.

## 10. 다음 실험 후보

- ver4에서는 시간 피쳐를 강화한다. 예: 직전 1/3/6/12개월 수익률, rolling mean, 거래량 변화율.
- 현재 test 구조의 한계를 줄이기 위해 horizon별 holdout 평가를 별도로 둔다.
- 입지 피쳐는 단순 직선거리이므로, 이후 도로망 거리/대중교통 접근성/학군 품질 같은 질적 피쳐가 들어오면 별도 버전으로 분리한다.
