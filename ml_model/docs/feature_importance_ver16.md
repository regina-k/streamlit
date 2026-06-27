# ver16 Feature Importance 분석

## 1. 목적

최종 서비스 모델 `ver16_hierarchical_apt_size_residual`의 base LightGBM이 실제로 어떤 feature를 사용했는지 확인하기 위해 gain/split importance와 target 상관을 산출했다. ver16의 최종 예측은 base LightGBM 예측값에 계층형 residual calibration을 더하는 구조이므로, 아래 중요도는 base model 기준이다.

## 2. 분석 대상

- 모델 파일: ml_model/outputs/models/ver16_service_multihorizon_base_model.pkl
- feature store: data/integration/apartment_multihorizon_ver9_stability_features.csv
- 전체 feature 수: 55개
- 중요도 CSV: ml_model/docs/feature_importance_ver16.csv

## 3. Feature Group Importance

| feature_group | features | gain_share_pct | split_share_pct |
| --- | --- | --- | --- |
| apartment_meta | 15 | 31.26 | 29.08 |
| individual_stability_without_actual_tx | 17 | 21.87 | 32.30 |
| kb_market | 4 | 17.26 | 11.39 |
| horizon | 1 | 16.56 | 5.83 |
| poi_accessibility | 18 | 13.05 | 21.40 |

## 4. Gain Importance Top 30

| rank_gain | feature | feature_group | gain_share_pct | split | spearman_corr_target |
| --- | --- | --- | --- | --- | --- |
| 1 | horizon_months | horizon | 16.56 | 4339 | -0.0333 |
| 2 | kb_sale_price_manwon | kb_market | 11.86 | 2382 | 0.2306 |
| 3 | gu | apartment_meta | 6.93 | 3769 |  |
| 4 | households_total | apartment_meta | 6.68 | 2741 | -0.1173 |
| 5 | building_age_years | individual_stability_without_actual_tx | 4.80 | 7105 | -0.0399 |
| 6 | built_yyyymm | apartment_meta | 4.76 | 4450 | 0.0795 |
| 7 | lat | apartment_meta | 4.19 | 2403 | -0.1940 |
| 8 | sale_price_per_supply_pyeong | individual_stability_without_actual_tx | 3.67 | 2595 | 0.1724 |
| 9 | sale_price_per_exclusive_pyeong | individual_stability_without_actual_tx | 3.11 | 2949 | 0.1497 |
| 10 | gu_pp_premium_pct | individual_stability_without_actual_tx | 3.00 | 2257 | 0.0028 |
| 11 | kb_jeonse_ratio_pct | kb_market | 2.07 | 2110 | -0.0120 |
| 12 | hospital_doctor_sum_5000m | poi_accessibility | 1.93 | 1252 | 0.2748 |
| 13 | jeonse_price_per_exclusive_pyeong | individual_stability_without_actual_tx | 1.83 | 2044 | 0.1534 |
| 14 | kb_price_gap_manwon | kb_market | 1.74 | 2325 | 0.2101 |
| 15 | contract_area_pyeong | apartment_meta | 1.71 | 995 | 0.1765 |
| 16 | kb_jeonse_price_manwon | kb_market | 1.60 | 1658 | 0.2038 |
| 17 | lon | apartment_meta | 1.56 | 2020 | 0.0356 |
| 18 | nearest_station_m | poi_accessibility | 1.42 | 1843 | -0.1400 |
| 19 | floor_area_ratio | apartment_meta | 1.29 | 1584 | 0.0964 |
| 20 | households_by_size | apartment_meta | 1.26 | 586 | -0.1381 |
| 21 | nearest_tertiary_hospital_m | poi_accessibility | 1.25 | 1558 | -0.2624 |
| 22 | complex_sale_price_premium_pct | individual_stability_without_actual_tx | 1.23 | 1338 | 0.0159 |
| 23 | hospital_doctor_sum_3000m | poi_accessibility | 1.14 | 1183 | 0.1935 |
| 24 | tertiary_hospital_count_5000m | poi_accessibility | 1.09 | 235 | 0.2865 |
| 25 | gu_price_rank_pct | individual_stability_without_actual_tx | 0.92 | 1599 | 0.1087 |
| 26 | nearest_school_m | poi_accessibility | 0.75 | 1195 | 0.0652 |
| 27 | nearest_hospital_m | poi_accessibility | 0.75 | 1315 | -0.0346 |
| 28 | nearest_middle_school_m | poi_accessibility | 0.73 | 1352 | 0.0330 |
| 29 | exclusive_area_pyeong | apartment_meta | 0.72 | 555 | 0.1662 |
| 30 | nearest_elementary_school_m | poi_accessibility | 0.71 | 1196 | 0.0664 |

## 5. POI Feature 사용 여부

- poi_accessibility 그룹의 gain share는 **13.05%**다. 즉 학교/역/병원 접근성 feature는 0이 아니라 실제 분기에 사용되었다.

- 다만 gain share 기준 주도권은 KB 시세와 단지/평형 안정성 feature에 더 크다. POI는 단독으로 모델을 지배하기보다, 특정 입지 조건에서 보조 신호로 작동한 것으로 해석하는 편이 안전하다.

POI 중요도 상위 feature:

| rank_gain | feature | gain_share_pct | split | spearman_corr_target |
| --- | --- | --- | --- | --- |
| 12 | hospital_doctor_sum_5000m | 1.93 | 1252 | 0.2748 |
| 18 | nearest_station_m | 1.42 | 1843 | -0.1400 |
| 21 | nearest_tertiary_hospital_m | 1.25 | 1558 | -0.2624 |
| 23 | hospital_doctor_sum_3000m | 1.14 | 1183 | 0.1935 |
| 24 | tertiary_hospital_count_5000m | 1.09 | 235 | 0.2865 |
| 26 | nearest_school_m | 0.75 | 1195 | 0.0652 |
| 27 | nearest_hospital_m | 0.75 | 1315 | -0.0346 |
| 28 | nearest_middle_school_m | 0.73 | 1352 | 0.0330 |
| 30 | nearest_elementary_school_m | 0.71 | 1196 | 0.0664 |
| 34 | nearest_high_school_m | 0.63 | 1310 | 0.0129 |

## 6. 해석

- 최상위 feature는 가격 수준, 전세가율/시세갭, 단지 내 면적·가격 순위, 구 대비 프리미엄, 단지 규모 같은 정형 feature가 중심이다. 이는 아파트 상승률 예측에서 현재 가격 포지션과 단지·평형 상대 위치가 가장 강한 신호였다는 뜻이다.

- `horizon_months`도 중요도 상위권에 포함되어, 하나의 모델이 예측 기간별 패턴을 구분하는 데 실제로 이 값을 사용했음을 확인했다.

- POI feature는 gain share가 제한적이지만 0이 아니며, 역/학교/병원 접근성 일부 feature가 top feature 목록에 포함된다. 따라서 입지 feature는 성능의 주역이라기보다 보조 설명 변수로 보는 것이 적절하다.

- 상관계수는 단일 feature와 target의 단순 단조 관계만 보여준다. LightGBM은 비선형 분기와 feature interaction을 사용하므로, 중요도 판단은 correlation보다 gain/split importance를 우선한다.

## 7. Feature 간 상관관계 점검

숫자형 feature를 대상으로 Spearman 절대상관 상위쌍을 산출했다. 전체 데이터가 크기 때문에 300,000행을 고정 random seed로 샘플링해 계산했다. 상세 CSV는 `ml_model/docs/feature_correlation_ver16.csv`에 저장했다.

| feature_a | feature_b | abs_spearman_corr |
| --- | --- | --- |
| kb_sale_price_manwon | log_kb_sale_price | 1.0000 |
| households_by_size | log_households_by_size | 1.0000 |
| households_total | log_households_total | 1.0000 |
| supply_area_pyeong | supply_area_m2 | 1.0000 |
| exclusive_area_pyeong | exclusive_area_m2 | 0.9998 |
| built_yyyymm | built_year | 0.9987 |
| sale_price_per_exclusive_pyeong | sale_price_per_supply_pyeong | 0.9830 |
| built_yyyymm | building_age_years | 0.9814 |
| built_year | building_age_years | 0.9803 |
| supply_area_pyeong | exclusive_area_pyeong | 0.9494 |
| exclusive_area_pyeong | supply_area_m2 | 0.9494 |
| supply_area_pyeong | exclusive_area_m2 | 0.9493 |
| supply_area_m2 | exclusive_area_m2 | 0.9493 |
| supply_area_pyeong | contract_area_pyeong | 0.9364 |
| contract_area_pyeong | supply_area_m2 | 0.9364 |
| kb_price_gap_manwon | log_kb_sale_price | 0.9356 |
| kb_sale_price_manwon | kb_price_gap_manwon | 0.9356 |
| kb_jeonse_price_manwon | log_kb_sale_price | 0.9235 |
| kb_sale_price_manwon | kb_jeonse_price_manwon | 0.9235 |
| complex_area_rank_pct | complex_price_rank_pct | 0.9052 |

해석상 높은 상관은 주로 공급/전용 면적, 가격 per-pyeong 계열, 병원 doctor sum 반경 계열처럼 정의상 유사한 feature에서 나타난다. 이는 선형회귀라면 다중공선성 이슈가 될 수 있지만, LightGBM에서는 치명적 문제라기보다 중요도가 유사 feature 사이에 나뉘는 해석상 주의점으로 보는 것이 적절하다.

## 8. 발표용 요약

최종 모델에서 feature importance를 확인한 결과, KB 시세와 단지·평형 상대 가격 feature가 가장 큰 설명력을 보였고, `horizon_months` 역시 중요 feature로 사용되어 multi-horizon 구조가 실제로 작동함을 확인했다. 학교·역·병원 접근성 feature도 gain이 0이 아니어서 모델이 일부 입지 정보를 활용했지만, 핵심 신호는 가격·전세·단지 메타 feature였다고 설명하는 것이 정확하다.
