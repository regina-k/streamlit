# AI 부동산 분석 및 대출 제안 서비스

KB 아파트 데이터, 입지 피처, LightGBM 상승률 예측 모델, 신한은행 주택담보대출 RAG 문서를 연결한 Streamlit 서비스이다. 사용자는 보유 자금과 조건을 입력하고 아파트 후보, 1년/3년/5년 상승률 예측, 대출 한도, 필요 자기자금, AI 종합 분석을 확인한다.

## 1. 프로젝트 구조

```text
final/
├── scripts/                       # 아파트/additional/integration 데이터와 ML 산출물 재현 스크립트
└── streamlit/
    ├── app.py                     # Streamlit 진입점
    ├── config.py                  # 앱 공통 경로와 상수
    ├── requirements.txt           # 버전 고정 Python 의존성
    ├── .env                       # 앱/RAG용 로컬 환경변수. Git 제외
    ├── modules/                   # 데이터 로딩, 대출 계산, ML/RAG 모듈
    ├── data/
    │   ├── apartment/             # KB 아파트 원천/전처리 데이터
    │   ├── additional/            # 학교, 역, 병원 원천/전처리 입지 데이터
    │   ├── integration/           # 아파트 + additional 결합 ML feature store
    │   └── rag_docs/              # RAG 원천 문서. Git 추적
    ├── docs/                      # PRD와 기능 구현 현황
    ├── scripts/                   # RAG 문서 수집/FAISS 생성 스크립트
    ├── ml_model/                  # 학습 코드, config, 실험 문서, 모델 산출물
    └── vector_store/              # FAISS 산출물. Git 제외
```

## 2. 설치

앱 실행은 `streamlit/` 폴더를 기준으로 한다.

```powershell
cd C:\Users\User\Desktop\final\streamlit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`streamlit/.env`에는 앱과 RAG 답변에 필요한 값을 둔다.

```text
OPENAI_API_KEY=...
```

`final/.env`에는 데이터 전처리 API 호출에 필요한 값을 둔다.

```text
DATA_API_KEY=...
JUSO_API_KEY=...
```

현재 `preprocess_locations.py`는 병원정보서비스 호출에 `DATA_API_KEY`를 사용한다. `JUSO_API_KEY`는 주소/좌표 API 확장 시 사용할 수 있도록 보관한다.

## 3. 로컬 데이터

대용량 데이터, 모델 파일, FAISS 인덱스는 Git에 올리지 않는다. 앱 실행에 필요한 핵심 파일은 다음과 같다.

```text
streamlit/data/apartment/kb_apt_seoul_full.csv
streamlit/data/apartment/kb_timeseries_seoul.csv
streamlit/data/integration/apartment_multihorizon_ver9_latest_features.csv
streamlit/ml_model/outputs/models/ver16_service_multihorizon_base_model.pkl
```

`streamlit/data/additional/`은 입지 피처 생성에 필요한 외부 데이터 영역이다. 원천 파일과 전처리 파일은 아래처럼 관리한다.

```text
streamlit/data/additional/한국교육시설안전원_초중등학교위치_20260320.csv
streamlit/data/additional/전체_도시철도역사정보_20260228.xlsx
streamlit/data/additional/OpenAPI활용가이드_건강보험심사평가원(병원정보서비스)_210616.docx
streamlit/data/additional/preprocessed/school.csv
streamlit/data/additional/preprocessed/station.csv
streamlit/data/additional/preprocessed/hospital.csv
streamlit/data/additional/preprocessed/README.md
```

`school.csv`, `station.csv`, `hospital.csv`는 모두 WGS84 위도/경도(`lat`, `lon`) 기준이며, `streamlit/data/integration/`의 통합 feature store를 만들 때 사용한다.

## 4. 데이터 재생성

아파트, additional, integration 데이터 재생성은 상위 루트 `final/`에서 실행한다.

```powershell
cd C:\Users\User\Desktop\final
python .\scripts\preprocess_main.py
python .\scripts\preprocess_locations.py
python .\scripts\build_integration_features.py
python .\scripts\build_ver6_features.py
python .\scripts\build_ver9_multihorizon_features.py
```

최종 앱 추론용 최신 feature store는 학습된 ver9b 계열 모델 파일이 있어야 만들 수 있다.

```powershell
python .\scripts\build_multihorizon_inference_store.py
```

주요 산출물은 다음 위치에 생성된다.

```text
streamlit/data/apartment/preprocessed/apartment.csv
streamlit/data/apartment/preprocessed/apartment_multihorizon.csv
streamlit/data/additional/preprocessed/school.csv
streamlit/data/additional/preprocessed/station.csv
streamlit/data/additional/preprocessed/hospital.csv
streamlit/data/integration/apartment_multihorizon_poi.csv
streamlit/data/integration/apartment_multihorizon_ver6_individual.csv
streamlit/data/integration/apartment_multihorizon_ver9_stability_features.csv
streamlit/data/integration/apartment_multihorizon_ver9_latest_features.csv
```

## 5. ML 모델 재현

최종 서비스 후보는 ver16이다. 기본 `config/config.yaml`이 ver16 재현용 pipeline config로 맞춰져 있다.

```powershell
cd C:\Users\User\Desktop\final\streamlit\ml_model
$env:PYTHONPATH="src"
python -m ml_project.train --config config/config.yaml
```

학습 결과와 실험 기록은 `streamlit/ml_model/outputs/`에 생성된다. Markdown 성능 문서는 Git 추적 대상이고, 모델/예측/로그 산출물은 Git 제외 대상이다.

## 6. FAISS 벡터스토어 생성

RAG 답변을 사용하려면 최초 실행 전 `streamlit/`에서 FAISS를 생성한다.

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

FAISS가 없어도 앱은 실행되지만, AI 분석 영역은 벡터스토어 생성 안내 또는 fallback 답변을 표시한다.

## 7. Streamlit 실행

```powershell
cd C:\Users\User\Desktop\final\streamlit
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

브라우저가 자동으로 열리지 않으면 터미널에 표시되는 주소로 접속한다.

```text
http://localhost:8501
```

## 8. 동작 확인 체크리스트

- 사이드바에서 `OPENAI_API_KEY` 감지 여부를 확인한다.
- 아파트 검색 탭에서 지역, 단지명, 가격대, 면적, 평형 필터가 동작하는지 확인한다.
- 후보 단지를 선택하면 대출 한도, LTV, 필요 자기자금이 표시되는지 확인한다.
- AI 종합 분석 탭에서 12/24/36/60개월 ML 예측 카드가 표시되는지 확인한다.
- FAISS 생성 후 AI 분석 실행 버튼을 눌러 RAG 답변이 생성되는지 확인한다.

## 9. 개발 검증 명령

문법 검증:

```powershell
cd C:\Users\User\Desktop\final\streamlit
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

## 10. 참고 문서

- `AGENTS.md`: 이 프로젝트를 다루는 에이전트 작업 규칙
- `docs/prd.md`: 원본 기능 메모
- `docs/prd_refined.md`: 정리된 PRD
- `docs/feature_implementation_status.md`: 기능별 구현 현황표
- `data/additional/preprocessed/README.md`: 학교/역/병원 입지 데이터 컬럼 설명
- `data/apartment/preprocessed/README.md`: 아파트 전처리 데이터 설명
- `data/integration/README.md`: 통합 feature store 설명
- `ml_model/README.md`: ML 학습/추론 재현 안내
- `ml_model/docs/model_version_performance_summary.md`: ML 버전별 성능 요약
- `ml_model/outputs/performance/VERSION_LOG.md`: 전체 실험 버전 로그
