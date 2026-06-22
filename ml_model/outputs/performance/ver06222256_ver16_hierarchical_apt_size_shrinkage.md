# ver06222256_ver16_hierarchical_apt_size_shrinkage

## 목적

12개월, 24개월, 36개월, 60개월 전용 모델을 따로 만들지 않고, 기존 ver9b 단일 multi-horizon LightGBM 구조를 유지한다. 즉 inference 때 `horizon_months`에 12/24/36/60을 넣어 예측값을 받는 방식은 그대로 둔다.

이번 ver16은 모델 자체를 교체하지 않고, ver15의 `apt_size_id + horizon_months` residual offset을 더 안정적으로 만드는 실험이다.

## 변경 사항

- 기준 모델: `apartment_return_lightgbm_ver9b_multihorizon_calibrated_target_return_pct_20260622_060733.pkl`
- 서비스용 안정 모델 경로: `streamlit/ml_model/outputs/models/ver16_service_multihorizon_base_model.pkl`
- 기존 ver15: 단지-평형-horizon residual 평균을 0 방향으로 shrinkage
- ver16: 단지-평형-horizon residual 평균을 하위 fallback 보정값 방향으로 shrinkage
- 선택값: 최근 3개 validation 월, `shrinkage=0.5`, `min_rows=1`
- 생성 파일: `streamlit/ml_model/outputs/calibration/ver16_hierarchical_apt_size_offsets.csv`
- 서비스 버전: `ver16_hierarchical_apt_size_residual`

보정식:

```text
residual_offset = prior_mean + weight * (raw_mean - prior_mean)
weight = valid_rows / (valid_rows + shrinkage)
```

여기서 `prior_mean`은 같은 단지/평형이 없을 때 쓰던 `complex_id+horizon`, `group_gu_area`, `horizon_global`, `global` 계층의 보정값이다.

## 성능

| version | Test MAE | Test RMSE | Test R2 | Spearman | P80 | P90 |
|---|---:|---:|---:|---:|---:|---:|
| ver12d | 6.4376 | 9.7159 | 0.5971 | 0.8064 | 10.4177 | 16.1514 |
| ver15 | 5.4754 | 8.6560 | 0.6802 | 0.8573 | 9.2523 | 14.5367 |
| ver16 | 5.0376 | 8.1711 | 0.7150 | 0.8715 | 8.6336 | 13.6911 |

Horizon별 test MAE:

| horizon | MAE | RMSE | P80 | P90 |
|---:|---:|---:|---:|---:|
| 12m | 4.8955 | 7.7892 | 8.2674 | 12.8447 |
| 24m | 4.9194 | 8.1016 | 8.5971 | 13.8572 |
| 36m | 6.0684 | 9.7123 | 10.4556 | 16.8060 |
| 48m | 4.3172 | 6.9706 | 7.5701 | 11.8045 |

Validation rolling holdout에서도 best grid는 같은 설정이었다.

| source_months | shrinkage | min_rows | MAE | RMSE | R2 | Spearman | P90 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 0.5 | 1 | 2.4264 | 4.2110 | 0.9067 | 0.9546 | 6.5323 |

## 서비스 적용

`streamlit/modules/ml_predictor.py`는 이제 `ver16_hierarchical_apt_size_offsets.csv`를 읽는다.

Fallback 순서:

```text
hier_apt_size_id+horizon -> complex_id+horizon -> group_gu_area -> horizon_global -> global
```

최신 feature store 기준 coverage:

- 12m: `hier_apt_size_id+horizon` row coverage 95.29%
- 24m: `hier_apt_size_id+horizon` row coverage 73.04%
- 36m: `hier_apt_size_id+horizon` row coverage 73.04%
- 60m: global fallback 100%, test window가 없어 low confidence 유지

## 검증 명령어

```powershell
cd C:\Users\User\Desktop\final\streamlit\ml_model
$env:PYTHONPATH="src"
python -m ml_project.train --config config/config.yaml
```

위 명령은 base LightGBM 학습과 ver16 hierarchical residual post-calibration을 한 번에 수행한다.

개별 검증 명령:

```powershell
cd C:\Users\User\Desktop\final
python -m py_compile .\scripts\compare_hierarchical_apt_size_shrinkage.py .\scripts\analyze_service_offset_coverage.py .\scripts\smoke_test_service_prediction.py .\scripts\smoke_test_service_ui_captions.py .\streamlit\modules\ml_predictor.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\compare_hierarchical_apt_size_shrinkage.py --selected-source-months 3 --selected-shrinkage 0.5 --selected-min-rows 1
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_prediction.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_ui_captions.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\analyze_service_offset_coverage.py
```

## 판단

ver16은 ver15보다 test와 validation holdout 양쪽에서 개선되었고, horizon 입력형 단일 모델 구조도 유지한다. 현재 서비스 후보는 ver16으로 보는 것이 맞다.
