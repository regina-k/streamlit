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

# ── 캐시 래퍼 (data_loader는 순수 함수 → app.py에서 캐싱 처리) ──────────
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

# ──────────────────────────────────────────────────────────────────────
# Tab 1: 단지 탐색 (기존 갈아타기 스카우터 기능 유지)
# ──────────────────────────────────────────────────────────────────────
with tab1:
    df_all = _cached_load_kb_apt_data()

    # ── 서비스 이용 가이드 ────────────────────────────────────────────
    with st.expander("📖 서비스 이용 가이드", expanded=False):
        st.markdown("""
        1. **사이드바**에서 내 아파트를 검색하고 확정하세요.
        2. 아래 필터로 관심 단지를 좁힌 뒤 **표에서 타겟 단지를 클릭**하세요.
        3. 선택된 단지의 대출 한도·필요 현금을 자동으로 계산해드립니다.
        4. 내 집과 타겟이 모두 선택되면 **체급 비교 대시보드**가 활성화됩니다.
        """)

    # ── 대시보드 요약 메트릭 4종 ─────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 단지 수",   f"{len(df_all):,}개")
    m2.metric("평균 시세",    man_to_eok_str(int(df_all["매매일반거래가"].mean())) if "매매일반거래가" in df_all.columns else "-")
    m3.metric("최저 시세",    man_to_eok_str(int(df_all["매매일반거래가"].min()))  if "매매일반거래가" in df_all.columns else "-")
    m4.metric("최고 시세",    man_to_eok_str(int(df_all["매매일반거래가"].max()))  if "매매일반거래가" in df_all.columns else "-")

    st.markdown("---")
    st.subheader("🔍 타겟 단지 검색 · 필터")

    # ── 필터 UI ──────────────────────────────────────────────────────
    f1, f2, f3 = st.columns(3)
    with f1:
        regions = ["전체"] + sorted(df_all["시도"].dropna().unique().tolist()) if "시도" in df_all.columns else ["전체"]
        sel_region = st.selectbox("시도", regions)

        dongs = ["전체"]
        if sel_region != "전체" and "시군구" in df_all.columns:
            dongs += sorted(df_all[df_all["시도"] == sel_region]["시군구"].dropna().unique().tolist())
        sel_dong = st.selectbox("시군구", dongs)

    with f2:
        keyword = st.text_input("단지명 검색", placeholder="예: 래미안")

        area_types = ["전체"] + AREA_TYPES if AREA_TYPES else ["전체"]
        sel_area = st.selectbox("평형 유형", area_types)

    with f3:
        price_col_exists = "매매일반거래가" in df_all.columns
        if price_col_exists:
            price_min_raw = int(df_all["매매일반거래가"].min())
            price_max_raw = int(df_all["매매일반거래가"].max())
        else:
            price_min_raw, price_max_raw = 0, 200000

        price_range = st.slider(
            "시세 범위 (만원)",
            min_value=price_min_raw,
            max_value=price_max_raw,
            value=(price_min_raw, price_max_raw),
            step=1000,
            format="%d만",
        )

        unit_max = int(df_all["세대수"].max()) if "세대수" in df_all.columns else 5000
        min_units = st.number_input("최소 세대수", min_value=0, max_value=unit_max, value=0, step=100)

    # ── filter_apartments 호출 ────────────────────────────────────────
    filter_kwargs = dict(
        region=sel_region   if sel_region != "전체" else None,
        dong=sel_dong       if sel_dong   != "전체" else None,
        keyword=keyword     or None,
        area_type=sel_area  if sel_area   != "전체" else None,
        price_min=price_range[0],
        price_max=price_range[1],
        min_units=min_units if min_units > 0 else None,
    )
    # filter_apartments 시그니처가 다를 경우 아래처럼 **kwargs 대신 직접 맞춰주세요
    try:
        df_filt = filter_apartments(df_all, **filter_kwargs)
    except TypeError:
        # 함수 시그니처가 다르면 df_all 그대로 사용 (fallback)
        df_filt = df_all.copy()
        st.warning("⚠️ filter_apartments 시그니처를 확인해주세요.")

    st.caption(f"필터 결과: **{len(df_filt):,}개** 단지")

    # ── 데이터프레임 (클릭 선택) ──────────────────────────────────────
    display_cols = [c for c in [
        "단지명", "시도", "시군구", "매매일반거래가", "공급면적평", "세대수", "입주년월"
    ] if c in df_filt.columns]

    selection = st.dataframe(
        df_filt[display_cols].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="apt_table",
    )

    selected_indices = selection.selection.rows if selection.selection else []
    target_row = None

    if selected_indices:
        target_row = df_filt.iloc[selected_indices[0]]
        st.session_state["selected_target_row"] = target_row

    # ── 타겟 선택 시: 대출 규제 분석 카드 ───────────────────────────
    if target_row is not None:
        target_price = int(target_row.get("매매일반거래가", 0) or 0)
        my_asset_man = int(
            st.session_state.get("my_current_price", 0) - 
            my_purchase_price_man +
            (st.session_state.get("user_profile", {}).get("available_cash_man", 0))
        )

        loan_limit = calc_loan_limit(target_price)
        cash_info  = calc_cash_needed(target_price, loan_limit, max(my_asset_man, 0))

        st.markdown("---")
        st.subheader(f"🏢 선택 단지: {target_row.get('단지명', '—')}")

        tc1, tc2 = st.columns(2)

        with tc1:
            with st.container(border=True):
                st.markdown("**단지 정보**")
                info_items = {
                    "주소":     f"{target_row.get('시도','')} {target_row.get('시군구','')}",
                    "KB 매매시세": man_to_eok_str(target_price),
                    "공급면적": f"{target_row.get('공급면적평', '-')}평",
                    "세대수":   f"{target_row.get('세대수', '-')}세대",
                    "입주년월": str(target_row.get("입주년월", "-")),
                }
                for k, v in info_items.items():
                    st.markdown(f"- **{k}**: {v}")

        with tc2:
            with st.container(border=True):
                st.markdown("**대출 규제 분석**")
                la, lb = st.columns(2)
                la.metric("최대 대출 한도", man_to_eok_str(loan_limit))
                lb.metric("필요 현금",      man_to_eok_str(cash_info.get("cash_needed", 0)))

                ltv = calc_ltv(loan_limit, target_price)
                dsr_val = calc_dsr(
                    loan_limit,
                    st.session_state.get("user_profile", {}).get("annual_income_man", 0),
                )
                lc, ld = st.columns(2)
                lc.metric("LTV",  f"{ltv:.1f}%"   if ltv  else "-")
                ld.metric("DSR",  f"{dsr_val:.1f}%" if dsr_val else "-")

                if cash_info.get("shortfall", 0) > 0:
                    st.error(f"⚠️ 현금 {man_to_eok_str(cash_info['shortfall'])} 부족")
                else:
                    st.success("✅ 자산 범위 내 매수 가능")

    # ── 체급 비교 대시보드 ────────────────────────────────────────────
    my_name  = st.session_state.get("my_name")
    my_price = st.session_state.get("my_current_price", 0)

    if my_name and target_row is not None and target_price > 0 and my_price > 0:
        st.markdown("---")
        st.subheader("⚖️ 체급 비교")

        gap = target_price - my_price
        ratio = target_price / my_price if my_price else 0

        ca, cb, cc = st.columns(3)
        ca.metric("내 집 시세",    man_to_eok_str(my_price))
        cb.metric("타겟 시세",     man_to_eok_str(target_price),
                  delta=man_to_eok_str(abs(gap)) + (" ↑" if gap > 0 else " ↓"))
        cc.metric("시세 배율",     f"{ratio:.2f}x")

        upgrade_cost = gap + cash_info.get("transaction_cost", int(target_price * 0.04))
        st.info(f"💡 갈아타기 예상 추가 비용(취득세·중개비 포함): **{man_to_eok_str(upgrade_cost)}** 수준")


# ──────────────────────────────────────────────────────────────────────
# Tab 2: 투자 프로파일 입력
# ──────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("👤 투자 유형 프로파일 입력")

    # 기존 저장값 불러오기 (재진입 시 유지)
    saved = st.session_state.get("user_profile", {})

    col_a, col_b = st.columns(2)

    with col_a:
        household_type = st.selectbox(
            "가구 형태",
            options=HOUSEHOLD_TYPES,
            index=HOUSEHOLD_TYPES.index(saved["household_type"]) if saved.get("household_type") in HOUSEHOLD_TYPES else 0,
        )
        purpose = st.radio(
            "매매 목적",
            options=PURPOSE_OPTIONS,
            index=PURPOSE_OPTIONS.index(saved["purpose"]) if saved.get("purpose") in PURPOSE_OPTIONS else 0,
            horizontal=True,
        )
        available_cash_eok = st.number_input(
            "가용 자본금 (억 원)",
            min_value=0.0, max_value=500.0,
            value=float(saved.get("available_cash_man", 0)) / 10000,
            step=0.1, format="%.1f",
        )

    with col_b:
        annual_income_man = st.number_input(
            "부부합산 연소득 (만원)",
            min_value=0, max_value=100000,
            value=int(saved.get("annual_income_man", 5000)),
            step=100,
        )
        existing_loan_man = st.number_input(
            "현재 보유 대출 (만원)",
            min_value=0, max_value=500000,
            value=int(saved.get("existing_loan_man", 0)),
            step=500,
        )
        area_type = st.selectbox(
            "선호 평형",
            options=AREA_TYPES,
            index=AREA_TYPES.index(saved["area_type"]) if saved.get("area_type") in AREA_TYPES else 0,
        )

    # ── 요약 미리보기 ─────────────────────────────────────────────────
    st.markdown("---")
    with st.container(border=True):
        st.caption("입력 내용 미리보기")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("가구 형태",   household_type)
        p2.metric("매매 목적",   purpose)
        p3.metric("가용 자본금", f"{available_cash_eok:.1f}억")
        p4.metric("연소득",      f"{annual_income_man:,}만")

        q1, q2, q3 = st.columns(3)
        q1.metric("보유 대출",   f"{existing_loan_man:,}만")
        q2.metric("선호 평형",   area_type)

        # DSR 사전 체크
        if annual_income_man > 0 and existing_loan_man > 0:
            pre_dsr = calc_dsr(existing_loan_man, annual_income_man)
            color = "inverse" if pre_dsr < 40 else "off"
            q3.metric("현재 DSR (기존 대출)", f"{pre_dsr:.1f}%", delta="규제 이하 ✅" if pre_dsr < 40 else "40% 초과 ⚠️", delta_color=color)

    # ── 저장 버튼 ─────────────────────────────────────────────────────
    if st.button("💾 프로파일 저장", use_container_width=True, type="primary"):
        st.session_state["user_profile"] = {
            "household_type":      household_type,
            "purpose":             purpose,
            "available_cash_man":  round(available_cash_eok * 10000),
            "annual_income_man":   annual_income_man,
            "existing_loan_man":   existing_loan_man,
            "area_type":           area_type,
        }
        st.success("✅ 프로파일이 저장되었습니다. Tab 3에서 AI 분석을 실행하세요.")
        st.balloons()
# ──────────────────────────────────────────────────────────────────────
# Tab 3: AI 종합 분석
# ──────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("📊 AI 종합 분석")

    user_profile = st.session_state.get("user_profile")
    target_row   = st.session_state.get("selected_target_row")

    # ── 사전 조건 체크 ────────────────────────────────────────────────
    if not user_profile:
        st.info("💡 Tab 2에서 투자 프로파일을 먼저 입력해 주세요.")
    if target_row is None:
        st.info("💡 Tab 1에서 타겟 아파트를 먼저 선택해 주세요.")

    if not user_profile or target_row is None:
        st.stop()

    # ── 기본값 추출 ───────────────────────────────────────────────────
    target_price      = int(target_row.get("매매일반거래가", 0) or 0)
    target_name       = target_row.get("단지명", "선택 단지")
    region            = target_row.get("시도", "")
    area_type         = user_profile.get("area_type", "")
    annual_income_man = user_profile.get("annual_income_man", 0)
    existing_loan_man = user_profile.get("existing_loan_man", 0)
    available_cash_man= user_profile.get("available_cash_man", 0)
    my_price          = st.session_state.get("my_current_price", 0)
    my_name           = st.session_state.get("my_name", "내 집")

    # ── STUB 배너 ─────────────────────────────────────────────────────
    pred_test = predict_price_growth(region, area_type, "1yr")
    if str(pred_test.get("model_version", "")).upper().startswith("STUB"):
        st.warning("⚠️ ML 모델 준비 중 — 아래 수치는 더미 데이터입니다. 실제 모델 연동 후 정확도가 높아집니다.")

    # ── ML 가격 예측 카드 ─────────────────────────────────────────────
    st.markdown("### 📈 AI 가격 예측")

    with st.spinner("ML 모델 예측 중..."):
        pred_1yr = predict_price_growth(region, area_type, "1yr")
        pred_3yr = predict_price_growth(region, area_type, "3yr")
        pred_5yr = predict_price_growth(region, area_type, "5yr")

    pc1, pc2, pc3 = st.columns(3)

    def _growth_metric(col, label, pred, base_price):
        pct   = pred.get("predicted_growth_pct", 0)
        delta = int(base_price * pct / 100)
        col.metric(
            label,
            f"{pct:+.1f}%",
            delta=man_to_eok_str(abs(delta)) + (" 상승" if delta >= 0 else " 하락"),
            delta_color="normal" if delta >= 0 else "inverse",
        )

    _growth_metric(pc1, "1년 예측 상승률", pred_1yr, target_price)
    _growth_metric(pc2, "3년 예측 상승률", pred_3yr, target_price)
    _growth_metric(pc3, "5년 예측 상승률", pred_5yr, target_price)

    with st.expander("예측 상세 정보 보기"):
        for label, pred in [("1년", pred_1yr), ("3년", pred_3yr), ("5년", pred_5yr)]:
            st.markdown(f"**{label}**: {pred.get('note', '정보 없음')}")

    st.markdown("---")

    # ── 대출 한도 · DSR 분석 ─────────────────────────────────────────
    st.markdown("### 🏦 대출 한도 · DSR 분석")

    loan_limit  = calc_loan_limit(target_price)
    ltv         = calc_ltv(loan_limit, target_price)
    dsr_val     = calc_dsr(loan_limit + existing_loan_man, annual_income_man)
    cash_info   = calc_cash_needed(target_price, loan_limit, available_cash_man)
    products    = recommend_loan_products(
        price=target_price,
        loan_limit=loan_limit,
        household_type=user_profile.get("household_type", ""),
        purpose=user_profile.get("purpose", ""),
        annual_income_man=annual_income_man,
    )

    la, lb, lc, ld = st.columns(4)
    la.metric("최대 대출 한도", man_to_eok_str(loan_limit))
    lb.metric("LTV",           f"{ltv:.1f}%",   delta="규제 이하 ✅" if ltv <= 70 else "규제 초과 ⚠️",
              delta_color="off" if ltv <= 70 else "inverse")
    lc.metric("DSR (합산)",    f"{dsr_val:.1f}%", delta="규제 이하 ✅" if dsr_val < 40 else "40% 초과 ⚠️",
              delta_color="off" if dsr_val < 40 else "inverse")
    ld.metric("필요 현금",     man_to_eok_str(cash_info.get("cash_needed", 0)))

    # 부족 현금 경고
    shortfall = cash_info.get("shortfall", 0)
    if shortfall > 0:
        st.error(f"⚠️ 현금 **{man_to_eok_str(shortfall)}** 부족 — 추가 자금 마련이 필요합니다.")
    else:
        st.success("✅ 보유 자산 범위 내 매수 가능합니다.")

    # 추천 대출 상품
    if products:
        st.markdown("**추천 대출 상품**")
        for p in products:
            with st.container(border=True):
                pa, pb, pc_ = st.columns([3, 1, 1])
                pa.markdown(f"**{p.get('name', '상품명 없음')}**  \n{p.get('description', '')}")
                pb.metric("금리", p.get("rate", "-"))
                pc_.metric("한도", man_to_eok_str(p.get("limit_man", 0)))

    st.markdown("---")

    # ── AI 어드바이저 ─────────────────────────────────────────────────
    st.markdown("### 🤖 AI 어드바이저")

    if not api_key:
        st.warning("⚠️ 사이드바에서 OpenAI API Key를 입력해야 AI 분석을 실행할 수 있습니다.")
    else:
        if st.button("🤖 AI 분석 실행", use_container_width=True, type="primary"):
            advice_payload = {
                "target_name":        target_name,
                "target_price":       target_price,
                "my_name":            my_name,
                "my_price":           my_price,
                "loan_limit":         loan_limit,
                "ltv":                ltv,
                "dsr":                dsr_val,
                "cash_needed":        cash_info.get("cash_needed", 0),
                "shortfall":          shortfall,
                "annual_income_man":  annual_income_man,
                "household_type":     user_profile.get("household_type", ""),
                "purpose":            user_profile.get("purpose", ""),
                "pred_1yr":           pred_1yr.get("predicted_growth_pct", 0),
                "pred_3yr":           pred_3yr.get("predicted_growth_pct", 0),
                "pred_5yr":           pred_5yr.get("predicted_growth_pct", 0),
                "products":           products,
                "api_key":            api_key,
            }

            with st.spinner("AI가 분석 중입니다..."):
                try:
                    advice = get_loan_advice(advice_payload)
                    st.session_state["ai_advice"] = advice
                except Exception as e:
                    st.error(f"AI 분석 실패: {e}")

        if st.session_state.get("ai_advice"):
            with st.container(border=True):
                st.markdown(st.session_state["ai_advice"])

    st.markdown("---")

    # ── 갈아타기 리포트 ───────────────────────────────────────────────
    st.markdown("### 🔄 갈아타기 시뮬레이션")

    if my_price > 0:
        gap            = target_price - my_price
        transaction_cost = int(target_price * 0.04)   # 취득세 + 중개비 근사
        upgrade_total  = gap + transaction_cost

        ra, rb, rc = st.columns(3)
        ra.metric("내 집 시세",       man_to_eok_str(my_price))
        rb.metric("타겟 시세",        man_to_eok_str(target_price),
                  delta=man_to_eok_str(abs(gap)) + (" ↑" if gap > 0 else " ↓"))
        rc.metric("시세 차액",        man_to_eok_str(abs(gap)))

        rd, re = st.columns(2)
        rd.metric("취득세·중개비(약 4%)", man_to_eok_str(transaction_cost))
        re.metric("갈아타기 총 추가비용",  man_to_eok_str(upgrade_total),
                  delta="자산 범위 내" if upgrade_total <= available_cash_man else "자산 초과",
                  delta_color="off" if upgrade_total <= available_cash_man else "inverse")

        # 5년 후 예상 수익 시뮬레이션
        st.markdown("**5년 후 예상 시세 비교**")
        growth_5yr = pred_5yr.get("predicted_growth_pct", 0) / 100
        my_future   = int(my_price    * (1 + growth_5yr))
        tgt_future  = int(target_price * (1 + growth_5yr))

        sa, sb, sc = st.columns(3)
        sa.metric("내 집 5년 후 예상",   man_to_eok_str(my_future))
        sb.metric("타겟 5년 후 예상",    man_to_eok_str(tgt_future))
        sc.metric("5년 후 예상 추가 차익", man_to_eok_str(tgt_future - my_future - upgrade_total),
                  delta="갈아타기 유리" if tgt_future - my_future > upgrade_total else "보유 유리",
                  delta_color="normal" if tgt_future - my_future > upgrade_total else "inverse")

    else:
        st.info("💡 사이드바에서 내 아파트를 선택하면 갈아타기 시뮬레이션이 활성화됩니다.")
# ── 푸터 ─────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("데이터 출처: KB부동산  |  AI 분석 엔진: OpenAI GPT-4o  |  신한은행 AI Intensive 7조")
