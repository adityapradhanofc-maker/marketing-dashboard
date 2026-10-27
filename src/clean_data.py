"""
Step 2: Clean the raw marketing dataset.

Run from the project root:
    python src/clean_data.py

Input : data/raw/marketing_data.csv
Output: data/clean/marketing_clean.csv
        docs/cleaning_log.txt  (what was fixed and how many rows)
"""
import os
import numpy as np
import pandas as pd

RAW = "data/raw/marketing_data.csv"
CLEAN = "data/clean/marketing_clean.csv"
LOG = "docs/cleaning_log.txt"

log_lines = []


def log(msg: str):
    print(msg)
    log_lines.append(msg)


def parse_dates(s: pd.Series) -> pd.Series:
    """Handle two formats: YYYY-MM-DD (ISO) and DD/MM/YYYY."""
    s = s.astype(str).str.strip()
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    dmy = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    return iso.fillna(dmy)


def main():
    df = pd.read_csv(RAW)
    log("=== DATA CLEANING LOG ===")
    log(f"Raw rows loaded: {len(df):,}")

    # ---- 1. Standardise dates ----
    n_slash = df["date"].astype(str).str.contains("/").sum()
    df["date"] = parse_dates(df["date"])
    bad_dates = df["date"].isna().sum()
    df = df.dropna(subset=["date"])
    log(f"\n[1] Dates: converted {n_slash:,} DD/MM/YYYY values to a single "
        f"format; dropped {bad_dates} unparseable rows")

    # ---- 2. Standardise text (channel, campaign) ----
    ch_before = df["channel"].nunique()
    camp_before = df["campaign"].nunique()
    for col in ["channel", "campaign"]:
        df[col] = df[col].astype(str).str.strip()
        key = df[col].str.lower()
        # canonical spelling = the most common spelling for each lowercase key
        canon = (df.assign(_k=key).groupby("_k")[col]
                   .agg(lambda x: x.value_counts().idxmax()))
        # prefer a spelling that is not all-lowercase / all-uppercase
        for k in canon.index:
            variants = df.loc[key == k, col].unique()
            good = [v for v in variants if v != v.lower() and v != v.upper()]
            if good:
                canon[k] = pd.Series(
                    df.loc[df[col].isin(good) & (key == k), col]
                ).value_counts().idxmax()
        df[col] = key.map(canon)
    log(f"\n[2] Text: channel spellings {ch_before} -> {df['channel'].nunique()}, "
        f"campaign spellings {camp_before} -> {df['campaign'].nunique()}")

    # ---- 3. Remove duplicates ----
    before = len(df)
    df = df.drop_duplicates()
    exact = before - len(df)
    before = len(df)
    df = df.drop_duplicates(subset=["date", "campaign"], keep="first")
    keyed = before - len(df)
    log(f"\n[3] Duplicates: removed {exact} exact duplicates and "
        f"{keyed} repeated date+campaign rows")

    # ---- 4. Fix impossible values ----
    neg = (df["spend"] < 0).sum()
    df.loc[df["spend"] < 0, "spend"] = df.loc[df["spend"] < 0, "spend"].abs()
    over = (df["clicks"] > df["impressions"]).sum()
    df.loc[df["clicks"] > df["impressions"], "clicks"] = np.nan
    log(f"\n[4] Invalid values: fixed {neg} negative spend values (sign error, "
        f"made positive); set {over} rows with clicks > impressions to missing "
        f"(re-filled in step 5)")

    # ---- 5. Fill missing values (campaign-level typical ratios) ----
    missing_before = df.isna().sum()
    g = df.groupby("campaign")

    def fill(col, ratio):
        """Fill col using the campaign's median ratio (ratio = col / base)."""
        base, num = ratio
        r = (df[num] / df[base]).replace([np.inf, -np.inf], np.nan)
        med = r.groupby(df["campaign"]).transform("median")
        df[col] = df[col].fillna(df[base] * med)

    # clicks from impressions, then conversions-aware floor
    r = df["clicks"] / df["impressions"]
    df["clicks"] = df["clicks"].fillna(
        df["impressions"] * r.groupby(df["campaign"]).transform("median"))
    df["clicks"] = np.maximum(df["clicks"], df["conversions"])

    # spend from clicks (cost per click)
    cpc = (df["spend"] / df["clicks"]).replace([np.inf, -np.inf], np.nan)
    df["spend"] = df["spend"].fillna(
        df["clicks"] * cpc.groupby(df["campaign"]).transform("median"))

    # revenue from conversions (revenue per conversion)
    rpc = (df["revenue"] / df["conversions"]).replace([np.inf, -np.inf], np.nan)
    df["revenue"] = df["revenue"].fillna(
        df["conversions"] * rpc.groupby(df["campaign"]).transform("median"))
    df["revenue"] = df["revenue"].fillna(0)  # conversions == 0 -> no revenue

    # engagement and reach from impressions
    for col in ["engagement", "reach"]:
        ratio = df[col] / df["impressions"]
        df[col] = df[col].fillna(
            df["impressions"] * ratio.groupby(df["campaign"]).transform("median"))

    log("\n[5] Missing values filled (using each campaign's own typical ratio):")
    for col in ["clicks", "spend", "revenue", "engagement", "reach"]:
        if missing_before[col] > 0:
            log(f"    - {col}: {int(missing_before[col])} filled")
    log("    Method: clicks from CTR, spend from cost-per-click, revenue from "
        "revenue-per-conversion, engagement/reach from impressions")

    # ---- 6. Final types and tidy-up ----
    for col in ["impressions", "clicks", "conversions", "engagement", "reach"]:
        df[col] = df[col].round().astype(int)
    for col in ["spend", "revenue"]:
        df[col] = df[col].round(2)
    df = df.sort_values(["date", "campaign"]).reset_index(drop=True)

    # ---- 7. Validation ----
    nulls = int(df.isna().sum().sum())
    dupes = int(df.duplicated().sum())
    log("\n[6] Validation checks:")
    log(f"    - Null values left: {nulls}")
    log(f"    - Duplicate rows left: {dupes}")
    log(f"    - Negative numbers left: {int((df.select_dtypes('number') < 0).sum().sum())}")
    log(f"    - Clicks > impressions: {int((df['clicks'] > df['impressions']).sum())}")
    log(f"    - Channels: {sorted(df['channel'].unique())}")
    log(f"    - Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    log(f"\nClean rows saved: {len(df):,}")

    os.makedirs("data/clean", exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    df.to_csv(CLEAN, index=False)
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print(f"\nSaved {CLEAN} and {LOG}")


if __name__ == "__main__":
    main()
