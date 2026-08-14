# Threat model

## Scope and assumptions

This model covers the React/Vite browser application, FastAPI service, World Bank client,
forecasting process, CSV downloads, OpenStreetMap tiles, package installation, and GitHub
Actions. The application currently has no accounts, authorization boundary, database, or
required server secret. Internet clients and upstream responses are untrusted.
`WB_API_BASE` and deployment environment variables are trusted operator configuration,
not browser input.

## Assets

- Availability of the UI, API, workers, metadata cache, upstream quota, CPU, and memory.
- Integrity and provenance of observations, forecasts, model metrics, and CSV downloads.
- Runtime configuration and any future deployment credentials.
- Repository source, GitHub Actions tokens, dependency pins/lockfile, and CI integrity.
- Browser trust, including DOM safety and safe handling by spreadsheet software.

## Trust boundaries and data flow

1. An untrusted browser loads the static Vite build from a frontend host or CDN.
2. The browser calls FastAPI through `/countries`, `/indicators`, `/data`, and `/forecast`.
   Query strings cross the first trust boundary. CORS limits cross-origin browser reads;
   it is not authentication or a server-side rate limit.
3. FastAPI contacts a configured World Bank HTTPS origin. Country, indicator, range, and
   forecast controls must be validated before they influence URLs or expensive work.
4. World Bank JSON crosses an external-data boundary and must be checked for pagination,
   required fields, valid years, finite values, duplicates, and missing observations.
5. Statistical fitting crosses a resource boundary: CPU-heavy model candidates need
   bounded search, concurrency, history, horizon, and deterministic failure behavior.
6. Browser tile requests go directly to OpenStreetMap and disclose the browser IP, map
   bounds, and user agent to that third party. No application credential is sent.
7. CSV strings cross into spreadsheet software, where leading formula characters can
   change data into executable spreadsheet expressions.
8. CI downloads actions and packages from GitHub, PyPI, and npm. A read-only workflow token
   reduces impact but publishers and mutable references remain supply-chain trust inputs.

## Entry points and abuse cases

| Entry point | Realistic abuse | Required control |
| --- | --- | --- |
| `/countries` | Expired-cache refresh storm or malformed metadata | Locked TTL cache, bounded pages, stale-on-error, safe 503 |
| `/indicators` | Huge response, expensive filtering, refresh storm | Search/pagination bounds and cached metadata |
| `/data` | Traversal syntax, Unicode, huge ranges, upstream probing | Anchored code patterns, known metadata, interval bound, safe errors |
| `/forecast` | Repeated CPU-heavy fits or huge candidate parameters | Server-owned bounded candidates, horizon/range caps, concurrency/rate limits |
| CSV export | Formula execution, broken quoting, deceptive filename | Typed serializer, formula neutralization, deterministic columns |
| CORS | Malicious origin reads browser-accessible API responses | Exact origins, GET only, no credentials, restricted headers |
| `WB_API_BASE` | Operator points client to unsafe or credential-bearing URL | Trusted configuration, HTTPS validation, redirect/host policy |
| World Bank response | Malformed JSON/pages, NaN/Inf, duplicates, missing years | Structural and statistical validation before modeling/rendering |
| Map tiles | Third-party tracking or outage | HTTPS, attribution, optional/non-critical role, documented host policy |
| GitHub Actions | Action/package compromise or token misuse | SHA pins, least privilege, clean installs, audits, dependency review |

## Assets-to-controls summary

- Availability depends on upstream timeouts, cache behavior, pagination caps, forecast
  concurrency, reverse-proxy rate limits, worker timeouts, and container resource limits.
- Result integrity depends on response schemas, annual indexing, missing-year disclosure,
  finite-value checks, temporal evaluation, and visible uncertainty.
- Configuration integrity depends on server-only environment variables, no frontend
  secrets, exact origin parsing, and deployment secret stores.
- Supply-chain integrity depends on reviewed pins, lockfile enforcement, action SHA pins,
  audit automation, Dependabot, and read-only CI permissions.

## Residual risks

- Process-local caches and semaphores do not coordinate multiple workers. A shared Redis
  cache/limiter or platform control is appropriate only when the deployment needs it.
- A public API without identity cannot enforce a strong per-user quota. The reverse proxy
  should rate-limit using a trusted client-IP chain and cap request duration/body size.
- The application inherits World Bank correctness and availability risk.
- OpenStreetMap privacy, availability, and acceptable-use policy are external concerns.
- Registry and GitHub Action publishers remain supply-chain trust dependencies.
- Forecasts are estimates, not facts, and must expose validation and uncertainty.
