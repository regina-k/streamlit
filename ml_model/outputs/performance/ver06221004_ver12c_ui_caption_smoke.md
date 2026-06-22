# ver12c UI Caption Smoke Test

## 목적

ver12c 예측 카드는 horizon별 fallback 방식, valid rows, source window를 보여줘야 한다. Streamlit 화면에서 긴 메타데이터가 깨지거나 누락되면 개별 단지 예측의 운영 추적성이 떨어진다.

## 변경 내용

- `streamlit/app.py`
  - horizon별 카드 caption을 ASCII 구분자 `|` 기반으로 정리했다.
  - 각 카드에 `fallback`, `valid rows`, `source_min_date~source_max_date`를 표시한다.
- `scripts/smoke_test_service_ui_captions.py`
  - 서비스 예측 결과를 이용해 UI caption 문자열을 재현한다.
  - prediction별 source window 누락, invalid valid rows를 검증한다.

## 검증 결과

covered case `complex_id=1`:

```text
12m: P80 +/- 9.9%p | medium | complex_id+horizon | rows 12 | 2024-11-01~2025-01-01
24m: P80 +/- 11.2%p | medium | complex_id+horizon | rows 12 | 2023-11-01~2024-01-01
36m: P80 +/- 12.5%p | low | complex_id+horizon | rows 12 | 2022-11-01~2023-01-01
60m: P80 +/- 10.4%p | low | global | rows 0 | 2021-11-01~2025-01-01
```

fallback case `complex_id=7`:

```text
12m: P80 +/- 9.9%p | medium | horizon_global | rows 48901 | 2024-11-01~2025-01-01
24m: P80 +/- 11.2%p | medium | horizon_global | rows 36596 | 2023-11-01~2024-01-01
36m: P80 +/- 12.5%p | low | horizon_global | rows 36596 | 2022-11-01~2023-01-01
60m: P80 +/- 10.4%p | low | global | rows 0 | 2021-11-01~2025-01-01
```

## Browser 확인 시도

ML 가상환경에 `streamlit`이 없어 설치 후 Streamlit 서버를 실행했다. shell 기준으로는 `http://localhost:8508` HTTP 200까지 확인했다. 다만 in-app browser에서는 `localhost:8508`이 `ERR_CONNECTION_REFUSED`, `host.docker.internal:8508`이 name resolution 실패로 접근되지 않았다. 따라서 실제 브라우저 렌더링 확인은 환경 제한으로 완료하지 못했고, 서비스 함수 출력과 UI caption 생성 경로를 스모크 테스트로 검증했다.

## 검증 명령어

```powershell
python -m py_compile C:\Users\User\Desktop\final\scripts\smoke_test_service_ui_captions.py C:\Users\User\Desktop\final\streamlit\app.py
```

```powershell
& C:\Users\User\Desktop\final\streamlit\ml_model\.venv\Scripts\python.exe C:\Users\User\Desktop\final\scripts\smoke_test_service_ui_captions.py
```

## 판단

서비스 후보는 계속 ver12c다. 이번 작업은 예측 성능이 아니라 화면 표시 안정성 개선이다. 각 horizon 카드가 해당 horizon의 보정 방식과 source window를 독립적으로 보여주므로, 사용자가 클릭한 단지의 예측값을 운영자가 추적하기 쉬워졌다.
