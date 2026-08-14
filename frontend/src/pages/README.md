# Frontend page orchestration

Dashboard.tsx is the product workflow boundary between typed API functions and reusable
visual components.

## Responsibilities

- Load country metadata and perform debounced, bounded indicator search.
- Own one-to-five selected countries, a shared indicator, a shared annual range, and a
  forecast horizon of 1, 3, 5, or 10 years.
- Reject reversed or incomplete ranges before requesting data.
- Cancel superseded metadata, comparison, and forecast requests.
- Fetch multi-country history and clear stale responses on selection changes.
- Calculate latest value, latest year, previous-period change, and evaluation KPIs.
- Allow evaluated forecasting only when exactly one country is selected.
- Present loading, validation, upstream, empty, and forecast failure states.
- Pass normalized series and bounds to charts without hiding missing-year warnings.
- Enable CSV export only when current data exists.

The map intentionally shows the first selected country as lightweight context; it is not
a quantitative choropleth and does not replace the comparison chart.

## State and request lifecycle

Country and indicator options, selected filters, comparison points, forecast response,
three independent loading flags, and one user-visible message are separate state.
Historical changes clear forecast state immediately.

Each request family owns an AbortController. Cleanup aborts in-flight work, and completion
handlers update loading state only when they still own the active controller. Cancellation
is not surfaced as a user error.

Indicator input is debounced before calling GET /indicators. Valid selections call
GET /data/compare with repeated country query parameters. The explicit forecast button
calls GET /forecast/evaluate and displays selection metrics, baseline comparison,
warnings, and the uncertainty band.

## Tests

Dashboard tests use accessible names and mocked API functions. They verify metadata,
selection, stale-request cancellation, invalid dates, loading and upstream failures,
comparison rendering, forecast evaluation, metrics, and bounds. Keep orchestration tests
here; test reusable CSV/chart behavior beside its component or utility.
