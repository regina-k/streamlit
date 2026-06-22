# ver12 Horizon-Specific Complex Residual Calibration

## 목적

사용자가 클릭한 개별 단지의 상승률 예측을 더 잘 맞히기 위해 ver11의 단지별 residual 보정을 horizon별로 분리했다. ver11은 `complex_id` 단위 offset 하나를 12/24/36/48/60개월 예측에 공통 적용했지만, 실제 오차 패턴은 예측 기간별로 다를 수 있다.

## 실험 구조

- 기반 모델: ver9b LightGBM multi-horizon
- 기반 예측 컬럼: `prediction_calibrated`
- 보정 대상: `target_return_pct - prediction_calibrated`
- 보정 그룹: `complex_id + horizon_months`
- shrinkage: `3.0`
- min rows: `2`
- fallback: horizon별 단지 offset이 없으면 global residual offset 사용
- 생성 산출물:
  - `scripts/build_horizon_complex_residual_calibration.py`
  - `streamlit/ml_model/outputs/calibration/ver12_horizon_complex_residual_offsets.csv`
  - `streamlit/ml_model/outputs/calibration/ver12_horizon_complex_residual_metrics.json`

## 성능 비교

| 버전 | 구조 | Test MAE | Test RMSE | Test R2 | Spearman | P80 abs error | P90 abs error |
|---|---|---:|---:|---:|---:|---:|---:|
| ver9b | multi-horizon base calibrated | 8.2285 | 12.1852 | 0.3662 | 0.6695 | 13.1196 | 20.3667 |
| ver11 | `complex_id` residual offset | 6.8216 | 10.1909 | 0.5567 | 0.7948 | 11.0954 | 16.9222 |
| ver12 | `complex_id + horizon_months` residual offset | 6.4354 | 9.7467 | 0.5945 | 0.8164 | 10.7157 | 16.2855 |

## Horizon별 Test MAE

| Horizon | Rows | MAE | RMSE | R2 | Spearman | Bias |
|---:|---:|---:|---:|---:|---:|---:|
| 12m | 82,571 | 5.9112 | 8.8990 | 0.3647 | 0.6928 | -2.6776 |
| 24m | 60,953 | 6.6304 | 10.0259 | 0.6041 | 0.8571 | -5.2786 |
| 36m | 60,952 | 7.7883 | 11.7536 | 0.5622 | 0.8418 | -6.7444 |
| 48m | 60,928 | 5.5974 | 8.2298 | 0.7375 | 0.8750 | -3.3883 |

60m는 현재 test window가 없어 정량 검증 대상에 포함되지 않았다. 서비스에서는 60m 예측을 반환하되 global fallback과 low confidence로 유지한다.

## Service 반영

- `streamlit/modules/ml_predictor.py`
  - service model version을 `ver12_ver9b_plus_horizon_complex_residual`로 변경했다.
  - horizon별 offset 파일 `ver12_horizon_complex_residual_offsets.csv`를 읽도록 추가했다.
  - 각 prediction에 `residual_calibration` 메타데이터를 포함한다.
  - top-level에도 대표 `residual_calibration`과 전체 `residual_calibration_by_horizon`을 반환한다.
- `scripts/smoke_test_service_prediction.py`
  - prediction별 residual calibration schema까지 검증하도록 확장했다.

## 재현 명령어

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\build_horizon_complex_residual_calibration.py
```

```powershell
python -m py_compile C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py C:\Users\User\Desktop\final\streamlit\modules\ml_predictor.py C:\Users\User\Desktop\final\streamlit\app.py
```

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py
```

## 판단

ver12는 현재까지의 multi-horizon 서비스 후보 중 가장 좋다. MAE, RMSE, R2, Spearman, P80/P90 절대오차가 모두 ver11보다 개선됐다. 단, 개선은 최근 validation residual이 다음 test 구간에도 이어진다는 적응형 보정 가정에 의존한다. 따라서 운영에서는 새 월별 라벨이 확보될 때 offset을 주기적으로 재생성해야 한다.
