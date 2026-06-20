"""
데이터 로드 및 전처리 모듈. (김혜민 담당)

Streamlit 의존성 없음 — 순수 pandas 함수만 포함한다.
@st.cache_data 래핑은 app.py에서 처리한다.
"""

import pandas as pd

from config import KB_DATA_CSV, ML_TIMESERIES_CSV


def load_kb_apt_data() -> pd.DataFrame:
    """로컬 KB 단지 CSV를 로드하고 컬럼 타입을 정규화한다.

    파일 경로: config.KB_DATA_CSV

    Returns:
        정규화된 DataFrame. 주요 컬럼:
        - KB매매시세(만원): float
        - 세대수: int
        - 단지ID: int
        - 공급면적(평): float
        - 구: str
        - 지역: str  (도로명주소에서 파생, 필터 UI용)

    Raises:
        FileNotFoundError: CSV 파일이 없을 때.
    """
    # TODO (김혜민): pd.read_csv(KB_DATA_CSV) 후 숫자형 컬럼 변환 및 '지역' 컬럼 생성
    pass


def load_ml_timeseries() -> pd.DataFrame:
    """ML 학습용 KB 아파트 지수 시계열 CSV를 로드한다.

    파일 경로: config.ML_TIMESERIES_CSV

    Returns:
        시계열 DataFrame. 컬럼 구조는 원본 CSV 그대로.

    Raises:
        FileNotFoundError: CSV 파일이 없을 때.
    """
    # TODO (김혜민): pd.read_csv(ML_TIMESERIES_CSV) 후 날짜 파싱 등 필요한 전처리
    pass


def filter_apartments(
    df: pd.DataFrame,
    region: str | None = None,
    dong: str | None = None,
    keyword: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    units_min: int | None = None,
    area_min: float | None = None,
    area_max: float | None = None,
) -> pd.DataFrame:
    """조건에 따라 아파트 DataFrame을 필터링한다.

    모든 파라미터는 선택적이며 None이면 해당 조건을 무시한다.

    Args:
        df: load_kb_apt_data()가 반환한 DataFrame.
        region: '지역' 컬럼 일치 필터. 예) '서울 강남구'
        dong: '동' 컬럼 일치 필터. 예) '대치동'
        keyword: '아파트명' 부분 문자열 필터. 예) '힐스테이트'
        price_min: KB매매시세(만원) 하한 (포함).
        price_max: KB매매시세(만원) 상한 (포함).
        units_min: 세대수 하한 (포함).
        area_min: 공급면적(평) 하한 (포함).
        area_max: 공급면적(평) 상한 (포함).

    Returns:
        필터 조건을 모두 만족하는 행의 DataFrame (reset_index 적용).
    """
    # TODO (김혜민): 조건별 boolean mask 적용 후 reset_index(drop=True) 반환
    pass
