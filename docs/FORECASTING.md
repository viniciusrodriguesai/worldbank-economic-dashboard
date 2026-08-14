# Forecasting methodology

## Purpose and contract

GET /forecast/evaluate returns historical observations, future estimates, lower and upper
bounds, model-selection metadata, validation metrics, missing years, and warnings. It is
designed for transparent portfolio analytics, not automated economic decisions.

GET /forecast remains available for backward compatibility and uses the legacy fixed
server-side ARIMA path. The dashboard uses the evaluated endpoint.

## Annual index and missing values

World Bank series may omit calendar years. Treating 2018, 2019, 2021, and 2024 as four
equally spaced observations would silently compress time, so the service:

1. requires country, indicator, year, and value fields;
2. converts years and values to numeric types;
3. removes missing and non-finite observations;
4. sorts by year and rejects duplicate years;
5. enumerates every missing calendar year between first and last observation; and
6. models only the contiguous tail after the latest gap.

Missing economic values are never interpolated. The full cleaned history remains in the
response, missing years are explicit, and a warning identifies the modeled tail. At least
10 consecutive observations ending at the latest year are required. Otherwise forecasting
is rejected as statistically irresponsible.

## Temporal validation

There is no random shuffle. From the contiguous tail, the newest observations form a
chronological holdout:

~~~text
validation_points = max(2, min(5, observation_count // 4))
train = all earlier values
actual = final validation_points values
~~~

This creates a two-to-five-year holdout while preserving at least eight training values
under the minimum-history rule. It is intentionally bounded for predictable API cost.

## Candidate models

Two baselines are always evaluated:

- naive: repeat the last training value;
- drift: extrapolate the average change from first to last training value.

The best baseline is selected by lowest MAE, then RMSE. Non-constant series also evaluate
exactly five ARIMA orders:

~~~text
(0,1,0), (1,1,0), (0,1,1), (1,1,1), (1,0,0)
~~~

Statsmodels stationarity and invertibility enforcement are relaxed for candidate fitting.
Non-convergent, invalid, non-finite, or numerically failed candidates are discarded.
Constant series skip ARIMA and select the naive baseline.

## Metrics and selection

The service reports:

- MAE: mean absolute error, the primary selection metric;
- RMSE: root mean squared error, the deterministic tie-breaker;
- MAPE: returned only when every actual holdout value is safely non-zero;
- sMAPE: symmetric percentage error with zero denominators excluded.

The best ARIMA must have strictly lower holdout MAE than the best baseline. Otherwise the
baseline remains selected and the response says that no ARIMA candidate outperformed it.
Training fit criteria such as AIC do not override out-of-sample validation.

## Final fit and uncertainty

The selected model is refit on the complete contiguous tail for a horizon of 1-10 years.
ARIMA uses Statsmodels 95% forecast intervals. Baseline bounds are an approximate
uncertainty band:

~~~text
width(h) = 1.96 * standard_deviation(first_differences) * sqrt(h)
~~~

Baseline bands are not formal model confidence intervals and should not be interpreted as
guaranteed probability coverage. Lower and upper values are normalized before response
serialization.

If the selected ARIMA fails on the full history, the service falls back to the selected
baseline and adds a warning instead of returning invented values or crashing.

## Limitations

- Validation is one chronological holdout, not a full rolling-origin study.
- The candidate set is deliberately small to control denial-of-service risk.
- Models are univariate and do not incorporate policy, shocks, or exogenous variables.
- World Bank revisions can change history and future evaluations.
- Baseline uncertainty is heuristic.
- A model beating a baseline historically does not imply future economic accuracy.

The UI labels future points as forecasts, visually separates them from observations, and
shows warnings and metrics so users can judge these limitations.
