"""Loan-limit, LTV, DSR, and cash-gap helpers for the Streamlit app."""

from __future__ import annotations

from config import LOAN_LIMIT_RULES


def calc_loan_limit(price_man: int | float) -> int:
    """Return the mortgage cap in manwon based on the configured price bands."""
    price = max(int(price_man or 0), 0)
    for upper_price, limit in LOAN_LIMIT_RULES:
        if price <= upper_price:
            return min(price, int(limit))
    return min(price, int(LOAN_LIMIT_RULES[-1][1]))


def calc_ltv(price_man: int | float, loan_man: int | float) -> float:
    """Calculate LTV percentage from price and loan amount."""
    price = float(price_man or 0)
    loan = float(loan_man or 0)
    if price <= 0:
        return 0.0
    return loan / price * 100.0


def calc_dsr(
    loan_man: int | float,
    annual_income_man: int | float,
    existing_loan_man: int | float = 0,
    annual_rate: float = 0.045,
    years: int = 30,
) -> float:
    """Estimate DSR using an amortized mortgage payment plus existing-loan burden.

    Values are in manwon. Existing loans are approximated as 10% annual repayment
    burden because detailed amortization terms are not collected in the UI.
    """
    income = float(annual_income_man or 0)
    if income <= 0:
        return 0.0

    principal = max(float(loan_man or 0), 0.0)
    months = max(int(years) * 12, 1)
    monthly_rate = max(float(annual_rate), 0.0) / 12
    if monthly_rate == 0:
        annual_mortgage_payment = principal / max(years, 1)
    else:
        monthly_payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)
        annual_mortgage_payment = monthly_payment * 12

    existing_annual_payment = max(float(existing_loan_man or 0), 0.0) * 0.10
    return (annual_mortgage_payment + existing_annual_payment) / income * 100.0


def calc_cash_needed(
    price_man: int | float,
    loan_man: int | float,
    current_asset_man: int | float,
) -> dict:
    """Calculate required equity and the user's remaining surplus or shortage."""
    price = max(int(price_man or 0), 0)
    loan = max(int(loan_man or 0), 0)
    asset = max(int(current_asset_man or 0), 0)
    cash_needed = max(price - loan, 0)
    asset_gap = asset - cash_needed
    return {
        "cash_needed": cash_needed,
        "asset_gap": asset_gap,
        "is_affordable": asset_gap >= 0,
    }


def recommend_loan_products(
    price: int | float | None = None,
    loan_limit: int | float | None = None,
    annual_income: int | float | None = None,
    household_type: str = "",
    purpose: str = "",
    price_man: int | float | None = None,
    annual_income_man: int | float | None = None,
) -> list[dict]:
    """Return simple rule-based Shinhan-style mortgage product candidates."""
    target_price = int(price if price is not None else price_man or 0)
    limit = int(loan_limit if loan_limit is not None else calc_loan_limit(target_price))
    income = int(annual_income if annual_income is not None else annual_income_man or 0)

    products = [
        {
            "name": "신한 주택담보대출",
            "description": "일반 아파트 매수 목적의 기본 주택담보대출 후보입니다.",
            "rate": "영업점 확인",
            "limit": limit,
        }
    ]

    if household_type in {"신혼부부", "신생아출산"} and purpose == "실거주":
        products.insert(
            0,
            {
                "name": "신한 신혼부부/생애주기 우대 주담대",
                "description": "가구 유형 우대 가능성을 우선 확인할 만한 후보입니다.",
                "rate": "우대금리 가능",
                "limit": limit,
            },
        )

    if income > 0 and target_price <= 150_000 and purpose == "실거주":
        products.append(
            {
                "name": "정책모기지 검토",
                "description": "가격과 소득 조건 충족 여부를 별도 확인할 가치가 있습니다.",
                "rate": "상품별 상이",
                "limit": min(limit, 50_000),
            }
        )

    return products
