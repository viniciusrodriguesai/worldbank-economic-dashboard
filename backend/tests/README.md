# Backend tests

This directory contains deterministic tests for the public FastAPI behavior.

Read [backend/README.md](../README.md) for service internals and the [root README](../../README.md) for full-stack validation commands.

## Goals

The backend suite protects:

- Public HTTP status codes.
- Pydantic response contracts.
- Query parameter forwarding.
- Validation boundaries.
- Cache behavior visible to callers.
- Forecast response semantics.
- Safe translation of upstream failures.

Tests must be reliable without internet access and must never depend on the current contents of the World Bank API.

## Files

| File | Purpose |
| --- | --- |
| `test_api.py` | Route-level behavior through FastAPI `TestClient` |
| `__init__.py` | Marks the test directory as a package |

Global Pytest configuration lives in `../../pyproject.toml`.

## Test isolation

The `client` fixture seeds country and indicator cache records and assigns a fresh monotonic timestamp. This prevents metadata routes from making live network requests.

Route-specific tests use `monkeypatch` to replace:

- `get_indicator_data_df`
- `forecast_indicator`
- `_refresh_caches`
- Cache timestamps or records

Each replacement returns a small deterministic DataFrame or raises a controlled error.

Do not patch `requests` when a route-level loader replacement communicates the intent more clearly. Lower-level loader tests may patch the session directly.

## Covered behavior

| Scenario | Expected behavior |
| --- | --- |
| Cached countries | 200 with ISO2 metadata |
| Cached indicators | 200 with typed ID and name |
| Selected historical period | Exact `start` and `end` forwarded to the loader |
| Reversed historical period | 400 before the loader runs |
| Empty historical series | 404 |
| Invalid ISO3 length | 422 from FastAPI validation |
| Successful forecast | Future `IndicatorPoint` records |
| Metadata refresh failure | 503 with a stable public message |

## Running tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run this directory only:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

Run one case:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_api.py -k forecast
```

Show extra detail:

```powershell
.\.venv\Scripts\python.exe -m pytest -vv
```

## Coverage

The root configuration enables terminal missing-line coverage for the `backend` package.

Coverage is a diagnostic, not a substitute for meaningful assertions. Prioritize:

1. Public contract branches.
2. Error translation.
3. Data normalization edge cases.
4. Forecast preconditions.
5. Cache expiration and concurrency behavior.

When adding a module, make sure it is imported through a test path so coverage includes it.

## Writing new tests

Use the Arrange-Act-Assert pattern:

1. Arrange deterministic cache, DataFrame, or exception state.
2. Act through `TestClient` when validating a public route.
3. Assert the HTTP status.
4. Assert the complete relevant response contract.
5. Assert mocked functions received the expected typed inputs.

Recommended naming:

```text
test_<unit>_<expected_behavior>_<condition>
```

Example:

```text
test_data_returns_404_for_empty_series
```

## Rules

- Never call the live World Bank API.
- Never depend on request ordering across tests.
- Never share mutable DataFrames between tests.
- Use `pytest.MonkeyPatch` for temporary global state.
- Restore cache behavior automatically through fixtures.
- Assert user-facing details for controlled errors.
- Avoid asserting internal log formatting unless logging itself is the feature.
- Add a regression test before or with every bug fix.
- Keep test data small enough to understand at a glance.

## Future coverage

Useful additions include:

- Paginated `_fetch_all` behavior with a mocked session.
- Required-field validation for malformed upstream JSON.
- Numeric conversion and missing-observation filtering.
- ARIMA minimum-history enforcement.
- Forecast horizon and custom order behavior.
- Metadata TTL expiration.
- Concurrent cache refresh behavior.
- Lifespan preload failure and recovery.
