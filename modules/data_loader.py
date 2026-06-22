"""
데이터 로드 및 전처리 모듈. (김혜민 담당)

Streamlit 의존성 없음 — 순수 pandas 함수만 포함한다.
@st.cache_data 래핑은 app.py에서 처리한다.
"""

import pandas as pd

from config import KB_DATA_CSV, ML_TIMESERIES_CSV


NUMERIC_COLUMNS = [
    "단지ID",
    "위도",
    "경도",
    "세대수",
    "공급면적(평)",
    "전용면적(평)",
    "계약면적(평)",
    "공급면적(m2)",
    "전용면적(m2)",
    "면적일련번호",
    "KB매매시세(만원)",
    "매매상한가(만원)",
    "매매하한가(만원)",
    "KB전세시세(만원)",
    "세대수(평형)",
    "전세가율",
    "용적률",
    "건폐율",
    "월간매매변동률",
    "월간전세변동률",
]


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
    df = pd.read_csv(KB_DATA_CSV)

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "시군구" in df.columns and "구" not in df.columns:
        df["구"] = df["시군구"].astype("string")
    if "지역" not in df.columns:
        df["지역"] = "서울 " + df.get("시군구", pd.Series("", index=df.index)).astype("string")
    if "동" not in df.columns:
        df["동"] = ""
    if "아파트명" not in df.columns and "단지명" in df.columns:
        df["아파트명"] = df["단지명"]

    return df


def load_ml_timeseries() -> pd.DataFrame:
    """ML 학습용 KB 아파트 지수 시계열 CSV를 로드한다.

    파일 경로: config.ML_TIMESERIES_CSV

    Returns:
        시계열 DataFrame. 컬럼 구조는 원본 CSV 그대로.

    Raises:
        FileNotFoundError: CSV 파일이 없을 때.
    """
    df = pd.read_csv(ML_TIMESERIES_CSV)
    if "기준년월" in df.columns:
        df["기준년월"] = df["기준년월"].astype(str)
    for col in df.columns:
        if col != "기준년월":
            converted = pd.to_numeric(df[col], errors="coerce")
            if converted.notna().any():
                df[col] = converted
    return df


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
    if df is None or df.empty:
        return pd.DataFrame()

    mask = pd.Series(True, index=df.index)

    if region and "지역" in df.columns:
        mask &= df["지역"].astype(str).str.contains(str(region), na=False)
    if dong and "동" in df.columns:
        mask &= df["동"].astype(str).str.contains(str(dong), na=False)
    if keyword:
        name_col = "아파트명" if "아파트명" in df.columns else "단지명"
        if name_col in df.columns:
            mask &= df[name_col].astype(str).str.contains(
                str(keyword), case=False, na=False, regex=False
            )
    if price_min is not None and "KB매매시세(만원)" in df.columns:
        mask &= df["KB매매시세(만원)"] >= price_min
    if price_max is not None and "KB매매시세(만원)" in df.columns:
        mask &= df["KB매매시세(만원)"] <= price_max
    if units_min is not None and "세대수" in df.columns:
        mask &= df["세대수"] >= units_min
    if area_min is not None and "공급면적(평)" in df.columns:
        mask &= df["공급면적(평)"] >= area_min
    if area_max is not None and "공급면적(평)" in df.columns:
        mask &= df["공급면적(평)"] <= area_max

    return df.loc[mask].reset_index(drop=True)
