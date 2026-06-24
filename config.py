# -*- coding: utf-8 -*-
"""프로젝트 전역 상수 및 설정."""

from pathlib import Path

# ── 디렉토리 경로 ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
APARTMENT_DATA_DIR = DATA_DIR / "apartment"
MODELS_DIR = BASE_DIR / "models"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"

# ── CSV 파일 경로 ────────────────────────────────────────────────────────
KB_DATA_CSV = APARTMENT_DATA_DIR / "kb_apt_seoul_full.csv"
ML_TIMESERIES_CSV = APARTMENT_DATA_DIR / "kb_timeseries_seoul.csv"

# ── KB부동산 API ─────────────────────────────────────────────────────────
KB_BASE_URL = "https://api.kbland.kr"
KB_MAP_ENDPOINT = "/land-complex/map/map250mBlwInfoList"
KB_MPRI_ENDPOINT = "/land-complex/complex/mpriByType"
KB_TIMESERIES_URL = f"{KB_BASE_URL}/land-price/price/complex/preSaleChart"

KB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://kbland.kr/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

KB_BASE_HEADERS = {
    **KB_HEADERS,
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://kbland.kr",
    "Content-Type": "application/json",
}

UA_POOL = [
    KB_HEADERS["User-Agent"],
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# ── KB/MOLIT 수집 파라미터 ────────────────────────────────────────────────
SEMAPHORE_LIMIT = 10
JITTER_MIN = 0.3
JITTER_MAX = 0.6
REQUEST_TIMEOUT = 30
REQUEST_TIMEOUT_PHASE1 = (10, 120)
MAX_RETRY = 3
RETRY_WAIT_INITIAL = 1.0
RETRY_WAIT_MAX = 8.0
BLOCK_STATUS_CODES = frozenset({403, 429})
BLOCK_WAIT_SECONDS = 60
CONSECUTIVE_FAIL_THRESHOLD = 5
ZOOM_LEVEL = 15
PAD_LAT = 0.038
PAD_LNG = 0.050

# ── 파일 경로 ────────────────────────────────────────────────────────────
DIR_RAW = str(DATA_DIR / "raw")
DIR_RAW_MPRI = str(DATA_DIR / "raw" / "phase2_mpri")
DIR_RAW_MOLIT = str(DATA_DIR / "raw" / "phase3_molit")
DIR_CHECKPOINT = str(DATA_DIR / "checkpoint")
DIR_PROCESSED = str(DATA_DIR / "processed")
DIR_LOGS = str(BASE_DIR / "logs")

FILE_PHASE1 = str(DATA_DIR / "raw" / "phase1_complexes.json")
FILE_REGION_MAP = str(DATA_DIR / "raw" / "region_complex_map.json")
FILE_CHECKPOINT_MPRI = str(DATA_DIR / "checkpoint" / "done_mpri.txt")
FILE_CHECKPOINT_MOLIT = str(DATA_DIR / "checkpoint" / "done_molit.txt")
FILE_FAILED_MPRI = str(DATA_DIR / "checkpoint" / "failed_mpri.txt")
FILE_FAILED_MOLIT = str(DATA_DIR / "checkpoint" / "failed_molit.txt")
FILE_CSV_OUTPUT = str(APARTMENT_DATA_DIR / "kb_apt_seoul_full.csv")

MOLIT_BASE_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
MOLIT_ROWS_PER_PAGE = 1000
MOLIT_TIMESERIES_MONTHS = 60
MOLIT_SEMAPHORE_LIMIT = 5
MOLIT_JITTER_MIN = 0.5
MOLIT_JITTER_MAX = 1.0

# ── 대출 규제 상수 ───────────────────────────────────────────────────────
LOAN_LIMIT_RULES: list[tuple[int, int]] = [
    (150_000, 60_000),
    (250_000, 40_000),
    (999_999_999, 20_000),
]

# ── UI 드롭다운 옵션 ─────────────────────────────────────────────────────
HOUSEHOLD_TYPES: list[str] = ["신혼부부", "1인가구", "신생아출산", "다자녀"]
PURPOSE_OPTIONS: list[str] = ["실거주", "투자"]

AREA_TYPES: list[str] = [
    "40㎡이하",
    "60㎡이하",
    "85㎡이하",
    "102㎡이하",
    "135㎡이하",
    "135㎡초과",
]

AREA_TYPE_BOUNDS: dict[str, float] = {
    "40㎡이하": 40.0,
    "60㎡이하": 60.0,
    "85㎡이하": 85.0,
    "102㎡이하": 102.0,
    "135㎡이하": 135.0,
    "135㎡초과": float("inf"),
}
