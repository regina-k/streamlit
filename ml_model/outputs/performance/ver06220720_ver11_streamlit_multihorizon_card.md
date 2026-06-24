# ver11 Streamlit multi-horizon card

## 목적

서비스에서는 사용자가 클릭한 단지의 예측 상승률을 화면에서 바로 확인해야 한다. 기존 Streamlit Tab 3 예측 카드는 12개월 전용 `predict_apartment_growth(...)`만 호출하고 있었다. ver11 후보를 실제 서비스 흐름에 맞추기 위해 multi-horizon 함수 `predict_apartment_growth_horizons(...)`를 화면에 연결했다.

## 변경 파일

- `C:/Users/User/Desktop/final/streamlit/app.py`
- `C:/Users/User/Desktop/final/streamlit/modules/ml_predictor.py`

## 변경 내용

- `app.py`에서 `predict_apartment_growth_horizons`를 import한다.
- 선택된 `my_complex_id`, `my_current_price` 기준으로 12/24/36/60개월 예측을 한 번에 호출한다.
- Tab 3에 horizon별 metric 카드를 렌더링한다.
- 각 카드에는 예측 상승률, P80 절대오차 폭, confidence를 표시한다.
- 하단 caption에는 기준월, 모델 버전, residual 보정 fallback, valid row 수를 표시한다.
- 장기 horizon 또는 신뢰도가 낮은 예측이 있으면 보수적 해석 warning을 표시한다.

## 검증

문법 검사:

```powershell
python -m py_compile C:\Users\User\Desktop\final\streamlit\app.py
```

결과: 통과.

서비스 예측 smoke test:

```powershell
python .\scripts\smoke_test_service_prediction.py
```

검증 내용:

- covered complex `complex_id=1`은 complex residual offset을 적용해야 한다.
- fallback complex `complex_id=7`은 global residual offset으로 fallback해야 한다.
- 두 케이스 모두 12/24/36/60개월 예측 4개를 반환해야 한다.
- 각 예측에는 상승률, P80/P90 구간, confidence가 있어야 한다.
- `residual_calibration`에는 offset 적용 여부, fallback, valid row 수, source window가 있어야 한다.

결과: 통과.

```text
model_version: ver11_ver9b_plus_complex_residual
residual_calibration: {'offset_applied': True, 'residual_offset': 6.323282278672215, 'valid_rows': 80, 'source_max_date': '2025-01-01', 'fallback': 'complex_id'}
```

## 추가 복구

`app.py`에 기존 인코딩 깨짐으로 닫히지 않은 문자열이 여러 개 있어 `py_compile`이 실패했다. 이번 UI 연결 검증을 위해 다음 문구를 정상 문자열로 복구했다.

- `st.set_page_config`의 `page_title`, `page_icon`
- 단지 검색 입력 label/placeholder
- 단지 정보 카드의 세대수/입주년월/면적 선택/현재 KB매매시세 문구
- 매수 시점 및 매수가 입력 문구
- 앱 title, tab label, 일부 subheader
- footer caption

## 판단

이제 모델 후보 ver11은 단순 함수 수준이 아니라 Streamlit 화면의 실제 클릭 단지 흐름에 연결됐다. 현재 앱에서는 12/24/36/60개월이 같은 단지/평형 기준으로 표시된다.
