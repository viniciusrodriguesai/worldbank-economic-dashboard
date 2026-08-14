import time

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend import app as app_module
from backend.exceptions import UpstreamConnectionError, UpstreamTimeoutError


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        app_module,
        "_countries_cache",
        [
            {
                "id": "BRA",
                "iso2Code": "BR",
                "name": "Brazil",
                "region": "Latin America & Caribbean",
                "capitalCity": "Brasilia",
            }
        ],
    )
    monkeypatch.setattr(
        app_module,
        "_indicators_cache",
        [{"id": "NY.GDP.MKTP.CD", "name": "GDP (current US$)"}],
    )
    monkeypatch.setattr(app_module, "_cache_timestamp", time.monotonic())
    return TestClient(app_module.app)


def test_lists_cached_countries_and_indicators(client: TestClient) -> None:
    countries_response = client.get("/countries")
    indicators_response = client.get("/indicators")

    assert countries_response.status_code == 200
    assert countries_response.json()[0]["iso2Code"] == "BR"
    assert indicators_response.status_code == 200
    assert indicators_response.json() == [
        {"id": "NY.GDP.MKTP.CD", "name": "GDP (current US$)"}
    ]


def test_indicator_search_is_filtered_and_bounded(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_module,
        "_indicators_cache",
        [
            {"id": "SP.POP.TOTL", "name": "Population, total"},
            {"id": "NY.GDP.PCAP.CD", "name": "GDP per capita"},
            {"id": "NY.GDP.MKTP.CD", "name": "GDP"},
        ],
    )
    response = client.get("/indicators", params={"search": "gdp", "limit": 1, "offset": 1})
    assert response.status_code == 200
    assert response.json() == [{"id": "NY.GDP.MKTP.CD", "name": "GDP"}]


def test_data_forwards_selected_period(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict[str, object] = {}

    def fake_data(country: str, indicator: str, start: int, end: int) -> pd.DataFrame:
        received.update(
            country=country,
            indicator=indicator,
            start=start,
            end=end,
        )
        return pd.DataFrame(
            [
                {
                    "country": "Brazil",
                    "indicator": indicator,
                    "year": 2020,
                    "value": 1.48e12,
                }
            ]
        )

    monkeypatch.setattr(app_module, "get_indicator_data_df", fake_data)
    response = client.get(
        "/data",
        params={
            "country": "BRA",
            "indicator": "NY.GDP.MKTP.CD",
            "start": 2010,
            "end": 2020,
        },
    )

    assert response.status_code == 200
    assert received == {
        "country": "BRA",
        "indicator": "NY.GDP.MKTP.CD",
        "start": 2010,
        "end": 2020,
    }
    assert response.json()[0]["year"] == 2020


def test_data_rejects_reversed_period(client: TestClient) -> None:
    response = client.get(
        "/data",
        params={
            "country": "BRA",
            "indicator": "NY.GDP.MKTP.CD",
            "start": 2021,
            "end": 2020,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Start year cannot be greater than end year."


def test_data_returns_404_for_empty_series(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_module,
        "get_indicator_data_df",
        lambda *_: pd.DataFrame(),
    )

    response = client.get(
        "/data",
        params={
            "country": "BRA",
            "indicator": "NY.GDP.MKTP.CD",
            "start": 2010,
            "end": 2020,
        },
    )

    assert response.status_code == 404


def test_compare_data_limits_and_labels_countries_by_code(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_module,
        "_countries_cache",
        [
            {"id": "BRA", "iso2Code": "BR", "name": "Brazil", "region": "LAC", "capitalCity": "Brasilia"},
            {"id": "USA", "iso2Code": "US", "name": "United States", "region": "North America", "capitalCity": "Washington"},
        ],
    )
    monkeypatch.setattr(
        app_module,
        "get_indicator_data_df",
        lambda country, indicator, *_: pd.DataFrame(
            [{"country": "ignored", "indicator": indicator, "year": 2020, "value": 1.0}]
        ),
    )
    response = client.get(
        "/data/compare",
        params=[
            ("countries", "BRA"),
            ("countries", "USA"),
            ("indicator", "NY.GDP.MKTP.CD"),
            ("start", "2020"),
            ("end", "2020"),
        ],
    )
    assert response.status_code == 200
    assert [point["country"] for point in response.json()] == ["BRA", "USA"]


def test_compare_data_rejects_duplicate_countries(client: TestClient) -> None:
    response = client.get(
        "/data/compare",
        params=[
            ("countries", "BRA"),
            ("countries", "BRA"),
            ("indicator", "NY.GDP.MKTP.CD"),
        ],
    )
    assert response.status_code == 422


def test_data_validates_country_code(client: TestClient) -> None:
    response = client.get(
        "/data",
        params={"country": "BR", "indicator": "GDP"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("indicator", ["../secret", "GDP?redirect=x", "a" * 65])
def test_data_rejects_unsafe_indicator_codes(client: TestClient, indicator: str) -> None:
    response = client.get("/data", params={"country": "BRA", "indicator": indicator})
    assert response.status_code == 422


def test_data_rejects_unknown_metadata_code(client: TestClient) -> None:
    response = client.get("/data", params={"country": "USA", "indicator": "NY.GDP.MKTP.CD"})
    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown country code."


@pytest.mark.parametrize(
    ("failure", "status_code"),
    [(UpstreamTimeoutError("timeout"), 504), (UpstreamConnectionError("offline"), 503)],
)
def test_data_maps_upstream_availability_failures(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    status_code: int,
) -> None:
    def fail(*_: object) -> pd.DataFrame:
        raise failure

    monkeypatch.setattr(app_module, "get_indicator_data_df", fail)
    response = client.get(
        "/data",
        params={"country": "BRA", "indicator": "NY.GDP.MKTP.CD", "end": 2020},
    )
    assert response.status_code == status_code
    assert "timeout" not in response.text
    assert "offline" not in response.text


def test_forecast_returns_future_points(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_forecast(*_: object) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "country": "BRA",
                    "indicator": "NY.GDP.MKTP.CD",
                    "year": 2023,
                    "value": 2.0e12,
                }
            ]
        )

    monkeypatch.setattr(app_module, "forecast_indicator", fake_forecast)
    response = client.get(
        "/forecast",
        params={
            "country": "BRA",
            "indicator": "NY.GDP.MKTP.CD",
            "start": 2000,
            "end": 2022,
            "years_ahead": 1,
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["year"] == 2023


def test_forecast_rejects_excessive_horizon(client: TestClient) -> None:
    response = client.get(
        "/forecast",
        params={"country": "BRA", "indicator": "NY.GDP.MKTP.CD", "years_ahead": 11},
    )
    assert response.status_code == 422


def test_forecast_returns_429_when_capacity_is_busy(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BusySlots:
        def acquire(self, *, blocking: bool) -> bool:
            assert blocking is False
            return False

    monkeypatch.setattr(app_module, "_forecast_slots", BusySlots())
    response = client.get(
        "/forecast",
        params={"country": "BRA", "indicator": "NY.GDP.MKTP.CD", "end": 2020},
    )
    assert response.status_code == 429


def test_evaluated_forecast_returns_metrics_and_intervals(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_module,
        "get_indicator_data_df",
        lambda *_: pd.DataFrame(
            [{"country": "Brazil", "indicator": "NY.GDP.MKTP.CD", "year": year, "value": year} for year in range(2010, 2021)]
        ),
    )

    def fake_evaluate(*_: object) -> dict[str, object]:
        return {
            "history": [{"country": "Brazil", "indicator": "NY.GDP.MKTP.CD", "year": 2020, "value": 1.0}],
            "forecast": [{"country": "BRA", "indicator": "NY.GDP.MKTP.CD", "year": 2021, "value": 2.0, "lower_bound": 1.5, "upper_bound": 2.5}],
            "evaluation": {
                "selected_model": "drift",
                "selected_order": None,
                "validation_points": 2,
                "model_metrics": {"mae": 1, "rmse": 1, "mape": 2, "smape": 2},
                "baseline_model": "drift",
                "baseline_metrics": {"mae": 1, "rmse": 1, "mape": 2, "smape": 2},
                "beats_baseline": False,
            },
            "horizon": 1,
            "missing_years": [],
            "warnings": ["Baseline selected."],
        }

    monkeypatch.setattr(app_module, "evaluate_forecast", fake_evaluate)
    response = client.get(
        "/forecast/evaluate",
        params={"country": "BRA", "indicator": "NY.GDP.MKTP.CD", "end": 2020, "years_ahead": 1},
    )
    assert response.status_code == 200
    assert response.json()["forecast"][0]["lower_bound"] == 1.5
    assert response.json()["evaluation"]["selected_model"] == "drift"


def test_unexpected_data_error_does_not_leak_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_: object) -> pd.DataFrame:
        raise RuntimeError("internal=https://private.invalid/token")

    monkeypatch.setattr(app_module, "get_indicator_data_df", fail)
    response = client.get(
        "/data",
        params={"country": "BRA", "indicator": "NY.GDP.MKTP.CD", "end": 2020},
    )
    assert response.status_code == 500
    assert "private.invalid" not in response.text


def test_cors_rejects_wildcard_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="exact HTTP"):
        app_module._cors_origins()


def test_metadata_failure_returns_503(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module, "_cache_timestamp", None)

    def fail_refresh() -> None:
        raise ValueError("upstream unavailable")

    monkeypatch.setattr(app_module, "_refresh_caches", fail_refresh)
    response = client.get("/countries")

    assert response.status_code == 503
    assert response.json()["detail"] == "Country data is temporarily unavailable."


def test_metadata_cache_refreshes_once_and_then_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module, "_countries_cache", None)
    monkeypatch.setattr(app_module, "_indicators_cache", None)
    monkeypatch.setattr(app_module, "_cache_timestamp", None)
    calls = {"countries": 0, "indicators": 0}

    def countries_frame() -> pd.DataFrame:
        calls["countries"] += 1
        return pd.DataFrame([{
            "id": "BRA", "iso2Code": "BR", "name": "Brazil",
            "region": "Latin America", "capitalCity": "Brasilia",
        }])

    def indicators_frame() -> pd.DataFrame:
        calls["indicators"] += 1
        return pd.DataFrame([{"id": "GDP", "name": "GDP"}])

    monkeypatch.setattr(app_module, "get_countries_df", countries_frame)
    monkeypatch.setattr(app_module, "get_indicators_df", indicators_frame)
    app_module._ensure_cache_valid()
    app_module._ensure_cache_valid()
    assert calls == {"countries": 1, "indicators": 1}
    assert app_module._countries_cache[0]["id"] == "BRA"
