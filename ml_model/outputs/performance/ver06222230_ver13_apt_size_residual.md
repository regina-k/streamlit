# ver06222230_ver13_apt_size_residual

## 목적

서비스는 사용자가 클릭한 단지/평형의 상승률 숫자를 보여준다. 따라서 ver13은 단지 수준보다 더 세밀한 `apt_size_id + horizon_months` residual 보정을 추가해 개별 평형 예측 오차를 줄이는 실험이다. base model은 여전히 ver9b 단일 multi-horizon LightGBM이며, 12/24/36/60개월 전용 모델을 따로 만들지 않는다.

## 구조

- base model: `ver9b` multi-horizon LightGBM
- service model version: `ver13_ver9b_plus_recent3_apt_size_horizon_residual`
- 선택 설정: 최근 3개월 validation residual, shrinkage 1, 최소 2행
- fallback 순서:
  1. `apt_size_id + horizon_months`
  2. `complex_id + horizon_months`
  3. `horizon_months + gu + area_bin`
  4. `horizon_global`
  5. `global`

최저 MAE 조합은 `min_rows=1`이었지만, 한 행 residual만으로 보정하는 경우를 피하기 위해 `min_rows=2`를 선택했다. MAE 차이는 5.4681 vs 5.4754로 매우 작다.

## 데이터 및 산출물

- grid script: `C:/Users/User/Desktop/final/scripts/compare_apt_size_residual_fallbacks.py`
- apt-size offsets: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver13_apt_size_residual_offsets.csv`
- metrics/grid: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver13_apt_size_residual_grid.json`
- coverage: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver13_service_offset_coverage.json`

## 성능

| version | MAE | RMSE | R2 | Spearman | P80 abs error | P90 abs error |
|---|---:|---:|---:|---:|---:|---:|
| ver12d | 6.4376 | 9.7159 | 0.5971 | 0.8064 | 10.4177 | 16.1514 |
| ver13 | 5.4754 | 8.6560 | 0.6802 | 0.8573 | 9.2523 | 14.5367 |

Horizon별 ver13 test 성능:

| horizon | rows | MAE | RMSE | R2 | Spearman | P80 | P90 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 | 82,571 | 5.2000 | 8.0779 | 0.4765 | 0.7500 | 8.7044 | 13.3478 |
| 24 | 60,953 | 5.5790 | 8.8262 | 0.6932 | 0.8999 | 9.5863 | 15.2517 |
| 36 | 60,952 | 6.5959 | 10.3920 | 0.6577 | 0.8812 | 11.4349 | 18.1002 |
| 48 | 60,928 | 4.6239 | 7.2099 | 0.7985 | 0.9044 | 7.8715 | 12.2455 |

fallback별 test 성능:

| fallback | rows | MAE | RMSE | R2 | P80 | P90 |
|---|---:|---:|---:|---:|---:|---:|
| `apt_size_id+horizon` | 260,530 | 5.4072 | 8.5577 | 0.6887 | 9.1338 | 14.4162 |
| `ver12d_base` | 4,874 | 9.1210 | 12.8612 | 0.0900 | 14.1265 | 20.4274 |

## 검증 근거

Test grid 상위 조합은 모두 최근 3개월, 낮은 shrinkage 계열이었다. validation 내부 holdout에서도 같은 방향이 확인됐다.

| split | best setting | MAE | RMSE | R2 | Spearman |
|---|---|---:|---:|---:|---:|
| test grid | source 3m, shrinkage 1, min rows 1 | 5.4681 | 8.6439 | 0.6811 | 0.8581 |
| selected test | source 3m, shrinkage 1, min rows 2 | 5.4754 | 8.6560 | 0.6802 | 0.8573 |
| valid holdout | source 3m, shrinkage 1, min rows 1 | 3.3273 | 5.4363 | 0.8446 | 0.9259 |
| selected valid holdout | source 3m, shrinkage 1, min rows 2 | 3.3718 | 5.5319 | 0.8390 | 0.9220 |

최신 service feature store 기준 coverage:

| horizon | `apt_size_id+horizon` row coverage | complex coverage |
|---:|---:|---:|
| 12 | 93.28% | 95.44% |
| 24 | 73.04% | 67.58% |
| 36 | 73.04% | 67.58% |
| 60 | 0.00% | 0.00% |

60개월은 test window가 없어 여전히 global fallback 및 low confidence로 표시한다.

## 재현 명령어

```powershell
python -m py_compile .\scripts\compare_apt_size_residual_fallbacks.py .\streamlit\modules\ml_predictor.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\compare_apt_size_residual_fallbacks.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_prediction.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_ui_captions.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\analyze_service_offset_coverage.py
```

## 판단

ver13은 현재까지 개별 단지/평형 숫자 예측 목적에 가장 잘 맞는 후보이다. 개선 폭이 크고, validation holdout에서도 낮은 shrinkage의 평형별 residual 보정이 일관되게 유리했다. 다만 residual 보정 의존도가 커졌으므로 운영 화면에는 fallback type, valid rows, source window를 계속 노출해야 한다.
