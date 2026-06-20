"""
KB부동산 비공식 API 호출 모듈. (김혜민 담당)

Streamlit 의존성 없음 — 오류는 Exception으로 raise한다.
호출 측(app.py)에서 st.error()로 캐치할 것.
"""

from config import KB_BASE_URL, KB_HEADERS


def fetch_search_suggestions(keyword: str) -> list[dict]:
    """자동완성 API로 단지 후보 목록을 반환한다.

    엔드포인트: /land-complex/serch/autoKywrSerch

    Args:
        keyword: 검색 키워드. 예) '래미안 대치'

    Returns:
        단지 후보 리스트. 각 항목은 {'label': str, 'textTemp': str}.
        결과가 없으면 빈 리스트 반환.

    Raises:
        Exception: API 호출 실패 시.
    """
    # TODO (김혜민): requests.get() 호출 후 dataBody.data[0].COL_AT_HSCM 파싱
    pass


def fetch_complex_id(text_temp: str) -> dict:
    """통합검색 API로 단지 기본 정보를 반환한다.

    엔드포인트: /land-complex/serch/intgraSerch

    Args:
        text_temp: 자동완성 API의 textTemp 값.

    Returns:
        단지 정보 dict.
        {'complex_id': str, 'name': str, 'addr': str,
         'units': int, 'completion': str}
        단지를 찾지 못하면 빈 dict 반환.

    Raises:
        Exception: API 호출 실패 시.
    """
    # TODO (김혜민): requests.get() 호출 후 dataBody.data.data.HSCM.data[0] 파싱
    pass


def fetch_complex_price(complex_id: str) -> list[dict]:
    """단지 시세정보 API로 면적별 KB매매시세 리스트를 반환한다.

    엔드포인트: /land-complex/complex/mpriByType

    Args:
        complex_id: 단지 기본 일련번호.

    Returns:
        면적별 시세 리스트 (API 원본 구조 그대로).
        조회 실패 또는 데이터 없으면 빈 리스트 반환.

    Raises:
        Exception: API 호출 실패 시.
    """
    # TODO (김혜민): requests.get() 호출 후 dataBody.data 반환
    pass
