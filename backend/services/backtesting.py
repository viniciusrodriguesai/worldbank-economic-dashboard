"""Evaluate the deployed selection procedure on expanding historical prefixes."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.exceptions import ForecastUnavailableError, InvalidRequestError
from backend.services.forecasting import (
    _drift,
    _metrics,
    _naive,
    _prepare_history,
    evaluate_forecast,
)


def rolling_origin_evaluation(
    frame: pd.DataFrame,
    country_code: str,
    indicator_code: str,
    *,
    horizon: int = 3,
    minimum_train: int = 12,
    max_origins: int = 8,
) -> dict:
    """Nested temporal evaluation: selection sees only each origin's prefix.

    No outer error is used to choose candidates. Any failed origin aborts the
    evaluation instead of silently reporting only successful fits.
    """
    if not 1 <= horizon <= 10 or not 1 <= max_origins <= 20 or minimum_train < 10:
        raise InvalidRequestError("Invalid rolling-origin evaluation bounds.")
    if not {"country", "indicator", "year", "value"}.issubset(frame.columns):
        raise InvalidRequestError("Missing country, indicator, year or value columns.")
    if frame["country"].nunique() != 1 or frame["indicator"].nunique() != 1:
        raise InvalidRequestError("Evaluate exactly one country/indicator series.")
    _, tail, missing_years = _prepare_history(frame)
    origins = list(range(minimum_train, len(tail) - horizon + 1))[-max_origins:]
    if not origins:
        raise ForecastUnavailableError("Not enough history for an outer evaluation window.")
    rows = []
    folds = []
    for origin in origins:
        train = tail.iloc[:origin].copy()
        actual = tail.iloc[origin:origin + horizon]
        response = evaluate_forecast(train, country_code, indicator_code, horizon)
        training_values = train["value"].to_numpy(dtype=float)
        naive = _naive(training_values, horizon)
        drift = _drift(training_values, horizon)
        folds.append({
            "origin_year": int(train["year"].iloc[-1]),
            "training_points": len(train),
            "selected_model": response.evaluation.selected_model,
            "inner_validation_points": response.evaluation.validation_points,
            "warnings": response.warnings,
        })
        for step, point in enumerate(response.forecast):
            target_year = int(actual["year"].iloc[step])
            if point.year != target_year:
                raise ForecastUnavailableError("Forecast years do not match the outer window.")
            rows.append({
                "origin_year": folds[-1]["origin_year"], "horizon": step + 1,
                "target_year": target_year, "actual": float(actual["value"].iloc[step]),
                "selected": point.value, "naive": float(naive[step]),
                "drift": float(drift[step]),
            })

    def summarize(selected_rows: list[dict]) -> dict:
        actual = np.array([row["actual"] for row in selected_rows])
        return {name: _metrics(actual, np.array([row[name] for row in selected_rows])).model_dump()
                for name in ("selected", "naive", "drift")}

    return {
        "protocol": "nested-expanding-origin-v1", "horizon": horizon,
        "minimum_train": minimum_train, "max_origins": max_origins,
        "origin_count": len(origins), "missing_years": missing_years,
        "modeled_start_year": int(tail["year"].iloc[0]),
        "aggregate_metrics": summarize(rows),
        "metrics_by_horizon": {str(h): summarize([r for r in rows if r["horizon"] == h])
                               for h in range(1, horizon + 1)},
        "folds": folds, "predictions": rows,
    }
