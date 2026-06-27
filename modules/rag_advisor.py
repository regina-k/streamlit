"""LangChain RAG 기반 개인화 부동산·대출 어드바이저."""

import os
from pathlib import Path
from typing import Any

from config import (
    OPENAI_CHAT_MODEL,
    OPENAI_MAX_OUTPUT_TOKENS,
    OPENAI_RAG_RETRIEVER_K,
    OPENAI_REASONING_EFFORT,
    OPENAI_REQUEST_TIMEOUT,
    OPENAI_TEXT_VERBOSITY,
    OPENAI_USE_RESPONSES_API,
    VECTOR_STORE_DIR,
)

VECTORSTORE_PATH = str(VECTOR_STORE_DIR / "shinhan_faiss")


def get_loan_advice(
    user_profile: dict | None = None,
    target_apt: dict | None = None,
    ml_prediction: dict | None = None,
    **kwargs,
) -> str:
    """LangChain RAG 기반 맞춤형 대출·투자 어드바이저 응답을 생성한다.

    Args:
        user_profile: 고객 투자 유형 프로파일.
            {
                'household_type': str,      # config.HOUSEHOLD_TYPES 참고
                'purpose': str,             # '실거주' | '투자'
                'available_cash_man': int,  # 가용자본금 (만원)
                'annual_income_man': int,   # 부부합산연소득 (만원)
                'existing_loan_man': int,   # 현재 보유 대출 (만원)
            }
        target_apt: 선택 아파트 정보.
            {
                'name': str,
                'address': str,
                'price_man': int,
                'area': str,
                'units': int,
                'completion': str,
            }
        ml_prediction: ml_predictor.predict_price_growth() 반환값.

    Returns:
        마크다운 형식의 AI 어드바이저 응답 문자열.
    """
    api_key = kwargs.get("api_key")
    if api_key:
        os.environ["OPENAI_API_KEY"] = str(api_key)

    user_profile = _normalize_user_profile(user_profile or kwargs.get("user_profile") or {})
    target_apt = _normalize_target(target_apt or kwargs.get("target_info") or {})
    ml_prediction = _normalize_prediction(ml_prediction or kwargs.get("ml_prediction") or {}, target_apt)
    my_info = _normalize_home(kwargs.get("my_info") or {})
    loan_summary = _normalize_loan_summary(kwargs.get("loan_summary") or {})
    search_context = _normalize_search_context(kwargs.get("search_context") or {})
    user_question = str(kwargs.get("question") or "").strip()

    try:
        retriever = init_vector_store()
        chain = _build_rag_chain(retriever)
        query = _build_query(
            user_profile,
            target_apt,
            ml_prediction,
            my_info=my_info,
            loan_summary=loan_summary,
            search_context=search_context,
        )
        if user_question:
            query = f"{query}\n\n■ 사용자 추가 질문\n{user_question}"
        return chain.invoke(query)
    except Exception as exc:
        return _fallback_response(
            user_profile,
            target_apt,
            ml_prediction,
            my_info,
            loan_summary,
            search_context,
            exc,
        )


def init_vector_store(docs_path: str | None = None):
    """RAG용 벡터스토어를 초기화한다.

    Args:
        docs_path: 문서 경로. None이면 config.VECTOR_STORE_DIR 사용.

    Returns:
        초기화된 벡터스토어 객체. STUB 상태에서는 None 반환.
    """
    path = docs_path or VECTORSTORE_PATH
    if not Path(path).exists():
        raise FileNotFoundError(
            f"RAG vector store not found: {path}. Run `python scripts/build_vectorstore.py` first."
        )
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    return vectorstore.as_retriever(search_kwargs={"k": OPENAI_RAG_RETRIEVER_K})


def _build_rag_chain(retriever):
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough

    llm = ChatOpenAI(
        model=OPENAI_CHAT_MODEL,
        use_responses_api=OPENAI_USE_RESPONSES_API,
        reasoning_effort=OPENAI_REASONING_EFFORT,
        verbosity=OPENAI_TEXT_VERBOSITY,
        max_tokens=OPENAI_MAX_OUTPUT_TOKENS,
        request_timeout=OPENAI_REQUEST_TIMEOUT,
    )

    prompt = ChatPromptTemplate.from_template("""
당신은 신한은행 주택담보대출 전문 AI 어드바이저입니다.
아래 [참고 문서]와 [고객 분석 데이터]를 종합하여 맞춤형 대출·투자 분석 리포트를 작성하세요.

[참고 문서]
{context}

[고객 분석 데이터]
{question}

[작성 지침]
- 리포트 최상단에 반드시 아래 문구를 박스(> 인용문)로 삽입하세요:
  > :warning: **본 리포트는 AI가 생성한 참고용 분석입니다.**
  > 실제 대출 가능 여부·한도·금리는 신한은행 심사 기준에 따라 달라질 수 있으며,
  > 본 내용은 투자 권유 또는 금융 상품 가입 권유가 아닙니다.
  > 최종 의사결정 전 반드시 영업점 전문가 상담(:phone: 1599-8000)을 받으시기 바랍니다.
- 상품 안내, 비교, 추천은 반드시 신한은행 상품 또는 국가기금/공공 정책성 주택대출 상품으로만 제한하세요.
- 참고 문서에 타 은행 상품 정보가 포함되어 있더라도 타 은행 상품명, 조건, 금리, 장단점, 비교 추천을 답변에 포함하지 마세요.
- 사용자가 타 은행 비교를 요청하더라도 이 서비스는 신한은행/국가기금 상품 기준으로만 안내한다고 설명하세요.
- [고객 분석 데이터]의 프로파일, 탐색 조건, 선택 단지, ML 예측, 대출 계산값을 빠뜨리지 말고 서로 연결해 설명하세요.
- 값이 "없음"인 항목은 추측하거나 만들어내지 말고, 분석에 필요한 경우 추가 확인 사항으로 안내하세요.
- 고객의 실제 숫자를 인용하여 왜 해당 진단과 상품 추천이 나왔는지 근거를 설명하세요.
- 마크다운 형식으로 작성하세요 (### 소제목, **강조** 활용).
- 아래 4개 섹션을 반드시 포함하세요:
  1. ### 대출 가능성 요약 — LTV/DSR 적합 여부, 자금 충족 여부
  2. ### 추천 대출 상품 — 가구 형태와 목적에 맞는 상품 추천 이유
  3. ### 투자 전망 — ML 예측 수치 기반 1/3/5년 시세 전망 해석
  4. ### 종합 의견 — 매수 결정 시 고려사항, 주의 사항
- 참고 문서에 없는 금리·한도 수치는 "영업점 또는 1599-8000 문의 권장"으로 안내하세요.
- 금리/한도는 시점에 따라 변동될 수 있음을 명시하세요.
- 한국어로, 전문적이면서 이해하기 쉽게 작성하세요.
""")

    def format_docs(docs):
        return "\n\n".join(
            f"[출처: {d.metadata.get('filename', '?')}]\n{d.page_content}"
            for d in docs
        )

    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or value.strip().lower() in {"nan", "none", "null", "-"}
    try:
        return bool(value != value)
    except Exception:
        return False


def _text(value: Any) -> str:
    return "없음" if _is_missing(value) else str(value).strip()


def _number(value: Any, default: float = 0.0) -> float:
    if _is_missing(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    return int(round(_number(value, float(default))))


def _optional_number(value: Any) -> float | None:
    return None if _is_missing(value) else _number(value)


def _optional_integer(value: Any) -> int | None:
    return None if _is_missing(value) else _integer(value)


def _money(value: Any, *, zero_means_none: bool = False) -> str:
    if _is_missing(value):
        return "없음"
    amount = _integer(value)
    if zero_means_none and amount <= 0:
        return "없음"
    return f"{amount:,}만원"


def _metric(value: Any, suffix: str, decimals: int = 1, *, signed: bool = False) -> str:
    if _is_missing(value):
        return "없음"
    number = _number(value)
    sign = "+" if signed else ""
    return f"{number:{sign}.{decimals}f}{suffix}"


def _count(value: Any, suffix: str = "세대") -> str:
    return "없음" if _is_missing(value) else f"{_integer(value):,}{suffix}"


def _normalize_user_profile(profile: dict) -> dict:
    cash_man = profile.get("available_cash_man")
    if _is_missing(cash_man):
        cash_man = _number(profile.get("available_cash_eok")) * 10_000
    return {
        "household_type": _text(profile.get("household_type")),
        "purpose": _text(profile.get("purpose")),
        "available_cash_man": _integer(cash_man),
        "annual_income_man": _integer(profile.get("annual_income_man")),
        "existing_loan_man": _integer(profile.get("existing_loan_man")),
    }


def _normalize_target(target: dict) -> dict:
    return {
        "name": _text(target.get("name")),
        "address": _text(target.get("address") or target.get("region")),
        "district": _text(target.get("district") or target.get("region")),
        "complex_id": _text(target.get("complex_id")),
        "area_serial_no": _text(target.get("area_serial_no")),
        "price_man": _optional_integer(target.get("price_man")),
        "jeonse_price_man": _optional_integer(target.get("jeonse_price_man")),
        "jeonse_ratio_pct": _optional_number(target.get("jeonse_ratio_pct")),
        "area": _text(target.get("area") or target.get("area_type")),
        "supply_area_pyeong": _optional_number(target.get("supply_area_pyeong")),
        "exclusive_area_pyeong": _optional_number(target.get("exclusive_area_pyeong")),
        "units": _optional_integer(target.get("units")),
        "households_by_size": _optional_integer(target.get("households_by_size")),
        "completion": _text(target.get("completion")),
        "property_type": _text(target.get("property_type")),
        "floor_area_ratio": _optional_number(target.get("floor_area_ratio")),
        "building_coverage_ratio": _optional_number(target.get("building_coverage_ratio")),
        "monthly_sale_change_pct": _optional_number(target.get("monthly_sale_change_pct")),
        "monthly_jeonse_change_pct": _optional_number(target.get("monthly_jeonse_change_pct")),
    }


def _normalize_prediction(prediction: dict, target: dict) -> dict:
    normalized_items = []
    source_items = prediction.get("predictions") or []
    if not source_items and not _is_missing(prediction.get("predicted_growth_pct")):
        source_items = [prediction]
    for item in source_items:
        horizon = _integer(item.get("horizon_months"))
        growth = _number(item.get("predicted_growth_pct"))
        interval = item.get("prediction_interval_p80") or {}
        residual = item.get("residual_calibration") or {}
        current_price = _integer(target.get("price_man"))
        normalized_items.append(
            {
                "horizon_months": horizon,
                "predicted_growth_pct": growth,
                "estimated_price_man": int(round(current_price * (1 + growth / 100))) if current_price else 0,
                "confidence": _text(item.get("confidence")),
                "p80_half_width_pctp": _number(interval.get("half_width_pctp")),
                "fallback_source": _text(
                    item.get("fallback_source")
                    or item.get("calibration_source")
                    or residual.get("fallback")
                ),
            }
        )
    return {
        "model_version": _text(prediction.get("model_version")),
        "predictions": normalized_items,
        "note": _text(prediction.get("note")),
    }


def _normalize_home(home: dict) -> dict:
    current_price = _integer(home.get("current_price"))
    name = _text(home.get("name"))
    has_home = current_price > 0 or name != "없음"
    if not has_home:
        return {"has_home": False}
    return {
        "has_home": True,
        "name": name if name != "없음" else "직접 입력 보유 주택",
        "address": _text(home.get("address")),
        "current_price": current_price,
        "purchase_price": _optional_integer(home.get("purchase_price")),
        "purchase_date": _text(home.get("purchase_date")),
        "units": _optional_integer(home.get("units")),
        "completion": _text(home.get("completion")),
    }


def _normalize_loan_summary(summary: dict) -> dict:
    products = []
    for product in summary.get("recommended_products") or []:
        products.append(
            {
                "name": _text(product.get("name")),
                "reason": _text(product.get("description")),
                "rate": _text(product.get("rate")),
                "limit": _integer(product.get("limit")),
            }
        )
    return {
        "loan_limit": _integer(summary.get("loan_limit")),
        "ltv": _number(summary.get("ltv")),
        "dsr": _number(summary.get("dsr")),
        "cash_needed": _integer(summary.get("cash_needed")),
        "asset_gap": _integer(summary.get("asset_gap")),
        "available_cash": _integer(summary.get("available_cash")),
        "home_sale_equity": _integer(summary.get("home_sale_equity")),
        "total_available": _integer(summary.get("total_available")),
        "is_affordable": summary.get("is_affordable"),
        "recommended_products": products,
    }


def _normalize_search_context(context: dict) -> dict:
    return {
        "region": _text(context.get("region")),
        "keyword": _text(context.get("keyword")),
        "price_min_man": _optional_integer(context.get("price_min_man")),
        "price_max_man": _optional_integer(context.get("price_max_man")),
        "units_min": _optional_integer(context.get("units_min")),
        "units_max": _optional_integer(context.get("units_max")),
        "area_type": _text(context.get("area_type")),
        "sort_choice": _text(context.get("sort_choice")),
    }


def _prediction_lines(prediction: dict) -> str:
    items = prediction.get("predictions") or []
    if not items:
        return "- ML 예측: 없음"
    lines = [f"- 모델 버전: {prediction.get('model_version', '없음')}"]
    for item in items:
        horizon = item.get("horizon_months", 0)
        growth = item.get("predicted_growth_pct", 0.0)
        estimate = _money(item.get("estimated_price_man"), zero_means_none=True)
        half_width = item.get("p80_half_width_pctp", 0.0)
        error_band = f"±{half_width:.1f}%p" if half_width > 0 else "없음"
        lines.append(
            f"- {horizon}개월: 상승률 {growth:+.1f}%, 추정 시세 {estimate}, "
            f"신뢰도 {item.get('confidence', '없음')}, 경험적 P80 오차범위 {error_band}, "
            f"보정 경로 {item.get('fallback_source', '없음')}"
        )
    return "\n".join(lines)


def _product_lines(summary: dict) -> str:
    products = summary.get("recommended_products") or []
    if not products:
        return "- 추천 상품 후보: 없음"
    return "\n".join(
        f"- {product['name']}: {product['reason']} / 금리 {product['rate']} / 한도 {_money(product['limit'], zero_means_none=True)}"
        for product in products
    )


def _build_query(
    user_profile: dict,
    target_apt: dict,
    ml_prediction: dict,
    my_info: dict | None = None,
    loan_summary: dict | None = None,
    search_context: dict | None = None,
) -> str:
    """탭 1·2의 모든 개인화 입력을 RAG 체인용 구조화 문자열로 변환한다."""
    my_info = my_info or {"has_home": False}
    loan_summary = loan_summary or _normalize_loan_summary({})
    search_context = search_context or _normalize_search_context({})
    home_lines = "- 보유 주택: 없음"
    if my_info.get("has_home"):
        home_lines = f"""- 단지명: {my_info.get('name', '없음')}
- 주소: {my_info.get('address', '없음')}
- 현재 시세: {_money(my_info.get('current_price'), zero_means_none=True)}
- 매수 시점/매수가: {my_info.get('purchase_date', '없음')} / {_money(my_info.get('purchase_price'), zero_means_none=True)}
- 세대수/입주년월: {_count(my_info.get('units'))} / {my_info.get('completion', '없음')}"""

    affordability = loan_summary.get("is_affordable")
    affordability_text = "없음" if affordability is None else ("가능" if affordability else "부족")

    return f"""
■ 고객 프로파일
- 가구 형태: {user_profile.get('household_type', '없음')}
- 매매 목적: {user_profile.get('purpose', '없음')}
- 부부합산 연소득: {_money(user_profile.get('annual_income_man'))}
- 가용 자본금: {_money(user_profile.get('available_cash_man'))}
- 기존 보유 대출: {_money(user_profile.get('existing_loan_man'))}

■ 단지 탐색 조건
- 지역/검색어: {search_context.get('region', '없음')} / {search_context.get('keyword', '없음')}
- 시세 범위: {_money(search_context.get('price_min_man'), zero_means_none=True)} ~ {_money(search_context.get('price_max_man'), zero_means_none=True)}
- 세대수 범위: {_count(search_context.get('units_min'), '')} ~ {_count(search_context.get('units_max'))}
- 평형 유형/정렬: {search_context.get('area_type', '없음')} / {search_context.get('sort_choice', '없음')}

■ 타겟 아파트
- 단지명/ID: {target_apt.get('name', '없음')} / {target_apt.get('complex_id', '없음')}
- 주소: {target_apt.get('address', '없음')}
- KB 매매/전세시세: {_money(target_apt.get('price_man'), zero_means_none=True)} / {_money(target_apt.get('jeonse_price_man'), zero_means_none=True)}
- 전세가율: {_metric(target_apt.get('jeonse_ratio_pct'), '%')}
- 평형: {target_apt.get('area', '없음')} (공급 {_metric(target_apt.get('supply_area_pyeong'), '평')} / 전용 {_metric(target_apt.get('exclusive_area_pyeong'), '평')})
- 전체/평형 세대수: {_count(target_apt.get('units'))} / {_count(target_apt.get('households_by_size'))}
- 준공년월/물건종류: {target_apt.get('completion', '없음')} / {target_apt.get('property_type', '없음')}
- 용적률/건폐율: {_metric(target_apt.get('floor_area_ratio'), '%')} / {_metric(target_apt.get('building_coverage_ratio'), '%')}
- 월간 매매/전세 변동률: {_metric(target_apt.get('monthly_sale_change_pct'), '%', 2, signed=True)} / {_metric(target_apt.get('monthly_jeonse_change_pct'), '%', 2, signed=True)}

■ 현재 보유 주택
{home_lines}

■ ML 가격 예측
{_prediction_lines(ml_prediction)}

■ 대출·자금 계산
- 최대 대출 한도: {_money(loan_summary.get('loan_limit'), zero_means_none=True)}
- LTV/DSR: {loan_summary.get('ltv', 0):.1f}% / {loan_summary.get('dsr', 0):.1f}%
- 필요 자기자금: {_money(loan_summary.get('cash_needed'), zero_means_none=True)}
- 가용 자본금 대비 잔여/부족: {_money(loan_summary.get('asset_gap'))} ({affordability_text})
- 기존 가용자금/보유주택 매도 후 자기자본/총 동원 가능 자금: {_money(loan_summary.get('available_cash'))} / {_money(loan_summary.get('home_sale_equity'))} / {_money(loan_summary.get('total_available'))}
{_product_lines(loan_summary)}

위 값들을 실제 근거로 인용하여 이 고객에게 맞춤형 대출·투자 분석 리포트를 작성해주세요.
""".strip()


def _fallback_response(
    user_profile: dict,
    target_apt: dict,
    ml_prediction: dict,
    my_info: dict,
    loan_summary: dict,
    search_context: dict,
    error: Exception,
) -> str:
    """RAG 의존성 또는 벡터스토어가 없을 때 Streamlit UI가 중단되지 않도록 요약 응답을 만든다."""
    return f"""
> :warning: **본 리포트는 AI가 생성한 참고용 분석입니다.**
> 실제 대출 가능 여부·한도·금리는 신한은행 심사 기준에 따라 달라질 수 있으며,
> 본 내용은 투자 권유 또는 금융 상품 가입 권유가 아닙니다.
> 최종 의사결정 전 반드시 영업점 전문가 상담(:phone: 1599-8000)을 받으시기 바랍니다.

### AI 어드바이저 준비 상태

RAG 벡터스토어 또는 LangChain 의존성을 아직 사용할 수 없어, 규정 문서 검색 없이 입력값 기반 요약만 표시합니다.
상품 안내 범위는 신한은행 상품과 국가기금/공공 정책성 주택대출 상품으로 제한합니다.

### 입력 요약

- 가구 형태: **{user_profile.get('household_type', '-')}**
- 매매 목적: **{user_profile.get('purpose', '-')}**
- 연소득/가용 자본금/기존 대출: **{_money(user_profile.get('annual_income_man'))} / {_money(user_profile.get('available_cash_man'))} / {_money(user_profile.get('existing_loan_man'))}**
- 탐색 지역/평형: **{search_context.get('region', '없음')} / {search_context.get('area_type', '없음')}**
- 타겟 단지: **{target_apt.get('name', '-')}**
- 타겟 시세: **{target_apt.get('price_man', 0):,}만원**
- 보유 주택: **{my_info.get('name', '없음') if my_info.get('has_home') else '없음'}**
- 대출 한도: **{loan_summary.get('loan_limit', 0):,}만원**
- LTV/DSR: **{loan_summary.get('ltv', 0):.1f}% / {loan_summary.get('dsr', 0):.1f}%**
- 필요 자기자금/잔여·부족: **{_money(loan_summary.get('cash_needed'))} / {_money(loan_summary.get('asset_gap'))}**

### ML 예측 입력

{_prediction_lines(ml_prediction)}

### 다음 조치

`python scripts/build_vectorstore.py`로 벡터스토어를 생성한 뒤 다시 실행하면 신한 FAQ와 규제 문서를 검색해 답변합니다.

오류: `{type(error).__name__}: {error}`
""".strip()
