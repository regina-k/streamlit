# ver06201631_ver1_lightgbm_target_1yr

## 1. 실험 개요

- 버전: ver1
- 목적: 단지·평형·월 단위 데이터로 1년 뒤 KB매매시세 상승률을 예측
- 입력 데이터: `C:/Users/User/Desktop/final/data/apartment/preprocessed/apartment.csv`
- 타깃: `target_1yr`
- 모델: LightGBM Regressor
- Primary metric: MAE
- 결과 저장 시각: 2026-06-20 16:34
- 모델 파일: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/models/apartment_return_lightgbm_target_1yr_20260620_163423.pkl`
- Metric 파일: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/metrics_target_1yr_20260620_163423.json`

## 2. 데이터 분리

시간 순서를 유지한 7:2:1 비율 분리를 사용했다. 랜덤 split은 사용하지 않았다.

| Split | 기간 | 행 수 | 비고 |
|---|---|---:|---|
| Train | 2021-06-01 ~ 2024-03-01 | 532,031 | 오래된 70% 구간 |
| Valid | 2024-04-01 ~ 2024-12-01 | 169,625 | 다음 20% 구간 |
| Test | 2025-01-01 ~ 2025-06-01 | 143,756 | 마지막 10% 구간 |

학습 시 `target_1yr`가 결측인 행은 제거했다.

## 3. 사용 컬럼

아래 25개 컬럼만 모델 feature로 사용했다. `target_*`, `future_sale_price_*` 같은 미래 정보 컬럼은 사용하지 않았다.

| 컬럼 | 한국어 의미 | 처리 |
|---|---|---|
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

## 4. 첫 학습 행 feature 예시

```text
kb_sale_price_manwon=180000
kb_jeonse_price_manwon=72500
kb_jeonse_ratio_pct=40.2
kb_price_gap_manwon=107500.0
actual_sale_avg_manwon=186000
actual_jeonse_avg_manwon=48300
actual_jeonse_ratio_pct=25.9
actual_sale_count=0
actual_jeonse_count=2
actual_monthly_rent_count=2
gu=광진구
lat=37.51938
lon=127.0367525
households_total=548
built_yyyymm=1985.08
property_type=1
supply_area_pyeong=30.99
exclusive_area_pyeong=25.68
contract_area_pyeong=32.08
supply_area_m2=102.47
exclusive_area_m2=84.92
housing_type=NaN
households_by_size=380
floor_area_ratio=174.0
building_coverage_ratio=15.0
```

## 5. 모델 설정

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

## 6. Metric

`target_1yr`는 % 단위 상승률이므로 MAE/RMSE는 percentage point 단위로 해석한다.

| Split | MAE | RMSE | R2 | MAPE | Spearman |
|---|---:|---:|---:|---:|---:|
| Train | 3.6825 | 5.2027 | 0.4933 | 103.9225 | 0.6427 |
| Valid | 6.0329 | 9.4194 | -0.1574 | 134.2958 | 0.3659 |
| Test | 9.4061 | 13.5241 | -0.5187 | 147.9689 | 0.0682 |

## 7. 해석

- Test MAE 9.4061은 실제 1년 상승률과 예측값이 평균 약 9.41%p 차이난다는 뜻이다.
- 7:2:1 split으로 바꾸면서 valid 행 수가 늘었고, test는 마지막 6개월 구간으로 정리됐다.
- Valid/Test R2가 음수이므로 아직 평균 예측보다 안정적으로 낫다고 보기는 어렵다.
- Test Spearman 0.0682로 순위 예측력도 매우 약하다.
- 현재 실험은 ver1 baseline으로 남기고, 이후 lag/rolling 피처 추가 실험의 비교 기준으로 사용한다.

## 8. 다음 실험 후보

- 단지·평형별 최근 1/3/6/12개월 매매시세 변화율 추가.
- 단지·평형별 이동평균 및 모멘텀 추가.
- 구 단위 지수 피처 결합.
- `target_3yr` 모델 별도 학습.
- MAE 외 Top-K hit rate와 상위 예측군 실제 평균 수익률 추가.
