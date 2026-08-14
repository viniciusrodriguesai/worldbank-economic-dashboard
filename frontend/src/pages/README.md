# Frontend Pages

This directory contains route-level and screen-level modules. A page composes reusable components, owns application workflow state, coordinates API requests, and translates backend results into presentation-ready props.

The current application has one page: `Dashboard.tsx`.

## Dashboard responsibilities

`Dashboard` is the orchestration boundary between the typed API client and the visual component layer. It is responsible for:

- loading country and indicator metadata once;
- owning the selected country, indicator, and year range;
- validating the requested period before contacting the API;
- loading historical observations when valid inputs change;
- requesting an explicit five-year forecast;
- canceling obsolete or superseded requests;
- presenting loading, empty, and error states;
- normalizing observations for the chart contract;
- controlling when export is available; and
- lazy-loading the Plotly and Leaflet features.

Reusable components must not duplicate these responsibilities.

## State model

| State | Purpose | Reset conditions |
| --- | --- | --- |
| `countries` | Options returned by `GET /countries`. | Reloaded only when the page mounts. |
| `indicators` | Options returned by `GET /indicators`. | Reloaded only when the page mounts. |
| `country` | Controlled country selection. | Cleared by the country selector. |
| `indicator` | Controlled indicator selection. | Cleared by the indicator selector. |
| `range` | Inclusive historical start and end years. | Updated independently by the two numeric inputs. |
| `data` | Historical observations for the current selection. | Cleared for incomplete inputs, invalid ranges, or failed requests. |
| `forecast` | Future-only forecast observations. | Cleared whenever the selection or range changes. |
| `metadataLoading` | Initial filter loading state. | Ends after both metadata requests settle unless unmounted. |
| `dataLoading` | Historical request loading state. | Ends only for the currently active, non-aborted request. |
| `forecastLoading` | Forecast request loading state. | Ends only when the matching forecast controller settles. |
| `message` | User-visible validation, empty, or API feedback. | Cleared before a valid historical or forecast request. |

Keep independent loading flags. Combining them into one generic boolean would make unrelated controls disable each other and could conceal which operation is still active.

## Request lifecycle

### 1. Metadata initialization

On mount, the page creates one `AbortController` and loads countries and indicators with `Promise.all`. Both option lists become available together. If the page unmounts, the cleanup aborts both requests through the shared signal.

Cancellation is intentionally silent. Other failures pass through `getApiErrorMessage`, which extracts the backend's structured `detail` value when available and falls back to a stable user-facing message.

### 2. Historical data

A reactive effect runs whenever the country, indicator, or year range changes.

The effect performs these operations in order:

1. abort any forecast still running;
2. clear the previous forecast;
3. clear historical data and stop when a selection is incomplete;
4. validate that both years are integers and `start <= end`;
5. create a controller for the new historical request;
6. fetch data for the exact visible inputs;
7. ignore cancellation errors;
8. expose useful empty or failure feedback; and
9. abort the request during cleanup.

This cleanup is essential. Without it, a slower response for an old selection could overwrite the result for the user's newest selection.

### 3. Forecast generation

Forecasting is an explicit button action, not an automatic effect. The handler refuses to run until a country, indicator, and non-empty historical series exist.

Before starting, it aborts any previous forecast and stores the new controller in `forecastControllerRef`. The request reuses the visible historical range and asks for five future periods. In `finally`, the loading flag is cleared only when the completing controller is still the active one.

That identity check prevents an older aborted request from incorrectly marking a newer forecast as finished.

## Data transformations

The API returns `IndicatorPoint` records:

```ts
{
  country: string;
  indicator: string;
  year: number;
  value: number;
}
```

Charts receive the smaller `ChartPoint` representation:

```ts
{
  year: point.year,
  indicatorValue: point.value,
}
```

Keep this adaptation at the page boundary. The API client should preserve server contracts, while the chart should receive only the values required to render.

## Rendering and performance

`LineChart` and `MapChart` are imported with `React.lazy` and rendered inside `Suspense` boundaries. Plotly and Leaflet are substantial dependencies, so static imports here would increase the initial application bundle.

The page renders:

- the map only after a country is selected;
- historical and forecast charts only for non-empty collections;
- progress copy while historical data is loading;
- a forecast button disabled during invalid or conflicting states; and
- a CSV exporter disabled when historical data is absent or loading.

When adding another expensive visualization, follow the same lazy boundary and inspect the Vite production output.

## Error and empty-state policy

- Client validation errors should be specific and should avoid unnecessary requests.
- Canceled requests should not replace the current message.
- Empty successful results should produce an explicit empty-state message.
- Backend errors should use `getApiErrorMessage` instead of assuming an Axios error shape.
- A failed request must clear data that could otherwise be mistaken for the current result.
- Messages should describe what the user can understand, without exposing stack traces or transport internals.

## Dashboard tests

`Dashboard.test.tsx` is an orchestration test suite built with Vitest and React Testing Library. It mocks:

- API functions, so tests control request results and verify exact arguments;
- selectors with native `select` elements, so selection behavior remains easy to exercise;
- Plotly and Leaflet components, so page tests do not depend on browser layout engines.

The current suite verifies that:

1. metadata loads once, selected inputs request historical data, and forecast generation uses the visible year range; and
2. a reversed period is rejected in the browser without requesting historical data.

Add tests whenever page behavior changes. High-value cases include cancellation, structured API errors, empty series, repeated forecast clicks, and loading-state transitions.

Run the focused suite from `frontend/`:

```bash
npm test -- --run src/pages/Dashboard.test.tsx
```

Run the complete frontend verification before publishing:

```bash
npm test
npm run build
```

## Adding a page

1. Define its route-level responsibility and avoid duplicating component behavior.
2. Keep server access behind functions exported from `../api`.
3. Model shared payloads in `../types`.
4. Separate unrelated loading and error states.
5. Add cancellation for effects that can be superseded or unmounted.
6. Lazy-load expensive page-only features.
7. Add tests for the user workflow and request arguments.
8. Register routing only when the application has more than one page.
9. Update this guide and the source architecture documentation.

## Related documentation

- [`../README.md`](../README.md) defines the frontend source architecture.
- [`../components/README.md`](../components/README.md) documents reusable presentation contracts.
- [`../../README.md`](../../README.md) covers frontend development and production commands.
- [`../../../README.md`](../../../README.md) provides the repository-wide guide.
