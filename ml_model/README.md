# Apartment Return ML Project

서울 아파트 단지/평형 단위의 KB 매매시세 상승률을 예측하기 위한 LightGBM 기반 ML 프로젝트이다. 현재 서비스 후보는 `ver16_hierarchical_apt_size_residual`이다.

## 현재 최종 후보

- 최종 후보: `ver16`
- 기본 모델: `ver9b` 단일 multi-horizon LightGBM
- 사용 방식: `horizon_months`에 12, 24, 36, 60을 넣어 같은 모델로 horizon별 상승률을 예측
- 서비스 함수: `streamlit/modules/ml_predictor.py`의 `predict_apartment_growth_horizons`
- 주의: 60개월은 inference는 가능하지만 아직 성숙한 test window가 없어 `global` fallback 및 low confidence로 처리한다.

## 재현 설정

기본 `config/config.yaml`은 현재 최종 후보 ver16을 한 번에 재현하는 pipeline config이다.

ver16 전체 재현 정보는 아래 매니페스트에 정리되어 있다.

```text
config/config_ver16_reproduction.yaml
```

`config/config_ver9b_multihorizon_calibrated.yaml`은 base LightGBM만 학습할 때 사용하는 하위 설정이다. 기본 재현은 `config/config.yaml`을 사용한다.

## 주요 데이터

```text
C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_ver9_stability_features.csv
C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_ver9_latest_features.csv
```

첫 번째 파일은 학습/검증/테스트용 feature store이고, 두 번째 파일은 서비스 inference용 최신 기준월 feature store이다.

## 사용 피쳐

`config/config_ver9b_multihorizon_calibrated.yaml` 기준 active feature set:

- `horizon`: `horizon_months`
- `kb_market`: KB 매매/전세 시세, 전세가율, 시세갭
- `apartment_meta`: 구, 좌표, 세대수, 준공월, 면적, 용적률, 건폐율 등 단지/평형 메타
- `poi_accessibility`: 역/학교/병원 거리 및 반경 내 개수
- `individual_stability_without_actual_tx`: 연식, 평당가, 단지 내 가격 순위, 구 대비 프리미엄 등 안정적 파생 피쳐

실거래 평균/거래량 계열은 서비스 시점에서 안정적으로 입력되기 어렵다고 보고 현재 최종 후보에서는 제외했다.

## 원큐 재현 명령어

```powershell
cd C:\Users\User\Desktop\final\streamlit\ml_model
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="src"
python -m ml_project.train --config config/config.yaml
```

이 명령은 다음을 순서대로 실행한다.

- `config_ver9b_multihorizon_calibrated.yaml`로 base LightGBM 학습
- 새 train/valid/test prediction CSV 저장
- 새 모델을 `outputs/models/ver16_service_multihorizon_base_model.pkl`로 복사
- 새 valid/test prediction으로 `ver16_hierarchical_apt_size_offsets.csv` 재생성
- pipeline 결과 JSON 저장

## base 모델만 학습

```powershell
cd C:\Users\User\Desktop\final\streamlit\ml_model
$env:PYTHONPATH="src"
python -m ml_project.train --config config/config_ver9b_multihorizon_calibrated.yaml
```

생성 산출물:

```text
streamlit/ml_model/outputs/calibration/ver16_hierarchical_apt_size_offsets.csv
streamlit/ml_model/outputs/calibration/ver16_hierarchical_apt_size_shrinkage_grid.json
streamlit/ml_model/outputs/models/ver16_service_multihorizon_base_model.pkl
```

## 검증 명령어

```powershell
python -m py_compile .\scripts\compare_hierarchical_apt_size_shrinkage.py .\scripts\analyze_service_offset_coverage.py .\scripts\smoke_test_service_prediction.py .\scripts\smoke_test_service_ui_captions.py .\streamlit\modules\ml_predictor.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_prediction.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\smoke_test_service_ui_captions.py
& .\streamlit\ml_model\.venv\Scripts\python.exe .\scripts\analyze_service_offset_coverage.py
```

## 성능 기록

버전별 성능과 판단 근거는 아래 문서를 먼저 확인한다.

```text
streamlit/ml_model/outputs/performance/VERSION_LOG.md
streamlit/ml_model/outputs/performance/ver06222256_ver16_hierarchical_apt_size_shrinkage.md
```

ver16 test 성능:

- MAE: `5.0376`
- RMSE: `8.1711`
- R2: `0.7150`
- Spearman: `0.8715`
- P80 absolute error: `8.6336`
- P90 absolute error: `13.6911`

## app.py와 모델 작업의 분리

이번 모델 작업의 핵심은 `streamlit/modules/ml_predictor.py`, `streamlit/ml_model/config`, `streamlit/ml_model/outputs`, `scripts`에 있다. `app.py`는 UI 레이어이므로 원복해도 ver16 모델 산출물과 predictor 함수에는 영향이 없다.
