# Marketing Performance Dashboard

SkillOrbit Data Analytics Capstone. An interactive dashboard that tracks and compares marketing campaign performance across channels, with KPIs, business insights and downloadable reports.

**Live app:** _add your Streamlit Cloud link here_

## Features
- Sidebar filters: date range, channel, campaign
- KPI cards: Spend, Revenue, ROI, ROAS, CTR, Conversion Rate, CPC, CPA, Engagement Rate
- 6 tabs: Trends, Channels, Campaigns, Funnel, Insights, Reports
- Auto-generated business insights and recommendations (change with the filters)
- Report downloads: campaign report, monthly report, marketing summary, 4-sheet Excel workbook

## Tech stack
Python 3.10+, Pandas, NumPy, Plotly, Streamlit, SQLite, openpyxl, pytest

## Project structure
```
marketing-dashboard/
  app.py                  Streamlit dashboard
  marketing.db            SQLite database (keep it in the repo, the app reads it)
  requirements.txt
  src/
    generate_data.py      Step 1: creates the messy raw dataset
    clean_data.py         Step 2: cleans it, writes docs/cleaning_log.txt
    load_to_db.py         Step 3: builds marketing.db + sample SQL
    kpis.py               Step 4: KPI formulas and summary tables
    insights.py           Step 6: business insights text
    reports.py            Step 7: report generation
  data/raw/               marketing_data.csv (messy)
  data/clean/             marketing_clean.csv
  tests/test_kpis.py      Step 8: 18 tests
  reports/                generated report files
  docs/                   insights.md, cleaning_log.txt, project report
```

## How to run
```
pip install -r requirements.txt
streamlit run app.py
```
To rebuild everything from scratch (run from the project root, in this order):
```
python src/generate_data.py
python src/clean_data.py
python src/load_to_db.py
python src/kpis.py
python src/insights.py
python src/reports.py
```

## Run the tests
```
python -m pytest tests/ -v
```

## KPI definitions
All ratios are computed from sums, never by averaging row-level ratios.

| KPI | Formula |
|---|---|
| CTR | clicks / impressions |
| Conversion rate | conversions / clicks |
| CPC | spend / clicks |
| CPA | spend / conversions |
| ROI % | (revenue - spend) / spend x 100 |
| ROAS | revenue / spend |
| Engagement rate | engagement / impressions |

## Data note
The dataset is self-generated (4,503 clean rows, 6 channels, 24 campaigns, 2025) and deliberately messy before cleaning. Absolute values such as ROI are illustrative (Email looks unrealistically strong); the method and rankings are what matter.

## Deploy on Streamlit Cloud
1. Push this folder to a GitHub repo (include `marketing.db`; do not add it to `.gitignore`).
2. Go to share.streamlit.io, create a new app, pick the repo, set the main file to `app.py`.
3. Deploy and copy the link into this README.
