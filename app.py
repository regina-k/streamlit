"""
AI 기반 개인 맞춤형 부동산 분석 및 대출 제안 서비스
──────────────────────────────────────────────────
신한은행 AI Intensive 7조 | 이동욱 담당

UI 오케스트레이터 — 비즈니스 로직은 modules/ 에 위임한다.
"""

import os

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import HOUSEHOLD_TYPES, PURPOSE_OPTIONS, AREA_TYPES
from modules.kb_api import fetch_search_suggestions, fetch_complex_id, fetch_complex_price
from modules.data_loader import load_kb_apt_data, filter_apartments
from modules.utils import format_price_kor, man_to_eok_str
from modules.loan_calculator import (
    calc_loan_limit,
    calc_ltv,
    calc_dsr,
    calc_cash_needed,
    recommend_loan_products,
)
from modules.ml_predictor import predict_price_growth
from modules.rag_advisor import get_loan_advice

# ── 페이지 설정 ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI 부동산 분석 & 대출 제안 서비스",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 캐시 래퍼 ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="CSV 데이터를 불러오는 중...")
def _cached_load_kb_apt_data() -> pd.DataFrame:
    return load_kb_apt_data()


# ═══════════════════════════════════════════════════════════════════════
# 사이드바
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("🏠 내 집 정보 입력")
    st.markdown("---")

    # ── OpenAI API Key ───────────────────────────────────────────────
    st.subheader("🔑 OpenAI API Key")
    env_key = os.getenv("OPENAI_API_KEY", "").strip()

    if env_key:
        st.info("ℹ️ 환경변수에서 API Key를 읽었습니다. 아래에서 덮어쓸 수 있습니다.")
    else:
        st.warning("⚠️ 환경변수에서 Key를 찾지 못했습니다. 직접 입력해 주세요.")

    manual_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        key="api_key_input",
    ).strip()

    api_key = manual_key if manual_key else env_key
    st.markdown("---")

    # ── STEP 1: 내 아파트 검색 ──────────────────────────────────────
    st.subheader("📍 STEP 1 — 내 아파트 검색")

    search_keyword = st.text_input(
        "아파트 이름을 입력하세요",
        placeholder="예: 래미안 대치",
        key="search_keyword_input",
    )

    suggestions = []
    if search_keyword.strip():
        with st.spinner("단지를 검색 중..."):
            try:
                suggestions = fetch_search_suggestions(search_keyword.strip())
            except Exception as e:
                st.error(f"단지 검색 실패: {e}")

    if suggestions:
        labels    = [s["label"] for s in suggestions]
        sel_label = st.selectbox("검색된 단지 선택", options=labels, key="complex_select")
        sel_item  = next((s for s in suggestions if s["label"] == sel_label), None)

        if st.button("✅ 이 단지로 확정", use_container_width=True):
            if sel_item:
                try:
                    with st.spinner("KB부동산에서 단지 정보를 가져오는 중..."):
                        complex_meta = fetch_complex_id(sel_item["textTemp"])

                    if not complex_meta or not complex_meta.get("complex_id"):
                        st.error("단지 ID를 찾을 수 없습니다.")
                    else:
                        cid = complex_meta["complex_id"]
                        with st.spinner("KB 시세를 불러오는 중..."):
                            prices = fetch_complex_price(cid)

                        st.session_state.update({
                            "my_complex_id":    cid,
                            "my_name":          complex_meta["name"],
                            "my_addr":          complex_meta["addr"],
                            "my_units":         complex_meta["units"],
                            "my_completion":    complex_meta["completion"],
                            "my_prices":        prices,
                            "my_current_price": prices[0].get("매매일반거래가", 0) if prices else 0,
                        })
                        st.success("✅ 단지 정보 확정!")
                except Exception as e:
                    st.error(f"단지 정보 조회 실패: {e}")

    elif search_keyword.strip():
        st.warning("검색 결과가 없습니다.")

    # ── 확정된 내 집 정보 카드 ───────────────────────────────────────
    if st.session_state.get("my_name"):
        with st.container(border=True):
            st.markdown(f"**{st.session_state['my_name']}**")
            st.caption(st.session_state.get("my_addr", ""))

            c1, c2 = st.columns(2)
            with c1:
                st.metric("세대수",   f"{st.session_state.get('my_units', '-')}세대")
            with c2:
                st.metric("입주년월", st.session_state.get("my_completion", "-"))

            prices = st.session_state.get("my_prices", [])
            if prices:
                price_map = {
                    f"{p.get('공급면적평', '?')}평  ·  {man_to_eok_str(int(p.get('매매일반거래가', 0) or 0))}":
                    int(p.get("매매일반거래가", 0) or 0)
                    for p in prices
                }
                chosen = st.selectbox("면적 선택 (KB시세 연동)", list(price_map.keys()))
                st.session_state["my_current_price"] = price_map[chosen]
                st.metric("현재 KB매매시세", man_to_eok_str(st.session_state["my_current_price"]))

    st.markdown("---")

    # ── STEP 1 계속: 매수 시점 + 매수가 ────────────────────────────
    st.subheader("💰 매수 시점 및 매수가 입력")

    p_col1, p_col2 = st.columns(2)
    with p_col1:
        purchase_year = st.selectbox(
            "매수 연도",
            options=list(range(2000, 2027)),
            index=23,
            format_func=lambda y: f"{y}년",
            key="purchase_year",
        )
    with p_col2:
        purchase_month = st.selectbox(
            "매수 월",
            options=list(range(1, 13)),
            index=3,
            format_func=lambda m: f"{m}월",
            key="purchase_month",
        )

    purchase_date_str = f"{purchase_year}년 {purchase_month}월"

    purchase_eok = st.number_input(
        f"{purchase_date_str} 매수가 (억 원)",
        min_value=0.0, max_value=500.0, value=7.4, step=0.1, format="%.1f",
    )
    my_purchase_price_man = round(purchase_eok * 10000)

    if purchase_eok > 0:
        st.caption(f"입력 정보: **{purchase_date_str} 매수가 {format_price_kor(purchase_eok)}**")


# ═══════════════════════════════════════════════════════════════════════
# 메인 화면 — 3개 탭
# ═══════════════════════════════════════════════════════════════════════

st.title("🏙️ AI 기반 부동산 분석 & 대출 제안 서비스")

tab1, tab2, tab3 = st.tabs(["🔍 단지 탐색", "👤 내 투자 프로파일", "📊 AI 종합 분석"])

# ── 공통 데이터 · 컬럼 감지 (탭 전체에서 공유) ─────────────────────────
df_all = _cached_load_kb_apt_data()

# 시세 컬럼 자동 감지
price_col = None
if df_all is not None and not df_all.empty:
    for _candidate in ["KB매매시세(만원)", "매매일반거래가", "시세", "매매가"]:
        if _candidate in df_all.columns:
            price_col = _candidate
            break
    if price_col is None:
        _numeric_cols = df_all.select_dtypes(include="number").columns.tolist()
        price_col = _numeric_cols[0] if _numeric_cols else None

# 지역 / 동 / 세대수 컬럼 자동 감지
region_col = next((c for c in ["시군구", "지역", "구", "시도"] if c in (df_all.columns if df_all is not None else [])), None)
dong_col   = next((c for c in ["법정동", "동", "읍면동"] if c in (df_all.columns if df_all is not None else [])), None)
units_col  = next((c for c in ["세대수", "총세대수", "units"] if c in (df_all.columns if df_all is not None else [])), None)


# ──────────────────────────────────────────────────────────────────────
# Tab 1: 단지 탐색
# ──────────────────────────────────────────────────────────────────────
with tab1:
    # ── 서비스 이용 가이드 ───────────────────────────────────────────
    with st.expander("📖 서비스 이용 가이드", expanded=False):
        st.markdown(
            """
            **이 서비스를 사용하는 방법**

            1. **사이드바**에서 현재 보유한 아파트를 검색하고 면적·매수가를 입력하세요.
            2. **Tab 2 (투자 프로파일)**에서 가구 형태, 소득, 자본금 등을 입력하고 저장하세요.
            3. **Tab 1 (단지 탐색)**에서 필터를 적용해 갈아타기 후보 단지를 탐색하세요.
            4. 원하는 단지를 클릭하면 자동으로 **대출 규제·자금 분석**이 수행됩니다.
            5. **Tab 3 (AI 종합 분석)**에서 ML 가격 예측과 AI 어드바이저 분석을 확인하세요.

            > 💡 **데이터 출처:** KB부동산 시세 / **AI 엔진:** OpenAI GPT-4o
            """
        )

    # ── 대시보드 요약 메트릭 4종 ─────────────────────────────────────
    if df_all is not None and not df_all.empty:
        total_count = len(df_all)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("📦 총 단지 수", f"{total_count:,}개")
        with m2:
            if price_col:
                avg_price = df_all[price_col].dropna().mean()
                st.metric("📊 평균 시세", man_to_eok_str(int(avg_price)))
            else:
                st.metric("📊 평균 시세", "-")
        with m3:
            if price_col:
                min_price = df_all[price_col].dropna().min()
                st.metric("📉 최저 시세", man_to_eok_str(int(min_price)))
            else:
                st.metric("📉 최저 시세", "-")
        with m4:
            if price_col:
                max_price = df_all[price_col].dropna().max()
                st.metric("📈 최고 시세", man_to_eok_str(int(max_price)))
            else:
                st.metric("📈 최고 시세", "-")
    else:
        st.warning("⚠️ 데이터를 불러오지 못했습니다. CSV 파일 경로를 확인하세요.")

    st.markdown("---")
    st.subheader("🔍 타겟 단지 검색 · 필터")

    # ── 필터 UI ──────────────────────────────────────────────────────
    with st.container():
        f_col1, f_col2, f_col3 = st.columns(3)

        with f_col1:
            if region_col and df_all is not None:
                region_options = ["전체"] + sorted(df_all[region_col].dropna().unique().tolist())
                sel_region = st.selectbox("지역 (시군구)", region_options, key="filter_region")
            else:
                sel_region = "전체"
                st.selectbox("지역 (시군구)", ["전체"], key="filter_region")

        with f_col2:
            # 선택된 지역에 따라 동 필터 동적 갱신
            if dong_col and df_all is not None:
                if sel_region != "전체" and region_col:
                    dong_src = df_all[df_all[region_col] == sel_region]
                else:
                    dong_src = df_all
                dong_options = ["전체"] + sorted(dong_src[dong_col].dropna().unique().tolist())
            else:
                dong_options = ["전체"]
            sel_dong = st.selectbox("동", dong_options, key="filter_dong")

        with f_col3:
            keyword_filter = st.text_input("단지명 검색", placeholder="예: 래미안", key="filter_keyword")

        f_col4, f_col5, f_col6 = st.columns(3)

        with f_col4:
            # 시세 범위 슬라이더
            if price_col and df_all is not None:
                price_min_raw = int(df_all[price_col].dropna().min())
                price_max_raw = int(df_all[price_col].dropna().max())
                price_range = st.slider(
                    "시세 범위 (만 원)",
                    min_value=price_min_raw,
                    max_value=price_max_raw,
                    value=(price_min_raw, price_max_raw),
                    step=1000,
                    format="%d만",
                    key="filter_price_range",
                )
            else:
                price_range = (0, 999_999_999)

        with f_col5:
            # 세대수 범위
            if units_col and df_all is not None:
                units_min_raw = int(df_all[units_col].dropna().min())
                units_max_raw = int(df_all[units_col].dropna().max())
                units_range = st.slider(
                    "세대수 범위",
                    min_value=units_min_raw,
                    max_value=units_max_raw,
                    value=(units_min_raw, units_max_raw),
                    step=50,
                    key="filter_units_range",
                )
            else:
                units_range = (0, 99_999)

        with f_col6:
            sel_area_type = st.selectbox(
                "평형 유형",
                options=["전체"] + list(AREA_TYPES),
                key="filter_area_type",
            )

    # ── filter_apartments 호출 ───────────────────────────────────────
    filter_kwargs = {
        "keyword":     keyword_filter if keyword_filter.strip() else None,
        "price_range": price_range,
        "units_range": units_range,
    }
    if sel_region != "전체" and region_col:
        filter_kwargs["region"] = sel_region
    if sel_dong != "전체" and dong_col:
        filter_kwargs["dong"] = sel_dong
    if sel_area_type != "전체":
        filter_kwargs["area_type"] = sel_area_type

    try:
        df_filt = filter_apartments(df_all, **filter_kwargs)
    except TypeError:
        # filter_apartments 시그니처가 다를 경우 안전 폴백: 직접 필터링
        df_filt = df_all.copy() if df_all is not None else pd.DataFrame()
        if keyword_filter.strip() and "단지명" in df_filt.columns:
            df_filt = df_filt[df_filt["단지명"].str.contains(keyword_filter.strip(), na=False)]
        if sel_region != "전체" and region_col and region_col in df_filt.columns:
            df_filt = df_filt[df_filt[region_col] == sel_region]
        if sel_dong != "전체" and dong_col and dong_col in df_filt.columns:
            df_filt = df_filt[df_filt[dong_col] == sel_dong]
        if price_col and price_col in df_filt.columns:
            df_filt = df_filt[
                (df_filt[price_col] >= price_range[0]) &
                (df_filt[price_col] <= price_range[1])
            ]

    st.caption(f"🏘️ 검색 결과: **{len(df_filt):,}개** 단지")

    # ── 데이터 테이블 (선택 가능) ────────────────────────────────────
    if df_filt is not None and not df_filt.empty:
        event = st.dataframe(
            df_filt.reset_index(drop=True),
            use_container_width=True,
            height=320,
            on_select="rerun",
            selection_mode="single-row",
            key="apt_table",
        )

        # 선택된 행 추출
        selected_rows = event.selection.get("rows", []) if hasattr(event, "selection") else []
        if selected_rows:
            target_row = df_filt.iloc[selected_rows[0]].to_dict()
            st.session_state["selected_target_row"] = target_row
        else:
            target_row = st.session_state.get("selected_target_row")
    else:
        st.info("검색 결과가 없습니다. 필터를 조정해 보세요.")
        target_row = st.session_state.get("selected_target_row")

    # ── 선택된 타겟 정보 카드 + 대출 규제 분석 ──────────────────────
    if target_row:
        st.markdown("---")
        st.subheader("🎯 선택된 타겟 단지")

        # 타겟 시세 추출
        target_price_man = int(target_row.get(price_col, 0) or 0) if price_col else 0
        target_name      = (
            target_row.get("단지명")
            or target_row.get("name")
            or target_row.get(list(target_row.keys())[0], "선택된 단지")
        )

        user_profile = st.session_state.get("user_profile", {})
        my_asset_man = round(user_profile.get("available_cash_eok", 0) * 10000) if user_profile else 0

        tc1, tc2 = st.columns(2)

        # 타겟 정보 카드
        with tc1:
            with st.container(border=True):
                st.markdown(f"#### 🏢 {target_name}")
                if region_col and region_col in target_row:
                    st.caption(f"📍 {target_row.get(region_col, '')} {target_row.get(dong_col, '') if dong_col else ''}")
                if units_col and units_col in target_row:
                    st.metric("세대수", f"{int(target_row.get(units_col, 0) or 0):,}세대")
                if price_col:
                    st.metric("매매 시세", man_to_eok_str(target_price_man))

        # 대출 규제 분석 카드
        with tc2:
            with st.container(border=True):
                st.markdown("#### 💳 대출 규제 분석")
                if target_price_man > 0:
                    try:
                        loan_limit = calc_loan_limit(target_price_man)
                        ltv        = calc_ltv(loan_limit, target_price_man)
                        cash_info  = calc_cash_needed(target_price_man, loan_limit, my_asset_man)

                        st.metric("대출 한도",    man_to_eok_str(int(loan_limit)))
                        st.metric("LTV",          f"{ltv:.1f}%")
                        st.metric("필요 자기자금", man_to_eok_str(int(cash_info.get("cash_needed", target_price_man - loan_limit))))

                        gap = cash_info.get("asset_gap", my_asset_man - cash_info.get("cash_needed", 0))
                        if gap >= 0:
                            st.success(f"✅ 자금 여유: {man_to_eok_str(int(gap))}")
                        else:
                            st.error(f"❌ 자금 부족: {man_to_eok_str(int(abs(gap)))}")
                    except Exception as e:
                        st.warning(f"대출 한도 계산 오류: {e}")
                else:
                    st.info("시세 정보가 없어 대출 분석을 수행할 수 없습니다.")

        # ── 내 집 + 타겟 체급 비교 대시보드 ─────────────────────────
        my_price_man = st.session_state.get("my_current_price", 0)
        if my_price_man and my_price_man > 0 and target_price_man > 0:
            st.markdown("---")
            st.subheader("⚖️ 내 집 vs 타겟 체급 비교")

            cmp1, cmp2, cmp3 = st.columns(3)
            with cmp1:
                diff_man = target_price_man - my_price_man
                st.metric(
                    "시세 차이",
                    man_to_eok_str(abs(int(diff_man))),
                    delta=f"{'▲ 상향' if diff_man > 0 else '▼ 하향'} 갈아타기",
                    delta_color="inverse" if diff_man > 0 else "normal",
                )
            with cmp2:
                ratio = (target_price_man / my_price_man * 100) if my_price_man else 0
                st.metric("타겟/현재 시세 비율", f"{ratio:.1f}%")
            with cmp3:
                gain = my_price_man - my_purchase_price_man
                gain_pct = (gain / my_purchase_price_man * 100) if my_purchase_price_man else 0
                st.metric(
                    "현 보유 차익",
                    man_to_eok_str(int(gain)),
                    delta=f"{gain_pct:+.1f}%",
                    delta_color="normal" if gain >= 0 else "inverse",
                )


# ──────────────────────────────────────────────────────────────────────
# Tab 2: 투자 프로파일 입력
# ──────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("👤 투자 유형 프로파일 입력")
    st.markdown("아래 정보를 입력하고 저장하면 Tab 3에서 개인화된 AI 분석이 시작됩니다.")

    # 기존 저장된 값을 기본값으로 로드
    saved_profile = st.session_state.get("user_profile", {})

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("##### 가구 정보")
        household_type = st.selectbox(
            "가구 형태",
            options=HOUSEHOLD_TYPES,
            index=HOUSEHOLD_TYPES.index(saved_profile["household_type"])
                  if saved_profile.get("household_type") in HOUSEHOLD_TYPES else 0,
            key="profile_household",
        )
        purpose = st.radio(
            "매매 목적",
            options=PURPOSE_OPTIONS,
            index=PURPOSE_OPTIONS.index(saved_profile["purpose"])
                  if saved_profile.get("purpose") in PURPOSE_OPTIONS else 0,
            key="profile_purpose",
            horizontal=True,
        )
        existing_loan_man = st.number_input(
            "현재 보유 대출 (만 원)",
            min_value=0,
            max_value=500_000,
            value=int(saved_profile.get("existing_loan_man", 0)),
            step=500,
            format="%d",
            key="profile_existing_loan",
            help="주택담보대출, 신용대출 등 현재 상환 중인 모든 대출의 잔액 합계",
        )

    with col_b:
        st.markdown("##### 자산 · 소득 정보")
        available_cash_eok = st.number_input(
            "가용 자본금 (억 원)",
            min_value=0.0,
            max_value=500.0,
            value=float(saved_profile.get("available_cash_eok", 3.0)),
            step=0.1,
            format="%.1f",
            key="profile_cash",
            help="현금, 예금, 주식 등 즉시 동원 가능한 자산 (현재 주택 매도 차익 포함 가능)",
        )
        annual_income_man = st.number_input(
            "부부합산 연소득 (만 원)",
            min_value=0,
            max_value=100_000,
            value=int(saved_profile.get("annual_income_man", 8_000)),
            step=100,
            format="%d",
            key="profile_income",
            help="세전 기준. 배우자 소득 합산 가능",
        )

        # DSR 미리보기 (실시간)
        target_row_preview = st.session_state.get("selected_target_row")
        if target_row_preview and price_col and target_row_preview.get(price_col):
            preview_price = int(target_row_preview.get(price_col, 0) or 0)
            if preview_price > 0 and annual_income_man > 0:
                try:
                    preview_loan  = calc_loan_limit(preview_price)
                    preview_dsr   = calc_dsr(preview_loan, annual_income_man, existing_loan_man)
                    color = "🟢" if preview_dsr <= 40 else ("🟡" if preview_dsr <= 60 else "🔴")
                    st.info(f"{color} 선택된 타겟 기준 예상 DSR: **{preview_dsr:.1f}%**  (기준: 40% 이하)")
                except Exception:
                    pass

    st.markdown("---")

    # ── 저장 버튼 ─────────────────────────────────────────────────
    if st.button("💾 프로파일 저장", type="primary", use_container_width=True):
        st.session_state["user_profile"] = {
            "household_type":     household_type,
            "purpose":            purpose,
            "available_cash_eok": available_cash_eok,
            "annual_income_man":  annual_income_man,
            "existing_loan_man":  existing_loan_man,
        }
        st.success("✅ 프로파일이 저장되었습니다! Tab 3에서 AI 분석을 확인하세요.")
        st.balloons()

    # ── 저장된 프로파일 요약 표시 ────────────────────────────────────
    if saved_profile:
        with st.expander("📋 현재 저장된 프로파일 보기", expanded=False):
            st.json(saved_profile)


# ──────────────────────────────────────────────────────────────────────
# Tab 3: AI 종합 분석
# ──────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("📊 AI 종합 분석")

    user_profile = st.session_state.get("user_profile")
    target_row   = st.session_state.get("selected_target_row")

    # ── 사전 조건 안내 ───────────────────────────────────────────────
    prereq_ok = True
    if not user_profile:
        st.info("💡 **Tab 2**에서 투자 프로파일을 먼저 입력해 주세요.")
        prereq_ok = False
    if not target_row:
        st.info("💡 **Tab 1**에서 타겟 아파트를 먼저 선택해 주세요.")
        prereq_ok = False
    if not api_key:
        st.warning("⚠️ 사이드바에서 OpenAI API Key를 입력해야 AI 어드바이저를 사용할 수 있습니다.")

    if prereq_ok:
        # ── 타겟 정보 파싱 ────────────────────────────────────────────
        target_price_man = int(target_row.get(price_col, 0) or 0) if price_col else 0
        target_name      = (
            target_row.get("단지명")
            or target_row.get("name")
            or "선택된 단지"
        )
        target_region    = target_row.get(region_col, "") if region_col else ""
        target_area_type = target_row.get("평형유형", target_row.get("면적유형", "중형"))

        # ── STUB 상태 배너 ───────────────────────────────────────────
        try:
            stub_check = predict_price_growth(target_region, target_area_type, "1yr")
            if str(stub_check.get("model_version", "")).upper().startswith("STUB"):
                st.warning("⚠️ ML 모델 분석 준비 중 — 더미 데이터가 표시됩니다.")
        except Exception:
            st.warning("⚠️ ML 예측 모듈을 초기화할 수 없습니다. 더미 데이터가 표시될 수 있습니다.")

        st.markdown("---")

        # ── ML 가격 예측 카드 ─────────────────────────────────────────
        st.subheader("📈 AI 가격 상승률 예측")
        st.caption(f"대상 지역: **{target_region}** / 평형 유형: **{target_area_type}**")

        ml_col1, ml_col2, ml_col3 = st.columns(3)
        ml_periods = [("1yr", "1년 후", ml_col1), ("3yr", "3년 후", ml_col2), ("5yr", "5년 후", ml_col3)]

        for period_key, period_label, col in ml_periods:
            with col:
                try:
                    pred = predict_price_growth(target_region, target_area_type, period_key)
                    growth_pct   = pred.get("predicted_growth_pct", 0)
                    confidence   = pred.get("confidence", "-")
                    model_ver    = pred.get("model_version", "")
                    est_price    = int(target_price_man * (1 + growth_pct / 100))

                    with st.container(border=True):
                        st.markdown(f"**{period_label} 예측**")
                        st.metric(
                            "예측 상승률",
                            f"{growth_pct:+.1f}%",
                            delta_color="normal" if growth_pct >= 0 else "inverse",
                        )
                        st.metric("추정 시세", man_to_eok_str(est_price))
                        st.caption(f"신뢰도: {confidence}  |  모델: {model_ver}")
                except Exception as e:
                    with st.container(border=True):
                        st.markdown(f"**{period_label} 예측**")
                        st.error(f"예측 실패: {e}")

        st.markdown("---")

        # ── 대출 한도 · DSR 분석 ─────────────────────────────────────
        st.subheader("💳 대출 한도 · DSR 분석")

        annual_income_man = user_profile.get("annual_income_man", 0)
        existing_loan_man = user_profile.get("existing_loan_man", 0)
        available_cash_man = round(user_profile.get("available_cash_eok", 0) * 10000)

        if target_price_man > 0:
            try:
                loan_limit    = calc_loan_limit(target_price_man)
                ltv           = calc_ltv(loan_limit, target_price_man)
                dsr           = calc_dsr(loan_limit, annual_income_man, existing_loan_man)
                cash_info     = calc_cash_needed(target_price_man, loan_limit, available_cash_man)
                loan_products = recommend_loan_products(
                    price=target_price_man,
                    loan_limit=loan_limit,
                    annual_income=annual_income_man,
                    household_type=user_profile.get("household_type", ""),
                    purpose=user_profile.get("purpose", ""),
                )

                # 핵심 지표 메트릭
                dl1, dl2, dl3, dl4 = st.columns(4)
                with dl1:
                    st.metric("최대 대출 한도", man_to_eok_str(int(loan_limit)))
                with dl2:
                    ltv_color = "🟢" if ltv <= 40 else ("🟡" if ltv <= 60 else "🔴")
                    st.metric("LTV", f"{ltv_color} {ltv:.1f}%")
                with dl3:
                    dsr_color = "🟢" if dsr <= 40 else ("🟡" if dsr <= 60 else "🔴")
                    st.metric("DSR", f"{dsr_color} {dsr:.1f}%")
                with dl4:
                    cash_needed = int(cash_info.get("cash_needed", target_price_man - loan_limit))
                    st.metric("필요 자기자금", man_to_eok_str(cash_needed))

                # 자금 여유/부족 배너
                asset_gap = available_cash_man - cash_needed
                if asset_gap >= 0:
                    st.success(f"✅ 현재 자본금으로 매수 가능합니다. 여유 자금: **{man_to_eok_str(int(asset_gap))}**")
                else:
                    st.error(f"❌ 자금이 부족합니다. 추가 필요 금액: **{man_to_eok_str(int(abs(asset_gap)))}**")

                # 추천 대출 상품
                if loan_products:
                    st.markdown("##### 🏦 추천 대출 상품")
                    for prod in loan_products:
                        with st.container(border=True):
                            p1, p2, p3 = st.columns([3, 2, 2])
                            with p1:
                                st.markdown(f"**{prod.get('name', '상품명 미상')}**")
                                st.caption(prod.get("description", ""))
                            with p2:
                                st.metric("금리", prod.get("rate", "-"))
                            with p3:
                                st.metric("한도", man_to_eok_str(int(prod.get("limit", 0))) if prod.get("limit") else "-")

            except Exception as e:
                st.error(f"대출 분석 중 오류가 발생했습니다: {e}")
        else:
            st.info("타겟 시세 정보가 없어 대출 분석을 수행할 수 없습니다.")

        st.markdown("---")

        # ── AI 어드바이저 응답 ────────────────────────────────────────
        st.subheader("🤖 AI 어드바이저 분석")

        if st.button("🤖 AI 분석 실행", type="primary", use_container_width=True, key="run_ai_btn"):
            if not api_key:
                st.error("OpenAI API Key를 사이드바에 입력해 주세요.")
            else:
                with st.spinner("AI가 종합 분석 중입니다... (10~30초 소요)"):
                    try:
                        advice = get_loan_advice(
                            api_key=api_key,
                            user_profile=user_profile,
                            target_info={
                                "name":         target_name,
                                "region":       target_region,
                                "price_man":    target_price_man,
                                "area_type":    target_area_type,
                            },
                            my_info={
                                "name":           st.session_state.get("my_name", ""),
                                "current_price":  st.session_state.get("my_current_price", 0),
                                "purchase_price": my_purchase_price_man,
                                "purchase_date":  purchase_date_str,
                            },
                            loan_summary={
                                "loan_limit": int(loan_limit) if "loan_limit" in dir() else 0,
                                "ltv":        ltv if "ltv" in dir() else 0,
                                "dsr":        dsr if "dsr" in dir() else 0,
                            },
                        )
                        st.session_state["ai_advice"] = advice
                    except Exception as e:
                        st.error(f"AI 분석 실패: {e}")

        if st.session_state.get("ai_advice"):
            with st.container(border=True):
                st.markdown(st.session_state["ai_advice"])

        st.markdown("---")

        # ── 갈아타기 리포트 ───────────────────────────────────────────
        st.subheader("📋 갈아타기 종합 리포트")

        my_name_val    = st.session_state.get("my_name", "")
        my_price_val   = st.session_state.get("my_current_price", 0)

        if my_name_val and my_price_val and target_price_man:
            rc1, rc2 = st.columns(2)
            with rc1:
                with st.container(border=True):
                    st.markdown("##### 🏠 현재 보유 아파트")
                    st.markdown(f"**{my_name_val}**")
                    st.metric("매수가",   man_to_eok_str(my_purchase_price_man))
                    st.metric("현재 시세", man_to_eok_str(my_price_val))
                    gain_man = my_price_val - my_purchase_price_man
                    gain_pct = (gain_man / my_purchase_price_man * 100) if my_purchase_price_man else 0
                    st.metric("평가 손익", man_to_eok_str(int(gain_man)), delta=f"{gain_pct:+.1f}%",
                              delta_color="normal" if gain_man >= 0 else "inverse")

            with rc2:
                with st.container(border=True):
                    st.markdown("##### 🎯 갈아타기 타겟")
                    st.markdown(f"**{target_name}**")
                    st.metric("타겟 시세", man_to_eok_str(target_price_man))
                    diff = target_price_man - my_price_val
                    st.metric("추가 필요 자금 (시세 기준)", man_to_eok_str(int(abs(diff))),
                              delta="상향" if diff > 0 else "하향")
                    feasible = available_cash_man >= (cash_needed if "cash_needed" in dir() else diff)
                    st.metric("갈아타기 가능 여부", "✅ 가능" if feasible else "❌ 자금 부족")
        else:
            st.info("내 아파트 정보를 사이드바에서 확정하면 갈아타기 리포트가 표시됩니다.")


# ── 푸터 ─────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("데이터 출처: KB부동산  |  AI 분석 엔진: OpenAI GPT-4o  |  신한은행 AI Intensive 7조")
