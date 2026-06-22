# ver12c Recent-3 Residual Refresh Policy

## 목적

ver12b는 horizon별 최근 residual 보정을 쓰지만, source window는 valid 5개월 전체였다. 이전 안정성 검증에서 test 월이 뒤로 갈수록 개선폭이 줄어드는 패턴이 확인됐기 때문에, 더 최근 residual을 쓰는 refresh policy를 비교했다.

## 비교 방법

test label은 offset 생성에 사용하지 않았다. horizon별 valid 구간에서 최근 `1/2/3/4/5`개월 residual만 사용해 `complex_id + horizon_months` offset을 만들고, 동일한 test 구간 전체에 고정 적용했다.

- 기반 모델: ver9b LightGBM multi-horizon
- 보정 그룹: `complex_id + horizon_months`
- shrinkage: `10.0`
- min rows: `5`
- 비교 산출물: `streamlit/ml_model/outputs/calibration/ver12b_residual_refresh_policy_comparison.json`

## 결과

| 정책 | Source rows | Offset count | MAE | RMSE | R2 | Spearman | P80 abs error | P90 abs error |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| base ver9b | - | - | 8.2285 | 12.1852 | 0.3662 | 0.6695 | 13.1196 | 20.3667 |
| last 5 valid months, ver12b | 262,890 | 12,805 | 6.7041 | 10.1303 | 0.5620 | 0.7998 | 11.1308 | 16.9984 |
| last 4 valid months | 210,319 | 11,855 | 6.5254 | 9.8675 | 0.5844 | 0.8043 | 10.6985 | 16.4548 |
| last 3 valid months, ver12c | 158,659 | 11,811 | 6.4437 | 9.7261 | 0.5962 | 0.8060 | 10.4476 | 16.1566 |
| last 2 valid months | 106,334 | 9,625 | 6.5948 | 9.8972 | 0.5819 | 0.7914 | 10.5130 | 16.3235 |
| last 1 valid month | 53,265 | 4,152 | 7.2771 | 10.7116 | 0.5102 | 0.7363 | 11.3035 | 17.4084 |

최근 3개월 정책이 전체 MAE와 P80/P90 기준에서 가장 좋았다. 최근 1개월은 표본 부족으로 성능이 크게 나빠졌고, 5개월은 안정적이지만 stale residual이 섞이는 것으로 보인다.

## Service 반영

- `streamlit/modules/ml_predictor.py`
  - service model version: `ver12c_ver9b_plus_recent3_horizon_complex_residual`
  - offset file: `ver12c_recent3_horizon_complex_residual_offsets.csv`
  - P80/P90 interval을 ver12c horizon별 error profile로 갱신
- 60m는 계속 검증 가능한 test window가 없으므로 global fallback과 low confidence를 유지한다.

## 재현 명령어

정책 비교:

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\compare_residual_refresh_policies.py
```

ver12c offset 생성:

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\build_horizon_complex_residual_calibration.py --source-months 3 --shrinkage 10 --min-rows 5 --output C:\Users\User\Desktop\final\streamlit\ml_model\outputs\calibration\ver12c_recent3_horizon_complex_residual_offsets.csv --metrics-output C:\Users\User\Desktop\final\streamlit\ml_model\outputs\calibration\ver12c_recent3_horizon_complex_residual_metrics.json
```

서비스 스모크 테스트:

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py
```

## 판단

서비스 후보를 ver12b에서 ver12c로 갱신한다. ver12c는 shrinkage와 min rows를 보수형 `10/5`로 유지하면서 source window만 최근 3개월로 줄인 정책이다. 이는 성능 개선과 residual stale 현상 완화라는 두 근거를 모두 가진다.

단, source window 길이도 test 결과로 비교한 선택이라는 점은 남는다. 다음 데이터가 들어오면 `last_3_valid_months` 정책이 유지되는지 가장 먼저 재검증해야 한다. 더 공격적인 shrinkage 3 조합은 test grid 상으로 더 좋지만 과최적화 위험이 커서 서비스 후보로 채택하지 않는다.
