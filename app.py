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

    # TODO (이동욱): 서비스 이용 가이드 expander 렌더링
    # TODO (이동욱): 대시보드 요약 메트릭 4종 (단지 수, 평균·최저·최고 시세) 렌더링

    st.markdown("---")
    st.subheader("🔍 타겟 단지 검색 · 필터")

    # TODO (이동욱): 필터 UI (지역/동/키워드/시세범위/세대수/평형) 렌더링
    # TODO (이동욱): filter_apartments(df_all, ...) 호출 후 df_filt 구성
    # TODO (이동욱): st.dataframe(on_select='rerun') 렌더링 및 target_row 추출

    # TODO (이동욱): target_row 선택 시 —
    #   loan_limit = calc_loan_limit(target_price)
    #   cash_info  = calc_cash_needed(target_price, loan_limit, my_asset)
    #   선택된 타겟 정보 카드 + 대출 규제 분석 카드 렌더링

    # TODO (이동욱): 내 집 + 타겟 모두 선택된 경우 체급 비교 대시보드 렌더링


# ──────────────────────────────────────────────────────────────────────
# Tab 2: 투자 프로파일 입력
# ──────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("👤 투자 유형 프로파일 입력")

    # TODO (이동욱): 아래 5개 입력 위젯 렌더링 후 st.session_state['user_profile']에 저장
    #
    # col_a, col_b = st.columns(2)
    # with col_a:
    #   household_type = st.selectbox('가구 형태', HOUSEHOLD_TYPES)
    #   purpose        = st.radio('매매 목적', PURPOSE_OPTIONS)
    # with col_b:
    #   available_cash  = st.number_input('가용자본금 (억 원)', ...)
    #   annual_income   = st.number_input('부부합산연소득 (만원)', ...)
    #   existing_loan   = st.number_input('현재 보유 대출 (만원)', ...)
    #
    # if st.button('프로파일 저장'):
    #   st.session_state['user_profile'] = { ... }
    #   st.success('저장 완료')
    pass


# ──────────────────────────────────────────────────────────────────────
# Tab 3: AI 종합 분석
# ──────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("📊 AI 종합 분석")

    user_profile = st.session_state.get("user_profile")
    target_row   = st.session_state.get("selected_target_row")  # Tab1에서 저장 예정

    # ── STUB 상태 배너 ───────────────────────────────────────────────
    # TODO (이동욱): ml_predictor / rag_advisor STUB 여부를 note 필드로 감지 후 배너 표시
    # 예시:
    # if pred.get('model_version', '').startswith('STUB'):
    #     st.warning('⚠️ ML 모델 분석 준비 중 — 더미 데이터가 표시됩니다.')

    # ── ML 예측 카드 ─────────────────────────────────────────────────
    # TODO (이동욱): predict_price_growth() 1yr/3yr/5yr 3회 호출 후 카드 렌더링
    # 예시:
    # pred_1yr = predict_price_growth(region, area_type, '1yr')
    # pred_3yr = predict_price_growth(region, area_type, '3yr')
    # pred_5yr = predict_price_growth(region, area_type, '5yr')
    # col1, col2, col3 = st.columns(3)
    # with col1: st.metric('1년 예측 상승률', f"{pred_1yr['predicted_growth_pct']:.1f}%")
    # ...

    # ── 대출 한도·DSR 분석 ──────────────────────────────────────────
    # TODO (이동욱): user_profile + target_row 기반으로
    #   calc_ltv / calc_dsr / recommend_loan_products 호출 후 렌더링

    # ── AI 어드바이저 응답 ───────────────────────────────────────────
    # TODO (이동욱): '🤖 AI 분석 실행' 버튼 → get_loan_advice() 호출 후 st.markdown()

    # ── 갈아타기 리포트 (기존 기능 유지) ────────────────────────────
    # TODO (이동욱): Tab1의 GPT 갈아타기 리포트 로직 이관 및 탭 렌더링

    if not user_profile:
        st.info("💡 Tab 2에서 투자 프로파일을 먼저 입력해 주세요.")
    if not target_row:
        st.info("💡 Tab 1에서 타겟 아파트를 먼저 선택해 주세요.")


# ── 푸터 ─────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("데이터 출처: KB부동산  |  AI 분석 엔진: OpenAI GPT-4o  |  신한은행 AI Intensive 7조")
