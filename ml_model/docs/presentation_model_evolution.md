# 모델 개선 과정 발표 정리

## 발표 핵심 메시지

이 프로젝트의 모델링 목표는 "서울 아파트 단지/평형별로 12/24/36/60개월 뒤 KB 매매시세 상승률을 예측하는 것"이다. 단순히 상승 가능성이 높은 후보를 랭킹하는 것이 아니라, 사용자가 클릭한 특정 단지와 평형에 대해 숫자 예측을 제공해야 하므로 최종 평가지표는 개별 row 단위의 오차, 특히 MAE와 큰 오차 구간(P80/P90)을 중심으로 보았다.

최종 후보는 `ver16_hierarchical_apt_size_residual`이다. 하나의 LightGBM 모델에 `horizon_months`를 입력해 여러 기간을 예측하고, 그 위에 단지-평형-horizon 단위 residual을 계층적으로 보정한다.

## 문제 정의가 바뀐 과정

처음에는 1년 뒤 상승률만 예측하는 단순 문제로 시작했다. 그러나 실제 서비스에서는 사용자가 1년, 3년, 5년처럼 다른 기간을 보고 싶어 한다. 모델을 기간별로 따로 만들면 구조는 단순하지만, 데이터가 horizon별로 쪼개지고 운영 코드도 복잡해진다. 그래서 `ver2` 이후에는 `horizon_months`를 feature로 넣어 하나의 모델에서 여러 기간을 예측하는 방향을 유지했다.

이 선택은 최종 `ver16`까지 이어진다. 60개월은 아직 충분한 test window가 없어 신뢰도는 낮게 표시하지만, 같은 인터페이스에서 예측값은 반환할 수 있게 했다.

## 버전별 의사결정 흐름

| 단계 | 핵심 질문 | 주요 버전 | 판단 |
|---|---|---|---|
| baseline | 구 단위/1년 상승률만으로 충분한가? | ver1 | MAE 9.4061, Spearman 0.0682로 개별 단지 예측에는 부족 |
| multi-horizon | 기간을 모델 입력으로 넣을 수 있는가? | ver2 | 구조는 서비스 목적에 맞지만 성능 개선은 제한적 |
| 입지 feature | 역/학교/병원 접근성이 도움이 되는가? | ver3 | 성능 개선은 작지만 설명 가능한 feature로 유지할 가치 있음 |
| label/feature 변환 | 로그수익률, lag, rolling feature가 더 좋은가? | ver4 | 대체로 과적합 또는 성능 악화. 복잡한 시계열 파생은 제한 |
| split 조정 | train/test 9:1이 더 나은가? | ver5 | 수치는 좋아졌지만 검증 구조가 약해 최종 후보로 보지 않음 |
| 개별 단지 12개월 | 단기 예측 전용 모델을 강화하면? | ver6~ver8 | ver7d가 12개월 MAE 7.1215까지 개선. 하지만 기간별 범용성 부족 |
| single multi-horizon 확정 | 하나의 모델로 12/24/36/48/60개월을 처리할 수 있는가? | ver9~ver10 | ver9b가 최종 base model 역할. ver10 변형은 악화 |
| residual 보정 | 개별 단지 오차 패턴을 후처리로 줄일 수 있는가? | ver11~ver12d | MAE 8.2285 -> 6.4376으로 개선 |
| 평형 단위 보정 | 같은 단지 안에서도 평형별 오차가 다른가? | ver13 | MAE 5.4754로 크게 개선 |
| blend 검증 | test 성능이 더 좋은 blend를 써도 되는가? | ver14~ver15 | ver14는 test 개선, 하지만 holdout 안정성 실패. ver15에서 복귀 |
| 계층형 shrinkage | 평형 residual을 더 안정적으로 보정할 수 있는가? | ver16 | test와 validation holdout 모두 개선. 최종 채택 |

## 피쳐 선택 논리

최종 base model인 `ver9b`는 다음 feature set을 사용한다.

| feature set | 사용 이유 |
|---|---|
| `horizon` | 하나의 모델로 12/24/36/48/60개월 예측을 하기 위한 핵심 feature |
| `kb_market` | 현재 매매시세, 전세시세, 전세가율, 시세갭은 가격 수준과 수요/부담을 직접 반영 |
| `apartment_meta` | 구, 좌표, 세대수, 준공월, 면적, 용적률, 건폐율 등은 단지의 구조적 특성 |
| `poi_accessibility` | 역/학교/병원 접근성은 부동산 가치 설명에 자연스러운 입지 변수 |
| `individual_stability_without_actual_tx` | 연식, 평당가, 단지 내 순위, 구 대비 프리미엄 등 서비스 시점에 안정적으로 계산 가능한 파생 변수 |

실거래 평균/거래량 계열은 최종 후보에서 제외했다. 이유는 성능만의 문제가 아니라 서비스 안정성 때문이다. 실거래 데이터는 단지/평형별로 결측과 지연이 생기기 쉽고, inference 시점에 항상 같은 품질로 입력된다고 보장하기 어렵다. 발표에서는 "최고 성능만 추구한 것이 아니라, 서비스 시점에 재현 가능한 feature를 우선했다"고 설명하면 된다.

## 주요 성능 개선 경로

| 채택 버전 | 핵심 변경 | Test MAE | 누적 개선 해석 |
|---|---|---:|---|
| ver9b | single multi-horizon base | 8.2285 | 최종 구조의 기준점 |
| ver11 | complex residual 보정 | 6.8216 | 단지별 오차 패턴이 남아 있음을 확인 |
| ver12d | horizon/구/면적 fallback 추가 | 6.4376 | exact residual이 없는 단지도 보수적으로 보정 |
| ver13 | apt-size + horizon residual | 5.4754 | 같은 단지 안 평형별 오차 차이를 반영 |
| ver16 | hierarchical apt-size shrinkage | 5.0376 | residual을 0이 아니라 fallback prior로 수축해 안정화 |

`ver9b`에서 `ver16`까지 채택 경로 기준 MAE는 8.2285에서 5.0376으로 줄었다. 이는 약 38.8% 개선이다.

## 왜 ver9b가 base model인가

`ver7d`는 12개월 전용으로는 강했다. 하지만 서비스는 1년/3년/5년을 하나의 방식으로 제공해야 한다. 기간별 모델을 따로 만들면 12개월 성능은 약간 좋아질 수 있지만, 24/36/60개월까지 동일한 운영 구조로 다루기 어렵다.

`ver9b`는 `horizon_months`를 feature로 넣는 single multi-horizon 구조를 확정했고, 이후 모든 개선은 이 구조 위에서 이루어졌다. 따라서 base model로는 `ver9b`가 가장 일관성 있는 선택이다.

## 왜 residual 보정이 의미 있었는가

LightGBM base model은 전체 데이터의 평균적인 패턴을 잘 잡는다. 그러나 특정 단지나 평형은 지속적으로 과대평가 또는 과소평가되는 경향이 남을 수 있다. 예를 들어 어떤 단지는 항상 주변 평균보다 프리미엄이 유지되고, 어떤 평형은 같은 단지 안에서도 더 강하거나 약할 수 있다.

`ver11` 이후의 residual 보정은 이 남은 오차 패턴을 validation 기간에서 추정해 다음 test 기간에 적용하는 방식이다. 단순히 test set을 맞춘 것이 아니라, valid residual을 사용해 test를 개선했기 때문에 "최근 오차 패턴이 단기적으로 지속된다"는 가설이 실험적으로 확인된 것이다.

## ver14를 버린 이유

`ver14`는 test MAE 5.3811로 `ver13`보다 좋아 보였다. 하지만 blend alpha 0.7은 test grid에서 선택됐다. 이 경우 test set에 맞춘 의사결정일 위험이 있다.

그래서 `ver15`에서 validation rolling holdout으로 alpha 안정성을 검증했다. 결과적으로 모든 holdout window에서 alpha 1.0, 즉 `ver13` 방식 단독이 가장 안정적이었다. 따라서 test 성능만 보면 ver14가 좋아도, 서비스 후보로는 채택하지 않았다. 이 판단은 발표에서 중요한 포인트다. "성능이 좋아 보이는 모델을 무조건 채택하지 않고, 검증 안정성을 우선했다"는 근거가 된다.

## ver16의 최종 개선 논리

`ver13/ver15`는 단지-평형-horizon residual 평균을 0 방향으로 shrinkage했다. 하지만 residual 보정값이 부족한 경우 0으로 수축하는 것보다, 더 넓은 계층의 fallback 보정값으로 수축하는 것이 자연스럽다.

`ver16`은 이 아이디어를 적용했다.

```text
residual_offset = prior_mean + weight * (raw_mean - prior_mean)
weight = valid_rows / (valid_rows + shrinkage)
```

여기서 `prior_mean`은 `complex_id+horizon`, `group_gu_area`, `horizon_global`, `global` 순서의 fallback 보정값이다. 즉 데이터가 충분하면 해당 평형의 residual을 많이 반영하고, 데이터가 적으면 더 넓은 집단의 residual 쪽으로 부드럽게 수축한다.

이 방식은 test 성능과 validation rolling holdout 모두에서 개선됐다.

| 지표 | ver15 | ver16 |
|---|---:|---:|
| Test MAE | 5.4754 | 5.0376 |
| Test RMSE | 8.6560 | 8.1711 |
| Test R2 | 0.6802 | 0.7150 |
| Spearman | 0.8573 | 0.8715 |
| P90 absolute error | 14.5367 | 13.6911 |

## 최종 모델의 한계

1. 60개월은 inference는 가능하지만 test window가 충분하지 않아 low confidence로 표시한다.
2. residual 보정은 최근 valid 기간의 오차 패턴이 일정 기간 유지된다는 가정이 있다.
3. 외부 거시경제, 금리, 정책 변화는 현재 feature에 직접 들어가 있지 않다.
4. 예측값은 금융 의사결정의 확정값이 아니라, 후보 비교와 리스크 점검을 위한 참고값이다.

## 발표용 결론

모델 개선은 단순히 feature를 많이 넣거나 더 복잡한 모델을 쓰는 방향이 아니었다. 서비스 목적에 맞게 "한 모델로 여러 기간을 예측한다"는 구조를 먼저 확정했고, 그 뒤 개별 단지/평형에서 반복적으로 남는 오차를 residual calibration으로 줄였다.

최종 `ver16`은 성능, 운영 일관성, 설명가능성의 균형이 가장 좋다. 특히 `ver14`처럼 test 성능만 좋은 후보를 보류하고 holdout 안정성을 통과한 방식만 채택했다는 점에서, 발표 시 모델 선택의 신뢰성을 강조할 수 있다.

## 근거 문서

- `streamlit/ml_model/docs/model_version_performance_summary.md`
- `streamlit/ml_model/outputs/performance/VERSION_LOG.md`
- `streamlit/ml_model/outputs/performance/ver06222256_ver16_hierarchical_apt_size_shrinkage.md`
- `streamlit/ml_model/outputs/performance/ver06222244_ver15_alpha_stability.md`
- `streamlit/ml_model/config/config.yaml`
- `streamlit/ml_model/config/config_ver9b_multihorizon_calibrated.yaml`
