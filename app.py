"""
Step 5: Marketing Performance Dashboard (Streamlit)

Run from the project root:
    streamlit run app.py
"""
import streamlit as st
import plotly.express as px

from src.kpis import load_data, summarize, overall, funnel
from src.insights import build_insights, share_table
from src.reports import (campaign_report, monthly_report, marketing_summary,
                         excel_report)

st.set_page_config(page_title="Marketing Performance Dashboard",
                   page_icon="📈", layout="wide")


@st.cache_data
def get_data():
    return load_data()


df = get_data()

# ---------------- Sidebar filters ----------------
st.sidebar.header("Filters")
d_min, d_max = df["date"].min().date(), df["date"].max().date()
date_range = st.sidebar.date_input("Date range", (d_min, d_max),
                                   min_value=d_min, max_value=d_max)
channels = st.sidebar.multiselect("Channel", sorted(df["channel"].unique()),
                                  default=sorted(df["channel"].unique()))
camp_options = sorted(df[df["channel"].isin(channels)]["campaign"].unique())
campaigns = st.sidebar.multiselect("Campaign", camp_options, default=camp_options)

if len(date_range) != 2:
    st.info("Pick both a start and an end date in the sidebar.")
    st.stop()

f = df[(df["date"].dt.date >= date_range[0]) & (df["date"].dt.date <= date_range[1])
       & df["channel"].isin(channels) & df["campaign"].isin(campaigns)]

st.title("📈 Marketing Performance Dashboard")
if f.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# ---------------- KPI cards ----------------
k = overall(f)
c = st.columns(6)
c[0].metric("Spend", f"₹{k.spend/1e6:,.2f}M")
c[1].metric("Revenue", f"₹{k.revenue/1e6:,.2f}M")
c[2].metric("ROI", f"{k.roi:,.0f}%")
c[3].metric("ROAS", f"{k.roas:.2f}x")
c[4].metric("CTR", f"{k.ctr:.2f}%")
c[5].metric("Conversion rate", f"{k.conversion_rate:.2f}%")
c = st.columns(4)
c[0].metric("Impressions", f"{k.impressions/1e6:,.2f}M")
c[1].metric("Conversions", f"{int(k.conversions):,}")
c[2].metric("Cost per acquisition", f"₹{k.cpa:,.0f}")
c[3].metric("Engagement rate", f"{k.engagement_rate:.2f}%")

# ---------------- Tabs ----------------
t1, t2, t3, t4, t5, t6 = st.tabs(["Trends", "Channels", "Campaigns", "Funnel",
                                   "Insights", "Reports"])

with t1:
    m = summarize(f, "month").sort_values("month")
    a, b = st.columns(2)
    a.plotly_chart(px.line(m, x="month", y=["spend", "revenue"], markers=True,
                           title="Monthly spend vs revenue",
                           labels={"value": "₹", "month": "", "variable": ""}),
                   use_container_width=True)
    b.plotly_chart(px.line(m, x="month", y="engagement_rate", markers=True,
                           title="Engagement rate trend (%)",
                           labels={"engagement_rate": "%", "month": ""}),
                   use_container_width=True)
    st.plotly_chart(px.bar(m, x="month", y="conversions",
                           title="Monthly conversions",
                           labels={"month": ""}), use_container_width=True)

with t2:
    ch = summarize(f, "channel").sort_values("roi", ascending=False)
    a, b = st.columns(2)
    a.plotly_chart(px.bar(ch, x="channel", y="roi", color="channel",
                          title="ROI by channel (%)", labels={"channel": ""})
                   .update_layout(showlegend=False), use_container_width=True)
    b.plotly_chart(px.bar(ch, x="channel", y="conversion_rate", color="channel",
                          title="Conversion rate by channel (%)",
                          labels={"channel": "", "conversion_rate": "%"})
                   .update_layout(showlegend=False), use_container_width=True)
    st.subheader("Channel comparison")
    st.dataframe(
        ch[["channel", "spend", "revenue", "ctr", "conversion_rate",
            "cpc", "cpa", "roi", "roas", "engagement_rate"]].round(2),
        use_container_width=True, hide_index=True)

with t3:
    cp = summarize(f, ["campaign", "channel"])
    metric = st.radio("Rank campaigns by", ["revenue", "roi", "conversions"],
                      horizontal=True)
    top = cp.sort_values(metric, ascending=False).head(10)
    st.plotly_chart(px.bar(top, x=metric, y="campaign", color="channel",
                           orientation="h", title=f"Top 10 campaigns by {metric}")
                    .update_layout(yaxis={"categoryorder": "total ascending"}),
                    use_container_width=True)
    st.dataframe(cp.sort_values("roi", ascending=False).round(2),
                 use_container_width=True, hide_index=True)

with t4:
    fn = funnel(f)
    st.plotly_chart(px.funnel(fn, x="count", y="stage",
                              title="Impressions → Clicks → Conversions"),
                    use_container_width=True)
    st.caption(f"{k.ctr:.2f}% of impressions became clicks; "
               f"{k.conversion_rate:.2f}% of clicks became conversions.")

with t5:
    st.header("Business insights")
    st.caption("Generated from the data currently selected in the sidebar.")
    st.markdown(build_insights(f))
    sh = share_table(f).melt(id_vars="channel",
                             value_vars=["spend_share", "revenue_share"],
                             var_name="measure", value_name="share")
    sh["measure"] = sh["measure"].map({"spend_share": "Share of spend",
                                       "revenue_share": "Share of revenue"})
    st.plotly_chart(px.bar(sh, x="channel", y="share", color="measure",
                           barmode="group", title="Spend share vs revenue share (%)",
                           labels={"share": "%", "channel": "", "measure": ""}),
                    use_container_width=True)

with t6:
    st.header("Download reports")
    st.caption("Reports use the filters currently selected in the sidebar.")
    st.download_button("📊 Full report (Excel, 4 sheets)", excel_report(f),
                       "marketing_report.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    a, b, c = st.columns(3)
    a.download_button("Campaign report (CSV)",
                      campaign_report(f).to_csv(index=False),
                      "campaign_report.csv", "text/csv")
    b.download_button("Monthly analytics report (CSV)",
                      monthly_report(f).to_csv(index=False),
                      "monthly_report.csv", "text/csv")
    c.download_button("Marketing summary (Markdown)", marketing_summary(f),
                      "marketing_summary.md", "text/markdown")
    st.subheader("Preview: monthly analytics report")
    st.dataframe(monthly_report(f), use_container_width=True, hide_index=True)

st.sidebar.caption("Data: self-generated marketing dataset (2025).")
