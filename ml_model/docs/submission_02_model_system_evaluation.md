# 제출파일 2. 아파트 상승률 예측 모델·시스템 및 평가 결과

## 1. 문제 정의

서울 아파트의 **단지·평형별 KB 매매시세 상승률**을 예측한다. 입력은 기준월의 단지·평형 정보와 예측기간(`horizon_months`)이며, 출력은 N개월 후 누적 상승률(%p)이다. 12/24/36/60개월마다 모델을 분리하지 않고 하나의 multi-horizon 회귀 모델을 사용한다.

최종 서비스 후보는 `ver16_hierarchical_apt_size_residual`이다.

## 2. 데이터와 전처리

학습 feature store는 `data/integration/apartment_multihorizon_ver9_stability_features.csv`이다.

| 항목 | 값 |
|---|---:|
| 전체 행 | 1,569,946 |
| 아파트 단지 | 4,527 |
| 단지·평형 ID | 18,894 |
| 자치구 | 21 |
| 기준월 범위 | 2021-06 ~ 2025-06 |
| horizon | 12, 24, 36, 48, 60개월 |

라벨은 다음과 같다.

```text
target_return_pct
= (미래 KB 매매시세 / 기준월 KB 매매시세 - 1) × 100
```

전처리 원칙은 다음과 같다.

- 라벨이 없는 행은 학습에서 제외한다.
- `gu`, `property_type`, `housing_type`은 범주형으로 처리한다.
- 20만 행 품질 점검에서 `housing_type`은 약 61.8%, 전세가율·시세갭은 약 1.7%가 결측이다. 임의 최빈값 대체로 유형을 왜곡하지 않고 LightGBM의 결측 분기를 사용한다.
- 실거래 평균·거래량은 서비스 시점의 안정적인 입력을 보장하기 어려워 최종 특징에서 제외한다.
- 무작위 분할 대신 horizon별 마지막 5개월을 test, 직전 5개월을 validation으로 사용한다.
- 분할 결과는 train 1,041,652행, validation 262,890행, test 265,404행이다.
- 60개월은 라벨 기준월이 1개뿐이므로 학습에는 포함하지만 정식 test 평가는 하지 않는다.

## 3. 입력 특징

`config/config_ver9b_multihorizon_calibrated.yaml`의 5개 feature set을 사용한다.

| 그룹 | 주요 열과 의미 |
|---|---|
| 예측기간 | `horizon_months`: 몇 개월 후 상승률인지 지정 |
| KB 시장정보 | 매매·전세시세, 전세가율, 시세갭 |
| 단지·평형 메타 | 구, 위·경도, 세대수, 준공월, 면적, 평형별 세대수, 용적률, 건폐율 |
| 생활 인프라 | 최근접 역·학교·병원 거리, 반경별 시설 수, 병원 의사 수 |
| 파생 안정성 특징 | 연식, 평당가, 단지 내 가격·면적 순위, 구 대비 프리미엄, 로그 세대수 |

전체 열 목록과 그룹별 개수는 제출 노트북 첫 부분에서 config로부터 직접 출력한다. 특징 생성 결과를 임의로 다시 계산하지 않고 동일한 feature store를 학습과 서비스가 공유한다.

## 4. 모델 구조

### 4.1 Base model: ver9b

단일 LightGBM 회귀 모델에 `horizon_months`를 특징으로 넣는다.

| 설정 | 값 |
|---|---:|
| objective | regression |
| n_estimators | 1,200 |
| learning_rate | 0.03 |
| num_leaves | 63 |
| min_child_samples | 80 |
| subsample / colsample_bytree | 0.9 / 0.9 |
| reg_lambda | 1.0 |
| early stopping | validation L1, 80 rounds |

Base 단계에서도 validation residual을 `horizon + 구 + 매매가격 사분위` 그룹으로 평균 내고, 표본 수에 따라 전체 평균 쪽으로 축소한다.

### 4.2 Final calibration: ver16

최근 validation 3개월에서 단지·평형·horizon별 반복 오차를 계산한다.

```text
raw residual = 실제 상승률 - base 예측
weight = 표본 수 / (표본 수 + 0.5)
final offset = prior + weight × (raw residual 평균 - prior)
final prediction = base prediction + final offset
```

표본이 부족하거나 처음 보는 단지·평형이면 다음 순서로 prior를 조회한다.

```text
단지·평형+horizon
→ 단지+horizon
→ 구+면적 그룹
→ horizon 전체
→ 전체 평균
```

test 라벨은 보정값 생성이나 설정 선택에 사용하지 않는다. 저장된 offset CSV는 실시간으로 누적 학습되는 값이 아니라 validation으로 미리 만든 고정 산출물이다.

## 5. 버전 개선 과정

서비스 목적과 동일한 multi-horizon 경로에서의 핵심 개선은 다음과 같다.

| 버전 | 핵심 변경 | Test MAE(%p) | 누적 개선 |
|---|---|---:|---:|
| ver9b | 단일 multi-horizon LightGBM | 8.2285 | 기준 |
| ver11 | 단지 residual 보정 | 6.8216 | 17.1% |
| ver12d | 그룹·horizon fallback | 6.4376 | 21.8% |
| ver13 | 단지·평형·horizon 보정 | 5.4754 | 33.5% |
| ver16 | 계층형 prior + shrinkage | **5.0376** | **38.8%** |

ver14는 test MAE가 5.3811로 낮았지만 validation rolling holdout에서 안정성이 확인되지 않아 최종 후보에서 제외했다. 최종 선택은 test 수치만이 아니라 validation 안정성까지 반영했다.

## 6. 최종 평가

전체 test 265,404행의 결과다. MAE와 RMSE 단위는 상승률의 percentage point(%p)다.

| 지표 | ver16 |
|---|---:|
| MAE | **5.0376** |
| RMSE | 8.1711 |
| R² | 0.7150 |
| Spearman | 0.8715 |
| 절대오차 P80 | 8.6336 |
| 절대오차 P90 | 13.6911 |

| horizon | 행 수 | MAE | RMSE | P80 | P90 |
|---:|---:|---:|---:|---:|---:|
| 12개월 | 82,571 | 4.8955 | 7.7892 | 8.2674 | 12.8447 |
| 24개월 | 60,953 | 4.9194 | 8.1016 | 8.5971 | 13.8572 |
| 36개월 | 60,952 | 6.0684 | 9.7123 | 10.4556 | 16.8060 |
| 48개월 | 60,928 | 4.3172 | 6.9706 | 7.5701 | 11.8045 |

P80/P90은 통계적 신뢰구간이 아니라 test 절대오차의 경험적 분위수다. 예를 들어 P80 8.6336은 test 표본의 80%에서 절대오차가 8.6336%p 이하였다는 뜻이다.

## 7. 코드와 서비스 연결

| 역할 | 경로 |
|---|---|
| 데이터 로드·시간 분할 | `src/ml_project/preprocessing.py` |
| LightGBM wrapper | `src/ml_project/models.py` |
| 학습·평가·산출물 저장 | `src/ml_project/train.py` |
| 서비스 추론 | `../modules/ml_predictor.py` |
| 최종 pipeline 설정 | `config/config.yaml` |
| base 설정 | `config/config_ver9b_multihorizon_calibrated.yaml` |
| 제출 검증 노트북 | `notebooks/submission_01_eda_preprocessing_ver16.ipynb` |

서비스에서는 최신 단지·평형 특징을 조회한 뒤 같은 base 모델에 12/24/36/60을 각각 넣고, ver16 offset을 적용한다. 60개월은 출력 가능하지만 성숙한 test window가 없어 `low confidence`로 취급한다.

## 8. 재현 방법

### 제출 노트북 실행

```powershell
cd C:\Users\User\Desktop\final\streamlit\ml_model
.\.venv\Scripts\python.exe -m jupyter nbconvert `
  --to notebook --execute notebooks\submission_01_eda_preprocessing_ver16.ipynb `
  --inplace `
  --ExecutePreprocessor.timeout=900
```

노트북은 feature schema, 시간 분할, ver16 offset 재생성, 최종 성능 일치 assertion까지 수행한다.

### 전체 pipeline 재학습

```powershell
cd C:\Users\User\Desktop\final\streamlit\ml_model
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe -m ml_project.train --config config/config.yaml
```

필수 로컬 산출물은 다음과 같다.

- `data/integration/apartment_multihorizon_ver9_stability_features.csv`
- `outputs/predictions/predictions_valid_target_return_pct_<timestamp>.csv`
- `outputs/predictions/predictions_test_target_return_pct_<timestamp>.csv`
- `outputs/calibration/ver12c_recent3_horizon_complex_residual_offsets.csv`
- `outputs/calibration/ver12d_group_residual_fallback_offsets.csv`
- `outputs/calibration/ver16_hierarchical_apt_size_offsets.csv`

대용량 데이터·모델·예측 파일은 Git에 올리지 않으므로 제출 또는 인수인계 시 별도 데이터 압축 파일에 포함해야 한다.

## 9. 해석상 한계

- 예측은 KB 시세 변화에 대한 통계적 추정이며 실제 매매 수익을 보장하지 않는다.
- 금리·정책·공급 충격을 인과적으로 설명하는 모델은 아니다.
- 36개월은 다른 평가 horizon보다 오차가 크다.
- 60개월 성능은 아직 test로 검증되지 않았다.
- 동일 단지·평형의 최근 validation 이력이 없는 경우 상위 그룹 보정으로 대체되므로 fallback 유형도 함께 제공해야 한다.
