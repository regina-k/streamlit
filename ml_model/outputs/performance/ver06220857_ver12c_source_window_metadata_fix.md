# ver12c Source Window Metadata Fix

## 목적

ver12c는 horizon별 최근 3개월 validation residual을 사용한다. 하지만 기존 offset 파일은 `source_min_date`, `source_max_date`를 전체 horizon 통합 min/max로 기록해, 12/24/36/48개월의 실제 보정 기준 기간을 구분하지 못했다. 예측값 자체에는 영향이 없지만 서비스 운영 메타데이터가 부정확했다.

## 변경 내용

- `scripts/build_horizon_complex_residual_calibration.py`
  - `source_months` 적용 후 horizon별 source window를 계산한다.
  - offset CSV의 각 row에 해당 `horizon_months`의 `source_min_date`, `source_max_date`를 기록한다.
- `streamlit/modules/ml_predictor.py`
  - horizon-specific residual offset을 읽을 때 파일 첫 행의 source window가 아니라 각 row의 source window를 사용한다.
  - global fallback은 전체 offset 파일의 min/max source window를 유지한다.

## 확인 결과

재생성된 `ver12c_recent3_horizon_complex_residual_offsets.csv`의 horizon별 source window:

| Horizon | Source min | Source max |
|---:|---|---|
| 12m | 2024-11-01 | 2025-01-01 |
| 24m | 2023-11-01 | 2024-01-01 |
| 36m | 2022-11-01 | 2023-01-01 |
| 48m | 2021-11-01 | 2022-01-01 |

서비스 smoke test에서 `complex_id=1`, 12m 대표 calibration은 다음과 같이 반환됐다.

- `model_version=ver12c_ver9b_plus_recent3_horizon_complex_residual`
- `fallback=complex_id+horizon`
- `valid_rows=12`
- `source_min_date=2024-11-01`
- `source_max_date=2025-01-01`

## 검증 명령어

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\build_horizon_complex_residual_calibration.py --source-months 3 --shrinkage 10 --min-rows 5 --output C:\Users\User\Desktop\final\streamlit\ml_model\outputs\calibration\ver12c_recent3_horizon_complex_residual_offsets.csv --metrics-output C:\Users\User\Desktop\final\streamlit\ml_model\outputs\calibration\ver12c_recent3_horizon_complex_residual_metrics.json
```

```powershell
python -m py_compile C:\Users\User\Desktop\final\scripts\build_horizon_complex_residual_calibration.py C:\Users\User\Desktop\final\streamlit\modules\ml_predictor.py C:\Users\User\Desktop\final\streamlit\app.py C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py
```

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py
```

## 판단

서비스 후보와 성능 수치는 ver12c 그대로 유지한다. 이번 수정은 예측값 개선이 아니라 보정 메타데이터 정합성 개선이다. 단지별 예측을 운영할 때 horizon별 보정 기준 기간을 정확히 추적할 수 있게 됐다.
