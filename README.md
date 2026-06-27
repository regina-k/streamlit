# AI 기반 부동산 분석 및 대출 제안 서비스

서울 아파트 단지·평형 데이터를 기반으로 미래 시세 상승률을 예측하고, 사용자의 자금 조건과 신한은행 주택담보대출 문서를 연결해 개인화된 매수·갈아타기 판단을 돕는 Streamlit 서비스입니다.

이 저장소에는 **앱 코드, ML/RAG 코드, 문서, RAG 원천 문서**가 포함됩니다. 대용량 데이터, 학습 모델, FAISS 벡터스토어는 Git에 올리지 않으므로 실행자는 별도 공유받은 산출물을 정해진 경로에 복원해야 합니다.

## 1. 서비스 개요와 사용자 흐름

서비스는 세 개의 탭으로 구성됩니다.

1. **내 투자 프로파일**
   - 가구 형태, 매수 목적, 가용 자본금, 연소득, 기존 대출을 입력합니다.
   - 선택 입력으로 보유 주택 현재 시세와 매수가를 입력하면 갈아타기 분석에 반영됩니다.

2. **단지 탐색**
   - 서울 아파트 단지를 지역, 단지명, 가격, 세대수, 평형 기준으로 필터링합니다.
   - 후보 단지에 대해 1년 AI 예측 상승률, 필요 자기자금, 자금 여유를 비교합니다.
   - 특정 단지·평형을 선택하면 탭3 분석 대상으로 전달됩니다.

3. **AI 종합 분석**
   - 선택 단지의 1년·3년·5년 상승률을 ML 모델로 예측합니다.
   - 대출 한도, LTV, DSR, 필요 자기자금, 잔여/부족 자금을 계산합니다.
   - 보유 주택이 있으면 `가용자금 + 보유주택 매도 후 자기자본` 기준으로 갈아타기 가능 여부를 판단합니다.
   - GPT-5.5 기반 RAG 어드바이저가 사용자 프로파일, 선택 단지, ML 예측, 대출 계산값, 신한은행 문서를 결합해 초개인화 상담 리포트를 생성합니다.

데이터나 모델 산출물이 없어 앱을 실행하기 어렵다면 [docs/capture](docs/capture) 폴더의 화면 캡쳐로 전체 서비스 흐름을 확인할 수 있습니다.

## 2. 프로젝트 구성

```text
streamlit/
├── app.py                         # Streamlit 진입점
├── config.py                      # 경로, 모델, API, 대출 규칙 설정
├── requirements.txt               # 앱 실행용 Python 의존성
├── AGENTS.md                      # 이 프로젝트 작업 규칙
├── modules/                       # 데이터 로딩, ML 추론, 대출 계산, RAG 상담 모듈
│   ├── ml_predictor.py
│   ├── loan_calculator.py
│   ├── rag_advisor.py
│   └── ...
├── scripts/                       # FAISS 생성, RAG 문서 수집/전처리 스크립트
├── data/                          # 로컬 데이터 위치. Git에는 구조만 유지
│   ├── apartment/                 # KB 아파트 원천/시계열 데이터
│   ├── additional/                # 학교, 역, 병원 등 입지 데이터
│   ├── integration/               # ML feature store
│   └── rag_docs/                  # RAG 원천 문서. Git 추적 대상
├── vector_store/                  # FAISS 산출물. Git 제외
├── ml_model/                      # ML 학습 코드, config, 실험 문서, 산출물 위치
├── docs/                          # PRD, 구현 현황, 제출용 캡쳐
└── tests/                         # 최소 회귀 테스트
```

Git 관리 원칙:

- `data/`, `vector_store/`, `ml_model/outputs/`의 대용량 산출물은 기본적으로 Git 제외입니다.
- `data/rag_docs/`의 RAG 원천 문서와 `ml_model/outputs/**/*.md` 형태의 실험 기록 문서는 추적 대상입니다.
- `.env`, 로그, 모델 바이너리, 예측 CSV, FAISS 인덱스는 커밋하지 않습니다.

## 3. 필수 로컬 데이터와 산출물

레포를 clone한 상태만으로는 실제 서비스가 완전히 실행되지 않습니다. 아래 파일을 정해진 위치에 복원해야 합니다.

| 구분 | 필수 경로 |
| --- | --- |
| 아파트 단지 데이터 | `data/apartment/kb_apt_seoul_full.csv` |
| 아파트 월별 시계열 | `data/apartment/kb_timeseries_seoul.csv` |
| 서비스용 최신 feature store | `data/integration/apartment_multihorizon_ver9_latest_features.csv` |
| 학습/평가용 feature store | `data/integration/apartment_multihorizon_ver9_stability_features.csv` |
| 최종 ML 모델 | `ml_model/outputs/models/ver16_service_multihorizon_base_model.pkl` |
| 최종 residual 보정 | `ml_model/outputs/calibration/ver16_hierarchical_apt_size_offsets.csv` |
| residual fallback 파일 | `ml_model/outputs/calibration/ver12c_recent3_horizon_complex_residual_offsets.csv` |
| residual group fallback 파일 | `ml_model/outputs/calibration/ver12d_group_residual_fallback_offsets.csv` |
| FAISS 인덱스 | `vector_store/shinhan_faiss/index.faiss`, `vector_store/shinhan_faiss/index.pkl` |

공유용 압축 파일을 받았다면 `streamlit/` 루트에 압축을 풀어 아래 구조가 바로 생기게 해야 합니다.

```text
streamlit/data/...
streamlit/ml_model/outputs/...
streamlit/vector_store/...
```

`data/`만 복원하면 ML 모델 파일과 FAISS 인덱스가 없어 일부 기능이 동작하지 않습니다.

## 4. ML 모델 설명

현재 서비스 모델은 `ver16_hierarchical_apt_size_residual`입니다.

핵심 구조:

- 기본 모델은 `ver9b` 단일 multi-horizon LightGBM입니다.
- 하나의 모델에 `horizon_months` 값을 입력해 12개월, 24개월, 36개월, 60개월 상승률을 예측합니다.
- 서비스 화면에서는 주로 12개월, 36개월, 60개월 결과를 1년·3년·5년 예측으로 보여줍니다.
- 추가 입지 feature로 학교, 역, 병원 접근성 및 반경별 시설 수를 사용합니다.
- 최종 ver16은 base 예측값에 계층형 residual calibration을 더합니다.

최종 fallback 순서:

```text
hier_apt_size_id+horizon
→ complex_id+horizon
→ group_gu_area
→ horizon_global
→ global
```

평가 방식:

- 랜덤 분할이 아니라 시간 순서 기반 holdout을 사용합니다.
- 각 horizon에서 라벨이 존재하는 가장 최근 5개월을 test로 두고, 그 직전 5개월을 validation으로 둡니다.
- validation 구간의 최근 3개월 residual을 이용해 보정값을 계산합니다.
- 60개월은 데이터 기간상 성숙한 test window가 부족하므로 inference는 가능하지만 `low confidence` 및 global fallback으로 처리합니다.

최종 test 성능:

| 지표 | 값 | 의미 |
| --- | ---: | --- |
| MAE | 5.0376%p | 평균 절대 상승률 오차 |
| RMSE | 8.1711%p | 큰 오차에 민감한 평균 오차 |
| R² | 0.7150 | 상승률 변동 설명력 |
| Spearman | 0.8715 | 상승률 순위/방향성 일치도 |
| P80 abs error | 8.6336%p | test 샘플 80%가 이 오차 이하 |
| P90 abs error | 13.6911%p | test 샘플 90%가 이 오차 이하 |

재현 명령:

```powershell
cd C:\Users\User\Desktop\final\streamlit\ml_model
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="src"
python -m ml_project.train --config config/config.yaml
```

관련 문서:

- [ml_model/README.md](ml_model/README.md)
- [ml_model/docs/model_version_performance_summary.md](ml_model/docs/model_version_performance_summary.md)
- [ml_model/outputs/performance/VERSION_LOG.md](ml_model/outputs/performance/VERSION_LOG.md)
- [ml_model/outputs/performance/ver06222256_ver16_hierarchical_apt_size_shrinkage.md](ml_model/outputs/performance/ver06222256_ver16_hierarchical_apt_size_shrinkage.md)

## 5. RAG·LLM 초개인화 상담 구조

RAG 어드바이저는 [modules/rag_advisor.py](modules/rag_advisor.py)에 구현되어 있습니다.

입력으로 들어가는 정보:

- 사용자 프로파일: 가구 형태, 매수 목적, 가용자금, 연소득, 기존 대출
- 보유 주택 정보: 현재 시세, 매수가, 매수 시점, 세대수, 준공월
- 선택 단지 정보: 단지명, 지역, 단지 ID, 평형 ID, KB 매매/전세 시세, 세대수, 준공월, 용적률, 건폐율
- ML 예측: 12/36/60개월 상승률, 추정 시세, P80 error band, confidence
- 대출 계산값: 한도, LTV, DSR, 필요 자기자금, 보유주택 매도 후 자기자본, 최종 잔여/부족
- 검색 조건: 지역, 키워드, 가격 범위, 세대수 범위, 정렬 기준

모델 설정:

- 기본 LLM: `gpt-5.5`
- 기본 reasoning: `low`
- 기본 verbosity: `low`
- 기본 RAG 검색 문서 수: `k=3`

이 설정은 `.env`에 넣지 않아도 [config.py](config.py) 기본값으로 동작합니다. `.env`에는 API key만 있다고 가정합니다.

```text
OPENAI_API_KEY=...
```

FAISS 생성:

```powershell
cd C:\Users\User\Desktop\final\streamlit
.\.venv\Scripts\Activate.ps1
python scripts\build_vectorstore.py
```

생성 결과:

```text
vector_store/shinhan_faiss/index.faiss
vector_store/shinhan_faiss/index.pkl
```

FAISS가 없으면 앱 전체가 중단되지는 않지만, 문서 기반 RAG 답변 대신 fallback 안내가 표시됩니다.

## 6. 설치와 실행

### 6.1 Python 환경 만들기

```powershell
cd C:\Users\User\Desktop\final\streamlit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 6.2 환경변수 설정

`streamlit/.env` 파일을 만들고 다음 값을 넣습니다.

```text
OPENAI_API_KEY=sk-...
```

데이터 재생성 스크립트를 실행할 경우에는 프로젝트 상위 `final/.env`에 공공데이터 API key가 필요할 수 있습니다.

```text
DATA_API_KEY=...
JUSO_API_KEY=...
```

일반 앱 실행만 할 때는 `streamlit/.env`의 `OPENAI_API_KEY`와 로컬 데이터/모델 산출물이 핵심입니다.

### 6.3 로컬에서 실행

```powershell
cd C:\Users\User\Desktop\final\streamlit
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

브라우저에서 접속:

```text
http://localhost:8501
```

같은 네트워크의 다른 사람이 접속해야 하면 다음처럼 실행합니다.

```powershell
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

실행 후 표시되는 Network URL 또는 PC의 내부 IP 주소로 접속합니다.

```text
http://<내부IP>:8501
```

## 7. 데이터가 없을 때 서비스 확인 방법

GitHub에는 대용량 데이터와 모델 산출물이 올라가지 않습니다. 데이터 복원이 어렵다면 먼저 캡쳐로 서비스 흐름을 확인합니다.

캡쳐 위치:

```text
docs/capture/
```

주요 화면:

- `01_profile_required_inputs.png`: 프로파일 필수 입력
- `02_profile_optional_home_inputs.png`: 보유 주택 선택 입력
- `03_profile_saved_success.png`: 프로파일 저장
- `04_search_filters_and_ai_results.png`: 단지 탐색 및 AI 후보 계산
- `05_selected_target_and_prediction.png`: 선택 단지와 ML 예측
- `06_ai_analysis_ml_prediction.png`: 탭3 가격 상승률 예측
- `07_ai_analysis_loan_products.png`: 대출 한도, DSR, 추천 상품
- `08_ai_advisor_response.png`: RAG·LLM 상담 결과
- `09_current_home_comparison_section.png`: 갈아타기 리포트

## 8. 개발 검증 명령

문법 검사:

```powershell
cd C:\Users\User\Desktop\final\streamlit
$files = @('app.py','config.py') + (Get-ChildItem modules -Filter *.py | ForEach-Object { $_.FullName }) + (Get-ChildItem scripts -Filter *.py | ForEach-Object { $_.FullName })
python -m py_compile @files
```

의존성 검사:

```powershell
python -m pip check
```

RAG 컨텍스트 회귀 테스트:

```powershell
python -m unittest tests.test_rag_advisor_context -v
```

Streamlit 실행 확인:

```powershell
streamlit run app.py
```

UI 변경 후에는 직접 다음 흐름을 확인합니다.

1. 탭1에서 프로파일 저장
2. 보유 주택 시세 입력
3. 탭2에서 단지 검색 및 선택
4. 탭3에서 ML 예측, 대출 분석, 갈아타기 리포트 확인
5. AI 분석 실행 후 개인화 정보가 답변에 반영되는지 확인

## 9. 참고 문서

- [AGENTS.md](AGENTS.md): 프로젝트 작업 규칙
- [docs/prd.md](docs/prd.md): 초기 PRD
- [docs/prd_refined.md](docs/prd_refined.md): 정리된 PRD
- [docs/feature_implementation_status.md](docs/feature_implementation_status.md): 기능 구현 현황
- [docs/ux_review_20260623.md](docs/ux_review_20260623.md): UI/UX 검토 기록
- [ml_model/docs/submission_02_model_system_evaluation.md](ml_model/docs/submission_02_model_system_evaluation.md): 제출용 모델 시스템 평가 설명
- [ml_model/docs/presentation_five_minute_script.md](ml_model/docs/presentation_five_minute_script.md): 발표 대본
- [ml_model/docs/presentation_expected_questions.md](ml_model/docs/presentation_expected_questions.md): 예상 질문

## 10. 운영상 주의사항

- 이 서비스는 의사결정 보조 도구입니다. 실제 대출 가능 여부와 금리는 신한은행 영업점 또는 공식 채널 확인이 필요합니다.
- ML 예측값은 확정 수익률이 아니라 경험적 오차 범위를 동반한 상승률 추정치입니다.
- 60개월 예측은 데이터 제약으로 낮은 신뢰도로 표시됩니다.
- 보유 주택을 입력한 갈아타기 분석은 `보유주택 현재시세 - 기존 보유 대출`을 매도 후 자기자본으로 봅니다. 실제 세금, 중개보수, 상환 조건, 신용대출 분리 여부는 별도 검토가 필요합니다.
- `.env`, 데이터, 모델 파일, FAISS 인덱스, 로그는 커밋하지 않습니다.
