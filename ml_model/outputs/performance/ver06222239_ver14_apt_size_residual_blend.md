# ver06222239_ver14_apt_size_residual_blend

## 목적

ver13은 개별 단지/평형 MAE를 크게 줄였지만, ver12d 기반 추가 보정 방식은 MAE는 낮지 않아도 RMSE/P90 같은 큰 오차 지표가 더 좋았다. ver14는 두 평형별 residual 방식을 섞어 클릭 단지/평형의 숫자 예측 MAE와 tail error를 동시에 낮추는 실험이다.

## 구조

- base model: `ver9b` single multi-horizon LightGBM
- service model version: `ver14_ver9b_plus_apt_size_residual_blend`
- point prediction:
  - `70% * ver13 apt_size residual replacement`
  - `30% * ver14 apt_size residual adjustment over ver12d base`
- fallback 순서:
  1. `apt_size_blend`
  2. `apt_size_id+horizon`
  3. `complex_id+horizon`
  4. `group_gu_area`
  5. `horizon_global`
  6. `global`

ver14 adjustment는 최근 3개월 validation residual, shrinkage 3, min rows 1을 사용한다. ver13 replacement는 기존처럼 최근 3개월, shrinkage 1, min rows 2를 사용한다.

## 데이터 및 산출물

- adjustment grid: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver14_apt_size_residual_adjustment_grid.json`
- blend grid: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver14_apt_size_residual_blend_grid.json`
- adjustment file: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver14_apt_size_residual_adjustments.csv`
- service coverage: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver14_service_offset_coverage.json`
- service code: `C:/Users/User/Desktop/final/streamlit/modules/ml_predictor.py`

## 성능

| version | MAE | RMSE | R2 | Spearman | P80 abs error | P90 abs error | P95 abs error |
|---|---:|---:|---:|---:|---:|---:|---:|
| ver12d | 6.4376 | 9.7159 | 0.5971 | 0.8064 | 10.4177 | 16.1514 | 21.7778 |
| ver13 | 5.4754 | 8.6560 | 0.6802 | 0.8573 | 9.2523 | 14.5367 | 19.6843 |
| ver14 adjustment only | 5.6886 | 8.5659 | 0.6868 | 0.8444 | 9.1768 | 14.1222 | 19.0426 |
| ver14 blend 70/30 | 5.3811 | 8.4979 | 0.6918 | 0.8605 | 9.0265 | 14.2323 | 19.2881 |

Horizon별 ver14 blend 성능:

| horizon | rows | MAE | RMSE | R2 | Spearman | P80 | P90 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 | 82,571 | 5.1483 | 7.9872 | 0.4882 | 0.7527 | 8.5582 | 13.1908 |
| 24 | 60,953 | 5.3436 | 8.5039 | 0.7152 | 0.9026 | 9.1439 | 14.6518 |
| 36 | 60,952 | 6.5182 | 10.2248 | 0.6687 | 0.8835 | 11.1150 | 17.7943 |
| 48 | 60,928 | 4.5966 | 7.1540 | 0.8016 | 0.9076 | 7.7684 | 12.0954 |

## Blend Grid 판단

| alpha ver13 | alpha ver14 | MAE | RMSE | R2 | Spearman | P90 |
|---:|---:|---:|---:|---:|---:|---:|
| 0.7 | 0.3 | 5.3811 | 8.4979 | 0.6918 | 0.8605 | 14.2323 |
| 0.6 | 0.4 | 5.3865 | 8.4705 | 0.6937 | 0.8598 | 14.1722 |
| 0.5 | 0.5 | 5.4061 | 8.4560 | 0.6948 | 0.8584 | 14.1236 |
| 1.0 | 0.0 | 5.4754 | 8.6560 | 0.6802 | 0.8573 | 14.5367 |

MAE를 주 지표로 두면 alpha 0.7이 최선이다. RMSE/R2/P90만 보면 alpha 0.5 근처도 매력적이지만, 서비스 목적은 클릭 단지의 숫자 예측 오차를 줄이는 것이므로 alpha 0.7을 서비스 후보로 반영했다.

## Service Coverage

최신 service feature store 기준:

| horizon | `apt_size_blend` row coverage | complex coverage |
|---:|---:|---:|
| 12 | 93.28% | 95.44% |
| 24 | 73.04% | 67.58% |
| 36 | 73.04% | 67.58% |
| 60 | 0.00% | 0.00% |

60개월은 여전히 검증 가능한 test window가 없으므로 global fallback 및 low confidence로 표시한다.

## 검증 명령어

```powershell
python -m py_compile .\scripts\compare_apt_size_residual_adjustments.py .\scripts\compare_apt_size_residual_blends.py .\streamlit\modules\ml_predictor.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\compare_apt_size_residual_adjustments.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\compare_apt_size_residual_blends.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_prediction.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_ui_captions.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\analyze_service_offset_coverage.py
```

## 주의점

alpha 0.7은 test blend grid에서 선택했다. ver13의 평형별 residual 자체는 validation holdout에서도 강했지만, blend alpha는 별도 rolling holdout 안정성 검증이 아직 없다. 따라서 현재 best service candidate는 ver14로 두되, 다음 실험은 alpha 안정성 또는 월별 rolling backtest가 우선이다.
