# World Bank Economic Dashboard

A full-stack dashboard for exploring live World Bank economic indicators, viewing country locations, exporting historical data, and generating short-term ARIMA forecasts.

## What is implemented

- Searchable country and indicator selectors.
- Historical time-series charts with a configurable year range.
- A country map that uses World Bank ISO2 metadata.
- Five-year ARIMA forecasts fitted to the selected period.
- CSV export with Excel-compatible UTF-8 encoding.
- Request cancellation, timeout handling, and readable API errors.
- Typed API responses with Pydantic and a strict TypeScript frontend.
- Automated backend and frontend tests.

The application currently analyzes one country and one indicator at a time. It does not implement Prophet, regional comparison views, or local database persistence.

## Technology

### Backend

- Python 3.11
- FastAPI and Pydantic
- Pandas
- Statsmodels ARIMA
- Requests
- Pytest

### Frontend

- TypeScript
- React 19
- Vite 8
- Plotly basic distribution
- React Leaflet
- Axios
- Vitest and Testing Library

## Project structure

```text
worldbank-economic-dashboard/
|-- backend/
|   |-- app.py                  # FastAPI routes, CORS, and metadata cache
|   |-- data_loader.py          # World Bank client and ARIMA forecasting
|   |-- models.py               # Pydantic response contracts
|   |-- requirements.txt        # Runtime dependencies
|   |-- requirements-dev.txt    # Runtime and test dependencies
|   `-- tests/                  # Backend API tests
|-- frontend/
|   |-- src/
|   |   |-- components/         # Typed selectors, charts, map, and CSV export
|   |   |-- pages/              # Dashboard and component tests
|   |   |-- api.ts              # Typed HTTP client
|   |   `-- types.ts            # Shared frontend contracts
|   |-- package.json
|   |-- tsconfig.json
|   `-- vite.config.ts
|-- .env.example
|-- pyproject.toml
`-- README.md
```

## Prerequisites

- Python 3.11 or newer.
- Node.js 22.13 or newer and npm.
- Git.
- Internet access while the application is running, because indicator data comes from the World Bank API.

## Installation

Clone the repository:

```powershell
git clone https://github.com/viniciusrodriguesai/worldbank-economic-dashboard.git
cd worldbank-economic-dashboard
```

### Backend

Create an isolated environment from the repository root.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
uvicorn backend.app:app --reload --port 8000
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
uvicorn backend.app:app --reload --port 8000
```

The API and interactive OpenAPI documentation are available at:

- API: http://127.0.0.1:8000
- OpenAPI UI: http://127.0.0.1:8000/docs

Use `backend/requirements.txt` instead when only runtime dependencies are needed.

### Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server runs at http://localhost:5173 and proxies `/api` requests to the backend at `http://127.0.0.1:8000`.

## Configuration

Copy the example files only when you need to override their defaults.

| Variable | Default | Purpose |
| --- | --- | --- |
| `WB_API_BASE` | `https://api.worldbank.org/v2` | World Bank REST API base URL |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated FastAPI origin allowlist |
| `VITE_API_BASE_URL` | `/api` | Frontend API base URL |

For a deployed frontend, set `VITE_API_BASE_URL` to the public backend URL before running the production build.

## API

| Method | Route | Main parameters | Result |
| --- | --- | --- | --- |
| GET | `/countries` | none | Cached World Bank country metadata |
| GET | `/indicators` | none | Cached World Bank indicator metadata |
| GET | `/data` | `country`, `indicator`, `start`, `end` | Historical observations |
| GET | `/forecast` | `country`, `indicator`, `start`, `end`, `years_ahead` | Future ARIMA points |

Historical data example:

```bash
curl "http://127.0.0.1:8000/data?country=BRA&indicator=NY.GDP.MKTP.CD&start=2000&end=2022"
```

Forecast example:

```bash
curl "http://127.0.0.1:8000/forecast?country=BRA&indicator=NY.GDP.MKTP.CD&start=2000&end=2022&years_ahead=5"
```

## Validation

Run backend tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run frontend tests and a production build:

```powershell
cd frontend
npm test
npm run build
```

The production frontend is generated in `frontend/dist/`. Plotly and Leaflet are loaded as separate lazy chunks so the initial application bundle remains smaller.

## Data and forecasting notes

- Data is fetched live over HTTPS from the World Bank API.
- Country and indicator metadata is cached in memory for one hour.
- No local SQLite database is required or shipped.
- ARIMA needs at least ten valid historical observations.
- Forecasts are statistical estimates and should not be treated as financial or policy advice.

## License

Licensed under the MIT License. See [LICENSE](LICENSE).

## Author

Vinicius Mangueira - Data Science and Artificial Intelligence student at UFPB.
