# Six-series temporal replication

The country/indicator grid was fixed before execution: BRA, USA and DEU × GDP growth (`NY.GDP.MKTP.KD.ZG`) and CPI inflation (`FP.CPI.TOTL.ZG`). All six runs are reported, without changing models or using their outer errors for selection. The same nested expanding-origin procedure evaluates eight origins and horizons 1–3 per series: 144 forecast/actual pairs.

Current World Bank API vintages were downloaded in October 2026. These are revised observations, not real-time historical vintages. Snapshot responses, normalized CSVs, hashes, model choices, all forecasts and baselines are tracked in `docs/data/expanded-v1/`.

| Country | Indicator | Points | Selected MAE | Naive MAE | Drift MAE |
| --- | --- | --- | --- | --- | --- |
| BRA | NY.GDP.MKTP.KD.ZG | 65 | 2.6171 | 3.1268 | 3.2840 |
| BRA | FP.CPI.TOTL.ZG | 45 | 3.2508 | 3.2571 | 4.7280 |
| USA | NY.GDP.MKTP.KD.ZG | 65 | 1.4342 | 2.3070 | 2.3455 |
| USA | FP.CPI.TOTL.ZG | 65 | 1.7659 | 1.8533 | 1.8710 |
| DEU | NY.GDP.MKTP.KD.ZG | 65 | 2.4413 | 2.8208 | 2.8412 |
| DEU | FP.CPI.TOTL.ZG | 66 | 1.9341 | 2.1602 | 2.1955 |

MAE is measured in percentage points; do not pool GDP growth and inflation errors as one score. The selection procedure has lower aggregate MAE than naive on all six series, but Brazil inflation improves by only about 0.0063 percentage points. Not all metrics or horizons improve; per-horizon metrics and all predictions are available. MAPE is unstable around zero and negative growth; MAE/RMSE are the primary descriptive comparisons here.

Eight adjacent origins overlap their forecast windows; these are not 144 independent observations. Countries are a fixed convenience grid, not a representative global sample. No significance, interval-coverage or future performance claim follows. This remains developer-run evaluation, not an independent external review.

Reproduce in a new empty output directory (the runner refuses to overwrite its snapshot):

```bash
python scripts/evaluate_expanded.py
```

For an exact offline rerun, use each tracked CSV with `scripts/evaluate_forecasts.py` and a fresh output path. Running the network collector again may retrieve revised observations. The unchanged evaluation code is tied to source commit `d84a0c47037bdeb6924b1b79c799fcb7ef43312f`; source hashes and package versions are recorded in each report.
