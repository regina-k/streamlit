# ver11 Service Metadata QA

## 목적

서비스에서는 사용자가 클릭한 개별 단지의 12/24/36/60개월 예측 상승률을 바로 보여준다. 현재 최선 후보인 ver11은 ver9b multi-horizon 예측값에 `complex_id`별 최근 validation residual offset을 더하는 구조이므로, 예측값과 함께 보정 기준 정보가 노출되어야 운영 중 성능 저하나 보정 stale 여부를 추적할 수 있다.

## 변경 내용

- `streamlit/app.py`의 단지별 상승률 예측 caption에 `source_max_date`를 추가했다.
- 기존 표시 정보는 유지했다.
  - 기준월
  - 모델 버전
  - residual 보정 fallback 방식
  - residual 보정 valid row 수
- 추가 표시 정보:
  - residual offset 산출에 사용된 source window의 마지막 날짜

## 사용 모델과 데이터

- 서비스 모델: `ver11_ver9b_plus_complex_residual`
- 기반 모델: ver9b LightGBM multi-horizon
- 보정: `complex_id`별 validation residual offset, fallback은 global residual
- 최신 서비스 feature store: `data/integration/apartment_multihorizon_ver9_latest_features.csv`
- residual offset: `streamlit/ml_model/outputs/calibration/ver11_complex_residual_offsets.csv`

## 검증

문법 검증:

```powershell
python -m py_compile C:\Users\User\Desktop\final\streamlit\app.py C:\Users\User\Desktop\final\streamlit\modules\ml_predictor.py
```

결과: 통과.

서비스 예측 smoke test:

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\smoke_test_service_prediction.py
```

결과: 통과.

확인된 반환값:

- covered case `complex_id=1`
  - `offset_applied=True`
  - `fallback=complex_id`
  - `valid_rows=80`
  - `source_max_date=2025-01-01`
  - 12/24/36/60개월 예측 모두 반환
- fallback case `complex_id=7`
  - `offset_applied=False`
  - `fallback=global`
  - `valid_rows=0`
  - `source_max_date=2025-01-01`
  - 12/24/36/60개월 예측 모두 반환

## 판단

이번 변경은 모델 성능을 직접 개선한 실험은 아니지만, 개별 단지 예측을 서비스에서 쓰기 위한 운영 안정성 개선이다. ver11 보정은 최근 validation residual에 의존하므로, 예측 카드에 보정 기준일을 표시해야 이후 데이터 갱신 시점과 예측 품질을 함께 점검할 수 있다.

다음 성능 개선은 ver11 구조를 유지하되, 클릭 단지별 예측 오차를 줄이는 방향으로 진행하는 것이 좋다. 우선순위는 단지별 residual 보정의 기간 민감도, horizon별 별도 residual offset, 그리고 단지별 최근 가격 모멘텀/변동성 피쳐의 누수 없는 재설계다.
