# World Bank Economic Dashboard

A security-conscious economic analytics application for exploring live World Bank
indicators, comparing up to five countries, exporting safe CSV data, and evaluating
bounded annual forecasts without presenting estimates as facts.

[![Continuous Integration](https://github.com/viniciusrodriguesai/worldbank-economic-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/viniciusrodriguesai/worldbank-economic-dashboard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Deployment status: **deploy-ready, not publicly deployed**. No live-demo URL is claimed.

## Why it is useful

- Search bounded World Bank indicator metadata.
- Compare one indicator across one to five countries over a shared annual range.
- Inspect observations, latest values, changes, maps, and responsive charts.
- Evaluate naive/drift baselines against a small server-owned ARIMA candidate set.
- See temporal validation metrics, missing-year warnings, and uncertainty bands.
- Download deterministic UTF-8 CSV protected against spreadsheet formula injection.
- Distinguish invalid input, missing data, upstream outages, timeouts, and model failures.

## Architecture

~~~mermaid
flowchart LR
    Browser[Browser]
    UI[React + TypeScript]
    Edge[nginx / TLS edge]
    API[FastAPI]
    Cache[Metadata cache]
    Forecast[Forecast service]
    WB[World Bank API]
    OSM[OpenStreetMap]
    CSV[Safe CSV]

    Browser --> Edge --> UI
    UI --> Edge --> API
    UI --> CSV
    Browser --> OSM
    API --> Cache --> WB
    API --> WB
    API --> Forecast
~~~

FastAPI owns HTTP validation and error semantics. World Bank retrieval and normalization
stay server-side. Forecast evaluation is isolated in a bounded service. The frontend
uses typed API clients and cancels stale requests. Production nginx serves static assets,
applies browser security headers, and rate-limits the internal API proxy.

See [architecture details](docs/ARCHITECTURE.md) and the
[threat model](docs/THREAT_MODEL.md).

## Forecasting methodology

The evaluated forecast endpoint:

1. removes invalid and non-finite values and rejects duplicate years;
2. detects missing calendar years without interpolating them;
3. models only a contiguous annual tail ending at the latest observation, requiring
   at least 10 consecutive values;
4. reserves the last 2 to 5 points as a chronological holdout;
5. evaluates naive and drift baselines plus five bounded ARIMA orders;
6. selects by holdout MAE, using RMSE as a tie-breaker;
7. selects ARIMA only when it strictly beats the best baseline; and
8. returns MAE, RMSE, safe MAPE, sMAPE, warnings, and future bounds.

Forecasts are estimates, not economic advice or observed facts. Baseline bands are
approximate; ARIMA intervals use the fitted model's 95% interval.
See [forecasting methodology](docs/FORECASTING.md).

## Security and reliability

- Strict country, indicator, period, pagination, and forecast bounds.
- HTTPS-only credential-free World Bank base with cross-host redirects blocked.
- Explicit HTTP error mapping without internal detail leakage.
- Two forecast slots plus nginx throttling and container resource limits.
- Thread-safe cache with single-flight refresh, bounded stale fallback, and backoff.
- Exact CORS origins, GET-only policy, no credentials, and narrow headers.
- Typed CSV formula neutralization that preserves negative numbers.
- Read-only non-root containers, dropped capabilities, pinned images, and health checks.
- Read-only CI token, SHA-pinned actions, clean installs, scans, and Dependabot.

Read the [security audit](docs/SECURITY_AUDIT.md) and
[vulnerability reporting policy](SECURITY.md).

## Technology

| Layer | Stack |
| --- | --- |
| API and contracts | Python 3.11, FastAPI, Pydantic |
| Data and forecasting | Pandas, NumPy, Statsmodels ARIMA |
| Frontend | React 19, strict TypeScript, Vite |
| Visualization | Plotly, Leaflet, OpenStreetMap |
| Quality | Pytest, Ruff, Bandit, pip-audit, Vitest, Oxlint |
| Delivery | GitHub Actions, Docker Compose, nginx |

## Quick start

Backend:

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
~~~

Frontend in another terminal:

~~~powershell
Set-Location frontend
npm ci
npm run dev
~~~

Open http://localhost:5173. Vite proxies /api to the local backend.
On macOS/Linux use equivalent virtual-environment activation and path syntax.

Production-equivalent containers:

~~~powershell
Copy-Item .env.example .env
docker compose config
docker compose up --build
~~~

Open http://localhost:8080. FastAPI is not published to the host. Public deployment
requires a TLS edge, DNS, credentials, monitoring, and image scanning; see
[deployment](docs/DEPLOYMENT.md).

## API

| Endpoint | Purpose | Important bounds |
| --- | --- | --- |
| GET /health | Process liveness | No upstream call |
| GET /countries | Country metadata | Cached and validated |
| GET /indicators | Indicator discovery | Search and pagination bounds |
| GET /data | Single-country history | Known codes, maximum 120-year span |
| GET /data/compare | Multi-country history | 1-5 unique countries |
| GET /forecast | Backward-compatible legacy forecast | Horizon 1-10 |
| GET /forecast/evaluate | Forecast plus evaluation | Bounded candidates and concurrency |

OpenAPI documentation is available at /docs while the backend runs.

## Testing

~~~powershell
# Backend
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\bandit.exe -q -r backend -x backend\tests
.\.venv\Scripts\python.exe -m pip_audit -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pytest

# Frontend
Set-Location frontend
npm audit --audit-level=high
npm run lint
npm run test:coverage
npm run build
~~~

Pytest enforces 85% backend coverage. Vitest enforces 78% statements, 65% branches,
80% functions, and 80% lines. CI executes both layers independently.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Forecasting methodology](docs/FORECASTING.md)
- [Security audit](docs/SECURITY_AUDIT.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Backend guide](backend/README.md)
- [Frontend guide](frontend/README.md)
- [CI guide](.github/workflows/README.md)

## License

MIT. World Bank data and OpenStreetMap tiles remain subject to their respective terms
and attribution requirements.
