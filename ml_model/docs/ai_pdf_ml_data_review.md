# AI.pdf ML·데이터 내용 검토 및 수정 지시서

## 검토 범위와 기준

- 대상: `ml_model/docs/AI.pdf` 전체 10페이지
- 범위: 아파트 상승률 예측 ML, 학습 데이터, POI 결합, 모델 평가, 앱의 ML 연결
- 제외: LLM·RAG의 구현과 성능
- 페이지 표기: `PDF 페이지 / 자료 내부 SLIDE 번호`

판단 기준은 최종 설정 `config/config.yaml`, base 설정 `config/config_ver9b_multihorizon_calibrated.yaml`, 최종 보고서 `ver06222256_ver16_hierarchical_apt_size_shrinkage.md`, `modules/ml_predictor.py`, 실제 데이터 생성 스크립트다.

## 페이지별 관련 내용 구분

| PDF 페이지 | 내부 표기 | ML·데이터 관련 내용 | 검토 결과 |
|---:|---|---|---|
| 1 | 표지 | LightGBM Multi-Horizon 가격 예측 | 대체로 일치, 표현 보완 권장 |
| 2 | SLIDE 1 | 사용자 프로필과 시스템 입력 | ML 입력과 대출 입력의 역할 구분 필요 |
| 3 | SLIDE 2 | ML 기반 DSR·상환 위험·NPL 방어 | 실제 구현과 불일치 |
| 4 | SLIDE 3 | 아파트·시계열·POI 데이터 구축 | 수집 방식과 기술 스택 다수 불일치 |
| 5 | SLIDE 4 | Multi-Horizon LightGBM과 feature | 최종 모델 구조와 feature 역할 불일치 |
| 6 | SLIDE 5 | 성능지표와 residual calibration | 단위·보정 방식·신뢰구간 표현 수정 필요 |
| 7 | SLIDE 6 | FAQ RAG | 검토 제외 |
| 8 | SLIDE 7 | Streamlit에서 ML 사용 | 탭 순서와 후보 예측 범위 불일치 |
| 9 | SLIDE 8 | 이상치·데이터 한계 대응 | `RobustScaler` 등 미구현 기술 기재 |
| 10 | SLIDE 9 | 최종 ML 구조·R²·60개월 | 모델 명칭과 지표 해석 보완 필요 |

## 핵심 수정 사항

1. 최종 모델은 **LightGBM ver16**이 아니다. **ver9b single multi-horizon LightGBM + ver16 hierarchical residual post-calibration**이다.
2. `apt_size_id`, `complex_id`는 base LightGBM 입력 feature가 아니라 residual offset을 찾는 식별 키다. `gu_area`라는 원시 feature도 없으며, `gu + area_bin` 조합이 fallback 보정에 사용된다.
3. 최종 pipeline에는 `RobustScaler`가 없다. LightGBM에는 별도 scaling을 적용하지 않았고, residual calibration을 이상치 제거라고 설명해서도 안 된다.
4. MAE와 RMSE 단위는 `%`가 아니라 상승률의 `%p`다. R²와 Spearman에는 단위가 없다.
5. P80 8.6336%p는 test 절대오차의 80분위수다. 정식 통계적 신뢰구간이나 “금융권 수준 정밀도”로 표현할 근거는 없다.
6. 60개월은 inference가 가능하지만 성숙한 test window가 없어 `low confidence`다.
7. 성장률 모델은 DSR, 상환 위험, 부실채권 발생 가능성을 예측하지 않는다. 대출 한도·LTV·DSR은 `loan_calculator.py`의 규칙과 산식으로 계산한다.

## 페이지별 수정 지시

### PDF 1페이지 / 표지

**현재 표현**

`KB 부동산 시세 엔진 · LightGBM Multi-Horizon 가격 예측`

**판단**

큰 방향은 맞지만 모델이 직접 예측하는 값은 미래 가격 자체가 아니라 현재 KB 매매시세 대비 미래 KB 매매시세의 상승률이다. 추정 미래 시세는 현재 시세에 예측 상승률을 적용해 계산한다.

**권장 교체 문구**

> KB 시세 기반 Multi-Horizon 상승률 예측 · 계층형 residual 보정

### PDF 2페이지 / SLIDE 1

**문제점**

가구 형태, 매매 목적, 재무 상태, 선호 평형이 모두 하나의 “초개인화 엔진” 입력인 것처럼 보인다. 이 중 사용자 프로필은 대출·자금 분석에 사용되며, ML 상승률 모델은 단지·평형·시세·입지 feature를 사용한다. 실거주/투자 목적이나 소득은 상승률 모델 feature가 아니다.

또한 `4대 투자 유형`은 실제로 네 가지 투자 유형이 아니라 네 종류의 입력 항목을 뜻하므로 `개인화 입력 항목`으로 고친다.

**수정 지시**

입력 구조를 다음 두 갈래로 분리해 표현한다.

> 사용자 프로필: 가구 형태·소득·가용 자금·기존 대출 → 대출 한도·DSR·필요 자기자금 계산  
> 아파트 정보: 단지·평형·KB 시세·입지 → 1년·3년·5년 상승률 예측  
> 두 결과를 화면에서 결합해 의사결정을 지원

### PDF 3페이지 / SLIDE 2

**현재 오류**

`DSR과 상환 위험도를 머신러닝으로 정밀 평가하여 NPL 발생 리스크를 방어`

현재 ML은 아파트 KB 시세 상승률만 예측한다. 신용 위험, 상환 가능성, 연체, NPL을 학습하거나 평가한 모델과 관련 라벨은 없다. DSR은 소득, 대출액, 금리, 기간을 사용한 산식 기반 추정이다.

**필수 교체 문구**

> ML은 선택 단지·평형의 예상 시세 상승률과 경험적 오차 범위를 제공한다. 대출 한도·LTV·DSR은 규칙 기반 산식으로 계산하며, 두 결과를 함께 보여줘 매수 자금 부담과 가격 변동 위험을 점검한다.

`NPL 선제적 방어`, `상환 위험도 ML 정밀 평가` 문구는 삭제한다. 실제 신용평가 모델이 추가되기 전에는 여신 리스크 모델처럼 발표하면 안 된다.

### PDF 4페이지 / SLIDE 3

**현재 오류**

- 학습 데이터가 `KB API`에서 직접 가동된다고 단정한다.
- POI를 `공공데이터포털 API + BeautifulSoup 웹 스크래핑`으로 수집했다고 설명한다.
- 기술 스택에 `playwright`가 포함돼 있다.
- 가상 고객 500건이 상승률 학습 데이터에 사용된 것처럼 배치돼 있다.

**실제 구현**

- 아파트 학습 데이터: `kb_apt_seoul_full.csv`, `kb_timeseries_seoul.csv` 결합
- 학교: 한국교육시설안전원 CSV
- 역: 전체 도시철도 역사정보 XLSX
- 병원: 건강보험심사평가원 병원정보서비스 OpenAPI
- 좌표: 원천 WGS84 위도·경도 사용. 도로명주소 좌표 변환이나 웹 스크래핑 미사용
- 거리: 서울권 평면 좌표로 근사한 뒤 `KDTree`로 직선거리와 반경 내 개수 계산
- Synthetic persona: 상승률 모델 학습·평가에 사용하지 않으며, 저장소에서 500건 데이터 근거도 확인되지 않음

**슬라이드 교체 문구**

> 단지·평형 메타 CSV와 월별 KB 시계열 CSV를 결합해 월 단위 학습 테이블을 구축했다. 학교 CSV, 도시철도 역사 XLSX, HIRA 병원 OpenAPI의 WGS84 좌표를 통합하고, KDTree 기반 직선거리·반경 내 시설 수 feature를 단지 좌표에 결합했다.

기술 스택은 `Pandas · HIRA OpenAPI · WGS84 · scikit-learn KDTree`로 고친다. `BeautifulSoup`, `playwright`, `Synthetic Data 500건`은 이 페이지에서 삭제한다. `가동`은 `가공`으로 수정한다.

**Synthetic Data 500건 대체 숫자**

현재 로컬 데이터 파일을 직접 집계한 결과는 다음과 같다.

| 강조 항목 | 수치 | 의미 |
|---|---:|---|
| Multi-horizon 라벨 데이터 | 2,026,935행 | 단지·평형·기준월·예측기간 단위 모델링 데이터 |
| 모델링 대상 단지 | 6,297개 | 라벨 데이터에 포함된 고유 단지 |
| 단지·평형 조합 | 27,902개 | 라벨 데이터의 고유 `apt_size_id` |
| 원천 월별 시계열 | 2,657,585행 | 2021-06~2026-06 KB 시계열 관측치 |
| 서울 소재 POI | 1,785개 | 학교 1,318개, 역 405개, 병원 62개 |
| 최종 모델 입력 feature | 55개 | 최종 ver9b base config의 활성 feature 수 |

서로 단위가 다른 단지 수, 시계열 행 수, POI 수를 모두 더해 하나의 `총 N건`으로 표현하지 않는다. 가장 큰 대표 숫자는 **`약 203만 건의 multi-horizon 모델링 데이터`**로 제시하고, 단지·평형 및 POI 수를 별도 보조 지표로 둔다.

발표자료의 숫자 카드 권장안:

> 약 203만 건 · Multi-Horizon 모델링 데이터  
> 6,297개 · 모델링 대상 아파트 단지  
> 27,902개 · 단지·평형 예측 단위  
> 1,785개 · 서울 학교·역·종합병원 POI

### PDF 5페이지 / SLIDE 4

**현재 오류**

- `LightGBM ver16 알고리즘`이라고 표기했다.
- `apt_size_id`, `complex_id`, `gu_area`를 base model feature처럼 나열했다.
- POI를 하나의 `입지 가중치 수치`로 설명했다.
- 네 기간을 한 번에 출력하는 multi-output 모델처럼 `동시 추론`이라고 표현했다.

**실제 구조**

> ver9b single multi-horizon LightGBM base  
> + ver16 hierarchical apt-size residual post-calibration

동일한 LightGBM에 `horizon_months`를 넣어 기간별로 호출한다. 서비스 함수가 12·24·36·60개월 결과를 묶어 반환할 수 있지만, 하나의 multi-output 벡터를 직접 예측하는 구조는 아니다.

**Feature Set 교체안**

- 예측 기간: `horizon_months`
- KB 시장정보: 매매시세, 전세시세, 전세가율, 시세갭
- 단지·평형 메타: 구, 면적, 연식, 세대수, 용적률, 건폐율
- POI 접근성: 최근접 역·학교·병원 거리와 반경별 시설 수
- 안정 파생 feature: 평당가, 단지 내 면적·가격 순위, 구 대비 프리미엄

하단에 다음을 별도로 표시한다.

> 보정 식별 키: `apt_size_id + horizon` → `complex_id + horizon` → `gu + area_bin` → horizon global → global

`apt_size_id`를 “평형 크기”라고 설명하지 말고 “단지·평형 식별자”라고 쓴다. `POI 입지 가중치`는 `POI 거리·개수 feature`로 바꾼다.

### PDF 6페이지 / SLIDE 5

**지표 표기 수정**

| 현재 | 수정 |
|---|---|
| MAE `5.04%` | MAE `5.0376%p` |
| RMSE `8.17%` | RMSE `8.1711%p` |
| R² `0.715`, 모델 신뢰도 | R² `0.7150`, test 분산 설명 지표 |
| Spearman `0.872`, 압도적 신뢰도 | Spearman `0.8715`, 순위 상관 |

`압도적 신뢰도`, `금융권 수준의 정밀도 확보`, `오차 극최소화`는 근거가 없는 과장 표현이므로 삭제한다.

**Calibration 설명 교체안**

> LightGBM이 먼저 기본 상승률을 예측한다. 그다음 최근 검증 데이터에서 특정 단지·평형을 반복적으로 높게 또는 낮게 예측했던 오차를 확인해 예측값을 한 번 더 보정한다. 해당 평형의 데이터가 적으면 같은 단지, 같은 구의 비슷한 면적, 같은 예측기간의 평균 오차를 참고해 과도한 보정을 막는다.

쉽게 말하면 **“기본 예측 + 과거에 반복된 오차 보정”** 구조다. 보정값은 최근 3개 validation 월을 이용해 미리 계산하고 CSV에 저장한다. 사용자가 예측을 요청할 때 모델을 다시 학습하는 것이 아니라, 저장된 보정값을 조회해 기본 예측에 더한다.

**P80 설명 교체안**

> 과거 test 결과에서 전체 예측 오차의 80%는 8.6336%p 이내였고, 90%는 13.6911%p 이내였다. 이 값을 이용해 사용자가 예측 결과가 어느 정도 빗나갈 수 있는지 함께 확인하도록 한다.

예를 들어 예상 상승률이 10%이고 적용되는 P80 오차가 8%p라면, 과거 오차를 참고한 범위를 약 2%~18%로 표시할 수 있다. 이는 “실제 값이 80% 확률로 반드시 이 안에 있다”는 통계적 신뢰구간이 아니다. 따라서 화면과 발표에서는 `신뢰 구간`보다 **`과거 test 오차 기준 예상 범위`** 또는 **`경험적 오차 범위`**라고 표현한다. 실제 서비스에서는 예측기간과 보정 방식에 맞는 P80/P90 값을 사용한다.

### PDF 7페이지 / SLIDE 6

LLM·RAG 페이지이므로 이번 검토에서 제외한다.

### PDF 8페이지 / SLIDE 7

**현재 구현과 다른 부분**

- 실제 탭 순서는 `내 투자 프로파일 → 단지 탐색 → AI 종합 분석`이다.
- 단지 탐색에서 전체 후보의 상승률을 자동 일괄 계산하지 않는다.
- 필터 결과가 1,500개 이하일 때 버튼이 활성화되고, 현재 코드는 상위 5개 후보의 1년 상승률을 계산한다.
- 선택한 단지·평형 카드에서는 1년·3년·5년 예측을 제공한다.

**교체안**

> Tab 1 내 투자 프로파일: 가구·자산·소득·기존 대출 입력, DSR 미리보기  
> Tab 2 단지 탐색: 조건 필터링, 상위 5개 후보 1년 상승률 계산 및 정렬, 선택 단지 1·3·5년 예측  
> Tab 3 AI 종합 분석: 상승률·추정 시세와 대출·자금 분석 결과 종합

후보 수나 계산 범위를 확장하기 전에는 `서울 전체 후보 일괄 정렬 엔진`이라고 표현하지 않는다.

### PDF 9페이지 / SLIDE 8

**현재 오류**

- 최종 pipeline에 없는 `RobustScaler` 적용을 주장한다.
- residual offset을 이상치 억제 기법으로 설명한다.
- `대단지 아파트 중심 필터링`을 데이터 무결성 장치로 설명한다.

실제 원천 데이터 자체가 아파트 단지·평형 범위이며, 최종 config에는 대단지 세대수 필터나 RobustScaler가 없다. residual calibration은 단지·평형별 반복 편향을 보정하는 절차이지 가격 폭등·폭락 이상치를 제거하는 기법이 아니다.

**교체안**

> 분석 대상 명확화: 서울 아파트의 단지·평형별 KB 시세만 사용하고, 빌라·다세대는 분석 대상에서 제외  
> 시간 순서에 따른 검증: 과거 데이터로 학습하고, 그다음 5개월로 모델을 조정한 뒤, 가장 최근 5개월로 최종 성능 확인  
> 과도한 보정 방지: 특정 평형의 데이터가 적으면 같은 단지나 비슷한 지역·면적의 평균 오차를 참고  
> 예측 한계 표시: 과거 test 오차를 기준으로 예상 오차 범위를 함께 제공하고, 검증 데이터가 부족한 5년 예측은 낮은 신뢰도로 표시

빌라·다세대는 “이상치라 제거”한 것이 아니라 현재 프로젝트의 데이터 범위 밖이라고 표현한다.

### PDF 10페이지 / SLIDE 9

**현재 오류와 보완점**

- `LightGBM ver16`은 모델 구조를 잘못 합친 표현이다.
- R² 0.715를 단독으로 `모델 신뢰도`라 부르는 것은 부정확하다.
- `60M 장기 추론`에 검증 한계가 표시되지 않았다.
- `Synthetic Data 500건`은 상승률 모델 성과가 아니다.

**교체 문구**

> Pandas 데이터 pipeline + ver9b single multi-horizon LightGBM + ver16 hierarchical residual calibration

성과 박스는 다음처럼 바꾼다.

> Test MAE 5.0376%p  
> Test RMSE 8.1711%p  
> R² 0.7150  
> Spearman 0.8715  
> ver9b 대비 MAE 38.8% 개선

60개월 박스에는 반드시 다음 주석을 붙인다.

> 60개월 inference 지원 · 성숙한 test window 미확보로 low confidence

`R² 0.715 모델 신뢰도`는 `R² 0.715 test 설명력`으로 바꾼다. `Synthetic Data 500건` 박스는 **`약 203만 건 Multi-Horizon 모델링 데이터`** 또는 **`27,902개 단지·평형 예측 단위`**로 교체한다.

## 발표자료 수정 우선순위

### 반드시 수정

1. 3페이지의 DSR·상환 위험·NPL ML 주장
2. 4페이지의 BeautifulSoup·Playwright·Synthetic Data 수집 설명
3. 5페이지의 LightGBM ver16 및 ID feature 표기
4. 6페이지의 `%` 단위, 신뢰구간, 과장 표현
5. 9페이지의 RobustScaler 주장
6. 10페이지의 R² 신뢰도·60개월 무조건적 성과 표현

### 권장 수정

1. 1페이지의 가격 예측을 상승률 예측으로 구체화
2. 2페이지에서 사용자 프로필과 ML feature 흐름 분리
3. 8페이지 탭 순서와 상위 5개 후보 계산 범위 반영

## 최종 발표용 한 문장

> 서울 아파트 단지·평형의 KB 시세와 입지 feature를 사용해 하나의 LightGBM으로 여러 예측 기간의 상승률을 추정하고, validation에서 확인한 단지·평형별 반복 오차를 계층형 residual calibration으로 보정한 모델이다.

## 근거 파일

- `ml_model/config/config.yaml`
- `ml_model/config/config_ver9b_multihorizon_calibrated.yaml`
- `ml_model/outputs/performance/ver06222256_ver16_hierarchical_apt_size_shrinkage.md`
- `ml_model/docs/model_version_performance_summary.md`
- `modules/ml_predictor.py`
- `modules/loan_calculator.py`
- `data/apartment/preprocessed/README.md`
- `data/additional/preprocessed/README.md`
- `data/integration/README.md`
- `../scripts/preprocess_locations.py`
- `../scripts/build_integration_features.py`
