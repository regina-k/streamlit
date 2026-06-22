# ver12c Service Offset Coverage

## 목적

서비스에서는 사용자가 최신 단지/평형을 클릭한다. 따라서 ver12c가 학습/test 성능뿐 아니라 실제 최신 feature store의 클릭 대상에 얼마나 자주 `complex_id+horizon` 보정을 적용할 수 있는지 확인해야 한다.

## 분석 대상

- feature store: `data/integration/apartment_multihorizon_ver9_latest_features.csv`
- offset file: `streamlit/ml_model/outputs/calibration/ver12c_recent3_horizon_complex_residual_offsets.csv`
- base date: `2025-06-01`
- latest rows: `16,679`
- latest complexes: `4,275`
- horizons: `12/24/36/60`

재현 스크립트:

- `scripts/analyze_service_offset_coverage.py`
- output: `streamlit/ml_model/outputs/calibration/ver12c_service_offset_coverage.json`

## Coverage

| Horizon | Fallback type | Rows | Row rate | Complexes | Complex rate |
|---:|---|---:|---:|---:|---:|
| 12m | complex_id+horizon | 15,644 | 93.79% | 3,665 | 85.73% |
| 12m | horizon_global | 1,035 | 6.21% | 610 | 14.27% |
| 24m | complex_id+horizon | 11,988 | 71.87% | 2,693 | 62.99% |
| 24m | horizon_global | 4,691 | 28.13% | 1,582 | 37.01% |
| 36m | complex_id+horizon | 11,990 | 71.89% | 2,694 | 63.02% |
| 36m | horizon_global | 4,689 | 28.11% | 1,581 | 36.98% |
| 60m | global | 16,679 | 100.00% | 4,275 | 100.00% |

## Complex-Level Summary

| Exact calibrated horizons per complex | Complex count |
|---:|---:|
| 0 | 609 |
| 1 | 973 |
| 3 | 2,693 |

해석:

- 최신 단지 중 `2,693`개는 12/24/36개월 모두 `complex_id+horizon` 보정이 가능하다.
- `973`개는 12개월만 단지별 보정이 가능하고, 24/36개월은 horizon fallback을 사용한다.
- `609`개는 12/24/36개월 모두 horizon fallback을 사용한다.
- 60개월은 검증 가능한 test window가 없어 항상 global fallback이다.

## 판단

현재 UI/서비스 정책과 일치한다.

- `horizon_global` fallback은 `confidence=low`로 표시한다.
- 60m는 global fallback과 low confidence를 유지한다.
- 화면 caption에는 horizon별 fallback type, valid rows, source window가 표시된다.

추가 성능 개선 관점에서는 fallback 단지 609개와 24/36개월 fallback 비율을 줄이는 것이 다음 과제다. 다만 이것은 단순 calibration보다 더 과거 라벨 또는 추가 feature coverage를 늘리는 데이터 문제에 가깝다.

## 검증 명령어

```powershell
python -m py_compile C:\Users\User\Desktop\final\scripts\analyze_service_offset_coverage.py
```

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\analyze_service_offset_coverage.py
```
