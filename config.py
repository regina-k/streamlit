"""
프로젝트 전역 상수 및 설정.
모든 모듈은 여기서 상수를 import해서 사용한다.
"""

from pathlib import Path

# ── 디렉토리 경로 ────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
DATA_DIR        = BASE_DIR / "data"
MODELS_DIR      = BASE_DIR / "models"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"

# ── CSV 파일 경로 ────────────────────────────────────────────────────────
KB_DATA_CSV       = DATA_DIR / "kb_data.csv"
ML_TIMESERIES_CSV = DATA_DIR / "ml_apt_index_sigungu.csv"

# ── KB부동산 API ─────────────────────────────────────────────────────────
KB_BASE_URL = "https://api.kbland.kr"

KB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer":         "https://kbland.kr/",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# ── 대출 규제 상수 (가계부채 관리방안) ──────────────────────────────────
# [(매매가 상한_만원, 주담대 한도_만원), ...]  — 마지막 항목이 기본값
LOAN_LIMIT_RULES: list[tuple[int, int]] = [
    (150_000, 60_000),          # ≤15억 → 6억
    (250_000, 40_000),          # ≤25억 → 4억
    (999_999_999, 20_000),      # 25억 초과 → 2억
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

# ── 평형 구분 기준 (㎡ 상한 기준) ───────────────────────────────────────
AREA_TYPE_BOUNDS: dict[str, float] = {
    "40㎡이하":  40.0,
    "60㎡이하":  60.0,
    "85㎡이하":  85.0,
    "102㎡이하": 102.0,
    "135㎡이하": 135.0,
    "135㎡초과": float("inf"),
}
