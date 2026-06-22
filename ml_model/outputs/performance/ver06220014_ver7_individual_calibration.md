# ver06220014_ver7_individual_calibration

## 목적

서비스 목표는 사용자가 클릭한 개별 단지/평형의 12개월 뒤 상승률을 숫자로 보여주는 것이다. 따라서 ver7은 랭킹 성능보다 개별 예측 오차를 줄이는 것을 우선했다. 핵심 평가지표는 MAE, RMSE, Bias이며 Spearman은 보조지표로만 본다.

## 공통 조건

- 예측 단위: 단지ID + 면적일련번호의 12개월 뒤 상승률
- Test window: 2025-02-01 ~ 2025-06-01
- Valid window: 2024-09-01 ~ 2025-01-01
- 기준 모델: ver6j와 동일한 LightGBM 2000 trees, learning_rate 0.03
- 실무 제약: 현재 클릭 시점에 안정적으로 알기 어려운 실거래 평균/거래량 계열은 제외

## 실험별 변경

| Variant | Config | 데이터 | 변경 내용 |
|---|---|---|---|
| ver7a | `config_ver7a_kb_history.yaml` | `data/integration/apartment_12m_ver7_kb_history_features.csv` | KB 매매/전세 시세의 lag, rolling, 구 대비 momentum feature 추가 |
| ver7b | `config_ver7b_valid_bias_calibrated.yaml` | `data/integration/apartment_12m_ver6f_stability_features.csv` | ver6j feature 유지, valid 평균잔차를 전체 예측값에 더함 |
| ver7c | `config_ver7c_gu_calibrated.yaml` | `data/integration/apartment_12m_ver6f_stability_features.csv` | valid 잔차 평균을 구별로 계산해 보정 |
| ver7d | `config_ver7d_gu_price_calibrated.yaml` | `data/integration/apartment_12m_ver6f_stability_features.csv` | 구 + KB매매가격 4분위별 잔차 보정, shrinkage 500 적용 |

## 성능

| Variant | Train MAE | Valid MAE | Test MAE | Test RMSE | Test R2 | Test MAPE | Test Spearman | Test Bias |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ver6j 기준 | 2.1807 | 5.3197 | 7.7040 | 11.1904 | -0.0262 | 127.8385 | 0.4212 | -4.1127 |
| ver7a | 3.3707 | 6.5973 | 9.2235 | 13.2227 | -0.4328 | 119.4675 | 0.2471 | -7.3616 |
| ver7b | 2.7075 | 5.4760 | 7.4752 | 10.6972 | 0.0622 | 146.2614 | 0.4212 | -2.4738 |
| ver7c | 3.3691 | 5.1452 | 7.2876 | 10.3590 | 0.1206 | 142.6060 | 0.4989 | -2.4459 |
| ver7d | 3.3877 | 4.9931 | 7.1215 | 10.2786 | 0.1342 | 135.7039 | 0.5260 | -2.4524 |

## 판단

ver7a는 실패다. KB 히스토리 feature를 추가했지만 valid/test MAE가 모두 악화됐고, 특히 test bias가 -7.3616%p로 커졌다. 현재 상승 구간에서 과거 momentum feature가 오히려 보수적인 예측을 강화한 것으로 본다.

ver7b~ver7d는 모델 자체를 바꾸지 않고 validation 잔차로 예측값을 보정한 실험이다. 전체 평균 보정보다 구별 보정이 낫고, 구 + 가격분위 보정이 가장 좋았다. ver7d는 ver6j 대비 test MAE를 7.7040에서 7.1215로 낮췄고 RMSE도 11.1904에서 10.2786으로 낮췄다. R2도 음수에서 0.1342로 개선됐다.

현재 검증셋을 유지한 모델 선택 기준으로는 ver7d가 최선이다. 다만 train+valid를 합친 배포 후보였던 ver6k의 test MAE 6.0465와는 직접 비교하면 안 된다. ver6k는 validation 없이 더 긴 학습기간을 사용한 배포 후보이고, ver7d는 모델 선택을 위한 validation 유지 실험이다.

## 취약 구간

ver7d test 기준 MAE가 큰 구는 다음과 같다.

| 구 | Rows | Test MAE | Test Bias |
|---|---:|---:|---:|
| 송파구 | 1,257 | 16.167 | -13.511 |
| 성동구 | 1,385 | 12.318 | -2.049 |
| 동작구 | 4,573 | 9.440 | -4.446 |
| 강동구 | 13,364 | 9.146 | -3.900 |
| 강남구 | 544 | 8.377 | -2.995 |

송파구는 보정 후에도 강한 과소예측이 남아 있어 별도 점검이 필요하다. 단순한 전체 보정보다는 특정 지역/가격대/시장국면에 대한 feature나 calibration이 추가로 필요하다.

## 재현 명령어

```powershell
python .\scripts\build_ver7_features.py

$env:PYTHONPATH='C:\Users\User\Desktop\final\streamlit\ml_model\src'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver7a_kb_history.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver7b_valid_bias_calibrated.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver7c_gu_calibrated.yaml'
& 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -m ml_project.train --config 'C:\Users\User\Desktop\final\streamlit\ml_model\config\config_ver7d_gu_price_calibrated.yaml'
```

## 산출물

- ver7a model: `outputs/models/apartment_return_lightgbm_ver7a_12m_kb_history_target_return_pct_20260621_235107.pkl`
- ver7b model: `outputs/models/apartment_return_lightgbm_ver7b_valid_bias_calibrated_target_return_pct_20260621_235855.pkl`
- ver7c model: `outputs/models/apartment_return_lightgbm_ver7c_gu_calibrated_target_return_pct_20260622_000659.pkl`
- ver7d model: `outputs/models/apartment_return_lightgbm_ver7d_gu_price_calibrated_target_return_pct_20260622_001315.pkl`
- ver7d metrics: `outputs/metrics_target_return_pct_20260622_001315.json`

## 다음 실험

- ver7e: 송파구/성동구처럼 과소예측이 큰 구간의 공통 feature를 점검한다.
- ver7f: prediction interval을 만든다. 단일 상승률만 보여주기보다 `예상 상승률 ± 최근 test MAE 기반 오차범위`를 함께 제공하는 것이 서비스상 안전하다.
- ver8: 검증 유지 기준에서 선택된 ver7d 구조를 train+valid 9:1 배포 후보로 확장하되, test를 반복 튜닝에 쓰지 않도록 별도 holdout 원칙을 문서화한다.
