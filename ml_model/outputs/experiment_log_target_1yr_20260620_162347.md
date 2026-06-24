# 실험 기록: target_1yr LightGBM baseline

## 개요

- 실험 목적: 단지·평형·월 단위 데이터로 1년 뒤 KB매매시세 상승률을 예측한다.
- 입력 데이터: `C:/Users/User/Desktop/final/data/apartment/preprocessed/apartment.csv`
- 타깃: `target_1yr`
- 모델: LightGBM Regressor
- Primary metric: MAE
- 모델 파일: `C:\Users\User\Desktop\final\streamlit\ml_model\outputs\models\apartment_return_lightgbm_target_1yr_20260620_162347.pkl`

## 데이터 분리

시간 기준으로 분리했다. 랜덤 분리는 사용하지 않았다.

| Split | 기준 |
|---|---|
| Train | `date <= 2024-06-01` |
| Valid | `2024-06-01 < date <= 2024-12-01` |
| Test | `date >= 2025-01-01` |

학습 시 결측 타깃(`target_1yr`) 행은 제거했다.

| Split | 행 수 |
|---|---:|
| Train | 579,933 |
| Valid | 121,723 |
| Test | 143,756 |

## 사용 컬럼

타깃과 미래 가격 컬럼은 feature에 넣지 않았다.

| 컬럼 | 의미 | 타입/처리 |
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

## 모델 설정

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

## 평가 결과

`target_1yr`는 % 단위 상승률이므로 MAE는 percentage point 단위로 해석한다.

| Split | MAE | RMSE | R2 | MAPE | Spearman |
|---|---:|---:|---:|---:|---:|
| Train | 3.7517 | 5.3302 | 0.4895 | 104.7612 | 0.6415 |
| Valid | 6.2857 | 9.6842 | -0.1391 | 131.5663 | 0.3739 |
| Test | 9.1291 | 13.1692 | -0.4400 | 133.2058 | 0.1767 |

## 해석

- Test MAE 9.1291은 실제 1년 상승률과 예측값이 평균 약 9.13%p 차이난다는 뜻이다.
- Valid/Test R2가 음수라서 현재 모델은 평균 예측보다 안정적으로 낫다고 보기 어렵다.
- Spearman이 Test에서 0.1767이므로 상승률 순위 예측력도 아직 약하다.
- 현재 결과는 baseline으로 기록하고, 이후 피처 추가나 타깃 변경 실험과 비교하는 기준점으로 사용한다.

## 다음 개선 후보

- 단지별 lag/rolling 피처 추가: 최근 1/3/6/12개월 KB매매시세 변화율, 이동평균, 모멘텀.
- 구 단위 시장 지수 피처 결합.
- `target_3yr` 별도 모델 학습 후 비교.
- 가격대/구/평형별 오차 분석.
- MAE 외 Top-K hit rate, Spearman, 상위 예측군 실제 평균 수익률 등 추천 관점 metric 추가.
