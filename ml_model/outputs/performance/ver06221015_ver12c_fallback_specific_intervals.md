# ver12c Fallback-Specific Prediction Intervals

## 목적

ver12c는 `complex_id+horizon` offset이 있는 단지와 `horizon_global` fallback 단지를 모두 예측한다. 하지만 두 그룹은 오차 분포가 다르므로 같은 P80/P90 interval을 표시하면 fallback 단지의 불확실성을 과소평가할 수 있다.

## 분석 방법

`predictions_test_target_return_pct_20260622_060733.csv`에 ver12c offset을 적용한 뒤, `calibration_type`별 오차를 분리했다.

- `complex_id+horizon`: 해당 단지와 horizon의 residual offset이 있음
- `horizon_global`: 단지별 offset은 없지만 horizon별 global residual offset을 사용
- 60m: 검증 가능한 test window가 없어 기존 global fallback 유지

재현 스크립트:

- `scripts/analyze_error_profile_by_fallback.py`
- 산출물: `streamlit/ml_model/outputs/calibration/ver12c_error_profile_by_fallback.json`

## 주요 결과

| Horizon | Type | Rows | MAE | P80 | P90 |
|---:|---|---:|---:|---:|---:|
| 12m | complex_id+horizon | 78,035 | 5.8188 | 9.6525 | 14.4548 |
| 12m | horizon_global | 4,536 | 8.7386 | 13.2247 | 19.3750 |
| 24m | complex_id+horizon | 59,957 | 6.7900 | 11.0926 | 17.5971 |
| 24m | horizon_global | 996 | 9.6643 | 14.2427 | 25.3343 |
| 36m | complex_id+horizon | 59,961 | 7.5498 | 12.4289 | 19.9253 |
| 36m | horizon_global | 991 | 10.2307 | 16.0776 | 25.1585 |
| 48m | complex_id+horizon | 59,910 | 5.4952 | 8.8773 | 13.3852 |
| 48m | horizon_global | 1,018 | 7.5499 | 12.1668 | 17.8746 |

fallback 단지는 모든 horizon에서 더 큰 오차를 보였다.

## Service 반영

- `streamlit/modules/ml_predictor.py`
  - `MULTIHORIZON_INTERVALS`를 fallback type별 dict로 변경했다.
  - `complex_id+horizon`과 `horizon_global`에 서로 다른 P80/P90 interval을 사용한다.
  - `horizon_global` fallback 예측은 non-60m도 `confidence=low`로 표시한다.
- `scripts/smoke_test_service_prediction.py`
  - fallback 샘플의 non-60m horizon이 `horizon_global`과 `low` confidence를 반환하는지 검증한다.

## 검증 결과

covered `complex_id=1`:

```text
12m: P80 +/- 9.7%p | medium | complex_id+horizon
24m: P80 +/- 11.1%p | medium | complex_id+horizon
36m: P80 +/- 12.4%p | low | complex_id+horizon
```

fallback `complex_id=7`:

```text
12m: P80 +/- 13.2%p | low | horizon_global
24m: P80 +/- 14.2%p | low | horizon_global
36m: P80 +/- 16.1%p | low | horizon_global
```

검증 명령어:

```powershell
python -m py_compile C:\Users\User\Desktop\final\scripts\analyze_error_profile_by_fallback.py C:\Users\User\Desktop\final\streamlit\modules\ml_predictor.py C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py C:\Users\User\Desktop\final\scripts\smoke_test_service_ui_captions.py
```

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\analyze_error_profile_by_fallback.py
```

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py
```

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\smoke_test_service_ui_captions.py
```

## 판단

서비스 후보는 계속 ver12c다. 이번 변경은 point prediction 성능 개선이 아니라 uncertainty calibration 개선이다. 사용자가 클릭한 단지가 fallback 대상일 때 더 넓은 예측구간과 low confidence가 표시되므로, 개별 단지 예측을 더 정직하게 보여준다.
