# AI 기반 개인 맞춤형 부동산 분석 및 대출 제안 서비스

신한은행 AI Intensive 7조 — KB부동산 라이브 데이터와 ML 예측, LangChain RAG를 결합하여
고객 맞춤형 아파트 투자 분석 및 대출 포트폴리오를 제안하는 Streamlit 앱.

---

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

환경변수 설정:

```bash
cp .env.example .env
# .env 파일에 OPENAI_API_KEY 입력
```

---

## 디렉토리 구조

```
project_root/
├── app.py                    # 메인 Streamlit 앱 — UI 오케스트레이터 (이동욱)
├── config.py                 # 전역 상수·경로 설정
├── requirements.txt
├── .env.example
│
├── modules/
│   ├── kb_api.py             # KB부동산 API 호출 (김혜민)
│   ├── data_loader.py        # CSV 로드·필터링 (김혜민)
│   ├── utils.py              # 금액 포맷팅 공통 유틸
│   ├── loan_calculator.py    # LTV/DSR/대출한도 계산
│   ├── ml_predictor.py       # 아파트 상승률 ML 예측 (장원준) ← STUB
│   └── rag_advisor.py        # RAG/LLM 어드바이저 (김동하) ← STUB
│
├── data/
│   ├── kb_data.csv           # KB 단지 데이터
│   └── ml_apt_index_sigungu.csv
│
├── models/                   # 학습된 ML 모델 (장원준)
└── vector_store/             # RAG 벡터 DB (김동하)
```

---

## 팀원별 담당 파일 및 TODO

| 이름 | 파일 | TODO |
|---|---|---|
| **김혜민** | `modules/kb_api.py` | `fetch_*` 함수 3개 구현 (API 호출 로직) |
| **김혜민** | `modules/data_loader.py` | `load_kb_apt_data`, `load_ml_timeseries`, `filter_apartments` 구현 |
| **장원준** | `modules/ml_predictor.py` | `predict_price_growth` 내부를 LightGBM 실제 예측으로 교체, `models/` 에 모델 저장 |
| **김동하** | `modules/rag_advisor.py` | `_stub_gpt_response` → `get_loan_advice` RAG 파이프라인으로 교체, `vector_store/` 구성 |
| **이동욱** | `app.py` | Tab 1~3 UI 구현, 각 모듈 함수 호출 연결 (파일 내 TODO 주석 참고) |
| **공통** | `modules/utils.py`, `modules/loan_calculator.py` | 함수 내 TODO 구현 |

> **함수 시그니처(입출력 타입) 변경 금지** — 특히 `predict_price_growth`, `get_loan_advice`.
> 내부 구현만 교체할 것.

---

## 설계 원칙

- **Streamlit 격리**: `modules/` 내 파일에는 `st.*` 사용 금지. 에러는 `Exception`으로 raise, `app.py`에서 `st.error()`로 캐치.
- **STUB 우선**: `ml_predictor`, `rag_advisor`가 더미 반환 중에도 UI 완전 동작. `note` 필드 확인으로 STUB 여부 감지.
- **인터페이스 계약**: 함수 시그니처 확정 → 담당자가 내부만 채우면 `app.py` 무수정 연동.
