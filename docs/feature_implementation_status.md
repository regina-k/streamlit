# 기능 구현 현황표

## 기준

- 완료: 현재 앱에서 실행 가능한 수준으로 연결됨
- 부분 구현: 기본 동작은 있으나 정확도, UX, 예외 처리, 외부 연동 보강 필요
- 미구현: PRD에는 있으나 현재 코드에 기능이 없음

| 구분 | 기능 | 현재 상태 | 관련 파일/경로 | 비고 / 다음 작업 |
|---|---|---:|---|---|
| 실행 환경 | 버전 고정 의존성 | 완료 | `requirements.txt` | 새 환경 설치와 `pip check` 통과 기준 |
| 데이터 구조 | KB 아파트 데이터 관리 | 완료 | `data/apartment/` | 원천 CSV와 전처리 CSV 보관. Git 제외 |
| 데이터 구조 | 학교/역/병원 입지 데이터 관리 | 완료 | `data/additional/`, `data/additional/preprocessed/` | `school.csv`, `station.csv`, `hospital.csv`를 통합 feature store 재생성에 사용 |
| 데이터 구조 | ML 통합 feature store 관리 | 완료 | `data/integration/` | 앱 추론은 `apartment_multihorizon_ver9_latest_features.csv` 사용 |
| 데이터 구조 | RAG 문서 위치 정리 | 완료 | `data/rag_docs/`, `.gitignore` | RAG 원천 문서는 추적, FAISS 산출물은 제외 |
| 데이터 로딩 | KB 아파트 CSV 로딩 | 완료 | `modules/data_loader.py` | `kb_apt_seoul_full.csv` 사용 |
| 데이터 로딩 | KB 시계열 CSV 로딩 | 완료 | `modules/data_loader.py` | `kb_timeseries_seoul.csv` 사용 |
| 단지 검색 | 지역/가격/면적/평형 필터 | 완료 | `app.py`, `modules/data_loader.py` | 기본 검색 workflow 동작 |
| 단지 검색 | 단지명 유사도 검색 | 부분 구현 | `app.py`, `modules/data_loader.py` | 현재는 문자열 포함 검색 중심 |
| 단지 검색 | 필요자본/상승률 기준 정렬 | 미구현 | `app.py` | PRD 요구사항. 계산 컬럼과 정렬 UI 추가 필요 |
| 단지 상세 | 선택 단지 기본 정보 표시 | 완료 | `app.py` | Streamlit table selection 기반 |
| 단지 상세 | 실거래가/시계열 추이 표시 | 미구현 | `app.py`, `modules/data_loader.py` | 시계열 데이터는 있으나 차트 UI 미연결 |
| ML 예측 | 1년/3년/5년 상승률 예측 | 완료 | `modules/ml_predictor.py`, `app.py` | `ver16_hierarchical_apt_size_residual` 연결 |
| ML 예측 | 예측 신뢰도/모델 버전 표시 | 완료 | `app.py`, `modules/ml_predictor.py` | 예측 카드에 표시 |
| 대출 계산 | 대출 한도/LTV/DSR/필요 자기자금 | 완료 | `modules/loan_calculator.py`, `app.py` | 규칙 기반 추정치. 실제 심사 확정값은 아님 |
| 대출 상품 | 사용자 조건 기반 상품 안내 | 부분 구현 | `modules/loan_calculator.py`, `app.py` | 실제 상품 DB/API 연동 필요 |
| 대출 상품 | 상품 상세 사이트 연결 | 미구현 | `app.py` | PRD 선택 기능 |
| 사용자 입력 | 가구 형태/목적/자본/소득/대출 입력 | 완료 | `app.py` | 사이드바 입력 |
| 보유 주택 | 매수 시점/매수가 입력 | 완료 | `app.py` | 보유 주택 비교의 기반 입력 |
| 보유 주택 | 보유 주택과 대상 단지 비교 리포트 | 부분 구현 | `app.py` | 보유 단지 식별과 비교 metric 보강 필요 |
| RAG | RAG 원천 문서 관리 | 완료 | `data/rag_docs/` | 규제 문서와 신한 FAQ 포함 |
| RAG | FAISS 벡터스토어 생성 | 부분 구현 | `scripts/build_vectorstore.py` | `OPENAI_API_KEY` 필요, 산출물은 Git 제외 |
| RAG | AI 종합 분석 답변 | 부분 구현 | `modules/rag_advisor.py`, `app.py` | 벡터스토어가 있으면 RAG, 없으면 안내 표시 |
| RAG | 채널형/상태 유지형 채팅 UI | 미구현 | `app.py` | 현재는 버튼 실행형 단발 분석 |
| 문서화 | PRD 구체화 | 완료 | `docs/prd_refined.md` | 원본 `docs/prd.md` 보존 |
| 문서화 | 기능 구현 현황표 | 완료 | `docs/feature_implementation_status.md` | 현재 문서 |

## 검증 기록

- `pip install -r requirements.txt` 후 `pip check` 통과
- Python compile 검증 통과
- `load_kb_apt_data`, `filter_apartments` smoke 검증 통과
- `predict_price_growth('1yr'/'3yr'/'5yr')` smoke 검증 통과
- `get_loan_advice` fallback smoke 검증 통과
- Streamlit `AppTest` 초기 렌더링 예외 0개 기준으로 확인
