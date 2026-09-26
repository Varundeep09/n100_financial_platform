"""Financial Ratios Table Population Pipeline (Sprint 2, Day 12).

Combines:
1. Profitability, Leverage & Efficiency metrics (src.analytics.ratios)
2. Revenue, PAT, and EPS CAGR metrics across 3yr, 5yr, and 10yr windows (src.analytics.cagr)
3. Cash Flow KPIs & 8-pattern Capital Allocation classifier (src.analytics.cashflow_kpis)
4. Financial baseline statement items (EPS, Book Value per Share, Dividend Payout, Total Debt, CFO)
5. Composite Quality Score (percentile rank average) and Sector Relative Benchmarking Flag.

Populates the production SQLite table `financial_ratios` in db/nifty100.db.
"""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from src.analytics.cagr import calculate_cagr_metrics
from src.analytics.cashflow_kpis import calculate_cashflow_kpis
from src.analytics.ratios import (
    DB_PATH,
    FINANCIALS_SECTOR_COMPANIES,
    REPO_ROOT,
    UNRELIABLE_BALANCESHEET_COMPANIES,
    calculate_profitability_metrics,
)

logger = logging.getLogger(__name__)

SCHEMA_PATH = REPO_ROOT / "db" / "schema.sql"

FINANCIAL_RATIOS_DDL = """
CREATE TABLE IF NOT EXISTS financial_ratios (
    company_id VARCHAR(20) NOT NULL,
    year VARCHAR(10) NOT NULL,
    net_profit_margin_pct NUMERIC,
    operating_profit_margin_pct NUMERIC,
    return_on_equity_pct NUMERIC,
    return_on_capital_employed_pct NUMERIC,
    return_on_assets_pct NUMERIC,
    debt_to_equity NUMERIC,
    high_leverage_flag INTEGER,
    interest_coverage NUMERIC,
    icr_label VARCHAR(50),
    icr_risk_flag INTEGER,
    net_debt_cr NUMERIC,
    asset_turnover NUMERIC,
    revenue_cagr_3yr NUMERIC,
    revenue_cagr_3yr_flag VARCHAR(50),
    revenue_cagr_5yr NUMERIC,
    revenue_cagr_5yr_flag VARCHAR(50),
    revenue_cagr_10yr NUMERIC,
    revenue_cagr_10yr_flag VARCHAR(50),
    pat_cagr_3yr NUMERIC,
    pat_cagr_3yr_flag VARCHAR(50),
    pat_cagr_5yr NUMERIC,
    pat_cagr_5yr_flag VARCHAR(50),
    pat_cagr_10yr NUMERIC,
    pat_cagr_10yr_flag VARCHAR(50),
    eps_cagr_3yr NUMERIC,
    eps_cagr_3yr_flag VARCHAR(50),
    eps_cagr_5yr NUMERIC,
    eps_cagr_5yr_flag VARCHAR(50),
    eps_cagr_10yr NUMERIC,
    eps_cagr_10yr_flag VARCHAR(50),
    free_cash_flow_cr NUMERIC,
    cfo_quality_score NUMERIC,
    cfo_quality_label VARCHAR(50),
    capex_intensity_pct NUMERIC,
    capex_label VARCHAR(50),
    fcf_conversion_rate_pct NUMERIC,
    fcf_conversion_label VARCHAR(50),
    capital_allocation_pattern VARCHAR(50),
    earnings_per_share NUMERIC,
    book_value_per_share NUMERIC,
    dividend_payout_ratio_pct NUMERIC,
    total_debt_cr NUMERIC,
    cash_from_operations_cr NUMERIC,
    composite_quality_score NUMERIC,
    sector_relative_flag INTEGER,
    extreme_magnitude_flag INTEGER,
    data_quality_flag INTEGER,
    data_quality_label VARCHAR(50),
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_fr_company_year ON financial_ratios(company_id, year);
CREATE INDEX IF NOT EXISTS idx_fr_quality_score ON financial_ratios(composite_quality_score);
CREATE INDEX IF NOT EXISTS idx_fr_data_quality ON financial_ratios(data_quality_flag);
CREATE INDEX IF NOT EXISTS idx_fr_extreme_magnitude ON financial_ratios(extreme_magnitude_flag);
"""


def ensure_financial_ratios_schema(conn: sqlite3.Connection) -> None:
    """Execute DDL to ensure financial_ratios table and indexes exist."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(financial_ratios);")
    cols = [r[1] for r in cursor.fetchall()]
    if cols and "extreme_magnitude_flag" not in cols:
        logger.info(
            "Migrating financial_ratios table to include extreme_magnitude_flag and data_quality fields..."
        )
        cursor.execute("DROP TABLE IF EXISTS financial_ratios;")
        conn.commit()
    conn.executescript(FINANCIAL_RATIOS_DDL)


def get_all_company_years_data(conn: sqlite3.Connection) -> pd.DataFrame:
    """Extract unified company-year dataset joining P&L, Balance Sheet, Cash Flow, and Master metadata."""
    query = """
    WITH all_company_years AS (
        SELECT company_id, year FROM profitandloss
        UNION
        SELECT company_id, year FROM balancesheet
        UNION
        SELECT company_id, year FROM cashflow
    )
    SELECT 
        acy.company_id,
        acy.year,
        pl.sales,
        pl.expenses,
        pl.operating_profit,
        pl.opm_percentage,
        pl.other_income,
        pl.interest,
        pl.depreciation,
        pl.profit_before_tax,
        pl.tax_percentage,
        pl.net_profit,
        pl.eps,
        pl.dividend_payout,
        bs.equity_capital,
        bs.reserves,
        bs.borrowings,
        bs.other_liabilities,
        bs.total_liabilities,
        bs.fixed_assets,
        bs.cwip,
        bs.investments,
        bs.other_asset,
        bs.total_assets,
        cf.operating_activity,
        cf.investing_activity,
        cf.financing_activity,
        cf.net_cash_flow,
        s.broad_sector,
        c.book_value AS master_book_value,
        c.face_value
    FROM all_company_years acy
    LEFT JOIN profitandloss pl ON acy.company_id = pl.company_id AND acy.year = pl.year
    LEFT JOIN balancesheet bs ON acy.company_id = bs.company_id AND acy.year = bs.year
    LEFT JOIN cashflow cf ON acy.company_id = cf.company_id AND acy.year = cf.year
    LEFT JOIN sectors s ON acy.company_id = s.company_id
    LEFT JOIN companies c ON acy.company_id = c.id
    ORDER BY acy.company_id, acy.year;
    """
    return pd.read_sql_query(query, conn)


def build_financial_ratios_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Run all 3 KPI engines and assemble the final 47-column financial_ratios dataset."""
    logger.info("Executing profitability, leverage, CAGR, and cash flow engines...")
    df_ratios = calculate_profitability_metrics(raw_df)
    df_cagr = calculate_cagr_metrics(raw_df)
    df_cf = calculate_cashflow_kpis(raw_df)

    final_df = pd.DataFrame()
    final_df["company_id"] = raw_df["company_id"]
    final_df["year"] = raw_df["year"]

    # 1. Profitability
    final_df["net_profit_margin_pct"] = df_ratios["npm_pct"]
    final_df["operating_profit_margin_pct"] = df_ratios["opm_pct"]
    final_df["return_on_equity_pct"] = df_ratios["roe_pct"]
    final_df["return_on_capital_employed_pct"] = df_ratios["roce_pct"]
    final_df["return_on_assets_pct"] = df_ratios["roa_pct"]

    # 2. Leverage & Efficiency
    final_df["debt_to_equity"] = df_ratios["debt_to_equity"]
    final_df["high_leverage_flag"] = df_ratios["high_leverage_flag"].astype(int)
    final_df["interest_coverage"] = df_ratios["icr"]
    final_df["icr_label"] = df_ratios["icr_label"]
    final_df["icr_risk_flag"] = df_ratios["icr_risk_flag"].astype(int)
    final_df["net_debt_cr"] = df_ratios["net_debt"]
    final_df["asset_turnover"] = df_ratios["asset_turnover"]

    # 3. Growth & CAGR (3yr, 5yr, 10yr) + flags
    cagr_cols = [
        "revenue_cagr_3yr",
        "revenue_cagr_3yr_flag",
        "revenue_cagr_5yr",
        "revenue_cagr_5yr_flag",
        "revenue_cagr_10yr",
        "revenue_cagr_10yr_flag",
        "pat_cagr_3yr",
        "pat_cagr_3yr_flag",
        "pat_cagr_5yr",
        "pat_cagr_5yr_flag",
        "pat_cagr_10yr",
        "pat_cagr_10yr_flag",
        "eps_cagr_3yr",
        "eps_cagr_3yr_flag",
        "eps_cagr_5yr",
        "eps_cagr_5yr_flag",
        "eps_cagr_10yr",
        "eps_cagr_10yr_flag",
    ]
    for col in cagr_cols:
        final_df[col] = df_cagr[col]

    # 4. Cash Flow KPIs & Capital Allocation
    final_df["free_cash_flow_cr"] = df_cf["fcf"]
    final_df["cfo_quality_score"] = df_cf["cfo_quality_score"]
    final_df["cfo_quality_label"] = df_cf["cfo_quality_label"]
    final_df["capex_intensity_pct"] = df_cf["capex_intensity"]
    final_df["capex_label"] = df_cf["capex_intensity_label"]
    final_df["fcf_conversion_rate_pct"] = df_cf["fcf_conversion_rate"]
    final_df["fcf_conversion_label"] = df_cf["fcf_conversion_label"]
    final_df["capital_allocation_pattern"] = df_cf["pattern_label"]

    # 5. Financial Baseline Items
    final_df["earnings_per_share"] = raw_df["eps"]

    # Book Value per Share (calculated as (equity + reserves) / (equity / face_value) with fallback)
    bvps_list: list[float | None] = []
    for _, r in raw_df.iterrows():
        cid = str(r["company_id"])
        if cid in UNRELIABLE_BALANCESHEET_COMPANIES:
            bvps_list.append(None)
            continue
        eq = r["equity_capital"]
        res = r["reserves"]
        fv = r["face_value"]
        mbv = r["master_book_value"]
        if (
            eq is not None
            and fv is not None
            and not pd.isna(eq)
            and not pd.isna(fv)
            and float(eq) > 0
            and float(fv) > 0
        ):
            res_val = float(res) if res is not None and not pd.isna(res) else 0.0
            shares = float(eq) / float(fv)
            bvps_list.append(round((float(eq) + res_val) / shares, 2))
        elif mbv is not None and not pd.isna(mbv):
            bvps_list.append(float(mbv))
        else:
            bvps_list.append(None)
    final_df["book_value_per_share"] = bvps_list

    final_df["dividend_payout_ratio_pct"] = raw_df["dividend_payout"]

    # Total debt (neutralized to None for corrupted balance sheet companies)
    debt_list: list[float | None] = []
    for _, r in raw_df.iterrows():
        cid = str(r["company_id"])
        if cid in UNRELIABLE_BALANCESHEET_COMPANIES:
            debt_list.append(None)
        else:
            debt_list.append(r["borrowings"])
    final_df["total_debt_cr"] = debt_list

    final_df["cash_from_operations_cr"] = raw_df["operating_activity"]

    # 6. Sector Relative Flag
    sec_flags: list[int] = []
    for _, r in raw_df.iterrows():
        cid = str(r["company_id"])
        sec = r.get("broad_sector")
        if sec == "Financials" or cid in FINANCIALS_SECTOR_COMPANIES:
            sec_flags.append(1)
        else:
            sec_flags.append(0)
    final_df["sector_relative_flag"] = sec_flags

    # 7. Extreme Magnitude & Data Quality Flags
    final_df["extreme_magnitude_flag"] = df_ratios["extreme_magnitude_flag"].astype(int)
    final_df["data_quality_flag"] = df_ratios["data_quality_flag"].astype(int)
    final_df["data_quality_label"] = df_ratios["data_quality_label"]

    # 7. Composite Quality Score (Average of normalized ROE, ROCE/ROA, and NPM percentile ranks)
    roe_clip = final_df["return_on_equity_pct"].clip(lower=-50.0, upper=100.0)
    roce_clip = (
        final_df["return_on_capital_employed_pct"]
        .fillna(final_df["return_on_assets_pct"])
        .clip(lower=-20.0, upper=80.0)
    )
    npm_clip = final_df["net_profit_margin_pct"].clip(lower=-30.0, upper=60.0)

    r_roe = roe_clip.rank(pct=True) * 100.0
    r_roce = roce_clip.rank(pct=True) * 100.0
    r_npm = npm_clip.rank(pct=True) * 100.0

    comp_score = (
        r_roe.fillna(50.0) * 0.4 + r_roce.fillna(50.0) * 0.4 + r_npm.fillna(50.0) * 0.2
    ).round(2)
    final_df["composite_quality_score"] = comp_score

    return final_df


def populate_financial_ratios(
    db_path: Path = DB_PATH,
) -> pd.DataFrame:
    """Compute and populate financial_ratios table in SQLite database."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        ensure_financial_ratios_schema(conn)

        raw_df = get_all_company_years_data(conn)
        final_df = build_financial_ratios_dataframe(raw_df)

        # Clear existing data and bulk insert
        cursor = conn.cursor()
        cursor.execute("DELETE FROM financial_ratios;")
        conn.commit()

        final_df.to_sql("financial_ratios", conn, if_exists="append", index=False)
        conn.commit()
        logger.info(
            "Successfully populated financial_ratios with %d rows across %d companies.",
            len(final_df),
            final_df["company_id"].nunique(),
        )
        return final_df
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = populate_financial_ratios()
    print(f"Populated financial_ratios table successfully: {len(df)} rows.")
