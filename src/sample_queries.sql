-- Sample SQL queries for the Marketing Performance Dashboard

-- 1. Total spend, revenue and ROI by channel
SELECT channel,
               ROUND(SUM(spend), 0)                                   AS total_spend,
               ROUND(SUM(revenue), 0)                                 AS total_revenue,
               ROUND((SUM(revenue) - SUM(spend)) * 100.0 / SUM(spend), 1) AS roi_pct
        FROM v_marketing
        GROUP BY channel
        ORDER BY roi_pct DESC;

-- 2. Top 5 campaigns by revenue
SELECT campaign, channel, ROUND(SUM(revenue), 0) AS total_revenue
        FROM v_marketing
        GROUP BY campaign, channel
        ORDER BY total_revenue DESC
        LIMIT 5;

-- 3. Monthly impressions and conversions
SELECT SUBSTR(date, 1, 7) AS month,
               SUM(impressions) AS impressions,
               SUM(conversions) AS conversions
        FROM v_marketing
        GROUP BY month
        ORDER BY month;

-- 4. Conversion rate (conversions / clicks) by channel
SELECT channel,
               ROUND(SUM(conversions) * 100.0 / SUM(clicks), 2) AS conversion_rate_pct
        FROM v_marketing
        GROUP BY channel
        ORDER BY conversion_rate_pct DESC;

-- 5. Campaigns with ROI above the overall average (high performers)
SELECT campaign, channel,
               ROUND((SUM(revenue) - SUM(spend)) * 100.0 / SUM(spend), 0) AS roi_pct
        FROM v_marketing
        GROUP BY campaign, channel
        HAVING roi_pct > (SELECT (SUM(revenue) - SUM(spend)) * 100.0 / SUM(spend)
                          FROM v_marketing)
        ORDER BY roi_pct DESC;
