"""Nifty 100 Financial Intelligence Platform - Interactive Streamlit Dashboard.

Sprint 4: Company Intelligence Dashboard & Valuation Engine
Module 5: Interactive Streamlit Dashboard
Screen 1: Home / Overview
Screen 2: Company Profile Tearsheet
Screen 3: Financial Screener (Sliders, Presets, Live Results, CSV Download)
Screen 4: Peer Comparison (20 Metrics Heatmap, Benchmark Gap Chart, Best-in-Class)
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

SCREENS = [
    "🏠 Home / Overview",
    "🏢 Company Profile",
    "🔍 Financial Screener",
    "👥 Peer Comparison",
    "📈 Trend Analysis",
    "📊 Sector Analysis",
    "🗺️ Capital Allocation Map",
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
        "min_composite_score": 50.0,
    },
    "Asset Light Champion": {
        "min_roe": 20.0,
        "max_de": 5.0,
        "min_fcf": -10000.0,
        "min_opm": 20.0,
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
        "min_cfo_quality": 0.91,
        "max_capex_intensity": 50.0,
        "min_composite_score": 50.0,
    },
}


@st.cache_resource
def get_db_path() -> Path:
    """Resolve database path defensively."""
    if DEFAULT_DB_PATH.exists():
        return DEFAULT_DB_PATH
    alt_path = Path(__file__).resolve().parents[2] / "db" / "nifty100.db"
    if alt_path.exists():
        return alt_path
    return DEFAULT_DB_PATH


@st.cache_data(ttl=600)
def load_query(sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    """Execute a read-only query against the SQLite database and return a DataFrame."""
    db_path = get_db_path()
    if not db_path.exists():
        logger.warning("Database not found at %s", db_path)
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df
    except (sqlite3.Error, pd.errors.DatabaseError, OSError) as exc:
        logger.error("Failed to query SQLite: %s", exc)
        return pd.DataFrame()


@st.cache_data(ttl=600)
def load_screener_summary() -> pd.DataFrame:
    """Load the pre-computed screener summary with composite scores and preset matches."""
    if SCREENER_OUTPUT_PATH.exists():
        try:
            return pd.read_excel(SCREENER_OUTPUT_PATH, sheet_name="Summary")
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
            fr.free_cash_flow_cr,
            fr.revenue_cagr_3yr,
            fr.pat_cagr_3yr,
            fr.cfo_quality_score,
            fr.capex_intensity_pct,
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
def load_company_pnl(company_id: str) -> pd.DataFrame:
    """Load 10-year historical P&L figures for a company."""
    sql = """
        SELECT year, sales, operating_profit, net_profit, eps
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year ASC;
    """
    return load_query(sql, params=(company_id,))


@st.cache_data(ttl=600)
def load_company_peer_info(company_id: str) -> dict[str, Any]:
    """Load peer group and classification breakdown for a company."""
    pg_sql = (
        "SELECT peer_group_name, is_benchmark FROM peer_groups WHERE company_id = ?;"
    )
    pg_df = load_query(pg_sql, params=(company_id,))

    pp_sql = """
        SELECT classification, COUNT(*) as cnt 
        FROM peer_percentiles 
        WHERE company_id = ? 
        GROUP BY classification;
    """
    pp_df = load_query(pp_sql, params=(company_id,))

    if not pg_df.empty:
        peer_group_name = pg_df.iloc[0]["peer_group_name"]
        is_benchmark = bool(pg_df.iloc[0]["is_benchmark"])
    else:
        peer_group_name = None
        is_benchmark = False

    classifications = {"Best in Class": 0, "In Line": 0, "Watch List": 0}
    for _, row in pp_df.iterrows():
        c_label = row["classification"]
        if c_label in classifications:
            classifications[c_label] = int(row["cnt"])

    return {
        "peer_group_name": peer_group_name,
        "is_benchmark": is_benchmark,
        "classifications": classifications,
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


def render_sidebar(universe_df: pd.DataFrame) -> tuple[str, str, dict[str, float], str]:
    """Render the sidebar branding, screen navigation, and screen-specific controls."""
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
        min_revenue_cagr_3yr = st.sidebar.slider(
            "Min 3Y Revenue CAGR (%)",
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
        min_pat_cagr_3yr = st.sidebar.slider(
            "Min 3Y PAT CAGR (%)",
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
        min_cfo_quality = st.sidebar.slider(
            "Min CFO Quality Score (x)",
            min_value=0.0,
            max_value=2.0,
            value=float(
                st.session_state.get("slider_min_cfo_quality", curr["min_cfo_quality"])
            ),
            step=0.05,
            key="slider_min_cfo_quality",
        )
        max_capex_intensity = st.sidebar.slider(
            "Max CapEx Intensity (%)",
            min_value=0.5,
            max_value=30.0,
            value=float(
                st.session_state.get(
                    "slider_max_capex_intensity", curr["max_capex_intensity"]
                )
            ),
            step=0.5,
            key="slider_max_capex_intensity",
        )
        min_composite_score = st.sidebar.slider(
            "Min Composite Ranking Score",
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
            "min_revenue_cagr_3yr": min_revenue_cagr_3yr,
            "min_pat_cagr_3yr": min_pat_cagr_3yr,
            "min_cfo_quality": min_cfo_quality,
            "max_capex_intensity": max_capex_intensity,
            "min_composite_score": min_composite_score,
        }

    # Screen 4: Peer Comparison Group Selector
    elif selected_screen == "👥 Peer Comparison":
        st.sidebar.markdown("---")
        st.sidebar.subheader("Peer Group Selector")
        selected_peer_group = st.sidebar.selectbox(
            "Choose Peer Group (11 Groups):",
            options=PEER_GROUPS,
            index=3,  # Default to IT Services
        )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Platform Status")
    st.sidebar.metric(label="Coverage", value="92 Companies", delta="100% Audited")
    st.sidebar.caption("Sprint 4 · Interactive Dashboard & Valuation")
    st.sidebar.caption("Fast In-Memory Cache · Plotly Visualizations")

    return selected_screen, selected_ticker, screener_thresholds, selected_peer_group


def render_home_screen(universe_df: pd.DataFrame) -> None:
    """SCREEN 1: Home / Overview Screen."""
    st.title("🏠 Nifty 100 Market Intelligence Overview")
    st.markdown(
        "Institutional fundamental intelligence, macro valuation distributions, "
        "and multi-factor market rankings across the **Nifty 100 universe**."
    )

    st.markdown("---")

    # 1. 4 KPI Tiles at the top
    total_companies = len(universe_df)

    clean_roe_series = pd.to_numeric(
        universe_df.loc[
            ~universe_df["company_id"].isin(["BEL", "HAL"]), "return_on_equity_pct"
        ],
        errors="coerce",
    ).dropna()
    avg_roe = clean_roe_series.mean() if not clean_roe_series.empty else 0.0

    pe_series = pd.to_numeric(universe_df["pe_ratio"], errors="coerce").dropna()
    median_pe = pe_series.median() if not pe_series.empty else 0.0

    quality_compounders_count = int(
        (universe_df.get("in_quality_compounder", pd.Series(dtype=int)) == 1).sum()
    )

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(
            label="Total Companies",
            value=f"{total_companies}",
            delta="100% Tracked",
            help="Total constituents in the audited Nifty 100 universe.",
        )
    with kpi2:
        st.metric(
            label="Avg Index ROE",
            value=f"{avg_roe:.1f}%",
            delta="Healthy Returns",
            help="Mean Return on Equity across universe (neutralized for BEL/HAL scale errors).",
        )
    with kpi3:
        st.metric(
            label="Median P/E Ratio",
            value=f"{median_pe:.1f}x",
            delta="Historical Valuation",
            help="Median Price-to-Earnings multiple based on latest fiscal statements.",
        )
    with kpi4:
        st.metric(
            label="Quality Compounders",
            value=f"{quality_compounders_count}",
            delta="Preset Matched",
            help="Companies matching strict institutional Quality Compounder screener criteria.",
        )

    st.markdown("---")

    # 2. Top 10 Styled Table and Sector Distribution Bar Chart
    col_left, col_right = st.columns([1.1, 0.9])

    with col_left:
        st.subheader("🏆 Top 10 by Composite Ranking Score")
        st.markdown(
            "Multi-factor institutional score $[0, 100]$ balancing Profitability (35%), "
            "Cash Quality (30%), Growth (20%), and Solvency (15%)."
        )

        ranked_df = (
            universe_df.sort_values(by="composite_ranking_score", ascending=False)
            .head(10)
            .copy()
        )
        ranked_df["Rank"] = range(1, len(ranked_df) + 1)

        display_df = pd.DataFrame(
            {
                "Rank": ranked_df["Rank"],
                "Company": ranked_df["company_name"],
                "Sector": ranked_df["broad_sector"],
                "Composite Score": ranked_df["composite_ranking_score"].apply(
                    lambda x: f"{x:.1f}" if pd.notna(x) else "—"
                ),
                "ROE": ranked_df["return_on_equity_pct"].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
                ),
                "Rev CAGR 3Y": ranked_df["revenue_cagr_3yr"].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
                ),
            }
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=390,
        )

    with col_right:
        st.subheader("📊 Sector Distribution")
        st.markdown("Count of constituents categorized across broad sectors.")

        sector_counts = universe_df["broad_sector"].value_counts().reset_index()
        sector_counts.columns = ["broad_sector", "company_count"]

        fig_sector = px.bar(
            sector_counts,
            x="company_count",
            y="broad_sector",
            orientation="h",
            text="company_count",
            labels={
                "broad_sector": "Broad Sector",
                "company_count": "Companies",
            },
            color="company_count",
            color_continuous_scale="Blues",
        )
        fig_sector.update_layout(
            margin={"l": 10, "r": 20, "t": 10, "b": 10},
            height=390,
            yaxis={"autorange": "reversed"},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
        )
        fig_sector.update_traces(textposition="outside")
        st.plotly_chart(fig_sector, use_container_width=True)

    st.markdown("---")

    # 3. Market Pulse Summary
    st.subheader("💓 Market Pulse Summary")
    st.markdown(
        "Solvency and cash generation health indicators across all 92 companies."
    )

    fcf_positive_count = int(
        (pd.to_numeric(universe_df["free_cash_flow_cr"], errors="coerce") > 0.0).sum()
    )
    fcf_pct = (fcf_positive_count / total_companies) * 100

    low_de_count = int(
        (pd.to_numeric(universe_df["debt_to_equity"], errors="coerce") < 1.0).sum()
    )
    low_de_pct = (low_de_count / total_companies) * 100

    high_lev_count = int(
        (pd.to_numeric(universe_df["high_leverage_flag"], errors="coerce") == 1).sum()
    )
    high_lev_pct = (high_lev_count / total_companies) * 100

    pulse_col1, pulse_col2, pulse_col3 = st.columns(3)
    with pulse_col1:
        st.success(
            f"**Positive Free Cash Flow:** {fcf_positive_count} Companies ({fcf_pct:.1f}%)\n\n"
            "Constituents generating organic surplus cash above capital expenditures."
        )
    with pulse_col2:
        st.info(
            f"**Conservative Solvency (D/E < 1.0):** {low_de_count} Companies ({low_de_pct:.1f}%)\n\n"
            "Constituents with healthy balance sheets and low financial gearing."
        )
    with pulse_col3:
        if high_lev_count > 0:
            st.warning(
                f"**High Leverage Flagged:** {high_lev_count} Company ({high_lev_pct:.1f}%)\n\n"
                "Non-financial constituents flagged with aggressive debt loads."
            )
        else:
            st.success(
                "**High Leverage Flagged:** 0 Companies\n\n"
                "No non-financial companies exceed extreme solvency stress thresholds."
            )


def render_company_profile_screen(universe_df: pd.DataFrame, ticker: str) -> None:
    """SCREEN 2: Company Profile Tearsheet Screen."""
    company_row = universe_df[universe_df["company_id"] == ticker]

    if company_row.empty:
        st.error(f"Company `{ticker}` not found in universe.")
        return

    comp = company_row.iloc[0]
    company_name = comp["company_name"]
    sector = comp.get("broad_sector", "General")
    sub_sector = comp.get("sub_sector", "—")
    about = comp.get("about_company", "Institutional constituent of Nifty 100.")
    website = comp.get("website")
    logo_url = comp.get("company_logo")

    # 1. Company Card Header
    st.title(f"🏢 {company_name} ({ticker})")

    card_col1, card_col2 = st.columns([0.18, 0.82])
    with card_col1:
        if logo_url and str(logo_url).strip():
            try:
                st.image(str(logo_url), width=105)
            except (OSError, ValueError):
                st.markdown(f"### `[{ticker}]`")
        else:
            st.markdown(f"### `[{ticker}]`")

    with card_col2:
        st.markdown(
            f"**Sector:** {sector} &nbsp;|&nbsp; **Sub-Industry:** {sub_sector}"
        )
        st.markdown(f"{about}")
        if website and str(website).strip():
            st.markdown(f"🌐 [Visit Official Corporate Website]({website})")

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

    # 3. 10-Year P&L Trend Chart & 8-Axis Radar Chart
    chart_col, radar_col = st.columns([1.15, 0.85])

    with chart_col:
        st.subheader("📈 10-Year Financial Trajectory (P&L)")
        st.markdown("Annual Sales and Net Profit performance (₹ Crore).")

        pnl_df = load_company_pnl(ticker)
        if not pnl_df.empty:
            fig_pnl = go.Figure()
            fig_pnl.add_trace(
                go.Scatter(
                    x=pnl_df["year"],
                    y=pnl_df["sales"],
                    name="Sales (Revenue)",
                    mode="lines+markers",
                    line={"color": "#1E88E5", "width": 3},
                    marker={"size": 7},
                    hovertemplate="%{x}<br>Sales: ₹%{y:,.0f} Cr<extra></extra>",
                )
            )
            fig_pnl.add_trace(
                go.Scatter(
                    x=pnl_df["year"],
                    y=pnl_df["net_profit"],
                    name="Net Profit (PAT)",
                    mode="lines+markers",
                    line={"color": "#2E7D32", "width": 3},
                    marker={"size": 7},
                    hovertemplate="%{x}<br>Net Profit: ₹%{y:,.0f} Cr<extra></extra>",
                )
            )
            fig_pnl.update_layout(
                margin={"l": 10, "r": 10, "t": 10, "b": 10},
                height=360,
                legend={
                    "orientation": "h",
                    "yanchor": "bottom",
                    "y": 1.02,
                    "xanchor": "right",
                    "x": 1,
                },
                xaxis={"title": "Fiscal Year", "tickangle": -30},
                yaxis={
                    "title": "Amount (₹ Crore)",
                    "gridcolor": "rgba(200,200,200,0.15)",
                },
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pnl, use_container_width=True)
        else:
            st.info(f"No historical P&L statements recorded for `{ticker}`.")

    with radar_col:
        st.subheader("🎯 8-Axis Intra-Industry Radar")
        st.markdown("Percentile rank vs. peer group / sector distribution.")

        radar_file = RADAR_CHARTS_DIR / f"{ticker}_radar.png"
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

    # Filter logic: require non-null values for active constraints
    df = universe_df.copy()

    # Apply filters
    mask = pd.Series(True, index=df.index)

    # 1. ROE (strict null exclusion)
    if thresholds["min_roe"] > 0.0:
        mask &= (
            pd.to_numeric(df["return_on_equity_pct"], errors="coerce")
            >= thresholds["min_roe"]
        )

    # 2. D/E (strict null exclusion)
    if thresholds["max_de"] < 5.0:
        mask &= (
            pd.to_numeric(df["debt_to_equity"], errors="coerce") <= thresholds["max_de"]
        )

    # 3. FCF (strict null exclusion)
    if thresholds["min_fcf"] > -5000.0:
        mask &= (
            pd.to_numeric(df["free_cash_flow_cr"], errors="coerce")
            >= thresholds["min_fcf"]
        )

    # 4. OPM (strict null exclusion)
    if thresholds["min_opm"] > 0.0:
        mask &= (
            pd.to_numeric(df["operating_profit_margin_pct"], errors="coerce")
            >= thresholds["min_opm"]
        )

    # 5. P/E (strict null exclusion)
    if thresholds["max_pe"] < 150.0:
        mask &= pd.to_numeric(df["pe_ratio"], errors="coerce") <= thresholds["max_pe"]

    # 6. Revenue CAGR 3Y
    if thresholds["min_revenue_cagr_3yr"] > -20.0:
        mask &= (
            pd.to_numeric(df["revenue_cagr_3yr"], errors="coerce")
            >= thresholds["min_revenue_cagr_3yr"]
        )

    # 7. PAT CAGR 3Y
    if thresholds["min_pat_cagr_3yr"] > -20.0:
        mask &= (
            pd.to_numeric(df["pat_cagr_3yr"], errors="coerce")
            >= thresholds["min_pat_cagr_3yr"]
        )

    # 8. CFO Quality Score
    if thresholds["min_cfo_quality"] > 0.0:
        mask &= (
            pd.to_numeric(df["cfo_quality_score"], errors="coerce")
            >= thresholds["min_cfo_quality"]
        )

    # 9. CapEx Intensity
    if thresholds["max_capex_intensity"] < 30.0:
        mask &= (
            pd.to_numeric(df["capex_intensity_pct"], errors="coerce")
            <= thresholds["max_capex_intensity"]
        )

    # 10. Composite Score
    if thresholds["min_composite_score"] > 0.0:
        mask &= (
            pd.to_numeric(df["composite_ranking_score"], errors="coerce")
            >= thresholds["min_composite_score"]
        )

    filtered_df = (
        df[mask].sort_values(by="composite_ranking_score", ascending=False).copy()
    )
    match_count = len(filtered_df)

    # Status & Row Count Banner
    top_col1, top_col2 = st.columns([0.7, 0.3])
    with top_col1:
        st.success(
            f"🎯 **{match_count} companies match your screening criteria** (out of 92 universe constituents)."
        )
    with top_col2:
        csv_data = (
            filtered_df[
                [
                    "company_id",
                    "company_name",
                    "broad_sector",
                    "composite_ranking_score",
                    "return_on_equity_pct",
                    "operating_profit_margin_pct",
                    "debt_to_equity",
                    "free_cash_flow_cr",
                    "pe_ratio",
                    "revenue_cagr_3yr",
                    "cfo_quality_score",
                ]
            ]
            .to_csv(index=False)
            .encode("utf-8")
        )
        st.download_button(
            label="📥 Export Filtered Results (CSV)",
            data=csv_data,
            file_name="nifty100_filtered_screener.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Neutralized Tickers Verification
    excluded_in_results = [
        t for t in ["SBIN", "BEL", "HAL"] if t in filtered_df["company_id"].values
    ]
    if excluded_in_results:
        st.warning(f"⚠️ Flagged Tickers in Results: {', '.join(excluded_in_results)}")
    else:
        st.caption(
            "🛡️ **Integrity Verification:** SBIN, BEL, and HAL are completely excluded from "
            "filtered results due to verified source data gaps / scale errors."
        )

    # Live Results Table
    if not filtered_df.empty:
        display_results = pd.DataFrame(
            {
                "Ticker": filtered_df["company_id"],
                "Company Name": filtered_df["company_name"],
                "Sector": filtered_df["broad_sector"],
                "Composite Score": filtered_df["composite_ranking_score"].apply(
                    lambda x: f"{x:.1f}" if pd.notna(x) else "—"
                ),
                "ROE (%)": filtered_df["return_on_equity_pct"].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
                ),
                "OPM (%)": filtered_df["operating_profit_margin_pct"].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
                ),
                "D/E (x)": filtered_df["debt_to_equity"].apply(
                    lambda x: f"{x:.2f}x" if pd.notna(x) else "—"
                ),
                "FCF (₹ Cr)": filtered_df["free_cash_flow_cr"].apply(
                    lambda x: f"₹{x:,.0f}" if pd.notna(x) else "—"
                ),
                "P/E (x)": filtered_df["pe_ratio"].apply(
                    lambda x: f"{x:.1f}x" if pd.notna(x) else "—"
                ),
                "Rev CAGR 3Y": filtered_df["revenue_cagr_3yr"].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
                ),
                "CFO Quality": filtered_df["cfo_quality_score"].apply(
                    lambda x: f"{x:.2f}x" if pd.notna(x) else "—"
                ),
            }
        )

        st.dataframe(
            display_results,
            use_container_width=True,
            hide_index=True,
            height=500,
        )
    else:
        st.warning(
            "No companies match the selected combination of slider thresholds. Relax one or more filters."
        )


def render_peer_comparison_screen(selected_peer_group: str) -> None:
    """SCREEN 4: Intra-Industry Peer Comparison Screen."""
    st.title("👥 Intra-Industry Peer Comparison")
    st.markdown(
        f"Comparative fundamental benchmarking across **{selected_peer_group}** peer group. "
        "Evaluates 20 metrics, intra-group percentile rankings, and percentage gaps relative to the benchmark leader."
    )

    st.markdown("---")

    peer_df = load_peer_group_metrics(selected_peer_group)

    if peer_df.empty:
        st.warning(f"No peer records found for `{selected_peer_group}`.")
        return

    # Identify Benchmark Company
    bench_records = peer_df[peer_df["is_benchmark"] == 1]
    bench_id = bench_records.iloc[0]["company_id"] if not bench_records.empty else "TCS"
    bench_name = (
        bench_records.iloc[0]["company_name"] if not bench_records.empty else bench_id
    )

    st.info(
        f"🏆 **Designated Peer Group Benchmark Leader:** **{bench_name} ({bench_id})**"
    )

    # 1. 20-Metric Comparative Heatmap Table
    st.subheader("📋 20-Metric Side-by-Side Comparative Matrix")
    st.markdown(
        "Conditional formatting applied row-wise: 🟢 **Green** = Top Intra-Group Performer, "
        "🟡 **Yellow** = Median, 🔴 **Red** = Bottom Performer."
    )

    # Pivot metric values (rows = metric_name, cols = company_id)
    piv_val = peer_df.pivot(
        index="metric_name", columns="company_id", values="metric_value"
    )

    # Highlight benchmark column name
    column_renames = {
        cid: f"{cid} 🏆 (Benchmark)" if cid == bench_id else cid
        for cid in piv_val.columns
    }
    piv_display = piv_val.rename(columns=column_renames)

    # Apply pandas Styler background gradient
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
        r"Percentage variance relative to the benchmark leader ($0.0\%$) for **ROE, ROCE, "
        "Revenue CAGR 3Y, OPM, and Composite Score**."
    )

    top5_metrics = ["ROE", "ROCE", "Revenue CAGR 3yr", "OPM", "Composite Score"]
    gap_df = peer_df[peer_df["metric_name"].isin(top5_metrics)].copy()
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
            hover_data={"metric_value": ":.2f", "benchmark_gap_pct": ":.1f%"},
            title=f"Intra-Group Spread vs. Benchmark Leader ({bench_id} = 0.0%)",
        )
        fig_gap.update_layout(
            margin={"l": 20, "r": 20, "t": 50, "b": 30},
            height=400,
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
            },
            yaxis={
                "title": "Gap vs. Benchmark (%)",
                "zeroline": True,
                "zerolinecolor": "rgba(255,255,255,0.4)",
            },
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
    selected_screen, selected_ticker, screener_thresholds, selected_peer_group = (
        render_sidebar(universe_df)
    )

    if selected_screen == "🏠 Home / Overview":
        render_home_screen(universe_df)
    elif selected_screen == "🏢 Company Profile":
        render_company_profile_screen(universe_df, selected_ticker)
    elif selected_screen == "🔍 Financial Screener":
        render_financial_screener_screen(universe_df, screener_thresholds)
    elif selected_screen == "👥 Peer Comparison":
        render_peer_comparison_screen(selected_peer_group)
    elif selected_screen == "📈 Trend Analysis":
        render_placeholder(
            "📈 Trend Analysis",
            "10-year financial sparklines, YoY percentage change annotations, and multi-metric overlay mode.",
            "Sprint 4, Day 25 (Oct 11)",
        )
    elif selected_screen == "📊 Sector Analysis":
        render_placeholder(
            "📊 Sector Analysis",
            "Cross-sector comparative bubble charts and median multiples distribution bar charts.",
            "Sprint 4, Day 25 (Oct 11)",
        )
    elif selected_screen == "🗺️ Capital Allocation Map":
        render_placeholder(
            "🗺️ Capital Allocation Map",
            "Interactive treemap of 92 companies categorized across the 8 CFO/CFI/CFF capital allocation patterns.",
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
