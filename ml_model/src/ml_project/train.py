from __future__ import annotations

import argparse
import pickle
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .models import build_model
from .preprocessing import prepare_dataset
from .utils import ensure_dir, evaluate_metrics, load_yaml, save_json, setup_logger, timestamp_tag


def evaluate_by_horizon(split_df, y_pred, target_column: str, metrics_enabled: list[str]) -> dict:
    if "horizon_months" not in split_df.columns:
        return {}
    out = {}
    tmp = split_df[["horizon_months", target_column]].copy()
    tmp["prediction"] = y_pred
    for horizon, group in tmp.groupby("horizon_months"):
        out[str(int(horizon))] = {
            "rows": int(len(group)),
            **evaluate_metrics(
                group[target_column].to_numpy(),
                group["prediction"].to_numpy(),
                metrics_enabled,
            ),
        }
    return out


def evaluate_by_group(
    split_df: pd.DataFrame,
    y_pred,
    target_column: str,
    metrics_enabled: list[str],
    group_config: dict | None,
) -> dict:
    if not group_config:
        return {}

    out = {}
    tmp = split_df.copy()
    tmp["prediction"] = y_pred
    quantile_bins = int(group_config.get("quantile_bins", 4))
    min_rows = int(group_config.get("min_rows", 30))

    for group_name, spec in (group_config.get("groups") or {}).items():
        col = spec["column"] if isinstance(spec, dict) else spec
        if col not in tmp.columns:
            continue

        labels = tmp[col]
        if isinstance(spec, dict) and spec.get("type") == "quantile":
            series = pd.to_numeric(tmp[col], errors="coerce")
            try:
                labels = pd.qcut(series, q=quantile_bins, duplicates="drop").astype(str)
            except ValueError:
                continue

        group_metrics = {}
        grouped = tmp.assign(_group_label=labels).dropna(subset=["_group_label"]).groupby("_group_label", observed=True)
        for label, group in grouped:
            if len(group) < min_rows:
                continue
            group_metrics[str(label)] = {
                "rows": int(len(group)),
                **evaluate_metrics(
                    group[target_column].to_numpy(),
                    group["prediction"].to_numpy(),
                    metrics_enabled,
                ),
            }
        out[group_name] = group_metrics
    return out


def transform_prediction(y_pred, config: dict):
    transform = config["data"].get("prediction_transform")
    if transform in (None, "none"):
        return y_pred
    if transform == "log_return_pct_to_return_pct":
        return np.expm1(np.asarray(y_pred, dtype=float) / 100.0) * 100.0
    raise ValueError(f"Unsupported prediction_transform: {transform}")


def transform_prediction_with_frame(split_df: pd.DataFrame, y_pred, config: dict):
    transform = config["data"].get("prediction_transform")
    if transform == "future_log_price_to_return_pct":
        current_price = split_df["kb_sale_price_manwon"].to_numpy(dtype=float)
        future_price_pred = np.exp(np.asarray(y_pred, dtype=float))
        return (future_price_pred / current_price - 1.0) * 100.0
    return transform_prediction(y_pred, config)


def evaluation_arrays(split_df: pd.DataFrame, y_pred, config: dict, target_column: str):
    evaluation_target = config["data"].get("evaluation_target_column")
    if not evaluation_target:
        return split_df[target_column].to_numpy(), y_pred, target_column
    return (
        split_df[evaluation_target].to_numpy(),
        transform_prediction_with_frame(split_df, y_pred, config),
        evaluation_target,
    )


def _calibration_key_frame(
    df: pd.DataFrame,
    groups: list[dict],
    learned_bins: dict[str, list[float]] | None = None,
) -> tuple[pd.Series, dict[str, list[float]]]:
    labels = []
    bins_out: dict[str, list[float]] = {}
    learned_bins = learned_bins or {}

    for spec in groups:
        col = spec["column"] if isinstance(spec, dict) else str(spec)
        name = spec.get("name", col) if isinstance(spec, dict) else col
        if col not in df.columns:
            raise KeyError(f"Missing calibration group column: {col}")

        if isinstance(spec, dict) and spec.get("type") == "quantile":
            if name in learned_bins:
                bins = learned_bins[name]
            else:
                _, bins_array = pd.qcut(
                    pd.to_numeric(df[col], errors="coerce"),
                    q=int(spec.get("bins", 4)),
                    duplicates="drop",
                    retbins=True,
                )
                bins = [float(x) for x in bins_array]
            bins_out[name] = bins
            label = pd.cut(
                pd.to_numeric(df[col], errors="coerce"),
                bins=bins,
                include_lowest=True,
            ).astype(str)
        else:
            label = df[col].astype("string").fillna("<NA>").astype(str)
        labels.append(name + "=" + label)

    key = labels[0]
    for label in labels[1:]:
        key = key + "\x1f" + label
    return key, bins_out


def build_calibration(
    valid_df: pd.DataFrame,
    model,
    config: dict,
    feature_columns: list[str],
    target_column: str,
) -> dict:
    calibration_cfg = config.get("calibration") or {}
    method = calibration_cfg.get("method")
    if method in (None, "none"):
        return {"method": "none", "global_offset": 0.0}
    if method not in {"valid_mean_residual", "grouped_mean_residual"}:
        raise ValueError(f"Unsupported calibration method: {method}")
    if valid_df.empty:
        raise ValueError(f"{method} calibration requires a non-empty validation split.")

    y_pred = model.predict(valid_df[feature_columns])
    y_true_eval, y_pred_eval, _ = evaluation_arrays(valid_df, y_pred, config, target_column)
    residual = pd.Series(y_true_eval - y_pred_eval, index=valid_df.index)
    global_offset = float(residual.mean())
    out = {"method": method, "global_offset": global_offset}

    if method == "grouped_mean_residual":
        groups = calibration_cfg.get("groups") or []
        if not groups:
            raise ValueError("grouped_mean_residual calibration requires calibration.groups.")
        keys, bins = _calibration_key_frame(valid_df, groups)
        stats = residual.groupby(keys).agg(["mean", "count"])
        shrinkage = float(calibration_cfg.get("shrinkage", 0.0))
        offsets = (stats["mean"] * stats["count"] + global_offset * shrinkage) / (stats["count"] + shrinkage)
        min_rows = int(calibration_cfg.get("min_rows", 1))
        offsets = offsets[stats["count"] >= min_rows]
        out.update(
            {
                "groups": groups,
                "bins": bins,
                "shrinkage": shrinkage,
                "min_rows": min_rows,
                "offsets": {str(k): float(v) for k, v in offsets.items()},
            }
        )
    return out


def apply_calibration(split_df: pd.DataFrame, y_pred_eval, calibration: dict):
    method = calibration.get("method")
    if method in (None, "none"):
        return y_pred_eval
    if method == "valid_mean_residual":
        return y_pred_eval + float(calibration.get("global_offset", 0.0))
    if method == "grouped_mean_residual":
        keys, _ = _calibration_key_frame(split_df, calibration["groups"], calibration.get("bins"))
        offsets = keys.map(calibration.get("offsets", {})).astype(float)
        offsets = offsets.fillna(float(calibration.get("global_offset", 0.0)))
        return y_pred_eval + offsets.to_numpy()
    raise ValueError(f"Unsupported calibration method: {method}")


def build_fit_params(config: dict) -> dict:
    fit_cfg = config["model"].get("fit", {}) or {}
    if not fit_cfg.get("early_stopping_rounds"):
        return {}

    try:
        from lightgbm import early_stopping, log_evaluation
    except ImportError as exc:
        raise ImportError("lightgbm is required for early stopping.") from exc

    callbacks = [
        early_stopping(int(fit_cfg["early_stopping_rounds"])),
        log_evaluation(int(fit_cfg.get("log_evaluation_period", 50))),
    ]
    out = {"callbacks": callbacks}
    eval_metric = fit_cfg.get("eval_metric")
    if eval_metric:
        out["eval_metric"] = eval_metric
    return out


def train(config_path: str | Path) -> dict:
    logger = setup_logger("ml_project.train")
    config = load_yaml(config_path)
    bundle = prepare_dataset(config)
    if bundle.train.empty:
        raise ValueError("Train split is empty. Check split dates and target availability.")
    if bundle.valid.empty:
        logger.warning("Validation split is empty.")
    if bundle.test.empty:
        logger.warning("Test split is empty.")

    X_train = bundle.train[bundle.feature_columns]
    y_train = bundle.train[bundle.target_column]
    X_valid = bundle.valid[bundle.feature_columns] if not bundle.valid.empty else None
    y_valid = bundle.valid[bundle.target_column] if not bundle.valid.empty else None
    model = build_model(config)
    model.fit(
        X_train,
        y_train,
        categorical_columns=bundle.categorical_columns,
        X_valid=X_valid,
        y_valid=y_valid,
        fit_params=build_fit_params(config),
    )
    calibration = build_calibration(
        bundle.valid,
        model,
        config,
        bundle.feature_columns,
        bundle.target_column,
    )
    if calibration.get("method") != "none":
        logger.info(
            "Prediction calibration: method=%s global_offset=%.6f groups=%d",
            calibration.get("method"),
            float(calibration.get("global_offset", 0.0)),
            len(calibration.get("offsets", {})),
        )

    metrics_enabled = config["metrics"]["enabled"]
    results = {}
    horizon_results = {}
    group_results = {}
    predictions = {}
    for split_name, split_df in [("train", bundle.train), ("valid", bundle.valid), ("test", bundle.test)]:
        if split_df.empty:
            continue
        y_pred = model.predict(split_df[bundle.feature_columns])
        y_true_eval, y_pred_eval, eval_target_name = evaluation_arrays(
            split_df, y_pred, config, bundle.target_column
        )
        y_pred_eval = apply_calibration(split_df, y_pred_eval, calibration)
        results[split_name] = evaluate_metrics(y_true_eval, y_pred_eval, metrics_enabled)
        horizon_results[split_name] = evaluate_by_horizon(
            split_df.assign(**{eval_target_name: y_true_eval}), y_pred_eval, eval_target_name, metrics_enabled
        )
        group_results[split_name] = evaluate_by_group(
            split_df.assign(**{eval_target_name: y_true_eval}),
            y_pred_eval,
            eval_target_name,
            metrics_enabled,
            config.get("group_evaluation"),
        )
        pred_df = split_df[bundle.id_columns + [bundle.target_column]].copy()
        if eval_target_name != bundle.target_column:
            pred_df[eval_target_name] = y_true_eval
        pred_df["prediction"] = y_pred
        if calibration.get("method") != "none":
            pred_df["prediction_calibrated"] = y_pred_eval
        if eval_target_name != bundle.target_column:
            pred_df["prediction_return_pct"] = y_pred_eval
        predictions[split_name] = pred_df
        logger.info("%s metrics: %s", split_name, results[split_name])
        if horizon_results[split_name]:
            logger.info("%s horizon metrics: %s", split_name, horizon_results[split_name])
        if group_results[split_name]:
            logger.info("%s group metrics: %s", split_name, group_results[split_name])

    tag = timestamp_tag()
    model_dir = ensure_dir(config["paths"]["model_dir"])
    prediction_dir = ensure_dir(config["paths"]["prediction_dir"])
    output_dir = ensure_dir(config["paths"]["output_dir"])

    model_path = model_dir / f"{config['project']['name']}_{bundle.target_column}_{tag}.pkl"
    with model_path.open("wb") as f:
        pickle.dump(
            {
                "model": model,
                "config": config,
                "feature_columns": bundle.feature_columns,
                "calibration": calibration,
                "calibration_offset": float(calibration.get("global_offset", 0.0)),
            },
            f,
        )

    metrics_path = output_dir / f"metrics_{bundle.target_column}_{tag}.json"
    save_json(
        {
            "model_path": str(model_path),
            "calibration": {
                k: v for k, v in calibration.items() if k != "offsets"
            } | {"offset_count": len(calibration.get("offsets", {}))},
            "metrics": results,
            "horizon_metrics": horizon_results,
            "group_metrics": group_results,
        },
        metrics_path,
    )

    prediction_paths = {}
    for split_name, pred_df in predictions.items():
        prediction_path = prediction_dir / f"predictions_{split_name}_{bundle.target_column}_{tag}.csv"
        pred_df.to_csv(prediction_path, index=False, encoding="utf-8-sig")
        prediction_paths[split_name] = str(prediction_path)

    logger.info("Saved model: %s", model_path)
    logger.info("Saved metrics: %s", metrics_path)
    return {
        "model_path": str(model_path),
        "metrics_path": str(metrics_path),
        "prediction_paths": prediction_paths,
        "tag": tag,
        "target_column": bundle.target_column,
        "metrics": results,
        "horizon_metrics": horizon_results,
        "group_metrics": group_results,
    }


def _resolve_config_path(path_value: str | Path, config_dir: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (config_dir / path).resolve()


def _resolve_repo_path(path_value: str | Path, repo_root: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def run_ver16_post_calibration(
    pipeline_config: dict,
    config_path: str | Path,
    train_result: dict,
) -> dict:
    logger = setup_logger("ml_project.train")
    config_path = Path(config_path).resolve()
    repo_root = config_path.parents[3]
    post_cfg = pipeline_config["post_calibration"]
    data_cfg = pipeline_config["data"]

    script_path = _resolve_repo_path(
        post_cfg.get("script", "scripts/compare_hierarchical_apt_size_shrinkage.py"),
        repo_root,
    )
    valid_predictions = train_result["prediction_paths"].get("valid")
    test_predictions = train_result["prediction_paths"].get("test")
    if not valid_predictions or not test_predictions:
        raise ValueError("ver16 post-calibration requires both valid and test prediction files.")

    output_grid = _resolve_repo_path(post_cfg["output_grid"], repo_root)
    output_offsets = _resolve_repo_path(post_cfg["output_offsets"], repo_root)
    service_model_output = post_cfg.get("service_model_output")
    service_model_path = None
    if service_model_output:
        service_model_path = _resolve_repo_path(service_model_output, repo_root)
        ensure_dir(service_model_path.parent)
        shutil.copy2(train_result["model_path"], service_model_path)
        logger.info("Copied service base model: %s", service_model_path)
    command = [
        sys.executable,
        str(script_path),
        "--features",
        str(_resolve_repo_path(data_cfg["training_feature_store"], repo_root)),
        "--valid-predictions",
        str(valid_predictions),
        "--test-predictions",
        str(test_predictions),
        "--complex-offsets",
        str(_resolve_repo_path(post_cfg["complex_offsets"], repo_root)),
        "--group-offsets",
        str(_resolve_repo_path(post_cfg["group_offsets"], repo_root)),
        "--output",
        str(output_grid),
        "--offsets-output",
        str(output_offsets),
        "--prediction-column",
        post_cfg.get("prediction_column", "prediction_calibrated"),
        "--target-column",
        data_cfg.get("target_column", "target_return_pct"),
        "--selected-source-months",
        str(post_cfg["source_months"]),
        "--selected-shrinkage",
        str(post_cfg["shrinkage"]),
        "--selected-min-rows",
        str(post_cfg["min_rows"]),
    ]
    logger.info("Running ver16 post-calibration: %s", " ".join(command))
    subprocess.run(command, check=True)
    return {
        "script_path": str(script_path),
        "output_grid": str(output_grid),
        "output_offsets": str(output_offsets),
        "service_model_output": str(service_model_path) if service_model_path else "",
    }


def run_pipeline(config_path: str | Path) -> dict:
    logger = setup_logger("ml_project.train")
    config_path = Path(config_path).resolve()
    config = load_yaml(config_path)
    pipeline_cfg = config.get("pipeline")
    if not pipeline_cfg:
        return train(config_path)
    if pipeline_cfg.get("type") != "train_then_ver16_post_calibration":
        raise ValueError(f"Unsupported pipeline type: {pipeline_cfg.get('type')}")

    base_config_path = _resolve_config_path(pipeline_cfg["base_training_config"], config_path.parent)
    logger.info("Running base training config: %s", base_config_path)
    train_result = train(base_config_path)
    post_result = run_ver16_post_calibration(config, config_path, train_result)

    base_config = load_yaml(base_config_path)
    output_dir = ensure_dir(base_config["paths"]["output_dir"])
    pipeline_result_path = output_dir / f"pipeline_{config['project']['name']}_{train_result['tag']}.json"
    result = {
        "pipeline_config": str(config_path),
        "base_training_config": str(base_config_path),
        "train_result": train_result,
        "post_calibration_result": post_result,
    }
    save_json(result, pipeline_result_path)
    logger.info("Saved pipeline result: %s", pipeline_result_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
