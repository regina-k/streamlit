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
│   ├── data_loader.py        # CSV 로드·필터링 (장원준) ← ML 입력 형태 설계
│   ├── utils.py              # 금액 포맷팅 공통 유틸
│   ├── loan_calculator.py    # LTV/DSR/대출한도 계산
│   ├── ml_predictor.py       # 아파트 상승률 ML 예측 (장원준) ← STUB
│   └── rag_advisor.py        # RAG/LLM 어드바이저 (김동하) ← STUB
│
├── data/
│   ├── kb_apt_seoul_full.csv      # KB 단지·시세 데이터 (normalize_to_csv.py 출력)
│   └── kb_timeseries_seoul.csv    # KB 월별 시세 시계열 (collect_kb_timeseries.py 출력)
│
├── models/                   # 학습된 ML 모델 (장원준)
└── vector_store/             # RAG 벡터 DB (김동하)
```

---

## 팀원별 담당 파일 및 TODO

| 이름 | 파일 | TODO |
|---|---|---|
| **김혜민** | `modules/kb_api.py` | `fetch_search_suggestions`, `fetch_complex_id`, `fetch_complex_price`, `fetch_complex_timeseries` 구현 완료 |
| **장원준** | `modules/data_loader.py` | `load_kb_apt_data`, `load_ml_timeseries`, `filter_apartments` — ML 모델이 요구하는 형태로 자유롭게 설계 |
| **장원준** | `modules/ml_predictor.py` | `predict_price_growth` 내부를 LightGBM 실제 예측으로 교체, `models/` 에 모델 저장 |
| **김동하** | `modules/rag_advisor.py` | `_stub_gpt_response` → `get_loan_advice` RAG 파이프라인으로 교체, `vector_store/` 구성 |
| **이동욱** | `app.py` | Tab 1~3 UI 구현, 각 모듈 함수 호출 연결 (파일 내 TODO 주석 참고) |
| **공통** | `modules/utils.py`, `modules/loan_calculator.py` | 함수 내 TODO 구현 |

> **함수 시그니처(입출력 타입) 변경 금지** — 특히 `predict_price_growth`, `get_loan_advice`.
> 내부 구현만 교체할 것.

---

## 데이터 파일 안내

| 파일 | 생성 스크립트 | 주요 컬럼 |
|---|---|---|
| `kb_apt_seoul_full.csv` | `collect_kb_data.py` + `normalize_to_csv.py` | 단지ID, 단지명, 시군구, 세대수, 준공년월, 공급면적(평), KB매매시세(만원) 등 |
| `kb_timeseries_seoul.csv` | `collect_kb_timeseries.py` | 단지ID, 면적일련번호, 기준년월, KB매매시세(만원), KB전세시세(만원) 등 월별 시세 |

`data_loader.py`를 담당하는 장원준은 위 CSV를 기반으로 ML 학습에 필요한 형태로 자유롭게 전처리 로직을 설계한다.
app.py와의 연결은 `filter_apartments()`의 반환 스펙(DataFrame, reset_index 적용)만 유지하면 된다.

---

## 설계 원칙

- **Streamlit 격리**: `modules/` 내 파일에는 `st.*` 사용 금지. 에러는 `Exception`으로 raise, `app.py`에서 `st.error()`로 캐치.
- **STUB 우선**: `ml_predictor`, `rag_advisor`가 더미 반환 중에도 UI 완전 동작. `note` 필드 확인으로 STUB 여부 감지.
- **인터페이스 계약**: 함수 시그니처 확정 → 담당자가 내부만 채우면 `app.py` 무수정 연동.
