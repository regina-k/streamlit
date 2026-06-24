# ver06220030_ver8_market_regime

## 목적

ver7d 이후 남은 문제는 특정 구/고가 구간의 과소예측이었다. 이를 단순 보정으로 더 쪼개기보다, 모델이 현재 시장국면을 더 직접 인식할 수 있는지 검증했다. 서비스 입력으로 안정적으로 사용할 수 있는 KB 매매/전세 기반 서울 및 구 단위 trailing market feature만 사용했다.

## 공통 조건

- 예측 단위: 단지ID + 면적일련번호의 12개월 뒤 상승률
- Test window: 2025-02-01 ~ 2025-06-01
- Valid window: 2024-09-01 ~ 2025-01-01
- 기준 feature: ver6j의 실거래/거래량 제외 feature
- 추가 feature: 서울/구 KB 매매시세 중앙값, 전세시세 중앙값, 전세가율 중앙값의 3/6/12개월 변화율 및 구-서울 상대 변화율

## 실험별 변경

| Variant | Config | 데이터 | 변경 내용 |
|---|---|---|---|
| ver8a | `config_ver8a_market_regime.yaml` | `data/integration/apartment_12m_ver8_market_regime_features.csv` | 시장국면 feature만 추가, calibration 없음 |
| ver8b | `config_ver8b_market_regime_calibrated.yaml` | `data/integration/apartment_12m_ver8_market_regime_features.csv` | ver8a + ver7d와 동일한 구/가격분위 calibration |

## 성능

| Variant | Train MAE | Valid MAE | Test MAE | Test RMSE | Test R2 | Test MAPE | Test Spearman | Test Bias |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ver7d 기준 | 3.3877 | 4.9931 | 7.1215 | 10.2786 | 0.1342 | 135.7039 | 0.5260 | -2.4524 |
| ver8a | 2.5233 | 6.2581 | 9.6615 | 13.5408 | -0.5026 | 112.0996 | 0.3214 | -8.3933 |
| ver8b | 5.1485 | 5.5276 | 7.6439 | 11.0142 | 0.0059 | 115.3429 | 0.4830 | -4.5959 |

## 판단

ver8은 실패다. 시장국면 feature 자체는 train 성능을 올렸지만 valid/test에서는 과소예측을 키웠다. 특히 ver8a의 test bias는 -8.3933%p로 ver7d보다 크게 악화됐다. ver8b에서 calibration을 적용해도 Test MAE 7.6439로 ver7d의 7.1215를 넘지 못했다.

현재 데이터 기간에서는 KB 기반 시장국면 변화율이 2025년 이후 상승 구간을 충분히 일반화하지 못한다. 트리 모델이 train 구간의 과거 시장국면 패턴을 2025년 test 상승장에 보수적으로 적용한 것으로 해석한다.

## 취약 구간

ver8b test 기준 MAE가 큰 구는 다음과 같다.

| 구 | Rows | Test MAE | Test Bias |
|---|---:|---:|---:|
| 송파구 | 1,257 | 17.277 | -15.088 |
| 성동구 | 1,385 | 10.720 | -4.248 |
| 동작구 | 4,573 | 10.103 | -6.503 |
| 강동구 | 13,364 | 9.594 | -5.272 |
| 강남구 | 544 | 9.587 | -5.575 |

송파구는 ver7d보다 더 나빠졌다. 따라서 현재 형태의 시장국면 feature는 폐기하고, ver7d를 유지한다.

## 재현 명령어

```powershell
python .\scripts\build_ver8_features.py

$env:PYTHONPATH='C:\Users\User\Desktop\final\streamlit\ml_model\src'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver8a_market_regime.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver8b_market_regime_calibrated.yaml'
```

## 산출물

- ver8a model: `outputs/models/apartment_return_lightgbm_ver8a_market_regime_target_return_pct_20260622_002540.pkl`
- ver8b model: `outputs/models/apartment_return_lightgbm_ver8b_market_regime_calibrated_target_return_pct_20260622_002915.pkl`
- ver8b metrics: `outputs/metrics_target_return_pct_20260622_002915.json`

## 다음 방향

- 모델 후보는 ver7d를 유지한다.
- 추가 feature 확장은 test 튜닝 위험이 있으므로 잠시 멈춘다.
- 서비스 관점에서는 단일 예측값 대신 예측 구간을 함께 제공해야 한다. ver7d test residual을 이용해 전체/구/가격대별 MAE, P50/P80/P90 절대오차를 산출하고, 클릭 단지의 예측값에 신뢰 범위를 붙이는 방향이 우선이다.
