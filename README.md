# AI 부동산 분석 및 대출 제안 서비스

KB 아파트 데이터, ML 상승률 예측 모델, 신한은행 주택담보대출 RAG 문서를 연결한 Streamlit 서비스이다. 사용자는 보유 자금과 조건을 입력하고 아파트 후보, 1년/3년/5년 상승률 예측, 대출 한도, 필요 자기자금, AI 종합 분석을 확인한다.

## 1. 프로젝트 구조

```text
streamlit/
├── app.py                         # Streamlit 진입점
├── config.py                      # 공통 경로와 상수
├── requirements.txt               # 버전 고정 Python 의존성
├── .env                           # 로컬 환경변수. Git 제외
├── modules/                       # 데이터 로딩, 대출 계산, ML/RAG 모듈
├── data/
│   ├── apartment/                 # KB 아파트 원천/전처리 데이터
│   ├── additional/                # 학교, 역, 병원 등 외부 입지 데이터
│   ├── integration/               # 아파트 + 입지 결합 ML feature store
│   └── rag_docs/                  # RAG 원천 문서. Git 추적
├── docs/                          # PRD와 기능 구현 현황
├── scripts/                       # RAG 수집/벡터스토어 생성 스크립트
├── ml_model/                      # 학습 코드, config, 실험 문서, 모델 산출물
└── vector_store/                  # FAISS 산출물. Git 제외
```

## 2. 설치

Windows PowerShell 기준으로 `streamlit/` 폴더에서 실행한다.

```powershell
cd C:\Users\User\Desktop\final\streamlit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`.env`에는 최소한 아래 값이 필요하다. RAG 벡터스토어 생성과 AI 답변에 사용한다.

```text
OPENAI_API_KEY=...
```

## 3. 로컬 데이터와 산출물

대용량 데이터, 모델 파일, FAISS 인덱스는 Git에 올리지 않는다. 현재 앱 실행에 필요한 핵심 파일은 다음과 같다.

```text
data/apartment/kb_apt_seoul_full.csv
data/apartment/kb_timeseries_seoul.csv
data/integration/apartment_multihorizon_ver9_latest_features.csv
ml_model/outputs/models/ver16_service_multihorizon_base_model.pkl
```

ML feature store를 다시 만들거나 확장하려면 아래 입지 데이터도 필요하다.

```text
data/additional/preprocessed/school.csv
data/additional/preprocessed/station.csv
data/additional/preprocessed/hospital.csv
```

`data/additional/`의 원천 파일은 학교 위치 CSV, 도시철도 역사 XLSX, 병원정보 API 활용 문서이다. `data/additional/preprocessed/README.md`에 각 전처리 CSV의 컬럼 설명이 있다. `data/integration/`은 아파트 데이터와 입지 피처를 결합한 학습/추론용 feature store이다.

`data/rag_docs/`의 Markdown/JSON 원천 문서는 Git 추적 대상이다. `vector_store/`의 FAISS 인덱스는 재생성 가능한 산출물이므로 Git에서 제외한다.

## 4. FAISS 벡터스토어 생성

RAG 답변을 사용하려면 최초 실행 전 한 번 생성한다.

```powershell
cd C:\Users\User\Desktop\final\streamlit
.\.venv\Scripts\Activate.ps1
python scripts\build_vectorstore.py
```

성공하면 아래 파일이 생성된다.

```text
vector_store/shinhan_faiss/index.faiss
vector_store/shinhan_faiss/index.pkl
```

FAISS가 없어도 앱은 실행되지만, AI 분석 영역은 벡터스토어 생성 안내를 표시한다.

## 5. Streamlit 실행

```powershell
cd C:\Users\User\Desktop\final\streamlit
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

브라우저가 자동으로 열리지 않으면 터미널에 표시되는 주소로 접속한다.

```text
http://localhost:8501
```

## 6. 동작 확인 체크리스트

- 사이드바에서 `OPENAI_API_KEY` 감지 여부를 확인한다.
- 아파트 검색 탭에서 지역, 가격대, 면적, 평형 필터가 동작하는지 확인한다.
- 후보 단지를 선택하면 대출 한도, LTV, 필요 자기자금이 표시되는지 확인한다.
- AI 종합 분석 탭에서 1년/3년/5년 ML 예측 카드가 표시되는지 확인한다.
- FAISS 생성 후 AI 분석 실행 버튼을 눌러 RAG 답변이 생성되는지 확인한다.

## 7. 개발 검증 명령

문법 검증:

```powershell
$files = @('app.py','config.py') + (Get-ChildItem modules -Filter *.py | ForEach-Object { $_.FullName }) + (Get-ChildItem scripts -Filter *.py | ForEach-Object { $_.FullName })
python -m py_compile @files
```

의존성 충돌 검증:

```powershell
python -m pip check
```

Streamlit 초기 렌더 검증:

```powershell
python - <<'PY'
from streamlit.testing.v1 import AppTest
app = AppTest.from_file("app.py", default_timeout=90)
app.run()
print("exceptions:", len(app.exception))
PY
```

## 8. 참고 문서

- `docs/prd.md`: 원본 기능 메모
- `docs/prd_refined.md`: 정리된 PRD
- `docs/feature_implementation_status.md`: 기능별 구현 현황표
- `data/additional/preprocessed/README.md`: 입지 데이터 컬럼 설명
- `data/apartment/preprocessed/README.md`: 아파트 전처리 데이터 설명
- `data/integration/README.md`: 통합 feature store 설명
- `ml_model/docs/model_version_performance_summary.md`: ML 버전별 성능 요약
- `ml_model/outputs/performance/VERSION_LOG.md`: 전체 실험 버전 로그
