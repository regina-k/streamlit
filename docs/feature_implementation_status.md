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
| 보안/UX | OpenAI API Key 화면 노출 제거 | 완료 | `app.py`, `.env` | 키 직접 입력 UI 제거, 환경변수 연결 상태만 표시 |
| 데이터 로딩 | KB 아파트 CSV 로딩 | 완료 | `modules/data_loader.py` | `kb_apt_seoul_full.csv` 사용 |
| 데이터 로딩 | KB 시계열 CSV 로딩 | 완료 | `modules/data_loader.py` | `kb_timeseries_seoul.csv` 사용 |
| 단지 검색 | 지역/가격/면적/평형 필터 | 완료 | `app.py`, `modules/data_loader.py` | 기본 검색 workflow 동작 |
| 단지 검색 | 단지명 유사도 검색 | 완료 | `app.py`, `modules/data_loader.py` | 포함 검색과 표기 차이/오타 유사도 점수 기반 검색 연결. 점수는 내부 정렬에만 사용하고 화면 표에는 미노출 |
| 단지 검색 | 필요자본/상승률 기준 정렬 | 완료 | `app.py`, `modules/ml_predictor.py` | 필요자기자금/매매시세/월간매매변동률 정렬과 필터로 좁힌 후보 상위 5개 AI 1년 상승률 정렬 구현. 계산 후 `AI 계산 후보만 보기` 토글 제공 |
| 단지 상세 | 선택 단지 기본 정보 표시 | 완료 | `app.py` | Streamlit table selection 기반. 선택 단지 상세 영역에 1년/3년/5년 예측 카드 표시 |
| 단지 상세 | 실거래가/시계열 추이 표시 | 완료 | `app.py`, `modules/data_loader.py` | 선택 단지/평형의 KB 매매·전세 및 실거래 평균 시계열 차트 연결 |
| ML 예측 | 1년/3년/5년 상승률 예측 | 완료 | `modules/ml_predictor.py`, `app.py` | `ver16_hierarchical_apt_size_residual` 연결 |
| ML 예측 | 예측 신뢰도/모델 버전 표시 | 완료 | `app.py`, `modules/ml_predictor.py` | 예측 카드에 표시 |
| 대출 계산 | 대출 한도/LTV/DSR/필요 자기자금 | 완료 | `modules/loan_calculator.py`, `app.py` | 규칙 기반 추정치. 실제 심사 확정값은 아님 |
| 대출 상품 | 사용자 조건 기반 상품 안내 | 부분 구현 | `modules/loan_calculator.py`, `app.py` | 실제 상품 DB/API 연동 필요 |
| 대출 상품 | 상품 상세 사이트 연결 | 완료 | `app.py`, `modules/loan_calculator.py` | 추천 상품 카드에 신한은행 공식 상품 상세/목록 링크 버튼 연결 |
| 사용자 입력 | 가구 형태/목적/자본/소득/대출 입력 | 완료 | `app.py` | `내 투자 프로파일` 탭 입력 |
| 보유 주택 | 보유 단지 검색/매수 시점/매수가 입력 | 완료 | `app.py` | `내 투자 프로파일` 탭의 선택 입력. 갈아타기 비교가 필요할 때만 사용 |
| 보유 주택 | 보유 주택과 대상 단지 비교 리포트 | 완료 | `app.py` | KB 검색 또는 직접 입력 시세를 기반으로 매도 후 자기자본, 필요 자기자금, 잔여/부족 자금 표시 |
| RAG | RAG 원천 문서 관리 | 완료 | `data/rag_docs/` | 규제 문서와 신한 FAQ 포함 |
| RAG | FAISS 벡터스토어 생성 | 부분 구현 | `scripts/build_vectorstore.py` | `OPENAI_API_KEY` 필요, 산출물은 Git 제외 |
| RAG | AI 종합 분석 답변 | 부분 구현 | `modules/rag_advisor.py`, `app.py` | 벡터스토어가 있으면 RAG, 없으면 입력값 기반 fallback 안내 표시 |
| RAG | 채널형/상태 유지형 채팅 UI | 완료 | `app.py`, `modules/rag_advisor.py` | 빠른 질문, 자유 질문, 대화 이력 표시를 Tab 3에 연결 |
| 문서화 | PRD 구체화 | 완료 | `docs/prd_refined.md` | 원본 `docs/prd.md` 보존 |
| 문서화 | 기능 구현 현황표 | 완료 | `docs/feature_implementation_status.md` | 현재 문서 |
| 문서화 | UX 직접 점검 기록 | 완료 | `docs/ux_review_20260623.md` | Playwright 기반 탭/검색/계산/정렬 관찰과 개선 방향 기록 |

## 검증 기록

- `pip install -r requirements.txt` 후 `pip check` 통과
- Python compile 검증 통과
- `load_kb_apt_data`, `filter_apartments` smoke 검증 통과
- `predict_price_growth('1yr'/'3yr'/'5yr')` smoke 검증 통과
- `get_loan_advice` fallback smoke 검증 통과
- Streamlit `AppTest` 초기 렌더링 예외 0개 기준으로 확인
- Playwright로 `http://localhost:8510` 직접 실행 확인: API Key 입력창 제거, 가격 포맷 정상, 검색/정렬 UI 동작, 콘솔 error 0개
- 단지명 유사도 검색과 AI 상담형 UI 추가 후 Python compile 및 Streamlit `AppTest` 예외 0개 확인
- 후보별 AI 상승률 계산 버튼과 보유 주택 직접 입력 비교 리포트 추가 후 Python compile 및 Streamlit `AppTest` 예외 0개 확인
- Playwright 재검증 중 기본 화면의 0원 시세 노출과 전체 후보 AI 계산 UX 병목을 확인했고, 양수 시세 기준 지표/필터와 후보 1,500개 이하에서만 열리는 AI 상승률 계산 UX로 수정. 재검증 콘솔 error/warning 0개 확인
- Playwright로 탭/검색/계산/정렬 흐름 재점검 후 `내 투자 프로파일`을 1번 탭으로 이동, `AI 계산 후보만 보기` 토글 추가, 선택 단지 상세 영역에 1년/3년/5년 예측 카드 추가
- 단지 탐색 표에서 `검색유사도` 컬럼을 숨기고, 보유 주택/매수 정보 입력을 사이드바에서 `내 투자 프로파일` 탭으로 이동한 뒤 Python compile 및 Streamlit `AppTest` 예외 0개 확인
- 보유 주택 입력이 필수처럼 보이지 않도록 `내 투자 프로파일` 탭의 접힌 선택 입력으로 변경. 보유 주택 없이도 기본 프로파일, 단지 탐색, 대출/AI 분석이 가능하도록 UX 정리
