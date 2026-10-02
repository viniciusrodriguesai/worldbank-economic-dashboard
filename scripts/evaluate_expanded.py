"""Fixed six-series replication; snapshot current API vintages, then evaluate offline."""
import concurrent.futures
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SERIES = [(country, indicator) for country in ('BRA', 'USA', 'DEU')
          for indicator in ('NY.GDP.MKTP.KD.ZG', 'FP.CPI.TOTL.ZG')]
DEST = ROOT / 'docs/data/expanded-v1'


def run_series(spec):
    country, indicator = spec
    stem = country.lower() + '-' + ('gdp-growth' if indicator.startswith('NY.') else 'inflation')
    url = f'https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=20000'
    raw = urlopen(url, timeout=60).read()
    metadata, values = json.loads(raw)
    if metadata['pages'] != 1:
        raise ValueError('Expected a complete single response')
    rawpath = DEST / (stem + '-source.json')
    with rawpath.open('xb') as f:
        f.write(raw)
    datapath = DEST / (stem + '.csv')
    rows = sorted((int(v['date']), v['value']) for v in values if v['value'] is not None)
    with datapath.open('x', newline='') as f:
        writer = csv.writer(f); writer.writerow(['country', 'indicator', 'year', 'value'])
        writer.writerows((country, indicator, year, value) for year, value in rows)
    out = DEST / (stem + '-backtest.json')
    subprocess.run([sys.executable, str(ROOT/'scripts/evaluate_forecasts.py'), '--data', str(datapath),
                    '--country', country, '--indicator', indicator, '--output', str(out)], check=True)
    report = json.loads(out.read_text())
    return {'country': country, 'indicator': indicator, 'source_url': url,
            'source_sha256': hashlib.sha256(raw).hexdigest(), 'source_lastupdated': metadata.get('lastupdated'),
            'non_null_points': len(rows), 'first_year': rows[0][0], 'last_year': rows[-1][0],
            'report': out.name, 'origin_count': report['origin_count'],
            'metrics': report['aggregate_metrics'], 'metrics_by_horizon': report['metrics_by_horizon']}


if __name__ == '__main__':
    DEST.mkdir(parents=True, exist_ok=True)
    if any(DEST.iterdir()):
        raise SystemExit('Output directory must be empty; preserve previous runs')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run_series, SERIES))
    summary = {'protocol': 'six-series-current-vintage-v1', 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
               'countries': ['BRA', 'USA', 'DEU'], 'indicators': ['NY.GDP.MKTP.KD.ZG', 'FP.CPI.TOTL.ZG'],
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'series': results}
    with (DEST/'summary.json').open('x') as f:
        json.dump(summary, f, indent=2, allow_nan=False); f.write('\n')
    for r in results:
        print(r['country'], r['indicator'], r['non_null_points'], r['metrics'], flush=True)
