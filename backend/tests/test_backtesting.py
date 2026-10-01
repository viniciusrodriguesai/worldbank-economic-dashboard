from types import SimpleNamespace

import pandas as pd
import pytest

from backend.exceptions import ForecastUnavailableError, InvalidRequestError
from backend.services import backtesting


def series(values):
    return pd.DataFrame({"country": "Brazil", "indicator": "GDP", "year": range(2000, 2000 + len(values)), "value": values})


def test_outer_targets_never_reach_model_selection(monkeypatch):
    seen = []

    def spy(frame, country, indicator, horizon):
        seen.append(frame.copy())
        year = int(frame.year.iloc[-1])
        return SimpleNamespace(
            evaluation=SimpleNamespace(selected_model="naive", validation_points=2),
            warnings=[], forecast=[SimpleNamespace(year=year + h, value=float(frame.value.iloc[-1])) for h in range(1, horizon + 1)],
        )

    monkeypatch.setattr(backtesting, "evaluate_forecast", spy)
    frame = series(list(range(19)) + [999999])
    report = backtesting.rolling_origin_evaluation(frame, "BRA", "GDP", max_origins=3)
    assert [len(f) for f in seen] == [15, 16, 17]
    assert all(999999 not in f.value.values for f in seen)
    assert all(r["target_year"] > r["origin_year"] for r in report["predictions"])
    assert report["aggregate_metrics"]["selected"] == report["aggregate_metrics"]["naive"]
    assert len(report["predictions"]) == 9


def test_constant_series_has_zero_error():
    report = backtesting.rolling_origin_evaluation(series([7] * 20), "BRA", "GDP")
    assert report["aggregate_metrics"]["selected"]["mae"] == 0
    assert all(f["selected_model"] == "naive" for f in report["folds"])


def test_bounds_and_insufficient_history():
    with pytest.raises(InvalidRequestError):
        backtesting.rolling_origin_evaluation(series([7] * 20), "BRA", "GDP", horizon=0)
    with pytest.raises(ForecastUnavailableError):
        backtesting.rolling_origin_evaluation(series([7] * 12), "BRA", "GDP")
    frame = series([7] * 20)
    frame.loc[0, "country"] = "Canada"
    with pytest.raises(InvalidRequestError):
        backtesting.rolling_origin_evaluation(frame, "BRA", "GDP")
