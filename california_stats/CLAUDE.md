# Project: California Prop 13 Property Tax Disparity Analysis

## Overview
Analyzes the property tax gap created by Proposition 13 (1978) across all 58 California counties.
Produces interactive choropleth maps, bar charts, and scatter plots showing which counties have the
largest disparities between assessed values and current market values — and who benefits most.

## Architecture
- `src/ca_data.py` — Data fetching, embedded fallback data, and metric computation
- `data/processed/county_prop13.csv` — Merged output from notebook 01 (inputs for 02-05)
- `notebooks/` — Jupyter notebooks (01-05), must run in order
- `scripts/generate_html.py` — Generates `docs/report.html` from executed notebook outputs
- `docs/report.html` — Final self-contained report with all interactive charts

## Methodology
**Assessment Ratio = BOE Residential AV / Zillow Market Value**
- BOE total secured roll × residential fraction (~70%) = residential assessed value (AV)
- Zillow median home value × Census owner-occupied units = estimated market value
- Lower ratio → larger Prop 13 benefit (long-tenure owners, high-appreciation areas)

**Annual Tax Gap = (Market Value − Residential AV) × 1.1%**
- 1.1% = California's 1% base rate plus average local bonds/special assessments
- Represents estimated additional revenue if all homes assessed at current market value

## Notebook Pipeline
Notebooks must run in order (02-05 depend on `data/processed/county_prop13.csv` from 01):

1. `01_data_collection` — Fetch/merge BOE, Zillow, Census data → `county_prop13.csv`
2. `02_assessment_ratio_map` — Choropleth: assessment ratio by county (lower = more Prop 13 benefit)
3. `03_top_bottom_counties` — Bar charts: all counties ranked by assessment ratio and gap per household
4. `04_revenue_gap_map` — Choropleth: total and per-household annual tax gap by county
5. `05_income_correlation` — Scatter plots: does income correlate with Prop 13 benefit?

## Data Sources
- **CA Board of Equalization Annual Report 2022-23** — County-level total secured assessed values
  (embedded in `src/ca_data.py`; source: boe.ca.gov)
- **Zillow Research ZHVI** — County-level median home values, SFR+condo, all tiers
  (downloaded at runtime; falls back to embedded 2023 estimates)
- **Census ACS 5-Year 2022** — Owner-occupied units, median income, median home value
  (fetched via Census API at runtime; no API key required; falls back to embedded estimates)
- Joined on 5-digit FIPS codes (zero-padded strings)

## Running Notebooks
```bash
# Set up environment
uv venv && uv pip install -e .

# Run all notebooks in order
.venv/bin/python -m papermill notebooks/01_data_collection.ipynb /dev/null --cwd notebooks
.venv/bin/python -m papermill notebooks/02_assessment_ratio_map.ipynb /dev/null --cwd notebooks
.venv/bin/python -m papermill notebooks/03_top_bottom_counties.ipynb /dev/null --cwd notebooks
.venv/bin/python -m papermill notebooks/04_revenue_gap_map.ipynb /dev/null --cwd notebooks
.venv/bin/python -m papermill notebooks/05_income_correlation.ipynb /dev/null --cwd notebooks
```

## Generating the HTML Report
After running all notebooks:
```bash
.venv/bin/python scripts/generate_html.py
```
Output: `docs/report.html` — single self-contained file with all interactive Plotly charts.

## Environment
- Python 3.9+ virtualenv at `.venv/`
- No API keys required (Census API works unauthenticated for these queries)
- Key dependencies: pandas, numpy, plotly, scipy, papermill
