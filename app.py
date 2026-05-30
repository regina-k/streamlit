"""
AI 갈아타기 & 상급지 스카우터
────────────────────────────
KB부동산 라이브 API로 내 아파트를 검색하고,
로컬 CSV(14~16억 단지 데이터)에서 타겟을 골라
GPT-4o가 갈아타기 전략 리포트를 생성합니다.
"""

import os
import re
import requests
import pandas as pd
import streamlit as st

# ── python-dotenv (로컬 개발 편의용, 배포 환경에서는 Secrets 환경변수 사용) ─
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── OpenAI 라이브러리 임포트 ────────────────────────────────────────────
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════
# 상수
# ═══════════════════════════════════════════════════════════════════════
KB_BASE_URL = "https://api.kbland.kr"
CSV_FILE    = "kb_data.csv"

KB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://kbland.kr/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# ── 페이지 설정 (최상단 1회 호출) ──────────────────────────────────────
st.set_page_config(
    page_title="AI 갈아타기 & 상급지 스카우터",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════
# 헬퍼: 금액 한글 표시
# ═══════════════════════════════════════════════════════════════════════

def format_price_kor(eok: float) -> str:
    """13.4 → '13억 4,000만 원' (억 단위 float 입력)."""
    if eok <= 0:
        return "0원"
    man_total = round(eok * 10000)
    eok_part  = man_total // 10000
    man_part  = man_total % 10000
    if eok_part > 0 and man_part > 0:
        return f"{eok_part}억 {man_part:,}만 원"
    elif eok_part > 0:
        return f"{eok_part}억"
    else:
        return f"{man_part:,}만 원"


def man_to_eok_str(man: int) -> str:
    """134000 → '13억 4,000만 원' (만원 단위 int 입력)."""
    return format_price_kor(man / 10000)


def calc_loan_limit(target_price_man: int) -> int:
    """가계부채 관리방안 기준 주담대 한도 반환 (만원 단위).
    ≤15억 → 6억 / 15억 초과~25억 이하 → 4억 / 25억 초과 → 2억
    """
    if target_price_man <= 150_000:
        return 60_000
    elif target_price_man <= 250_000:
        return 40_000
    else:
        return 20_000


# ═══════════════════════════════════════════════════════════════════════
# KB부동산 API 헬퍼 함수
# ═══════════════════════════════════════════════════════════════════════

def fetch_search_suggestions(keyword: str) -> list:
    """자동완성 API: 키워드로 단지 후보 목록 반환.
    엔드포인트: /land-complex/serch/autoKywrSerch
    """
    url    = f"{KB_BASE_URL}/land-complex/serch/autoKywrSerch"
    params = {
        "컬렉션설정명": (
            "COL_AT_JUSO:100;COL_AT_SCHOOL:100;"
            "COL_AT_SUBWAY:100;COL_AT_HSCM:100;COL_AT_VILLA:100"
        ),
        "검색키워드": keyword,
    }
    try:
        resp = requests.get(url, params=params, headers=KB_HEADERS, timeout=10)
        resp.raise_for_status()
        raw_list = (
            resp.json()
                .get("dataBody", {})
                .get("data", [{}])[0]
                .get("COL_AT_HSCM", [])
        )
        result = []
        for item in raw_list:
            name      = item.get("text", "")
            addr      = item.get("addr", "")
            text_temp = item.get("textTemp", f"({addr}){name}")
            label     = f"{name}  ({addr})"
            result.append({"label": label, "textTemp": text_temp})
        return result
    except Exception as e:
        st.error(f"단지 검색 실패: {e}")
        return []


def fetch_complex_id(text_temp: str) -> dict:
    """통합검색 API: textTemp로 단지 기본정보(COMPLEX_NO 포함) 반환.
    엔드포인트: /land-complex/serch/intgraSerch
    """
    url    = f"{KB_BASE_URL}/land-complex/serch/intgraSerch"
    params = {
        "검색설정명": "SRC_HSCM",
        "검색키워드": text_temp,
        "출력갯수": 2,
        "페이지설정값": 1,
    }
    try:
        resp = requests.get(url, params=params, headers=KB_HEADERS, timeout=10)
        resp.raise_for_status()
        hscm = (
            resp.json()
                .get("dataBody", {})
                .get("data", {})
                .get("data", {})
                .get("HSCM", {})
                .get("data", [])
        )
        if not hscm:
            return {}
        item       = hscm[0]
        raw_comp   = str(item.get("MVIHS_DATE", ""))
        completion = (
            f"{raw_comp[:4]}.{raw_comp[4:]}" if len(raw_comp) >= 6 else raw_comp
        )
        return {
            "complex_id": item.get("COMPLEX_NO", ""),
            "name":       item.get("HSCM_NM", ""),
            "addr":       item.get("BUBADDR_SHORT", "") or item.get("BUBADDR", ""),
            "units":      item.get("THS_NUM", ""),
            "completion": completion,
        }
    except Exception as e:
        st.error(f"단지 ID 조회 실패: {e}")
        return {}


def fetch_complex_price(complex_id: str) -> list:
    """단지 시세정보 API: 면적별 KB매매시세 리스트 반환.
    엔드포인트: /land-complex/complex/mpriByType
    """
    url    = f"{KB_BASE_URL}/land-complex/complex/mpriByType"
    params = {"단지기본일련번호": complex_id}
    try:
        resp = requests.get(url, params=params, headers=KB_HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json().get("dataBody", {}).get("data", []) or []
    except Exception as e:
        st.error(f"단지 시세 조회 실패 (ID={complex_id}): {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════
# 캐시 데이터 로더: CSV → DataFrame
# ── get_unique_complexes() 제거: 다중 평형 선택을 위해 df_all 직접 사용
# ═══════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="CSV 데이터를 불러오는 중...")
def load_apartment_data() -> pd.DataFrame:
    """로컬 CSV 로드 + 타입 정규화. 모든 평형 행을 그대로 유지."""
    try:
        df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(CSV_FILE, encoding="cp949")

    # 숫자형 컬럼 정규화
    for col in ["KB매매시세(만원)", "매매상한가(만원)", "매매하한가(만원)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "세대수" in df.columns:
        df["세대수"] = pd.to_numeric(df["세대수"], errors="coerce").fillna(0).astype(int)
    if "단지ID" in df.columns:
        df["단지ID"] = pd.to_numeric(df["단지ID"], errors="coerce").fillna(0).astype(int)
    if "공급면적(평)" in df.columns:
        df["공급면적(평)"] = pd.to_numeric(df["공급면적(평)"], errors="coerce")
    if "구" in df.columns:
        df["구"] = df["구"].fillna("").astype(str).str.strip()

    # 도로명주소에서 시·구 단위 지역 라벨 생성 (필터 UI용)
    if "도로명주소" in df.columns:
        df["지역"] = df["도로명주소"].str.extract(r"^(\S+\s+\S+)")[0].fillna("")
    else:
        df["지역"] = df.get("구", "")

    return df


# ═══════════════════════════════════════════════════════════════════════
# ░░  사이드바 UI  ░░
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("🏠 내 집 정보 입력")
    st.markdown("---")

    # ── OpenAI API Key ──────────────────────────────────────────────
    st.subheader("🔑 OpenAI API Key")
    env_key = os.getenv("OPENAI_API_KEY", "").strip()

    # 항상 text_input을 노출 — env 키가 있어도 수동 입력으로 덮어쓸 수 있음
    # (env 키가 만료/무효일 때 사용자가 직접 갱신할 수 있도록)
    if env_key:
        st.info("ℹ️ Secrets 환경변수에서 API Key를 읽었습니다. 아래에서 다른 키로 덮어쓸 수 있습니다.")
    else:
        st.warning("⚠️ Secrets 환경변수에서 Key를 찾지 못했습니다. 직접 입력해 주세요.")

    manual_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...  (입력하면 환경변수 값 대신 사용)",
        help="OpenAI 대시보드에서 발급한 API Key를 입력하세요.",
        key="api_key_input",
    ).strip()

    # 수동 입력 우선, 없으면 환경변수 값 사용
    api_key = manual_key if manual_key else env_key

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════
    # STEP 1 ▸ 아파트명 통합검색 (자동완성 2단계 API)
    # ══════════════════════════════════════════════════════════════════
    st.subheader("📍 STEP 1 — 내 아파트 검색")

    search_keyword = st.text_input(
        "아파트 이름을 입력하세요",
        placeholder="예: 래미안 대치",
        help="단지명 일부만 입력해도 됩니다.",
        key="search_keyword_input",
    )

    # 키워드 입력 시 자동완성 API 호출
    suggestions = []
    if search_keyword.strip():
        with st.spinner("단지를 검색 중..."):
            suggestions = fetch_search_suggestions(search_keyword.strip())

    if suggestions:
        labels    = [s["label"] for s in suggestions]
        sel_label = st.selectbox(
            "검색된 단지 선택",
            options=labels,
            help="정확한 단지를 선택하세요.",
            key="complex_select",
        )
        sel_item = next((s for s in suggestions if s["label"] == sel_label), None)

        confirm_btn = st.button("✅ 이 단지로 확정", use_container_width=True)

        if confirm_btn and sel_item:
            with st.spinner("KB부동산에서 단지 정보를 가져오는 중..."):
                complex_meta = fetch_complex_id(sel_item["textTemp"])

            if not complex_meta or not complex_meta.get("complex_id"):
                st.error("단지 ID를 찾을 수 없습니다. 다른 검색어를 시도해 보세요.")
            else:
                cid = complex_meta["complex_id"]
                with st.spinner("KB 시세를 불러오는 중..."):
                    prices = fetch_complex_price(cid)

                st.session_state["my_complex_id"]    = cid
                st.session_state["my_name"]          = complex_meta["name"]
                st.session_state["my_addr"]          = complex_meta["addr"]
                st.session_state["my_units"]         = complex_meta["units"]
                st.session_state["my_completion"]    = complex_meta["completion"]
                st.session_state["my_prices"]        = prices
                if prices:
                    st.session_state["my_current_price"] = prices[0].get("매매일반거래가", 0)
                st.success("✅ 단지 정보 확정!")

    elif search_keyword.strip():
        st.warning("검색 결과가 없습니다. 다른 키워드로 검색해 보세요.")

    # ── 확정된 내 집 정보 카드 ──────────────────────────────────────
    if st.session_state.get("my_name"):
        with st.container(border=True):
            st.markdown(f"**{st.session_state['my_name']}**")
            st.caption(st.session_state.get("my_addr", ""))

            c1, c2 = st.columns(2)
            with c1:
                st.metric("세대수",   f"{st.session_state.get('my_units', '-')}세대")
            with c2:
                st.metric("입주년월", st.session_state.get("my_completion", "-"))

            # 면적별 시세 선택 (KB API 응답 기준)
            prices = st.session_state.get("my_prices", [])
            if prices:
                price_map = {}
                for p in prices:
                    area = p.get("공급면적평", "?")
                    amt  = int(p.get("매매일반거래가", 0) or 0)
                    key  = f"{area}평  ·  {man_to_eok_str(amt)}"
                    price_map[key] = amt

                chosen = st.selectbox("면적 선택 (KB시세 연동)", list(price_map.keys()))
                st.session_state["my_current_price"] = price_map[chosen]
                st.metric(
                    "현재 KB매매시세",
                    man_to_eok_str(st.session_state["my_current_price"]),
                )

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════
    # STEP 1 계속 ▸ 매수 시점(연·월) + 매수가 (억 단위 소수점 입력)
    # ══════════════════════════════════════════════════════════════════
    st.subheader("💰 매수 시점 및 매수가 입력")

    # ── 연도·월 selectbox (기본값: 2023년 4월) ──────────────────────
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        purchase_year = st.selectbox(
            "매수 연도",
            options=list(range(2000, 2027)),
            index=23,                         # 2023 - 2000 = 23
            format_func=lambda y: f"{y}년",
            key="purchase_year",
        )
    with p_col2:
        purchase_month = st.selectbox(
            "매수 월",
            options=list(range(1, 13)),
            index=3,                          # 4월 → 0-based index 3
            format_func=lambda m: f"{m}월",
            key="purchase_month",
        )

    # 화면 표시용 날짜 문자열 (동적으로 변경)
    purchase_date_str = f"{purchase_year}년 {purchase_month}월"

    # ── 매수가 입력 ──────────────────────────────────────────────────
    purchase_eok = st.number_input(
        f"{purchase_date_str} 매수가 (억 원)",
        min_value=0.0,
        max_value=500.0,
        value=7.4,
        step=0.1,
        format="%.1f",
        help="예) 13.4 입력 → 13억 4,000만 원으로 자동 환산됩니다.",
    )
    # 내부 연산용 만원 단위 역산 (예: 13.4억 → 134,000만원)
    my_purchase_price_man = round(purchase_eok * 10000)

    # 동적 안내 문구: 연·월 + 금액 실시간 반영
    if purchase_eok > 0:
        st.caption(
            f"입력 정보: **{purchase_date_str} 매수가 {format_price_kor(purchase_eok)}**"
        )


# ═══════════════════════════════════════════════════════════════════════
# ░░  메인 화면  ░░
# ═══════════════════════════════════════════════════════════════════════

st.title("🏙️ AI 갈아타기 & 상급지 스카우터")

# ── 서비스 이용 가이드 ──────────────────────────────────────────────
with st.expander("📖 서비스 이용 가이드 (클릭하여 펼치기/접기)", expanded=True):
    g1, g2, g3 = st.columns(3)

    with g1:
        st.markdown(
            """
            <div style="background:#EFF6FF;border-left:4px solid #3B82F6;
                        padding:14px 16px;border-radius:6px;min-height:130px;">
            <b>① STEP 1 · 좌측 사이드바</b><br><br>
            내 아파트 이름을 검색하고 정확한 단지를 선택합니다.<br>
            이어서 <b>매수 시점(연·월)과 매수가</b>를 억 단위로 입력하세요.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with g2:
        st.markdown(
            """
            <div style="background:#F0FDF4;border-left:4px solid #22C55E;
                        padding:14px 16px;border-radius:6px;min-height:130px;">
            <b>② STEP 2 · 메인 화면 대시보드</b><br><br>
            아래 <b>서울·수도권 14~16억 아파트 목록</b>에서<br>
            원하는 타겟 아파트 행을 <b>마우스로 클릭</b>하면<br>
            즉시 자금 분석이 활성화됩니다.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with g3:
        st.markdown(
            """
            <div style="background:#FFF7ED;border-left:4px solid #F97316;
                        padding:14px 16px;border-radius:6px;min-height:130px;">
            <b>③ STEP 3 · AI 분석</b><br><br>
            하단의 <b>[🤖 AI 갈아타기 전략 분석]</b> 버튼을 클릭하면<br>
            GPT가 두 단지의 자산 가치를 비교하고<br>
            전문적인 갈아타기 컨설팅 리포트를 생성합니다.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 데이터 정적 갱신 주기 안내 캡션 (매주 금요일 갱신)
    st.caption(
        "※ 본 부동산 시세 정보는 매주 금요일에 갱신되는 정적 데이터셋을 기반으로 합니다."
    )

st.markdown("---")

# ── CSV 로드 (모든 평형 행 포함) ────────────────────────────────────
df_all = load_apartment_data()

# ── 대시보드 요약 메트릭 ─────────────────────────────────────────────
# 단지 수: 단지ID 기준 고유값 / 시세 통계: 단지별 대표 1행으로 계산
df_dedup = df_all.dropna(subset=["KB매매시세(만원)"]).drop_duplicates(subset="단지ID")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("총 단지 수",  f"{df_all['단지ID'].nunique():,}개")
with m2:
    st.metric("평균 KB시세", man_to_eok_str(int(df_dedup["KB매매시세(만원)"].mean())))
with m3:
    st.metric("최저 시세",   man_to_eok_str(int(df_all["KB매매시세(만원)"].min())))
with m4:
    st.metric("최고 시세",   man_to_eok_str(int(df_all["KB매매시세(만원)"].max())))

st.markdown("---")

# ── 필터 섹션 ─────────────────────────────────────────────────────────
st.subheader("🔍 타겟 단지 검색 · 필터")

fc1, fc2, fc3 = st.columns([1, 1, 2])

with fc1:
    # 지역 필터 옵션을 df_all 전체에서 추출
    region_opts = ["전체"] + sorted(df_all["지역"].dropna().unique().tolist())
    sel_region  = st.selectbox("지역 (시·구)", region_opts)

with fc2:
    # 선택된 지역 기준으로 동 목록 추출
    base_dong = df_all if sel_region == "전체" else df_all[df_all["지역"] == sel_region]
    dong_opts = (
        ["전체"] + sorted(base_dong["동"].dropna().unique().tolist())
        if "동" in df_all.columns else ["전체"]
    )
    sel_dong = st.selectbox("동", dong_opts)

with fc3:
    keyword = st.text_input("아파트명 검색 (타겟용)", placeholder="예: 힐스테이트")

# ── 필터 적용 (df_all 기반 → 모든 평형 행 포함) ─────────────────────
df_filt = df_all.copy()
if sel_region != "전체":
    df_filt = df_filt[df_filt["지역"] == sel_region]
if sel_dong != "전체" and "동" in df_filt.columns:
    df_filt = df_filt[df_filt["동"] == sel_dong]
if keyword.strip():
    df_filt = df_filt[df_filt["아파트명"].str.contains(keyword.strip(), na=False)]

# reset_index 필수: on_select 이벤트의 행 인덱스가 0-based 순번이어야 함
df_filt = df_filt.reset_index(drop=True)

# ── 검색 결과 요약 + 행 클릭 안내 ──────────────────────────────────
st.markdown(
    f"**검색 결과:** {df_filt['단지ID'].nunique():,}개 단지 "
    f"/ 총 {len(df_filt):,}개 평형 유형 &nbsp;&nbsp;"
    f"<span style='color:#6B7280;font-size:0.85em;'>👆 원하는 행을 클릭하면 즉시 타겟으로 선택됩니다</span>",
    unsafe_allow_html=True,
)

disp_cols = [c for c in [
    "아파트명", "지역", "동", "세대수", "준공년월",
    "공급면적(평)", "KB매매시세(만원)", "KB매매시세",
    "도로명주소", "단지ID",
] if c in df_filt.columns]

# ─────────────────────────────────────────────────────────────────────
# [수정2] on_select="rerun": 행 클릭 시 즉시 리런 → selectbox 불필요
#         selection_mode="single-row": 단일 행만 선택 허용
# ─────────────────────────────────────────────────────────────────────
event = st.dataframe(
    df_filt[disp_cols],
    on_select="rerun",
    selection_mode="single-row",
    use_container_width=True,
    height=380,
    column_config={
        "KB매매시세(만원)": st.column_config.NumberColumn("KB시세(만원)",  format="%d"),
        "세대수":           st.column_config.NumberColumn("세대수",        format="%d세대"),
        "단지ID":           st.column_config.NumberColumn("단지ID",        format="%d"),
        "공급면적(평)":     st.column_config.NumberColumn("공급면적(평)",  format="%.2f평"),
    },
    hide_index=True,
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════
# 선택된 행 → target_row 매핑 + 대출 규제 연산
# ═══════════════════════════════════════════════════════════════════════
target_row      = None
loan_limit_man  = 0
cash_needed_man = 0
gap_man         = 0

# event.selection.rows: 클릭된 행의 0-based 인덱스 리스트
selected_indices = event.selection.rows

if selected_indices:
    idx        = selected_indices[0]
    target_row = df_filt.iloc[idx]  # df_filt는 reset_index 완료 상태

    # ── 대출 규제 3단계 연산 ──────────────────────────────────────
    tgt_price_for_loan = int(target_row.get("KB매매시세(만원)", 0))
    my_cur_for_loan    = int(st.session_state.get("my_current_price", 0))
    loan_limit_man     = calc_loan_limit(tgt_price_for_loan)
    cash_needed_man    = tgt_price_for_loan - loan_limit_man
    gap_man            = cash_needed_man - my_cur_for_loan

    # ── 선택된 타겟 정보 카드 ─────────────────────────────────────
    area     = target_row.get("공급면적(평)", "-")
    area_str = (
        f"{area:.2f}".rstrip("0").rstrip(".")
        if isinstance(area, float) else str(area)
    )
    pv = target_row.get("KB매매시세(만원)", 0)

    with st.container(border=True):
        st.markdown("**✅ 선택된 타겟 아파트 정보**")

        # 기본 스펙 5컬럼
        tc1, tc2, tc3, tc4, tc5 = st.columns(5)
        with tc1:
            st.metric("단지명",    target_row.get("아파트명", "-"))
        with tc2:
            st.metric("KB시세",    man_to_eok_str(int(pv)) if pd.notna(pv) else "-")
        with tc3:
            st.metric("세대수",    f"{int(target_row.get('세대수', 0)):,}세대")
        with tc4:
            st.metric("준공년월",  str(target_row.get("준공년월", "-")))
        with tc5:
            st.metric("선택 평형", f"{area_str}평")

        # ── 대출 규제 기반 필요현금 분석 ─────────────────────────
        st.markdown(
            "**💳 대출 규제 기반 필요현금 분석**  "
            "<small style='color:#888;'>가계부채 관리방안 적용 — "
            "15억 이하 6억 / 15~25억 4억 / 25억 초과 2억</small>",
            unsafe_allow_html=True,
        )
        lc1, lc2, lc3 = st.columns(3)
        with lc1:
            st.metric("주담대 한도", man_to_eok_str(loan_limit_man))
        with lc2:
            st.metric("타겟 매수 필요 현금", man_to_eok_str(cash_needed_man))
        with lc3:
            gap_label = man_to_eok_str(abs(gap_man))
            gap_delta = "현금 부족" if gap_man > 0 else "현금 여유"
            st.metric(
                "최종 추가자금 Gap",
                gap_label,
                delta=gap_delta,
                delta_color="inverse" if gap_man > 0 else "normal",
            )

else:
    # [수정5] Empty State: 타겟 미선택 시 안내 문구 (에러 없이 깔끔하게 처리)
    st.info("💡 타겟 아파트를 표에서 선택하면 상세 자금 분석이 활성화됩니다.")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════
# [수정3] 체급 비교 대시보드 — 내 집 vs 타겟 나란히 비교
#         내 집 정보 + 타겟 선택이 모두 완료된 경우에만 렌더링
# ═══════════════════════════════════════════════════════════════════════
my_cur_price_ss = int(st.session_state.get("my_current_price", 0))

if st.session_state.get("my_name") and target_row is not None:
    st.subheader("⚖️ 체급 비교 대시보드")

    left_col, right_col = st.columns(2)

    with left_col:
        with st.container(border=True):
            st.markdown("##### 🏠 내 집 현재 스펙")

            # 매수 이후 수익률 사전 계산
            if my_purchase_price_man > 0 and my_cur_price_ss > 0:
                gain_pct_dash = (
                    (my_cur_price_ss - my_purchase_price_man)
                    / my_purchase_price_man * 100
                )
            else:
                gain_pct_dash = 0.0

            st.metric("단지명",     st.session_state.get("my_name", "-"))
            st.metric(
                "현재 KB매매시세",
                man_to_eok_str(my_cur_price_ss),
                delta=f"{gain_pct_dash:+.1f}% ({purchase_date_str} 대비)",
            )
            st.metric(
                f"{purchase_date_str} 매수가",
                format_price_kor(purchase_eok),
            )
            st.metric("입주년월",   st.session_state.get("my_completion", "-"))

    with right_col:
        with st.container(border=True):
            st.markdown("##### 🎯 타겟 아파트 스펙")

            tgt_pv       = target_row.get("KB매매시세(만원)", 0)
            tgt_area_d   = target_row.get("공급면적(평)", "-")
            tgt_area_str = (
                f"{tgt_area_d:.2f}".rstrip("0").rstrip(".")
                if isinstance(tgt_area_d, float) else str(tgt_area_d)
            )
            # 내 집 대비 시세 차액 계산
            price_diff = int(tgt_pv) - my_cur_price_ss

            st.metric("단지명",  target_row.get("아파트명", "-"))
            st.metric(
                "현재 KB매매시세",
                man_to_eok_str(int(tgt_pv)),
                delta=(
                    f"내 집 대비 {man_to_eok_str(abs(price_diff))} "
                    f"{'높음' if price_diff > 0 else '낮음'}"
                ),
                delta_color="inverse" if price_diff > 0 else "normal",
            )
            st.metric("선택 평형", f"{tgt_area_str}평")
            st.metric("준공년월",  str(target_row.get("준공년월", "-")))

    st.markdown("---")

# ── AI 분석 버튼 ────────────────────────────────────────────────────
analyze_btn = st.button(
    "🤖 AI 갈아타기 전략 분석",
    type="primary",
    use_container_width=True,
    disabled=(target_row is None),
)

if analyze_btn:

    # ── 사전 유효성 검사 ──────────────────────────────────────────
    errors = []
    if not OPENAI_AVAILABLE:
        errors.append("`openai` 패키지가 없습니다. `pip install openai`를 실행해 주세요.")
    if not api_key:
        errors.append("OpenAI API Key가 없습니다. 사이드바에서 입력해 주세요.")
    if not st.session_state.get("my_name"):
        errors.append("내 아파트 정보를 먼저 검색·확정해 주세요. (사이드바 STEP 1)")
    if my_purchase_price_man <= 0:
        errors.append(f"{purchase_date_str} 매수가를 입력해 주세요. (사이드바)")
    if target_row is None:
        errors.append("갈아탈 아파트를 표에서 클릭하여 선택해 주세요.")

    for err in errors:
        st.error(f"❌ {err}")

    if not errors:

        # ── 내 집 데이터 ───────────────────────────────────────────
        my_name       = st.session_state.get("my_name", "알 수 없음")
        my_units      = st.session_state.get("my_units", "알 수 없음")
        my_completion = st.session_state.get("my_completion", "알 수 없음")
        my_cur_price  = int(st.session_state.get("my_current_price", 0))

        # 자산 상승률 계산 (만원 단위)
        if my_purchase_price_man > 0 and my_cur_price > 0:
            gain_pct = (my_cur_price - my_purchase_price_man) / my_purchase_price_man * 100
            gain_amt = my_cur_price - my_purchase_price_man
        else:
            gain_pct, gain_amt = 0.0, 0

        # ── 타겟 아파트 데이터 ─────────────────────────────────────
        tgt_name       = target_row.get("아파트명", "알 수 없음")
        tgt_region     = target_row.get("지역", "")
        tgt_dong       = target_row.get("동", "")
        tgt_units      = int(target_row.get("세대수", 0))
        tgt_completion = str(target_row.get("준공년월", "알 수 없음"))
        tgt_area_raw   = target_row.get("공급면적(평)", "알 수 없음")
        tgt_area       = (
            f"{tgt_area_raw:.2f}".rstrip("0").rstrip(".")
            if isinstance(tgt_area_raw, float) else str(tgt_area_raw)
        )
        tgt_price   = int(target_row.get("KB매매시세(만원)", 0))
        tgt_address = target_row.get("도로명주소", f"{tgt_region} {tgt_dong}".strip())

        # ── GPT 시스템 프롬프트 (가계부채 전문가 페르소나 포함) ───
        system_prompt = (
            "너는 대한민국 최고의 자산관리사이자 부동산 갈아타기 전문 컨설턴트야. "
            "현업 전문가 입장에서 날카롭고 객관적인 리포트를 작성해 줘. "
            "수치 근거를 토대로 명확한 판단을 내리고, 시장 리스크도 균형 있게 언급해 줘. "
            "또한 너는 가계부채 관리방안 대출 규제를 완벽히 이해하는 금융 전문가야. "
            "타겟 아파트 가격에 따라 주담대 한도(15억 이하→6억 / 15~25억→4억 / 25억 초과→2억)가 "
            "달라지는 규제를 연산 데이터 기반으로 팩트 체크하고, "
            "섹션 4에서 DSR·신용대출 활용 방안 등 구체적 재무 제언을 반드시 포함해. "
            "리포트는 반드시 마크다운 형식으로 출력해."
        )

        user_prompt = f"""아래 두 아파트 데이터를 기반으로 '갈아타기 전략 리포트'를 작성해 줘.

---

## 📌 내 현재 아파트
- 단지명                   : {my_name}
- 총 세대수                : {my_units}세대
- 입주(준공)년월           : {my_completion}
- {purchase_date_str} 매수가 : {format_price_kor(purchase_eok)}  ({my_purchase_price_man:,}만원)
- 현재 KB매매시세          : {man_to_eok_str(my_cur_price)}  ({my_cur_price:,}만원)
- {purchase_date_str} 대비 상승률 : {gain_pct:+.1f}%  ({gain_amt:+,}만원)

## 🎯 갈아탈 타겟 아파트
- 단지명        : {tgt_name}
- 주소          : {tgt_address}
- 총 세대수     : {tgt_units:,}세대
- 준공년월      : {tgt_completion}
- 선택 공급면적 : {tgt_area}평
- 현재 KB시세   : {man_to_eok_str(tgt_price)}  ({tgt_price:,}만원)

## 💳 대출 규제 분석 (가계부채 관리방안)
- 주담대 한도             : {man_to_eok_str(loan_limit_man)}
- 타겟 매수 필요 현금      : {man_to_eok_str(cash_needed_man)}
- 최종 추가 자금 Gap       : {man_to_eok_str(abs(gap_man))} {'부족' if gap_man > 0 else '여유'}

---

아래 4개 섹션 구조로 마크다운 리포트를 작성해 줘:

## 1. 두 단지의 자산 가치 비교 (연식·세대수 측면)
(연식, 세대수, 입지 관점에서 두 단지를 객관적으로 비교)

## 2. 동기간 자산 상승률 비교 패러다임
(내 집의 {purchase_date_str} 이후 상승률과 타겟 아파트 시세 수준을 비교하며 향후 상승 잠재력 분석)

## 3. 갈아타기 시 실거주·환금성 이점 분석
(실거주—학군·편의시설·연식 등—과 환금성—세대수·유동성—의 이점 및 리스크 분석)

## 4. 최종 이동 타이밍 및 재무 제언
(현시점 갈아타기 권장 여부에 대한 명확한 판단, 타이밍 조언, DSR·신용대출 활용 방안 등 구체적 재무 제언 반드시 포함)
"""

        # ── GPT API 호출 ───────────────────────────────────────────
        try:
            client_gpt = OpenAI(api_key=api_key)

            with st.spinner("🤖 AI가 부동산 가치 및 갈아타기 시뮬레이션을 분석 중입니다..."):
                response = client_gpt.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    temperature=0.65,
                    max_tokens=2500,
                )

            report_text = response.choices[0].message.content

            # ── 리포트 헤더 요약 메트릭 3종 ───────────────────────
            st.markdown("---")
            st.markdown("## 📊 AI 갈아타기 전략 리포트")

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric(
                    "현재 집 KB시세",
                    man_to_eok_str(my_cur_price),
                    delta=f"{gain_pct:+.1f}% ({purchase_date_str} 대비)",
                )
            with col_b:
                st.metric("타겟 집 KB시세", man_to_eok_str(tgt_price))
            with col_c:
                diff = tgt_price - my_cur_price
                st.metric(
                    "추가 필요 자금 추정",
                    man_to_eok_str(abs(diff)),
                    delta="갈아타기 방향" if diff > 0 else "차익 발생",
                    delta_color="inverse" if diff > 0 else "normal",
                )

            st.markdown("---")
            st.markdown(f"**분석 대상:** {my_name}  →  {tgt_name} ({tgt_area}평)")
            st.markdown("---")

            # ────────────────────────────────────────────────────────
            # [수정4] st.tabs — GPT 응답을 ## 1. / ## 2. / ## 3. / ## 4. 기준으로
            #         분할하여 탭별 렌더링 (긴 텍스트 벽 방지)
            # ────────────────────────────────────────────────────────
            # 줄 시작 기준 ## N. 앞에서 분할 (lookahead 사용)
            raw_parts = re.split(r'\n(?=##\s*[1-4]\.)', "\n" + report_text.strip())

            # 섹션 번호 → 본문 딕셔너리 구성
            section_map: dict = {}
            for part in raw_parts:
                part = part.strip()
                if not part:
                    continue
                m = re.match(r'^##\s*([1-4])\.', part)
                if m:
                    section_map[int(m.group(1))] = part

            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 자산 가치 비교",
                "📈 상승률 패러다임",
                "🏫 실거주·환금성",
                "💡 재무 & 대출 제언",
            ])

            with tab1:
                st.markdown(section_map.get(1, "_섹션 1 내용을 파싱하지 못했습니다._"))
            with tab2:
                st.markdown(section_map.get(2, "_섹션 2 내용을 파싱하지 못했습니다._"))
            with tab3:
                st.markdown(section_map.get(3, "_섹션 3 내용을 파싱하지 못했습니다._"))
            with tab4:
                st.markdown(section_map.get(4, "_섹션 4 내용을 파싱하지 못했습니다._"))

            st.info(
                "⚠️ 본 리포트는 AI가 생성한 참고용 분석이며, "
                "실제 투자·매매 결정은 반드시 전문가 상담을 통해 신중히 검토하시기 바랍니다."
            )

        except Exception as e:
            st.error(f"❌ GPT API 호출 오류: {e}")

# ── 푸터 ────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("데이터 출처: KB부동산  |  AI 분석 엔진: OpenAI GPT-4o")
