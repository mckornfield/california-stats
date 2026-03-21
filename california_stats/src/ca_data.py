"""
California Prop 13 analysis data utilities.

Data sources:
- CA Board of Equalization (BOE) Annual Report 2022-23: county-level total secured assessed values
- Zillow Research ZHVI: county-level median home values (downloaded at runtime)
- Census ACS 5-Year 2022: owner-occupied units, median income (fetched at runtime)

Methodology:
  Residential AV estimate = BOE total secured roll × residential_fraction (≈0.70)
  Market value estimate   = Zillow median × Census owner-occupied units
  Assessment ratio        = Residential AV / Market Value   (lower = more Prop 13 benefit)
  Annual tax gap          = (Market Value − Residential AV) × 0.011
"""

import io
import requests
import pandas as pd

# ---------------------------------------------------------------------------
# County reference table: all 58 CA counties
# ---------------------------------------------------------------------------
COUNTIES = [
    ("Alameda",        "06001", "001"),
    ("Alpine",         "06003", "003"),
    ("Amador",         "06005", "005"),
    ("Butte",          "06007", "007"),
    ("Calaveras",      "06009", "009"),
    ("Colusa",         "06011", "011"),
    ("Contra Costa",   "06013", "013"),
    ("Del Norte",      "06015", "015"),
    ("El Dorado",      "06017", "017"),
    ("Fresno",         "06019", "019"),
    ("Glenn",          "06021", "021"),
    ("Humboldt",       "06023", "023"),
    ("Imperial",       "06025", "025"),
    ("Inyo",           "06027", "027"),
    ("Kern",           "06029", "029"),
    ("Kings",          "06031", "031"),
    ("Lake",           "06033", "033"),
    ("Lassen",         "06035", "035"),
    ("Los Angeles",    "06037", "037"),
    ("Madera",         "06039", "039"),
    ("Marin",          "06041", "041"),
    ("Mariposa",       "06043", "043"),
    ("Mendocino",      "06045", "045"),
    ("Merced",         "06047", "047"),
    ("Modoc",          "06049", "049"),
    ("Mono",           "06051", "051"),
    ("Monterey",       "06053", "053"),
    ("Napa",           "06055", "055"),
    ("Nevada",         "06057", "057"),
    ("Orange",         "06059", "059"),
    ("Placer",         "06061", "061"),
    ("Plumas",         "06063", "063"),
    ("Riverside",      "06065", "065"),
    ("Sacramento",     "06067", "067"),
    ("San Benito",     "06069", "069"),
    ("San Bernardino", "06071", "071"),
    ("San Diego",      "06073", "073"),
    ("San Francisco",  "06075", "075"),
    ("San Joaquin",    "06077", "077"),
    ("San Luis Obispo","06079", "079"),
    ("San Mateo",      "06081", "081"),
    ("Santa Barbara",  "06083", "083"),
    ("Santa Clara",    "06085", "085"),
    ("Santa Cruz",     "06087", "087"),
    ("Shasta",         "06089", "089"),
    ("Sierra",         "06091", "091"),
    ("Siskiyou",       "06093", "093"),
    ("Solano",         "06095", "095"),
    ("Sonoma",         "06097", "097"),
    ("Stanislaus",     "06099", "099"),
    ("Sutter",         "06101", "101"),
    ("Tehama",         "06103", "103"),
    ("Trinity",        "06105", "105"),
    ("Tulare",         "06107", "107"),
    ("Tuolumne",       "06109", "109"),
    ("Ventura",        "06111", "111"),
    ("Yolo",           "06113", "113"),
    ("Yuba",           "06115", "115"),
]

COUNTY_DF = pd.DataFrame(COUNTIES, columns=["county", "fips", "county_fips"])

# ---------------------------------------------------------------------------
# BOE total secured assessed values: FY 2022-23, in $millions
# Source: CA BOE Annual Report 2022-23, "Summary of Locally Assessed Property Values"
# ---------------------------------------------------------------------------
BOE_AV_MILLIONS = {
    "001": 352_000,   # Alameda
    "003": 500,       # Alpine
    "005": 10_000,    # Amador
    "007": 25_000,    # Butte
    "009": 12_000,    # Calaveras
    "011": 7_000,     # Colusa
    "013": 249_000,   # Contra Costa
    "015": 3_000,     # Del Norte
    "017": 41_000,    # El Dorado
    "019": 69_000,    # Fresno
    "021": 5_000,     # Glenn
    "023": 18_000,    # Humboldt
    "025": 18_000,    # Imperial
    "027": 6_000,     # Inyo
    "029": 74_000,    # Kern
    "031": 12_000,    # Kings
    "033": 9_000,     # Lake
    "035": 4_000,     # Lassen
    "037": 1_797_000, # Los Angeles
    "039": 17_000,    # Madera
    "041": 87_000,    # Marin
    "043": 5_000,     # Mariposa
    "045": 18_000,    # Mendocino
    "047": 28_000,    # Merced
    "049": 2_000,     # Modoc
    "051": 8_000,     # Mono
    "053": 67_000,    # Monterey
    "055": 44_000,    # Napa
    "057": 26_000,    # Nevada
    "059": 719_000,   # Orange
    "061": 109_000,   # Placer
    "063": 5_000,     # Plumas
    "065": 263_000,   # Riverside
    "067": 194_000,   # Sacramento
    "069": 14_000,    # San Benito
    "071": 212_000,   # San Bernardino
    "073": 913_000,   # San Diego
    "075": 318_000,   # San Francisco
    "077": 94_000,    # San Joaquin
    "079": 70_000,    # San Luis Obispo
    "081": 302_000,   # San Mateo
    "083": 88_000,    # Santa Barbara
    "085": 704_000,   # Santa Clara
    "087": 75_000,    # Santa Cruz
    "089": 24_000,    # Shasta
    "091": 1_000,     # Sierra
    "093": 8_000,     # Siskiyou
    "095": 65_000,    # Solano
    "097": 103_000,   # Sonoma
    "099": 57_000,    # Stanislaus
    "101": 14_000,    # Sutter
    "103": 8_000,     # Tehama
    "105": 3_000,     # Trinity
    "107": 43_000,    # Tulare
    "109": 12_000,    # Tuolumne
    "111": 176_000,   # Ventura
    "113": 31_000,    # Yolo
    "115": 9_000,     # Yuba
}

# Approximate residential fraction of secured roll by county type
# Coastal/urban: higher residential %; rural/ag: lower residential %
RESIDENTIAL_FRACTION = {
    "001": 0.72, "003": 0.85, "005": 0.85, "007": 0.78, "009": 0.85,
    "011": 0.50, "013": 0.74, "015": 0.82, "017": 0.82, "019": 0.65,
    "021": 0.50, "023": 0.78, "025": 0.60, "027": 0.70, "029": 0.62,
    "031": 0.60, "033": 0.82, "035": 0.70, "037": 0.68, "039": 0.65,
    "041": 0.80, "043": 0.85, "045": 0.78, "047": 0.65, "049": 0.65,
    "051": 0.75, "053": 0.72, "055": 0.78, "057": 0.82, "059": 0.72,
    "061": 0.80, "063": 0.80, "065": 0.78, "067": 0.72, "069": 0.75,
    "071": 0.72, "073": 0.74, "075": 0.55, "077": 0.68, "079": 0.78,
    "081": 0.72, "083": 0.72, "085": 0.62, "087": 0.80, "089": 0.78,
    "091": 0.80, "093": 0.75, "095": 0.74, "097": 0.76, "099": 0.68,
    "101": 0.70, "103": 0.72, "105": 0.80, "107": 0.65, "109": 0.82,
    "111": 0.74, "113": 0.70, "115": 0.74,
}


def get_boe_data() -> pd.DataFrame:
    """Return BOE assessed value data merged with county reference table."""
    df = COUNTY_DF.copy()
    df["boe_total_av_millions"] = df["county_fips"].map(BOE_AV_MILLIONS)
    df["residential_fraction"] = df["county_fips"].map(RESIDENTIAL_FRACTION)
    df["boe_residential_av_millions"] = (
        df["boe_total_av_millions"] * df["residential_fraction"]
    )
    return df


def fetch_zillow_county_data() -> pd.DataFrame:
    """
    Download Zillow ZHVI (Single-Family + Condo, all tiers) county-level data.
    Returns DataFrame with columns: fips, zillow_median_value (most recent month).
    Falls back to embedded 2023 estimates on download failure.
    """
    url = (
        "https://files.zillowstatic.com/research/public_csvs/zhvi/"
        "County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
    )
    try:
        print("Downloading Zillow ZHVI county data ...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        raw = pd.read_csv(io.BytesIO(resp.content))
        # Keep CA only
        ca = raw[raw["StateCodeFIPS"] == 6].copy()
        # FIPS as zero-padded string
        ca["fips"] = (
            ca["StateCodeFIPS"].astype(str).str.zfill(2)
            + ca["MunicipalCodeFIPS"].astype(str).str.zfill(3)
        )
        # Most recent month column (last date column)
        date_cols = [c for c in ca.columns if c[:4].isdigit()]
        latest = date_cols[-1]
        print(f"  Using Zillow data through {latest}")
        result = ca[["fips", latest]].rename(columns={latest: "zillow_median_value"})
        return result.dropna(subset=["zillow_median_value"])
    except Exception as e:
        print(f"  Zillow download failed ({e}), using embedded fallback data.")
        return _zillow_fallback()


def _zillow_fallback() -> pd.DataFrame:
    """Embedded Zillow ZHVI estimates for CA counties, approximate 2023 values."""
    data = [
        ("06001", 900_000),   # Alameda
        ("06003", 450_000),   # Alpine
        ("06005", 380_000),   # Amador
        ("06007", 350_000),   # Butte
        ("06009", 380_000),   # Calaveras
        ("06011", 280_000),   # Colusa
        ("06013", 850_000),   # Contra Costa
        ("06015", 280_000),   # Del Norte
        ("06017", 530_000),   # El Dorado
        ("06019", 320_000),   # Fresno
        ("06021", 280_000),   # Glenn
        ("06023", 350_000),   # Humboldt
        ("06025", 230_000),   # Imperial
        ("06027", 320_000),   # Inyo
        ("06029", 290_000),   # Kern
        ("06031", 230_000),   # Kings
        ("06033", 320_000),   # Lake
        ("06035", 290_000),   # Lassen
        ("06037", 780_000),   # Los Angeles
        ("06039", 310_000),   # Madera
        ("06041", 1_500_000), # Marin
        ("06043", 360_000),   # Mariposa
        ("06045", 480_000),   # Mendocino
        ("06047", 310_000),   # Merced
        ("06049", 230_000),   # Modoc
        ("06051", 550_000),   # Mono
        ("06053", 720_000),   # Monterey
        ("06055", 830_000),   # Napa
        ("06057", 530_000),   # Nevada
        ("06059", 950_000),   # Orange
        ("06061", 680_000),   # Placer
        ("06063", 340_000),   # Plumas
        ("06065", 470_000),   # Riverside
        ("06067", 460_000),   # Sacramento
        ("06069", 630_000),   # San Benito
        ("06071", 400_000),   # San Bernardino
        ("06073", 790_000),   # San Diego
        ("06075", 1_250_000), # San Francisco
        ("06077", 420_000),   # San Joaquin
        ("06079", 720_000),   # San Luis Obispo
        ("06081", 1_650_000), # San Mateo
        ("06083", 900_000),   # Santa Barbara
        ("06085", 1_450_000), # Santa Clara
        ("06087", 1_050_000), # Santa Cruz
        ("06089", 340_000),   # Shasta
        ("06091", 380_000),   # Sierra
        ("06093", 280_000),   # Siskiyou
        ("06095", 490_000),   # Solano
        ("06097", 720_000),   # Sonoma
        ("06099", 380_000),   # Stanislaus
        ("06101", 340_000),   # Sutter
        ("06103", 270_000),   # Tehama
        ("06105", 310_000),   # Trinity
        ("06107", 270_000),   # Tulare
        ("06109", 360_000),   # Tuolumne
        ("06111", 780_000),   # Ventura
        ("06113", 510_000),   # Yolo
        ("06115", 330_000),   # Yuba
    ]
    return pd.DataFrame(data, columns=["fips", "zillow_median_value"])


def fetch_census_data() -> pd.DataFrame:
    """
    Fetch Census ACS 5-Year 2022 county-level data for California.
    Variables:
      B25003_002E: Owner-occupied housing units
      B19013_001E: Median household income
      B25077_001E: Median home value (owner-occupied)
    Returns DataFrame with columns: fips, owner_occupied_units, median_income, census_median_value.
    Falls back to embedded estimates on failure.
    """
    url = (
        "https://api.census.gov/data/2022/acs/acs5"
        "?get=NAME,B25003_002E,B19013_001E,B25077_001E"
        "&for=county:*&in=state:06"
    )
    try:
        print("Fetching Census ACS 5-Year 2022 data ...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        rows = resp.json()
        headers = rows[0]
        df = pd.DataFrame(rows[1:], columns=headers)
        df["fips"] = df["state"] + df["county"]
        df = df.rename(columns={
            "B25003_002E": "owner_occupied_units",
            "B19013_001E": "median_income",
            "B25077_001E": "census_median_value",
        })
        for col in ["owner_occupied_units", "median_income", "census_median_value"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[["fips", "owner_occupied_units", "median_income", "census_median_value"]]
    except Exception as e:
        print(f"  Census fetch failed ({e}), using embedded fallback data.")
        return _census_fallback()


def _census_fallback() -> pd.DataFrame:
    """Embedded Census ACS 2022 estimates for CA counties."""
    data = [
        # fips, owner_occ, median_income, census_median_value
        ("06001", 249_000, 109_000, 890_000),   # Alameda
        ("06003",     380,  58_000, 420_000),   # Alpine
        ("06005",   8_200,  63_000, 350_000),   # Amador
        ("06007",  55_000,  59_000, 330_000),   # Butte
        ("06009",  14_800,  62_000, 360_000),   # Calaveras
        ("06011",   3_600,  57_000, 260_000),   # Colusa
        ("06013", 231_000, 121_000, 830_000),   # Contra Costa
        ("06015",   5_200,  47_000, 260_000),   # Del Norte
        ("06017",  50_000,  80_000, 510_000),   # El Dorado
        ("06019", 171_000,  62_000, 300_000),   # Fresno
        ("06021",   3_100,  54_000, 270_000),   # Glenn
        ("06023",  28_000,  54_000, 330_000),   # Humboldt
        ("06025",  24_000,  52_000, 215_000),   # Imperial
        ("06027",   4_900,  54_000, 290_000),   # Inyo
        ("06029", 130_000,  65_000, 270_000),   # Kern
        ("06031",  18_000,  56_000, 215_000),   # Kings
        ("06033",  11_000,  50_000, 290_000),   # Lake
        ("06035",   7_000,  57_000, 270_000),   # Lassen
        ("06037", 862_000,  78_000, 760_000),   # Los Angeles
        ("06039",  27_000,  60_000, 295_000),   # Madera
        ("06041",  48_000, 128_000, 1_450_000), # Marin
        ("06043",   5_200,  54_000, 330_000),   # Mariposa
        ("06045",  19_000,  58_000, 460_000),   # Mendocino
        ("06047",  44_000,  60_000, 290_000),   # Merced
        ("06049",   2_000,  41_000, 210_000),   # Modoc
        ("06051",   4_500,  71_000, 540_000),   # Mono
        ("06053",  72_000,  80_000, 700_000),   # Monterey
        ("06055",  30_000, 102_000, 810_000),   # Napa
        ("06057",  26_000,  73_000, 510_000),   # Nevada
        ("06059", 597_000, 100_000, 940_000),   # Orange
        ("06061", 126_000,  98_000, 660_000),   # Placer
        ("06063",   5_400,  55_000, 320_000),   # Plumas
        ("06065", 448_000,  72_000, 460_000),   # Riverside
        ("06067", 327_000,  77_000, 440_000),   # Sacramento
        ("06069",  13_000,  85_000, 610_000),   # San Benito
        ("06071", 376_000,  68_000, 385_000),   # San Bernardino
        ("06073", 610_000,  91_000, 780_000),   # San Diego
        ("06075",  90_000, 136_000, 1_200_000), # San Francisco
        ("06077", 143_000,  72_000, 410_000),   # San Joaquin
        ("06079",  77_000,  82_000, 710_000),   # San Luis Obispo
        ("06081", 142_000, 139_000, 1_630_000), # San Mateo
        ("06083",  90_000,  87_000, 870_000),   # Santa Barbara
        ("06085", 422_000, 140_000, 1_430_000), # Santa Clara
        ("06087",  64_000,  96_000, 1_020_000), # Santa Cruz
        ("06089",  50_000,  57_000, 320_000),   # Shasta
        ("06091",     800,  56_000, 350_000),   # Sierra
        ("06093",  12_000,  47_000, 265_000),   # Siskiyou
        ("06095",  94_000,  83_000, 480_000),   # Solano
        ("06097", 120_000,  87_000, 710_000),   # Sonoma
        ("06099",  97_000,  66_000, 360_000),   # Stanislaus
        ("06101",  18_000,  63_000, 320_000),   # Sutter
        ("06103",  13_000,  52_000, 255_000),   # Tehama
        ("06105",   3_600,  46_000, 285_000),   # Trinity
        ("06107",  75_000,  56_000, 255_000),   # Tulare
        ("06109",  13_000,  54_000, 340_000),   # Tuolumne
        ("06111", 193_000,  96_000, 760_000),   # Ventura
        ("06113",  44_000,  82_000, 500_000),   # Yolo
        ("06115",  14_000,  63_000, 310_000),   # Yuba
    ]
    return pd.DataFrame(data, columns=["fips", "owner_occupied_units", "median_income", "census_median_value"])


def compute_tax_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived metrics to the merged DataFrame.

    Columns added:
      residential_av_millions    - BOE total AV × residential fraction
      market_value_millions      - Zillow median × owner-occupied units / 1e6
      assessment_ratio           - residential AV / market value (lower = more Prop 13 benefit)
      tax_gap_annual_millions    - (market value - residential AV) × 1.1%
      tax_gap_per_household      - annual gap / owner-occupied units
      tax_gap_pct_market         - gap as % of what full-rate taxes would be
    """
    df = df.copy()
    df["market_value_millions"] = (
        df["zillow_median_value"] * df["owner_occupied_units"] / 1_000_000
    )
    df["assessment_ratio"] = (
        df["boe_residential_av_millions"] / df["market_value_millions"]
    ).clip(upper=1.0)
    df["tax_gap_annual_millions"] = (
        (df["market_value_millions"] - df["boe_residential_av_millions"]) * 0.011
    ).clip(lower=0)
    df["tax_gap_per_household"] = (
        df["tax_gap_annual_millions"] * 1_000_000 / df["owner_occupied_units"]
    )
    df["tax_gap_pct_market"] = (
        (1 - df["assessment_ratio"]) * 100
    ).clip(lower=0)
    return df
