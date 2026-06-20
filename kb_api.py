"""
KB부동산 비공식 API 호출 모듈. (김혜민 담당)

Streamlit 의존성 없음 — 오류는 Exception으로 raise한다.
호출 측(app.py)에서 st.error()로 캐치할 것.
"""

import random
import time
from datetime import date

import requests

from config import KB_BASE_HEADERS, KB_BASE_URL, KB_TIMESERIES_URL, UA_POOL


# ── 내부 유틸 ────────────────────────────────────────────────────────────────

def _make_headers(extra: dict | None = None) -> dict[str, str]:
    """요청마다 UA를 랜덤 선택한 헤더 dict 반환."""
    headers = {**KB_BASE_HEADERS, "User-Agent": random.choice(UA_POOL)}
    if extra:
        headers.update(extra)
    return headers


# ── Public API ───────────────────────────────────────────────────────────────

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
    url = f"{KB_BASE_URL}/land-complex/serch/autoKywrSerch"
    params = {
        "컬렉션설정명": (
            "COL_AT_JUSO:100;COL_AT_SCHOOL:100;"
            "COL_AT_SUBWAY:100;COL_AT_HSCM:100;COL_AT_VILLA:100"
        ),
        "검색키워드": keyword,
    }
    resp = requests.get(url, params=params, headers=_make_headers(), timeout=10)
    resp.raise_for_status()

    data_list = resp.json().get("dataBody", {}).get("data", [])
    raw_list  = data_list[0].get("COL_AT_HSCM", []) if data_list else []
    result = []
    for item in raw_list:
        name      = item.get("text", "")
        addr      = item.get("addr", "")
        text_temp = item.get("textTemp", f"({addr}){name}")
        label     = f"{name}  ({addr})"
        result.append({"label": label, "textTemp": text_temp})
    return result


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
    url = f"{KB_BASE_URL}/land-complex/serch/intgraSerch"
    params = {
        "검색설정명": "SRC_HSCM",
        "검색키워드": text_temp,
        "출력갯수":   2,
        "페이지설정값": 1,
    }
    resp = requests.get(url, params=params, headers=_make_headers(), timeout=10)
    resp.raise_for_status()

    hscm = (
        resp.json()
            .get("dataBody", {})
            .get("data", {})
            .get("data", {})
            .get("HSCM", {})
            .get("data", [])
    )
    if not hscm:
        return {}

    item     = hscm[0]
    raw_comp = str(item.get("MVIHS_DATE", ""))
    completion = (
        f"{raw_comp[:4]}.{raw_comp[4:]}" if len(raw_comp) >= 6 else raw_comp
    )
    return {
        "complex_id": item.get("COMPLEX_NO", ""),
        "name":       item.get("HSCM_NM", ""),
        "addr":       item.get("BUBADDR_SHORT", "") or item.get("BUBADDR", ""),
        "units":      item.get("THS_NUM", ""),
        "completion": completion,
    }


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
    url    = f"{KB_BASE_URL}/land-complex/complex/mpriByType"
    params = {"단지기본일련번호": complex_id}

    resp = requests.get(url, params=params, headers=_make_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json().get("dataBody", {}).get("data", []) or []


def fetch_complex_timeseries(
    complex_id: str,
    area_id: str,
    date_start: str | None = None,
    date_end: str | None = None,
) -> list[dict]:
    """단지 시세 시계열 API로 월별 KB매매/전세 시세를 반환한다 (최대 5년).

    엔드포인트: /land-price/price/complex/preSaleChart

    Args:
        complex_id: 단지 기본 일련번호.
        area_id: 면적 일련번호.
        date_start: 조회 시작일 (YYYYMMDD). None이면 오늘 기준 5년 전.
        date_end: 조회 종료일 (YYYYMMDD). None이면 오늘.

    Returns:
        월별 시세 리스트. 각 항목 예시:
        {
            '기준년월': '202501',
            '매매일반거래가': 120000,
            '전세일반거래가': 75000,
            '전세가율': 62.5,
            '시세갭가격': 45000,
            '매매실거래평균가': 118000,
            ...
        }
        데이터 없거나 API 미지원 단지면 빈 리스트 반환.

    Raises:
        Exception: API 호출 3회 재시도 모두 실패 시.
    """
    today     = date.today()
    _date_end   = date_end   or today.strftime("%Y%m%d")
    _date_start = date_start or f"{today.year - 5}{_date_end[4:]}"

    params = {
        "단지기본일련번호": complex_id,
        "면적일련번호":    area_id,
        "거래구분":        "0",   # 0 = 전체(매매+전세)
        "조회구분":        "2",   # 고정값
        "면적그룹여부":    "0",   # 0 = 개별 평형
        "조회시작일":      _date_start,
        "조회종료일":      _date_end,
    }
    # preSaleChart 전용 필수 헤더 (브라우저 네트워크 캡처로 확인)
    headers = _make_headers(extra={"webservice": "1"})

    last_exc: Exception = Exception("알 수 없는 오류")
    for attempt in range(1, 4):
        try:
            time.sleep(random.uniform(0.2, 0.5))
            resp = requests.get(
                KB_TIMESERIES_URL, params=params, headers=headers, timeout=15
            )
            resp.raise_for_status()
            body = resp.json()
            rc = body.get("dataBody", {}).get("resultCode")
            if rc != 11000:
                # resultCode != 11000 은 데이터 없음 (시세 미제공 단지)
                return []
            return body["dataBody"]["data"].get("시세", [])
        except Exception as exc:
            last_exc = exc
            if attempt < 3:
                time.sleep(attempt * 1.5)

    raise Exception(f"시계열 조회 실패 (complex={complex_id}, area={area_id}): {last_exc}")
