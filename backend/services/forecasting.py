"""Bounded annual forecasting with temporal validation and honest baselines."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from backend.exceptions import ForecastUnavailableError, InvalidRequestError
from backend.models import (
    ForecastMetrics,
    ForecastPoint,
    ForecastResponse,
    IndicatorPoint,
    ModelEvaluation,
)

MIN_CONTIGUOUS_OBSERVATIONS = 10
ARIMA_CANDIDATES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 0),
    (1, 1, 0),
    (0, 1, 1),
    (1, 1, 1),
    (1, 0, 0),
)


@dataclass(frozen=True)
class CandidateResult:
    name: str
    order: tuple[int, int, int] | None
    metrics: ForecastMetrics


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> ForecastMetrics:
    errors = actual - predicted
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    nonzero_actual = np.abs(actual) > np.finfo(float).eps
    mape = None
    if bool(np.all(nonzero_actual)):
        mape = float(np.mean(np.abs(errors / actual)) * 100)
    denominator = np.abs(actual) + np.abs(predicted)
    valid_smape = denominator > np.finfo(float).eps
    smape = 0.0 if not bool(np.any(valid_smape)) else float(
        np.mean(200 * np.abs(errors[valid_smape]) / denominator[valid_smape])
    )
    return ForecastMetrics(mae=mae, rmse=rmse, mape=mape, smape=smape)


def _naive(values: np.ndarray, steps: int) -> np.ndarray:
    return np.repeat(values[-1], steps).astype(float)


def _drift(values: np.ndarray, steps: int) -> np.ndarray:
    if len(values) < 2:
        return _naive(values, steps)
    slope = (values[-1] - values[0]) / (len(values) - 1)
    return values[-1] + slope * np.arange(1, steps + 1)


def _fit_arima(
    values: np.ndarray,
    order: tuple[int, int, int],
    steps: int,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = ARIMA(
            values,
            order=order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit()
    convergence = getattr(fitted, "mle_retvals", {}).get("converged", True)
    if convergence is False:
        raise ForecastUnavailableError("ARIMA candidate did not converge.")
    result = fitted.get_forecast(steps=steps)
    predicted = np.asarray(result.predicted_mean, dtype=float)
    interval = np.asarray(result.conf_int(alpha=0.05), dtype=float)
    if predicted.shape != (steps,) or interval.shape != (steps, 2):
        raise ForecastUnavailableError("ARIMA returned an invalid forecast shape.")
    if not bool(np.all(np.isfinite(predicted))) or not bool(np.all(np.isfinite(interval))):
        raise ForecastUnavailableError("ARIMA returned non-finite forecast values.")
    return predicted, interval[:, 0], interval[:, 1]


def _prepare_history(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[int]]:
    required = {"country", "indicator", "year", "value"}
    if not required.issubset(frame.columns):
        raise ForecastUnavailableError("Historical data is missing required fields.")
    clean = frame.loc[:, ["country", "indicator", "year", "value"]].copy()
    clean["year"] = pd.to_numeric(clean["year"], errors="coerce")
    clean["value"] = pd.to_numeric(clean["value"], errors="coerce")
    clean = clean.dropna(subset=["year", "value"])
    clean = clean[np.isfinite(clean["value"])]
    clean["year"] = clean["year"].astype(int)
    clean = clean.sort_values("year").reset_index(drop=True)
    if clean.empty:
        raise ForecastUnavailableError("No finite annual observations are available.")
    if clean["year"].duplicated().any():
        raise ForecastUnavailableError("Duplicate annual observations cannot be modeled.")
    first_year, last_year = int(clean["year"].iloc[0]), int(clean["year"].iloc[-1])
    observed = set(clean["year"].tolist())
    missing = [year for year in range(first_year, last_year + 1) if year not in observed]
    tail_start = (max(missing) + 1) if missing else first_year
    contiguous_tail = clean[clean["year"] >= tail_start].reset_index(drop=True)
    if len(contiguous_tail) < MIN_CONTIGUOUS_OBSERVATIONS:
        raise ForecastUnavailableError(
            "At least 10 consecutive annual observations ending at the latest year are required."
        )
    return clean, contiguous_tail, missing


def _best_baseline(train: np.ndarray, actual: np.ndarray) -> CandidateResult:
    candidates = []
    for name, predicted in (("naive", _naive(train, len(actual))), ("drift", _drift(train, len(actual)))):
        candidates.append(CandidateResult(name=name, order=None, metrics=_metrics(actual, predicted)))
    return min(candidates, key=lambda result: (result.metrics.mae, result.metrics.rmse))


def _baseline_forecast(name: str, values: np.ndarray, steps: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    predicted = _naive(values, steps) if name == "naive" else _drift(values, steps)
    differences = np.diff(values)
    residual_scale = float(np.std(differences, ddof=1)) if len(differences) > 1 else 0.0
    widths = 1.96 * residual_scale * np.sqrt(np.arange(1, steps + 1))
    return predicted, predicted - widths, predicted + widths


def evaluate_forecast(
    frame: pd.DataFrame,
    country_code: str,
    indicator_code: str,
    years_ahead: int,
) -> ForecastResponse:
    """Evaluate bounded candidates and forecast from a contiguous annual tail."""
    if not 1 <= years_ahead <= 10:
        raise InvalidRequestError("Forecast horizon must be between 1 and 10 years.")
    clean, tail, missing_years = _prepare_history(frame)
    values = tail["value"].to_numpy(dtype=float)
    validation_points = max(2, min(5, len(values) // 4))
    train, actual = values[:-validation_points], values[-validation_points:]
    baseline = _best_baseline(train, actual)
    arima_results: list[CandidateResult] = []
    if not bool(np.allclose(values, values[0])):
        for order in ARIMA_CANDIDATES:
            try:
                predicted, _, _ = _fit_arima(train, order, validation_points)
            except (ForecastUnavailableError, ValueError, ArithmeticError, np.linalg.LinAlgError):
                continue
            arima_results.append(
                CandidateResult(name=f"ARIMA{order}", order=order, metrics=_metrics(actual, predicted))
            )

    best_arima = min(
        arima_results,
        key=lambda result: (result.metrics.mae, result.metrics.rmse, result.name),
        default=None,
    )
    selected = baseline
    beats_baseline = False
    if best_arima is not None and best_arima.metrics.mae < baseline.metrics.mae:
        selected = best_arima
        beats_baseline = True

    warnings_out: list[str] = []
    if missing_years:
        warnings_out.append(
            f"Missing annual observations were not interpolated: {missing_years}. "
            f"Only the contiguous tail from {int(tail['year'].iloc[0])} was modeled."
        )
    if bool(np.allclose(values, values[0])):
        warnings_out.append("The series is constant; the naive baseline was selected.")
    elif not beats_baseline:
        warnings_out.append("No evaluated ARIMA candidate outperformed the temporal baseline.")

    if selected.order is None:
        predicted, lower, upper = _baseline_forecast(selected.name, values, years_ahead)
    else:
        try:
            predicted, lower_raw, upper_raw = _fit_arima(values, selected.order, years_ahead)
            lower, upper = lower_raw, upper_raw
        except (ForecastUnavailableError, ValueError, ArithmeticError, np.linalg.LinAlgError):
            warnings_out.append("The selected ARIMA failed on the full history; baseline used instead.")
            selected = baseline
            beats_baseline = False
            predicted, lower, upper = _baseline_forecast(selected.name, values, years_ahead)

    last_year = int(tail["year"].iloc[-1])
    history = [
        IndicatorPoint(
            country=str(row.country),
            indicator=str(row.indicator),
            year=int(row.year),
            value=float(row.value),
        )
        for row in clean.itertuples(index=False)
    ]
    forecast = [
        ForecastPoint(
            country=country_code,
            indicator=indicator_code,
            year=last_year + step,
            value=float(predicted[step - 1]),
            lower_bound=float(min(lower[step - 1], upper[step - 1])),
            upper_bound=float(max(lower[step - 1], upper[step - 1])),
        )
        for step in range(1, years_ahead + 1)
    ]
    return ForecastResponse(
        history=history,
        forecast=forecast,
        evaluation=ModelEvaluation(
            selected_model=selected.name,
            selected_order=selected.order,
            validation_points=validation_points,
            model_metrics=selected.metrics,
            baseline_model=baseline.name,
            baseline_metrics=baseline.metrics,
            beats_baseline=beats_baseline,
        ),
        horizon=years_ahead,
        missing_years=missing_years,
        warnings=warnings_out,
    )
