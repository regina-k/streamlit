"""
대출 한도 계산 및 LTV/DSR 분석 모듈.

가계부채 관리방안 규제 기준을 반영한 순수 계산 함수 모음.
Streamlit 의존성 없음.
"""

from config import LOAN_LIMIT_RULES


def calc_loan_limit(price_man: int) -> int:
    """매매가 기준 주담대 한도를 반환한다.

    가계부채 관리방안 기준:
    - ≤15억 → 6억 (60,000만원)
    - 15억 초과~25억 이하 → 4억 (40,000만원)
    - 25억 초과 → 2억 (20,000만원)

    Args:
        price_man: 매매가 (만원 단위).

    Returns:
        주담대 한도 (만원 단위).
    """
    # TODO: LOAN_LIMIT_RULES를 순회하며 price_man과 비교 후 해당 한도 반환
    pass


def calc_ltv(price_man: int, loan_man: int) -> float:
    """LTV(주택담보대출비율)를 계산한다.

    Args:
        price_man: 매매가 (만원 단위).
        loan_man: 대출금 (만원 단위).

    Returns:
        LTV (%). 예) 40.0
    """
    # TODO: loan_man / price_man * 100
    pass


def calc_dsr(annual_income_man: int, annual_loan_payment_man: int) -> float:
    """DSR(총부채원리금상환비율)을 계산한다.

    Args:
        annual_income_man: 연간 소득 (만원 단위).
        annual_loan_payment_man: 연간 원리금 상환액 (만원 단위).

    Returns:
        DSR (%). 예) 35.0
    """
    # TODO: annual_loan_payment_man / annual_income_man * 100
    pass


def calc_cash_needed(
    price_man: int,
    loan_man: int,
    current_asset_man: int,
) -> dict:
    """매수에 필요한 현금 및 부족분을 계산한다.

    Args:
        price_man: 매매가 (만원 단위).
        loan_man: 조달 가능 대출금 (만원 단위).
        current_asset_man: 현재 보유 현금성 자산 (만원 단위).

    Returns:
        {
            '필요현금': int,   # 매매가 - 대출금
            '부족Gap': int,    # 필요현금 - 현재자산 (음수면 여유)
            '여유여부': bool,  # 부족Gap <= 0
        }
    """
    # TODO: 각 값 계산 후 dict 반환
    pass


def recommend_loan_products(
    price_man: int,
    household_type: str,
    purpose: str,
    annual_income_man: int,
) -> list[dict]:
    """가구 유형·목적·소득 기반 신한은행 주담대 상품 목록을 반환한다.

    Args:
        price_man: 매매가 (만원 단위).
        household_type: 가구 유형. config.HOUSEHOLD_TYPES 참고.
        purpose: 매매 목적. '실거주' 또는 '투자'.
        annual_income_man: 연간 소득 (만원 단위).

    Returns:
        추천 상품 리스트. 각 항목 예시:
        {
            '상품명': str,
            '금리': str,     # 예) '연 3.5%~4.2%'
            '한도_만원': int,
            '특이사항': str,
        }

    Note:
        현재는 하드코딩 더미 데이터 반환.
        김동하가 RAG 파이프라인 완성 후 실제 상품 데이터로 교체 예정.
    """
    # TODO: household_type / purpose 조합별 더미 상품 데이터 dict 리스트 반환
    # TODO (김동하 인수인계): rag_advisor.py RAG 완성 후 실제 API 연동으로 교체
    pass
