from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import setup_logger


@dataclass
class DatasetBundle:
    train: pd.DataFrame
    valid: pd.DataFrame
    test: pd.DataFrame
    feature_columns: list[str]
    categorical_columns: list[str]
    target_column: str
    id_columns: list[str]


def resolve_feature_columns(config: dict[str, Any]) -> list[str]:
    data_cfg = config["data"]
    features: list[str] = []

    for col in data_cfg.get("feature_columns") or []:
        if col not in features:
            features.append(col)

    feature_sets = data_cfg.get("feature_sets") or {}
    for set_name in data_cfg.get("active_feature_sets") or []:
        if set_name not in feature_sets:
            raise KeyError(f"Unknown feature set in config: {set_name}")
        for col in feature_sets[set_name]:
            if col not in features:
                features.append(col)

    if not features:
        raise ValueError("No feature columns configured. Use feature_columns or active_feature_sets.")
    return features


def load_raw_data(config: dict[str, Any]) -> pd.DataFrame:
    data_path = Path(config["paths"]["data_path"])
    df = pd.read_csv(data_path, encoding="utf-8-sig")
    date_col = config["data"]["date_column"]
    df[date_col] = pd.to_datetime(df[date_col])
    return df


def _apply_row_limits(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    data_cfg = config["data"]
    sample_frac = data_cfg.get("sample_frac")
    max_rows = data_cfg.get("max_rows")
    random_state = config["project"].get("random_state", 42)
    if sample_frac:
        df = df.sample(frac=float(sample_frac), random_state=random_state)
    if max_rows:
        df = df.head(int(max_rows))
    return df


def _apply_row_filters(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    filters = config["data"].get("row_filters") or {}
    out = df
    for col, allowed in filters.items():
        if col not in out.columns:
            raise KeyError(f"Missing row filter column in data: {col}")
        values = allowed if isinstance(allowed, list) else [allowed]
        out = out[out[col].isin(values)]
    return out.copy()


def build_model_frame(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    target = config["data"]["target_column"]
    evaluation_target = config["data"].get("evaluation_target_column")
    features = resolve_feature_columns(config)
    ids = config["data"].get("id_columns", [])
    required = list(dict.fromkeys(ids + features + [target] + ([evaluation_target] if evaluation_target else [])))
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise KeyError(f"Missing columns in data: {missing}")
    out = df[required].copy()
    out = _apply_row_filters(out, config)
    if config["data"].get("drop_missing_target", True):
        out = out[out[target].notna()].copy()
    out = _apply_row_limits(out, config)
    for col in config["data"].get("categorical_columns", []):
        if col in out.columns:
            out[col] = out[col].astype("category")
    return out


def split_dataset(model_df: pd.DataFrame, config: dict[str, Any]) -> DatasetBundle:
    date_col = config["data"]["date_column"]
    target = config["data"]["target_column"]
    features = resolve_feature_columns(config)
    categoricals = config["data"].get("categorical_columns", [])
    ids = config["data"].get("id_columns", [])
    split = config["split"]

    strategy = split.get("strategy")
    if strategy == "time":
        train_end = pd.Timestamp(split["train_end"])
        valid_end = pd.Timestamp(split["valid_end"])
        test_start = pd.Timestamp(split["test_start"])

        train = model_df[model_df[date_col] <= train_end].copy()
        valid = model_df[(model_df[date_col] > train_end) & (model_df[date_col] <= valid_end)].copy()
        test = model_df[model_df[date_col] >= test_start].copy()
    elif strategy == "time_ratio":
        train_ratio = float(split.get("train_ratio", 0.7))
        valid_ratio = float(split.get("valid_ratio", 0.2))
        test_ratio = float(split.get("test_ratio", 0.1))
        ratio_sum = train_ratio + valid_ratio + test_ratio
        if abs(ratio_sum - 1.0) > 1e-6:
            raise ValueError(f"Split ratios must sum to 1.0. Got {ratio_sum}")

        dates = sorted(model_df[date_col].dropna().unique())
        if len(dates) < 3:
            raise ValueError("At least three unique dates are required for time_ratio split.")
        train_n = max(1, int(len(dates) * train_ratio))
        valid_n = max(1, int(len(dates) * valid_ratio))
        if train_n + valid_n >= len(dates):
            valid_n = max(1, len(dates) - train_n - 1)
        train_dates = set(dates[:train_n])
        valid_dates = set(dates[train_n : train_n + valid_n])
        test_dates = set(dates[train_n + valid_n :])

        train = model_df[model_df[date_col].isin(train_dates)].copy()
        valid = model_df[model_df[date_col].isin(valid_dates)].copy()
        test = model_df[model_df[date_col].isin(test_dates)].copy()
    elif strategy == "time_train_test_ratio":
        train_ratio = float(split.get("train_ratio", 0.9))
        test_ratio = float(split.get("test_ratio", 0.1))
        ratio_sum = train_ratio + test_ratio
        if abs(ratio_sum - 1.0) > 1e-6:
            raise ValueError(f"Train/test ratios must sum to 1.0. Got {ratio_sum}")

        dates = sorted(model_df[date_col].dropna().unique())
        if len(dates) < 2:
            raise ValueError("At least two unique dates are required for time_train_test_ratio split.")
        train_n = max(1, int(len(dates) * train_ratio))
        if train_n >= len(dates):
            train_n = len(dates) - 1
        train_dates = set(dates[:train_n])
        test_dates = set(dates[train_n:])

        train = model_df[model_df[date_col].isin(train_dates)].copy()
        valid = model_df.iloc[0:0].copy()
        test = model_df[model_df[date_col].isin(test_dates)].copy()
    elif strategy == "time_by_horizon_tail":
        horizon_col = split.get("horizon_column", "horizon_months")
        if horizon_col not in model_df.columns:
            raise KeyError(f"Missing horizon split column: {horizon_col}")

        valid_tail_months = int(split.get("valid_tail_months", 5))
        test_tail_months = int(split.get("test_tail_months", 5))
        if valid_tail_months < 1 or test_tail_months < 1:
            raise ValueError("valid_tail_months and test_tail_months must be positive.")

        train_parts = []
        valid_parts = []
        test_parts = []
        min_train_dates = int(split.get("min_train_dates", 1))
        short_horizon_train_only = bool(split.get("short_horizon_train_only", False))
        for _, group in model_df.groupby(horizon_col, sort=True, observed=True):
            dates = sorted(group[date_col].dropna().unique())
            required_dates = min_train_dates + valid_tail_months + test_tail_months
            if len(dates) < required_dates:
                if short_horizon_train_only:
                    train_parts.append(group)
                    continue
                raise ValueError(
                    f"Not enough dates for {horizon_col}={group[horizon_col].iloc[0]}: "
                    f"{len(dates)} < {required_dates}"
                )
            test_dates = set(dates[-test_tail_months:])
            valid_dates = set(dates[-(valid_tail_months + test_tail_months) : -test_tail_months])
            train_dates = set(dates[: -(valid_tail_months + test_tail_months)])

            train_parts.append(group[group[date_col].isin(train_dates)])
            valid_parts.append(group[group[date_col].isin(valid_dates)])
            test_parts.append(group[group[date_col].isin(test_dates)])

        train = pd.concat(train_parts, ignore_index=False).copy()
        valid = pd.concat(valid_parts, ignore_index=False).copy()
        test = pd.concat(test_parts, ignore_index=False).copy()
    else:
        raise ValueError(f"Unsupported split strategy: {strategy}")

    return DatasetBundle(
        train=train,
        valid=valid,
        test=test,
        feature_columns=features,
        categorical_columns=[col for col in categoricals if col in features],
        target_column=target,
        id_columns=ids,
    )


def log_feature_preview(bundle: DatasetBundle) -> None:
    logger = setup_logger("ml_project.preprocessing")
    logger.info("Model target column: %s", bundle.target_column)
    logger.info("Model feature columns (%d): %s", len(bundle.feature_columns), bundle.feature_columns)
    logger.info("Categorical columns (%d): %s", len(bundle.categorical_columns), bundle.categorical_columns)
    logger.info("Train/valid/test rows: %d / %d / %d", len(bundle.train), len(bundle.valid), len(bundle.test))
    if len(bundle.train) > 0:
        preview = bundle.train[bundle.feature_columns].head(1).to_dict(orient="records")[0]
        logger.info("First training feature row example: %s", preview)


def prepare_dataset(config: dict[str, Any]) -> DatasetBundle:
    raw = load_raw_data(config)
    model_df = build_model_frame(raw, config)
    bundle = split_dataset(model_df, config)
    log_feature_preview(bundle)
    return bundle
