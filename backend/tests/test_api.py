import time

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend import app as app_module


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


def test_data_validates_country_code(client: TestClient) -> None:
    response = client.get(
        "/data",
        params={"country": "BR", "indicator": "GDP"},
    )

    assert response.status_code == 422


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
