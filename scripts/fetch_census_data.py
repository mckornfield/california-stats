#!/usr/bin/env python3
"""Fetch Census ACS data and save as CSV for reproducibility.

Fetches B25082 (aggregate home values) and B25090 (aggregate property taxes)
alongside the standard owner-occupied units, median income, and median home value.

Output: data/raw/census_acs_2022.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ca_data import fetch_census_data

OUT = ROOT / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

df = fetch_census_data()
out_path = OUT / "census_acs_2022.csv"
df.to_csv(out_path, index=False)
print(f"Saved {len(df)} counties to {out_path}")
print(df.head().to_string())
