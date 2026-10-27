"""
Step 4: KPI calculations and summary tables.

Used by the dashboard (app.py) and runnable on its own:
    python src/kpis.py          -> prints summaries, saves CSVs to reports/

KPI definitions (ratios are computed from SUMS, never by averaging row ratios):
    CTR             = clicks / impressions
    Conversion Rate = conversions / clicks
    CPC             = spend / clicks
    CPA             = spend / conversions
    ROI %           = (revenue - spend) / spend * 100
    ROAS            = revenue / spend
    Engagement Rate = engagement / impressions
"""
import os
import sqlite3
import numpy as np
import pandas as pd

DB = "marketing.db"
SUM_COLS = ["impressions", "clicks", "conversions", "spend",
            "revenue", "engagement", "reach"]


def load_data(db_path: str = DB) -> pd.DataFrame:
    """Read the flat view from SQLite."""
    con = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM v_marketing", con, parse_dates=["date"])
    con.close()
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df


def _div(a, b):
    """Safe division: returns NaN instead of inf when b is 0."""
    return a / b.replace(0, np.nan)


def add_kpis(t: pd.DataFrame) -> pd.DataFrame:
    """Add KPI columns to a table of summed metrics."""
    t = t.copy()
    t["ctr"] = _div(t["clicks"], t["impressions"]) * 100
    t["conversion_rate"] = _div(t["conversions"], t["clicks"]) * 100
    t["cpc"] = _div(t["spend"], t["clicks"])
    t["cpa"] = _div(t["spend"], t["conversions"])
    t["roi"] = _div(t["revenue"] - t["spend"], t["spend"]) * 100
    t["roas"] = _div(t["revenue"], t["spend"])
    t["engagement_rate"] = _div(t["engagement"], t["impressions"]) * 100
    return t


def summarize(df: pd.DataFrame, by) -> pd.DataFrame:
    """Aggregate by one or more columns, then add KPIs."""
    return add_kpis(df.groupby(by, as_index=False)[SUM_COLS].sum())


def overall(df: pd.DataFrame) -> pd.Series:
    """Single-row totals + KPIs for the whole (filtered) dataset."""
    tot = df[SUM_COLS].sum().to_frame().T
    return add_kpis(tot).iloc[0]


def funnel(df: pd.DataFrame) -> pd.DataFrame:
    """Impressions -> Clicks -> Conversions."""
    s = df[["impressions", "clicks", "conversions"]].sum()
    return pd.DataFrame({"stage": ["Impressions", "Clicks", "Conversions"],
                         "count": [s["impressions"], s["clicks"], s["conversions"]]})


def _r(t):
    """Round numeric columns only (avoids warnings on date columns)."""
    return t.round({c: 2 for c in t.select_dtypes("number").columns})


def main():
    df = load_data()
    os.makedirs("reports", exist_ok=True)

    tot = overall(df)
    print("=== OVERALL KPIs ===")
    print(f"Spend: {tot.spend:,.0f} | Revenue: {tot.revenue:,.0f} | "
          f"ROI: {tot.roi:,.0f}% | ROAS: {tot.roas:.2f}x")
    print(f"CTR: {tot.ctr:.2f}% | Conv. rate: {tot.conversion_rate:.2f}% | "
          f"CPC: {tot.cpc:.2f} | CPA: {tot.cpa:.2f} | "
          f"Engagement rate: {tot.engagement_rate:.2f}%")

    tables = {
        "kpi_by_channel": summarize(df, "channel").sort_values("roi", ascending=False),
        "kpi_by_campaign": summarize(df, ["campaign", "channel"]).sort_values("roi", ascending=False),
        "kpi_by_month": summarize(df, "month").sort_values("month"),
    }
    for name, t in tables.items():
        _r(t).to_csv(f"reports/{name}.csv", index=False)
        print(f"\n--- {name} (saved to reports/{name}.csv) ---")
        cols = [c for c in t.columns if c in
                ("channel", "campaign", "month", "ctr", "conversion_rate", "cpa", "roi", "roas")]
        print(_r(t[cols]).head(8).to_string(index=False))


if __name__ == "__main__":
    main()
