"""
Step 6: Business insights, generated from the data (so they stay correct
if the data or the dashboard filters change).

Used by the dashboard's Insights tab and runnable on its own:
    python src/insights.py   -> writes docs/insights.md
"""
import os
import pandas as pd
try:
    from src.kpis import load_data, summarize, overall   # when imported by app.py
except ModuleNotFoundError:
    from kpis import load_data, summarize, overall        # when run as a script


def share_table(df: pd.DataFrame) -> pd.DataFrame:
    """Each channel's share of spend vs share of revenue (%)."""
    ch = summarize(df, "channel")
    ch["spend_share"] = ch["spend"] / ch["spend"].sum() * 100
    ch["revenue_share"] = ch["revenue"] / ch["revenue"].sum() * 100
    return ch


def build_insights(df: pd.DataFrame) -> str:
    """Return the insights as markdown for the given (filtered) data."""
    if df.empty:
        return "No data for the selected filters."

    tot = overall(df)
    ch = share_table(df)
    cp = summarize(df, ["campaign", "channel"])
    m = summarize(df, "month").sort_values("month")
    out = []

    out.append(f"**Overview:** ₹{tot.spend/1e6:,.2f}M spend produced "
               f"₹{tot.revenue/1e6:,.2f}M revenue (ROI {tot.roi:,.0f}%, "
               f"ROAS {tot.roas:.1f}x) across {len(ch)} channel(s) and "
               f"{len(cp)} campaign(s).\n")

    # ---- 1. Best-performing campaigns ----
    out.append("### 1. Best-performing campaigns")
    top_roi = cp.sort_values("roi", ascending=False).head(3)
    top_rev = cp.sort_values("revenue", ascending=False).head(3)
    out.append("**Highest ROI:** " + "; ".join(
        f"{r.campaign} ({r.channel}) {r.roi:,.0f}%" for r in top_roi.itertuples()))
    out.append("\n**Highest revenue:** " + "; ".join(
        f"{r.campaign} ({r.channel}) ₹{r.revenue/1e6:,.1f}M"
        for r in top_rev.itertuples()))
    low = cp.sort_values("roi").head(3)
    out.append("\n**Weakest ROI:** " + "; ".join(
        f"{r.campaign} ({r.channel}) {r.roi:,.0f}%" for r in low.itertuples()) + "\n")

    # ---- 2. High-conversion channels ----
    out.append("### 2. High-conversion channels")
    by_cr = ch.sort_values("conversion_rate", ascending=False)
    best, worst = by_cr.iloc[0], by_cr.iloc[-1]
    out.append(f"- **{best.channel}** converts best: {best.conversion_rate:.2f}% of "
               f"clicks, at a CPA of ₹{best.cpa:,.0f}.")
    if len(by_cr) > 1:
        out.append(f"- **{worst.channel}** converts least: "
                   f"{worst.conversion_rate:.2f}% (CPA ₹{worst.cpa:,.0f}).")
        dear = ch.sort_values("cpa", ascending=False).iloc[0]
        out.append(f"- Most expensive customers: **{dear.channel}** "
                   f"(CPA ₹{dear.cpa:,.0f}).")
    out.append("")

    # ---- 3. Engagement trends ----
    out.append("### 3. Customer engagement trends")
    top_eng = ch.sort_values("engagement_rate", ascending=False).iloc[0]
    out.append(f"- Highest engagement rate: **{top_eng.channel}** "
               f"({top_eng.engagement_rate:.2f}% of impressions).")
    if len(m) >= 4:
        k = min(3, len(m) // 2)
        first, last = m["engagement_rate"].head(k).mean(), m["engagement_rate"].tail(k).mean()
        trend = "rose" if last > first else "fell"
        out.append(f"- Engagement rate {trend} from {first:.2f}% (first {k} months) "
                   f"to {last:.2f}% (last {k} months).")
        pk = m.loc[m["engagement_rate"].idxmax()]
        out.append(f"- Peak month: **{pk.month:%B %Y}** ({pk.engagement_rate:.2f}%).")
    out.append("")

    # ---- 4. Recommendations ----
    out.append("### 4. Recommendations")
    recs = []
    ch["gap"] = ch["revenue_share"] - ch["spend_share"]
    up = ch.sort_values("gap", ascending=False).iloc[0]
    if up.gap > 0:
        recs.append(f"**Shift budget towards {up.channel}.** It gets "
                    f"{up.spend_share:.0f}% of spend but earns {up.revenue_share:.0f}% "
                    f"of revenue.")
    down = ch.sort_values("gap").iloc[0]
    if down.gap < 0:
        recs.append(f"**Review spend on {down.channel}.** It takes "
                    f"{down.spend_share:.0f}% of spend but returns only "
                    f"{down.revenue_share:.0f}% of revenue; cut low-ROI campaigns "
                    f"before cutting the channel.")
    if len(low):
        w = low.iloc[0]
        recs.append(f"**Fix or pause {w.campaign} ({w.channel}).** It has the lowest "
                    f"ROI ({w.roi:,.0f}%); test new creatives or targeting first.")
    if len(ch) > 1 and top_eng.channel != best.channel:
        recs.append(f"**Turn {top_eng.channel} engagement into sales.** It leads on "
                    f"engagement ({top_eng.engagement_rate:.1f}%) but converts at only "
                    f"{ch.loc[ch.channel == top_eng.channel, 'conversion_rate'].iloc[0]:.1f}%; "
                    f"add clearer calls-to-action and shoppable links.")
    if len(ch) > 1:
        dear = ch.sort_values("cpa", ascending=False).iloc[0]
        recs.append(f"**Cut acquisition cost on {dear.channel}** "
                    f"(CPA ₹{dear.cpa:,.0f}) with tighter targeting and "
                    f"better landing pages.")
    for i, r in enumerate(recs[:5], 1):
        out.append(f"{i}. {r}")
    out.append("")
    out.append("*Note: figures come from a self-generated dataset (2025), so "
               "absolute ROI values are illustrative; the rankings and "
               "method are what matter.*")
    return "\n".join(out)


def main():
    df = load_data()
    os.makedirs("docs", exist_ok=True)
    text = "# Business Insights\n\n" + build_insights(df) + "\n"
    with open("docs/insights.md", "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print("Saved docs/insights.md")


if __name__ == "__main__":
    main()
