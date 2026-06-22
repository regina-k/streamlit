# ver06222220_ver12d_group_residual_fallback

## 목적

12/24/36/60개월 전용 모델을 따로 만들지 않고, 기존 ver9b 단일 multi-horizon LightGBM 구조를 유지한다. `horizon_months`를 입력 피처로 넣어 원하는 개월 수의 상승률을 예측하되, 단지별 보정값이 없는 경우의 성능을 개선하기 위해 `구 + 평형대 + horizon` residual fallback을 추가했다.

## 구조

- base model: `ver9b` multi-horizon LightGBM
- service model version: `ver12d_ver9b_plus_recent3_horizon_complex_group_fallback`
- 입력 horizon: 12/24/36/60개월
- fallback 순서:
  1. `complex_id + horizon_months`
  2. `horizon_months + gu + area_bin`
  3. `horizon_global`
  4. `global`

`area_bin`은 전용면적 평 기준으로 `a18`, `a25`, `a34`, `a45`, `a45p`로 나눈다. group fallback은 최근 3개월 validation residual 평균을 사용하고, 그룹 최소 행 수는 100으로 설정했다.

## 데이터 및 산출물

- feature data: `C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_ver9_stability_features.csv`
- latest service feature store: `C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_ver9_latest_features.csv`
- group fallback offsets: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver12d_group_residual_fallback_offsets.csv`
- metrics: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver12d_group_residual_fallback_metrics.json`
- coverage: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver12d_service_offset_coverage.json`

## 성능

| version | MAE | RMSE | R2 | Spearman | P80 abs error | P90 abs error |
|---|---:|---:|---:|---:|---:|---:|
| ver12c | 6.4437 | 9.7261 | 0.5962 | 0.8060 | 10.4476 | 16.1566 |
| ver12d | 6.4376 | 9.7159 | 0.5971 | 0.8064 | 10.4177 | 16.1514 |

fallback별 test 성능:

| fallback | rows | MAE | RMSE | R2 | P80 | P90 |
|---|---:|---:|---:|---:|---:|---:|
| `complex_id+horizon` | 257,863 | 6.3720 | 9.6199 | 0.6066 | 10.3363 | 16.0426 |
| `group_gu_area` | 7,402 | 8.5799 | 12.4236 | 0.2263 | 12.9248 | 19.8574 |
| `horizon_global` | 139 | 14.0850 | 18.6740 | -1.0719 | 21.3155 | 29.6013 |

개선 폭은 작지만, fallback-only 행에서 `horizon_global`보다 더 지역/평형 맥락이 있는 보정을 적용할 수 있다. latest feature store 기준 24/36개월에서는 약 27.2%의 행이 `group_gu_area` fallback으로 커버된다.

## 재현 명령어

```powershell
python -m py_compile .\streamlit\modules\ml_predictor.py .\scripts\build_group_residual_fallbacks.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\build_group_residual_fallbacks.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_prediction.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_ui_captions.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\analyze_service_offset_coverage.py
```

## 판단

전용 모델 분리보다 multi-horizon 단일 모델을 유지하는 방향이 현재 서비스 목적에 더 적합하다. ver12d는 성능 개선 폭이 크지는 않지만, 12/24/36개월을 하나의 모델 인터페이스로 유지하면서 fallback 품질을 개선한다. 60개월은 여전히 검증 가능한 test window가 없으므로 low confidence로 표시해야 한다.
