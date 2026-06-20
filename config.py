# -*- coding: utf-8 -*-
"""전역 상수 설정. 모든 매직 넘버는 여기에."""

# ── KB API ──────────────────────────────────────────────────────────────
KB_BASE_URL        = "https://api.kbland.kr"
KB_MAP_ENDPOINT    = "/land-complex/map/map250mBlwInfoList"
KB_MPRI_ENDPOINT   = "/land-complex/complex/mpriByType"

# ── 동시성 ──────────────────────────────────────────────────────────────
SEMAPHORE_LIMIT    = 10
JITTER_MIN         = 0.3   # 요청 간 최소 대기(초)
JITTER_MAX         = 0.6   # 요청 간 최대 대기(초)
REQUEST_TIMEOUT       = 30    # Phase 2 mpriByType 타임아웃(초)
REQUEST_TIMEOUT_PHASE1 = (10, 120)  # Phase 1 map POST (connect=10s, read=120s, 응답 최대 5MB)

# ── Retry ───────────────────────────────────────────────────────────────
MAX_RETRY          = 3
RETRY_WAIT_INITIAL = 1.0   # 첫 재시도 대기(초)
RETRY_WAIT_MAX     = 8.0   # 최대 대기(초)

# ── 차단 감지 ────────────────────────────────────────────────────────────
BLOCK_STATUS_CODES          = frozenset({403, 429})
BLOCK_WAIT_SECONDS          = 60
CONSECUTIVE_FAIL_THRESHOLD  = 5

# ── KB 지도 파라미터 ─────────────────────────────────────────────────────
ZOOM_LEVEL = 15
PAD_LAT    = 0.038   # 구 중심에서 ± 위도 패딩 (~4.2 km)
PAD_LNG    = 0.050   # 구 중심에서 ± 경도 패딩 (~4.2 km)

# ── User-Agent 풀 ────────────────────────────────────────────────────────
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

KB_BASE_HEADERS = {
    "Referer":          "https://kbland.kr/",
    "Accept":           "application/json, text/plain, */*",
    "Accept-Language":  "ko-KR,ko;q=0.9",
    "Accept-Encoding":  "gzip, deflate, br",
    "Origin":           "https://kbland.kr",
    "Content-Type":     "application/json",
}

# ── 파일 경로 ────────────────────────────────────────────────────────────
DIR_RAW          = "data/raw"
DIR_RAW_MPRI     = "data/raw/phase2_mpri"
DIR_RAW_MOLIT    = "data/raw/phase3_molit"
DIR_CHECKPOINT   = "data/checkpoint"
DIR_PROCESSED    = "data/processed"
DIR_LOGS         = "logs"

FILE_PHASE1           = f"{DIR_RAW}/phase1_complexes.json"
FILE_REGION_MAP       = f"{DIR_RAW}/region_complex_map.json"
FILE_CHECKPOINT_MPRI  = f"{DIR_CHECKPOINT}/done_mpri.txt"
FILE_CHECKPOINT_MOLIT = f"{DIR_CHECKPOINT}/done_molit.txt"
FILE_FAILED_MPRI      = f"{DIR_CHECKPOINT}/failed_mpri.txt"
FILE_FAILED_MOLIT     = f"{DIR_CHECKPOINT}/failed_molit.txt"
FILE_CSV_OUTPUT       = f"{DIR_PROCESSED}/kb_apt_seoul_full.csv"

# ── 국토부 실거래가 API ──────────────────────────────────────────────────
MOLIT_BASE_URL          = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
MOLIT_ROWS_PER_PAGE     = 1000     # 최대 1000
MOLIT_TIMESERIES_MONTHS = 60       # 5년치 (60개월)
MOLIT_SEMAPHORE_LIMIT   = 5        # 국토부 API 더 보수적으로
MOLIT_JITTER_MIN        = 0.5
MOLIT_JITTER_MAX        = 1.0
