"""
신한은행 주택자금대출 상품 60개 수집기 v4
- trxCd: 목록=RSRLO0201A10 / 상세=RSRLO0201A06
- 목록 응답: dataBody.TB_PRODUCT
- 상세 응답: dataBody (dm_R_TDL1013 구조)
"""

import time, random, json, requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("data/rag_docs/shinhan_faq")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://bank.shinhan.com"
ENDPOINT = f"{BASE_URL}/serviceEndpoint/httpDigital"

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type":    "application/json; charset=UTF-8",
    "Accept":          "application/json, text/javascript, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer":         "https://bank.shinhan.com/index.jsp",
    "Origin":          "https://bank.shinhan.com",
}

def make_ric_info(service_code: str, callback: str = "") -> dict:
    return {
        "serviceType": "TG", "serviceCode": service_code,
        "nextServiceCode": "", "pkcs7Data": "", "signCode": "", "signData": "",
        "useSign": "", "useCert": "", "permitMultiTransaction": "",
        "keepTransactionSession": "", "skipErrorMsg": "", "mode": "",
        "language": "ko", "exe2e": "", "hideProcess": "", "clearTarget": "",
        "callBack": callback, "exceptionCallback": "", "requestMessage": "",
        "responseMessage": "", "serviceOption": "", "pcLog": "",
        "preInqForMulti": "", "makesum": "", "removeIndex": "",
        "redirectUrl": "", "preInqKey": "", "_multi_transfer_": "",
        "_multi_transfer_count_": "", "_multi_transfer_amt_": "",
        "userCallback": "", "menuCode": "", "certtype": "",
        "fromMulti": "", "fromMultiIdx": "",
        "isRule": "N", "webUri": "/index.jsp", "gubun": "", "tmpField2": "",
    }

def call_api(trx_cd: str, service_code: str, body_params: dict, callback: str = "") -> dict | None:
    payload = {
        "dataHeader": {
            "trxCd": trx_cd,
            "language": "ko",
            "subChannel": "49",
            "channelGbn": "D0",
        },
        "dataBody": {
            "ricInptRootInfo": make_ric_info(service_code, callback),
            **body_params,
        },
    }
    try:
        resp = requests.post(ENDPOINT, json=payload, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ❌ API 오류 ({service_code}): {e}")
        return None


# ── STEP 1: 상품 목록 (THO0409 / trxCd=A10) ─────────────
def fetch_product_list() -> list[dict]:
    print("\n📋 [STEP 1] 상품 목록 조회 (THO0409) ...")

    data = call_api(
        trx_cd="RSRLO0201A10",          # ← 목록 전용 trxCd
        service_code="THO0409",
        body_params={
            "loanType":  "20",           # 주택자금대출
            "PAGE":      "1",
            "PAGESIZE":  "100",
            "SORT_FLAG": "",
            "joinbit":   "",
            "houseType": "",
            "schWord":   "",
            "FROM_ROW":  "",
            "END_ROW":   "",
        },
        callback="shbObj.fncDoTHO0409Callback",
    )

    if not data:
        return []

    # 응답 저장
    (OUTPUT_DIR / "_debug_tho0409.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 응답 구조: dataBody.TB_PRODUCT
    body         = data.get("dataBody", {})
    product_list = body.get("TB_PRODUCT", [])

    if not product_list:
        print(f"  ⚠️  TB_PRODUCT 없음. 응답 키: {list(body.keys())}")
        print(f"  📄 _debug_tho0409.json 확인하세요")
        return []

    def is_discontinued(item: dict) -> bool:
        name   = item.get('C_PROD_NAME', '')
        pledge = item.get('C_PLEDGE_NAME', '').strip()
        client = item.get('C_PER_CLIENT', '')

        # 조건1: 판매중지 명시
        if '판매중지' in name:
            return True

        # 조건2: 모든 채널 0 (신청 불가)
        all_zero = all(
            item.get(k, '0') == '0'
            for k in ['JOIN_INT_YN', 'JOIN_MOB_YN', 'JOIN_BNK_YN', 'JOIN_CAL_YN', 'JOIN_YSL_YN']
        )
        if all_zero:
            return True

        # 조건3: 명시적 제외 카테고리 (매매 키워드보다 먼저 체크)
        EXCLUDE_KEYWORDS = [
            '오피스텔',                      # 오피스텔 제외
            '월세대출', '월세',              # 월세 제외
            '상업용', 'Tops 부동산',         # 상업용 부동산 제외
            '임대아파트', '집단전세', '임대주택',  # 임대 제외
        ]
        if any(k in name for k in EXCLUDE_KEYWORDS):
            return True

        # 조건4: 매매/구입 목적 키워드 → 전세 포함이라도 유지
        PURCHASE_KEYWORDS = ['구입', '매매', '분양', '재건축', '재개발', '이주비', '중도금', '디딤돌', '보금자리론']
        if any(k in name or k in client for k in PURCHASE_KEYWORDS):
            return False

        # 조건5: 담보 없고 전세/임차 키워드 → 제외
        RENTAL_KEYWORDS = ['전세', '임차', '보증금']
        if not pledge and any(k in name for k in RENTAL_KEYWORDS):
            return True

        return False

    products = []
    skipped  = []
    for item in product_list:
        if is_discontinued(item):
            skipped.append(item.get('C_PROD_NAME', ''))
            continue
        products.append({
            "id":            item.get("C_PROD_ID", ""),
            "name":          item.get("C_PROD_NAME", ""),
            "outline":       item.get("C_PROD_OUTLINE1", ""),
            "client":        item.get("C_PER_CLIENT", ""),
            "limit":         item.get("C_PER_LOAN_LIMIT", ""),
            "loan_type":     item.get("LOAN_TYPE", ""),
            "join_internet": item.get("JOIN_INT_YN") == "1",
            "join_mobile":   item.get("JOIN_MOB_YN") == "1",
            "join_branch":   item.get("JOIN_BNK_YN") == "1",
        })

    print(f"  ✅ 판매중인 상품: {len(products)}개 수집")
    print(f"  🚫 판매중지 제외: {len(skipped)}개")
    for name in skipped:
        print(f"     - {name}")
    return products


# ── STEP 2: 상품 상세 (TDL1013 / trxCd=A06) ─────────────
def fetch_product_detail(prod_id: str) -> dict:
    data = call_api(
        trx_cd="RSRLO0201A06",          # ← 상세 전용 trxCd
        service_code="TDL1013",
        body_params={
            "P_C_PROD_ID": prod_id,
            "C_JUMIN_NO":  "",
        },
        callback="shbObj.getDetailTaskCallback",
    )

    if not data:
        return {}

    body   = data.get("dataBody", {})
    detail = body.get("dm_R_TDL1013") or body.get("TB_PRODUCT") or body

    return {
        "outline2":      detail.get("C_PROD_OUTLINE2", ""),
        "client2":       detail.get("C_CLIENT2", ""),
        "loan_limit2":   detail.get("C_LOAN_LIMIT2", ""),
        "loan_date":     detail.get("C_LOAN_DATE", ""),
        "exchange_way":  detail.get("C_EXCHANGE_WAY", ""),
        "exchange_fee":  detail.get("C_EXCHANGE_FEE", ""),
        "need_doc":      detail.get("C_NEED_DOC", ""),
        "attention":     detail.get("C_ATTENTION", ""),
        "rate_nm":       detail.get("C_RATE_NM", ""),
        "loan_cost":     detail.get("C_LOAN_COST", ""),
        "loan_rate_url": detail.get("C_LOAN_RATE_URL", ""),   # ← 금리 정보 HTML
        "rate_cd":       detail.get("C_RATE_CD", ""),          # 1=고정 2=변동 3=혼합
    }


# ── STEP 3: 마크다운 저장 ────────────────────────────────
def html_to_text(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)

def save_markdown(products: list[dict]):
    md  = "# 신한은행 주택자금대출 상품 안내\n\n"
    md += f"> 출처: {BASE_URL}/index.jsp#020305010000\n"
    md += f"> 수집일: {datetime.now().strftime('%Y-%m-%d')}\n"
    md += f"> 총 {len(products)}개 상품\n\n---\n\n"

    for i, p in enumerate(products, 1):
        md += f"## {i}. {p['name']}\n\n"

        channels = []
        if p.get("join_internet"): channels.append("인터넷")
        if p.get("join_mobile"):   channels.append("모바일")
        if p.get("join_branch"):   channels.append("영업점")
        if channels:
            md += f"**신청 채널**: {' / '.join(channels)}\n\n"

        for label, keys in [
            ("상품 개요",       ["outline", "outline2"]),
            ("대출 대상",       ["client", "client2"]),
            ("대출 한도",       ["limit", "loan_limit2"]),
            ("대출 기간",       ["loan_date"]),
            ("상환 방법",       ["exchange_way"]),
            ("중도상환 수수료", ["exchange_fee"]),
            ("대출 비용",       ["loan_cost"]),
            ("필요 서류",       ["need_doc"]),
            ("유의사항",        ["attention"]),
        ]:
            for key in keys:
                val = html_to_text(p.get(key, ""))
                if val:
                    md += f"**{label}**: {val}\n\n"
                    break

        # 금리 정보 (C_LOAN_RATE_URL → HTML 파싱)
        rate_html = p.get("loan_rate_url", "")
        if rate_html:
            rate_text = html_to_text(rate_html)
            if rate_text:
                # 금리 유형 텍스트 추가
                rate_cd = p.get("rate_cd", "")
                rate_type = {"1": "고정금리", "2": "변동금리", "3": "고정 또는 변동금리"}.get(rate_cd, "")
                if rate_type:
                    md += f"**금리 유형**: {rate_type}\n\n"
                md += f"**대출금리**:\n{rate_text}\n\n"

        md += "---\n\n"

    out = OUTPUT_DIR / "신한은행_주택자금대출_전상품.md"
    out.write_text(md, encoding="utf-8")
    print(f"\n✅ 저장 완료: {out}")
    print(f"   {len(products)}개 상품 / {len(md):,}자")


# ── 메인 ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("🏦 신한은행 주택자금대출 상품 수집기 v4")
    print(f"📡 엔드포인트: {ENDPOINT}\n")

    session = requests.Session()
    try:
        session.get(BASE_URL, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=10)
        print("🍪 세션 초기화 완료")
    except Exception as e:
        print(f"⚠️  세션 초기화 실패: {e}")

    products = fetch_product_list()
    if not products:
        print("\n⛔ 목록 수집 실패")
        exit(1)

    print(f"\n📦 [STEP 2] 상품 상세 수집 (총 {len(products)}개)")
    for i, p in enumerate(products, 1):
        print(f"  [{i:02d}/{len(products)}] {p['name']}")
        detail = fetch_product_detail(p["id"])
        products[i-1].update(detail)
        time.sleep(random.uniform(0.5, 1.0))

    save_markdown(products)
    print("\n📌 다음 단계: python scripts/build_vectorstore.py")
