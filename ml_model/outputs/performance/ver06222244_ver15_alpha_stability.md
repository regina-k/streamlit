# ver06222244_ver15_alpha_stability

## 목적

ver14는 test grid에서 `ver13 70% + adjustment 30%` blend가 가장 낮은 MAE를 보였다. 그러나 alpha가 test grid에서 선택됐기 때문에, 서비스 후보로 쓰기 전에 validation 내부 rolling holdout으로 alpha 안정성을 검증했다.

## 검증 방식

- 데이터: `predictions_valid_target_return_pct_20260622_060733.csv`
- horizon별 valid 기간은 5개월이다.
- 각 horizon에서 이전 3개월을 source로 사용하고 다음 1개월을 holdout으로 평가했다.
- 가능한 holdout window는 horizon별 2개, 총 8개다.
- 각 window에서 ver13 replacement, ver14 adjustment, alpha blend를 모두 source window 내부에서 다시 계산했다.
- 기존 test/valid 전체 offset 파일을 그대로 쓰지 않아 holdout leakage를 피했다.

재현 스크립트:

- `C:/Users/User/Desktop/final/scripts/validate_blend_alpha_stability.py`
- output: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver15_alpha_stability_valid_holdout.json`

## 결과

Validation rolling holdout aggregate:

| alpha ver13 | alpha adjustment | MAE | RMSE | R2 | Spearman | P90 |
|---:|---:|---:|---:|---:|---:|---:|
| 1.0 | 0.0 | 2.9489 | 4.8238 | 0.8776 | 0.9413 | 7.4365 |
| 0.9 | 0.1 | 2.9561 | 4.8302 | 0.8773 | 0.9411 | 7.4471 |
| 0.8 | 0.2 | 2.9650 | 4.8383 | 0.8769 | 0.9408 | 7.4598 |
| 0.7 | 0.3 | 2.9755 | 4.8481 | 0.8764 | 0.9405 | 7.4879 |
| 0.5 | 0.5 | 3.0014 | 4.8726 | 0.8751 | 0.9395 | 7.5405 |
| 0.0 | 1.0 | 3.0923 | 4.9623 | 0.8705 | 0.9359 | 7.7145 |

8개 개별 holdout window에서도 MAE 기준 최선 alpha는 모두 1.0이었다. 즉 validation 내부에서는 adjustment blend가 도움이 되지 않았고, ver13 단독이 가장 안정적이었다.

## 판단

ver14는 test set에서는 ver13보다 좋았지만, alpha 0.7 선택이 holdout 안정성 검증을 통과하지 못했다. 서비스 모델은 test 최적화보다 검증 안정성을 우선해야 하므로, 현재 후보를 ver15로 조정한다.

- service model version: `ver15_validated_apt_size_horizon_residual`
- point prediction: ver13과 동일한 `apt_size_id + horizon_months` residual replacement
- fallback order: `apt_size_id+horizon` -> `complex_id+horizon` -> `group_gu_area` -> `horizon_global` -> `global`
- 60m은 계속 global fallback 및 low confidence

## 성능 해석

공식 test 성능은 ver13과 같다.

| version | MAE | RMSE | R2 | Spearman | P80 | P90 |
|---|---:|---:|---:|---:|---:|---:|
| ver13/ver15 | 5.4754 | 8.6560 | 0.6802 | 0.8573 | 9.2523 | 14.5367 |
| ver14 test blend | 5.3811 | 8.4979 | 0.6918 | 0.8605 | 9.0265 | 14.2323 |

ver14의 test 성능은 기록으로 보존하되, 현재 서비스 후보는 holdout 안정성을 통과한 ver15로 둔다.

## 검증 명령어

```powershell
python -m py_compile .\scripts\validate_blend_alpha_stability.py .\streamlit\modules\ml_predictor.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\validate_blend_alpha_stability.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_prediction.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_ui_captions.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\analyze_service_offset_coverage.py
```

## 다음 방향

추가 성능 개선은 alpha blend보다 residual offset의 과적합을 줄이는 쪽이 낫다. 후보는 `apt_size_id` residual의 hierarchical shrinkage, 단지/평형별 source row 수에 따른 동적 confidence, 또는 fallback-only 행의 feature 개선이다.
