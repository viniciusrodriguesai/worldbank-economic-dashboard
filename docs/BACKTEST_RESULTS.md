# Brazil GDP-growth backtest

A real-data demonstration of the deployed selection procedure, executed on 2026-10-01 with Python 3.12.14. Source: [World Bank GDP growth, Brazil](https://api.worldbank.org/v2/country/BRA/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=100), indicator `NY.GDP.MKTP.KD.ZG`, annual percentage growth. API source id 2, last updated 2026-07-13.

The normalized [CSV snapshot](data/bra-gdp-growth.csv) has 65 consecutive annual observations, 1961–2025. The evaluator uses the last eight eligible origins (2015–2022), each with a three-year outer horizon, for 24 forecast/target pairs. Each origin selects its model only using an inner temporal holdout; its outer targets do not influence selection.

| Aggregate error | Selected procedure | Naive | Drift |
| --- | ---: | ---: | ---: |
| MAE (percentage points) | 2.6171 | 3.1268 | 3.2840 |
| RMSE (percentage points) | 3.2446 | 3.9049 | 4.1106 |
| sMAPE (%) | 117.5008 | 114.1765 | 116.9417 |

Aggregate MAE is 16.3% lower than naive and 20.3% lower than drift on this snapshot. This is not uniform superiority: one-year MAE is **2.5763** for the procedure versus **2.5500** for naive, and aggregate sMAPE is worse than both baselines. Negative or near-zero GDP growth makes percentage-error measures difficult to interpret; emphasize MAE/RMSE in percentage points.

The procedure selected ARIMA in five origins, drift in two, and naive in one. All model choices, warnings, per-horizon metrics and actual predictions are in the [machine-readable report](data/bra-gdp-growth-backtest.json).

## Reproduce offline

```bash
python -m pip install -r backend/requirements.txt
python scripts/evaluate_forecasts.py --data docs/data/bra-gdp-growth.csv --country BRA --indicator NY.GDP.MKTP.KD.ZG --output runs/bra-gdp-growth.json
```

Choose a new output path; existing reports cannot be overwritten. The checked-in snapshot makes this demo independent of live API availability. Exact installed package versions and SHA-256 fingerprints for the data and all evaluation/forecast source files are recorded in the JSON report. The source commit is `b145e47aa55563cd187c905bf1933d9c09a273a6`.

## Limits

This is a small single-country/single-indicator benchmark on today's revised historical data, not a real-time vintage backtest. Origin windows overlap, so the 24 errors are not independent observations. No statistical significance, interval coverage or broader economic forecasting advantage is established. No live hosted application is claimed. See [the full protocol](BACKTESTING.md).

Source data attribution: World Bank, GDP growth (annual %), Brazil, retrieved 2026-10-01. [World Bank dataset terms](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets) apply independently of the repository's code license.
