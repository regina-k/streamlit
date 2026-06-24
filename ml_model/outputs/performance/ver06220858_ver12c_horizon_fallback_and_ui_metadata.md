# ver12c Horizon Fallback and UI Metadata

## 목적

서비스에서 사용자가 클릭한 개별 단지의 예측을 보여줄 때, 각 horizon별 보정 방식과 source window를 확인할 수 있어야 한다. 또한 `complex_id + horizon_months` offset이 없는 단지에는 전체 horizon 통합 global offset보다 horizon별 global residual fallback이 더 자연스럽다.

## 변경 내용

- `streamlit/app.py`
  - 각 12/24/36/60개월 카드에 residual calibration 정보를 추가 표시한다.
  - 표시 항목: fallback 방식, valid rows, source window.
- `scripts/build_horizon_complex_residual_calibration.py`
  - offset CSV에 `complex_id=-1`인 horizon별 fallback row를 추가한다.
  - fallback row는 해당 horizon의 최근 3개월 residual 평균을 사용한다.
- `streamlit/modules/ml_predictor.py`
  - 단지+horizon offset이 없으면 `(-1, horizon_months)` fallback을 먼저 사용한다.
  - 그래도 없을 때만 전체 global fallback을 사용한다.
- `scripts/compare_residual_refresh_policies.py`
  - 정책 비교도 서비스와 동일하게 horizon별 global fallback을 반영한다.
- `scripts/smoke_test_service_prediction.py`
  - prediction별 `source_min_date`, `source_max_date`를 검증한다.

## 성능 영향

fallback 대상은 전체 test rows의 약 `2.84%`였다. 전체 성능 개선은 작지만, offset coverage 밖 단지의 예측에는 직접 영향을 준다.

| 방식 | 전체 MAE | fallback rows MAE |
|---|---:|---:|
| 전체 global fallback | 6.4462 | 8.9839 |
| horizon global fallback | 6.4437 | 8.8965 |

ver12c 최신 metrics:

- Test MAE: `6.4437`
- Test RMSE: `9.7261`
- Test R2: `0.5962`
- Spearman: `0.8060`
- P80 abs error: `10.4476`
- P90 abs error: `16.1566`

## Smoke Test 확인

covered case `complex_id=1`:

- 12m/24m/36m: `complex_id+horizon`
- 60m: `global`

fallback case `complex_id=7`:

- 12m/24m/36m: `horizon_global`
- 60m: `global`

12m fallback source window 예시:

- `source_min_date=2024-11-01`
- `source_max_date=2025-01-01`

## 검증 명령어

```powershell
python -m py_compile C:\Users\User\Desktop\final\scripts\compare_residual_refresh_policies.py C:\Users\User\Desktop\final\scripts\build_horizon_complex_residual_calibration.py C:\Users\User\Desktop\final\streamlit\modules\ml_predictor.py C:\Users\User\Desktop\final\streamlit\app.py C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py
```

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py
```

## 판단

서비스 후보는 계속 ver12c다. 이번 변경은 핵심 모델 구조 변경이 아니라 fallback과 화면 메타데이터를 운영 관점에 맞게 정렬한 것이다. 개별 단지 예측에서 offset coverage 밖 단지가 들어와도 horizon별 평균 residual을 우선 사용하므로 이전 global fallback보다 더 일관적인 예측을 제공한다.
