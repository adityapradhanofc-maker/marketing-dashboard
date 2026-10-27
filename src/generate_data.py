"""
Step 1: Generate a realistic, deliberately messy marketing dataset.

Run from the project root:
    python src/generate_data.py

Output: data/raw/marketing_data.csv
"""
import os
import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

# ---------- Channel behaviour (rough, realistic ranges) ----------
# ctr = click-through rate, cvr = conversion rate (of clicks),
# cpc = cost per click (INR), aov = avg order value (INR),
# eng = engagement actions per impression
CHANNELS = {
    "Google Ads": dict(ctr=0.045, cvr=0.060, cpc=22, aov=2400, eng=0.020, reach=0.78),
    "Facebook":   dict(ctr=0.018, cvr=0.028, cpc=11, aov=1900, eng=0.060, reach=0.70),
    "Instagram":  dict(ctr=0.022, cvr=0.032, cpc=14, aov=2100, eng=0.085, reach=0.72),
    "Email":      dict(ctr=0.055, cvr=0.090, cpc=3,  aov=2600, eng=0.040, reach=0.95),
    "YouTube":    dict(ctr=0.012, cvr=0.020, cpc=9,  aov=1800, eng=0.050, reach=0.65),
    "LinkedIn":   dict(ctr=0.010, cvr=0.045, cpc=38, aov=4200, eng=0.030, reach=0.80),
}

# ---------- Campaigns (name, channel) ----------
CAMPAIGNS = [
    ("Summer Sale", "Google Ads"), ("Brand Search", "Google Ads"),
    ("Competitor Keywords", "Google Ads"), ("Shopping Ads Q4", "Google Ads"),
    ("New Arrivals", "Facebook"), ("Retargeting Push", "Facebook"),
    ("Diwali Offer", "Facebook"), ("Lookalike Audience", "Facebook"),
    ("Influencer Collab", "Instagram"), ("Reels Challenge", "Instagram"),
    ("Story Ads Spring", "Instagram"), ("Festive Giveaway", "Instagram"),
    ("Welcome Series", "Email"), ("Cart Abandonment", "Email"),
    ("Monthly Newsletter", "Email"), ("Loyalty Rewards", "Email"),
    ("Product Demo Video", "YouTube"), ("Brand Story", "YouTube"),
    ("Unboxing Series", "YouTube"), ("Tutorial Ads", "YouTube"),
    ("B2B Lead Gen", "LinkedIn"), ("Webinar Promo", "LinkedIn"),
    ("Thought Leadership", "LinkedIn"), ("Case Study Push", "LinkedIn"),
]

START = pd.Timestamp("2025-01-01")
END = pd.Timestamp("2025-12-31")


def build_clean_rows() -> pd.DataFrame:
    rows = []
    for name, channel in CAMPAIGNS:
        p = CHANNELS[channel]
        # each campaign runs for a random window
        length = int(rng.integers(150, 230))
        start = START + pd.Timedelta(days=int(rng.integers(0, 365 - length + 1)))
        days = pd.date_range(start, periods=length)
        days = days[days <= END]

        # campaign-specific quality multiplier (some campaigns are just better)
        quality = rng.normal(1.0, 0.25)
        quality = max(quality, 0.5)
        base_impr = rng.integers(8_000, 30_000)

        for d in days:
            # weekly + seasonal pattern (more activity in Oct-Dec festive season)
            weekday = 1.15 if d.weekday() < 5 else 0.85
            season = 1.35 if d.month in (10, 11, 12) else 1.0
            impressions = int(base_impr * weekday * season * rng.uniform(0.7, 1.3))

            ctr = max(p["ctr"] * quality * rng.normal(1, 0.15), 0.002)
            clicks = int(impressions * ctr)
            cvr = max(p["cvr"] * quality * rng.normal(1, 0.20), 0.002)
            conversions = int(rng.binomial(clicks, min(cvr, 0.5))) if clicks else 0
            spend = round(clicks * p["cpc"] * rng.normal(1, 0.12), 2)
            revenue = round(conversions * p["aov"] * rng.normal(1, 0.18), 2)
            engagement = int(impressions * p["eng"] * quality * rng.normal(1, 0.2))
            reach = int(impressions * p["reach"] * rng.uniform(0.9, 1.0))

            rows.append(
                dict(date=d, campaign=name, channel=channel,
                     impressions=impressions, clicks=clicks,
                     conversions=conversions, spend=spend,
                     revenue=revenue, engagement=max(engagement, 0),
                     reach=reach)
            )
    return pd.DataFrame(rows)


def make_messy(df: pd.DataFrame) -> pd.DataFrame:
    """Inject realistic data-quality problems for Step 2 to fix."""
    df = df.copy()
    n = len(df)

    # 1) Mixed date formats: ~6% as DD/MM/YYYY, rest ISO YYYY-MM-DD
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    idx = rng.choice(n, int(n * 0.06), replace=False)
    df.loc[idx, "date"] = pd.to_datetime(df.loc[idx, "date"]).dt.strftime("%d/%m/%Y")

    # 2) Inconsistent channel / campaign text (casing, extra spaces)
    idx = rng.choice(n, int(n * 0.08), replace=False)
    df.loc[idx, "channel"] = df.loc[idx, "channel"].str.lower()
    idx = rng.choice(n, int(n * 0.05), replace=False)
    df.loc[idx, "channel"] = "  " + df.loc[idx, "channel"].str.upper() + " "
    idx = rng.choice(n, int(n * 0.05), replace=False)
    df.loc[idx, "campaign"] = df.loc[idx, "campaign"].str.lower() + " "

    # 3) Missing values in numeric columns
    for col, frac in [("clicks", 0.03), ("spend", 0.025),
                      ("engagement", 0.04), ("revenue", 0.02),
                      ("reach", 0.02)]:
        idx = rng.choice(n, int(n * frac), replace=False)
        df.loc[idx, col] = np.nan

    # 4) A few impossible values (negative spend, clicks > impressions)
    idx = rng.choice(n, 8, replace=False)
    df.loc[idx, "spend"] = -df.loc[idx, "spend"].abs()
    idx = rng.choice(n, 6, replace=False)
    df.loc[idx, "clicks"] = df.loc[idx, "impressions"] + rng.integers(50, 500, 6)

    # 5) Exact duplicate rows (~2%)
    dupes = df.sample(int(n * 0.02), random_state=SEED)
    df = pd.concat([df, dupes], ignore_index=True)

    # shuffle so the mess isn't ordered
    return df.sample(frac=1, random_state=SEED).reset_index(drop=True)


def main():
    clean = build_clean_rows()
    messy = make_messy(clean)

    os.makedirs("data/raw", exist_ok=True)
    out = "data/raw/marketing_data.csv"
    messy.to_csv(out, index=False)

    print(f"Saved {out}")
    print(f"Rows: {len(messy):,}  |  Campaigns: {clean['campaign'].nunique()}"
          f"  |  Channels: {clean['channel'].nunique()}")
    print("\nMissing values per column:")
    print(messy.isna().sum()[lambda s: s > 0].to_string())
    print(f"\nExact duplicate rows: {messy.duplicated().sum()}")
    print(f"Distinct channel spellings: {messy['channel'].nunique()}")


if __name__ == "__main__":
    main()
