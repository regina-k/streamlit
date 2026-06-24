# ver11 complex residual calibration

## 목적

서비스에서는 사용자가 클릭한 개별 단지의 상승률 예측이 중요하다. ver9b multi-horizon 모델은 전체 구조가 가장 균형적이지만, test bias와 개별 예측 절대오차가 여전히 컸다. ver11에서는 모델을 재학습하지 않고, ver9b의 valid 예측 residual을 단지별로 학습해 test 예측에 post-calibration으로 적용했다.

## 방법

- 기준 모델: ver9b
- valid prediction: `predictions_valid_target_return_pct_20260622_060733.csv`
- test prediction: `predictions_test_target_return_pct_20260622_060733.csv`
- 기준 예측 컬럼: `prediction_calibrated`
- 그룹: `complex_id`
- residual: `target_return_pct - prediction_calibrated`
- shrinkage: 20
- min_rows: 5
- offset 수: 4,134개 단지

단지별 residual offset은 다음 식으로 계산했다.

```text
offset = (complex_residual_mean * valid_rows + global_offset * shrinkage) / (valid_rows + shrinkage)
```

재현 명령어:

```powershell
python .\scripts\build_complex_residual_calibration.py
```

## 성능 비교

| 버전 | 설명 | Test MAE | Test RMSE | Test R2 | Test Spearman | Test Bias | P80 Abs Error | P90 Abs Error |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ver9b | horizon/gu/가격대 validation residual 보정 | 8.2285 | 12.1852 | 0.3662 | 0.6695 | -4.3574 | 13.1196 | 20.3667 |
| ver11 | ver9b + complex residual post-calibration | 6.8216 | 10.1909 | 0.5567 | 0.7948 | -4.3072 | 11.0954 | 16.9222 |

## Horizon별 Test 성능

| Horizon | MAE | RMSE | R2 | Spearman | Bias | P80 Abs Error | P90 Abs Error |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 | 6.4459 | 9.3877 | 0.2930 | 0.6347 | -2.7641 | 10.4979 | 15.4001 |
| 24 | 7.4250 | 11.0484 | 0.5192 | 0.8117 | -5.7573 | 12.3876 | 19.0488 |
| 36 | 8.0785 | 12.2137 | 0.5272 | 0.8345 | -6.8792 | 13.6865 | 21.3349 |
| 48 | 5.4695 | 7.8490 | 0.7612 | 0.8829 | -2.3745 | 8.7606 | 12.9880 |

## 판단

ver11은 현재까지 개별 단지 예측 관점에서 가장 강한 후보이다. 전체 MAE, RMSE, R2, Spearman, P80/P90 절대오차가 모두 ver9b보다 개선됐다. 특히 사용자가 클릭한 단지 하나에 보여줄 예측값의 체감 리스크인 P90 절대오차가 20.37%p에서 16.92%p로 줄었다.

다만 이 보정은 valid 기간에서 관측된 단지별 residual 패턴이 test 기간에도 일부 지속된다는 가정에 의존한다. 단지가 valid에 충분히 등장하지 않으면 global offset으로 fallback한다. 운영에서는 offset 적용 여부와 valid row 수를 함께 추적하는 것이 좋다.

## Residual Source 민감도

단지별 residual offset을 어느 기간에서 학습해야 하는지 확인했다. 같은 ver9b prediction을 기준으로 offset source를 바꿔 test 성능을 비교했다.

재현 명령어:

```powershell
python .\scripts\analyze_residual_calibration_sensitivity.py
```

산출물:

- `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver11_residual_source_sensitivity.json`

핵심 결과:

| Offset source | Shrinkage | Test MAE | Test RMSE | Test R2 | Test Bias | P80 Abs Error | P90 Abs Error |
|---|---:|---:|---:|---:|---:|---:|---:|
| none, ver9b baseline | - | 8.2285 | 12.1852 | 0.3662 | -4.3574 | 13.1196 | 20.3667 |
| train residual | 1000 | 9.7235 | 14.1668 | 0.1433 | -8.1977 | 16.2969 | 24.2636 |
| train+valid residual | 20 | 9.1203 | 13.5311 | 0.2185 | -7.4060 | 15.4988 | 23.2532 |
| valid residual | 20 | 6.8216 | 10.1909 | 0.5567 | -4.3072 | 11.0954 | 16.9222 |

해석:

- ver11 개선은 과거 전체 residual을 평균내는 효과가 아니라, 가장 최근 valid 구간의 단지별 residual이 다음 test 구간으로 이어지는 국소적 시간 적응 효과다.
- train residual은 현재 국면과 맞지 않아 baseline보다 악화된다.
- 따라서 서비스 offset은 train 또는 train+valid로 임의 변경하지 않는다.
- 운영에서는 최신 라벨이 확보될 때마다 최근 구간 기준으로 offset을 갱신하는 방식이 맞다.

## 서비스 반영

`streamlit/modules/ml_predictor.py`의 `predict_apartment_growth_horizons(...)`에 ver11 offset을 적용했다. 모델 자체는 ver9b artifact를 사용하고, 예측 후 `complex_id`별 residual offset을 더한다.

- offset 파일: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver11_complex_residual_offsets.csv`
- metrics 파일: `C:/Users/User/Desktop/final/streamlit/ml_model/outputs/calibration/ver11_complex_residual_metrics.json`
- service model version: `ver11_ver9b_plus_complex_residual`

60개월은 ver11 offset을 적용해 반환하지만, 60개월 test window가 없어 신뢰도는 계속 낮게 둔다.

## 운영 커버리지 점검

최신 service feature store `apartment_multihorizon_ver9_latest_features.csv` 기준으로 ver11 offset 적용 가능 범위를 확인했다.

- 최신 단지-평형 행: 16,679개
- 최신 unique complex: 4,275개
- offset 적용 가능 행: 16,149개
- row coverage: 96.82%
- offset 적용 가능 complex: 4,027개
- offset valid row 중앙값: 80개

coverage가 낮은 구도 대부분 92% 이상이었다.

| 구 | 최신 행 수 | offset coverage |
|---|---:|---:|
| 서초구 | 1,433 | 92.32% |
| 송파구 | 132 | 92.42% |
| 광진구 | 580 | 93.28% |
| 강동구 | 1,966 | 95.17% |
| 마포구 | 1,089 | 95.32% |

서비스 반환값에는 다음 메타를 추가했다.

- `residual_calibration.offset_applied`: 단지별 offset 적용 여부
- `residual_calibration.residual_offset`: 최종 적용 residual offset
- `residual_calibration.valid_rows`: 해당 단지 offset 계산에 사용된 valid row 수
- `residual_calibration.source_min_date`, `source_max_date`: offset을 계산한 residual source window
- `residual_calibration.test_min_date`, `test_max_date`: 성능 검증에 사용한 test window
- `residual_calibration.fallback`: `complex_id` 또는 `global`

`source_min_date`와 `source_max_date`는 horizon별 valid tail을 합친 전체 범위다. horizon마다 라벨 가능 기간이 다르기 때문에 전체 source window는 길게 보일 수 있다.

검증 예시:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\final\streamlit'
python -c "from modules.ml_predictor import predict_apartment_growth_horizons; r=predict_apartment_growth_horizons(complex_id=1,horizons=('12m','24m')); print(r['residual_calibration'])"
```

결과:

```text
{'offset_applied': True, 'residual_offset': 6.323282278672215, 'valid_rows': 80, 'source_min_date': '2021-09-01', 'source_max_date': '2025-01-01', 'test_min_date': '2022-02-01', 'test_max_date': '2025-06-01', 'fallback': 'complex_id'}
```

offset이 없는 단지는 global fallback으로 동작함을 확인했다.
