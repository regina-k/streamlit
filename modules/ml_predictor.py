"""Apartment return prediction helpers."""

from __future__ import annotations

import pickle
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import MODELS_DIR


STREAMLIT_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = STREAMLIT_DIR.parent
ML_MODEL_DIR = STREAMLIT_DIR / "ml_model"
ML_SRC_DIR = ML_MODEL_DIR / "src"

DEFAULT_MODEL_PATH = (
    ML_MODEL_DIR
    / "outputs"
    / "models"
    / "apartment_return_lightgbm_ver7d_gu_price_calibrated_target_return_pct_20260622_001315.pkl"
)
DEFAULT_FEATURE_STORE_PATH = ROOT_DIR / "data" / "integration" / "apartment_12m_ver6f_stability_features.csv"
DEFAULT_ERROR_PROFILE_PATH = (
    ML_MODEL_DIR / "outputs" / "performance" / "ver06220040_ver7d_error_profile.csv"
)

MULTIHORIZON_MODEL_PATH = (
    ML_MODEL_DIR
    / "outputs"
    / "models"
    / "ver16_service_multihorizon_base_model.pkl"
)
MULTIHORIZON_FEATURE_STORE_PATH = (
    ROOT_DIR / "data" / "integration" / "apartment_multihorizon_ver9_latest_features.csv"
)
COMPLEX_RESIDUAL_OFFSET_PATH = (
    ML_MODEL_DIR / "outputs" / "calibration" / "ver11_complex_residual_offsets.csv"
)
HORIZON_COMPLEX_RESIDUAL_OFFSET_PATH = (
    ML_MODEL_DIR / "outputs" / "calibration" / "ver12c_recent3_horizon_complex_residual_offsets.csv"
)
GROUP_RESIDUAL_FALLBACK_PATH = (
    ML_MODEL_DIR / "outputs" / "calibration" / "ver12d_group_residual_fallback_offsets.csv"
)
APT_SIZE_RESIDUAL_OFFSET_PATH = (
    ML_MODEL_DIR / "outputs" / "calibration" / "ver16_hierarchical_apt_size_offsets.csv"
)
APT_SIZE_RESIDUAL_ADJUSTMENT_PATH = (
    ML_MODEL_DIR / "outputs" / "calibration" / "ver14_apt_size_residual_adjustments.csv"
)

MODEL_VERSION = "ver7d_lightgbm_12m_gu_price_calibrated"
MULTIHORIZON_MODEL_VERSION = "ver16_hierarchical_apt_size_residual"
SUPPORTED_HORIZON = "1yr"
DEFAULT_INTERVAL_P80 = 11.460
DEFAULT_INTERVAL_P90 = 16.751
LOW_CONFIDENCE_GU: set[str] = set()
HORIZON_ALIASES = {
    "12": 12,
    "12m": 12,
    "1y": 12,
    "1yr": 12,
    "24": 24,
    "24m": 24,
    "2y": 24,
    "2yr": 24,
    "36": 36,
    "36m": 36,
    "3y": 36,
    "3yr": 36,
    "48": 48,
    "48m": 48,
    "4y": 48,
    "4yr": 48,
    "60": 60,
    "60m": 60,
    "5y": 60,
    "5yr": 60,
}
SUPPORTED_HORIZON_MONTHS = {12, 24, 36, 48, 60}
MULTIHORIZON_INTERVALS = {
    "apt_size_blend": {
        12: {"p80": 8.5582, "p90": 13.1908},
        24: {"p80": 9.1439, "p90": 14.6518},
        36: {"p80": 11.1150, "p90": 17.7943},
        48: {"p80": 7.7684, "p90": 12.0954},
    },
    "apt_size_id+horizon": {
        12: {"p80": 8.3515, "p90": 12.8203},
        24: {"p80": 9.5855, "p90": 15.2540},
        36: {"p80": 11.4296, "p90": 18.0955},
        48: {"p80": 7.8675, "p90": 12.2441},
    },
    "hier_apt_size_id+horizon": {
        12: {"p80": 8.2674, "p90": 12.8447},
        24: {"p80": 8.5971, "p90": 13.8572},
        36: {"p80": 10.4556, "p90": 16.8060},
        48: {"p80": 7.5701, "p90": 11.8045},
    },
    "complex_id+horizon": {
        12: {"p80": 9.6525, "p90": 14.4548},
        24: {"p80": 11.0926, "p90": 17.5971},
        36: {"p80": 12.4289, "p90": 19.9253},
        48: {"p80": 8.8773, "p90": 13.3852},
    },
    "horizon_global": {
        12: {"p80": 13.2247, "p90": 19.3750},
        24: {"p80": 14.2427, "p90": 25.3343},
        36: {"p80": 16.0776, "p90": 25.1585},
        48: {"p80": 12.1668, "p90": 17.8746},
    },
    "group_gu_area": {
        12: {"p80": 12.8111, "p90": 18.9264},
        24: {"p80": 13.6111, "p90": 22.5974},
        36: {"p80": 15.6115, "p90": 24.5332},
        48: {"p80": 11.4957, "p90": 16.8879},
    },
    "global": {
        60: {"p80": 10.4476, "p90": 16.1566},
    },
}
APT_SIZE_BLEND_ALPHA = 1.0

if str(ML_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(ML_SRC_DIR))

from ml_project.train import apply_calibration  # noqa: E402


def _to_int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _normalize_horizon(horizon: str) -> str:
    aliases = {"12m": "1yr", "1y": "1yr", "1yr": "1yr"}
    return aliases.get(str(horizon).lower(), str(horizon).lower())


def _horizon_months(horizon: str | int) -> int:
    if isinstance(horizon, (int, np.integer)):
        value = int(horizon)
    else:
        value = HORIZON_ALIASES.get(str(horizon).lower().strip())
        if value is None:
            raise ValueError(f"Unsupported horizon: {horizon}")
    if value not in SUPPORTED_HORIZON_MONTHS:
        raise ValueError(f"Unsupported horizon months: {value}")
    return value


def _area_bin(value: Any) -> str:
    area = pd.to_numeric(value, errors="coerce")
    if pd.isna(area):
        return "nan"
    if area <= 18:
        return "a18"
    if area <= 25:
        return "a25"
    if area <= 34:
        return "a34"
    if area <= 45:
        return "a45"
    return "a45p"


@lru_cache(maxsize=2)
def load_model(model_path: str | None = None) -> dict:
    path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
    if not path.exists():
        fallback = MODELS_DIR / path.name
        if fallback.exists():
            path = fallback
        else:
            raise FileNotFoundError(f"ML model file not found: {path}")
    with path.open("rb") as f:
        return pickle.load(f)


@lru_cache(maxsize=1)
def load_multihorizon_model() -> dict:
    if not MULTIHORIZON_MODEL_PATH.exists():
        raise FileNotFoundError(f"Multi-horizon ML model file not found: {MULTIHORIZON_MODEL_PATH}")
    with MULTIHORIZON_MODEL_PATH.open("rb") as f:
        return pickle.load(f)


@lru_cache(maxsize=1)
def _load_error_profile(path: str | None = None) -> pd.DataFrame:
    profile_path = Path(path) if path else DEFAULT_ERROR_PROFILE_PATH
    if not profile_path.exists():
        return pd.DataFrame()
    return pd.read_csv(profile_path, encoding="utf-8-sig")


def _feature_usecols(artifact: dict) -> list[str]:
    id_cols = [
        "apt_size_id",
        "complex_id",
        "area_serial_no",
        "date",
        "yyyymm",
        "complex_name",
        "gu",
        "kb_sale_price_manwon",
        "supply_area_pyeong",
        "exclusive_area_pyeong",
    ]
    return list(dict.fromkeys(id_cols + artifact["feature_columns"]))


@lru_cache(maxsize=1)
def _load_feature_store(path: str | None = None) -> pd.DataFrame:
    artifact = load_model()
    feature_path = Path(path) if path else DEFAULT_FEATURE_STORE_PATH
    if not feature_path.exists():
        raise FileNotFoundError(f"Feature store not found: {feature_path}")

    df = pd.read_csv(feature_path, usecols=_feature_usecols(artifact), encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"])
    for col in artifact["config"]["data"].get("categorical_columns", []):
        if col in df.columns:
            df[col] = df[col].astype("category")
    return df


@lru_cache(maxsize=1)
def _load_multihorizon_feature_store(path: str | None = None) -> pd.DataFrame:
    artifact = load_multihorizon_model()
    feature_path = Path(path) if path else MULTIHORIZON_FEATURE_STORE_PATH
    if not feature_path.exists():
        raise FileNotFoundError(f"Multi-horizon feature store not found: {feature_path}")

    df = pd.read_csv(feature_path, usecols=_feature_usecols(artifact), encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"])
    for col in artifact["config"]["data"].get("categorical_columns", []):
        if col in df.columns:
            df[col] = df[col].astype("category")
    return df


@lru_cache(maxsize=1)
def _load_complex_residual_offsets(path: str | None = None) -> tuple[dict[int, dict[str, float]], float]:
    offset_path = Path(path) if path else COMPLEX_RESIDUAL_OFFSET_PATH
    if not offset_path.exists():
        return {}, 0.0
    df = pd.read_csv(offset_path, encoding="utf-8-sig")
    global_offset = float(df["global_offset"].iloc[0]) if "global_offset" in df.columns and not df.empty else 0.0
    source_min_date = str(df["source_min_date"].iloc[0]) if "source_min_date" in df.columns and not df.empty else ""
    source_max_date = str(df["source_max_date"].iloc[0]) if "source_max_date" in df.columns and not df.empty else ""
    test_min_date = str(df["test_min_date"].iloc[0]) if "test_min_date" in df.columns and not df.empty else ""
    test_max_date = str(df["test_max_date"].iloc[0]) if "test_max_date" in df.columns and not df.empty else ""
    offsets = {
        int(row["complex_id"]): {
            "residual_offset": float(row["residual_offset"]),
            "valid_rows": int(row["valid_rows"]) if pd.notna(row.get("valid_rows")) else 0,
            "source_min_date": source_min_date,
            "source_max_date": source_max_date,
            "test_min_date": test_min_date,
            "test_max_date": test_max_date,
        }
        for _, row in df.iterrows()
        if pd.notna(row.get("complex_id")) and pd.notna(row.get("residual_offset"))
    }
    offsets[-1] = {
        "residual_offset": global_offset,
        "valid_rows": 0,
        "source_min_date": source_min_date,
        "source_max_date": source_max_date,
        "test_min_date": test_min_date,
        "test_max_date": test_max_date,
    }
    return offsets, global_offset


@lru_cache(maxsize=1)
def _load_horizon_complex_residual_offsets(
    path: str | None = None,
) -> tuple[dict[tuple[int, int], dict[str, float]], float]:
    offset_path = Path(path) if path else HORIZON_COMPLEX_RESIDUAL_OFFSET_PATH
    if not offset_path.exists():
        return {}, 0.0
    df = pd.read_csv(offset_path, encoding="utf-8-sig")
    global_offset = float(df["global_offset"].iloc[0]) if "global_offset" in df.columns and not df.empty else 0.0
    global_source_min_date = (
        str(df["source_min_date"].min()) if "source_min_date" in df.columns and not df.empty else ""
    )
    global_source_max_date = (
        str(df["source_max_date"].max()) if "source_max_date" in df.columns and not df.empty else ""
    )
    test_min_date = str(df["test_min_date"].iloc[0]) if "test_min_date" in df.columns and not df.empty else ""
    test_max_date = str(df["test_max_date"].iloc[0]) if "test_max_date" in df.columns and not df.empty else ""
    offsets = {
        (int(row["complex_id"]), int(row["horizon_months"])): {
            "residual_offset": float(row["residual_offset"]),
            "valid_rows": int(row["valid_rows"]) if pd.notna(row.get("valid_rows")) else 0,
            "source_min_date": str(row.get("source_min_date", "")),
            "source_max_date": str(row.get("source_max_date", "")),
            "test_min_date": test_min_date,
            "test_max_date": test_max_date,
        }
        for _, row in df.iterrows()
        if pd.notna(row.get("complex_id"))
        and pd.notna(row.get("horizon_months"))
        and pd.notna(row.get("residual_offset"))
    }
    offsets[(-1, -1)] = {
        "residual_offset": global_offset,
        "valid_rows": 0,
        "source_min_date": global_source_min_date,
        "source_max_date": global_source_max_date,
        "test_min_date": test_min_date,
        "test_max_date": test_max_date,
    }
    return offsets, global_offset


@lru_cache(maxsize=1)
def _load_group_residual_fallbacks(
    path: str | None = None,
) -> dict[tuple[int, str, str], dict[str, Any]]:
    offset_path = Path(path) if path else GROUP_RESIDUAL_FALLBACK_PATH
    if not offset_path.exists():
        return {}
    df = pd.read_csv(offset_path, encoding="utf-8-sig")
    return {
        (int(row["horizon_months"]), str(row["gu"]), str(row["area_bin"])): {
            "residual_offset": float(row["residual_offset"]),
            "valid_rows": int(row["valid_rows"]) if pd.notna(row.get("valid_rows")) else 0,
            "source_min_date": str(row.get("source_min_date", "")),
            "source_max_date": str(row.get("source_max_date", "")),
            "test_min_date": "",
            "test_max_date": "",
        }
        for _, row in df.iterrows()
        if pd.notna(row.get("horizon_months"))
        and pd.notna(row.get("gu"))
        and pd.notna(row.get("area_bin"))
        and pd.notna(row.get("residual_offset"))
    }


@lru_cache(maxsize=1)
def _load_apt_size_residual_offsets(
    path: str | None = None,
) -> dict[tuple[str, int], dict[str, Any]]:
    offset_path = Path(path) if path else APT_SIZE_RESIDUAL_OFFSET_PATH
    if not offset_path.exists():
        return {}
    df = pd.read_csv(offset_path, encoding="utf-8-sig")
    return {
        (str(row["apt_size_id"]), int(row["horizon_months"])): {
            "residual_offset": float(row["residual_offset"]),
            "valid_rows": int(row["valid_rows"]) if pd.notna(row.get("valid_rows")) else 0,
            "source_min_date": str(row.get("source_min_date", "")),
            "source_max_date": str(row.get("source_max_date", "")),
            "test_min_date": "",
            "test_max_date": "",
            "source_months": int(row["source_months"]) if pd.notna(row.get("source_months")) else 0,
            "shrinkage": float(row["shrinkage"]) if pd.notna(row.get("shrinkage")) else 0.0,
            "min_rows": int(row["min_rows"]) if pd.notna(row.get("min_rows")) else 0,
            "prior_mean": float(row["prior_mean"]) if pd.notna(row.get("prior_mean")) else None,
            "raw_mean": float(row["raw_mean"]) if pd.notna(row.get("raw_mean")) else None,
            "shrink_weight": float(row["shrink_weight"]) if pd.notna(row.get("shrink_weight")) else None,
        }
        for _, row in df.iterrows()
        if pd.notna(row.get("apt_size_id"))
        and pd.notna(row.get("horizon_months"))
        and pd.notna(row.get("residual_offset"))
    }


@lru_cache(maxsize=1)
def _load_apt_size_residual_adjustments(
    path: str | None = None,
) -> dict[tuple[str, int], dict[str, Any]]:
    adjustment_path = Path(path) if path else APT_SIZE_RESIDUAL_ADJUSTMENT_PATH
    if not adjustment_path.exists():
        return {}
    df = pd.read_csv(adjustment_path, encoding="utf-8-sig")
    return {
        (str(row["apt_size_id"]), int(row["horizon_months"])): {
            "residual_adjustment": float(row["residual_adjustment"]),
            "valid_rows": int(row["valid_rows"]) if pd.notna(row.get("valid_rows")) else 0,
            "source_months": int(row["source_months"]) if pd.notna(row.get("source_months")) else 0,
            "shrinkage": float(row["shrinkage"]) if pd.notna(row.get("shrinkage")) else 0.0,
            "min_rows": int(row["min_rows"]) if pd.notna(row.get("min_rows")) else 0,
        }
        for _, row in df.iterrows()
        if pd.notna(row.get("apt_size_id"))
        and pd.notna(row.get("horizon_months"))
        and pd.notna(row.get("residual_adjustment"))
    }


def _complex_residual_metadata(row: pd.Series) -> dict[str, Any]:
    offsets, global_offset = _load_complex_residual_offsets()
    complex_id = _to_int_or_none(row.get("complex_id"))
    matched = offsets.get(complex_id)
    if matched:
        return {
            "offset_applied": True,
            "residual_offset": matched["residual_offset"],
            "valid_rows": matched["valid_rows"],
            "source_min_date": matched.get("source_min_date", ""),
            "source_max_date": matched.get("source_max_date", ""),
            "test_min_date": matched.get("test_min_date", ""),
            "test_max_date": matched.get("test_max_date", ""),
            "fallback": "complex_id",
        }
    global_meta = offsets.get(-1, {})
    return {
        "offset_applied": False,
        "residual_offset": global_offset,
        "valid_rows": 0,
        "source_min_date": global_meta.get("source_min_date", ""),
        "source_max_date": global_meta.get("source_max_date", ""),
        "test_min_date": global_meta.get("test_min_date", ""),
        "test_max_date": global_meta.get("test_max_date", ""),
        "fallback": "global",
    }


def _base_horizon_residual_metadata(row: pd.Series, horizon_months: int) -> dict[str, Any]:
    offsets, global_offset = _load_horizon_complex_residual_offsets()
    complex_id = _to_int_or_none(row.get("complex_id"))
    matched = offsets.get((complex_id, horizon_months))
    if matched:
        return {
            "offset_applied": True,
            "residual_offset": matched["residual_offset"],
            "valid_rows": matched["valid_rows"],
            "source_min_date": matched.get("source_min_date", ""),
            "source_max_date": matched.get("source_max_date", ""),
            "test_min_date": matched.get("test_min_date", ""),
            "test_max_date": matched.get("test_max_date", ""),
            "fallback": "complex_id+horizon",
        }
    group_fallbacks = _load_group_residual_fallbacks()
    group_key = (horizon_months, str(row.get("gu", "")), _area_bin(row.get("exclusive_area_pyeong")))
    group_fallback = group_fallbacks.get(group_key)
    if group_fallback:
        return {
            "offset_applied": False,
            "residual_offset": group_fallback["residual_offset"],
            "valid_rows": group_fallback["valid_rows"],
            "source_min_date": group_fallback.get("source_min_date", ""),
            "source_max_date": group_fallback.get("source_max_date", ""),
            "test_min_date": group_fallback.get("test_min_date", ""),
            "test_max_date": group_fallback.get("test_max_date", ""),
            "fallback": "group_gu_area",
        }
    horizon_fallback = offsets.get((-1, horizon_months))
    if horizon_fallback:
        return {
            "offset_applied": False,
            "residual_offset": horizon_fallback["residual_offset"],
            "valid_rows": horizon_fallback["valid_rows"],
            "source_min_date": horizon_fallback.get("source_min_date", ""),
            "source_max_date": horizon_fallback.get("source_max_date", ""),
            "test_min_date": horizon_fallback.get("test_min_date", ""),
            "test_max_date": horizon_fallback.get("test_max_date", ""),
            "fallback": "horizon_global",
        }
    global_meta = offsets.get((-1, -1), {})
    return {
        "offset_applied": False,
        "residual_offset": global_offset,
        "valid_rows": 0,
        "source_min_date": global_meta.get("source_min_date", ""),
        "source_max_date": global_meta.get("source_max_date", ""),
        "test_min_date": global_meta.get("test_min_date", ""),
        "test_max_date": global_meta.get("test_max_date", ""),
        "fallback": "global",
    }


def _horizon_complex_residual_metadata(row: pd.Series, horizon_months: int) -> dict[str, Any]:
    apt_size_offsets = _load_apt_size_residual_offsets()
    apt_size_adjustments = _load_apt_size_residual_adjustments()
    apt_size_id = str(row.get("apt_size_id", ""))
    apt_size_match = apt_size_offsets.get((apt_size_id, horizon_months))
    base_meta = _base_horizon_residual_metadata(row, horizon_months)
    if apt_size_match:
        adjustment = apt_size_adjustments.get((apt_size_id, horizon_months))
        if adjustment and APT_SIZE_BLEND_ALPHA < 1.0:
            residual_offset = (
                APT_SIZE_BLEND_ALPHA * float(apt_size_match["residual_offset"])
                + (1 - APT_SIZE_BLEND_ALPHA)
                * (float(base_meta["residual_offset"]) + float(adjustment["residual_adjustment"]))
            )
            return {
                "offset_applied": True,
                "residual_offset": residual_offset,
                "valid_rows": apt_size_match["valid_rows"],
                "source_min_date": apt_size_match.get("source_min_date", ""),
                "source_max_date": apt_size_match.get("source_max_date", ""),
                "test_min_date": apt_size_match.get("test_min_date", ""),
                "test_max_date": apt_size_match.get("test_max_date", ""),
                "fallback": "apt_size_blend",
                "source_months": apt_size_match.get("source_months", 0),
                "shrinkage": apt_size_match.get("shrinkage", 0.0),
                "min_rows": apt_size_match.get("min_rows", 0),
                "blend_alpha_ver13": APT_SIZE_BLEND_ALPHA,
                "blend_alpha_ver14": 1 - APT_SIZE_BLEND_ALPHA,
                "base_fallback": base_meta.get("fallback", ""),
                "adjustment_valid_rows": adjustment.get("valid_rows", 0),
                "adjustment_shrinkage": adjustment.get("shrinkage", 0.0),
                "adjustment_min_rows": adjustment.get("min_rows", 0),
            }
        return {
            "offset_applied": True,
            "residual_offset": apt_size_match["residual_offset"],
            "valid_rows": apt_size_match["valid_rows"],
            "source_min_date": apt_size_match.get("source_min_date", ""),
            "source_max_date": apt_size_match.get("source_max_date", ""),
            "test_min_date": apt_size_match.get("test_min_date", ""),
            "test_max_date": apt_size_match.get("test_max_date", ""),
            "fallback": "hier_apt_size_id+horizon",
            "source_months": apt_size_match.get("source_months", 0),
            "shrinkage": apt_size_match.get("shrinkage", 0.0),
            "min_rows": apt_size_match.get("min_rows", 0),
            "prior_mean": apt_size_match.get("prior_mean"),
            "raw_mean": apt_size_match.get("raw_mean"),
            "shrink_weight": apt_size_match.get("shrink_weight"),
            "base_fallback": base_meta.get("fallback", ""),
        }
    return base_meta


def _latest_rows(df: pd.DataFrame) -> pd.DataFrame:
    max_date = df["date"].max()
    return df[df["date"].eq(max_date)].copy()


def _area_type_upper(area_type: str | None) -> float | None:
    if not area_type:
        return None
    digits = "".join(ch for ch in str(area_type) if ch.isdigit())
    if not digits:
        return None
    return float(digits)


def _filter_rows(
    df: pd.DataFrame,
    complex_id: int | str | None = None,
    apt_size_id: str | None = None,
    area_serial_no: int | str | None = None,
    current_price_manwon: float | None = None,
    region: str | None = None,
    area_type: str | None = None,
) -> pd.Series:
    complex_id_int = _to_int_or_none(complex_id)
    if complex_id_int is not None:
        df = df[df["complex_id"].astype(int).eq(complex_id_int)]
    if apt_size_id:
        df = df[df["apt_size_id"].astype(str).eq(str(apt_size_id))]
    area_serial_int = _to_int_or_none(area_serial_no)
    if area_serial_int is not None:
        df = df[df["area_serial_no"].astype(int).eq(area_serial_int)]
    if region:
        region_key = str(region).replace("서울", "").strip()
        if region_key:
            df = df[df["gu"].astype(str).str.contains(region_key, regex=False, na=False)]

    area_upper = _area_type_upper(area_type)
    if area_upper is not None and "exclusive_area_pyeong" in df.columns:
        df = df[df["exclusive_area_pyeong"].le(area_upper)]

    if df.empty:
        raise ValueError("No matching latest apartment feature row found.")

    if current_price_manwon and "kb_sale_price_manwon" in df.columns:
        price = pd.to_numeric(df["kb_sale_price_manwon"], errors="coerce")
        idx = (price - float(current_price_manwon)).abs().idxmin()
        return df.loc[idx]

    return df.sort_values(["complex_id", "area_serial_no"]).iloc[0]


def _select_feature_row(
    complex_id: int | str | None = None,
    apt_size_id: str | None = None,
    area_serial_no: int | str | None = None,
    current_price_manwon: float | None = None,
    region: str | None = None,
    area_type: str | None = None,
) -> pd.Series:
    return _filter_rows(
        _latest_rows(_load_feature_store()),
        complex_id=complex_id,
        apt_size_id=apt_size_id,
        area_serial_no=area_serial_no,
        current_price_manwon=current_price_manwon,
        region=region,
        area_type=area_type,
    )


def _select_multihorizon_feature_row(
    complex_id: int | str | None = None,
    apt_size_id: str | None = None,
    area_serial_no: int | str | None = None,
    current_price_manwon: float | None = None,
) -> pd.Series:
    return _filter_rows(
        _load_multihorizon_feature_store(),
        complex_id=complex_id,
        apt_size_id=apt_size_id,
        area_serial_no=area_serial_no,
        current_price_manwon=current_price_manwon,
    )


def _predict_with_artifact(row: pd.Series, artifact: dict) -> float:
    frame = pd.DataFrame([row])
    for col in artifact["config"]["data"].get("categorical_columns", []):
        if col in frame.columns:
            frame[col] = frame[col].astype("category")
    raw_pred = artifact["model"].predict(frame[artifact["feature_columns"]])
    pred = apply_calibration(frame, raw_pred, artifact.get("calibration", {"method": "none"}))
    return float(np.asarray(pred)[0])


def _predict_row(row: pd.Series) -> float:
    return _predict_with_artifact(row, load_model())


def _predict_multihorizon_row(row: pd.Series, horizon_months: int) -> tuple[float, dict[str, Any]]:
    row = row.copy()
    row["horizon_months"] = horizon_months
    pred = _predict_with_artifact(row, load_multihorizon_model())
    calibration = _horizon_complex_residual_metadata(row, horizon_months)
    return pred + float(calibration["residual_offset"]), calibration


def _error_interval_for_row(row: pd.Series) -> dict:
    profile = _load_error_profile()
    interval = {
        "p80_abs_error_pctp": DEFAULT_INTERVAL_P80,
        "p90_abs_error_pctp": DEFAULT_INTERVAL_P90,
        "source": "overall",
    }
    if profile.empty:
        return interval

    gu_key = f"gu={row.get('gu')}"
    matched = profile[profile["group"].eq(gu_key)]
    if not matched.empty and int(matched.iloc[0]["rows"]) >= 100:
        interval.update(
            {
                "p80_abs_error_pctp": float(matched.iloc[0]["abs_error_p80"]),
                "p90_abs_error_pctp": float(matched.iloc[0]["abs_error_p90"]),
                "source": gu_key,
            }
        )
    return interval


def _confidence(row: pd.Series, interval: dict) -> str:
    gu = str(row.get("gu", ""))
    if gu in LOW_CONFIDENCE_GU:
        return "low"
    if float(interval["p90_abs_error_pctp"]) <= 15:
        return "medium"
    return "low"


def predict_apartment_growth(
    complex_id: int | str | None = None,
    area_serial_no: int | str | None = None,
    current_price_manwon: float | None = None,
    apt_size_id: str | None = None,
) -> dict:
    """Predict 12-month return for a clicked apartment complex/size."""
    row = _select_feature_row(
        complex_id=complex_id,
        area_serial_no=area_serial_no,
        current_price_manwon=current_price_manwon,
        apt_size_id=apt_size_id,
    )
    pred = _predict_row(row)
    interval = _error_interval_for_row(row)
    confidence = _confidence(row, interval)

    return {
        "complex_id": int(row["complex_id"]),
        "apt_size_id": str(row["apt_size_id"]),
        "area_serial_no": int(row["area_serial_no"]),
        "complex_name": str(row.get("complex_name", "")),
        "region": str(row.get("gu", "")),
        "horizon": SUPPORTED_HORIZON,
        "base_yyyymm": int(row["yyyymm"]),
        "base_date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
        "kb_sale_price_manwon": float(row["kb_sale_price_manwon"]),
        "predicted_growth_pct": pred,
        "prediction_interval_p80": {
            "lower": pred - interval["p80_abs_error_pctp"],
            "upper": pred + interval["p80_abs_error_pctp"],
            "half_width_pctp": interval["p80_abs_error_pctp"],
        },
        "prediction_interval_p90": {
            "lower": pred - interval["p90_abs_error_pctp"],
            "upper": pred + interval["p90_abs_error_pctp"],
            "half_width_pctp": interval["p90_abs_error_pctp"],
        },
        "confidence": confidence,
        "model_version": MODEL_VERSION,
        "note": f"ver7d model with residual interval profile ({interval['source']})",
    }


def predict_apartment_growth_horizons(
    complex_id: int | str | None = None,
    area_serial_no: int | str | None = None,
    current_price_manwon: float | None = None,
    apt_size_id: str | None = None,
    horizons: tuple[str | int, ...] = ("12m", "24m", "36m", "60m"),
) -> dict:
    """Predict returns for multiple horizons with the ver9b multi-horizon model."""
    row = _select_multihorizon_feature_row(
        complex_id=complex_id,
        area_serial_no=area_serial_no,
        current_price_manwon=current_price_manwon,
        apt_size_id=apt_size_id,
    )
    residual_calibrations = []

    predictions = []
    for horizon in horizons:
        months = _horizon_months(horizon)
        pred, calibration = _predict_multihorizon_row(row, months)
        residual_calibrations.append({"horizon_months": months, **calibration})
        fallback_type = str(calibration.get("fallback", "global"))
        interval = MULTIHORIZON_INTERVALS.get(fallback_type, {}).get(
            months,
            MULTIHORIZON_INTERVALS["global"].get(months, {"p80": 10.4476, "p90": 16.1566}),
        )
        exact_fallbacks = {
            "apt_size_blend",
            "apt_size_id+horizon",
            "hier_apt_size_id+horizon",
            "complex_id+horizon",
        }
        confidence = "low" if months in {36, 60} or fallback_type not in exact_fallbacks else "medium"
        predictions.append(
            {
                "horizon_months": months,
                "horizon": f"{months}m",
                "predicted_growth_pct": pred,
                "prediction_interval_p80": {
                    "lower": pred - interval["p80"],
                    "upper": pred + interval["p80"],
                    "half_width_pctp": interval["p80"],
                },
                "prediction_interval_p90": {
                    "lower": pred - interval["p90"],
                    "upper": pred + interval["p90"],
                    "half_width_pctp": interval["p90"],
                },
                "confidence": confidence,
                "residual_calibration": calibration,
                "note": (
                    "60m uses global residual fallback because 60m had no test window."
                    if months == 60
                    else "ver16 hierarchical apt-size residual with fallback interval profile"
                ),
            }
        )

    primary_calibration = next(
        (item for item in residual_calibrations if item["offset_applied"]),
        residual_calibrations[0] if residual_calibrations else {},
    )

    return {
        "complex_id": int(row["complex_id"]),
        "apt_size_id": str(row["apt_size_id"]),
        "area_serial_no": int(row["area_serial_no"]),
        "complex_name": str(row.get("complex_name", "")),
        "region": str(row.get("gu", "")),
        "base_yyyymm": int(row["yyyymm"]),
        "base_date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
        "kb_sale_price_manwon": float(row["kb_sale_price_manwon"]),
        "model_version": MULTIHORIZON_MODEL_VERSION,
        "residual_calibration": primary_calibration,
        "residual_calibration_by_horizon": residual_calibrations,
        "predictions": predictions,
    }


def predict_price_growth(
    region: str,
    area_type: str,
    horizon: str,
    current_index: float | None = None,
) -> dict:
    """Predict apartment return while keeping the original app contract."""
    normalized_horizon = _normalize_horizon(horizon)
    if normalized_horizon != SUPPORTED_HORIZON:
        return {
            "region": region,
            "horizon": horizon,
            "predicted_growth_pct": 0.0,
            "confidence": "low",
            "model_version": MODEL_VERSION,
            "note": "Only 1yr/12m prediction is currently supported by this compatibility function.",
        }

    try:
        row = _select_feature_row(
            region=region,
            area_type=area_type,
            current_price_manwon=current_index,
        )
        pred = _predict_row(row)
        interval = _error_interval_for_row(row)
        return {
            "region": str(row.get("gu", region)),
            "horizon": horizon,
            "predicted_growth_pct": pred,
            "confidence": _confidence(row, interval),
            "model_version": MODEL_VERSION,
            "note": (
                f"Matched latest feature row {row['apt_size_id']} at "
                f"{pd.Timestamp(row['date']).strftime('%Y-%m-%d')}; "
                f"P80 +/- {interval['p80_abs_error_pctp']:.1f}%p"
            ),
        }
    except Exception as exc:
        return {
            "region": region,
            "horizon": horizon,
            "predicted_growth_pct": 0.0,
            "confidence": "low",
            "model_version": MODEL_VERSION,
            "note": f"Prediction unavailable: {exc}",
        }
