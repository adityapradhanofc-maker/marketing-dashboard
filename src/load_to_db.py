"""
Step 3: Load the clean dataset into a SQLite database.

Run from the project root:
    python src/load_to_db.py

Input : data/clean/marketing_clean.csv
Output: marketing.db
        src/sample_queries.sql (example SQL for your report)

Database design (3 tables + 1 view):
    channels(channel_id, channel_name)
    campaigns(campaign_id, campaign_name, channel_id)
    daily_performance(id, date, campaign_id, impressions, clicks,
                      conversions, spend, revenue, engagement, reach)
    v_marketing  -> flat view joining all three (used by KPIs + dashboard)
"""
import os
import sqlite3
import pandas as pd

CLEAN = "data/clean/marketing_clean.csv"
DB = "marketing.db"

SCHEMA = """
DROP VIEW  IF EXISTS v_marketing;
DROP TABLE IF EXISTS daily_performance;
DROP TABLE IF EXISTS campaigns;
DROP TABLE IF EXISTS channels;

CREATE TABLE channels (
    channel_id   INTEGER PRIMARY KEY,
    channel_name TEXT NOT NULL UNIQUE
);

CREATE TABLE campaigns (
    campaign_id   INTEGER PRIMARY KEY,
    campaign_name TEXT NOT NULL UNIQUE,
    channel_id    INTEGER NOT NULL REFERENCES channels(channel_id)
);

CREATE TABLE daily_performance (
    id           INTEGER PRIMARY KEY,
    date         TEXT    NOT NULL,          -- ISO format YYYY-MM-DD
    campaign_id  INTEGER NOT NULL REFERENCES campaigns(campaign_id),
    impressions  INTEGER NOT NULL,
    clicks       INTEGER NOT NULL,
    conversions  INTEGER NOT NULL,
    spend        REAL    NOT NULL,
    revenue      REAL    NOT NULL,
    engagement   INTEGER NOT NULL,
    reach        INTEGER NOT NULL
);

CREATE INDEX idx_perf_date     ON daily_performance(date);
CREATE INDEX idx_perf_campaign ON daily_performance(campaign_id);

CREATE VIEW v_marketing AS
SELECT  d.date, c.campaign_name AS campaign, ch.channel_name AS channel,
        d.impressions, d.clicks, d.conversions, d.spend, d.revenue,
        d.engagement, d.reach
FROM daily_performance d
JOIN campaigns c  ON c.campaign_id = d.campaign_id
JOIN channels  ch ON ch.channel_id = c.channel_id;
"""

SAMPLE_QUERIES = {
    "1. Total spend, revenue and ROI by channel": """
        SELECT channel,
               ROUND(SUM(spend), 0)                                   AS total_spend,
               ROUND(SUM(revenue), 0)                                 AS total_revenue,
               ROUND((SUM(revenue) - SUM(spend)) * 100.0 / SUM(spend), 1) AS roi_pct
        FROM v_marketing
        GROUP BY channel
        ORDER BY roi_pct DESC;
    """,
    "2. Top 5 campaigns by revenue": """
        SELECT campaign, channel, ROUND(SUM(revenue), 0) AS total_revenue
        FROM v_marketing
        GROUP BY campaign, channel
        ORDER BY total_revenue DESC
        LIMIT 5;
    """,
    "3. Monthly impressions and conversions": """
        SELECT SUBSTR(date, 1, 7) AS month,
               SUM(impressions) AS impressions,
               SUM(conversions) AS conversions
        FROM v_marketing
        GROUP BY month
        ORDER BY month;
    """,
    "4. Conversion rate (conversions / clicks) by channel": """
        SELECT channel,
               ROUND(SUM(conversions) * 100.0 / SUM(clicks), 2) AS conversion_rate_pct
        FROM v_marketing
        GROUP BY channel
        ORDER BY conversion_rate_pct DESC;
    """,
    "5. Campaigns with ROI above the overall average (high performers)": """
        SELECT campaign, channel,
               ROUND((SUM(revenue) - SUM(spend)) * 100.0 / SUM(spend), 0) AS roi_pct
        FROM v_marketing
        GROUP BY campaign, channel
        HAVING roi_pct > (SELECT (SUM(revenue) - SUM(spend)) * 100.0 / SUM(spend)
                          FROM v_marketing)
        ORDER BY roi_pct DESC;
    """,
}


def main():
    df = pd.read_csv(CLEAN)
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)

    # channels
    channels = (pd.DataFrame({"channel_name": sorted(df["channel"].unique())})
                  .reset_index(names="channel_id"))
    channels["channel_id"] += 1
    channels.to_sql("channels", con, if_exists="append", index=False)

    # campaigns
    camps = (df[["campaign", "channel"]].drop_duplicates()
               .sort_values("campaign").reset_index(drop=True))
    camps = camps.merge(channels, left_on="channel", right_on="channel_name")
    camps = (camps[["campaign", "channel_id"]]
             .rename(columns={"campaign": "campaign_name"})
             .reset_index(drop=True))
    camps.insert(0, "campaign_id", camps.index + 1)
    camps.to_sql("campaigns", con, if_exists="append", index=False)

    # daily performance
    perf = df.merge(camps, left_on="campaign", right_on="campaign_name")
    perf = perf[["date", "campaign_id", "impressions", "clicks", "conversions",
                 "spend", "revenue", "engagement", "reach"]]
    perf.to_sql("daily_performance", con, if_exists="append", index=False)
    con.commit()

    # ---- verify ----
    print(f"Created {DB}")
    for t in ["channels", "campaigns", "daily_performance"]:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n:,} rows")
    view_n = con.execute("SELECT COUNT(*) FROM v_marketing").fetchone()[0]
    assert view_n == len(df), "View row count does not match the clean CSV!"
    print(f"  v_marketing (view): {view_n:,} rows  [matches clean CSV]")

    # ---- run sample queries ----
    sql_text = ["-- Sample SQL queries for the Marketing Performance Dashboard\n"]
    for title, q in SAMPLE_QUERIES.items():
        print(f"\n--- {title} ---")
        print(pd.read_sql_query(q, con).to_string(index=False))
        sql_text.append(f"-- {title}\n{q.strip()}\n")
    with open("src/sample_queries.sql", "w", encoding="utf-8") as f:
        f.write("\n".join(sql_text))
    con.close()
    print("\nSaved src/sample_queries.sql")


if __name__ == "__main__":
    main()
