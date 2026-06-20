"""
공통 유틸리티 함수 모음.
어떤 모듈에서도 의존성 없이 import 가능한 순수 함수만 포함한다.
"""


def format_price_kor(eok: float) -> str:
    """억 단위 float을 한글 금액 문자열로 변환한다.

    Args:
        eok: 억 단위 금액. 예) 13.4

    Returns:
        한글 금액 문자열. 예) '13억 4,000만 원'
    """
    # TODO: 구현
    pass


def man_to_eok_str(man: int) -> str:
    """만원 단위 int를 한글 금액 문자열로 변환한다.

    Args:
        man: 만원 단위 금액. 예) 134000

    Returns:
        한글 금액 문자열. 예) '13억 4,000만 원'
    """
    # TODO: format_price_kor(man / 10000) 호출로 구현
    pass
