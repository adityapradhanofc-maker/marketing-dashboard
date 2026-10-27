"""
Step 7: Report generation.

Three reports, all built from the (optionally filtered) data:
    campaign_report(df)   -> table, one row per campaign, with KPIs and rank
    monthly_report(df)    -> table, one row per month, with month-over-month change
    marketing_summary(df) -> markdown text (overview, channels, insights)
    excel_report(df)      -> bytes of one .xlsx workbook with all of the above

Run on its own to save all reports to reports/:
    python src/reports.py
"""
import io
import os
import pandas as pd

try:
    from src.kpis import load_data, summarize, overall
    from src.insights import build_insights
except ModuleNotFoundError:          # when run as a script
    from kpis import load_data, summarize, overall
    from insights import build_insights

KPI_COLS = ["spend", "revenue", "impressions", "clicks", "conversions",
            "ctr", "conversion_rate", "cpc", "cpa", "roi", "roas",
            "engagement_rate"]


def campaign_report(df: pd.DataFrame) -> pd.DataFrame:
    """One row per campaign, ranked by revenue."""
    t = summarize(df, ["campaign", "channel"]).sort_values("revenue", ascending=False)
    t.insert(0, "revenue_rank", range(1, len(t) + 1))
    t["roi_rank"] = t["roi"].rank(ascending=False, method="min").astype(int)
    return t[["revenue_rank", "roi_rank", "campaign", "channel"] + KPI_COLS].round(2)


def monthly_report(df: pd.DataFrame) -> pd.DataFrame:
    """One row per month with month-over-month % change."""
    t = summarize(df, "month").sort_values("month")
    for col in ["spend", "revenue", "conversions"]:
        t[f"{col}_mom_pct"] = t[col].pct_change() * 100
    t.insert(0, "month_label", t["month"].dt.strftime("%b %Y"))
    cols = ["month_label"] + KPI_COLS + [c for c in t.columns if c.endswith("_mom_pct")]
    return t[cols].round(2)


def channel_report(df: pd.DataFrame) -> pd.DataFrame:
    t = summarize(df, "channel").sort_values("roi", ascending=False)
    return t[["channel"] + KPI_COLS].round(2)


def marketing_summary(df: pd.DataFrame) -> str:
    """Executive summary in markdown."""
    if df.empty:
        return "No data for the selected filters."
    k = overall(df)
    ch = channel_report(df)
    lines = [
        "# Marketing Summary",
        f"*Period: {df['date'].min():%d %b %Y} to {df['date'].max():%d %b %Y} "
        f"| {df['campaign'].nunique()} campaigns | {df['channel'].nunique()} channels*",
        "",
        "## Headline KPIs",
        f"- Spend: ₹{k.spend:,.0f}",
        f"- Revenue: ₹{k.revenue:,.0f}",
        f"- ROI: {k.roi:,.0f}%  |  ROAS: {k.roas:.2f}x",
        f"- Impressions: {k.impressions:,.0f}  |  Clicks: {k.clicks:,.0f}  |  "
        f"Conversions: {k.conversions:,.0f}",
        f"- CTR: {k.ctr:.2f}%  |  Conversion rate: {k.conversion_rate:.2f}%",
        f"- CPC: ₹{k.cpc:.2f}  |  CPA: ₹{k.cpa:.2f}  |  "
        f"Engagement rate: {k.engagement_rate:.2f}%",
        "",
        "## Channel performance (ranked by ROI)",
        "| Channel | Spend (₹) | Revenue (₹) | Conv. rate % | CPA (₹) | ROI % |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in ch.itertuples():
        lines.append(f"| {r.channel} | {r.spend:,.0f} | {r.revenue:,.0f} | "
                     f"{r.conversion_rate:.2f} | {r.cpa:,.0f} | {r.roi:,.0f} |")
    lines += ["", "## Key insights", build_insights(df)]
    return "\n".join(lines) + "\n"


def excel_report(df: pd.DataFrame) -> bytes:
    """One workbook: Overview, Channels, Campaigns, Monthly."""
    k = overall(df)
    overview = pd.DataFrame({
        "metric": ["Spend", "Revenue", "ROI %", "ROAS", "Impressions", "Clicks",
                   "Conversions", "CTR %", "Conversion rate %", "CPC", "CPA",
                   "Engagement rate %"],
        "value": [k.spend, k.revenue, k.roi, k.roas, k.impressions, k.clicks,
                  k.conversions, k.ctr, k.conversion_rate, k.cpc, k.cpa,
                  k.engagement_rate]}).round(2)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        overview.to_excel(xw, sheet_name="Overview", index=False)
        channel_report(df).to_excel(xw, sheet_name="Channels", index=False)
        campaign_report(df).to_excel(xw, sheet_name="Campaigns", index=False)
        monthly_report(df).to_excel(xw, sheet_name="Monthly", index=False)
        for ws in xw.book.worksheets:            # readable column widths
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(width + 2, 30)
    return buf.getvalue()


def main():
    df = load_data()
    os.makedirs("reports", exist_ok=True)
    campaign_report(df).to_csv("reports/campaign_report.csv", index=False)
    monthly_report(df).to_csv("reports/monthly_report.csv", index=False)
    with open("reports/marketing_summary.md", "w", encoding="utf-8") as f:
        f.write(marketing_summary(df))
    with open("reports/marketing_report.xlsx", "wb") as f:
        f.write(excel_report(df))
    print("Saved to reports/: campaign_report.csv, monthly_report.csv, "
          "marketing_summary.md, marketing_report.xlsx")
    print("\n" + marketing_summary(df)[:900])


if __name__ == "__main__":
    main()
