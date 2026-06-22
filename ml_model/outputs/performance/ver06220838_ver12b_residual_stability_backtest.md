# ver12b Residual Stability Backtest

## 목적

ver12b의 성능 개선이 마지막 test 구간에만 우연히 맞은 것인지 확인했다. 서비스 목표는 사용자가 클릭한 개별 단지의 예측 상승률을 잘 맞히는 것이므로, 평균 성능뿐 아니라 residual 보정이 시간에 따라 유지되는지가 중요하다.

## 검증 1: Rolling Residual Backtest

각 horizon별 test 월을 평가할 때 같은 horizon의 직전 5개월 residual만 사용해 `complex_id` offset을 다시 계산했다.

- lookback months: `5`
- shrinkage: `10.0`
- min rows: `5`
- folds: `20`개
- 비교 대상: base ver9b, rolling global residual, rolling complex+horizon residual

| 방법 | MAE | RMSE | R2 | Spearman | P80 abs error | P90 abs error |
|---|---:|---:|---:|---:|---:|---:|
| base ver9b | 8.2285 | 12.1852 | 0.3662 | 0.6695 | 13.1196 | 20.3667 |
| rolling global residual | 8.0265 | 11.4833 | 0.4371 | 0.6789 | 12.3800 | 18.8356 |
| rolling complex+horizon residual | 5.4320 | 8.0684 | 0.7221 | 0.8673 | 8.7154 | 13.3012 |

### 해석 제한

rolling 결과는 residual 패턴이 강하게 지속된다는 증거이지만, 그대로 실시간 서비스 성능으로 해석하면 안 된다. 12/24/36/48개월 라벨은 해당 horizon이 지나야 알 수 있으므로, test 구간 안의 직전 월 residual을 다음 월 보정에 쓰는 것은 실서비스 시점에서는 즉시 가능하지 않다. 따라서 이 검증은 운영 가능한 검증이라기보다 residual 보정 가정의 시간 지속성 점검이다.

## 검증 2: Valid-Only Static Offset 월별 분해

서비스 후보인 ver12b offset은 valid 구간만 사용해 만든 뒤, test 구간 전체에 고정 적용된다. 이 방식은 미래 test residual을 사용하지 않는다.

모든 test 월/horizon에서 ver12b는 base ver9b보다 MAE를 낮췄다. 다만 test 월이 뒤로 갈수록 개선폭은 줄어드는 경향이 있었다.

| Horizon | 첫 test 월 개선폭 | 마지막 test 월 개선폭 |
|---:|---:|---:|
| 12m | -1.8914 | -0.9107 |
| 24m | -2.3572 | -1.7664 |
| 36m | -2.0557 | -1.2702 |
| 48m | -1.5235 | -0.8525 |

## 산출물

- `scripts/analyze_rolling_residual_backtest.py`
- `streamlit/ml_model/outputs/calibration/ver12b_rolling_residual_backtest.json`

## 재현 명령어

```powershell
python -m py_compile C:\Users\User\Desktop\final\scripts\analyze_rolling_residual_backtest.py
```

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\analyze_rolling_residual_backtest.py
```

## 판단

서비스 후보는 ver12b를 유지한다. rolling 결과는 residual 패턴이 시간적으로 지속된다는 강한 보조 근거를 준다. valid-only 월별 분해에서도 모든 월/horizon에서 base보다 개선됐다.

다만 개선폭이 시간이 지나며 줄어드는 패턴이 있으므로, 운영에서는 새 라벨이 확보될 때마다 residual offset을 주기적으로 재생성해야 한다. 다음 실험은 새 학습 모델보다 offset 갱신 정책, 예를 들어 최근 3개월/5개월/전체 valid window 중 어떤 방식이 가장 안정적인지 비교하는 것이 우선이다.
