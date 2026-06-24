# ver06201631_ver2_lightgbm_multihorizon

## 1. 실험 개요

- 버전: ver2
- 목적: `horizon_months`를 입력으로 받아 N개월 뒤 KB매매시세 상승률을 예측하는 단일 회귀 모델
- 입력 데이터: `C:/Users/User/Desktop/final/data/apartment/preprocessed/apartment_multihorizon.csv`
- 타깃: `target_return_pct`
- 사용 horizon: 12, 24, 36, 48, 60개월
- 모델: LightGBM Regressor
- Primary metric: MAE
- 모델 파일: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/models/apartment_return_lightgbm_ver2_multihorizon_target_return_pct_20260620_164513.pkl`
- Metric 파일: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/metrics_target_return_pct_20260620_164513.json`

## 2. 라벨 구조

ver1은 `target_1yr`, `target_3yr`, `target_5yr` 중 하나를 선택해서 모델을 학습했다.

ver2는 같은 기준월 행을 여러 horizon으로 펼친다.

| 기준월 | horizon_months | 미래월 | 라벨 |
|---|---:|---|---|
| 2022-03 | 12 | 2023-03 | `target_return_pct` |
| 2022-03 | 24 | 2024-03 | `target_return_pct` |
| 2022-03 | 36 | 2025-03 | `target_return_pct` |
| 2022-03 | 48 | 2026-03 | `target_return_pct` |

계산식:

```text
target_return_pct = (future_sale_price_manwon / kb_sale_price_manwon - 1) * 100
```

KB매매시세가 0인 행은 라벨 계산에서 제외했다.

## 3. 데이터 규모

| horizon_months | 행 수 |
|---:|---:|
| 12 | 845,412 |
| 24 | 578,570 |
| 36 | 387,338 |
| 48 | 200,306 |
| 60 | 15,309 |
| 전체 | 2,026,935 |

## 4. 데이터 분리

시간 순서를 유지한 7:2:1 비율 분리를 사용했다.

| Split | 행 수 | 포함 horizon |
|---|---:|---|
| Train | 1,665,765 | 12, 24, 36, 48, 60 |
| Valid | 217,414 | 12, 24 |
| Test | 143,756 | 12 |

주의: 데이터 기간이 2021-06 ~ 2026-06으로 짧기 때문에 뒤쪽 기준월에서는 긴 horizon 라벨이 존재하지 않는다. 따라서 현재 test set은 12개월 horizon 성능만 검증한다.

## 5. 사용 컬럼

아래 26개 컬럼을 feature로 사용했다. ver1 대비 `horizon_months`가 추가됐다.

| 컬럼 | 한국어 의미 | 처리 |
|---|---|---|
| `horizon_months` | 몇 개월 뒤 상승률을 예측할지 나타내는 예측 기간 | 숫자 |
| `kb_sale_price_manwon` | 현재 월 KB매매시세, 만원 | 숫자 |
| `kb_jeonse_price_manwon` | 현재 월 KB전세시세, 만원 | 숫자 |
| `kb_jeonse_ratio_pct` | KB 시세 기준 전세가율, % | 숫자 |
| `kb_price_gap_manwon` | KB매매시세와 KB전세시세 차이, 만원 | 숫자 |
| `actual_sale_avg_manwon` | 해당 월 실거래 매매 평균가, 만원 | 숫자 |
| `actual_jeonse_avg_manwon` | 해당 월 실거래 전세 평균가, 만원 | 숫자 |
| `actual_jeonse_ratio_pct` | 실거래 평균 기준 전세가율, % | 숫자 |
| `actual_sale_count` | 해당 월 매매 실거래 건수 | 숫자 |
| `actual_jeonse_count` | 해당 월 전세 실거래 건수 | 숫자 |
| `actual_monthly_rent_count` | 해당 월 월세 실거래 건수 | 숫자 |
| `gu` | 서울 자치구명 | 범주형 |
| `lat` | 단지 위도 | 숫자 |
| `lon` | 단지 경도 | 숫자 |
| `households_total` | 단지 전체 세대수 | 숫자 |
| `built_yyyymm` | 준공년월. 원천 형식 유지 | 숫자 |
| `property_type` | 원천 물건종류 코드 | 범주형 |
| `supply_area_pyeong` | 공급면적, 평 | 숫자 |
| `exclusive_area_pyeong` | 전용면적, 평 | 숫자 |
| `contract_area_pyeong` | 계약면적, 평 | 숫자 |
| `supply_area_m2` | 공급면적, 제곱미터 | 숫자 |
| `exclusive_area_m2` | 전용면적, 제곱미터 | 숫자 |
| `housing_type` | 주택형 | 범주형 |
| `households_by_size` | 해당 평형/면적의 세대수 | 숫자 |
| `floor_area_ratio` | 용적률 | 숫자 |
| `building_coverage_ratio` | 건폐율 | 숫자 |

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
| Train | 5.1827 | 7.3417 | 0.6493 | 111.4111 | 0.7475 |
| Valid | 7.5331 | 11.5048 | 0.0399 | 123.7643 | 0.4792 |
| Test | 9.5543 | 13.5895 | -0.5334 | 136.3163 | 0.1140 |

## 8. Horizon별 Metric

### Train

| Horizon | Rows | MAE | RMSE | R2 | Spearman |
|---:|---:|---:|---:|---:|---:|
| 12 | 532,031 | 4.0359 | 5.6524 | 0.4019 | 0.5814 |
| 24 | 530,781 | 5.5226 | 7.8485 | 0.5886 | 0.7478 |
| 36 | 387,338 | 6.0258 | 8.4666 | 0.6720 | 0.8058 |
| 48 | 200,306 | 5.5538 | 7.4075 | 0.7739 | 0.8681 |
| 60 | 15,309 | 7.0695 | 9.3386 | 0.7339 | 0.8599 |

### Valid

| Horizon | Rows | MAE | RMSE | R2 | Spearman |
|---:|---:|---:|---:|---:|---:|
| 12 | 169,625 | 6.0484 | 9.2356 | -0.1127 | 0.4135 |
| 24 | 47,789 | 12.8029 | 17.3035 | -0.0771 | 0.6838 |

### Test

| Horizon | Rows | MAE | RMSE | R2 | Spearman |
|---:|---:|---:|---:|---:|---:|
| 12 | 143,756 | 9.5543 | 13.5895 | -0.5334 | 0.1140 |

## 9. 해석

- ver2는 하나의 모델로 여러 예측 기간을 처리할 수 있게 된 점이 가장 큰 구조 개선이다.
- 전체 train/valid Spearman은 ver1보다 높지만, test는 마지막 12개월 horizon만 평가되어 직접 비교에 주의가 필요하다.
- Test MAE 9.5543은 ver1의 9.4061보다 약간 나쁘다.
- Valid에서는 horizon 24개월 Spearman이 0.6838로 순위 예측 신호가 보이지만, MAE는 12.8029로 크다.
- 36/48/60개월 horizon은 train에만 존재하므로, 현재 split으로는 장기 horizon의 out-of-time 성능을 검증할 수 없다.

## 10. 다음 실험 후보

- horizon별 검증이 가능하도록 split 전략을 조정한다. 예: 기준월 기준 test 외에 horizon별 holdout 설계.
- lag/rolling 피처를 추가한다.
- `horizon_months`를 숫자 하나가 아니라 `log_horizon`, horizon bucket 등으로 확장한다.
- 장기 horizon의 표본 부족 문제를 해결하기 위해 데이터 기간을 더 확보한다.
- horizon별 별도 모델과 multi-horizon 단일 모델을 비교한다.
