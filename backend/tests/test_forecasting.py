import numpy as np
import pandas as pd
import pytest

from backend.exceptions import ForecastUnavailableError
from backend.services import forecasting


def series(years: list[int], values: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"country": "Brazil", "indicator": "GDP", "year": years, "value": values})


def test_irregular_short_tail_is_rejected_without_compressing_time() -> None:
    frame = series([2018, 2019, 2021, 2024], [1, 2, 3, 4])
    with pytest.raises(ForecastUnavailableError, match="consecutive annual"):
        forecasting.evaluate_forecast(frame, "BRA", "GDP", 3)


def test_missing_years_are_disclosed_and_not_interpolated() -> None:
    years = [2000, 2001, *range(2003, 2015)]
    result = forecasting.evaluate_forecast(series(years, list(range(len(years)))), "BRA", "GDP", 3)
    assert result.missing_years == [2002]
    assert "not interpolated" in result.warnings[0]
    assert [point.year for point in result.forecast] == [2015, 2016, 2017]


def test_constant_series_selects_naive_with_finite_zero_width_interval() -> None:
    result = forecasting.evaluate_forecast(
        series(list(range(2000, 2015)), [7.0] * 15), "BRA", "GDP", 2
    )
    assert result.evaluation.selected_model == "naive"
    assert result.evaluation.model_metrics.mae == 0
    assert all(point.lower_bound == point.value == point.upper_bound for point in result.forecast)


def test_zero_series_does_not_report_misleading_mape() -> None:
    result = forecasting.evaluate_forecast(
        series(list(range(2000, 2015)), [0.0] * 15), "BRA", "GDP", 1
    )
    assert result.evaluation.model_metrics.mape is None
    assert result.evaluation.model_metrics.smape == 0


def test_candidate_failure_falls_back_to_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_: object, **__: object) -> tuple[np.ndarray, None, None]:
        raise ValueError("fit failed")

    monkeypatch.setattr(forecasting, "_fit_arima", fail)
    values = [float(year) for year in range(15)]
    result = forecasting.evaluate_forecast(
        series(list(range(2000, 2015)), values), "BRA", "GDP", 3
    )
    assert result.evaluation.selected_model in {"naive", "drift"}
    assert result.evaluation.beats_baseline is False
    assert len(result.forecast) == 3
    assert all(np.isfinite(point.lower_bound) for point in result.forecast)


def test_duplicate_years_and_short_series_are_rejected() -> None:
    with pytest.raises(ForecastUnavailableError, match="Duplicate"):
        forecasting.evaluate_forecast(series([2000] * 10, list(range(10))), "BRA", "GDP", 1)
    with pytest.raises(ForecastUnavailableError, match="consecutive"):
        forecasting.evaluate_forecast(
            series(list(range(2000, 2009)), list(range(9))), "BRA", "GDP", 1
        )
