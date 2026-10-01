"""Offline evaluation of one normalized World Bank annual CSV snapshot."""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from backend.services.backtesting import rolling_origin_evaluation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--country", required=True)
    parser.add_argument("--indicator", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new path to preserve previous results.")
    report = rolling_origin_evaluation(pd.read_csv(args.data), args.country, args.indicator)
    report["data_sha256"] = hashlib.sha256(args.data.read_bytes()).hexdigest()
    report["python"] = platform.python_version()
    report["versions"] = {p: importlib.metadata.version(p) for p in
                          ("numpy", "pandas", "scipy", "statsmodels")}
    report["source_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report["source_sha256"] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__).resolve(), ROOT / "backend/services/backtesting.py",
                  ROOT / "backend/services/forecasting.py")
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against a concurrent writer.
    with args.output.open("x") as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write("\n")


if __name__ == "__main__":
    main()
