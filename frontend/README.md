# Frontend

The frontend is a strict TypeScript/React data product built with Vite. It supports
bounded indicator search, one-to-five-country comparison, dynamic year ranges, KPIs,
Plotly history and forecast charts, Leaflet context, and secure CSV export.

See the [root guide](../README.md), [source guide](src/README.md), and
[page orchestration guide](src/pages/README.md).

## Technology

| Tool | Role |
| --- | --- |
| React 19 | UI state, semantics, and rendering |
| TypeScript 7 strict mode | Browser/API contract safety |
| Vite 8 | Development and optimized production build |
| Axios | Typed requests, timeouts, and cancellation |
| React Select | Accessible searchable multi-select controls |
| Plotly basic distribution | Historical lines, forecast line, and uncertainty band |
| React Leaflet | Geographic context and OpenStreetMap tiles |
| Vitest and Testing Library | User-oriented deterministic tests |
| Oxlint | TypeScript, React, accessibility, and suspicious-code checks |

## Commands

~~~powershell
npm ci
npm audit --audit-level=high
npm run lint
npm test
npm run test:coverage
npm run test:watch
npm run build
npm run dev
~~~

npm run build performs strict TypeScript validation before the Vite production build.
Coverage thresholds are configured in vite.config.ts and enforced in CI.

## Development

Vite listens on http://localhost:5173 and proxies /api to
http://127.0.0.1:8000. Production does not use this server; nginx serves dist and proxies
the same /api prefix.

VITE_API_BASE_URL defaults to /api. It is embedded into browser JavaScript at build time,
so it is public configuration. Never place a password, token, private host credential, or
server secret in any VITE-prefixed variable.

## Data flow

~~~mermaid
flowchart TD
    Start[Dashboard mounts]
    Countries[Load country metadata]
    Search[Debounced indicator search]
    Select[Choose 1-5 countries, indicator, years]
    Validate[Validate shared range]
    Cancel[Abort obsolete request]
    Compare[Fetch comparison data]
    KPIs[Calculate visible summaries]
    Chart[Render multi-line history]
    Export[Create safe CSV]
    Forecast[Evaluate one-country forecast]
    Band[Render metrics and uncertainty]

    Start --> Countries
    Start --> Search
    Countries --> Select
    Search --> Select
    Select --> Validate --> Cancel --> Compare
    Compare --> KPIs
    Compare --> Chart
    Compare --> Export
    Compare --> Forecast --> Band
~~~

## Security boundaries

- src/api.ts owns endpoint paths, the 20-second timeout, AbortSignal use, and safe FastAPI
  error extraction.
- src/csv.ts distinguishes numeric cells from untrusted text, quotes fields
  deterministically, and neutralizes spreadsheet formula prefixes.
- React renders text normally; there is no dangerouslySetInnerHTML use.
- Plotly and Leaflet receive normalized typed data. Map tiles are an external browser
  request and never receive an application credential.
- Object URLs created for downloads are revoked after use.
- Stale comparison and forecast requests are canceled and cannot replace newer state.

## Source layout

| Path | Responsibility |
| --- | --- |
| src/api.ts | Typed HTTP boundary and cancellation |
| src/types.ts | Shared API, selector, chart, and forecast contracts |
| src/csv.ts | Safe deterministic CSV serialization |
| src/pages/Dashboard.tsx | Product state and workflow orchestration |
| src/components | Selectors, charts, map, and export action |
| src/test/setup.ts | DOM matchers and test cleanup |
| nginx.conf | Production static host, CSP, headers, rate limit, and API proxy |

## Testing

The frontend tests cover metadata and indicator requests, country selection, historical
comparison, cancellation, invalid ranges, loading/error states, forecast metrics,
uncertainty rendering, CSV encoding/formula protection, accessible control names, and
download URL cleanup.

External HTTP is mocked. Tests must not call the live World Bank API or OpenStreetMap.

Latest measured local coverage is reported in the root engineering report; CI enforces
minimums of 78% statements, 65% branches, 80% functions, and 80% lines.

## Production

The multi-stage Dockerfile builds with Node and copies only dist into a digest-pinned
nginx runtime. nginx runs as UID 101 with a read-only root, dropped capabilities and
bounded temporary storage. See [deployment](../docs/DEPLOYMENT.md).
