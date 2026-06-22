# ver06220055_service_inference_integration

## 목적

서비스에서는 사용자가 클릭한 단지의 12개월 예상 상승률을 즉시 보여줘야 한다. 따라서 현재 검증 유지 기준 최선인 ver7d 모델을 Streamlit 앱에서 호출할 수 있도록 연결했다. 단일 예측값만 제공하지 않고, ver7d test residual 기반 오차범위도 함께 반환한다.

## 구현

- `streamlit/modules/ml_predictor.py`
  - 기존 `predict_price_growth(region, area_type, horizon, current_index)` 함수 시그니처는 유지했다.
  - 클릭 단지 전용 `predict_apartment_growth(complex_id, area_serial_no=None, current_price_manwon=None, apt_size_id=None)` 함수를 추가했다.
  - ver7d pickle model, `apartment_12m_ver6f_stability_features.csv`, `ver06220040_ver7d_error_profile.csv`를 로드한다.
  - 최신 기준월 feature row를 찾고, 모델 prediction + 저장된 calibration을 적용한다.
  - P80/P90 절대오차 기반 예측 구간과 confidence를 반환한다.

- `streamlit/app.py`
  - `my_complex_id`가 있는 경우 Tab3에서 12개월 상승률 예측 카드를 표시한다.
  - 표시 항목: 예상 상승률, 보수적 오차범위(P80), 신뢰도, P90 예상 범위, 모델 버전.

## 반환 예시

샘플 `complex_id=1`, `current_price_manwon=250000` 기준:

| 항목 | 값 |
|---|---:|
| 기준월 | 202506 |
| 예측 상승률 | 16.124% |
| P80 범위 | 5.955% ~ 26.292% |
| 신뢰도 | medium |
| 모델 버전 | `ver7d_lightgbm_12m_gu_price_calibrated` |

## 검증

```powershell
python -m py_compile streamlit/app.py streamlit/modules/ml_predictor.py

@'
import sys, json
sys.path.insert(0, r'C:\Users\User\Desktop\final\streamlit')
from modules.ml_predictor import predict_apartment_growth
result = predict_apartment_growth(complex_id=1, current_price_manwon=250000)
print(json.dumps(result, ensure_ascii=False, indent=2))
'@ | & 'C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe' -
```

검증 결과:

- `app.py`, `ml_predictor.py` 문법 컴파일 통과
- 샘플 단지 예측 정상 반환

## 주의

- 현재 실제 학습 모델은 12개월 예측만 지원한다. `3yr`, `5yr` 요청은 낮은 신뢰도와 미지원 note를 반환한다.
- 지역/평형 기반 기존 `predict_price_growth`는 호환용이다. 서비스의 클릭 단지 예측에는 `predict_apartment_growth`를 사용해야 한다.
- 첫 호출 시 모델과 feature store CSV를 로드하므로 시간이 걸릴 수 있다. Streamlit 배포 단계에서는 캐시 또는 사전 생성된 latest inference table을 고려한다.
