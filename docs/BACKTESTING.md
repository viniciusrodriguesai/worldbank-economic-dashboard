# Forecast evaluation across historical origins

The dashboard's last-window errors are used to select a model. They are selection scores, not an independent estimate of that selected procedure's performance.

`backend/services/backtesting.py` adds a separate **nested expanding-origin evaluation**:

1. Require one country/indicator series and use the latest contiguous annual tail; do not interpolate missing years.
2. Use up to eight most recent eligible origins, at least 12 training years, and a three-year horizon by default.
3. At each origin, pass only the historical prefix to the dashboard's existing selection procedure. Its inner chronological validation chooses between naive, drift and bounded ARIMA candidates.
4. Predict the next three years and score these outer observations only after selection.
5. Compare the procedure with both naive and drift on exactly the same targets. Report aggregate and horizon-specific MAE, RMSE, MAPE and sMAPE, plus every prediction and selected model.

Overlapping windows share target observations: pooled errors are origin/horizon pairs, not independent samples. Do not interpret these results as a statistical significance test. Any failed origin aborts the evaluation rather than silently favoring successful fits.

## Reproduce offline

Install `backend/requirements-dev.txt`. Save a normalized, single-series CSV with `country,indicator,year,value` columns and retain its World Bank source URL, retrieval date and indicator units separately. Then run from the repository root:

```bash
python scripts/evaluate_forecasts.py --data data/bra_gdp_growth.csv --country BRA --indicator NY.GDP.MKTP.KD.ZG --output reports/bra_gdp_growth_v1.json
```

The input path is an example, not a bundled dataset. The output path must be new. The report contains data/source fingerprints, package versions, source commit, predictions, warnings and metrics. Script fingerprints identify local changes even if the recorded commit predates them.

## Validation status

Synthetic tests verify that outer observations never reach selection, calendar alignment, constant-series behavior and input bounds. **No real World Bank performance result is claimed in this change**: the upstream retrieval timed out in the execution environment.

Use several predeclared countries and indicators before drawing general conclusions. Fix the evaluation protocol before inspecting results; retuning after inspection makes these windows development data. Current annual values can contain later revisions: this is a historical-value backtest, not a real-time vintage-data study. Calibration, interval coverage and external generalization remain unverified.

Reference: [Hyndman & Athanasopoulos, Forecasting: Principles and Practice, time series cross-validation](https://otexts.com/fpp3/tscv.html).
