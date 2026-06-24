# ver06212238_ver6_individual_prediction_study

## 1. 실험 목적

서비스 목표는 사용자가 클릭한 개별 단지/평형의 예측 상승률을 보여주는 것이다. 따라서 ver6는 랭킹 성능보다 개별 예측 오차, 특히 MAE/RMSE 개선을 우선으로 평가했다.

핵심 질문:

- 같은 마지막 5개월 test window에서 ver5a 개선이 유지되는가?
- multi-horizon 통합 모델보다 12개월 전용 모델이 개별 1년 상승률 예측에 유리한가?
- `target_return_pct`, `target_log_return_pct`, `future_log_price` 중 어떤 타깃이 상승률 MAE를 줄이는가?

## 2. 공통 설정

- Test window: `2025-02-01` ~ `2025-06-01`
- Valid window: `2024-09-01` ~ `2025-01-01`
- Train window: `2024-08-01` 이하
- 모델: LightGBM Regressor, 기존 300 trees 설정 유지
- 입지 피쳐: ver3의 역/학교/병원 POI 피쳐 유지
- 평가 metric: 예측값을 모두 `target_return_pct` 단위로 맞춘 뒤 계산

## 3. 데이터 및 Config

| Variant | Config | 데이터 | 목적 |
|---|---|---|---|
| ver6a | `config_ver6a.yaml` | `apartment_multihorizon_poi.csv` | 같은 test window의 multi-horizon 기준선 |
| ver6b | `config_ver6b.yaml` | `apartment_multihorizon_ver6_individual.csv` | 12개월 전용, 상승률 직접 예측 |
| ver6c | `config_ver6c.yaml` | `apartment_multihorizon_ver6_individual.csv` | 12개월 전용, 로그수익률 학습 후 상승률 복원 |
| ver6d | `config_ver6d.yaml` | `apartment_multihorizon_ver6_individual.csv` | 12개월 전용, 미래 로그가격 학습 후 상승률 복원 |
| ver6e-l1 | `config_ver6e_l1.yaml` | `apartment_multihorizon_ver6_individual.csv` | ver6b 구조에서 LightGBM `regression_l1` objective 비교 |
| ver6e-huber | `config_ver6e_huber.yaml` | `apartment_multihorizon_ver6_individual.csv` | ver6b 구조에서 LightGBM `huber` objective 비교 |
| ver6f | `config_ver6f.yaml` | `apartment_12m_ver6f_stability_features.csv` | ver6b + 개별 안정 피쳐 추가 |
| ver6g | `config_ver6g.yaml` | `apartment_12m_ver6f_stability_features.csv` | ver6f 피쳐 유지, train+valid를 합친 9:1 최종 후보 |
| ver6h | `config_ver6h_earlystop.yaml` | `apartment_12m_ver6f_stability_features.csv` | ver6f 피쳐 유지, 2000 trees + 낮은 learning rate + valid early stopping |
| ver6i | `config_ver6i.yaml` | `apartment_12m_ver6f_stability_features.csv` | ver6h 설정을 train+valid 합친 9:1 배포 후보로 확장 |
| ver6j | `config_ver6j_no_actual_tx.yaml` | `apartment_12m_ver6f_stability_features.csv` | ver6h 구조에서 실거래 평균/거래량 계열 피쳐 제거 |
| ver6k | `config_ver6k_no_actual_tx_train_test.yaml` | `apartment_12m_ver6f_stability_features.csv` | ver6j 피쳐를 train+valid 합친 9:1 배포 후보로 확장 |

`apartment_multihorizon_ver6_individual.csv`는 `apartment_multihorizon_poi.csv`에 아래 컬럼을 추가한 파일이다.

| 컬럼 | 의미 |
|---|---|
| `target_log_return_pct` | `log(future_sale_price_manwon / kb_sale_price_manwon) * 100` |
| `future_log_price` | `log(future_sale_price_manwon)` |

## 4. Split 규모

| Variant | Train rows | Valid rows | Test rows | Test horizon |
|---|---:|---:|---:|---|
| ver6a | 1,793,592 | 113,636 | 119,707 | 12 |
| ver6b | 612,069 | 113,636 | 119,707 | 12 |
| ver6c | 612,069 | 113,636 | 119,707 | 12 |
| ver6d | 612,069 | 113,636 | 119,707 | 12 |
| ver6e-l1 | 612,069 | 113,636 | 119,707 | 12 |
| ver6e-huber | 612,069 | 113,636 | 119,707 | 12 |
| ver6f | 612,069 | 113,636 | 119,707 | 12 |
| ver6g | 725,705 | 0 | 119,707 | 12 |
| ver6h | 612,069 | 113,636 | 119,707 | 12 |
| ver6i | 725,705 | 0 | 119,707 | 12 |
| ver6j | 612,069 | 113,636 | 119,707 | 12 |
| ver6k | 725,705 | 0 | 119,707 | 12 |

## 5. 성능

| Variant | Train MAE | Valid MAE | Test MAE | Test RMSE | Test R2 | Test MAPE | Test Spearman |
|---|---:|---:|---:|---:|---:|---:|---:|
| ver5a 참고 | 5.3853 | 없음 | 8.3319 | 12.0146 | -0.1829 | 126.4563 | 0.3576 |
| ver6a | 5.2803 | 6.8423 | 9.1334 | 13.0370 | -0.3928 | 120.9517 | 0.2461 |
| ver6b | 3.7530 | 6.8541 | 9.0327 | 13.0365 | -0.3927 | 130.4867 | 0.2144 |
| ver6c | 3.7435 | 6.9203 | 9.1304 | 13.1667 | -0.4207 | 123.7182 | 0.2138 |
| ver6d | 3.8362 | 7.5924 | 9.6852 | 13.5023 | -0.4940 | 174.2784 | 0.1020 |
| ver6e-l1 | 3.9445 | 7.2567 | 9.5052 | 13.5193 | -0.4978 | 100.4414 | 0.3391 |
| ver6e-huber | 4.3866 | 7.5059 | 9.7521 | 13.7643 | -0.5526 | 99.8465 | 0.3572 |
| ver6f | 3.1479 | 5.9959 | 8.2980 | 11.9374 | -0.1678 | 112.9886 | 0.4218 |
| ver6g | 3.4073 | 없음 | 6.6786 | 9.6969 | 0.2294 | 114.5984 | 0.6041 |
| ver6h | 2.2826 | 5.3964 | 7.7777 | 11.2727 | -0.0414 | 123.1825 | 0.4530 |
| ver6i | 2.5457 | 없음 | 6.0475 | 8.7856 | 0.3675 | 105.9414 | 0.6872 |
| ver6j | 2.1807 | 5.3197 | 7.7040 | 11.1904 | -0.0262 | 127.8385 | 0.4212 |
| ver6k | 2.5024 | 없음 | 6.0465 | 8.8701 | 0.3552 | 105.0970 | 0.6930 |

## 6. 해석

- 같은 마지막 5개월 test window에서 valid를 유지하면 ver6a MAE는 9.1334다. ver5a의 8.3319는 validation 구간을 train에 포함한 효과가 크다고 보는 것이 안전하다.
- 개별 12개월 예측에서는 12개월 전용 direct return 모델인 ver6b가 가장 낮은 Test MAE 9.0327을 기록했다.
- 로그수익률 라벨(ver6c)은 MAPE는 낮아졌지만 MAE/RMSE 기준으로는 direct return보다 좋지 않았다.
- 미래 로그가격 예측(ver6d)은 기대와 달리 가장 나빴다. 현재 피쳐 구성에서는 가격 레벨 예측 후 상승률 환산이 오차를 줄이지 못한다.
- `regression_l1`과 `huber` objective는 MAPE와 Spearman은 개선했지만 MAE/RMSE는 악화됐다. 개별 상승률 값을 정확히 보여주는 서비스 목적에서는 현재 `regression` objective가 더 낫다.
- ver6f의 안정 피쳐는 Test MAE를 9.0327에서 8.2980으로 줄였다. 같은 validation 구조에서 좋아졌으므로 피쳐 자체의 개선 효과로 볼 근거가 있다.
- ver6f의 상위 중요 피쳐에는 `building_age_years`, `sale_price_per_exclusive_pyeong`, `actual_sale_to_kb_gap_pct`, `total_tx_count_sum_12m`, `complex_sale_price_premium_pct` 등이 포함됐다. 연식, 평당가, 실거래 괴리, 거래 안정성이라는 설계 의도가 실제 모델에서 사용됐다.
- ver6g는 ver6f를 모델 선택 결과로 본 뒤 train+valid를 함께 학습한 배포 후보이다. Test MAE 6.6786, RMSE 9.6969, R2 0.2294로 가장 좋다. 다만 valid set이 없으므로 이후 하이퍼파라미터 선택에는 이 결과를 반복 사용하면 안 된다.
- ver6h는 validation을 유지한 모델 중 가장 좋다. Test MAE 7.7777이며 valid MAE도 5.3964로 ver6f보다 낮다. 다만 early stopping은 2000라운드까지 멈추지 않았으므로, 개선은 주로 `n_estimators` 증가와 낮은 `learning_rate` 효과로 해석한다.
- ver6i는 ver6h 설정을 train+valid 통합 학습에 적용한 배포 후보이다. Test MAE 6.0475, RMSE 8.7856, R2 0.3675로 현재 전체 실험 중 가장 좋다. 단, validation이 없으므로 모델 선택용이 아니라 배포 후보 성능 확인용으로만 해석한다.
- ver6j는 실거래 평균/거래량 계열 피쳐를 제거했는데도 valid MAE 5.3197, test MAE 7.7040으로 ver6h보다 소폭 좋았다. 실거래 피쳐는 입력 부담이 큰 반면 현재 검증 구조에서는 필수 개선 요인이 아니다.
- ver6k는 실거래 피쳐 없이 train+valid를 합친 배포 후보이다. Test MAE 6.0465로 ver6i와 사실상 같고, Spearman은 0.6930으로 더 높다. RMSE/R2는 ver6i가 약간 낫지만, 서비스 inference 안정성까지 고려하면 ver6k가 더 실용적인 후보이다.

## 7. 판단

현재 “검증을 유지하는 보수적 기준”에서는 ver6j가 개별 12개월 상승률 예측의 최선이다. 최종 배포 후보 관점에서는 ver6i와 ver6k가 거의 동률이며, 서비스 입력 안정성까지 고려하면 실거래 피쳐가 필요 없는 ver6k를 우선 후보로 본다. ver6k는 MAE 6.0465%p까지 내려왔지만, 사용자에게 단일 확정값처럼 보여주기보다는 예측 상승률과 함께 오차 범위 또는 신뢰도 표시를 제공하는 방향이 안전하다.

## 8. 다음 실험

- ver6l: ver6k를 서비스 inference 파이프라인에 연결할 수 있도록 현재월 feature 생성 함수를 정리한다.
- ver6m: 예측값과 함께 표시할 신뢰도/오차 범위 산출 방식을 설계한다.
- ver6n: 실거래 피쳐 없는 ver6k에서 단지 내 상대 피쳐 또는 구 상대 피쳐를 추가 제거하는 ablation을 수행한다.
