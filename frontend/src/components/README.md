# Frontend Components

This directory contains the reusable presentation and interaction building blocks used by the dashboard. Components receive typed data and callbacks through props; they do not call the backend directly or own application-level request state.

## Design principles

- Keep components focused on one visible responsibility.
- Prefer controlled inputs so the page remains the single source of truth.
- Import shared domain contracts from `../types` instead of redefining them.
- Keep HTTP requests, orchestration, and cross-component state in the page layer.
- Return a safe empty state when a visualization has no meaningful data.
- Preserve keyboard access, descriptive labels, and native browser behavior.
- Lazy-load visualization components from the consuming page because their libraries are comparatively large.

## Component catalog

| Component | Responsibility | Important contract |
| --- | --- | --- |
| `CountrySelector.tsx` | Displays a searchable, clearable country selector. | Receives `CountryOption[]`, a controlled value, an `onChange` callback, and optional loading state. |
| `IndicatorSelector.tsx` | Displays a searchable, clearable economic indicator selector. | Receives `IndicatorOption[]`, a controlled value, an `onChange` callback, and optional loading state. |
| `LineChart.tsx` | Renders historical and forecast time-series data with Plotly. | Accepts normalized `ChartPoint[]`; returns `null` when the collection is empty. |
| `MapChart.tsx` | Locates the selected country on an interactive Leaflet map. | Requires a `CountryOption` carrying the ISO 3166-1 alpha-2 code used by the coordinate lookup. |
| `ExportCSV.tsx` | Converts indicator observations into a browser download. | Accepts `IndicatorPoint[]`, a filename, and an optional disabled state. |

## Controlled selectors

`CountrySelector` and `IndicatorSelector` intentionally expose the same interaction model:

```tsx
<CountrySelector
  options={countries}
  value={selectedCountry}
  onChange={setSelectedCountry}
  isLoading={isMetadataLoading}
/>
```

The owning page controls the selected value. A selector must not fetch its own options, infer a default selection, or trigger side effects beyond calling `onChange`. This keeps request timing deterministic and makes both selectors straightforward to test.

Both selectors use explicit ARIA labels and remain clearable. If their visual width or styling changes, preserve readable focus states and keyboard navigation supplied by `react-select`.

## Line chart

`LineChart` consumes `ChartPoint`, the shared union-friendly shape used for historical observations and forecasts:

```ts
interface ChartPoint {
  year: number;
  indicatorValue: number;
}
```

The component uses `plotly.js-basic-dist-min` through the React Plotly factory. The basic distribution is deliberate: it supplies the scatter trace needed by this dashboard without pulling every Plotly chart type into the bundle.

The chart is responsive, hides the Plotly logo, and listens for container resizing. The page should import it with `React.lazy` so users do not download the visualization bundle before a chart is needed.

When extending the chart:

1. Normalize new data shapes before passing them into the component.
2. Keep trace construction deterministic and free of request logic.
3. Preserve the empty-array guard.
4. Check the production chunk sizes after adding Plotly features.
5. Add a focused test for any new branching behavior.

## Country map

`MapChart` uses React Leaflet and OpenStreetMap tiles. Its local `countryCoords` table maps ISO alpha-2 country codes to representative latitude and longitude pairs. The page passes the complete selected country rather than an untyped code.

`RecenterMap` is a small internal helper that calls Leaflet's imperative `setView` API whenever the selected country changes. Keeping this bridge inside the map module prevents map-specific behavior from leaking into `Dashboard`.

If a country is added or corrected:

- use the uppercase ISO alpha-2 code returned by the backend;
- add a valid `[latitude, longitude]` tuple;
- keep values within geographic bounds;
- verify that selecting the country moves the marker and viewport;
- retain OpenStreetMap attribution when changing tile configuration.

Like the line chart, the map must remain a lazy page dependency. Leaflet CSS is imported by the map module so it loads with the feature that requires it.

## CSV export

`ExportCSV` creates a UTF-8 CSV document entirely in the browser. It:

- derives headers from the typed indicator record;
- serializes individual fields with `JSON.stringify` for safe quoting;
- prepends a byte order mark for spreadsheet compatibility;
- creates a temporary object URL;
- triggers a native download; and
- removes the temporary element and revokes the URL immediately afterward.

The component returns early for empty data. Its button should also be disabled by the page whenever exporting would be misleading, such as while a request is loading or before observations exist.

## Dependency boundaries

Components may import:

- React and component-specific third-party libraries;
- shared interfaces from `../types`;
- colocated styles or assets when introduced; and
- small helpers that are presentation-specific.

Components must not import:

- the Axios client from `../api`;
- page modules;
- environment variables directly; or
- backend response details that have not been represented by shared types.

If a component needs server data, add the request to the page or a future dedicated data hook and pass the result through a typed prop.

## Accessibility checklist

Before publishing a component change, confirm that:

- interactive controls have accessible names;
- buttons declare the correct `type`;
- loading and disabled states are perceivable and enforceable;
- keyboard users can reach and operate every control;
- color is not the only way information is conveyed; and
- map or chart additions include a useful textual alternative in the surrounding page when necessary.

## Testing guidance

The frontend test environment uses Vitest, React Testing Library, and `@testing-library/jest-dom`. Prefer user-visible assertions over implementation details.

Good component tests cover:

- callbacks produced by real user interaction;
- empty, loading, and disabled states;
- accessible roles and labels;
- cleanup of browser resources such as object URLs; and
- deterministic rendering from representative typed props.

Plotly and Leaflet can be mocked at their module boundaries for unit tests. Browser-level integration tests should be reserved for validating real rendering, resizing, tile loading, and downloads.

## Adding a component

1. Define the smallest useful props interface next to the component.
2. Reuse a shared domain type when the prop represents API data.
3. Keep data fetching and page orchestration outside the component.
4. Add accessible names and explicit empty or disabled behavior.
5. Add or update tests for user-observable behavior.
6. Export the component as the default export to match the current convention.
7. Run `npm test` and `npm run build` from `frontend/`.
8. Update this catalog when the new component introduces a meaningful responsibility.

## Related documentation

- [`../README.md`](../README.md) explains the source-layer architecture and dependency direction.
- [`../../README.md`](../../README.md) covers frontend setup, scripts, testing, and production builds.
- [`../../../README.md`](../../../README.md) is the project-wide engineering and operations guide.
