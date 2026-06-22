"""
신한은행 주담대 상품 정보 수집기
- 신한은행 홈페이지 스크래핑 (BeautifulSoup)
- 금융감독원 finlife API (주택담보대출 비교 공시)
→ 수집 결과를 data/rag_docs/shinhan_faq/ 에 마크다운으로 저장

사용법:
    pip install requests beautifulsoup4 python-dotenv
    python collector.py

finlife API 키 발급:
    https://finlife.fss.or.kr → 회원가입 → API 키 발급 (무료, 즉시)
"""

import os
import time
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────
# 설정
# ──────────────────────────────────────────
OUTPUT_DIR = Path("data/rag_docs/shinhan_faq")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

FINLIFE_API_KEY = os.getenv("FINLIFE_API_KEY", "")  # .env에 입력

# ──────────────────────────────────────────
# 1. 신한은행 홈페이지 스크래핑
# ──────────────────────────────────────────

# 스크래핑 대상 URL 목록 (주담대 관련 페이지)
SHINHAN_PAGES = [
    {
        "name": "신한_주택담보대출_메인",
        "url": "https://www.shinhan.com/hpe/index.jsp#050101000000",
        "description": "신한은행 주택담보대출 상품 목록",
    },
    {
        "name": "신한_아파트론",
        "url": "https://www.shinhan.com/hpe/index.jsp#050101010000",
        "description": "신한 아파트론 상품 상세",
    },
    {
        "name": "신한_생애최초주택구입론",
        "url": "https://www.shinhan.com/hpe/index.jsp#050101020000",
        "description": "생애최초 주택구입 특례대출",
    },
    {
        "name": "신한_신혼부부대출",
        "url": "https://www.shinhan.com/hpe/index.jsp#050101030000",
        "description": "신혼부부 전용 주담대",
    },
    {
        "name": "신한_주담대_FAQ",
        "url": "https://www.shinhan.com/hpe/index.jsp#050101000000",  # FAQ 섹션
        "description": "주택담보대출 자주 묻는 질문",
    },
]


def scrape_shinhan_page(page_info: dict) -> str | None:
    """신한은행 페이지 하나를 스크래핑해서 마크다운으로 반환"""
    try:
        # SPA(Single Page App) 특성상 # 이후는 클라이언트 라우팅
        # 실제 콘텐츠 URL로 변환 시도
        base_url = page_info["url"].split("#")[0]
        menu_id = page_info["url"].split("#")[-1] if "#" in page_info["url"] else ""

        print(f"  📡 요청 중: {page_info['name']}")
        resp = requests.get(base_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # 본문 콘텐츠 추출 (신한은행 HTML 구조 기준)
        content_selectors = [
            "div.cont_wrap",       # 주요 콘텐츠 영역
            "div.product_info",    # 상품 정보
            "div.tab_cont",        # 탭 콘텐츠
            "div#contents",        # 일반 콘텐츠
            "main",
        ]

        text_blocks = []
        for selector in content_selectors:
            elements = soup.select(selector)
            for el in elements:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 100:  # 의미있는 텍스트만
                    text_blocks.append(text)

        if not text_blocks:
            # fallback: body 전체 텍스트
            text_blocks = [soup.get_text(separator="\n", strip=True)]

        # 마크다운 포맷으로 변환
        md = f"# {page_info['name']}\n\n"
        md += f"> 출처: {page_info['url']}\n"
        md += f"> 수집일: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        md += f"## 개요\n{page_info['description']}\n\n"
        md += "## 상품 정보\n\n"
        md += "\n\n".join(text_blocks[:3])  # 상위 3개 블록만

        return md

    except requests.exceptions.RequestException as e:
        print(f"  ⚠️  스크래핑 실패 ({page_info['name']}): {e}")
        return None


def run_shinhan_scraper():
    """신한은행 전체 스크래핑 실행"""
    print("\n🏦 [1단계] 신한은행 홈페이지 스크래핑 시작")
    print("=" * 50)

    success_count = 0
    for page in SHINHAN_PAGES:
        md_content = scrape_shinhan_page(page)

        if md_content:
            output_path = OUTPUT_DIR / f"{page['name']}.md"
            output_path.write_text(md_content, encoding="utf-8")
            print(f"  ✅ 저장 완료: {output_path}")
            success_count += 1
        else:
            # 스크래핑 실패 시 → 템플릿 파일 생성 (수동 입력 안내)
            fallback_path = OUTPUT_DIR / f"{page['name']}_수동입력필요.md"
            fallback_content = f"""# {page['name']} (수동 입력 필요)

> 출처: {page['url']}
> 스크래핑 실패 — 아래 내용을 직접 복사하여 채워주세요.

## 개요
{page['description']}

## 상품 정보
<!-- 신한은행 홈페이지에서 직접 복사 -->

## 대출 한도
- LTV: 
- DTI: 
- DSR: 

## 금리
- 기준금리: 
- 우대금리 조건: 

## 신청 자격
- 

## 필요 서류
- 
"""
            fallback_path.write_text(fallback_content, encoding="utf-8")
            print(f"  📝 템플릿 생성: {fallback_path} (직접 채워주세요)")

        time.sleep(1)  # 서버 부하 방지

    print(f"\n  → 스크래핑 결과: {success_count}/{len(SHINHAN_PAGES)} 성공")


# ──────────────────────────────────────────
# 2. 금융감독원 finlife API
# ──────────────────────────────────────────

FINLIFE_BASE = "https://finlife.fss.or.kr/finlifeapi"

# 신한은행 금융회사 코드
SHINHAN_FIN_CO_NO = "0010927"  # 신한은행 고유 코드


def fetch_finlife_mortgage_products() -> list[dict]:
    """
    finlife API: 주택담보대출 상품 목록 조회
    API 키: https://finlife.fss.or.kr 회원가입 후 발급 (무료)
    """
    if not FINLIFE_API_KEY:
        print("  ⚠️  FINLIFE_API_KEY가 없습니다. .env에 추가해주세요.")
        print("     발급: https://finlife.fss.or.kr → 로그인 → API 키 발급")
        return []

    url = f"{FINLIFE_BASE}/mortgageLoanProductsSearch.json"
    params = {
        "auth": FINLIFE_API_KEY,
        "topFinGrpNo": "020000",  # 은행권
        "pageNo": 1,
        "finCoNo": SHINHAN_FIN_CO_NO,  # 신한은행만 필터
    }

    try:
        print(f"  📡 finlife API 요청 중...")
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # 응답 구조: result → baseList(기본정보) + optionList(금리옵션)
        base_list = data.get("result", {}).get("baseList", [])
        option_list = data.get("result", {}).get("optionList", [])

        print(f"  ✅ 상품 {len(base_list)}개 수신")
        return {"base": base_list, "options": option_list}

    except Exception as e:
        print(f"  ❌ finlife API 오류: {e}")
        return []


def convert_finlife_to_markdown(data: dict) -> str:
    """finlife API 응답 → RAG용 마크다운 변환"""
    if not data:
        return ""

    base_list = data.get("base", [])
    option_list = data.get("options", [])

    # 옵션을 상품코드로 인덱싱
    options_by_code = {}
    for opt in option_list:
        code = opt.get("fin_prdt_cd", "")
        options_by_code.setdefault(code, []).append(opt)

    md = "# 신한은행 주택담보대출 상품 목록 (금융감독원 공시)\n\n"
    md += f"> 출처: 금융감독원 금융상품한눈에 (finlife.fss.or.kr)\n"
    md += f"> 수집일: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    md += "---\n\n"

    for product in base_list:
        code = product.get("fin_prdt_cd", "")
        name = product.get("fin_prdt_nm", "상품명 없음")
        join_way = product.get("join_way", "")
        loan_incl_excl = product.get("loan_incl_excl_info", "")
        erty_kind = product.get("erty_kind", "")  # 담보 종류
        loan_lmt = product.get("loan_lmt", "")
        dcls_strt_day = product.get("dcls_strt_day", "")

        md += f"## {name}\n\n"
        md += f"- **상품코드**: {code}\n"
        md += f"- **가입방법**: {join_way}\n"
        md += f"- **담보 종류**: {erty_kind}\n"
        md += f"- **대출 한도**: {loan_lmt}\n"
        md += f"- **공시 시작일**: {dcls_strt_day}\n"
        if loan_incl_excl:
            md += f"- **대출 포함/제외 정보**: {loan_incl_excl}\n"

        # 금리 옵션
        opts = options_by_code.get(code, [])
        if opts:
            md += "\n### 금리 옵션\n\n"
            md += "| 금리유형 | 대출기간 | 거치기간 | 상환방법 | 최저금리 | 최고금리 |\n"
            md += "|---------|---------|---------|---------|---------|----------|\n"
            for opt in opts:
                md += (
                    f"| {opt.get('mrtg_type_nm', '')} "
                    f"| {opt.get('loan_lmt', '')} "
                    f"| {opt.get('rpay_type_nm', '')} "
                    f"| {opt.get('lend_rate_type_nm', '')} "
                    f"| {opt.get('lend_rate_min', '')}% "
                    f"| {opt.get('lend_rate_max', '')}% |\n"
                )

        md += "\n---\n\n"

    return md


def run_finlife_collector():
    """finlife API 수집 실행"""
    print("\n📊 [2단계] 금융감독원 finlife API 수집 시작")
    print("=" * 50)

    data = fetch_finlife_mortgage_products()

    if data:
        md_content = convert_finlife_to_markdown(data)
        output_path = OUTPUT_DIR / "신한은행_주담대_금감원공시.md"
        output_path.write_text(md_content, encoding="utf-8")
        print(f"  ✅ 저장 완료: {output_path}")

        # 원본 JSON도 백업
        json_path = OUTPUT_DIR / "shinhan_mortgage_raw.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ 원본 JSON 백업: {json_path}")
    else:
        print("  ⚠️  finlife 데이터 없음 → API 키 확인 후 재실행")


# ──────────────────────────────────────────
# 3. 수동 입력 템플릿 생성 (핵심 규제 정보)
# ──────────────────────────────────────────

REGULATION_TEMPLATE = """# 2026년 주택담보대출 핵심 규제 정보

> 출처: 금융위원회, 국토교통부 공식 발표
> 수집일: {date}
> ⚠️ 규제는 자주 변경됩니다. 최신 정보로 업데이트 필요

---

## LTV (담보인정비율)

| 주택 유형 | 지역 | 1주택자 | 생애최초 |
|---------|------|---------|---------|
| 아파트 | 규제지역 | 50% | 80% |
| 아파트 | 비규제지역 | 70% | 80% |
| 아파트 | 투기지역 | 40% | 60% |

## DSR (총부채원리금상환비율)

- 1억 초과 대출: DSR 40% 적용 (은행권)
- 계산식: (연간 원리금 상환액 합계) / 연 소득 × 100

## DTI (총부채상환비율)

- 규제지역: 40% 이하
- 비규제지역: 60% 이하

---

## 특례 대출 상품

### 1. 생애최초 주택구입 특례대출
- 대상: 생애 처음으로 주택 구입하는 자
- LTV: 최대 80%
- 금리: 연 2.65% ~ 3.95% (소득·만기 따라 차등)
- 한도: 최대 5억원

### 2. 신혼부부 전용 (신혼희망타운 등)
- 대상: 결혼 7년 이내 또는 예비부부
- LTV: 최대 80%
- 금리: 연 2.45% ~ 3.55%
- 한도: 최대 4억원

### 3. 신생아 특례대출
- 대상: 2023년 이후 출산 가구
- LTV: 최대 80%
- 금리: 연 1.6% ~ 3.3%
- 한도: 최대 5억원

### 4. 디딤돌 대출 (서민·실수요자)
- 대상: 부부합산 연소득 6천만원 이하
- LTV: 최대 70%
- 금리: 연 2.35% ~ 3.65%
- 한도: 최대 2.5억원

---

## 신한은행 주담대 우대금리 조건

- 신한 급여이체: -0.1%
- 신한 카드 실적 (30만원 이상): -0.1%
- 자동이체 3건 이상: -0.05%
- 신한 청약저축 보유: -0.05%
- 최대 우대금리: -0.3%p

---

## 대출 가능 여부 계산 예시

### 예시 1: 신혼부부, 서울 아파트 6억, 연소득 8천만원
- 적용 LTV: 50% (규제지역)
- 최대 대출: 3억원
- DSR 40% 기준 최대 원리금: 연 3,200만원 (월 267만원)
- 30년 만기 3.5% 금리 기준 → 약 2.7억원 가능

### 예시 2: 1인가구, 경기도 아파트 4억, 연소득 5천만원
- 적용 LTV: 70% (비규제지역)
- 최대 대출: 2.8억원
- DSR 40% 기준 최대 원리금: 연 2,000만원 (월 167만원)
- 30년 만기 3.5% 기준 → 약 1.7억원 가능
"""


def generate_regulation_template():
    """규제 정보 템플릿 생성"""
    print("\n📋 [3단계] 규제 정보 템플릿 생성")
    print("=" * 50)

    regs_dir = Path("data/rag_docs/regulations")
    regs_dir.mkdir(parents=True, exist_ok=True)

    content = REGULATION_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"))
    output_path = regs_dir / "주담대_핵심규제_2026.md"
    output_path.write_text(content, encoding="utf-8")
    print(f"  ✅ 저장 완료: {output_path}")
    print(f"  ⚠️  내용 확인 후 최신 규제로 업데이트 필요")


# ──────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────

if __name__ == "__main__":
    print("🏠 홈런 7조 — 데이터 수집 파이프라인 시작")
    print(f"📁 저장 경로: {OUTPUT_DIR.absolute()}")
    print("=" * 50)

    # 1. 신한은행 스크래핑
    run_shinhan_scraper()

    # 2. 금감원 finlife API
    run_finlife_collector()

    # 3. 규제 정보 템플릿
    generate_regulation_template()

    print("\n✅ 전체 수집 완료!")
    print("\n📌 다음 단계:")
    print("  1. data/rag_docs/ 폴더의 _수동입력필요.md 파일들 직접 채우기")
    print("  2. .env에 FINLIFE_API_KEY 추가 후 재실행")
    print("  3. python scripts/build_vectorstore.py 실행 → RAG 인덱싱")
