#!/usr/bin/env python3
"""Fetch Zillow ZHVI data and save as CSV for reproducibility.

Output: data/raw/zillow_zhvi.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ca_data import fetch_zillow_county_data

OUT = ROOT / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

df = fetch_zillow_county_data()
out_path = OUT / "zillow_zhvi.csv"
df.to_csv(out_path, index=False)
print(f"Saved {len(df)} counties to {out_path}")
print(df.head().to_string())
