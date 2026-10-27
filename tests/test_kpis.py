"""
Step 8: Tests for KPI math, data quality and reports.

Run from the project root:
    pip install pytest
    python -m pytest tests/ -v
"""
import os
import sys

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.kpis import load_data, summarize, overall, funnel
from src.insights import build_insights, share_table
from src.reports import (campaign_report, monthly_report, channel_report,
                         marketing_summary, excel_report)


# ---------- tiny dataset with hand-calculated answers ----------
@pytest.fixture
def small():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2025-01-05", "2025-02-05"]),
        "campaign": ["Camp A", "Camp A"],
        "channel": ["Email", "Email"],
        "impressions": [1000, 1000],
        "clicks": [50, 150],
        "conversions": [5, 30],
        "spend": [500.0, 1500.0],
        "revenue": [2500.0, 2500.0],
        "engagement": [100, 100],
        "reach": [800, 800],
    })
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df


# ---------- KPI math ----------
def test_kpi_math_uses_sums(small):
    k = overall(small)
    assert k.spend == 2000
    assert k.revenue == 5000
    assert k.ctr == pytest.approx(10.0)             # 200 / 2000
    assert k.conversion_rate == pytest.approx(17.5)  # 35 / 200 (not 15)
    assert k.cpc == pytest.approx(10.0)             # 2000 / 200
    assert k.cpa == pytest.approx(2000 / 35)
    assert k.roi == pytest.approx(150.0)            # (5000-2000)/2000
    assert k.roas == pytest.approx(2.5)
    assert k.engagement_rate == pytest.approx(10.0)  # 200 / 2000


def test_summarize_by_month(small):
    m = summarize(small, "month").sort_values("month")
    assert len(m) == 2
    assert m.iloc[0]["roi"] == pytest.approx(400.0)   # (2500-500)/500
    assert m.iloc[1]["roas"] == pytest.approx(2500 / 1500)


def test_funnel_counts(small):
    fn = funnel(small)
    assert list(fn["count"]) == [2000, 200, 35]


# ---------- real data quality ----------
@pytest.fixture(scope="module")
def data():
    return load_data()


def test_no_nulls(data):
    assert data.isna().sum().sum() == 0


def test_no_duplicates(data):
    assert not data.duplicated().any()


def test_no_negative_numbers(data):
    cols = ["impressions", "clicks", "conversions", "spend", "revenue",
            "engagement", "reach"]
    assert (data[cols] >= 0).all().all()


def test_funnel_is_logical(data):
    assert (data["clicks"] <= data["impressions"]).all()
    assert (data["conversions"] <= data["clicks"]).all()


def test_expected_shape(data):
    assert data["channel"].nunique() == 6
    assert data["campaign"].nunique() >= 20
    assert len(data) > 1000


def test_channel_casing_consistent(data):
    assert (data["channel"] == data["channel"].str.strip()).all()
    assert data["channel"].nunique() == data["channel"].str.lower().nunique()


def test_channel_totals_match_overall(data):
    ch = summarize(data, "channel")
    k = overall(data)
    assert ch["spend"].sum() == pytest.approx(k.spend)
    assert ch["revenue"].sum() == pytest.approx(k.revenue)
    assert ch["conversions"].sum() == pytest.approx(k.conversions)


def test_campaign_channel_is_one_to_one(data):
    assert data.groupby("campaign")["channel"].nunique().max() == 1


# ---------- insights and reports ----------
def test_share_table_sums_to_100(data):
    s = share_table(data)
    assert s["spend_share"].sum() == pytest.approx(100)
    assert s["revenue_share"].sum() == pytest.approx(100)


def test_insights_text(data):
    t = build_insights(data)
    assert "Recommendations" in t
    assert "nan" not in t.lower()


def test_campaign_report(data):
    r = campaign_report(data)
    assert len(r) == data["campaign"].nunique()
    assert r["revenue_rank"].min() == 1
    assert r["revenue"].is_monotonic_decreasing


def test_monthly_report(data):
    r = monthly_report(data)
    assert len(r) == data["month"].nunique()
    assert pd.isna(r.iloc[0]["spend_mom_pct"])   # first month has no previous


def test_channel_report_sorted_by_roi(data):
    assert channel_report(data)["roi"].is_monotonic_decreasing


def test_summary_and_excel(data):
    assert "# Marketing Summary" in marketing_summary(data)
    x = excel_report(data)
    assert x[:2] == b"PK"   # xlsx files are zip files


def test_filtered_data_works(data):
    one = data[data["channel"] == data["channel"].iloc[0]]
    assert overall(one).spend == pytest.approx(one["spend"].sum())
    assert len(campaign_report(one)) == one["campaign"].nunique()
