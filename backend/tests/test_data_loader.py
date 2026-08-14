from typing import Any

import pytest
import requests

from backend import data_loader
from backend.exceptions import (
    InvalidRequestError,
    UpstreamConnectionError,
    UpstreamResponseError,
    UpstreamTimeoutError,
)


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.content = b"{}"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError("upstream failed")

    def json(self) -> Any:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def test_fetch_all_paginates_without_mutating_params(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    responses = iter([
        FakeResponse([{"pages": 2}, [{"id": "A"}]]),
        FakeResponse([{"pages": 2}, [{"id": "B"}]]),
    ])

    def fake_get(*_: object, **kwargs: object) -> FakeResponse:
        calls.append(dict(kwargs["params"]))  # type: ignore[arg-type]
        return next(responses)

    monkeypatch.setattr(data_loader._session, "get", fake_get)
    params = {"date": "2000:2020"}
    assert data_loader._fetch_all("country", params) == [{"id": "A"}, {"id": "B"}]
    assert params == {"date": "2000:2020"}
    assert [call["page"] for call in calls] == [1, 2]


@pytest.mark.parametrize(
    ("error", "expected"),
    [(requests.Timeout("slow"), UpstreamTimeoutError),
     (requests.ConnectionError("offline"), UpstreamConnectionError)],
)
def test_fetch_all_classifies_network_failures(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected: type[Exception],
) -> None:
    def fail(*_: object, **__: object) -> FakeResponse:
        raise error

    monkeypatch.setattr(data_loader._session, "get", fail)
    with pytest.raises(expected):
        data_loader._fetch_all("country", {})


@pytest.mark.parametrize(
    "payload",
    [ValueError("not json"), {}, [], [{"pages": 1}], [{"pages": 1}, None]],
)
def test_fetch_all_rejects_malformed_responses(
    monkeypatch: pytest.MonkeyPatch,
    payload: Any,
) -> None:
    monkeypatch.setattr(data_loader._session, "get", lambda *_, **__: FakeResponse(payload))
    with pytest.raises(UpstreamResponseError):
        data_loader._fetch_all("country", {})


def test_fetch_all_rejects_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        data_loader._session,
        "get",
        lambda *_, **__: FakeResponse([{"pages": 1}, []], status_code=302),
    )
    with pytest.raises(UpstreamResponseError, match="redirect"):
        data_loader._fetch_all("country", {})


@pytest.mark.parametrize(
    ("country", "indicator"),
    [("../", "GDP"), ("bra", "GDP"), ("BRA", "../GDP"), ("BRA", "@GDP")],
)
def test_series_request_rejects_unsafe_codes(country: str, indicator: str) -> None:
    with pytest.raises(InvalidRequestError):
        data_loader.validate_series_request(country, indicator, 2000, 2020)


def test_indicator_data_rejects_duplicate_years(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = [
        {"country": {"value": "Brazil"}, "indicator": {"id": "GDP"}, "date": "2020", "value": 1},
        {"country": {"value": "Brazil"}, "indicator": {"id": "GDP"}, "date": "2020", "value": 2},
    ]
    monkeypatch.setattr(data_loader, "_fetch_all", lambda *_: raw)
    with pytest.raises(UpstreamResponseError, match="duplicate"):
        data_loader.get_indicator_data_df("BRA", "GDP", 2020, 2020)


def test_api_base_requires_credential_free_https() -> None:
    for value in ["http://api.worldbank.org/v2", "https://user:pass@example.com/v2", "file:///tmp"]:
        with pytest.raises(RuntimeError):
            data_loader._validate_api_base(value)
