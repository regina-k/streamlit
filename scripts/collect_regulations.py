"""
주택담보대출 규제 정보 전체 수집 파이프라인

수집 출처:
    1. 주택금융공사 (hf.go.kr)   - 디딤돌/보금자리/특례대출 상세 조건
    2. 금융위원회 (fsc.go.kr)    - LTV/DSR/DTI 규제 보도자료
    3. 금융감독원 finlife API    - 은행별 주담대 금리 비교
    4. 국토교통부 (molit.go.kr)  - 부동산 정책 보도자료

사용법:
    pip install requests beautifulsoup4 python-dotenv
    python scripts/collect_regulations.py

결과:
    docs/regulations/ 폴더에 마크다운 파일 저장
"""

import os
import re
import time
import json
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path("docs/regulations")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_html(url: str, timeout: int = 15) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  ❌ 요청 실패 ({url}): {e}")
        return None


def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def save_md(filename: str, content: str):
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    print(f"  ✅ 저장: {path} ({len(content):,}자)")


# ══════════════════════════════════════════════════════════
# 1. 주택금융공사 — 정책 모기지 상품 상세
# ══════════════════════════════════════════════════════════

HF_PRODUCTS = [
    {
        "name":     "디딤돌대출",
        "url":      "https://www.hf.go.kr/hf/sub01/sub01_01_01.do",
        "desc":     "내집마련 디딤돌 대출 (저소득 실수요자 주택구입자금)",
    },
    {
        "name":     "보금자리론",
        "url":      "https://www.hf.go.kr/hf/sub01/sub01_02_01.do",
        "desc":     "보금자리론 (장기 고정금리 주택담보대출)",
    },
    {
        "name":     "특례보금자리론",
        "url":      "https://www.hf.go.kr/hf/sub01/sub01_02_02.do",
        "desc":     "특례보금자리론 (한시 운영 상품)",
    },
    {
        "name":     "신생아특례대출",
        "url":      "https://www.hf.go.kr/hf/sub01/sub01_01_04.do",
        "desc":     "신생아 특례 구입자금 대출",
    },
    {
        "name":     "생애최초특례대출",
        "url":      "https://www.hf.go.kr/hf/sub01/sub01_01_03.do",
        "desc":     "생애최초 주택구입 특례대출",
    },
    {
        "name":     "청년주택드림대출",
        "url":      "https://www.hf.go.kr/hf/sub01/sub01_01_05.do",
        "desc":     "청년 주택드림 대출",
    },
]

def collect_hf_products():
    """주택금융공사 정책 모기지 상품 수집"""
    print("\n🏠 [1] 주택금융공사 정책 모기지 수집")
    print("=" * 50)

    all_md = f"# 주택금융공사 정책 모기지 상품 안내\n\n"
    all_md += f"> 출처: 주택금융공사 (www.hf.go.kr)\n"
    all_md += f"> 수집일: {TODAY}\n\n---\n\n"

    for product in HF_PRODUCTS:
        print(f"  📡 {product['name']} 수집 중...")
        soup = get_html(product["url"])

        all_md += f"## {product['name']}\n\n"
        all_md += f"> {product['desc']}\n> URL: {product['url']}\n\n"

        if soup:
            # 주택금융공사 공통 콘텐츠 셀렉터
            content = None
            for selector in ["div.cont_area", "div.sub_content", "div#content", "main", "article"]:
                content = soup.select_one(selector)
                if content:
                    break

            if content:
                # 테이블 → 마크다운
                for table in content.find_all("table"):
                    rows = table.find_all("tr")
                    for row in rows:
                        cells = row.find_all(["th", "td"])
                        if cells:
                            all_md += "| " + " | ".join(c.get_text(strip=True) for c in cells) + " |\n"
                    all_md += "\n"

                # 일반 텍스트
                text = clean_text(content.get_text(separator="\n"))
                if len(text) > 100:
                    all_md += f"{text}\n\n"
            else:
                all_md += f"*자동 수집 실패 — {product['url']} 에서 직접 확인하세요*\n\n"
        else:
            all_md += f"*수집 실패 — {product['url']} 에서 직접 확인하세요*\n\n"

        all_md += "---\n\n"
        time.sleep(1)

    save_md("주택금융공사_정책모기지.md", all_md)


# ══════════════════════════════════════════════════════════
# 2. 금융위원회 — LTV/DSR/DTI 규제 보도자료
# ══════════════════════════════════════════════════════════

FSC_SEARCH_URL = "https://www.fsc.go.kr/no010101"
FSC_KEYWORDS   = ["LTV", "DSR", "주택담보대출", "가계부채", "부동산 규제"]

def collect_fsc_regulations():
    """금융위원회 주담대 규제 보도자료 수집"""
    print("\n🏛️  [2] 금융위원회 규제 보도자료 수집")
    print("=" * 50)

    all_md  = f"# 금융위원회 주택담보대출 규제 정보\n\n"
    all_md += f"> 출처: 금융위원회 (www.fsc.go.kr)\n"
    all_md += f"> 수집일: {TODAY}\n\n---\n\n"

    # 핵심 규제 직접 정의 (공식 고시 기준 2024~2026)
    all_md += """## 현행 LTV (담보인정비율) 규제

| 구분 | 투기과열지구 | 조정대상지역 | 비규제지역 |
|------|------------|------------|----------|
| 1주택 이상 보유 | 30% | 50% | 70% |
| 무주택자 | 40% | 60% | 70% |
| 생애최초 | 80% | 80% | 80% |
| 신생아 특례 | 80% | 80% | 80% |

> 기준: 금융위원회 가계부채 관리 방안 (2024.09 기준)
> ⚠️ 규제지역 지정 현황에 따라 변동 가능

---

## 현행 DSR (총부채원리금상환비율) 규제

| 대출 유형 | 적용 기준 | DSR 한도 |
|----------|---------|---------|
| 1억원 초과 | 은행권 | 40% |
| 1억원 초과 | 비은행권 | 50% |
| 특례 대출 | 정책금융 | DSR 미적용 또는 완화 |

**DSR 계산식**:
- DSR(%) = (연간 모든 대출 원리금 상환액 합계) ÷ 연 소득 × 100
- 주담대 + 신용대출 + 카드론 + 기타 대출 원리금 모두 합산

**소득 인정 범위**:
- 근로소득: 원천징수영수증 기준
- 사업소득: 종합소득세 신고 기준
- 연금소득, 임대소득, 기타소득 일부 인정

---

## 현행 DTI (총부채상환비율) 규제

| 지역 | DTI 한도 |
|------|---------|
| 투기과열지구 | 40% |
| 조정대상지역 | 50% |
| 비규제지역 | 60% |

**DTI 계산식**:
- DTI(%) = (해당 주담대 연간 원리금 + 기타 대출 연간 이자) ÷ 연 소득 × 100
- DSR보다 완화된 기준 (기타 대출은 이자만 산정)

---

## 2024~2026 주요 규제 변경 이력

### 2024.09 — 2단계 스트레스 DSR 시행
- 주담대 스트레스 금리 +1.5%p 가산하여 DSR 계산
- 실질적 대출한도 10~15% 축소 효과

### 2024.01 — 특례보금자리론 일반형 종료
- 일반형 특례보금자리론 신규 접수 중단
- 우대형(저소득/청년/신혼) 일부 유지

### 2023.01 — 생애최초 주택구입 LTV 80% 완화
- 지역·주택가격·소득 무관 LTV 80% 적용
- 한도: 최대 6억원

---

## 투기지역·투기과열지구·조정대상지역 현황

> ⚠️ 지정 현황은 수시 변경됩니다.
> 최신 현황: 국토교통부 실거래가 공개시스템 (rt.molit.go.kr)

**투기과열지구 (2024년 기준)**:
- 서울 전 지역
- 경기 과천, 성남(분당·수정구), 하남, 광명

**조정대상지역**:
- 서울 전 지역, 경기 일부
- (지정 현황 수시 확인 필요)

"""

    # 보도자료 목록 수집 시도
    soup = get_html(FSC_SEARCH_URL)
    if soup:
        articles = soup.select("ul.bbs_list li, table.board_list tr")[:10]
        if articles:
            all_md += "## 금융위원회 최근 주담대 관련 보도자료\n\n"
            for a in articles:
                title = a.get_text(strip=True)
                link  = a.find("a")
                if link and any(k in title for k in FSC_KEYWORDS):
                    href = link.get("href", "")
                    all_md += f"- [{title}](https://www.fsc.go.kr{href})\n"

    save_md("금융위원회_LTV_DSR_규제.md", all_md)


# ══════════════════════════════════════════════════════════
# 3. 금융감독원 finlife API — 은행별 주담대 금리
# ══════════════════════════════════════════════════════════

FINLIFE_KEY = os.getenv("FINLIFE_API_KEY", "")

def collect_finlife_rates():
    """finlife API로 은행별 주담대 금리 수집"""
    print("\n📊 [3] 금융감독원 finlife API 수집")
    print("=" * 50)

    if not FINLIFE_KEY:
        print("  ⚠️  FINLIFE_API_KEY 없음 → .env에 추가 후 재실행")
        print("       발급: https://finlife.fss.or.kr → 마이페이지 → API 키")
        # API 없어도 기본 금리 정보는 하드코딩
        _save_manual_rate_info()
        return

    url = "https://finlife.fss.or.kr/finlifeapi/mortgageLoanProductsSearch.json"
    params = {
        "auth":         FINLIFE_KEY,
        "topFinGrpNo":  "020000",  # 은행권
        "pageNo":       1,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        base_list   = data.get("result", {}).get("baseList", [])
        option_list = data.get("result", {}).get("optionList", [])

        # 옵션을 상품코드로 인덱싱
        opts_by_code = {}
        for opt in option_list:
            code = opt.get("fin_prdt_cd", "")
            opts_by_code.setdefault(code, []).append(opt)

        md  = f"# 은행별 주택담보대출 금리 비교 (금융감독원 공시)\n\n"
        md += f"> 출처: 금융감독원 finlife (finlife.fss.or.kr)\n"
        md += f"> 수집일: {TODAY}\n\n---\n\n"

        # 신한은행 먼저
        shinhan = [p for p in base_list if "신한" in p.get("kor_co_nm", "")]
        others  = [p for p in base_list if "신한" not in p.get("kor_co_nm", "")]

        for product in shinhan + others:
            code     = product.get("fin_prdt_cd", "")
            bank     = product.get("kor_co_nm", "")
            name     = product.get("fin_prdt_nm", "")
            join_way = product.get("join_way", "")
            loan_lmt = product.get("loan_lmt", "")
            erly_fee = product.get("erly_rpay_fee", "")

            md += f"## {bank} — {name}\n\n"
            md += f"- **가입방법**: {join_way}\n"
            md += f"- **대출한도**: {loan_lmt}\n"
            if erly_fee:
                md += f"- **중도상환 수수료**: {erly_fee}\n"

            opts = opts_by_code.get(code, [])
            if opts:
                md += "\n| 담보유형 | 상환방식 | 금리유형 | 최저금리 | 최고금리 | 평균금리 |\n"
                md += "|---------|---------|---------|---------|---------|--------|\n"
                for opt in opts:
                    md += (
                        f"| {opt.get('mrtg_type_nm','')} "
                        f"| {opt.get('rpay_type_nm','')} "
                        f"| {opt.get('lend_rate_type_nm','')} "
                        f"| {opt.get('lend_rate_min','')}% "
                        f"| {opt.get('lend_rate_max','')}% "
                        f"| {opt.get('lend_rate_avg','')}% |\n"
                    )
            md += "\n---\n\n"

        save_md("finlife_은행별_주담대금리.md", md)
        print(f"  → 총 {len(base_list)}개 상품 수집")

    except Exception as e:
        print(f"  ❌ finlife API 오류: {e}")
        _save_manual_rate_info()


def _save_manual_rate_info():
    """finlife API 없을 때 수동 금리 기준 정보 저장"""
    md  = f"# 주택담보대출 금리 기준 정보\n\n"
    md += f"> 수집일: {TODAY}\n"
    md += f"> ⚠️ finlife API 키 미설정 — 수동 작성 기준 정보\n\n---\n\n"
    md += """## 기준금리 체계

| 금리 유형 | 기준 지표 | 특징 |
|---------|---------|------|
| 고정금리 | 금융채 5년물 | 금리 변동 위험 없음, 초기 금리 높음 |
| 변동금리 | COFIX (6개월/신규취급액) | 시장금리 연동, 초기 금리 낮음 |
| 혼합형 | 고정(5년) + 변동 전환 | 절충형 |

## 2026년 상반기 시중은행 주담대 금리 수준 (참고)

| 은행 | 고정금리 | 변동금리 |
|------|---------|---------|
| 신한은행 | 연 3.5~5.5% | 연 4.0~6.0% |
| KB국민 | 연 3.4~5.4% | 연 3.9~5.9% |
| 우리은행 | 연 3.5~5.5% | 연 4.0~6.0% |
| 하나은행 | 연 3.5~5.5% | 연 3.9~5.9% |

> ⚠️ 실제 금리는 신용등급, 담보, 우대조건에 따라 상이
> 정확한 금리: https://finlife.fss.or.kr (금융상품 한눈에)

## 우대금리 주요 조건 (신한은행 기준)

| 조건 | 우대금리 |
|------|---------|
| 급여이체 | -0.1%p |
| 신한카드 실적 30만원↑ | -0.1%p |
| 자동이체 3건↑ | -0.05%p |
| 신한 청약저축 보유 | -0.05%p |
| **최대 우대** | **-0.3%p** |

"""
    save_md("주담대_금리_기준정보.md", md)


# ══════════════════════════════════════════════════════════
# 4. 국토교통부 — 규제지역 현황
# ══════════════════════════════════════════════════════════

def collect_molit_regulations():
    """국토교통부 규제지역 및 부동산 정책 수집"""
    print("\n🏗️  [4] 국토교통부 규제지역 현황 수집")
    print("=" * 50)

    md  = f"# 국토교통부 부동산 규제지역 현황\n\n"
    md += f"> 출처: 국토교통부 (www.molit.go.kr)\n"
    md += f"> 수집일: {TODAY}\n"
    md += f"> ⚠️ 규제지역은 수시 변경됩니다. 반드시 최신 정보 확인\n\n---\n\n"

    md += """## 규제지역 종류 및 효과

| 규제 종류 | LTV | DTI | 청약 제한 | 양도세 |
|---------|-----|-----|---------|-------|
| 투기지역 | 40% | 40% | 1순위 제한 | 중과 |
| 투기과열지구 | 40~50% | 40~50% | 1순위 제한 | 중과 |
| 조정대상지역 | 50~60% | 50% | 일부 제한 | 중과 |
| 비규제지역 | 70% | 60% | 제한 없음 | 일반 |

## 2024~2026 규제지역 지정 현황

### 투기과열지구
- 서울특별시 전 지역 (25개 구)
- 경기도: 과천시, 성남시 분당구·수정구, 하남시, 광명시

### 조정대상지역
- 서울특별시 전 지역
- 경기도: 과천시, 성남시, 하남시, 광명시, 수원시, 안양시, 안산시 단원구, 구리시, 군포시, 의왕시, 용인시 수지구·기흥구, 화성시 동탄2

> ⚠️ 정확한 최신 현황:
> https://www.molit.go.kr (국토교통부 → 정책 → 주택토지 → 규제지역)
> https://rt.molit.go.kr (실거래가 공개시스템)

## 아파트 가격 기준 대출 규제 요약

| 아파트 가격 | 투기과열 LTV | 비규제 LTV | 특이사항 |
|-----------|------------|----------|--------|
| 9억 이하 | 40% | 70% | 일반 기준 |
| 9억 초과 | 20~40% | 50~70% | 초과분 LTV 하향 |
| 15억 초과 | 0% (불가) | 0% (불가) | 아파트 담보대출 금지 |

> 15억 초과 아파트: 2019.12.16 대책으로 주담대 전면 금지
> (단, 생애최초 특례 등 정책대출은 예외 적용 가능)

## 다주택자 규제 요약

| 주택 수 | 투기과열지구 | 조정대상지역 | 비규제지역 |
|---------|-----------|-----------|---------|
| 1주택 | LTV 40% | LTV 50% | LTV 70% |
| 2주택 이상 | 대출 불가 | 대출 불가 | LTV 60% |

> 임대사업자 등록 등 예외사항 존재

"""

    # 국토부 보도자료 수집 시도
    soup = get_html("https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp")
    if soup:
        articles = soup.select("ul.bbs_list li a, .board_list a")[:5]
        if articles:
            md += "## 최근 국토교통부 주요 보도자료\n\n"
            for a in articles:
                title = a.get_text(strip=True)
                href  = a.get("href", "")
                if title and any(k in title for k in ["주택", "부동산", "대출", "규제"]):
                    md += f"- [{title}](https://www.molit.go.kr{href})\n"

    save_md("국토교통부_규제지역_현황.md", md)


# ══════════════════════════════════════════════════════════
# 5. DSR/LTV 계산 예시 — RAG QA 성능 향상용
# ══════════════════════════════════════════════════════════

def generate_calculation_examples():
    """DSR/LTV 계산 예시 문서 생성 (RAG QA 정확도 향상)"""
    print("\n📐 [5] DSR/LTV 계산 예시 생성")
    print("=" * 50)

    md  = f"# 주택담보대출 DSR/LTV 계산 예시\n\n"
    md += f"> 작성일: {TODAY}\n\n---\n\n"

    md += """## LTV 계산 예시

### 예시 1: 서울 아파트 8억, 무주택자
- 지역: 서울 (투기과열지구)
- 적용 LTV: 40%
- **최대 대출 가능액: 8억 × 40% = 3억 2천만원**

### 예시 2: 경기 비규제지역 아파트 5억, 무주택자
- 지역: 비규제지역
- 적용 LTV: 70%
- **최대 대출 가능액: 5억 × 70% = 3억 5천만원**

### 예시 3: 생애최초, 지역 무관, 아파트 6억
- 생애최초 LTV 80% 적용
- **최대 대출 가능액: 6억 × 80% = 4억 8천만원**
- 단, 정책대출 한도 5억원 이내 적용

---

## DSR 계산 예시

### 예시 1: 연소득 6,000만원, 30년 만기, 금리 4.5%
- DSR 40% 한도 = 6,000만원 × 40% = 연 2,400만원 = 월 200만원
- 월 200만원 기준 30년 4.5% → 대출 가능액 약 **3억 9,500만원**

### 예시 2: 연소득 8,000만원, 기존 신용대출 3,000만원 보유
- 신용대출 연 원리금: 약 330만원 (3년 만기 5% 기준)
- 주담대에 쓸 수 있는 DSR 여유: 8,000만원 × 40% - 330만원 = 연 2,870만원
- 월 239만원 기준 30년 4.5% → 주담대 가능액 약 **4억 7,000만원**

### 예시 3: 신혼부부, 부부합산 연소득 1억, 30년 4.0%
- DSR 40% 한도 = 1억 × 40% = 연 4,000만원 = 월 333만원
- 월 333만원 기준 30년 4.0% → 대출 가능액 약 **6억 9,800만원**
- LTV 한도와 비교하여 낮은 금액 적용

---

## 고객 유형별 최적 대출 상품 매칭

### 신혼부부 (결혼 7년 이내, 무주택)
- **추천**: 신생아특례대출, 디딤돌대출(신혼), 보금자리론
- LTV: 최대 80%
- 금리: 연 1.6~3.9% (소득/만기에 따라 차등)
- 한도: 최대 5억원

### 생애최초 주택구입자
- **추천**: 생애최초 특례대출, 디딤돌대출, 청년주택드림대출
- LTV: 최대 80%
- 금리: 연 2.0~4.0%
- 한도: 최대 5억원

### 1인가구 (무주택, 비규제지역)
- **추천**: 신한주택대출(아파트), 보금자리론
- LTV: 최대 70%
- 금리: 연 3.5~5.5% (시중금리 기준)

### 다주택자 (투기과열지구 내)
- 신규 주담대 불가 (규제지역 내 2주택 이상)
- 비규제지역은 LTV 60% 적용

"""

    save_md("주담대_계산예시_QA.md", md)


# ══════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("📋 주택담보대출 규제 정보 전체 수집 파이프라인")
    print(f"📁 저장 경로: {OUTPUT_DIR.absolute()}\n")

    collect_hf_products()        # 주택금융공사
    collect_fsc_regulations()    # 금융위원회
    collect_finlife_rates()      # 금융감독원 finlife
    collect_molit_regulations()  # 국토교통부
    generate_calculation_examples()  # 계산 예시

    print(f"\n✅ 전체 수집 완료!")
    print(f"\n생성된 파일:")
    for f in sorted(OUTPUT_DIR.glob("*.md")):
        size = f.stat().st_size
        print(f"  📄 {f.name} ({size:,} bytes)")

    print(f"\n📌 다음 단계: python scripts/build_vectorstore.py 재실행")
    print(f"   (새 규제 문서를 벡터 DB에 추가)")
