"""Nifty 100 Financial Intelligence Platform - Interactive Streamlit Dashboard.

Sprint 4: Company Intelligence Dashboard & Valuation Engine
Module 5: Interactive Streamlit Dashboard
Screen 1: Home / Overview
Screen 2: Company Profile Tearsheet
Screen 3: Financial Screener (Sliders, Presets, Live Results, CSV Download)
Screen 4: Peer Comparison (20 Metrics Heatmap, Benchmark Gap Chart, Best-in-Class)
Screen 5: Sector Analytics (KPIs, Side-by-Side Universe Chart, Company Ranking, Leadership Heatmap)
Screen 6: Cash Flow Intelligence (FCF Health KPIs, Capital Allocation Donut, 10Y Deep-Dive, Top 10 FCF, Watch List)
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)

# File Paths
DEFAULT_DB_PATH = Path("db/nifty100.db")
SCREENER_OUTPUT_PATH = Path("screener_output.xlsx")
SCREENER_CONFIG_PATH = Path("screener_config.yaml")
RADAR_CHARTS_DIR = Path("reports/radar_charts")
CAPITAL_ALLOCATION_PATH = Path("data/processed/capital_allocation.csv")

SCREENS = [
    "🏠 Home / Overview",
    "🏢 Company Profile",
    "🔍 Financial Screener",
    "👥 Peer Comparison",
    "📊 Sector Analysis",
    "🗺️ Capital Allocation & Cash Flow",
    "📈 Trend Analysis",
    "📑 Annual Reports",
]

PEER_GROUPS = [
    "Automobiles",
    "Consumer Finance",
    "FMCG",
    "IT Services",
    "Life Insurance",
    "Oil & Gas",
    "Pharmaceuticals",
    "Power & Utilities",
    "Private Banks",
    "Public Sector Banks",
    "Steel",
]

SECTOR_OPTIONS = [
    "All Sectors (Universe Overview)",
    "Financials",
    "Consumer Discretionary",
    "Energy",
    "Industrials",
    "Materials",
    "Consumer Staples",
    "Healthcare",
    "Information Technology",
    "Communication Services",
    "Real Estate",
]

PATTERN_COLORS = {
    "Shareholder Returns": "#2E7D32",  # Forest Green
    "Reinvestor": "#0288D1",  # Cerulean Blue
    "Mixed": "#FBC02D",  # Amber Yellow
    "Growth Funded by Debt": "#FB8C00",  # Deep Orange
    "Liquidating Assets": "#8E24AA",  # Royal Purple
    "Distress Signal": "#D32F2F",  # Crimson Red
    "Pre-Revenue": "#78909C",  # Blue-Grey
    "Cash Accumulator": "#00897B",  # Teal
    "Insufficient Data": "#B0BEC5",  # Light Slate
}

PRESET_DEFINITIONS: dict[str, dict[str, float]] = {
    "Custom (Analyst Configured)": {
        "min_roe": 15.0,
        "max_de": 1.0,
        "min_fcf": 0.0,
        "min_opm": 15.0,
        "max_pe": 50.0,
        "min_revenue_cagr_3yr": 10.0,
        "min_pat_cagr_3yr": 15.0,
        "min_cfo_quality": 0.8,
        "max_capex_intensity": 10.0,
        "min_composite_score": 50.0,
    },
    "Quality Compounder": {
        "min_roe": 15.0,
        "max_de": 1.0,
        "min_fcf": 0.0,
        "min_opm": 10.0,
        "max_pe": 150.0,
        "min_revenue_cagr_3yr": 10.0,
        "min_pat_cagr_3yr": -50.0,
        "min_cfo_quality": 0.0,
        "max_capex_intensity": 50.0,
        "min_composite_score": 50.0,
    },
    "Value Pick": {
        "min_roe": 11.0,
        "max_de": 2.0,
        "min_fcf": -10000.0,
        "min_opm": 0.0,
        "max_pe": 20.0,
        "min_revenue_cagr_3yr": -50.0,
        "min_pat_cagr_3yr": -50.0,
        "min_cfo_quality": 0.0,
        "max_capex_intensity": 50.0,
        "min_composite_score": 40.0,
    },
    "Dividend Aristocrat": {
        "min_roe": 12.0,
        "max_de": 1.0,
        "min_fcf": 0.0,
        "min_opm": 0.0,
        "max_pe": 150.0,
        "min_revenue_cagr_3yr": -50.0,
        "min_pat_cagr_3yr": -50.0,
        "min_cfo_quality": 0.0,
        "max_capex_intensity": 50.0,
        "min_composite_score": 40.0,
    },
    "Growth Rocket": {
        "min_roe": 0.0,
        "max_de": 5.0,
        "min_fcf": -10000.0,
        "min_opm": 15.0,
        "max_pe": 150.0,
        "min_revenue_cagr_3yr": 20.0,
        "min_pat_cagr_3yr": 20.0,
        "min_cfo_quality": 0.0,
        "max_capex_intensity": 50.0,
        "min_composite_score": 45.0,
    },
    "Asset Light Champion": {
        "min_roe": 15.0,
        "max_de": 0.5,
        "min_fcf": 0.0,
        "min_opm": 15.0,
        "max_pe": 150.0,
        "min_revenue_cagr_3yr": -50.0,
        "min_pat_cagr_3yr": -50.0,
        "min_cfo_quality": 0.0,
        "max_capex_intensity": 3.0,
        "min_composite_score": 50.0,
    },
    "Financial Health": {
        "min_roe": 0.0,
        "max_de": 0.5,
        "min_fcf": 0.0,
        "min_opm": 0.0,
        "max_pe": 150.0,
        "min_revenue_cagr_3yr": -50.0,
        "min_pat_cagr_3yr": -50.0,
        "min_cfo_quality": 0.8,
        "max_capex_intensity": 50.0,
        "min_composite_score": 50.0,
    },
}

TOP_STRATEGIC_METRICS = [
    "ROE",
    "ROCE",
    "Revenue CAGR 3yr",
    "OPM",
    "Composite Score",
]


# ==============================================================================
# DATABASE LOADERS & CACHING
# ==============================================================================


@st.cache_data(ttl=600)
def load_query(
    query: str,
    params: tuple[Any, ...] = (),
    db_path: Path | str = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Execute a read query against the SQLite database and return a DataFrame."""
    resolved_db = Path(db_path)
    if not resolved_db.exists():
        fallback = Path(__file__).resolve().parents[2] / "db" / "nifty100.db"
        if fallback.exists():
            resolved_db = fallback
        else:
            logger.error("Database not found at %s", resolved_db)
            return pd.DataFrame()

    try:
        with sqlite3.connect(resolved_db) as conn:
            return pd.read_sql_query(query, conn, params=params)
    except sqlite3.Error as exc:
        logger.error("Query failed: %s | Error: %s", query, exc)
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_screener_summary() -> pd.DataFrame:
    """Load the pre-computed screener summary with composite scores and preset matches."""
    resolved_screener = SCREENER_OUTPUT_PATH
    if not resolved_screener.exists():
        fallback = Path(__file__).resolve().parents[2] / "screener_output.xlsx"
        if fallback.exists():
            resolved_screener = fallback

    if resolved_screener.exists():
        try:
            return pd.read_excel(resolved_screener, sheet_name="Summary")
        except (OSError, ValueError, KeyError) as exc:
            logger.error("Failed to read screener_output.xlsx: %s", exc)

    sql = """
        SELECT c.id as company_id, c.company_name, s.broad_sector
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id;
    """
    return load_query(sql)


@st.cache_data(ttl=600)
def load_universe_snapshot() -> pd.DataFrame:
    """Load latest snapshot ratios joined with company metadata and composite scores."""
    sql = """
        SELECT 
            c.id as company_id,
            c.company_name,
            c.company_logo,
            c.about_company,
            c.website,
            s.broad_sector,
            s.sub_sector,
            fr.year,
            fr.return_on_equity_pct,
            fr.return_on_capital_employed_pct,
            fr.operating_profit_margin_pct,
            fr.net_profit_margin_pct,
            fr.debt_to_equity,
            fr.high_leverage_flag,
            fr.interest_coverage,
            fr.icr_risk_flag,
            fr.free_cash_flow_cr,
            fr.cash_from_operations_cr,
            fr.fcf_conversion_rate_pct,
            fr.revenue_cagr_3yr,
            fr.pat_cagr_3yr,
            fr.cfo_quality_score,
            fr.cfo_quality_label,
            fr.capex_intensity_pct,
            fr.capex_label,
            fr.capital_allocation_pattern,
            fr.extreme_magnitude_flag,
            mc.pe_ratio,
            mc.pb_ratio,
            mc.market_cap_crore
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT * FROM financial_ratios 
            WHERE year LIKE '%-03' 
            GROUP BY company_id 
            HAVING year = MAX(year)
        ) fr ON c.id = fr.company_id
        LEFT JOIN (
            SELECT * FROM market_cap 
            WHERE year LIKE '%-03' 
            GROUP BY company_id 
            HAVING year = MAX(year)
        ) mc ON c.id = mc.company_id;
    """
    df = load_query(sql)
    summary_df = load_screener_summary()

    if not summary_df.empty and "composite_ranking_score" in summary_df.columns:
        df = df.merge(
            summary_df[
                ["company_id", "composite_ranking_score", "in_quality_compounder"]
            ],
            on="company_id",
            how="left",
        )
    else:
        df["composite_ranking_score"] = None
        df["in_quality_compounder"] = 0

    return df


@st.cache_data(ttl=600)
def load_company_peer_info(company_id: str) -> dict[str, Any]:
    """Load peer group metadata and classifications for a specific company."""
    sql = """
        SELECT pg.peer_group_name, pg.is_benchmark, pp.metric_name, pp.classification, pp.percentile_rank
        FROM peer_groups pg
        LEFT JOIN peer_percentiles pp ON pg.peer_group_name = pp.peer_group_name AND pg.company_id = pp.company_id
        WHERE pg.company_id = ?;
    """
    df = load_query(sql, params=(company_id,))
    if df.empty:
        return {
            "peer_group_name": None,
            "is_benchmark": False,
            "classifications": {},
        }

    peer_group = df["peer_group_name"].iloc[0]
    is_benchmark = bool(df["is_benchmark"].iloc[0] == 1)
    class_counts = df["classification"].value_counts().to_dict()

    return {
        "peer_group_name": peer_group,
        "is_benchmark": is_benchmark,
        "classifications": class_counts,
    }


@st.cache_data(ttl=600)
def load_peer_group_metrics(peer_group_name: str) -> pd.DataFrame:
    """Load all 20 metrics and percentiles for a peer group."""
    sql = """
        SELECT 
            pp.company_id, 
            c.company_name,
            pp.metric_name, 
            pp.metric_value, 
            pp.percentile_rank, 
            pp.classification, 
            pp.benchmark_gap_pct,
            pg.is_benchmark
        FROM peer_percentiles pp
        JOIN companies c ON pp.company_id = c.id
        JOIN peer_groups pg ON pp.peer_group_name = pg.peer_group_name AND pp.company_id = pg.company_id
        WHERE pp.peer_group_name = ?
        ORDER BY pp.metric_name ASC, pp.company_id ASC;
    """
    return load_query(sql, params=(peer_group_name,))


@st.cache_data(ttl=600)
def load_capital_allocation_patterns() -> pd.DataFrame:
    """Load capital allocation pattern history and filter to latest year per company."""
    resolved_path = CAPITAL_ALLOCATION_PATH
    if not resolved_path.exists():
        fallback = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "processed"
            / "capital_allocation.csv"
        )
        if fallback.exists():
            resolved_path = fallback

    if not resolved_path.exists():
        logger.warning("capital_allocation.csv not found at %s", resolved_path)
        return pd.DataFrame()

    try:
        df = pd.read_csv(resolved_path)
        return df
    except (OSError, ValueError, KeyError) as exc:
        logger.error("Failed to load capital_allocation.csv: %s", exc)
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_company_cashflow_history(company_id: str) -> pd.DataFrame:
    """Load 10-year historical cashflow breakdown for a specific company."""
    sql = """
        SELECT year, operating_activity, investing_activity, financing_activity, net_cash_flow
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year ASC;
    """
    return load_query(sql, params=(company_id,))


@st.cache_data(ttl=600)
def load_peer_classifications_by_sector() -> pd.DataFrame:
    """Load distribution of Best in Class, In Line, and Watch List by broad sector."""
    sql = """
        SELECT pp.company_id, s.broad_sector, pp.classification, COUNT(*) as cnt
        FROM peer_percentiles pp
        JOIN sectors s ON pp.company_id = s.company_id
        GROUP BY pp.company_id, s.broad_sector, pp.classification;
    """
    return load_query(sql)


@st.cache_data(ttl=600)
def load_historical_stress_records() -> pd.DataFrame:
    """Load all records where ICR < 1.5 (icr_risk_flag=1) and FCF < 0."""
    sql = """
        SELECT 
            fr.company_id,
            c.company_name,
            s.broad_sector,
            fr.year,
            fr.interest_coverage,
            fr.free_cash_flow_cr,
            fr.icr_risk_flag
        FROM financial_ratios fr
        JOIN companies c ON fr.company_id = c.id
        LEFT JOIN sectors s ON fr.company_id = s.company_id
        WHERE fr.icr_risk_flag IN (1, '1', 'True') AND fr.free_cash_flow_cr < 0
        ORDER BY fr.year DESC, fr.free_cash_flow_cr ASC;
    """
    return load_query(sql)


# ==============================================================================
# SIDEBAR NAVIGATION & CONTROLS
# ==============================================================================


def render_sidebar(
    universe_df: pd.DataFrame,
) -> tuple[str, str, dict[str, float], str, str, str]:
    """Render sidebar branding, screen navigation, and screen-specific controls."""
    st.sidebar.markdown(
        """
        <div style="text-align: center; padding-bottom: 12px;">
            <h2 style="margin: 0; color: #1E88E5; font-weight: 700; letter-spacing: 1px;">BLUESTOCK</h2>
            <p style="font-size: 0.85rem; color: #90A4AE; margin-top: 2px;">
                N100 Financial Intelligence Platform
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Navigation")
    selected_screen = st.sidebar.radio(
        label="Select Screen",
        options=SCREENS,
        index=0,
        label_visibility="collapsed",
    )

    selected_ticker = "TCS"
    screener_thresholds: dict[str, float] = {}
    selected_peer_group = "IT Services"
    selected_sector = "All Sectors (Universe Overview)"
    selected_cf_ticker = "TCS"

    # Screen 2: Company Profile Selector
    if selected_screen == "🏢 Company Profile":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Company Selector")
        sorted_cos = universe_df.sort_values(by="company_name")
        company_options = [
            f"{row['company_name']} ({row['company_id']})"
            for _, row in sorted_cos.iterrows()
        ]
        default_idx = 0
        for idx, opt in enumerate(company_options):
            if "(TCS)" in opt:
                default_idx = idx
                break

        chosen_option = st.sidebar.selectbox(
            "Search or select company:",
            options=company_options,
            index=default_idx,
        )
        if chosen_option:
            selected_ticker = chosen_option.split("(")[-1].replace(")", "").strip()

    # Screen 3: Financial Screener Sliders & Preset Selector
    elif selected_screen == "🔍 Financial Screener":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Screener Presets")

        preset_choice = st.sidebar.selectbox(
            "Choose a Preset Template:",
            options=list(PRESET_DEFINITIONS.keys()),
            index=1,  # Default to Quality Compounder
        )

        # Check if preset changed to auto-populate slider defaults
        if st.session_state.get("active_preset") != preset_choice:
            st.session_state["active_preset"] = preset_choice
            target_preset = PRESET_DEFINITIONS[preset_choice]
            for key, val in target_preset.items():
                st.session_state[f"slider_{key}"] = float(val)

        st.sidebar.markdown("---")
        st.sidebar.subheader("Filter Sliders (10 Criteria)")

        curr = PRESET_DEFINITIONS.get(
            preset_choice, PRESET_DEFINITIONS["Custom (Analyst Configured)"]
        )

        min_roe = st.sidebar.slider(
            "Min ROE (%)",
            min_value=0.0,
            max_value=50.0,
            value=float(st.session_state.get("slider_min_roe", curr["min_roe"])),
            step=1.0,
            key="slider_min_roe",
        )
        max_de = st.sidebar.slider(
            "Max Debt-to-Equity (x)",
            min_value=0.0,
            max_value=5.0,
            value=float(st.session_state.get("slider_max_de", curr["max_de"])),
            step=0.1,
            key="slider_max_de",
        )
        min_fcf = st.sidebar.slider(
            "Min Free Cash Flow (₹ Cr)",
            min_value=-5000.0,
            max_value=10000.0,
            value=float(st.session_state.get("slider_min_fcf", curr["min_fcf"])),
            step=500.0,
            key="slider_min_fcf",
        )
        min_opm = st.sidebar.slider(
            "Min Operating Margin (%)",
            min_value=0.0,
            max_value=50.0,
            value=float(st.session_state.get("slider_min_opm", curr["min_opm"])),
            step=1.0,
            key="slider_min_opm",
        )
        max_pe = st.sidebar.slider(
            "Max P/E Multiple (x)",
            min_value=5.0,
            max_value=150.0,
            value=float(st.session_state.get("slider_max_pe", curr["max_pe"])),
            step=5.0,
            key="slider_max_pe",
        )
        min_rev_cagr = st.sidebar.slider(
            "Min Revenue CAGR 3Y (%)",
            min_value=-20.0,
            max_value=50.0,
            value=float(
                st.session_state.get(
                    "slider_min_revenue_cagr_3yr", curr["min_revenue_cagr_3yr"]
                )
            ),
            step=1.0,
            key="slider_min_revenue_cagr_3yr",
        )
        min_pat_cagr = st.sidebar.slider(
            "Min PAT CAGR 3Y (%)",
            min_value=-20.0,
            max_value=50.0,
            value=float(
                st.session_state.get(
                    "slider_min_pat_cagr_3yr", curr["min_pat_cagr_3yr"]
                )
            ),
            step=1.0,
            key="slider_min_pat_cagr_3yr",
        )
        min_cfo_q = st.sidebar.slider(
            "Min CFO Quality Score (0–1)",
            min_value=0.0,
            max_value=1.0,
            value=float(
                st.session_state.get("slider_min_cfo_quality", curr["min_cfo_quality"])
            ),
            step=0.05,
            key="slider_min_cfo_quality",
        )
        max_capex = st.sidebar.slider(
            "Max CapEx Intensity (%)",
            min_value=0.0,
            max_value=30.0,
            value=float(
                st.session_state.get(
                    "slider_max_capex_intensity", curr["max_capex_intensity"]
                )
            ),
            step=1.0,
            key="slider_max_capex_intensity",
        )
        min_comp_score = st.sidebar.slider(
            "Min Composite Score (0–100)",
            min_value=0.0,
            max_value=100.0,
            value=float(
                st.session_state.get(
                    "slider_min_composite_score", curr["min_composite_score"]
                )
            ),
            step=5.0,
            key="slider_min_composite_score",
        )

        screener_thresholds = {
            "min_roe": min_roe,
            "max_de": max_de,
            "min_fcf": min_fcf,
            "min_opm": min_opm,
            "max_pe": max_pe,
            "min_revenue_cagr_3yr": min_rev_cagr,
            "min_pat_cagr_3yr": min_pat_cagr,
            "min_cfo_quality": min_cfo_q,
            "max_capex_intensity": max_capex,
            "min_composite_score": min_comp_score,
        }

    # Screen 4: Peer Group Selector
    elif selected_screen == "👥 Peer Comparison":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Peer Group Selector")
        selected_peer_group = st.sidebar.selectbox(
            "Choose a Peer Group (11 Groups):",
            options=PEER_GROUPS,
            index=3,  # Default to IT Services
        )

    # Screen 5: Sector Selector
    elif selected_screen == "📊 Sector Analysis":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Sector Selector")
        selected_sector = st.sidebar.selectbox(
            "Choose Broad Sector (11 Options):",
            options=SECTOR_OPTIONS,
            index=0,  # Default to All Sectors
        )

    # Screen 6: Cash Flow Deep Dive Selector
    elif selected_screen == "🗺️ Capital Allocation & Cash Flow":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Cash Flow Deep-Dive")
        sorted_cos = universe_df.sort_values(by="company_name")
        cf_options = [
            f"{row['company_name']} ({row['company_id']})"
            for _, row in sorted_cos.iterrows()
        ]
        default_cf_idx = 0
        for idx, opt in enumerate(cf_options):
            if "(TCS)" in opt:
                default_cf_idx = idx
                break

        chosen_cf = st.sidebar.selectbox(
            "Select Company for Cash Flow History:",
            options=cf_options,
            index=default_cf_idx,
        )
        if chosen_cf:
            selected_cf_ticker = chosen_cf.split("(")[-1].replace(")", "").strip()

    st.sidebar.markdown("---")
    st.sidebar.caption("Institutional Intelligence Engine | Sprint 4 (Days 22–28)")

    return (
        selected_screen,
        selected_ticker,
        screener_thresholds,
        selected_peer_group,
        selected_sector,
        selected_cf_ticker,
    )


# ==============================================================================
# SCREEN 1: HOME / OVERVIEW
# ==============================================================================


def render_home_screen(universe_df: pd.DataFrame) -> None:
    """SCREEN 1: Home / Overview dashboard."""
    st.title("📈 Executive Overview & Universe Health")
    st.markdown(
        "Institutional analytics covering **92 NSE Nifty 100 constituents** across fundamentals, "
        "valuation multiples, and solvency risk metrics."
    )

    st.markdown("---")

    # 1. 4 KPI Tiles at top
    total_companies = len(universe_df)
    clean_roe = universe_df.loc[
        universe_df["extreme_magnitude_flag"] != 1, "return_on_equity_pct"
    ].dropna()
    avg_roe = clean_roe.mean() if not clean_roe.empty else 0.0

    clean_pe = universe_df["pe_ratio"].dropna()
    median_pe = clean_pe.median() if not clean_pe.empty else 0.0

    qc_count = int(universe_df["in_quality_compounder"].fillna(0).sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Total Companies",
        f"{total_companies}",
        help="Full Nifty 100 constituent coverage",
    )
    col2.metric(
        "Average ROE",
        f"{avg_roe:.1f}%",
        help="Universe mean ROE (scale-error neutralized)",
    )
    col3.metric(
        "Median P/E Multiple",
        f"{median_pe:.1f}x",
        help="Median Price-to-Earnings ratio",
    )
    col4.metric(
        "Quality Compounders",
        f"{qc_count}",
        help="Companies passing strict ROE > 15%, D/E < 1.0, FCF > 0 preset",
    )

    st.markdown("---")

    # 2. Sector Distribution Chart & Market Pulse Summary
    chart_col, pulse_col = st.columns([0.65, 0.35])

    with chart_col:
        st.subheader("📊 Sector Distribution (Broad Sectors)")
        sector_counts = (
            universe_df["broad_sector"]
            .fillna("Unassigned")
            .value_counts()
            .reset_index()
        )
        sector_counts.columns = ["broad_sector", "company_count"]

        fig_sector = px.bar(
            sector_counts,
            x="company_count",
            y="broad_sector",
            orientation="h",
            color="company_count",
            color_continuous_scale="Teal",
            labels={"company_count": "Number of Companies", "broad_sector": "Sector"},
        )
        fig_sector.update_layout(
            margin={"l": 0, "r": 20, "t": 20, "b": 20},
            height=340,
            yaxis={"autorange": "reversed"},
            coloraxis_showscale=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_sector, use_container_width=True)

    with pulse_col:
        st.subheader("💓 Market Pulse Summary")
        pos_fcf_count = int((universe_df["free_cash_flow_cr"] > 0).sum())
        clean_de = universe_df["debt_to_equity"].dropna()
        low_de_count = int((clean_de < 1.0).sum())
        high_lev_count = int((universe_df["high_leverage_flag"] == 1).sum())

        st.markdown(
            f"""
            <div style="background-color: #1e2638; padding: 18px; border-radius: 8px; border: 1px solid #2d3748;">
                <p style="margin: 0; font-size: 0.95rem;"><strong>Positive Free Cash Flow:</strong></p>
                <h3 style="margin: 2px 0 10px 0; color: #4CAF50;">{pos_fcf_count} / {total_companies} companies</h3>
                <p style="margin: 0; font-size: 0.95rem;"><strong>Solvent Balance Sheets (D/E &lt; 1.0):</strong></p>
                <h3 style="margin: 2px 0 10px 0; color: #2196F3;">{low_de_count} / {total_companies} companies</h3>
                <p style="margin: 0; font-size: 0.95rem;"><strong>High Leverage Watch Flag:</strong></p>
                <h3 style="margin: 2px 0 0 0; color: #FF9800;">{high_lev_count} companies flagged</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 3. Top 10 Companies by Composite Ranking Score Table
    st.subheader("🏆 Top 10 Companies by Composite Ranking Score")
    st.markdown(
        "Multi-pillar percentile ranking across Profitability (35%), Cash Quality (30%), Growth (20%), and Solvency (15%)."
    )

    top_10 = (
        universe_df.sort_values(by="composite_ranking_score", ascending=False)
        .head(10)
        .copy()
    )

    display_cols = [
        "company_id",
        "company_name",
        "broad_sector",
        "composite_ranking_score",
        "return_on_equity_pct",
        "revenue_cagr_3yr",
    ]
    top_10_display = top_10[display_cols].rename(
        columns={
            "company_id": "Ticker",
            "company_name": "Company Name",
            "broad_sector": "Sector",
            "composite_ranking_score": "Composite Score",
            "return_on_equity_pct": "ROE (%)",
            "revenue_cagr_3yr": "Revenue CAGR 3Y (%)",
        }
    )

    st.dataframe(
        top_10_display.style.format(
            {
                "Composite Score": "{:.1f}",
                "ROE (%)": "{:.1f}%",
                "Revenue CAGR 3Y (%)": "{:.1f}%",
            },
            na_rep="—",
        ).background_gradient(subset=["Composite Score"], cmap="Blues"),
        use_container_width=True,
        hide_index=True,
    )


# ==============================================================================
# SCREEN 2: COMPANY PROFILE TEARSHEET
# ==============================================================================


def render_company_profile_screen(universe_df: pd.DataFrame, ticker: str) -> None:
    """SCREEN 2: Company Profile Tearsheet."""
    comp_series = universe_df[universe_df["company_id"] == ticker]
    if comp_series.empty:
        st.error(f"Company '{ticker}' not found in universe snapshot.")
        return

    comp = comp_series.iloc[0]
    company_name = comp["company_name"]
    sector = comp.get("broad_sector", "General")
    sub_sector = comp.get("sub_sector", "N/A")
    website = comp.get("website", "")
    about = comp.get(
        "about_company",
        "Detailed corporate background available in annual disclosures.",
    )
    logo_url = comp.get("company_logo", "")

    # 1. Header Section: Name, Ticker, Sector, Logo, Website
    head_col1, head_col2 = st.columns([0.8, 0.2])
    with head_col1:
        st.title(f"{company_name} ({ticker})")
        st.markdown(
            f"**Sector:** `{sector}` &nbsp;|&nbsp; **Industry / Sub-Sector:** `{sub_sector}`"
        )
        if pd.notna(website) and str(website).strip():
            st.markdown(f"🌐 [Official Website]({website})")
    with head_col2:
        if pd.notna(logo_url) and str(logo_url).startswith("http"):
            st.image(logo_url, width=120)

    st.markdown("---")

    # 2. 4 KPI Tiles: Latest ROE, ROCE, D/E, Composite Score
    roe_val = comp.get("return_on_equity_pct")
    roce_val = comp.get("return_on_capital_employed_pct")
    de_val = comp.get("debt_to_equity")
    score_val = comp.get("composite_ranking_score")
    extreme_flag = comp.get("extreme_magnitude_flag") == 1

    if extreme_flag:
        roe_display = "N/A*"
        roe_help = "Neutralized: Source balance sheet data scale error (~100x)."
        roce_display = "N/A*"
        roce_help = "Neutralized: Source balance sheet data scale error (~100x)."
    elif sector == "Financials" and pd.isna(roce_val):
        roe_display = f"{roe_val:.1f}%" if pd.notna(roe_val) else "—"
        roe_help = "Return on Equity (Latest March snapshot)."
        roce_display = "N/A (Bank/NBFC)"
        roce_help = (
            "ROCE is structurally inapplicable for banking and finance templates."
        )
    else:
        roe_display = f"{roe_val:.1f}%" if pd.notna(roe_val) else "—"
        roe_help = "Return on Equity (Latest March snapshot)."
        roce_display = f"{roce_val:.1f}%" if pd.notna(roce_val) else "—"
        roce_help = "Return on Capital Employed (Latest March snapshot)."

    if sector == "Financials" and pd.isna(de_val):
        de_display = "N/A (Bank)"
        de_help = "Standard D/E is not applicable for banking business models."
    else:
        de_display = f"{de_val:.2f}x" if pd.notna(de_val) else "—"
        de_help = "Debt-to-Equity ratio (Latest March snapshot)."

    if pd.notna(score_val):
        score_display = f"{score_val:.1f} / 100"
        score_help = "Composite percentile ranking score across 4 pillars."
    else:
        score_display = "N/A (Neutralized)"
        score_help = (
            "Excluded from ranking due to source scale error or missing cash flow."
        )

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Return on Equity (ROE)", roe_display, help=roe_help)
    kpi2.metric("Return on Capital Employed (ROCE)", roce_display, help=roce_help)
    kpi3.metric("Debt-to-Equity (D/E)", de_display, help=de_help)
    kpi4.metric("Composite Ranking Score", score_display, help=score_help)

    if extreme_flag:
        st.warning(
            "⚠️ **Data Quality Notice:** Source balance sheet equity capital and reserves for "
            f"`{ticker}` contain a verified ~100x scale error in raw filings. All balance sheet ratios "
            "have been actively neutralized to protect analytical integrity."
        )

    st.markdown("---")

    # 3. About Company & Radar Chart Overlay
    desc_col, radar_col = st.columns([0.55, 0.45])

    with desc_col:
        st.subheader("📖 Business Overview")
        st.write(
            about
            if pd.notna(about)
            else "Corporate business summary currently being indexed."
        )

        st.markdown("##### 📌 Key Valuation & Growth Snapshot")
        pe_val = comp.get("pe_ratio")
        pb_val = comp.get("pb_ratio")
        rev_cagr = comp.get("revenue_cagr_3yr")
        fcf_val = comp.get("free_cash_flow_cr")

        snap1, snap2 = st.columns(2)
        snap1.metric("P/E Multiple", f"{pe_val:.1f}x" if pd.notna(pe_val) else "—")
        snap1.metric("P/B Multiple", f"{pb_val:.1f}x" if pd.notna(pb_val) else "—")
        snap2.metric(
            "Revenue CAGR 3Y", f"{rev_cagr:.1f}%" if pd.notna(rev_cagr) else "—"
        )
        snap2.metric(
            "Free Cash Flow", f"₹{fcf_val:,.0f} Cr" if pd.notna(fcf_val) else "—"
        )

    with radar_col:
        st.subheader("🎯 8-Axis Peer Radar Chart")
        st.markdown("Percentile rank vs. peer group / sector distribution.")

        radar_file = RADAR_CHARTS_DIR / f"{ticker}_radar.png"
        if not radar_file.exists():
            radar_file = (
                Path(__file__).resolve().parents[2]
                / "reports"
                / "radar_charts"
                / f"{ticker}_radar.png"
            )

        if radar_file.exists():
            st.image(
                str(radar_file),
                caption=f"Intra-Industry Percentile Profile: {ticker}",
                use_container_width=True,
            )
        else:
            st.info(f"Radar visualization artifact not found at `{radar_file}`.")

    st.markdown("---")

    # 4. Peer Group Badge & Classification Breakdown
    st.subheader("👥 Peer Group Benchmarking & Performance Badges")

    peer_info = load_company_peer_info(ticker)
    group_name = peer_info["peer_group_name"]
    is_benchmark = peer_info["is_benchmark"]
    classes = peer_info["classifications"]

    if group_name:
        b_col1, b_col2 = st.columns([0.45, 0.55])
        with b_col1:
            st.markdown(f"#### Peer Group: **`{group_name}`**")
            if is_benchmark:
                st.success("🏆 **Designated Industry Benchmark Leader**")
            else:
                st.info(
                    "Direct intra-group competitor within dedicated 11-member peer group."
                )

        with b_col2:
            st.markdown("##### 20-Metric Classification Breakdown:")
            c_best = classes.get("Best in Class", 0)
            c_line = classes.get("In Line", 0)
            c_watch = classes.get("Watch List", 0)

            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("🟢 Best in Class", f"{c_best} metrics")
            m_col2.metric("🟡 In Line", f"{c_line} metrics")
            m_col3.metric("🔴 Watch List", f"{c_watch} metrics")
    else:
        st.info(
            f"ℹ️ **Broad Sector Benchmark:** `{company_name}` belongs to **{sector}** broad sector distribution "
            "rather than one of the 11 high-homogeneity peer groups. Benchmarking evaluates sector-level percentiles."
        )


# ==============================================================================
# SCREEN 3: FINANCIAL SCREENER
# ==============================================================================


def render_financial_screener_screen(
    universe_df: pd.DataFrame, thresholds: dict[str, float]
) -> None:
    """SCREEN 3: Multi-Criteria Financial Screener Screen."""
    st.title("🔍 Multi-Criteria Fundamental Screener")
    st.markdown(
        "Filter and rank all 92 Nifty 100 companies using 10 custom institutional thresholds "
        "or instant production screener presets."
    )

    st.markdown("---")

    df = universe_df.copy()
    mask = pd.Series(True, index=df.index)

    # 1. ROE (strict null exclusion)
    if thresholds.get("min_roe", 0.0) > 0.0:
        mask &= (
            pd.to_numeric(df["return_on_equity_pct"], errors="coerce")
            >= thresholds["min_roe"]
        )

    # 2. D/E (strict null exclusion)
    if thresholds.get("max_de", 5.0) < 5.0:
        mask &= (
            pd.to_numeric(df["debt_to_equity"], errors="coerce") <= thresholds["max_de"]
        )

    # 3. FCF (strict null exclusion)
    if thresholds.get("min_fcf", -5000.0) > -5000.0:
        mask &= (
            pd.to_numeric(df["free_cash_flow_cr"], errors="coerce")
            >= thresholds["min_fcf"]
        )

    # 4. OPM (strict null exclusion)
    if thresholds.get("min_opm", 0.0) > 0.0:
        mask &= (
            pd.to_numeric(df["operating_profit_margin_pct"], errors="coerce")
            >= thresholds["min_opm"]
        )

    # 5. P/E (strict null exclusion)
    if thresholds.get("max_pe", 150.0) < 150.0:
        mask &= pd.to_numeric(df["pe_ratio"], errors="coerce") <= thresholds["max_pe"]

    # 6. Revenue CAGR 3Y
    if thresholds.get("min_revenue_cagr_3yr", -20.0) > -20.0:
        mask &= (
            pd.to_numeric(df["revenue_cagr_3yr"], errors="coerce")
            >= thresholds["min_revenue_cagr_3yr"]
        )

    # 7. PAT CAGR 3Y
    if thresholds.get("min_pat_cagr_3yr", -20.0) > -20.0:
        mask &= (
            pd.to_numeric(df["pat_cagr_3yr"], errors="coerce")
            >= thresholds["min_pat_cagr_3yr"]
        )

    # 8. CFO Quality Score
    if thresholds.get("min_cfo_quality", 0.0) > 0.0:
        mask &= (
            pd.to_numeric(df["cfo_quality_score"], errors="coerce")
            >= thresholds["min_cfo_quality"]
        )

    # 9. CapEx Intensity
    if thresholds.get("max_capex_intensity", 30.0) < 30.0:
        mask &= (
            pd.to_numeric(df["capex_intensity_pct"], errors="coerce")
            <= thresholds["max_capex_intensity"]
        )

    # 10. Composite Score
    if thresholds.get("min_composite_score", 0.0) > 0.0:
        mask &= (
            pd.to_numeric(df["composite_ranking_score"], errors="coerce")
            >= thresholds["min_composite_score"]
        )

    filtered_df = (
        df[mask].sort_values(by="composite_ranking_score", ascending=False).copy()
    )
    match_count = len(filtered_df)

    # 1. Matching Count Banner and Export Button
    banner_col, export_col = st.columns([0.75, 0.25])
    with banner_col:
        st.subheader(f"🎯 **{match_count}** companies match your criteria")
        st.caption(
            f"Universe of {len(df)} companies filtered across 10 active parameters."
        )

    with export_col:
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Filtered CSV",
            data=csv_data,
            file_name="n100_screener_filtered_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # 2. Integrity Exclusion Check (SBIN, BEL, HAL)
    flagged_cos = [
        c for c in ["SBIN", "BEL", "HAL"] if c in filtered_df["company_id"].values
    ]
    if flagged_cos:
        st.warning(
            f"⚠️ **Integrity Notice:** The following companies with known ratio caveats appear in results: `{flagged_cos}`. "
            "Verify whether their balance sheet ratios or banking templates satisfy institutional constraints."
        )
    else:
        st.success(
            "🛡️ **Integrity Verification:** High-risk caveat companies (`SBIN` [banking template], "
            "`BEL`, and `HAL` [neutralized balance sheet scale errors]) are strictly excluded from current constraints."
        )

    st.markdown("---")

    # 3. Live Results Table
    if not filtered_df.empty:
        display_cols = [
            "company_id",
            "company_name",
            "broad_sector",
            "composite_ranking_score",
            "return_on_equity_pct",
            "return_on_capital_employed_pct",
            "operating_profit_margin_pct",
            "debt_to_equity",
            "free_cash_flow_cr",
            "revenue_cagr_3yr",
            "pe_ratio",
        ]
        table_df = filtered_df[display_cols].rename(
            columns={
                "company_id": "Ticker",
                "company_name": "Company Name",
                "broad_sector": "Sector",
                "composite_ranking_score": "Composite Score",
                "return_on_equity_pct": "ROE (%)",
                "return_on_capital_employed_pct": "ROCE (%)",
                "operating_profit_margin_pct": "OPM (%)",
                "debt_to_equity": "D/E (x)",
                "free_cash_flow_cr": "FCF (₹ Cr)",
                "revenue_cagr_3yr": "Revenue CAGR 3Y (%)",
                "pe_ratio": "P/E Multiple",
            }
        )

        st.dataframe(
            table_df.style.format(
                {
                    "Composite Score": "{:.1f}",
                    "ROE (%)": "{:.1f}%",
                    "ROCE (%)": "{:.1f}%",
                    "OPM (%)": "{:.1f}%",
                    "D/E (x)": "{:.2f}x",
                    "FCF (₹ Cr)": "₹{:,.0f}",
                    "Revenue CAGR 3Y (%)": "{:.1f}%",
                    "P/E Multiple": "{:.1f}x",
                },
                na_rep="—",
            ).background_gradient(subset=["Composite Score"], cmap="Blues"),
            use_container_width=True,
            height=500,
        )
    else:
        st.info(
            "No companies in the N100 universe met all selected filter criteria simultaneously. Try loosening thresholds."
        )


# ==============================================================================
# SCREEN 4: PEER COMPARISON
# ==============================================================================


def render_peer_comparison_screen(peer_group_name: str) -> None:
    """SCREEN 4: Peer Comparison Screen with Heatmap & Benchmark Gap Analysis."""
    st.title(f"👥 Peer Group Comparison: {peer_group_name}")
    st.markdown(
        f"Comparative matrix and intra-industry benchmarking across all member companies in the **`{peer_group_name}`** cluster."
    )

    st.markdown("---")

    peer_df = load_peer_group_metrics(peer_group_name)
    if peer_df.empty:
        st.warning(f"No peer percentile data located for group '{peer_group_name}'.")
        return

    bench_series = peer_df[peer_df["is_benchmark"] == 1]
    bench_id = bench_series["company_id"].iloc[0] if not bench_series.empty else None
    bench_name = (
        bench_series["company_name"].iloc[0] if not bench_series.empty else "None"
    )

    meta_col1, meta_col2 = st.columns([0.6, 0.4])
    with meta_col1:
        st.markdown(
            f"#### Designated Benchmark Leader: **{bench_id}** ({bench_name}) 🏆"
        )
        st.caption(
            "Benchmark gap percentage measures performance divergence relative to this industry anchor."
        )
    with meta_col2:
        st.metric(
            "Total Peers in Group", f"{peer_df['company_id'].nunique()} companies"
        )

    st.markdown("---")

    # 1. 20-Metric Comparative Matrix with Color Scale (replicates peer_comparison.xlsx)
    st.subheader("📋 20-Metric Comparative Matrix (Heatmap)")
    st.caption(
        "Color gradient scaled per metric row: Green = Top Performer, Yellow = Median, Red = Lagging Performer."
    )

    piv_val = peer_df.pivot(
        index="metric_name", columns="company_id", values="metric_value"
    )

    column_renames = {
        cid: f"{cid} 🏆 (Benchmark)" if cid == bench_id else cid
        for cid in piv_val.columns
    }
    piv_display = piv_val.rename(columns=column_renames)

    styler = piv_display.style.background_gradient(cmap="RdYlGn", axis=1).format(
        "{:.2f}", na_rep="—"
    )

    st.dataframe(
        styler,
        use_container_width=True,
        height=560,
    )

    st.markdown("---")

    # 2. Benchmark Gap Chart (Top 5 Core Metrics)
    st.subheader("📊 Benchmark Gap Analysis (Top 5 Strategic Metrics)")
    st.markdown(
        "Percentage variance relative to the benchmark leader (0.0%) for **ROE, ROCE, "
        "Revenue CAGR 3Y, OPM, and Composite Score**."
    )

    gap_df = peer_df[peer_df["metric_name"].isin(TOP_STRATEGIC_METRICS)].copy()
    gap_df = gap_df[gap_df["benchmark_gap_pct"].notna()]

    if not gap_df.empty:
        fig_gap = px.bar(
            gap_df,
            x="metric_name",
            y="benchmark_gap_pct",
            color="company_id",
            barmode="group",
            labels={
                "metric_name": "Key Strategic Metric",
                "benchmark_gap_pct": "Benchmark Gap (%)",
                "company_id": "Company",
            },
        )
        fig_gap.update_layout(
            margin={"l": 20, "r": 20, "t": 30, "b": 20},
            height=420,
            xaxis_title="Strategic Metric",
            yaxis_title="Gap vs Benchmark (%)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_gap, use_container_width=True)
    else:
        st.info(
            "No non-null benchmark gaps recorded for strategic metrics in this peer group."
        )

    st.markdown("---")

    # 3. Best-in-Class Leadership Summary
    st.subheader("⭐ 'Best in Class' Leadership Breakdown")
    st.markdown(
        r"Identifies which companies achieve the $\ge 75$th percentile rank across the 20 evaluated dimensions."
    )

    best_df = peer_df[peer_df["classification"] == "Best in Class"].sort_values(
        by=["company_id", "metric_name"]
    )

    if not best_df.empty:
        companies_in_group = peer_df["company_id"].unique()
        b_cols = st.columns(min(len(companies_in_group), 4))

        for col_idx, cid in enumerate(sorted(companies_in_group)):
            c_metrics = best_df[best_df["company_id"] == cid]["metric_name"].tolist()
            c_name = peer_df[peer_df["company_id"] == cid]["company_name"].iloc[0]
            with b_cols[col_idx % len(b_cols)]:
                badge = " 🏆 (Benchmark)" if cid == bench_id else ""
                st.markdown(f"##### **{cid}**{badge}")
                st.caption(f"{c_name}")
                if c_metrics:
                    st.success(
                        f"**{len(c_metrics)} Best-in-Class Metrics:**\n\n"
                        + "\n".join([f"• {m}" for m in c_metrics])
                    )
                else:
                    st.info(r"No metric currently in $\ge 75$th percentile.")
    else:
        st.info(
            "No metrics currently classified as 'Best in Class' in this peer group."
        )


# ==============================================================================
# SCREEN 5: SECTOR ANALYTICS & CROSS-INDUSTRY BENCHMARKING
# ==============================================================================


def render_sector_analytics_screen(
    universe_df: pd.DataFrame, selected_sector: str
) -> None:
    """SCREEN 5: Sector Analytics & Cross-Industry Benchmarking."""
    st.title("📊 Sector Analytics & Cross-Industry Benchmarking")
    st.markdown(
        "Macro sector performance summaries, cross-industry fundamental benchmarks, "
        "and constituent company rankings across the 10 Nifty 100 broad sectors."
    )

    st.markdown("---")

    # 1. Sector Selector Dropdown
    sec_col1, sec_col2 = st.columns([0.65, 0.35])
    with sec_col1:
        chosen_sec = st.selectbox(
            "Select Broad Sector to Analyze (11 Options):",
            options=SECTOR_OPTIONS,
            index=(
                SECTOR_OPTIONS.index(selected_sector)
                if selected_sector in SECTOR_OPTIONS
                else 0
            ),
        )

    # Filter universe for selected sector
    is_all_sectors = chosen_sec == "All Sectors (Universe Overview)"
    if is_all_sectors:
        target_df = universe_df.copy()
        sector_title = "Full Universe (All Sectors)"
    else:
        target_df = universe_df[universe_df["broad_sector"] == chosen_sec].copy()
        sector_title = chosen_sec

    # Universe averages (excluding verified scale error)
    u_clean = universe_df[universe_df["extreme_magnitude_flag"] != 1]
    u_avg_roe = u_clean["return_on_equity_pct"].dropna().mean()
    u_avg_opm = u_clean["operating_profit_margin_pct"].dropna().mean()
    u_avg_rev_cagr = u_clean["revenue_cagr_3yr"].dropna().mean()
    u_med_de = u_clean["debt_to_equity"].dropna().median()

    # Sector averages
    s_clean = target_df[target_df["extreme_magnitude_flag"] != 1]
    s_avg_roe = (
        s_clean["return_on_equity_pct"].dropna().mean()
        if not s_clean["return_on_equity_pct"].dropna().empty
        else 0.0
    )
    s_avg_opm = (
        s_clean["operating_profit_margin_pct"].dropna().mean()
        if not s_clean["operating_profit_margin_pct"].dropna().empty
        else 0.0
    )
    s_avg_rev_cagr = (
        s_clean["revenue_cagr_3yr"].dropna().mean()
        if not s_clean["revenue_cagr_3yr"].dropna().empty
        else 0.0
    )
    s_med_de = (
        s_clean["debt_to_equity"].dropna().median()
        if not s_clean["debt_to_equity"].dropna().empty
        else 0.0
    )
    sector_company_count = len(target_df)

    # Peer classifications for this sector
    peer_class_df = load_peer_classifications_by_sector()
    if is_all_sectors:
        sec_bic = int(
            peer_class_df[peer_class_df["classification"] == "Best in Class"][
                "cnt"
            ].sum()
        )
        sec_wl = int(
            peer_class_df[peer_class_df["classification"] == "Watch List"]["cnt"].sum()
        )
    else:
        sec_rows = peer_class_df[peer_class_df["broad_sector"] == chosen_sec]
        sec_bic = (
            int(sec_rows[sec_rows["classification"] == "Best in Class"]["cnt"].sum())
            if not sec_rows.empty
            else 0
        )
        sec_wl = (
            int(sec_rows[sec_rows["classification"] == "Watch List"]["cnt"].sum())
            if not sec_rows.empty
            else 0
        )

    with sec_col2:
        st.metric(
            label="Sector Constituents",
            value=f"{sector_company_count} Companies",
            delta=f"{(sector_company_count / len(universe_df) * 100):.1f}% of Universe",
        )

    # 2. Sector KPI Summary (5 Tiles)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(
        "Avg ROE",
        f"{s_avg_roe:.1f}%",
        delta=f"{(s_avg_roe - u_avg_roe):+.1f}% vs Univ",
        help="Average Return on Equity across sector constituents",
    )
    k2.metric(
        "Avg OPM",
        f"{s_avg_opm:.1f}%",
        delta=f"{(s_avg_opm - u_avg_opm):+.1f}% vs Univ",
        help="Average Operating Profit Margin",
    )
    k3.metric(
        "Median D/E",
        f"{s_med_de:.2f}x",
        delta=f"{(s_med_de - u_med_de):+.2f}x vs Univ",
        delta_color="inverse",
        help="Median Debt-to-Equity ratio",
    )
    k4.metric(
        "Avg Revenue CAGR 3Y",
        f"{s_avg_rev_cagr:.1f}%",
        delta=f"{(s_avg_rev_cagr - u_avg_rev_cagr):+.1f}% vs Univ",
        help="Average 3-Year Topline Compounded Annual Growth Rate",
    )
    k5.metric(
        "Leadership Classification",
        f"{sec_bic} Best in Class",
        help=f"{sec_wl} metrics currently in Watch List for this sector",
    )

    st.markdown("---")

    # 3. Sector vs Universe Side-by-Side Comparison (Plotly Bar Chart)
    st.subheader(f"⚖️ Sector vs Universe Benchmark Comparison: {sector_title}")
    st.markdown(
        "Side-by-side grouped variance comparing key financial fundamentals against the 92-company Nifty 100 baseline."
    )

    metrics_list = ["ROE (%)", "OPM (%)", "Revenue CAGR 3Y (%)", "Debt-to-Equity (x)"]
    sector_vals = [s_avg_roe, s_avg_opm, s_avg_rev_cagr, s_med_de]
    universe_vals = [u_avg_roe, u_avg_opm, u_avg_rev_cagr, u_med_de]

    fig_compare = go.Figure(
        data=[
            go.Bar(
                name=f"{sector_title} Average",
                x=metrics_list,
                y=sector_vals,
                text=[f"{v:.1f}" for v in sector_vals],
                textposition="auto",
                marker_color="#1E88E5",
            ),
            go.Bar(
                name="Nifty 100 Universe Average",
                x=metrics_list,
                y=universe_vals,
                text=[f"{v:.1f}" for v in universe_vals],
                textposition="auto",
                marker_color="#90A4AE",
            ),
        ]
    )

    fig_compare.update_layout(
        barmode="group",
        height=380,
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis_title="Metric Value",
    )
    st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown("---")

    # 4. Company Ranking within Sector Table
    st.subheader(f"🏆 Company Ranking within {sector_title}")
    st.caption(
        "Sorted by Composite Ranking Score across Profitability, Cash Flow, Growth, and Solvency pillars."
    )

    ranked_df = target_df.sort_values(
        by="composite_ranking_score", ascending=False
    ).copy()

    display_cols = [
        "company_id",
        "company_name",
        "sub_sector",
        "composite_ranking_score",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "operating_profit_margin_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "revenue_cagr_3yr",
        "pe_ratio",
    ]

    sec_table = ranked_df[display_cols].rename(
        columns={
            "company_id": "Ticker",
            "company_name": "Company Name",
            "sub_sector": "Sub-Sector",
            "composite_ranking_score": "Composite Score",
            "return_on_equity_pct": "ROE (%)",
            "return_on_capital_employed_pct": "ROCE (%)",
            "operating_profit_margin_pct": "OPM (%)",
            "debt_to_equity": "D/E (x)",
            "free_cash_flow_cr": "FCF (₹ Cr)",
            "revenue_cagr_3yr": "Revenue CAGR 3Y (%)",
            "pe_ratio": "P/E",
        }
    )

    st.dataframe(
        sec_table.style.format(
            {
                "Composite Score": "{:.1f}",
                "ROE (%)": "{:.1f}%",
                "ROCE (%)": "{:.1f}%",
                "OPM (%)": "{:.1f}%",
                "D/E (x)": "{:.2f}x",
                "FCF (₹ Cr)": "₹{:,.0f}",
                "Revenue CAGR 3Y (%)": "{:.1f}%",
                "P/E": "{:.1f}x",
            },
            na_rep="—",
        ).background_gradient(subset=["Composite Score"], cmap="Blues"),
        use_container_width=True,
        height=420,
    )

    st.markdown("---")

    # 5. Sector Inflow Heatmap / Leadership Breakdown (Plotly Heatmap)
    st.subheader("🔥 Cross-Sector Leadership Distribution (Best in Class Heatmap)")
    st.markdown(
        "Distribution of granular metric classifications across all evaluated sectors. "
        "Shows which industries concentrate the most top-quartile leaders."
    )

    if not peer_class_df.empty:
        heat_piv = (
            peer_class_df.groupby(["broad_sector", "classification"])["cnt"]
            .sum()
            .unstack(fill_value=0)
        )
        # Order columns intuitively
        for col_name in ["Best in Class", "In Line", "Watch List"]:
            if col_name not in heat_piv.columns:
                heat_piv[col_name] = 0
        heat_piv = heat_piv[["Best in Class", "In Line", "Watch List"]].sort_values(
            by="Best in Class", ascending=True
        )

        fig_heat = px.imshow(
            heat_piv,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Viridis",
            labels={
                "x": "Performance Classification",
                "y": "Sector",
                "color": "Metric Count",
            },
        )
        fig_heat.update_layout(
            height=360,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No peer percentiles classification distribution available.")


# ==============================================================================
# SCREEN 6: CASH FLOW INTELLIGENCE & CAPITAL ALLOCATION
# ==============================================================================


def render_cashflow_intelligence_screen(
    universe_df: pd.DataFrame, selected_ticker: str
) -> None:
    """SCREEN 6: Cash Flow Intelligence & Capital Allocation Archetypes."""
    st.title("💰 Cash Flow Intelligence & Capital Allocation")
    st.markdown(
        "Institutional cash quality diagnostics, 8-archetype capital allocation distributions, "
        "10-year cash flow decomposition, and severe liquidity stress screening."
    )

    st.markdown("---")

    # 1. Universe-wide FCF Health Summary (4 KPIs)
    fcf_series = universe_df["free_cash_flow_cr"]
    pos_fcf = int((fcf_series > 0).sum())
    neg_fcf = int((fcf_series < 0).sum())
    zero_fcf = int((fcf_series == 0).sum())
    none_fcf = int(fcf_series.isna().sum()) + zero_fcf
    total_fcf_sum = float(fcf_series.dropna().sum())

    f1, f2, f3, f4 = st.columns(4)
    f1.metric(
        "🟢 Positive FCF Companies",
        f"{pos_fcf} Companies",
        f"{(pos_fcf / len(universe_df) * 100):.1f}% of Universe",
        help="Companies generating positive Free Cash Flow after capital investments",
    )
    f2.metric(
        "🔴 Negative FCF (Cash Burning)",
        f"{neg_fcf} Companies",
        f"{(neg_fcf / len(universe_df) * 100):.1f}% of Universe",
        delta_color="inverse",
        help="Companies whose operating cash flow did not cover fiscal capital expenditure",
    )
    f3.metric(
        "⚪ Neutral / None FCF",
        f"{none_fcf} Companies",
        help="Companies with missing or neutralized cash flow statements (e.g. BEL, HAL, or 0 FCF)",
    )
    f4.metric(
        "💵 Aggregate Universe FCF",
        f"₹{total_fcf_sum:,.0f} Cr",
        help="Net total Free Cash Flow generated across the Nifty 100 in FY24",
    )

    st.markdown("---")

    # 2. Capital Allocation Pattern Distribution (Donut Chart)
    st.subheader("🍩 Capital Allocation Pattern Distribution (8 Archetypes)")
    st.markdown(
        "Categorization of all 92 companies based on the cumulative directions of "
        "Cash from Operations (CFO), Cash from Investing (CFI), and Cash from Financing (CFF)."
    )

    cap_df = load_capital_allocation_patterns()
    if not cap_df.empty:
        # Filter to latest year per company
        latest_cap = (
            cap_df.sort_values("year").groupby("company_id").last().reset_index()
        )
        pattern_counts = latest_cap["pattern_label"].value_counts().reset_index()
        pattern_counts.columns = ["pattern_label", "count"]

        top_pattern = pattern_counts.iloc[0]["pattern_label"]
        top_count = pattern_counts.iloc[0]["count"]
        top_pct = (top_count / len(latest_cap)) * 100

        c_chart, c_callout = st.columns([0.65, 0.35])

        with c_chart:
            fig_donut = px.pie(
                pattern_counts,
                names="pattern_label",
                values="count",
                hole=0.45,
                color="pattern_label",
                color_discrete_map=PATTERN_COLORS,
            )
            fig_donut.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>Companies: %{value}<br>Share: %{percent}<extra></extra>",
            )
            fig_donut.update_layout(
                margin={"l": 10, "r": 10, "t": 10, "b": 10},
                height=360,
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        with c_callout:
            st.markdown(
                f"""
                <div style="background-color: #1a2234; border: 1px solid #2a3754; border-radius: 8px; padding: 18px; margin-top: 20px;">
                    <h4 style="margin: 0; color: #4CAF50;">⭐ Dominant Archetype:</h4>
                    <h3 style="margin: 4px 0 8px 0; color: #FFFFFF;">{top_pattern}</h3>
                    <p style="font-size: 0.95rem; margin: 0; color: #CBD5E1;">
                        <strong>{top_count} of {len(latest_cap)} companies ({top_pct:.1f}%)</strong> fall into this profile.
                    </p>
                    <hr style="border: 0; border-top: 1px solid #2a3754; margin: 12px 0;">
                    <p style="font-size: 0.85rem; color: #94A3B8; margin: 0;">
                        Companies in the <em>Shareholder Returns</em> archetype generate robust positive CFO (+), 
                        conduct disciplined reinvestment in operations (-), and return surplus capital through debt reduction, 
                        dividends, or buybacks (-).
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info(
            "Capital allocation CSV artifact not found at `data/processed/capital_allocation.csv`."
        )

    st.markdown("---")

    # 3. Top 10 FCF Generators Table
    st.subheader("🏆 Top 10 Free Cash Flow (FCF) Generators — FY24")
    st.caption(
        "Ranked by absolute Free Cash Flow generated (Cash from Operations less Capital Expenditures)."
    )

    top_fcf_cos = (
        universe_df.sort_values(by="free_cash_flow_cr", ascending=False).head(10).copy()
    )
    top_fcf_display = top_fcf_cos[
        [
            "company_id",
            "company_name",
            "broad_sector",
            "free_cash_flow_cr",
            "cash_from_operations_cr",
            "fcf_conversion_rate_pct",
            "revenue_cagr_3yr",
            "pe_ratio",
        ]
    ].rename(
        columns={
            "company_id": "Ticker",
            "company_name": "Company Name",
            "broad_sector": "Sector",
            "free_cash_flow_cr": "FCF (₹ Cr)",
            "cash_from_operations_cr": "CFO (₹ Cr)",
            "fcf_conversion_rate_pct": "FCF Conversion (%)",
            "revenue_cagr_3yr": "Revenue CAGR 3Y (%)",
            "pe_ratio": "P/E",
        }
    )

    st.dataframe(
        top_fcf_display.style.format(
            {
                "FCF (₹ Cr)": "₹{:,.0f}",
                "CFO (₹ Cr)": "₹{:,.0f}",
                "FCF Conversion (%)": "{:.1f}%",
                "Revenue CAGR 3Y (%)": "{:.1f}%",
                "P/E": "{:.1f}x",
            },
            na_rep="—",
        ).background_gradient(subset=["FCF (₹ Cr)"], cmap="Greens"),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    # 4. Company Deep-Dive: 10-Year Cash Flow History (Plotly Stacked Bar Chart)
    st.subheader(f"🔬 10-Year Cash Flow Trajectory & Quality: {selected_ticker}")
    st.markdown(
        "Decomposition of Cash from Operations (CFO), Investing (CFI), and Financing (CFF) across audited fiscal years."
    )

    cf_history = load_company_cashflow_history(selected_ticker)
    comp_row = universe_df[universe_df["company_id"] == selected_ticker]

    if not comp_row.empty:
        c_item = comp_row.iloc[0]
        cfo_label = c_item.get("cfo_quality_label", "N/A")
        cfo_score = c_item.get("cfo_quality_score")
        capex_label = c_item.get("capex_label", "N/A")
        capex_pct = c_item.get("capex_intensity_pct")
        pattern_curr = c_item.get("capital_allocation_pattern", "N/A")

        b1, b2, b3 = st.columns(3)
        b1.metric(
            "CFO Quality Classification",
            f"{cfo_label}",
            help=f"CFO Quality Score: {cfo_score:.2f}" if pd.notna(cfo_score) else None,
        )
        b2.metric(
            "CapEx Intensity Label",
            f"{capex_label}",
            help=(
                f"CapEx Intensity: {capex_pct:.1f}% of Revenue"
                if pd.notna(capex_pct)
                else None
            ),
        )
        b3.metric(
            "Capital Allocation Pattern",
            f"{pattern_curr}",
            help="Latest fiscal year capital allocation classification",
        )

    if not cf_history.empty:
        fig_cf = go.Figure()
        fig_cf.add_trace(
            go.Bar(
                name="Cash from Operations (CFO)",
                x=cf_history["year"],
                y=cf_history["operating_activity"],
                marker_color="#2E7D32",
            )
        )
        fig_cf.add_trace(
            go.Bar(
                name="Cash from Investing (CFI)",
                x=cf_history["year"],
                y=cf_history["investing_activity"],
                marker_color="#C62828",
            )
        )
        fig_cf.add_trace(
            go.Bar(
                name="Cash from Financing (CFF)",
                x=cf_history["year"],
                y=cf_history["financing_activity"],
                marker_color="#FB8C00",
            )
        )
        fig_cf.add_trace(
            go.Scatter(
                name="Net Cash Flow",
                x=cf_history["year"],
                y=cf_history["net_cash_flow"],
                mode="lines+markers",
                line={"color": "#29B6F6", "width": 3},
            )
        )

        fig_cf.update_layout(
            barmode="relative",
            height=420,
            margin={"l": 20, "r": 20, "t": 30, "b": 20},
            xaxis_title="Fiscal Year",
            yaxis_title="Cash Flow (₹ Crore)",
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            },
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_cf, use_container_width=True)
    else:
        st.info(f"No cashflow statement records found for `{selected_ticker}`.")

    st.markdown("---")

    # 5. Severe Financial Stress Watch List: ICR < 1.5 & Negative FCF Simultaneously
    st.subheader("⚠️ Severe Financial Stress Watch List (ICR < 1.5 & Negative FCF)")
    st.markdown(
        "Identifies companies facing dual liquidity pressure: Operating profit insufficient to service debt "
        "(Interest Coverage Ratio &lt; 1.5x) while simultaneously burning cash (Free Cash Flow &lt; 0)."
    )

    # Latest year check
    latest_stress = universe_df[
        (universe_df["icr_risk_flag"].isin([1, True, "1", "True"]))
        & (universe_df["free_cash_flow_cr"] < 0)
    ]

    if latest_stress.empty:
        st.success(
            "🛡️ **0 Companies Flagged in FY24 (Latest Snapshot)** — All 92 Nifty 100 constituents successfully "
            "avoided concurrent solvency risk (ICR &lt; 1.5x) and cash burn in FY24. Entities with low coverage "
            "(e.g., IRFC at 1.32x ICR) maintain positive cash flow generation (+₹7,906 Cr), demonstrating systemic solvency resilience."
        )
    else:
        st.error(f"🚨 **{len(latest_stress)} Companies Flagged in FY24:**")
        st.dataframe(
            latest_stress[
                [
                    "company_id",
                    "company_name",
                    "broad_sector",
                    "interest_coverage",
                    "free_cash_flow_cr",
                ]
            ],
            use_container_width=True,
        )

    # Historical stress audit archive
    with st.expander(
        "📜 10-Year Historical High-Stress Audit Archive (23 Occurrences)"
    ):
        st.markdown(
            "Historical occurrences across FY2013–FY2023 where Nifty 100 companies underwent dual ICR &lt; 1.5 and negative FCF. "
            "Audits how prior debt-fueled expansion cycles triggered temporary balance sheet stress before operational recovery."
        )
        stress_hist = load_historical_stress_records()
        if not stress_hist.empty:
            st.dataframe(
                stress_hist.rename(
                    columns={
                        "company_id": "Ticker",
                        "company_name": "Company Name",
                        "broad_sector": "Sector",
                        "year": "Fiscal Year",
                        "interest_coverage": "ICR (x)",
                        "free_cash_flow_cr": "FCF (₹ Cr)",
                    }
                ).style.format(
                    {"ICR (x)": "{:.2f}x", "FCF (₹ Cr)": "₹{:,.0f}"}, na_rep="—"
                ),
                use_container_width=True,
                height=320,
            )


# ==============================================================================
# PLACEHOLDER & MAIN APPLICATION ROUTER
# ==============================================================================


def render_placeholder(screen_name: str, description: str, scheduled_day: str) -> None:
    """Render placeholder for screens scheduled in upcoming sprint days."""
    st.title(screen_name)
    st.markdown(f"**Status:** Under Active Development (Scheduled for {scheduled_day})")
    st.info(f"{description}\n\nImplementation will be integrated on {scheduled_day}.")


def main() -> None:
    """Main application router."""
    st.set_page_config(
        page_title="Nifty 100 Financial Intelligence Platform",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    universe_df = load_universe_snapshot()
    (
        selected_screen,
        selected_ticker,
        screener_thresholds,
        selected_peer_group,
        selected_sector,
        selected_cf_ticker,
    ) = render_sidebar(universe_df)

    if selected_screen == "🏠 Home / Overview":
        render_home_screen(universe_df)
    elif selected_screen == "🏢 Company Profile":
        render_company_profile_screen(universe_df, selected_ticker)
    elif selected_screen == "🔍 Financial Screener":
        render_financial_screener_screen(universe_df, screener_thresholds)
    elif selected_screen == "👥 Peer Comparison":
        render_peer_comparison_screen(selected_peer_group)
    elif selected_screen == "📊 Sector Analysis":
        render_sector_analytics_screen(universe_df, selected_sector)
    elif selected_screen == "🗺️ Capital Allocation & Cash Flow":
        render_cashflow_intelligence_screen(universe_df, selected_cf_ticker)
    elif selected_screen == "📈 Trend Analysis":
        render_placeholder(
            "📈 Trend Analysis",
            "10-year financial sparklines, YoY percentage change annotations, and multi-metric overlay mode.",
            "Sprint 4, Day 25 (Oct 11)",
        )
    elif selected_screen == "📑 Annual Reports":
        render_placeholder(
            "📑 Annual Reports",
            "BSE annual report filing browser with direct PDF links and filing metadata.",
            "Sprint 4, Day 25 (Oct 11)",
        )
    else:
        render_home_screen(universe_df)


if __name__ == "__main__":
    main()
