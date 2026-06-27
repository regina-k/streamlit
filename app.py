"""
AI 기반 개인 맞춤형 부동산 분석 및 대출 제안 서비스
──────────────────────────────────────────────────
신한은행 AI Intensive 7조 | 이동욱 담당

UI 오케스트레이터 — 비즈니스 로직은 modules/ 에 위임한다.
"""

import os
import re
import hashlib
import json
from difflib import SequenceMatcher

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import (
    AREA_TYPES,
    HOUSEHOLD_TYPES,
    OPENAI_CHAT_MODEL_LABEL,
    PURPOSE_OPTIONS,
)
from modules.kb_api import fetch_search_suggestions, fetch_complex_id, fetch_complex_price
from modules.data_loader import load_kb_apt_data, load_ml_timeseries, filter_apartments
from modules.utils import format_price_kor, man_to_eok_str
from modules.loan_calculator import (
    calc_loan_limit,
    calc_ltv,
    calc_dsr,
    calc_cash_needed,
    recommend_loan_products,
)
from modules.ml_predictor import predict_apartment_growth_horizons
from modules.rag_advisor import get_loan_advice

# ── 페이지 설정 ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI 부동산 분석 & 대출 제안 서비스",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --app-primary: #2563eb;
        --app-ink: #111827;
        --app-muted: #6b7280;
        --app-line: #e5e7eb;
    }
    .stApp {
        background: #ffffff;
        color: var(--app-ink);
    }
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--app-line);
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--app-line);
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    div[data-testid="stTabs"] button[role="tab"] {
        font-weight: 700;
    }
    .ux-hero {
        border: 1px solid var(--app-line);
        border-radius: 8px;
        padding: 18px 20px;
        margin: 2px 0 18px;
        background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    }
    .ux-hero strong {
        color: var(--app-primary);
    }
    .ux-note {
        color: var(--app-muted);
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── 캐시 래퍼 ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="CSV 데이터를 불러오는 중...")
def _cached_load_kb_apt_data() -> pd.DataFrame:
    return load_kb_apt_data()


@st.cache_data(show_spinner="시계열 데이터를 불러오는 중...")
def _cached_load_ml_timeseries() -> pd.DataFrame:
    return load_ml_timeseries()


def _display_text(value, fallback: str = "데이터 없음") -> str:
    if value is None:
        return fallback
    if isinstance(value, float) and pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text and text not in {"-", "nan", "None"} else fallback


def _positive_numeric_series(df: pd.DataFrame, column: str | None) -> pd.Series:
    if df is None or df.empty or not column or column not in df.columns:
        return pd.Series(dtype=float)
    values = pd.to_numeric(df[column], errors="coerce")
    return values[values.gt(0)]


def _confidence_label(value: str | None) -> str:
    labels = {"high": "높음", "medium": "보통", "low": "낮음"}
    return labels.get(str(value or "").lower(), "확인 필요")


def _normalize_search_text(value: str) -> str:
    text = str(value or "").lower()
    replacements = {
        "레미안": "래미안",
        "레미": "래미",
        "힐스테잇": "힐스테이트",
        "아이파크": "아이파크",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return re.sub(r"[^0-9a-z가-힣]", "", text)


def _name_match_score(query: str, name: str) -> float:
    query_norm = _normalize_search_text(query)
    name_norm = _normalize_search_text(name)
    if not query_norm or not name_norm:
        return 0.0
    if query_norm in name_norm:
        return 1.0
    if len(query_norm) < 3:
        return 0.0
    window_scores = [
        SequenceMatcher(None, query_norm, name_norm[i : i + len(query_norm)]).ratio()
        for i in range(0, max(len(name_norm) - len(query_norm) + 1, 1))
    ]
    return max([SequenceMatcher(None, query_norm, name_norm).ratio(), *window_scores])


def _apply_name_search(df: pd.DataFrame, keyword: str | None) -> pd.DataFrame:
    keyword = str(keyword or "").strip()
    if not keyword or df is None or df.empty:
        return df

    name_col = "아파트명" if "아파트명" in df.columns else "단지명"
    if name_col not in df.columns:
        return df

    result = df.copy()
    names = result[name_col].fillna("").astype(str)
    normalized_query = _normalize_search_text(keyword)
    normalized_names = names.apply(_normalize_search_text)
    exact_mask = names.str.contains(keyword, case=False, na=False, regex=False)
    normalized_mask = normalized_names.str.contains(normalized_query, na=False, regex=False)

    if exact_mask.any():
        result = result.loc[exact_mask].copy()
        result["검색유사도"] = 100
        return result
    if normalized_mask.any():
        result = result.loc[normalized_mask].copy()
        result["검색유사도"] = 98
        return result.sort_values([name_col], ascending=True)

    scores = names.apply(lambda name: _name_match_score(keyword, name))
    keep_mask = scores.ge(0.72)
    result = result.loc[keep_mask].copy()
    if result.empty:
        return result
    result["검색유사도"] = (scores.loc[result.index] * 100).round(0).astype(int)
    return result.sort_values(["검색유사도", name_col], ascending=[False, True])


def _prepare_apartment_results(df: pd.DataFrame, price_column: str | None, user_cash_man: int) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    result = df.copy()
    if price_column and price_column in result.columns:
        prices = pd.to_numeric(result[price_column], errors="coerce").fillna(0)
        result["예상대출한도(만원)"] = prices.apply(calc_loan_limit).astype(int)
        result["필요자기자금(만원)"] = (prices - result["예상대출한도(만원)"]).clip(lower=0).astype(int)
        result["자금여유(만원)"] = int(user_cash_man or 0) - result["필요자기자금(만원)"]
    return result


def _candidate_key(row: pd.Series | dict, price_column: str | None) -> str:
    complex_id = row.get("단지ID", "")
    area_serial_no = row.get("면적일련번호", "")
    price = row.get(price_column, "") if price_column else ""
    return f"{complex_id}|{area_serial_no}|{price}"


def _apply_growth_scores(df: pd.DataFrame, price_column: str | None, score_map: dict[str, float]) -> pd.DataFrame:
    if df is None or df.empty or not score_map:
        return df
    result = df.copy()
    result["AI예측상승률(1년)"] = [
        score_map.get(_candidate_key(row, price_column))
        for _, row in result.iterrows()
    ]
    return result


def _target_prediction_key(row: pd.Series | dict, price_column: str | None) -> str:
    return _candidate_key(row, price_column)


def _clean_context_value(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value.item() if hasattr(value, "item") else value


def _area_type_label(row: pd.Series | dict, selected_area_type: str | None = None) -> str | None:
    for column in ["평형유형", "면적유형", "주택형"]:
        value = _clean_context_value(row.get(column))
        if value not in (None, ""):
            return str(value)
    if selected_area_type and selected_area_type != "전체":
        return selected_area_type
    exclusive_m2 = _clean_context_value(row.get("전용면적(m2)"))
    if exclusive_m2 is None:
        return None
    area = float(exclusive_m2)
    for label, upper in [("40㎡이하", 40), ("60㎡이하", 60), ("85㎡이하", 85), ("102㎡이하", 102), ("135㎡이하", 135)]:
        if area <= upper:
            return label
    return "135㎡초과"


def _build_target_advisor_context(
    row: pd.Series | dict,
    price_column: str | None,
    region_column: str | None,
    selected_area_type: str | None,
) -> dict:
    address_value = _clean_context_value(row.get("지역"))
    if address_value in (None, "") and region_column:
        address_value = _clean_context_value(row.get(region_column))
    return {
        "name": _clean_context_value(row.get("단지명") or row.get("name")),
        "address": address_value,
        "region": _clean_context_value(row.get(region_column)) if region_column else None,
        "complex_id": _clean_context_value(row.get("단지ID")),
        "area_serial_no": _clean_context_value(row.get("면적일련번호")),
        "price_man": _clean_context_value(row.get(price_column)) if price_column else None,
        "jeonse_price_man": _clean_context_value(row.get("KB전세시세(만원)")),
        "jeonse_ratio_pct": _clean_context_value(row.get("전세가율")),
        "area_type": _area_type_label(row, selected_area_type),
        "supply_area_pyeong": _clean_context_value(row.get("공급면적(평)")),
        "exclusive_area_pyeong": _clean_context_value(row.get("전용면적(평)")),
        "units": _clean_context_value(row.get("세대수")),
        "households_by_size": _clean_context_value(row.get("세대수(평형)")),
        "completion": _clean_context_value(row.get("준공년월")),
        "property_type": _clean_context_value(row.get("물건종류")),
        "floor_area_ratio": _clean_context_value(row.get("용적률")),
        "building_coverage_ratio": _clean_context_value(row.get("건폐율")),
        "monthly_sale_change_pct": _clean_context_value(row.get("월간매매변동률")),
        "monthly_jeonse_change_pct": _clean_context_value(row.get("월간전세변동률")),
    }


def _build_home_advisor_context() -> dict:
    current_price = int(
        st.session_state.get("my_current_price", 0)
        or st.session_state.get("manual_my_current_price_man", 0)
        or 0
    )
    name = str(st.session_state.get("my_name", "") or "").strip()
    if not name and current_price <= 0:
        return {}
    return {
        "name": name or "직접 입력 보유 주택",
        "address": st.session_state.get("my_addr"),
        "current_price": current_price,
        "purchase_price": my_purchase_price_man,
        "purchase_date": purchase_date_str,
        "units": st.session_state.get("my_units"),
        "completion": st.session_state.get("my_completion"),
    }


def _advisor_context_key(*contexts: dict) -> str:
    serialized = json.dumps(contexts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _get_target_horizon_predictions(row: pd.Series | dict, price_column: str | None) -> dict | None:
    key = _target_prediction_key(row, price_column)
    cache = st.session_state.setdefault("target_horizon_predictions", {})
    if key in cache:
        return cache[key]
    if not price_column or not row.get(price_column):
        return None
    result = predict_apartment_growth_horizons(
        complex_id=row.get("단지ID"),
        area_serial_no=row.get("면적일련번호"),
        current_price_manwon=row.get(price_column),
        horizons=("12m", "36m", "60m"),
    )
    cache[key] = result
    return result


def _score_growth_candidates(df: pd.DataFrame, price_column: str | None, limit: int = 30) -> dict[str, float]:
    scores: dict[str, float] = {}
    if df is None or df.empty or not price_column:
        return scores

    required = {"단지ID", "면적일련번호", price_column}
    if not required.issubset(df.columns):
        return scores

    for _, row in df.head(limit).iterrows():
        key = _candidate_key(row, price_column)
        try:
            result = predict_apartment_growth_horizons(
                complex_id=row.get("단지ID"),
                area_serial_no=row.get("면적일련번호"),
                current_price_manwon=row.get(price_column),
                horizons=("12m",),
            )
            scores[key] = float(result["predictions"][0]["predicted_growth_pct"])
        except Exception:
            continue
    return scores


def _format_result_table(df: pd.DataFrame, price_column: str | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    display = pd.DataFrame(index=df.index)
    display["_row_id"] = range(len(df))
    column_map = [
        ("단지명", "단지명"),
        ("시군구", "지역"),
        ("세대수", "세대수"),
        ("공급면적(평)", "공급면적"),
        ("전용면적(평)", "전용면적"),
        (price_column, "매매시세"),
        ("필요자기자금(만원)", "필요자기자금"),
        ("자금여유(만원)", "자금여유"),
        ("AI예측상승률(1년)", "AI예측(1년)"),
        ("월간매매변동률", "월간매매변동률"),
    ]
    for source, label in column_map:
        if source and source in df.columns:
            display[label] = df[source]

    for money_col in ["매매시세", "필요자기자금", "자금여유"]:
        if money_col in display.columns:
            display[money_col] = display[money_col].apply(
                lambda v: man_to_eok_str(v) if pd.notna(v) else "데이터 없음"
            )
    for area_col in ["공급면적", "전용면적"]:
        if area_col in display.columns:
            display[area_col] = display[area_col].apply(
                lambda v: f"{float(v):.1f}평" if pd.notna(v) else "데이터 없음"
            )
    if "세대수" in display.columns:
        display["세대수"] = display["세대수"].apply(
            lambda v: f"{int(v):,}세대" if pd.notna(v) else "데이터 없음"
        )
    if "AI예측(1년)" in display.columns:
        display["AI예측(1년)"] = display["AI예측(1년)"].apply(
            lambda v: f"{float(v):+.1f}%" if pd.notna(v) else "계산 전"
        )
    if "월간매매변동률" in display.columns:
        display["월간매매변동률"] = display["월간매매변동률"].apply(
            lambda v: f"{float(v):+.2f}%" if pd.notna(v) else "데이터 없음"
        )
    return display


# ═══════════════════════════════════════════════════════════════════════
# 사이드바
# ═══════════════════════════════════════════════════════════════════════

env_key = os.getenv("OPENAI_API_KEY", "").strip()
api_key = env_key

purchase_year = int(st.session_state.get("purchase_year", 2023))
purchase_month = int(st.session_state.get("purchase_month", 4))
purchase_eok = float(st.session_state.get("purchase_eok_value", 7.4))
purchase_date_str = f"{purchase_year}년 {purchase_month}월"
my_purchase_price_man = round(purchase_eok * 10000)

with st.sidebar:
    st.title("⚙️ 실행 상태")
    with st.expander("AI 연결 상태", expanded=False):
        if env_key:
            st.success("환경변수의 OpenAI API Key로 AI 분석을 사용할 수 있습니다.")
        else:
            st.warning("OPENAI_API_KEY가 없어 AI 어드바이저만 비활성화됩니다.")
    st.caption("필수 프로파일은 1번 탭에서 입력합니다. 보유 주택 정보는 선택 입력입니다.")


# ═══════════════════════════════════════════════════════════════════════
# 메인 화면 — 3개 탭
# ═══════════════════════════════════════════════════════════════════════

st.title("🏙️ AI 기반 부동산 분석 & 대출 제안 서비스")
st.markdown(
    """
    <div class="ux-hero">
      <strong>갈아타기 후보를 숫자로 비교하세요.</strong><br/>
      KB 시세, 대출 여력, ML 상승률 예측을 한 흐름에서 확인하도록 정리했습니다.
      <div class="ux-note">흰색 화면을 유지하면서 핵심 지표가 먼저 보이도록 구성했습니다.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab2, tab1, tab3 = st.tabs(["👤 내 투자 프로파일", "🔍 단지 탐색", "📊 AI 종합 분석"])

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
            f"""
            **이 서비스를 사용하는 방법**

            1. **Tab 1 (투자 프로파일)**에서 가구 형태, 소득, 자본금 등을 입력하고 저장하세요.
            2. 보유 주택을 함께 비교하고 싶다면 같은 탭의 **선택 입력**을 펼쳐 입력하세요.
            3. **Tab 2 (단지 탐색)**에서 필터를 적용해 갈아타기 후보 단지를 탐색하세요.
            4. 원하는 단지를 클릭하면 자동으로 **대출 규제·자금 분석**이 수행됩니다.
            5. **Tab 3 (AI 종합 분석)**에서 ML 가격 예측과 AI 어드바이저 분석을 확인하세요.

            > 💡 **데이터 출처:** KB부동산 시세 / **AI 엔진:** {OPENAI_CHAT_MODEL_LABEL}
            """
        )

    # ── 대시보드 요약 메트릭 4종 ─────────────────────────────────────
    if df_all is not None and not df_all.empty:
        total_count = len(df_all)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("📦 총 단지 수", f"{total_count:,}개")
        with m2:
            positive_prices = _positive_numeric_series(df_all, price_col)
            if price_col and not positive_prices.empty:
                avg_price = positive_prices.mean()
                st.metric("📊 평균 시세", man_to_eok_str(int(avg_price)))
            else:
                st.metric("📊 평균 시세", "데이터 없음")
        with m3:
            if price_col and not positive_prices.empty:
                min_price = positive_prices.min()
                st.metric("📉 최저 시세", man_to_eok_str(int(min_price)))
            else:
                st.metric("📉 최저 시세", "데이터 없음")
        with m4:
            if price_col and not positive_prices.empty:
                max_price = positive_prices.max()
                st.metric("📈 최고 시세", man_to_eok_str(int(max_price)))
            else:
                st.metric("📈 최고 시세", "데이터 없음")
    else:
        st.warning("⚠️ 데이터를 불러오지 못했습니다. CSV 파일 경로를 확인하세요.")

    st.markdown("---")
    st.subheader("🔍 타겟 단지 검색 · 필터")

    # ── 필터 UI ──────────────────────────────────────────────────────
    with st.container():
        f_col1, f_col3 = st.columns(2)
        sel_dong = "전체"

        with f_col1:
            if region_col and df_all is not None:
                region_options = ["전체"] + sorted(df_all[region_col].dropna().unique().tolist())
                sel_region = st.selectbox("지역 (시군구)", region_options, key="filter_region")
            else:
                sel_region = "전체"
                st.selectbox("지역 (시군구)", ["전체"], key="filter_region")

        with f_col3:
            keyword_filter = st.text_input("단지명 검색", placeholder="예: 래미안", key="filter_keyword")

        f_col4, f_col5, f_col6 = st.columns(3)

        with f_col4:
            # 시세 범위 슬라이더 (억 단위, 천만원 step)
            if price_col and df_all is not None:
                valid_price_values = _positive_numeric_series(df_all, price_col)
                if valid_price_values.empty:
                    price_min_raw, price_max_raw = 0, 999_999_999
                else:
                    price_min_raw = int(valid_price_values.min())
                    price_max_raw = int(valid_price_values.max())
                price_min_eok = round(price_min_raw / 10000, 1)
                price_max_eok = round(price_max_raw / 10000, 1)
                price_range_eok = st.slider(
                    "시세 범위 (억 원)",
                    min_value=price_min_eok,
                    max_value=price_max_eok,
                    value=(price_min_eok, price_max_eok),
                    step=0.1,
                    format="%.1f억",
                    key="filter_price_range",
                )
                price_range = (round(price_range_eok[0] * 10000), round(price_range_eok[1] * 10000))
                st.caption(f"{price_range[0]:,} ~ {price_range[1]:,} 만원")
            else:
                price_range = (0, 999_999_999)

        with f_col5:
            # 세대수 범위 (최소/최대 직접 입력)
            if units_col and df_all is not None:
                units_min_raw = int(df_all[units_col].dropna().min())
                units_max_raw = int(df_all[units_col].dropna().max())
                u_col1, u_col2 = st.columns(2)
                with u_col1:
                    units_min = st.number_input(
                        "세대수 최소",
                        min_value=units_min_raw,
                        max_value=units_max_raw,
                        value=units_min_raw,
                        step=100,
                        format="%d",
                        key="filter_units_min",
                    )
                with u_col2:
                    units_max = st.number_input(
                        "세대수 최대",
                        min_value=units_min_raw,
                        max_value=units_max_raw,
                        value=units_max_raw,
                        step=100,
                        format="%d",
                        key="filter_units_max",
                    )
                units_range = (units_min, units_max)
                st.caption(f"{units_min:,} ~ {units_max:,} 세대")
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

    df_filt = _apply_name_search(df_filt, keyword_filter)

    profile_for_filter = st.session_state.get("user_profile", {})
    user_cash_man = round(profile_for_filter.get("available_cash_eok", 0) * 10000) if profile_for_filter else 0
    df_filt = _prepare_apartment_results(df_filt, price_col, user_cash_man)

    score_map = st.session_state.get("candidate_growth_scores", {})
    df_filt = _apply_growth_scores(df_filt, price_col, score_map)

    score_candidate_limit = 5
    score_ready = df_filt is not None and 0 < len(df_filt) <= 1500
    score_col1, score_col2 = st.columns([2, 3])
    with score_col1:
        score_requested = st.button(
            "AI 상승률 계산",
            use_container_width=True,
            key="score_candidate_growth",
            disabled=not score_ready,
        )
    with score_col2:
        if score_ready:
            st.caption(
                f"현재 필터 결과의 상위 {score_candidate_limit}개 단지/평형을 계산합니다. "
                "첫 계산은 모델 로딩 때문에 20~30초 걸릴 수 있습니다."
            )
        else:
            st.caption("후보가 1,500개 이하가 되도록 지역·동·단지명·가격 필터를 먼저 좁히면 AI 상승률 계산이 열립니다.")

    if score_requested:
        with st.spinner("후보별 1년 상승률을 계산하는 중입니다..."):
            new_scores = _score_growth_candidates(df_filt, price_col, limit=score_candidate_limit)
        if new_scores:
            merged_scores = {**score_map, **new_scores}
            st.session_state["candidate_growth_scores"] = merged_scores
            st.session_state["show_scored_candidates_only_toggle"] = True
            df_filt = _apply_growth_scores(df_filt.drop(columns=["AI예측상승률(1년)"], errors="ignore"), price_col, merged_scores)
            st.success(f"{len(new_scores)}개 후보의 AI 상승률을 계산했습니다.")
        else:
            st.warning("현재 조건에서 계산 가능한 후보를 찾지 못했습니다.")

    has_scored_candidates = "AI예측상승률(1년)" in df_filt.columns and df_filt["AI예측상승률(1년)"].notna().any()
    if has_scored_candidates:
        if "show_scored_candidates_only_toggle" not in st.session_state:
            st.session_state["show_scored_candidates_only_toggle"] = True
        show_scored_only = st.toggle(
            "AI 계산 후보만 보기",
            key="show_scored_candidates_only_toggle",
            help="정렬을 바꿔도 방금 계산한 후보만 비교하고 싶을 때 켜두세요.",
        )
        if show_scored_only:
            df_filt = df_filt[df_filt["AI예측상승률(1년)"].notna()].copy()

    sort_options = ["AI예측(1년) 높은 순", "이름이 비슷한 순", "필요자기자금 낮은 순", "매매시세 낮은 순", "매매시세 높은 순", "월간매매변동률 높은 순"]
    sort_choice = st.radio(
        "정렬 기준",
        options=sort_options,
        index=0,
        horizontal=True,
        key="result_sort_order",
    )
    if sort_choice == "필요자기자금 낮은 순" and "필요자기자금(만원)" in df_filt.columns:
        df_filt = df_filt.sort_values("필요자기자금(만원)", ascending=True)
    elif sort_choice == "AI예측(1년) 높은 순" and "AI예측상승률(1년)" in df_filt.columns:
        df_filt = df_filt.sort_values("AI예측상승률(1년)", ascending=False, na_position="last")
    elif sort_choice == "이름이 비슷한 순" and "검색유사도" in df_filt.columns:
        df_filt = df_filt.sort_values("검색유사도", ascending=False)
    elif sort_choice == "매매시세 낮은 순" and price_col:
        df_filt = df_filt.sort_values(price_col, ascending=True)
    elif sort_choice == "매매시세 높은 순" and price_col:
        df_filt = df_filt.sort_values(price_col, ascending=False)
    elif sort_choice == "월간매매변동률 높은 순" and "월간매매변동률" in df_filt.columns:
        df_filt = df_filt.sort_values("월간매매변동률", ascending=False)
    elif keyword_filter.strip() and "검색유사도" in df_filt.columns:
        sort_cols = ["검색유사도"]
        ascending = [False]
        if "자금여유(만원)" in df_filt.columns:
            sort_cols.append("자금여유(만원)")
            ascending.append(False)
        df_filt = df_filt.sort_values(sort_cols, ascending=ascending)
    elif "자금여유(만원)" in df_filt.columns and price_col:
        df_filt = df_filt.assign(_affordable=df_filt["자금여유(만원)"] >= 0).sort_values(
            ["_affordable", "자금여유(만원)", price_col],
            ascending=[False, False, True],
        ).drop(columns=["_affordable"])

    st.session_state["apartment_search_context"] = {
        "region": sel_region if sel_region != "전체" else "전체",
        "keyword": keyword_filter.strip() or None,
        "price_min_man": int(price_range[0]),
        "price_max_man": int(price_range[1]),
        "units_min": int(units_range[0]),
        "units_max": int(units_range[1]),
        "area_type": sel_area_type if sel_area_type != "전체" else "전체",
        "sort_choice": sort_choice,
    }

    df_filt = df_filt.reset_index(drop=True)
    st.caption(f"🏘️ 검색 결과: **{len(df_filt):,}개** 단지")

    # ── 데이터 테이블 (선택 가능) ────────────────────────────────────
    if df_filt is not None and not df_filt.empty:
        display_df = _format_result_table(df_filt, price_col)
        event = st.dataframe(
            display_df.drop(columns=["_row_id"], errors="ignore"),
            use_container_width=True,
            height=320,
            on_select="rerun",
            selection_mode="single-row",
            key="apt_table",
        )

        # 선택된 행 추출
        selected_rows = event.selection.get("rows", []) if hasattr(event, "selection") else []
        if selected_rows:
            source_idx = int(display_df.iloc[selected_rows[0]].get("_row_id", selected_rows[0]))
            target_row = df_filt.iloc[source_idx].to_dict()
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
                        ltv        = calc_ltv(target_price_man, loan_limit)
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

        if target_price_man > 0:
            st.markdown("##### 선택 단지 AI 예측")
            try:
                with st.spinner("선택 단지의 1년·3년·5년 예측을 불러오는 중입니다..."):
                    horizon_result = _get_target_horizon_predictions(target_row, price_col)
                prediction_items = (horizon_result or {}).get("predictions", [])
                if prediction_items:
                    pred_cols = st.columns(len(prediction_items))
                    for pred, pred_col in zip(prediction_items, pred_cols):
                        months = int(pred.get("horizon_months", 0))
                        label = {12: "1년", 36: "3년", 60: "5년"}.get(months, f"{months}개월")
                        growth_pct = float(pred.get("predicted_growth_pct", 0.0))
                        estimated_price = int(target_price_man * (1 + growth_pct / 100))
                        interval = pred.get("prediction_interval_p80", {}) or {}
                        half_width = interval.get("half_width_pctp")
                        confidence = _confidence_label(pred.get("confidence"))
                        with pred_col:
                            with st.container(border=True):
                                st.markdown(f"**{label} 후**")
                                st.metric("예상 상승률", f"{growth_pct:+.1f}%")
                                st.metric("추정 시세", man_to_eok_str(estimated_price))
                                if half_width is not None:
                                    st.caption(f"신뢰도 {confidence} · P80 ±{float(half_width):.1f}%p")
                                else:
                                    st.caption(f"신뢰도 {confidence}")
                    st.caption(f"모델: {_display_text((horizon_result or {}).get('model_version'), '모델 확인 필요')}")
                else:
                    st.info("선택 단지 예측값을 계산할 수 없습니다.")
            except Exception as e:
                st.warning(f"선택 단지 예측을 불러오지 못했습니다: {e}")

        # ── 선택 단지 시계열 추이 ────────────────────────────────────
        complex_id = target_row.get("단지ID")
        area_serial_no = target_row.get("면적일련번호")
        if complex_id is not None and area_serial_no is not None:
            try:
                ts_df = _cached_load_ml_timeseries()
                if {"단지ID", "면적일련번호", "기준년월"}.issubset(ts_df.columns):
                    ts_slice = ts_df[
                        (ts_df["단지ID"].astype(str) == str(int(float(complex_id))))
                        & (ts_df["면적일련번호"].astype(str) == str(int(float(area_serial_no))))
                    ].copy()
                    if not ts_slice.empty:
                        ts_slice["기준월"] = pd.to_datetime(ts_slice["기준년월"].astype(str), format="%Y%m", errors="coerce")
                        ts_slice = ts_slice.sort_values("기준월")
                        chart_cols = [
                            col
                            for col in ["KB매매시세(만원)", "KB전세시세(만원)", "실거래매매평균(만원)", "실거래전세평균(만원)"]
                            if col in ts_slice.columns
                        ]
                        if chart_cols:
                            st.markdown("##### 📈 선택 단지 가격 추이")
                            st.line_chart(
                                ts_slice.set_index("기준월")[chart_cols],
                                height=260,
                                use_container_width=True,
                            )
                    else:
                        st.info("선택한 평형의 시계열 데이터는 아직 연결되지 않았습니다.")
            except Exception as e:
                st.warning(f"시계열 차트를 불러오지 못했습니다: {e}")

        # ── 내 집 + 타겟 체급 비교 대시보드 ─────────────────────────
        my_price_man = st.session_state.get("my_current_price", 0) or st.session_state.get("manual_my_current_price_man", 0)
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

            profile = st.session_state.get("user_profile", {})
            available_cash_man = round(profile.get("available_cash_eok", 0) * 10000) if profile else 0
            existing_loan_man = int(profile.get("existing_loan_man", 0) or 0) if profile else 0
            sale_equity_man = max(int(my_price_man) - existing_loan_man, 0)
            target_loan_man = calc_loan_limit(target_price_man)
            target_cash_needed_man = max(target_price_man - target_loan_man, 0)
            net_cash_gap_man = available_cash_man + sale_equity_man - target_cash_needed_man

            cmp4, cmp5, cmp6 = st.columns(3)
            with cmp4:
                st.metric("매도 후 예상 자기자본", man_to_eok_str(sale_equity_man))
            with cmp5:
                st.metric("타겟 필요 자기자금", man_to_eok_str(target_cash_needed_man))
            with cmp6:
                st.metric(
                    "갈아타기 후 잔여/부족",
                    man_to_eok_str(abs(int(net_cash_gap_man))),
                    delta="잔여" if net_cash_gap_man >= 0 else "부족",
                    delta_color="normal" if net_cash_gap_man >= 0 else "inverse",
                )


# ──────────────────────────────────────────────────────────────────────
# Tab 2: 투자 프로파일 입력
# ──────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("👤 내 투자 프로파일")
    st.markdown("가구 형태, 자산, 소득, 기존 대출만 입력해도 단지별 대출 한도와 AI 분석을 볼 수 있습니다.")

    with st.expander("선택 입력: 보유 주택 정보와 매수 이력", expanded=False):
        st.caption("갈아타기 리포트에서 보유 주택 매도 후 자기자본과 대상 단지 필요자금을 비교할 때만 사용합니다.")
        home_col1, home_col2 = st.columns(2)

        with home_col1:
            search_keyword = st.text_input(
                "내 아파트 이름",
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
                labels = [s["label"] for s in suggestions]
                sel_label = st.selectbox("검색된 단지 선택", options=labels, key="complex_select")
                sel_item = next((s for s in suggestions if s["label"] == sel_label), None)

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

            if st.session_state.get("my_name"):
                with st.container(border=True):
                    st.markdown(f"**{st.session_state['my_name']}**")
                    st.caption(st.session_state.get("my_addr", ""))

                    c1, c2 = st.columns(2)
                    with c1:
                        units_value = _display_text(st.session_state.get("my_units"), "확인 전")
                        st.metric("세대수", f"{units_value}세대" if units_value != "확인 전" else units_value)
                    with c2:
                        st.metric("입주년월", _display_text(st.session_state.get("my_completion"), "확인 전"))

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

        with home_col2:
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
                min_value=0.0,
                max_value=500.0,
                value=7.4,
                step=0.1,
                format="%.1f",
                key="purchase_eok_value",
            )
            my_purchase_price_man = round(purchase_eok * 10000)

            if purchase_eok > 0:
                st.caption(f"입력 정보: **{purchase_date_str} 매수가 {format_price_kor(purchase_eok)}**")

            manual_current_eok = st.number_input(
                "현재 보유 주택 시세 직접 입력 (억 원)",
                min_value=0.0,
                max_value=500.0,
                value=float(st.session_state.get("manual_my_current_price_man", 0) or 0) / 10000,
                step=0.1,
                format="%.1f",
                help="KB 검색이 어렵거나 보유 주택을 빠르게 비교하고 싶을 때 직접 입력하세요.",
                key="manual_current_home_price",
            )
            st.session_state["manual_my_current_price_man"] = round(manual_current_eok * 10000)
            if manual_current_eok > 0:
                st.caption(f"현재 시세 직접 입력: **{format_price_kor(manual_current_eok)}**")

    st.markdown("---")

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
        existing_loan_eok = st.number_input(
            "현재 보유 대출 (억 원)",
            min_value=0.0,
            max_value=50.0,
            value=round(float(saved_profile.get("existing_loan_man", 0)) / 10000, 1),
            step=0.1,
            format="%.1f",
            key="profile_existing_loan",
            help="주택담보대출, 신용대출 등 현재 상환 중인 모든 대출의 잔액 합계",
        )
        existing_loan_man = round(existing_loan_eok * 10000)
        st.caption(f"= {existing_loan_man:,} 만원")

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
        annual_income_chunman = st.number_input(
            "부부합산 연소득 (천만 원)",
            min_value=0,
            max_value=100,
            value=int(saved_profile.get("annual_income_man", 8_000)) // 1000,
            step=1,
            format="%d",
            key="profile_income",
            help="세전 기준. 배우자 소득 합산 가능",
        )
        annual_income_man = annual_income_chunman * 1000
        st.caption(f"= {annual_income_man:,} 만원")

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
        st.info("💡 **Tab 1**에서 투자 프로파일을 먼저 입력해 주세요.")
        prereq_ok = False
    if not target_row:
        st.info("💡 **Tab 2**에서 타겟 아파트를 먼저 선택해 주세요.")
        prereq_ok = False
    if not api_key:
        st.warning("⚠️ `.env`의 OPENAI_API_KEY가 없어 AI 어드바이저만 비활성화됩니다.")

    if prereq_ok:
        # ── 타겟 정보 파싱 ────────────────────────────────────────────
        target_price_man = int(target_row.get(price_col, 0) or 0) if price_col else 0
        target_name      = (
            target_row.get("단지명")
            or target_row.get("name")
            or "선택된 단지"
        )
        target_region    = target_row.get(region_col, "") if region_col else ""
        search_context = st.session_state.get("apartment_search_context", {})
        target_area_type = _area_type_label(target_row, search_context.get("area_type")) or "정보 없음"
        target_advisor_context = _build_target_advisor_context(
            target_row,
            price_col,
            region_col,
            search_context.get("area_type"),
        )
        home_advisor_context = _build_home_advisor_context()

        # 탭 2와 동일한 선택 단지·평형 예측 결과를 재사용한다.
        target_horizon_result = None
        target_prediction_error = None
        try:
            target_horizon_result = _get_target_horizon_predictions(target_row, price_col)
            if str((target_horizon_result or {}).get("model_version", "")).upper().startswith("STUB"):
                st.warning("⚠️ ML 모델 분석 준비 중 — 더미 데이터가 표시됩니다.")
        except Exception as exc:
            target_prediction_error = str(exc)
            st.warning("⚠️ 선택 단지의 ML 예측을 불러오지 못했습니다.")

        predictions_by_month = {
            int(pred.get("horizon_months", 0)): pred
            for pred in (target_horizon_result or {}).get("predictions", [])
        }
        target_model_ver = _display_text(
            (target_horizon_result or {}).get("model_version"),
            "모델 확인 필요",
        )

        st.markdown("---")

        # ── ML 가격 예측 카드 ─────────────────────────────────────────
        st.subheader("📈 AI 가격 상승률 예측")
        st.caption(f"대상 지역: **{target_region}** / 평형 유형: **{target_area_type}**")

        ml_col1, ml_col2, ml_col3 = st.columns(3)
        ml_periods = [(12, "1년 후", ml_col1), (36, "3년 후", ml_col2), (60, "5년 후", ml_col3)]

        for horizon_months, period_label, col in ml_periods:
            with col:
                try:
                    if target_prediction_error:
                        raise RuntimeError(target_prediction_error)
                    pred = predictions_by_month.get(horizon_months)
                    if pred is None:
                        raise ValueError(f"{horizon_months}개월 예측 결과가 없습니다.")
                    growth_pct   = pred.get("predicted_growth_pct", 0)
                    confidence   = _confidence_label(pred.get("confidence"))
                    est_price    = int(target_price_man * (1 + growth_pct / 100))

                    with st.container(border=True):
                        st.markdown(f"**{period_label} 예측**")
                        st.metric(
                            "예측 상승률",
                            f"{growth_pct:+.1f}%",
                            delta_color="normal" if growth_pct >= 0 else "inverse",
                        )
                        st.metric("추정 시세", man_to_eok_str(est_price))
                        st.caption(f"신뢰도: {confidence}  |  모델: {target_model_ver}")
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
        loan_context = {
            "loan_limit": 0,
            "ltv": 0.0,
            "dsr": 0.0,
            "cash_needed": 0,
            "asset_gap": 0,
            "is_affordable": None,
            "recommended_products": [],
        }

        if target_price_man > 0:
            try:
                loan_limit    = calc_loan_limit(target_price_man)
                ltv           = calc_ltv(target_price_man, loan_limit)
                dsr           = calc_dsr(loan_limit, annual_income_man, existing_loan_man)
                cash_info     = calc_cash_needed(target_price_man, loan_limit, available_cash_man)
                loan_products = recommend_loan_products(
                    price=target_price_man,
                    loan_limit=loan_limit,
                    annual_income=annual_income_man,
                    household_type=user_profile.get("household_type", ""),
                    purpose=user_profile.get("purpose", ""),
                )
                cash_needed = int(cash_info.get("cash_needed", target_price_man - loan_limit))
                asset_gap = int(cash_info.get("asset_gap", available_cash_man - cash_needed))
                loan_context = {
                    "loan_limit": int(loan_limit),
                    "ltv": float(ltv),
                    "dsr": float(dsr),
                    "cash_needed": cash_needed,
                    "asset_gap": asset_gap,
                    "is_affordable": bool(cash_info.get("is_affordable", asset_gap >= 0)),
                    "recommended_products": loan_products,
                }

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
                    st.metric("필요 자기자금", man_to_eok_str(cash_needed))

                # 자금 여유/부족 배너
                if asset_gap >= 0:
                    st.success(f"✅ 현재 자본금으로 매수 가능합니다. 여유 자금: **{man_to_eok_str(int(asset_gap))}**")
                else:
                    st.error(f"❌ 자금이 부족합니다. 추가 필요 금액: **{man_to_eok_str(int(abs(asset_gap)))}**")

                # 추천 대출 상품
                if loan_products:
                    st.markdown("##### 🏦 추천 대출 상품")
                    for prod in loan_products:
                        with st.container(border=True):
                            p1, p2, p3, p4 = st.columns([3, 2, 2, 1.4])
                            with p1:
                                st.markdown(f"**{prod.get('name', '상품명 미상')}**")
                                st.caption(prod.get("description", ""))
                            with p2:
                                st.metric("금리", _display_text(prod.get("rate"), "상담 필요"))
                            with p3:
                                st.metric("한도", man_to_eok_str(int(prod.get("limit", 0))) if prod.get("limit") else "상담 필요")
                            with p4:
                                if prod.get("url"):
                                    st.link_button("상세보기", prod["url"], use_container_width=True)

            except Exception as e:
                st.error(f"대출 분석 중 오류가 발생했습니다: {e}")
        else:
            st.info("타겟 시세 정보가 없어 대출 분석을 수행할 수 없습니다.")

        st.markdown("---")

        # ── AI 어드바이저 응답 ────────────────────────────────────────
        st.subheader("🤖 AI 어드바이저 분석")

        advisor_payload = {
            "user_profile": user_profile,
            "target_info": target_advisor_context,
            "my_info": home_advisor_context,
            "ml_prediction": target_horizon_result or {},
            "loan_summary": loan_context,
            "search_context": search_context,
        }
        current_advisor_context_key = _advisor_context_key(advisor_payload)
        if st.session_state.get("advisor_context_key") != current_advisor_context_key:
            st.session_state["advisor_context_key"] = current_advisor_context_key
            st.session_state.pop("ai_advice", None)
            st.session_state["advisor_messages"] = []

        if st.button("🤖 AI 분석 실행", type="primary", use_container_width=True, key="run_ai_btn"):
            if not api_key:
                st.error("`.env`에 OPENAI_API_KEY를 설정한 뒤 다시 실행해 주세요.")
            else:
                with st.spinner("AI가 종합 분석 중입니다... (10~30초 소요)"):
                    try:
                        advice = get_loan_advice(
                            api_key=api_key,
                            **advisor_payload,
                        )
                        st.session_state["ai_advice"] = advice
                    except Exception as e:
                        st.error(f"AI 분석 실패: {e}")

        if st.session_state.get("ai_advice"):
            with st.container(border=True):
                st.markdown(st.session_state["ai_advice"])

        st.markdown("##### 이어서 물어보기")
        st.caption("궁금한 규제, 대출 상품, 자금 부족 해소 방법을 대화처럼 이어서 확인할 수 있습니다.")

        if "advisor_messages" not in st.session_state:
            st.session_state["advisor_messages"] = []

        quick_question = st.selectbox(
            "빠른 질문",
            options=[
                "",
                "이 조건에서 가장 먼저 확인할 대출 리스크는?",
                "자금 부족을 줄이는 방법을 알려줘",
                "신혼부부가 확인할 만한 상품은?",
                "DSR 관점에서 조심할 점은?",
            ],
            index=0,
            key="advisor_quick_question",
        ) or None
        send_quick = st.button("선택한 질문 보내기", use_container_width=True, key="send_quick_question")
        typed_question = st.chat_input("대출 규제나 상품에 대해 질문해 보세요")
        pending_question = typed_question or (quick_question if send_quick and quick_question else "")

        for message in st.session_state["advisor_messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if pending_question:
            st.session_state["advisor_messages"].append({"role": "user", "content": pending_question})
            with st.chat_message("user"):
                st.markdown(pending_question)

            if not api_key:
                answer = "`.env`에 OPENAI_API_KEY가 없어 AI 상담 답변을 생성할 수 없습니다."
            else:
                with st.spinner("문서와 현재 조건을 함께 확인하는 중입니다..."):
                    answer = get_loan_advice(
                        api_key=api_key,
                        **advisor_payload,
                        question=pending_question,
                    )
            st.session_state["advisor_messages"].append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)

        st.markdown("---")

        # ── 갈아타기 리포트 ───────────────────────────────────────────
        st.subheader("📋 갈아타기 종합 리포트")

        my_name_val    = st.session_state.get("my_name", "") or "직접 입력 보유 주택"
        my_price_val   = st.session_state.get("my_current_price", 0) or st.session_state.get("manual_my_current_price_man", 0)

        if my_price_val and target_price_man:
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

            profile_existing_loan = int(user_profile.get("existing_loan_man", 0) or 0)
            sale_equity = max(int(my_price_val) - profile_existing_loan, 0)
            needed_cash = cash_needed if "cash_needed" in dir() else max(target_price_man - calc_loan_limit(target_price_man), 0)
            total_available = available_cash_man + sale_equity
            after_move_gap = total_available - needed_cash
            st.markdown("##### 갈아타기 자금 흐름")
            flow1, flow2, flow3, flow4 = st.columns(4)
            with flow1:
                st.metric("보유주택 매도 후 자기자본", man_to_eok_str(sale_equity))
            with flow2:
                st.metric("기존 가용자본", man_to_eok_str(available_cash_man))
            with flow3:
                st.metric("타겟 필요 자기자금", man_to_eok_str(int(needed_cash)))
            with flow4:
                st.metric(
                    "최종 잔여/부족",
                    man_to_eok_str(abs(int(after_move_gap))),
                    delta="잔여" if after_move_gap >= 0 else "부족",
                    delta_color="normal" if after_move_gap >= 0 else "inverse",
                )
        else:
            st.info("보유 주택 시세를 내 투자 프로파일 탭에서 검색하거나 직접 입력하면 갈아타기 리포트가 표시됩니다.")


# ── 푸터 ─────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(f"데이터 출처: KB부동산  |  AI 분석 엔진: {OPENAI_CHAT_MODEL_LABEL}  |  신한은행 AI Intensive 7조")
