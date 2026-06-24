# multi-horizon service inference integration

## 목적

사용자가 클릭한 단지/평형에 대해 12/24/36/60개월 예측 상승률을 한 번에 제공할 수 있도록 ver9b multi-horizon 모델의 서비스 호출 경로를 추가했다. 기존 12개월 전용 ver7d 함수는 유지했다.

## 추가 산출물

- 최신 inference feature store: `C:/Users/User/Desktop/final/data/integration/apartment_multihorizon_ver9_latest_features.csv`
- 생성 스크립트: `C:/Users/User/Desktop/final/scripts/build_multihorizon_inference_store.py`
- 서비스 함수: `predict_apartment_growth_horizons(...)`
- 수정 파일: `C:/Users/User/Desktop/final/streamlit/modules/ml_predictor.py`

## 재현 명령어

```powershell
python .\scripts\build_multihorizon_inference_store.py
```

## Feature Store 가공 방식

원본 `apartment_multihorizon_ver9_stability_features.csv`는 약 1.1GB라 Streamlit 앱에서 직접 읽기에는 무겁다. 따라서 ver9b 모델 artifact의 `feature_columns`와 서비스 식별 컬럼만 읽고, 최신 기준월인 2025-06-01의 단지-평형 행만 남겼다.

생성 결과:

- 기준월: 2025-06-01
- 행 수: 16,679
- 컬럼 수: 62

서비스 예측 시에는 이 최신 행을 선택한 뒤 `horizon_months`만 12/24/36/48/60으로 바꿔 ver9b 모델에 넣는다.

## 함수 구조

- `predict_apartment_growth(...)`: 기존 12개월 ver7d 모델 사용. 앱 호환성을 위해 유지.
- `predict_apartment_growth_horizons(...)`: ver9b multi-horizon 모델 사용. 기본 horizon은 `12m`, `24m`, `36m`, `60m`.
- `predict_price_growth(...)`: 기존 앱 호환 함수. 12개월만 지원하도록 유지.

## 검증

문법 검사:

```powershell
python -m py_compile C:\Users\User\Desktop\final\streamlit\modules\ml_predictor.py
```

multi-horizon 호출 예:

```powershell
$env:PYTHONPATH='C:\Users\User\Desktop\final\streamlit'
python -c "from modules.ml_predictor import predict_apartment_growth_horizons; r=predict_apartment_growth_horizons(complex_id=1,horizons=('12m','24m','36m','60m')); print(r['model_version'], r['base_date'], len(r['predictions']))"
```

검증 결과:

- model_version: `ver9b_lightgbm_multihorizon_calibrated`
- base_date: `2025-06-01`
- predictions: 4개 horizon 정상 반환

기존 12개월 호출도 확인했다.

- model_version: `ver7d_lightgbm_12m_gu_price_calibrated`
- base_date: `2025-06-01`
- 예측값 반환 정상

## 주의

60개월은 학습에는 포함됐지만 valid/test 검증이 불가능했다. 서비스에서는 `confidence='low'`로 반환한다. 12개월 단일 정확도는 여전히 ver7d가 더 낫고, 여러 horizon을 한 모델에서 제공하는 목적에는 ver9b가 더 적합하다.

