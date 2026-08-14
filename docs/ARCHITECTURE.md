# Architecture

## System boundaries

The application has three runtime boundaries:

1. The browser runs the React/Vite application, renders World Bank observations, fetches
   OpenStreetMap tiles, and creates CSV downloads.
2. FastAPI validates requests, retrieves and normalizes World Bank data, coordinates
   metadata caching, and invokes statistical evaluation.
3. The World Bank API is an untrusted external data source. Every response is bounded,
   structurally checked, normalized, and filtered before use.

Production nginx is both the static frontend host and the same-origin /api proxy. A
separate external edge must terminate TLS.

## Backend responsibilities

| Module | Responsibility |
| --- | --- |
| backend/app.py | FastAPI construction, CORS, HTTP validation, routes, exception-to-status mapping, cache coordination, and forecast capacity |
| backend/core/cache.py | Thread-safe TTL cache, single-flight refresh, stale-on-error window, and retry backoff |
| backend/data_loader.py | Validated World Bank HTTP/pagination, metadata and observation normalization, plus the backward-compatible legacy forecast |
| backend/services/forecasting.py | Annual-index preparation, temporal validation, baselines, bounded ARIMA candidates, selection, metrics, and bounds |
| backend/models.py | Pydantic response contracts |
| backend/exceptions.py | Application exception taxonomy kept separate from HTTP details |

Routes contain the remaining HTTP orchestration, while forecasting and infrastructure
logic are separated. data_loader.py remains a compatibility boundary for the original
public functions; splitting its World Bank transport into backend/clients is a reasonable
future refactor only if it does not break those imports.

## Frontend responsibilities

| Module | Responsibility |
| --- | --- |
| frontend/src/api.ts | Axios instance, typed endpoint calls, cancellation, and safe error extraction |
| frontend/src/pages/Dashboard.tsx | Analysis state, debounced metadata search, stale-request cancellation, comparison and forecast orchestration |
| frontend/src/components | Accessible selectors, Plotly history/forecast display, map context, and CSV action |
| frontend/src/csv.ts | Deterministic typed CSV encoding and spreadsheet formula neutralization |
| frontend/src/types.ts | Browser-side API and visualization contracts |
| frontend/nginx.conf | Static delivery, SPA fallback, browser security headers, API proxy and throttling |

The browser receives no server credential. VITE-prefixed variables are public build-time
configuration and must never contain secrets.

## Data flows

### Metadata

~~~text
Browser -> /api/countries or /api/indicators
        -> nginx rate limit
        -> FastAPI validation
        -> fresh cache, one locked refresh, or bounded stale snapshot
        -> paginated World Bank HTTPS responses
        -> normalized Pydantic response
~~~

### Historical comparison

~~~text
1-5 ISO3 codes + indicator + years
        -> request and known-metadata validation
        -> one bounded World Bank series request per country
        -> finite/unique annual observations
        -> typed response
        -> Plotly lines and safe multi-country CSV
~~~

### Forecast evaluation

~~~text
one country + indicator + years + horizon
        -> validation and non-blocking forecast capacity acquisition
        -> bounded World Bank history
        -> contiguous annual-tail preparation
        -> chronological candidate evaluation
        -> selected baseline or ARIMA
        -> metrics, warnings, estimates and bounds
~~~

## Configuration

WB_API_BASE and CORS_ORIGINS are server runtime configuration. VITE_API_BASE_URL is a
public frontend build value. Docker Compose also accepts DASHBOARD_BIND_ADDRESS, which
defaults to loopback. The application requires no secret today.

The World Bank base is HTTPS-only, cannot contain credentials, and cannot be redirected
to another host. Browser query parameters never select an upstream host.

## Availability controls

- World Bank pagination, response bytes, records, redirects, and timeouts are bounded.
- Metadata uses a one-hour TTL and at most six additional stale hours during an outage.
- Failed metadata refreshes back off for 60 seconds.
- Forecast horizon is 1-10 years and the ARIMA set contains five server-owned orders.
- Two in-process forecast operations may run concurrently.
- Production nginx applies a GET-only API proxy and request rate limit.
- Compose assigns CPU/memory limits and keeps FastAPI private.

In-memory cache and semaphore state are process-local. Multiple workers or replicas
multiply upstream refresh and forecast capacity. Scale only with matching platform limits
and monitoring; introduce shared infrastructure only when operational need justifies it.

## Deployment

The backend image contains Python runtime dependencies and runs Uvicorn without reload as
UID/GID 10001. The frontend is built in Node and copied into a separate nginx image
running as UID/GID 101. Both images are digest-pinned and monitored by Dependabot.

See DEPLOYMENT.md for TLS, secrets, health checks, resources, and remaining external steps.
