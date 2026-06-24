from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BaseRegressionModel(ABC):
    @abstractmethod
    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        categorical_columns: list[str] | None = None,
        X_valid: pd.DataFrame | None = None,
        y_valid: pd.Series | None = None,
        fit_params: dict[str, Any] | None = None,
    ) -> "BaseRegressionModel":
        raise NotImplementedError

    @abstractmethod
    def predict(self, X: pd.DataFrame):
        raise NotImplementedError


class LightGBMRegressionModel(BaseRegressionModel):
    def __init__(self, params: dict[str, Any] | None = None):
        try:
            from lightgbm import LGBMRegressor
        except ImportError as exc:
            raise ImportError("lightgbm is not installed. Install requirements.txt first.") from exc
        self.params = params or {}
        self.model = LGBMRegressor(**self.params)

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        categorical_columns: list[str] | None = None,
        X_valid: pd.DataFrame | None = None,
        y_valid: pd.Series | None = None,
        fit_params: dict[str, Any] | None = None,
    ) -> "LightGBMRegressionModel":
        fit_kwargs: dict[str, Any] = dict(fit_params or {})
        if categorical_columns:
            fit_kwargs["categorical_feature"] = categorical_columns
        if X_valid is not None and y_valid is not None:
            fit_kwargs["eval_set"] = [(X_valid, y_valid)]
        self.model.fit(X, y, **fit_kwargs)
        return self

    def predict(self, X: pd.DataFrame):
        return self.model.predict(X)


class RandomForestRegressionModel(BaseRegressionModel):
    def __init__(self, params: dict[str, Any] | None = None):
        from sklearn.ensemble import RandomForestRegressor
        self.params = params or {}
        self.model = RandomForestRegressor(**self.params)

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        categorical_columns: list[str] | None = None,
        X_valid: pd.DataFrame | None = None,
        y_valid: pd.Series | None = None,
        fit_params: dict[str, Any] | None = None,
    ) -> "RandomForestRegressionModel":
        X_fit = pd.get_dummies(X, columns=categorical_columns or [], dummy_na=True)
        self.columns_ = X_fit.columns.tolist()
        self.model.fit(X_fit, y)
        return self

    def predict(self, X: pd.DataFrame):
        X_pred = pd.get_dummies(X)
        X_pred = X_pred.reindex(columns=self.columns_, fill_value=0)
        return self.model.predict(X_pred)


def build_model(config: dict[str, Any]) -> BaseRegressionModel:
    model_type = config["model"]["type"].lower()
    params = config["model"].get("params", {})
    if model_type == "lightgbm":
        return LightGBMRegressionModel(params)
    if model_type == "random_forest":
        return RandomForestRegressionModel(params)
    raise ValueError(f"Unsupported model type: {model_type}")
