"""FastAPI REST Service Layer (Module 11 / Sprint 6).

Production REST API providing programmatic access to 92 Nifty 100 constituent
fundamentals, financial ratio models, multi-parameter screener engine,
sector benchmarks, peer group comparisons, and market data overviews.
"""

from __future__ import annotations

import functools
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import yaml
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("n100_api")

# Determine repository root and default paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "nifty100.db"
DEFAULT_CONFIG_PATH = REPO_ROOT / "screener_config.yaml"
START_TIME = time.time()

app = FastAPI(
    title="N100 Financial Intelligence Platform API",
    description=(
        "Production-grade RESTful service exposing 16 endpoints for institutional "
        "fundamental intelligence, ratio analytics, screener filtering, peer comparisons, "
        "and sector benchmarking across the Nifty 100 universe."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend and analyst client consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# PYDANTIC RESPONSE MODELS
# ==============================================================================


class CompanySummary(BaseModel):
    id: str = Field(..., description="NSE ticker symbol")
    name: str = Field(..., description="Full legal company name")
    sector: str = Field(..., description="Broad sector classification")
    peer_group: str = Field(..., description="Peer comparison group")
    composite_score: Optional[float] = Field(None, description="Composite Financial Health Score (0-100)")


class CompanyProfile(BaseModel):
    id: str = Field(..., description="NSE ticker symbol")
    company_name: str = Field(..., description="Full legal company name")
    company_logo: Optional[str] = Field(None, description="Company logo URL")
    about_company: Optional[str] = Field(None, description="Company overview / business description")
    website: Optional[str] = Field(None, description="Official company website")
    nse_profile: Optional[str] = Field(None, description="NSE market profile URL")
    bse_profile: Optional[str] = Field(None, description="BSE market profile URL")
    sector: str = Field(..., description="Broad sector classification")
    sub_sector: Optional[str] = Field(None, description="Detailed sub-sector classification")
    peer_group: str = Field(..., description="Peer group classification")
    composite_score: Optional[float] = Field(None, description="Composite ranking score")
    valuation_flag: Optional[str] = Field("Fair Value", description="Valuation status flag")
    face_value: Optional[float] = Field(None, description="Face value per share")
    book_value: Optional[float] = Field(None, description="Book value per share")
    latest_ratios: Optional[dict[str, Any]] = Field(default_factory=dict, description="Latest fiscal year financial ratios")


class CompanyRatiosResponse(BaseModel):
    ticker: str
    company_name: str
    total_years: int
    ratios: list[dict[str, Any]]


class CompanyFinancialsResponse(BaseModel):
    ticker: str
    company_name: str
    profit_and_loss: list[dict[str, Any]]
    balance_sheet: list[dict[str, Any]]
    cash_flow: list[dict[str, Any]]


class PeerMetricRank(BaseModel):
    value: Optional[float]
    percentile: Optional[float]
    classification: Optional[str] = "In Line"


class CompanyPeersResponse(BaseModel):
    ticker: str
    company_name: str
    peer_group: str
    peer_members: list[str]
    percentile_ranks: dict[str, PeerMetricRank]


class ScreenerCompanyItem(BaseModel):
    company_id: str
    company_name: str
    broad_sector: str
    roe: Optional[float] = None
    roce: Optional[float] = None
    opm: Optional[float] = None
    de: Optional[float] = None
    pe_ratio: Optional[float] = None
    fcf_cr: Optional[float] = None
    revenue_cagr_3yr: Optional[float] = None
    composite_ranking_score: Optional[float] = None
    valuation_flag: Optional[str] = "Fair Value"


class ScreenerPresetItem(BaseModel):
    preset_key: str
    name: str
    description: str
    logic: str
    thresholds: dict[str, Any]


class SectorSummaryItem(BaseModel):
    sector_name: str
    company_count: int
    avg_roe: float
    avg_opm: float
    median_de: float
    median_pe: float
    total_market_cap_cr: float


class SectorDetailResponse(BaseModel):
    sector_name: str
    company_count: int
    avg_roe: float
    avg_opm: float
    median_de: float
    median_pe: float
    companies: list[dict[str, Any]]


class MarketOverviewResponse(BaseModel):
    total_companies: int
    avg_roe: float
    median_pe: float
    count_positive_fcf: int
    count_low_leverage: int
    top_companies: list[dict[str, Any]]



class CashflowTrendItem(BaseModel):
    year: str
    cfo: Optional[float] = Field(None, description="Cash from Operations (Operating Activity) in ₹ Cr")
    cfi: Optional[float] = Field(None, description="Cash from Investing in ₹ Cr")
    cff: Optional[float] = Field(None, description="Cash from Financing in ₹ Cr")
    fcf: Optional[float] = Field(None, description="Free Cash Flow (CFO + CFI) in ₹ Cr")
    net_cash_flow: Optional[float] = Field(None, description="Net change in cash in ₹ Cr")


class CompanyCashflowResponse(BaseModel):
    ticker: str
    company_name: str
    capital_allocation_pattern: Optional[str] = Field(None, description="Institutional 8-pattern classification")
    cfo_quality_label: Optional[str] = Field(None, description="High Quality vs Accrual Warning")
    cfo_quality_score: Optional[float] = Field(None, description="Trailing 5Y CFO/PAT Quality Score")
    fcf_trend_5yr: list[CashflowTrendItem] = Field(default_factory=list, description="Trailing 5 audited fiscal years")


class CompanyValuationResponse(BaseModel):
    ticker: str
    company_name: str
    broad_sector: Optional[str] = None
    market_cap_crore: Optional[float] = None
    pe_ratio: Optional[float] = Field(None, description="Current Price-to-Earnings ratio")
    median_pe_5yr: Optional[float] = Field(None, description="5-Year Historical Median P/E")
    pb_ratio: Optional[float] = Field(None, description="Price-to-Book ratio")
    ev_ebitda: Optional[float] = Field(None, description="Enterprise Value to EBITDA multiple")
    dcf_implied_value_cr: Optional[float] = Field(None, description="DCF implied equity value in ₹ Cr")
    dcf_upside_pct: Optional[float] = Field(None, description="Implied DCF upside/downside percentage")
    valuation_flag: Optional[str] = Field(None, description="Valuation badge (Undervalued / Fair Value / Overvalued)")
    historical_valuation_flag: Optional[str] = Field(None, description="Valuation vs 5-year median")


class PeerMetricDetail(BaseModel):
    metric_name: str
    metric_value: Optional[float] = None
    percentile_rank: Optional[float] = None
    classification: Optional[str] = None
    benchmark_gap_pct: Optional[float] = None


class PeerMemberDetail(BaseModel):
    company_id: str
    company_name: str
    best_in_class_count: int = 0
    watch_list_count: int = 0
    in_line_count: int = 0
    composite_score_percentile: Optional[float] = None
    composite_score_classification: Optional[str] = None
    metrics: list[PeerMetricDetail] = Field(default_factory=list)


class PeerGroupDetailResponse(BaseModel):
    peer_group_name: str
    total_members: int
    metrics_count: int
    members: list[PeerMemberDetail]


# ==============================================================================
# DATABASE & DATA HELPERS WITH CACHING
# ==============================================================================


def get_db_path() -> Path:
    """Resolve the SQLite database path from environment or default repo location."""
    env_path = os.getenv("DB_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p.resolve()

    candidates = [
        DEFAULT_DB_PATH,
        Path("db/nifty100.db"),
        Path("../db/nifty100.db"),
        REPO_ROOT / "db" / "nifty100.db",
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()

    return DEFAULT_DB_PATH.resolve()


def get_db_connection() -> sqlite3.Connection:
    """Open an optimized SQLite database connection with row factory."""
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at: {db_path}")
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


@functools.lru_cache(maxsize=1)
def load_screener_config_cached() -> dict[str, Any]:
    """Load screener configuration YAML cached."""
    cfg_path = DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        cfg_path = Path("screener_config.yaml")
    if not cfg_path.exists():
        cfg_path = Path("../screener_config.yaml")

    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


@functools.lru_cache(maxsize=1)
def load_universe_df_cached() -> pd.DataFrame:
    """Load latest annual snapshot per company, joined with sectors, market_cap, and scores."""
    conn = get_db_connection()
    try:
        sql = """
            SELECT 
                c.id as company_id,
                c.company_name,
                c.company_logo,
                c.about_company,
                c.website,
                c.nse_profile,
                c.bse_profile,
                c.face_value,
                c.book_value,
                s.broad_sector,
                s.sub_sector,
                fr.year,
                fr.return_on_equity_pct as roe,
                fr.return_on_capital_employed_pct as roce,
                fr.operating_profit_margin_pct as opm,
                fr.net_profit_margin_pct as npm,
                fr.debt_to_equity as de,
                fr.interest_coverage,
                fr.free_cash_flow_cr as fcf,
                fr.revenue_cagr_3yr,
                fr.pat_cagr_3yr,
                fr.dividend_payout_ratio_pct,
                fr.capex_intensity_pct,
                fr.cfo_quality_score,
                mc.market_cap_crore,
                mc.pe_ratio,
                mc.pb_ratio
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
        df = pd.read_sql_query(sql, conn)

        # Peer group join
        pg_df = pd.read_sql_query("SELECT company_id, peer_group_name FROM peer_groups", conn)
        df = df.merge(pg_df, on="company_id", how="left")
        df["peer_group"] = df["peer_group_name"].fillna(df["broad_sector"]).fillna("General")

        # Partition 11 macro sectors (Utilities split from Energy)
        def assign_11_sectors(row: pd.Series) -> str:
            bs = str(row["broad_sector"])
            sub = str(row["sub_sector"]).lower()
            if bs == "Energy":
                if any(k in sub for k in ["power", "utility", "transmission", "renewable"]):
                    return "Utilities"
                return "Energy"
            return bs

        df["sector_11"] = df.apply(assign_11_sectors, axis=1)

        # Merge composite scores and presets from screener_output.xlsx
        screener_path = REPO_ROOT / "screener_output.xlsx"
        if not screener_path.exists():
            screener_path = REPO_ROOT / "reports" / "screener_output.xlsx"
        if screener_path.exists():
            try:
                scr_df = pd.read_excel(screener_path, sheet_name="Summary")
                cols = [c for c in scr_df.columns if c in ["company_id", "composite_ranking_score", "valuation_flag"]]
                df = df.merge(scr_df[cols], on="company_id", how="left")
            except Exception as exc:
                logger.warning("Could not read screener_output.xlsx: %s", exc)

        if "composite_ranking_score" not in df.columns:
            df["composite_ranking_score"] = 50.0

        val_flags_path = REPO_ROOT / "reports" / "valuation_flags.csv"
        if val_flags_path.exists():
            try:
                val_df = pd.read_csv(val_flags_path)
                if "valuation_flag" in val_df.columns and "valuation_flag" not in df.columns:
                    df = df.merge(val_df[["company_id", "valuation_flag"]], on="company_id", how="left")
            except Exception as exc:
                logger.warning("Could not read valuation_flags.csv: %s", exc)

        if "valuation_flag" not in df.columns:
            df["valuation_flag"] = "Fair Value"

        return df
    finally:
        conn.close()


# ==============================================================================
# DIAGNOSTIC & ROOT ENDPOINTS
# ==============================================================================


@app.get("/", tags=["Diagnostic"], summary="API Root Information", include_in_schema=False)
def root_info() -> dict[str, Any]:
    return {
        "platform": "N100 Financial Intelligence Platform API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health", tags=["Diagnostic"], summary="System Health & Database Verification", include_in_schema=False)
@app.get("/api/v1/health", tags=["Diagnostic"], summary="System Health & Database Verification (v1)", include_in_schema=False)
def health_check() -> JSONResponse:
    db_path = get_db_path()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        tables = [
            row[0]
            for row in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence' ORDER BY name;"
            ).fetchall()
        ]
        counts: dict[str, int] = {}
        for tbl in tables:
            counts[tbl] = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        conn.close()

        payload = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(time.time() - START_TIME, 2),
            "db_status": "connected",
            "db_path": str(db_path),
            "total_tables": len(counts),
            "db_row_counts": counts,
        }
        return JSONResponse(status_code=status.HTTP_200_OK, content=payload)
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(exc)},
        )



@functools.lru_cache(maxsize=1)
def load_valuation_summary_cached() -> pd.DataFrame:
    """Load pre-computed valuation summary table from reports/valuation_summary.xlsx."""
    candidates = [
        REPO_ROOT / "reports" / "valuation_summary.xlsx",
        REPO_ROOT / "valuation_summary.xlsx",
    ]
    for p in candidates:
        if p.exists():
            try:
                return pd.read_excel(p)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", p, exc)
    return pd.DataFrame()


def compute_dcf_implied(fcf_base: Optional[float], mcap: Optional[float]) -> tuple[Optional[float], Optional[float]]:
    """Compute 2-stage DCF implied enterprise/equity value and upside percentage."""
    if fcf_base is not None and not pd.isna(fcf_base) and fcf_base > 0:
        g = 0.12
        r = 0.115
        g_t = 0.045
        pv_fcf = sum((fcf_base * ((1 + g) ** yr)) / ((1 + r) ** yr) for yr in range(1, 6))
        term_val = (fcf_base * ((1 + g) ** 5) * (1 + g_t)) / (r - g_t)
        pv_term = term_val / ((1 + r) ** 5)
        implied_val = round(pv_fcf + pv_term, 2)
        upside = round(((implied_val - mcap) / mcap) * 100.0, 2) if mcap and mcap > 0 else None
        return implied_val, upside
    return None, None


# ==============================================================================
# GROUP 1: COMPANY ENDPOINTS
# ==============================================================================


@app.get(
    "/api/v1/companies",
    response_model=list[CompanySummary],
    tags=["Companies"],
    summary="List all 92 companies",
    description="Returns all 92 companies with ticker id, name, broad sector, peer group, and composite score.",
)
@app.get(
    "/companies",
    response_model=list[CompanySummary],
    tags=["Companies"],
    summary="List all 92 companies (alias)",
    include_in_schema=False,
)
def get_companies(sector: Optional[str] = Query(None, description="Filter by broad sector")) -> list[CompanySummary]:
    df = load_universe_df_cached()
    if sector:
        target_sec = sector.strip().lower()
        filtered = df[
            (df["broad_sector"].str.lower() == target_sec)
            | (df["sector_11"].str.lower() == target_sec)
        ]
    else:
        filtered = df

    results: list[CompanySummary] = []
    for _, row in filtered.iterrows():
        c_score = row.get("composite_ranking_score")
        score_val = float(c_score) if pd.notna(c_score) else None
        results.append(
            CompanySummary(
                id=str(row["company_id"]),
                name=str(row["company_name"]),
                sector=str(row["broad_sector"]),
                peer_group=str(row["peer_group"]),
                composite_score=score_val,
            )
        )
    return results


@app.get(
    "/api/v1/companies/{ticker}",
    response_model=CompanyProfile,
    tags=["Companies"],
    summary="Get Company Profile",
    description="Returns full profile metadata from companies table and latest annual financial ratios.",
)
@app.get(
    "/companies/{ticker}",
    response_model=CompanyProfile,
    tags=["Companies"],
    summary="Get Company Profile (alias)",
    include_in_schema=False,
)
def get_company_profile(ticker: str) -> CompanyProfile:
    clean_ticker = ticker.strip().upper()
    df = load_universe_df_cached()
    matched = df[df["company_id"].str.upper() == clean_ticker]
    if matched.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker '{ticker}' not found in Nifty 100 universe.",
        )

    row = matched.iloc[0]

    # Query full latest financial_ratios row
    conn = get_db_connection()
    try:
        r_row = conn.execute(
            """
            SELECT * FROM financial_ratios 
            WHERE company_id = ? AND year LIKE '%-03' 
            ORDER BY year DESC LIMIT 1;
            """,
            (row["company_id"],),
        ).fetchone()
        latest_ratios = dict(r_row) if r_row else {}
    finally:
        conn.close()

    c_score = row.get("composite_ranking_score")
    score_val = float(c_score) if pd.notna(c_score) else None

    return CompanyProfile(
        id=str(row["company_id"]),
        company_name=str(row["company_name"]),
        company_logo=str(row["company_logo"]) if pd.notna(row["company_logo"]) else None,
        about_company=str(row["about_company"]) if pd.notna(row["about_company"]) else None,
        website=str(row["website"]) if pd.notna(row["website"]) else None,
        nse_profile=str(row["nse_profile"]) if pd.notna(row["nse_profile"]) else None,
        bse_profile=str(row["bse_profile"]) if pd.notna(row["bse_profile"]) else None,
        sector=str(row["broad_sector"]),
        sub_sector=str(row["sub_sector"]) if pd.notna(row["sub_sector"]) else None,
        peer_group=str(row["peer_group"]),
        composite_score=score_val,
        valuation_flag=str(row.get("valuation_flag", "Fair Value")),
        face_value=float(row["face_value"]) if pd.notna(row["face_value"]) else None,
        book_value=float(row["book_value"]) if pd.notna(row["book_value"]) else None,
        latest_ratios=latest_ratios,
    )


@app.get(
    "/api/v1/companies/{ticker}/ratios",
    response_model=CompanyRatiosResponse,
    tags=["Companies"],
    summary="Get Company Ratios History",
    description="Returns all ratio rows across all years for a company.",
)
def get_company_ratios(ticker: str) -> CompanyRatiosResponse:
    clean_ticker = ticker.strip().upper()
    conn = get_db_connection()
    try:
        co = conn.execute("SELECT company_name FROM companies WHERE UPPER(id) = ?", (clean_ticker,)).fetchone()
        if not co:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker '{ticker}' not found.",
            )

        rows = conn.execute(
            "SELECT * FROM financial_ratios WHERE UPPER(company_id) = ? ORDER BY year ASC",
            (clean_ticker,),
        ).fetchall()
        ratios_list = [dict(r) for r in rows]

        return CompanyRatiosResponse(
            ticker=clean_ticker,
            company_name=co["company_name"],
            total_years=len(ratios_list),
            ratios=ratios_list,
        )
    finally:
        conn.close()


@app.get(
    "/api/v1/companies/{ticker}/financials",
    response_model=CompanyFinancialsResponse,
    tags=["Companies"],
    summary="Get Company Financial Statements",
    description="Returns multi-year historical P&L, Balance Sheet, and Cash Flow statements.",
)
def get_company_financials(ticker: str) -> CompanyFinancialsResponse:
    clean_ticker = ticker.strip().upper()
    conn = get_db_connection()
    try:
        co = conn.execute("SELECT company_name FROM companies WHERE UPPER(id) = ?", (clean_ticker,)).fetchone()
        if not co:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker '{ticker}' not found.",
            )

        pl_rows = [dict(r) for r in conn.execute("SELECT * FROM profitandloss WHERE UPPER(company_id) = ? ORDER BY year ASC", (clean_ticker,)).fetchall()]
        bs_rows = [dict(r) for r in conn.execute("SELECT * FROM balancesheet WHERE UPPER(company_id) = ? ORDER BY year ASC", (clean_ticker,)).fetchall()]
        cf_rows = [dict(r) for r in conn.execute("SELECT * FROM cashflow WHERE UPPER(company_id) = ? ORDER BY year ASC", (clean_ticker,)).fetchall()]

        return CompanyFinancialsResponse(
            ticker=clean_ticker,
            company_name=co["company_name"],
            profit_and_loss=pl_rows,
            balance_sheet=bs_rows,
            cash_flow=cf_rows,
        )
    finally:
        conn.close()


@app.get(
    "/api/v1/companies/{ticker}/peers",
    response_model=CompanyPeersResponse,
    tags=["Companies"],
    summary="Get Company Peer Percentiles & Radar Data",
    description="Returns peer group members and percentile ranks for ROE, ROCE, OPM, Rev CAGR 3yr, and Composite Score.",
)
def get_company_peers(ticker: str) -> CompanyPeersResponse:
    clean_ticker = ticker.strip().upper()
    conn = get_db_connection()
    try:
        co = conn.execute("SELECT company_name FROM companies WHERE UPPER(id) = ?", (clean_ticker,)).fetchone()
        if not co:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ticker '{ticker}' not found.",
            )

        # Peer group determination
        pg_row = conn.execute("SELECT peer_group_name FROM peer_groups WHERE UPPER(company_id) = ?", (clean_ticker,)).fetchone()
        if pg_row:
            pg_name = pg_row["peer_group_name"]
            members = [r["company_id"] for r in conn.execute("SELECT company_id FROM peer_groups WHERE peer_group_name = ? ORDER BY company_id", (pg_name,)).fetchall()]
        else:
            sec_row = conn.execute("SELECT broad_sector FROM sectors WHERE UPPER(company_id) = ?", (clean_ticker,)).fetchone()
            pg_name = sec_row["broad_sector"] if sec_row else "General"
            members = [r["company_id"] for r in conn.execute("SELECT company_id FROM sectors WHERE broad_sector = ? ORDER BY company_id", (pg_name,)).fetchall()]

        # Query percentiles from peer_percentiles table
        target_metrics = ["ROE", "ROCE", "OPM", "Revenue CAGR 3yr", "Composite Score"]
        pp_rows = conn.execute(
            "SELECT metric_name, metric_value, percentile_rank, classification FROM peer_percentiles WHERE UPPER(company_id) = ?",
            (clean_ticker,),
        ).fetchall()

        ranks_dict: dict[str, PeerMetricRank] = {}
        for r in pp_rows:
            m_name = r["metric_name"]
            if m_name in target_metrics:
                ranks_dict[m_name] = PeerMetricRank(
                    value=float(r["metric_value"]) if r["metric_value"] is not None else None,
                    percentile=float(r["percentile_rank"]) if r["percentile_rank"] is not None else None,
                    classification=str(r["classification"]),
                )

        # If any of the 5 metrics wasn't in peer_percentiles (e.g. non-peer-group company), compute fallback
        if len(ranks_dict) < len(target_metrics):
            df = load_universe_df_cached()
            co_row = df[df["company_id"].str.upper() == clean_ticker].iloc[0]
            metric_mapping = {
                "ROE": co_row.get("roe"),
                "ROCE": co_row.get("roce"),
                "OPM": co_row.get("opm"),
                "Revenue CAGR 3yr": co_row.get("revenue_cagr_3yr"),
                "Composite Score": co_row.get("composite_ranking_score"),
            }
            for tm in target_metrics:
                if tm not in ranks_dict:
                    val = metric_mapping.get(tm)
                    ranks_dict[tm] = PeerMetricRank(
                        value=float(val) if pd.notna(val) else None,
                        percentile=50.0,
                        classification="In Line",
                    )

        return CompanyPeersResponse(
            ticker=clean_ticker,
            company_name=co["company_name"],
            peer_group=pg_name,
            peer_members=members,
            percentile_ranks=ranks_dict,
        )
    finally:
        conn.close()


# ==============================================================================
# GROUP 2: SCREENER ENDPOINTS
# ==============================================================================


@app.get(
    "/api/v1/screener",
    response_model=list[ScreenerCompanyItem],
    tags=["Screener"],
    summary="Filter Universe (Screener Engine)",
    description="Multi-criteria screener matching Sprint 3 engine results. Query params: min_roe, max_de, min_fcf, min_opm, max_pe.",
)
@app.get(
    "/screener",
    response_model=list[ScreenerCompanyItem],
    tags=["Screener"],
    summary="Filter Universe (alias)",
    include_in_schema=False,
)
def run_screener_query(
    min_roe: Optional[float] = Query(None, description="Minimum ROE (%)"),
    max_de: Optional[float] = Query(None, description="Maximum Debt-to-Equity ratio"),
    min_fcf: Optional[float] = Query(None, description="Minimum Free Cash Flow (INR Cr)"),
    min_opm: Optional[float] = Query(None, description="Minimum Operating Profit Margin (%)"),
    max_pe: Optional[float] = Query(None, description="Maximum Price-to-Earnings multiple"),
) -> list[ScreenerCompanyItem]:
    df = load_universe_df_cached().copy()

    # Apply criteria with Sprint 3 strict null exclusion logic
    if min_roe is not None:
        df = df[df["roe"].notna() & (df["roe"] >= min_roe)]
    if max_de is not None:
        df = df[df["de"].notna() & (df["de"] <= max_de)]
    if min_fcf is not None:
        df = df[df["fcf"].notna() & (df["fcf"] >= min_fcf)]
    if min_opm is not None:
        df = df[df["opm"].notna() & (df["opm"] >= min_opm)]
    if max_pe is not None:
        df = df[df["pe_ratio"].notna() & (df["pe_ratio"] <= max_pe)]

    # Sort by composite score descending
    df["sort_score"] = df["composite_ranking_score"].fillna(-999.0)
    df = df.sort_values(by="sort_score", ascending=False)

    results: list[ScreenerCompanyItem] = []
    for _, row in df.iterrows():
        results.append(
            ScreenerCompanyItem(
                company_id=str(row["company_id"]),
                company_name=str(row["company_name"]),
                broad_sector=str(row["broad_sector"]),
                roe=float(row["roe"]) if pd.notna(row["roe"]) else None,
                roce=float(row["roce"]) if pd.notna(row["roce"]) else None,
                opm=float(row["opm"]) if pd.notna(row["opm"]) else None,
                de=float(row["de"]) if pd.notna(row["de"]) else None,
                pe_ratio=float(row["pe_ratio"]) if pd.notna(row["pe_ratio"]) else None,
                fcf_cr=float(row["fcf"]) if pd.notna(row["fcf"]) else None,
                revenue_cagr_3yr=float(row["revenue_cagr_3yr"]) if pd.notna(row["revenue_cagr_3yr"]) else None,
                composite_ranking_score=float(row["composite_ranking_score"]) if pd.notna(row["composite_ranking_score"]) else None,
                valuation_flag=str(row.get("valuation_flag", "Fair Value")),
            )
        )
    return results


@app.get(
    "/api/v1/screener/presets",
    response_model=list[ScreenerPresetItem],
    tags=["Screener"],
    summary="List All Screener Presets",
    description="Returns all 6 pre-built institutional screener presets and their filtering thresholds.",
)
@app.get(
    "/screener/presets",
    response_model=list[ScreenerPresetItem],
    tags=["Screener"],
    summary="List Screener Presets (alias)",
    include_in_schema=False,
)
def get_screener_presets() -> list[ScreenerPresetItem]:
    cfg = load_screener_config_cached()
    presets = cfg.get("presets", {})
    results: list[ScreenerPresetItem] = []
    for p_key, p_val in presets.items():
        results.append(
            ScreenerPresetItem(
                preset_key=p_key,
                name=p_val.get("name", p_key),
                description=p_val.get("description", ""),
                logic=p_val.get("logic", "AND"),
                thresholds=p_val.get("filters", {}),
            )
        )
    return results


@app.get(
    "/api/v1/screener/presets/{preset_name}",
    response_model=list[ScreenerCompanyItem],
    tags=["Screener"],
    summary="Run Screener Preset",
    description="Executes a named preset (e.g. 'quality_compounder', 'value_pick') and returns matching companies.",
)
def run_screener_preset(preset_name: str) -> list[ScreenerCompanyItem]:
    clean_name = preset_name.strip().lower().replace(" ", "_").replace("-", "_")
    cfg = load_screener_config_cached()
    presets = cfg.get("presets", {})

    target_preset = None
    for p_key, p_val in presets.items():
        if p_key == clean_name or p_val.get("name", "").lower().replace(" ", "_") == clean_name:
            target_preset = p_val
            break

    if not target_preset:
        valid_presets = list(presets.keys())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preset '{preset_name}' not found. Available presets: {valid_presets}",
        )

    filters = target_preset.get("filters", {})
    df = load_universe_df_cached().copy()

    for metric, bounds in filters.items():
        # Match metric column in dataframe
        col = metric
        if col not in df.columns:
            if col == "debt_to_equity":
                col = "de"
            elif col == "return_on_equity_pct":
                col = "roe"
            elif col == "operating_profit_margin_pct":
                col = "opm"
            elif col == "free_cash_flow_cr":
                col = "fcf"

        if col in df.columns:
            if "min" in bounds:
                df = df[df[col].notna() & (df[col] >= bounds["min"])]
            if "max" in bounds:
                df = df[df[col].notna() & (df[col] <= bounds["max"])]

    df["sort_score"] = df["composite_ranking_score"].fillna(-999.0)
    df = df.sort_values(by="sort_score", ascending=False)

    results: list[ScreenerCompanyItem] = []
    for _, row in df.iterrows():
        results.append(
            ScreenerCompanyItem(
                company_id=str(row["company_id"]),
                company_name=str(row["company_name"]),
                broad_sector=str(row["broad_sector"]),
                roe=float(row["roe"]) if pd.notna(row["roe"]) else None,
                roce=float(row["roce"]) if pd.notna(row["roce"]) else None,
                opm=float(row["opm"]) if pd.notna(row["opm"]) else None,
                de=float(row["de"]) if pd.notna(row["de"]) else None,
                pe_ratio=float(row["pe_ratio"]) if pd.notna(row["pe_ratio"]) else None,
                fcf_cr=float(row["fcf"]) if pd.notna(row["fcf"]) else None,
                revenue_cagr_3yr=float(row["revenue_cagr_3yr"]) if pd.notna(row["revenue_cagr_3yr"]) else None,
                composite_ranking_score=float(row["composite_ranking_score"]) if pd.notna(row["composite_ranking_score"]) else None,
                valuation_flag=str(row.get("valuation_flag", "Fair Value")),
            )
        )
    return results


# ==============================================================================
# GROUP 3: MARKET DATA & SECTOR ENDPOINTS
# ==============================================================================


@app.get(
    "/api/v1/sectors",
    response_model=list[SectorSummaryItem],
    tags=["Market Data"],
    summary="List All 11 Sectors",
    description="Returns aggregate fundamentals (avg ROE, avg OPM, median D/E, median PE, total market cap) across all 11 sectors.",
)
@app.get(
    "/sectors",
    response_model=list[SectorSummaryItem],
    tags=["Market Data"],
    summary="List All Sectors (alias)",
    include_in_schema=False,
)
def get_all_sectors() -> list[SectorSummaryItem]:
    df = load_universe_df_cached()
    results: list[SectorSummaryItem] = []
    for s_name, g in df.groupby("sector_11"):
        s_roe = float(g["roe"].dropna().mean()) if not g["roe"].dropna().empty else 0.0
        s_opm = float(g["opm"].dropna().mean()) if not g["opm"].dropna().empty else 0.0
        s_de = float(g["de"].dropna().median()) if not g["de"].dropna().empty else 0.0
        s_pe = float(g["pe_ratio"].dropna().median()) if not g["pe_ratio"].dropna().empty else 0.0
        s_mcap = float(g["market_cap_crore"].dropna().sum())

        results.append(
            SectorSummaryItem(
                sector_name=s_name,
                company_count=len(g),
                avg_roe=round(s_roe, 2),
                avg_opm=round(s_opm, 2),
                median_de=round(s_de, 2),
                median_pe=round(s_pe, 2),
                total_market_cap_cr=round(s_mcap, 2),
            )
        )
    return sorted(results, key=lambda x: x.company_count, reverse=True)


@app.get(
    "/api/v1/sectors/{sector_name}",
    response_model=SectorDetailResponse,
    tags=["Market Data"],
    summary="Get Sector Details & Constituents",
    description="Returns summary KPIs and constituent companies with latest ratios for a specific sector.",
)
def get_sector_detail(sector_name: str) -> SectorDetailResponse:
    clean_name = sector_name.strip().lower().replace("_", " ")
    df = load_universe_df_cached()

    # Match against sector_11 or broad_sector (with alias handling)
    matched = df[df["sector_11"].str.lower() == clean_name]
    if matched.empty:
        matched = df[df["broad_sector"].str.lower() == clean_name]
    if matched.empty and clean_name in ["it", "it services"]:
        matched = df[df["sector_11"] == "Information Technology"]

    if matched.empty:
        valid_sectors = sorted(df["sector_11"].unique())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sector '{sector_name}' not found. Available sectors: {valid_sectors}",
        )

    resolved_name = matched.iloc[0]["sector_11"]
    s_roe = float(matched["roe"].dropna().mean()) if not matched["roe"].dropna().empty else 0.0
    s_opm = float(matched["opm"].dropna().mean()) if not matched["opm"].dropna().empty else 0.0
    s_de = float(matched["de"].dropna().median()) if not matched["de"].dropna().empty else 0.0
    s_pe = float(matched["pe_ratio"].dropna().median()) if not matched["pe_ratio"].dropna().empty else 0.0

    companies_list: list[dict[str, Any]] = []
    for _, row in matched.sort_values(by="composite_ranking_score", ascending=False).iterrows():
        companies_list.append(
            {
                "id": str(row["company_id"]),
                "name": str(row["company_name"]),
                "roe": float(row["roe"]) if pd.notna(row["roe"]) else None,
                "opm": float(row["opm"]) if pd.notna(row["opm"]) else None,
                "de": float(row["de"]) if pd.notna(row["de"]) else None,
                "pe_ratio": float(row["pe_ratio"]) if pd.notna(row["pe_ratio"]) else None,
                "composite_score": float(row["composite_ranking_score"]) if pd.notna(row["composite_ranking_score"]) else None,
                "valuation_flag": str(row.get("valuation_flag", "Fair Value")),
            }
        )

    return SectorDetailResponse(
        sector_name=resolved_name,
        company_count=len(matched),
        avg_roe=round(s_roe, 2),
        avg_opm=round(s_opm, 2),
        median_de=round(s_de, 2),
        median_pe=round(s_pe, 2),
        companies=companies_list,
    )


@app.get(
    "/api/v1/market/overview",
    response_model=MarketOverviewResponse,
    tags=["Market Data"],
    summary="Universe Market Overview KPIs",
    description="Returns universe-wide benchmarks: avg ROE, median PE, count positive FCF, count D/E<1, and top 3 companies.",
)
@app.get(
    "/market/overview",
    response_model=MarketOverviewResponse,
    tags=["Market Data"],
    summary="Universe Market Overview (alias)",
    include_in_schema=False,
)
def get_market_overview() -> MarketOverviewResponse:
    df = load_universe_df_cached()

    u_roe = float(df["roe"].dropna().mean())
    u_pe = float(df["pe_ratio"].dropna().median())
    pos_fcf = int((df["fcf"] > 0).sum())
    low_de = int((df["de"] < 1.0).sum())

    top_cos_df = df.sort_values(by="composite_ranking_score", ascending=False).head(3)
    top_cos: list[dict[str, Any]] = []
    for _, row in top_cos_df.iterrows():
        top_cos.append(
            {
                "company_id": str(row["company_id"]),
                "company_name": str(row["company_name"]),
                "composite_score": float(row["composite_ranking_score"]) if pd.notna(row["composite_ranking_score"]) else None,
                "sector": str(row["broad_sector"]),
            }
        )

    return MarketOverviewResponse(
        total_companies=len(df),
        avg_roe=round(u_roe, 2),
        median_pe=round(u_pe, 2),
        count_positive_fcf=pos_fcf,
        count_low_leverage=low_de,
        top_companies=top_cos,
    )



# ==============================================================================
# GROUP 4: CASH FLOW & VALUATION ANALYTICS ENDPOINTS
# ==============================================================================


@app.get(
    "/api/v1/companies/{ticker}/cashflow",
    response_model=CompanyCashflowResponse,
    tags=["Company Analytics"],
    summary="Company Cash Flow Intelligence & 5Y Trend",
    description="Returns capital allocation pattern, CFO quality score/label, and trailing 5-year cash flow trend.",
)
@app.get(
    "/companies/{ticker}/cashflow",
    response_model=CompanyCashflowResponse,
    tags=["Company Analytics"],
    summary="Company Cash Flow (alias)",
    include_in_schema=False,
)
def get_company_cashflow(ticker: str) -> CompanyCashflowResponse:
    clean_ticker = ticker.strip().upper()
    conn = get_db_connection()
    cur = conn.cursor()

    # Verify company exists
    co_row = cur.execute("SELECT id, company_name FROM companies WHERE UPPER(id) = ?", (clean_ticker,)).fetchone()
    if not co_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ticker '{ticker}' not found in Nifty 100 universe.",
        )
    comp_name = co_row["company_name"]

    # Fetch latest capital allocation pattern and CFO quality
    pattern_row = cur.execute(
        """
        SELECT capital_allocation_pattern, cfo_quality_label, cfo_quality_score
        FROM financial_ratios
        WHERE UPPER(company_id) = ? AND (year LIKE '%-03' OR company_id = 'SIEMENS')
        ORDER BY year DESC LIMIT 1
        """,
        (clean_ticker,),
    ).fetchone()

    pattern = pattern_row["capital_allocation_pattern"] if pattern_row else None
    cfo_label = pattern_row["cfo_quality_label"] if pattern_row else None
    cfo_score = float(pattern_row["cfo_quality_score"]) if pattern_row and pattern_row["cfo_quality_score"] is not None else None

    # Fetch last 5 audited fiscal years from cashflow table
    cf_rows = cur.execute(
        """
        SELECT year, operating_activity, investing_activity, financing_activity, net_cash_flow
        FROM cashflow
        WHERE UPPER(company_id) = ? AND (year LIKE '%-03' OR company_id = 'SIEMENS')
        ORDER BY year DESC LIMIT 5
        """,
        (clean_ticker,),
    ).fetchall()

    trends: list[CashflowTrendItem] = []
    for r in cf_rows:
        cfo_val = float(r["operating_activity"]) if r["operating_activity"] is not None else None
        cfi_val = float(r["investing_activity"]) if r["investing_activity"] is not None else None
        cff_val = float(r["financing_activity"]) if r["financing_activity"] is not None else None
        net_val = float(r["net_cash_flow"]) if r["net_cash_flow"] is not None else None
        fcf_val = round(cfo_val + cfi_val, 2) if (cfo_val is not None and cfi_val is not None) else None

        trends.append(
            CashflowTrendItem(
                year=r["year"],
                cfo=cfo_val,
                cfi=cfi_val,
                cff=cff_val,
                fcf=fcf_val,
                net_cash_flow=net_val,
            )
        )

    return CompanyCashflowResponse(
        ticker=clean_ticker,
        company_name=comp_name,
        capital_allocation_pattern=pattern,
        cfo_quality_label=cfo_label,
        cfo_quality_score=cfo_score,
        fcf_trend_5yr=trends,
    )


@app.get(
    "/api/v1/companies/{ticker}/valuation",
    response_model=CompanyValuationResponse,
    tags=["Company Analytics"],
    summary="Company Valuation Multiples & DCF Model",
    description="Returns current PE, PB, EV/EBITDA, DCF implied value and upside, and valuation status flag.",
)
@app.get(
    "/companies/{ticker}/valuation",
    response_model=CompanyValuationResponse,
    tags=["Company Analytics"],
    summary="Company Valuation (alias)",
    include_in_schema=False,
)
def get_company_valuation(ticker: str) -> CompanyValuationResponse:
    clean_ticker = ticker.strip().upper()
    val_df = load_valuation_summary_cached()

    if val_df.empty:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Valuation summary dataset not available.",
        )

    matched = val_df[val_df["company_id"].str.upper() == clean_ticker]
    if matched.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Valuation metrics for ticker '{ticker}' not found.",
        )

    row = matched.iloc[0]
    mcap = float(row["market_cap_crore"]) if pd.notna(row.get("market_cap_crore")) else None
    fcf = float(row["free_cash_flow_cr"]) if pd.notna(row.get("free_cash_flow_cr")) else None
    dcf_val, dcf_upside = compute_dcf_implied(fcf, mcap)

    return CompanyValuationResponse(
        ticker=clean_ticker,
        company_name=str(row["company_name"]),
        broad_sector=str(row.get("broad_sector", "")),
        market_cap_crore=mcap,
        pe_ratio=float(row["pe_ratio"]) if pd.notna(row.get("pe_ratio")) else None,
        median_pe_5yr=float(row["median_pe_5yr"]) if pd.notna(row.get("median_pe_5yr")) else None,
        pb_ratio=float(row["pb_ratio"]) if pd.notna(row.get("pb_ratio")) else None,
        ev_ebitda=float(row["ev_ebitda"]) if pd.notna(row.get("ev_ebitda")) else None,
        dcf_implied_value_cr=dcf_val,
        dcf_upside_pct=dcf_upside,
        valuation_flag=str(row.get("valuation_flag", "Fair Value")),
        historical_valuation_flag=str(row.get("historical_valuation_flag", "Fair Value")),
    )


# ==============================================================================
# GROUP 5: PEER GROUPS & INSTITUTIONAL REPORTS ENDPOINTS
# ==============================================================================


@app.get(
    "/api/v1/peers/{peer_group_name}",
    response_model=PeerGroupDetailResponse,
    tags=["Peer Intelligence"],
    summary="Full Peer Group Analysis (20 Metrics)",
    description="Returns all constituent members of a peer group with percentile rankings across 20 financial metrics and leadership flags.",
)
@app.get(
    "/peers/{peer_group_name}",
    response_model=PeerGroupDetailResponse,
    tags=["Peer Intelligence"],
    summary="Peer Group Analysis (alias)",
    include_in_schema=False,
)
def get_peer_group_analysis(peer_group_name: str) -> PeerGroupDetailResponse:
    clean_query = peer_group_name.strip().lower().replace("_", " ").replace("-", " ")
    conn = get_db_connection()
    cur = conn.cursor()

    # Get available peer groups
    all_groups = [r["peer_group_name"] for r in cur.execute("SELECT DISTINCT peer_group_name FROM peer_percentiles").fetchall()]
    matched_group = next((g for g in all_groups if g.lower() == clean_query), None)

    # Alias handling (e.g. 'it' -> 'IT Services')
    if not matched_group and clean_query in ["it", "it services", "information technology"]:
        matched_group = "IT Services"

    if not matched_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peer group '{peer_group_name}' not found. Available peer groups: {sorted(all_groups)}",
        )

    # Fetch all records for this peer group
    query = """
    SELECT 
        pp.company_id,
        c.company_name,
        pp.metric_name,
        pp.metric_value,
        pp.percentile_rank,
        pp.classification,
        pp.benchmark_gap_pct
    FROM peer_percentiles pp
    LEFT JOIN companies c ON pp.company_id = c.id
    WHERE pp.peer_group_name = ?
    ORDER BY pp.company_id, pp.metric_name
    """
    rows = cur.execute(query, (matched_group,)).fetchall()

    members_map: dict[str, dict[str, Any]] = {}
    for r in rows:
        cid = r["company_id"]
        cname = r["company_name"] or cid
        if cid not in members_map:
            members_map[cid] = {
                "company_id": cid,
                "company_name": cname,
                "best_in_class_count": 0,
                "watch_list_count": 0,
                "in_line_count": 0,
                "composite_score_percentile": None,
                "composite_score_classification": None,
                "metrics": [],
            }

        classification = r["classification"]
        if classification == "Best in Class":
            members_map[cid]["best_in_class_count"] += 1
        elif classification == "Watch List":
            members_map[cid]["watch_list_count"] += 1
        elif classification == "In Line":
            members_map[cid]["in_line_count"] += 1

        if r["metric_name"] == "Composite Score":
            members_map[cid]["composite_score_percentile"] = float(r["percentile_rank"]) if r["percentile_rank"] is not None else None
            members_map[cid]["composite_score_classification"] = classification

        members_map[cid]["metrics"].append(
            PeerMetricDetail(
                metric_name=r["metric_name"],
                metric_value=float(r["metric_value"]) if r["metric_value"] is not None else None,
                percentile_rank=float(r["percentile_rank"]) if r["percentile_rank"] is not None else None,
                classification=classification,
                benchmark_gap_pct=float(r["benchmark_gap_pct"]) if r["benchmark_gap_pct"] is not None else None,
            )
        )

    members_list = [PeerMemberDetail(**m) for m in members_map.values()]
    members_list.sort(key=lambda x: x.best_in_class_count, reverse=True)

    return PeerGroupDetailResponse(
        peer_group_name=matched_group,
        total_members=len(members_list),
        metrics_count=20,
        members=members_list,
    )


@app.get(
    "/api/v1/reports/tearsheet/{ticker}",
    tags=["Reporting & Documents"],
    summary="Download Institutional Company Tearsheet PDF",
    description="Streams the pre-generated 2-page institutional PDF tearsheet for the requested ticker.",
    response_class=FileResponse,
)
@app.get(
    "/reports/tearsheet/{ticker}",
    tags=["Reporting & Documents"],
    summary="Company Tearsheet (alias)",
    response_class=FileResponse,
    include_in_schema=False,
)
def get_tearsheet_report(ticker: str) -> FileResponse:
    clean_ticker = ticker.strip().upper()
    tearsheet_path = REPO_ROOT / "reports" / "tearsheets" / f"{clean_ticker}_tearsheet.pdf"

    if not tearsheet_path.exists() or not tearsheet_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tearsheet PDF for ticker '{ticker}' not found at {tearsheet_path.name}.",
        )

    return FileResponse(
        path=tearsheet_path,
        media_type="application/pdf",
        filename=f"{clean_ticker}_tearsheet.pdf",
    )


@app.get(
    "/api/v1/reports/sector/{sector_name}",
    tags=["Reporting & Documents"],
    summary="Download Institutional Sector Report PDF",
    description="Streams the pre-generated comprehensive sector report PDF for the requested sector.",
    response_class=FileResponse,
)
@app.get(
    "/reports/sector/{sector_name}",
    tags=["Reporting & Documents"],
    summary="Sector Report (alias)",
    response_class=FileResponse,
    include_in_schema=False,
)
def get_sector_report_pdf(sector_name: str) -> FileResponse:
    clean_input = sector_name.strip().replace(" ", "_").replace("-", "_")
    sector_dir = REPO_ROOT / "reports" / "sector_reports"

    # Search for matching pdf file in sector_reports directory
    matched_file: Optional[Path] = None
    if sector_dir.exists():
        for f in sector_dir.glob("*.pdf"):
            base_name = f.stem.replace("_report", "").lower()
            if base_name == clean_input.lower() or base_name == clean_input.lower().replace("_", ""):
                matched_file = f
                break

    # Alias for IT
    if not matched_file and clean_input.lower() in ["it", "it_services", "infotech"]:
        cand = sector_dir / "Information_Technology_report.pdf"
        if cand.exists():
            matched_file = cand

    if not matched_file or not matched_file.is_file():
        available = sorted([f.stem.replace("_report", "") for f in sector_dir.glob("*.pdf")]) if sector_dir.exists() else []
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sector report for '{sector_name}' not found. Available sector reports: {available}",
        )

    return FileResponse(
        path=matched_file,
        media_type="application/pdf",
        filename=matched_file.name,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
