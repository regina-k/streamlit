from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logger(name: str = "ml_project", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        logger.addHandler(handler)
    return logger


def save_json(obj: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def mean_absolute_error_np(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def root_mean_squared_error_np(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(np.mean((y_true - y_pred) ** 2)))


def r2_score_np(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    return float(1 - ss_res / ss_tot) if ss_tot else float("nan")


def mean_absolute_percentage_error_np(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = np.where(np.abs(y_true) < 1e-9, np.nan, np.abs(y_true))
    return float(np.nanmean(np.abs((y_true - y_pred) / denom)) * 100)


def spearman_corr_np(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    true_rank = pd.Series(y_true).rank(method="average").to_numpy()
    pred_rank = pd.Series(y_pred).rank(method="average").to_numpy()
    if np.std(true_rank) == 0 or np.std(pred_rank) == 0:
        return float("nan")
    return float(np.corrcoef(true_rank, pred_rank)[0, 1])


def bias_np(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(y_pred - y_true))


def evaluate_metrics(y_true: np.ndarray, y_pred: np.ndarray, metrics: list[str]) -> dict[str, float]:
    funcs = {
        "mae": mean_absolute_error_np,
        "rmse": root_mean_squared_error_np,
        "r2": r2_score_np,
        "mape": mean_absolute_percentage_error_np,
        "spearman": spearman_corr_np,
        "bias": bias_np,
    }
    out: dict[str, float] = {}
    for metric in metrics:
        if metric not in funcs:
            raise ValueError(f"Unsupported metric: {metric}")
        out[metric] = funcs[metric](np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float))
    return out


def timestamp_tag() -> str:
    return pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
