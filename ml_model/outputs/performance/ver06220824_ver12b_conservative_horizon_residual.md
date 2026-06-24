# ver12b Conservative Horizon Residual Calibration

## 목적

ver12의 `complex_id + horizon_months` residual 보정은 성능이 좋았지만, shrinkage/min rows 조합을 test grid에서 고른 형태라 최종 서비스 성능으로 해석하기에는 공격적이다. ver12b는 같은 구조를 유지하되 더 보수적인 사전 규칙형 조합을 사용해 test-tuning 위험을 줄인 서비스 후보이다.

## 설정

- 기반 모델: ver9b LightGBM multi-horizon
- 보정 그룹: `complex_id + horizon_months`
- shrinkage: `10.0`
- min rows: `5`
- fallback: horizon별 단지 offset이 없으면 global residual offset
- offset count: `12,805`
- source window: `2021-09-01 ~ 2025-01-01`
- test window: `2022-02-01 ~ 2025-06-01`

## 성능 비교

| 버전 | 설명 | Test MAE | Test RMSE | Test R2 | Spearman | P80 abs error | P90 abs error |
|---|---|---:|---:|---:|---:|---:|---:|
| ver9b | base calibrated multi-horizon | 8.2285 | 12.1852 | 0.3662 | 0.6695 | 13.1196 | 20.3667 |
| ver11 | `complex_id` residual, shrinkage 20 | 6.8216 | 10.1909 | 0.5567 | 0.7948 | 11.0954 | 16.9222 |
| ver12 | `complex_id + horizon`, shrinkage 3, min rows 2 | 6.4354 | 9.7467 | 0.5945 | 0.8164 | 10.7157 | 16.2855 |
| ver12b | `complex_id + horizon`, shrinkage 10, min rows 5 | 6.7041 | 10.1303 | 0.5620 | 0.7998 | 11.1308 | 16.9984 |

## Horizon별 Test MAE

| Horizon | Rows | MAE | RMSE | R2 | Spearman | Bias |
|---:|---:|---:|---:|---:|---:|---:|
| 12m | 82,571 | 6.1299 | 9.1751 | 0.3246 | 0.6644 | -2.6450 |
| 24m | 60,953 | 7.0578 | 10.6244 | 0.5554 | 0.8402 | -5.4544 |
| 36m | 60,952 | 8.0607 | 12.2162 | 0.5270 | 0.8270 | -6.8063 |
| 48m | 60,928 | 5.7713 | 8.4100 | 0.7258 | 0.8660 | -3.2252 |

## Service 반영

- `streamlit/modules/ml_predictor.py`
  - service model version: `ver12b_ver9b_plus_horizon_complex_residual`
  - offset file: `ver12b_horizon_complex_residual_offsets.csv`
  - P80/P90 interval을 ver12b horizon별 error profile로 갱신
- `scripts/smoke_test_service_prediction.py`
  - prediction별 residual calibration metadata 검증 유지

## 검증 명령어

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\build_horizon_complex_residual_calibration.py --shrinkage 10 --min-rows 5 --output C:\Users\User\Desktop\final\streamlit\ml_model\outputs\calibration\ver12b_horizon_complex_residual_offsets.csv --metrics-output C:\Users\User\Desktop\final\streamlit\ml_model\outputs\calibration\ver12b_horizon_complex_residual_metrics.json
```

```powershell
python -m py_compile C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py C:\Users\User\Desktop\final\streamlit\modules\ml_predictor.py C:\Users\User\Desktop\final\streamlit\app.py
```

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py
```

## 판단

서비스 후보는 ver12보다 ver12b가 더 적절하다. ver12가 순수 test metric은 더 좋지만 shrinkage 선택이 test grid에 민감하다. ver12b는 보수적인 shrinkage와 최소 표본 조건을 사용하면서도 ver11보다 MAE, RMSE, R2, Spearman을 모두 개선한다.

60m는 여전히 검증 가능한 test window가 없으므로 global fallback과 low confidence로 유지한다.
