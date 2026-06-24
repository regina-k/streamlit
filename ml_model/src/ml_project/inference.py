from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import pandas as pd

from .preprocessing import build_model_frame, load_raw_data
from .train import apply_calibration
from .utils import ensure_dir, load_yaml


def predict(config_path: str | Path, model_path: str | Path, data_path: str | None = None, output_path: str | None = None) -> Path:
    config = load_yaml(config_path)
    if data_path:
        config["paths"]["data_path"] = data_path
    raw = load_raw_data(config)
    model_df = build_model_frame(raw, config)

    with Path(model_path).open("rb") as f:
        artifact = pickle.load(f)
    model = artifact["model"]
    feature_columns = artifact["feature_columns"]
    calibration = artifact.get("calibration") or {
        "method": "valid_mean_residual",
        "global_offset": float(artifact.get("calibration_offset", 0.0) or 0.0),
    }

    preds = model.predict(model_df[feature_columns])
    preds = apply_calibration(model_df, preds, calibration)
    ids = config["data"].get("id_columns", [])
    out = model_df[ids].copy()
    out["prediction"] = preds

    if output_path is None:
        output_dir = ensure_dir(config["paths"]["prediction_dir"])
        output_path = output_dir / "inference_predictions.csv"
    else:
        output_path = Path(output_path)
        ensure_dir(output_path.parent)
    out.to_csv(output_path, index=False, encoding="utf-8-sig")
    return Path(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--data-path")
    parser.add_argument("--output-path")
    args = parser.parse_args()
    path = predict(args.config, args.model_path, args.data_path, args.output_path)
    print(f"Saved predictions: {path}")


if __name__ == "__main__":
    main()
