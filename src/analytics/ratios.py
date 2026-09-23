"""Financial ratio computation engine (Profitability, Leverage, and Efficiency).

Includes:
- Profitability: NPM, OPM, ROE, ROCE, ROA.
- Leverage & Solvency: Debt-to-Equity, High Leverage Flag, Interest Coverage Ratio (ICR), Net Debt.
- Efficiency: Asset Turnover.
- Evidence-based Financials sector handling:
  * 16 confirmed banking/financing-template companies (where operating_profit is Operating Expenses/Financing Profit) -> OPM=None, ROCE=None, ICR=None ('Not Applicable (Banking Template)').
  * 7 clean Financials (JIOFIN, IRFC, RECLTD, BAJAJFINSV, BAJAJHLDNG, LICI, SBILIFE) -> Compute real OPM, ROCE, ICR normally, keeping sector_relative=True.
- Extreme value sanity flagging (|ROE| > 200%, |ROA| > 100%, |ROCE| > 200%) for near-zero equity/asset bases (INDIGO).
- Graceful None handling for zero/negative denominators or missing balance sheets (e.g. SBIN).
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "db" / "nifty100.db"

# Global log of OPM cross-check discrepancies
OPM_DISCREPANCIES: list[dict[str, Any]] = []

# Confirmed 16 companies with banking/financing P&L template or shifted columns
BANKING_TEMPLATE_COMPANIES: set[str] = {
    "AXISBANK",
    "BANKBARODA",
    "CANBK",
    "HDFCBANK",
    "ICICIBANK",
    "INDUSINDBK",
    "KOTAKBANK",
    "PNB",
    "SBIN",
    "BAJFINANCE",
    "CHOLAFIN",
    "PFC",
    "SHRIRAMFIN",
    "HDFCLIFE",
    "ICICIGI",
    "ICICIPRULI",
}

# All 23 Financials sector companies where high leverage is structurally normal
FINANCIALS_SECTOR_COMPANIES: set[str] = {
    "AXISBANK",
    "BAJAJFINSV",
    "BAJAJHLDNG",
    "BAJFINANCE",
    "BANKBARODA",
    "CANBK",
    "CHOLAFIN",
    "HDFCBANK",
    "HDFCLIFE",
    "ICICIBANK",
    "ICICIGI",
    "ICICIPRULI",
    "INDUSINDBK",
    "IRFC",
    "JIOFIN",
    "KOTAKBANK",
    "LICI",
    "PFC",
    "PNB",
    "RECLTD",
    "SBILIFE",
    "SBIN",
    "SHRIRAMFIN",
}


def normalize_pl_statement(
    sales: float | None,
    expenses: float | None,
    operating_profit: float | None,
    opm_percentage: float | None,
    other_income: float | None,
    depreciation: float | None,
    profit_before_tax: float | None,
    net_profit: float | None,
    company_id: str | None = None,
    broad_sector: str | None = None,
) -> dict[str, Any]:
    """Normalize and remap P&L line items based on evidence-based classification."""
    is_financial = broad_sector == "Financials"
    is_banking_template = (
        company_id in BANKING_TEMPLATE_COMPANIES if company_id else False
    )

    if is_banking_template:
        return {
            "true_sales": sales,
            "true_expenses": expenses,
            "true_operating_profit": None,
            "true_other_income": None,
            "true_depreciation": depreciation,
            "true_pbt": profit_before_tax,
            "true_net_profit": net_profit,
            "is_financial": True,
            "is_shifted": False,
            "is_banking_template": True,
            "status": "BANKING_TEMPLATE_FINANCIAL",
        }

    s_val = float(sales) if sales is not None and not np.isnan(sales) else 0.0
    e_val = float(expenses) if expenses is not None and not np.isnan(expenses) else 0.0
    op_val = (
        float(operating_profit)
        if operating_profit is not None and not np.isnan(operating_profit)
        else 0.0
    )
    opm_col_val = (
        float(opm_percentage)
        if opm_percentage is not None and not np.isnan(opm_percentage)
        else 0.0
    )

    std_diff = abs(s_val - e_val - op_val)
    shift_diff = abs(s_val - op_val - opm_col_val)
    tolerance = max(2.0, 0.02 * abs(s_val))

    if not is_financial and shift_diff <= tolerance and std_diff > tolerance:
        return {
            "true_sales": sales,
            "true_expenses": operating_profit,
            "true_operating_profit": opm_percentage,
            "true_other_income": expenses,
            "true_depreciation": depreciation,
            "true_pbt": profit_before_tax,
            "true_net_profit": net_profit,
            "is_financial": False,
            "is_shifted": True,
            "is_banking_template": False,
            "status": "SHIFTED_NON_FINANCIAL_RECOVERED",
        }

    status = "CLEAN_FINANCIAL" if is_financial else "STANDARD_NON_FINANCIAL"
    return {
        "true_sales": sales,
        "true_expenses": expenses,
        "true_operating_profit": operating_profit,
        "true_other_income": other_income,
        "true_depreciation": depreciation,
        "true_pbt": profit_before_tax,
        "true_net_profit": net_profit,
        "is_financial": is_financial,
        "is_shifted": False,
        "is_banking_template": False,
        "status": status,
    }


def compute_npm(net_profit: float | None, sales: float | None) -> float | None:
    """Calculate Net Profit Margin as (net_profit / sales) * 100, returning None if sales <= 0."""
    if net_profit is None or sales is None:
        return None
    if isinstance(net_profit, (float, np.floating)) and np.isnan(net_profit):
        return None
    if isinstance(sales, (float, np.floating)) and np.isnan(sales):
        return None
    if abs(float(sales)) < 1e-9:
        return None
    return round((float(net_profit) / float(sales)) * 100.0, 4)


def compute_opm(
    operating_profit: float | None,
    sales: float | None,
    source_opm: float | None = None,
    company_id: str | None = None,
    year: str | None = None,
    is_banking_template: bool = False,
) -> float | None:
    """Calculate Operating Profit Margin as (operating_profit / sales) * 100, returning None for banking templates."""
    if is_banking_template or (company_id and company_id in BANKING_TEMPLATE_COMPANIES):
        return None

    if operating_profit is None or sales is None:
        return None
    if isinstance(operating_profit, (float, np.floating)) and np.isnan(
        operating_profit
    ):
        return None
    if isinstance(sales, (float, np.floating)) and np.isnan(sales):
        return None
    if abs(float(sales)) < 1e-9:
        return None

    computed_opm = round((float(operating_profit) / float(sales)) * 100.0, 4)

    if source_opm is not None and not (
        isinstance(source_opm, (float, np.floating)) and np.isnan(source_opm)
    ):
        diff = abs(computed_opm - float(source_opm))
        if diff > 1.0:
            discrepancy = {
                "company_id": company_id or "UNKNOWN",
                "year": year or "UNKNOWN",
                "sales": float(sales),
                "operating_profit": float(operating_profit),
                "computed_opm": computed_opm,
                "source_opm": float(source_opm),
                "diff": round(diff, 4),
            }
            OPM_DISCREPANCIES.append(discrepancy)
            logger.debug(
                f"OPM mismatch for {company_id} ({year}): computed={computed_opm}%, source={source_opm}% (diff={diff:.2f}%)"
            )

    return computed_opm


def compute_roe(
    net_profit: float | None,
    equity_capital: float | None,
    reserves: float | None,
) -> float | None:
    """Calculate Return on Equity as (net_profit / (equity_capital + reserves)) * 100, returning None if equity <= 0."""
    if net_profit is None or equity_capital is None or reserves is None:
        return None
    for val in [net_profit, equity_capital, reserves]:
        if isinstance(val, (float, np.floating)) and np.isnan(val):
            return None
    total_equity = float(equity_capital) + float(reserves)
    if total_equity <= 0.0:
        return None
    return round((float(net_profit) / total_equity) * 100.0, 4)


def compute_roce(
    operating_profit: float | None,
    depreciation: float | None,
    equity_capital: float | None,
    reserves: float | None,
    borrowings: float | None,
    broad_sector: str | None = None,
    is_banking_template: bool = False,
) -> dict[str, Any]:
    """Calculate ROCE as EBIT / Capital Employed, returning None for banking templates but preserving sector_relative flag."""
    is_financials = broad_sector == "Financials"
    if is_banking_template:
        return {"value": None, "sector_relative": True}

    if operating_profit is None or equity_capital is None or reserves is None:
        return {"value": None, "sector_relative": is_financials}
    for val in [operating_profit, equity_capital, reserves]:
        if isinstance(val, (float, np.floating)) and np.isnan(val):
            return {"value": None, "sector_relative": is_financials}

    depr_val = (
        float(depreciation)
        if depreciation is not None and not np.isnan(depreciation)
        else 0.0
    )
    bor_val = (
        float(borrowings)
        if borrowings is not None and not np.isnan(borrowings)
        else 0.0
    )

    ebit = float(operating_profit) - depr_val
    capital_employed = float(equity_capital) + float(reserves) + bor_val

    if capital_employed <= 0.0:
        return {"value": None, "sector_relative": is_financials}

    roce_val = round((ebit / capital_employed) * 100.0, 4)
    return {"value": roce_val, "sector_relative": is_financials}


def compute_roa(net_profit: float | None, total_assets: float | None) -> float | None:
    """Calculate Return on Assets as (net_profit / total_assets) * 100, returning None if assets <= 0."""
    if net_profit is None or total_assets is None:
        return None
    if isinstance(net_profit, (float, np.floating)) and np.isnan(net_profit):
        return None
    if isinstance(total_assets, (float, np.floating)) and np.isnan(total_assets):
        return None
    if float(total_assets) <= 0.0:
        return None
    return round((float(net_profit) / float(total_assets)) * 100.0, 4)


def check_extreme_magnitude_flag(
    roe: float | None,
    roce: float | None,
    roa: float | None,
) -> bool:
    """Flag extreme statistical outlier ratios driven by near-zero equity/asset denominators."""
    if roe is not None and abs(roe) > 200.0:
        return True
    if roce is not None and abs(roce) > 200.0:
        return True
    return bool(roa is not None and abs(roa) > 100.0)


# =============================================================================
# LEVERAGE & EFFICIENCY RATIOS (DAY 9)
# =============================================================================


def compute_debt_to_equity(
    borrowings: float | None,
    equity_capital: float | None,
    reserves: float | None,
) -> float | None:
    """Calculate Debt-to-Equity as borrowings / (equity_capital + reserves), returning 0 if borrowings == 0."""
    if equity_capital is None or reserves is None:
        return None
    for val in [equity_capital, reserves]:
        if isinstance(val, (float, np.floating)) and np.isnan(val):
            return None
    total_equity = float(equity_capital) + float(reserves)
    if total_equity <= 0.0:
        return None
    if borrowings is None or (
        isinstance(borrowings, (float, np.floating)) and np.isnan(borrowings)
    ):
        return None
    b_val = float(borrowings)
    if abs(b_val) < 1e-9:
        return 0.0
    return round(b_val / total_equity, 4)


def check_high_leverage_flag(
    debt_to_equity: float | None,
    broad_sector: str | None = None,
    company_id: str | None = None,
) -> bool:
    """Flag high leverage if D/E > 5 and company is NOT in the Financials sector."""
    if broad_sector == "Financials":
        return False
    if company_id and company_id in FINANCIALS_SECTOR_COMPANIES:
        return False
    if debt_to_equity is None or (
        isinstance(debt_to_equity, (float, np.floating)) and np.isnan(debt_to_equity)
    ):
        return False
    return float(debt_to_equity) > 5.0


def compute_interest_coverage(
    operating_profit: float | None,
    other_income: float | None = None,
    interest: float | None = None,
    company_id: str | None = None,
    is_banking_template: bool = False,
) -> dict[str, Any]:
    """Calculate Interest Coverage Ratio (ICR) as (operating_profit + other_income) / interest."""
    if is_banking_template or (company_id and company_id in BANKING_TEMPLATE_COMPANIES):
        return {
            "value": None,
            "label": "Not Applicable (Banking Template)",
            "risk_flag": False,
        }

    if interest is None or (
        isinstance(interest, (float, np.floating)) and np.isnan(interest)
    ):
        return {
            "value": None,
            "label": "Debt Free",
            "risk_flag": False,
        }

    i_val = float(interest)
    if abs(i_val) < 1e-9:
        return {
            "value": None,
            "label": "Debt Free",
            "risk_flag": False,
        }

    if operating_profit is None or (
        isinstance(operating_profit, (float, np.floating))
        and np.isnan(operating_profit)
    ):
        return {
            "value": None,
            "label": "Debt Free",
            "risk_flag": False,
        }

    op_val = float(operating_profit)
    oth_val = (
        float(other_income)
        if other_income is not None and not np.isnan(other_income)
        else 0.0
    )

    icr_val = round((op_val + oth_val) / i_val, 4)
    risk_flag = icr_val < 1.5

    return {
        "value": icr_val,
        "label": "Normal",
        "risk_flag": risk_flag,
    }


def compute_net_debt(
    borrowings: float | None,
    investments: float | None = None,
) -> float | None:
    """Calculate Net Debt as borrowings - investments."""
    if borrowings is None or (
        isinstance(borrowings, (float, np.floating)) and np.isnan(borrowings)
    ):
        return None
    b_val = float(borrowings)
    inv_val = (
        float(investments)
        if investments is not None and not np.isnan(investments)
        else 0.0
    )
    return round(b_val - inv_val, 4)


def compute_asset_turnover(
    sales: float | None,
    total_assets: float | None,
) -> float | None:
    """Calculate Asset Turnover as sales / total_assets, returning None if total_assets <= 0."""
    if sales is None or total_assets is None:
        return None
    if isinstance(sales, (float, np.floating)) and np.isnan(sales):
        return None
    if isinstance(total_assets, (float, np.floating)) and np.isnan(total_assets):
        return None
    a_val = float(total_assets)
    if a_val <= 0.0:
        return None
    return round(float(sales) / a_val, 4)


def get_financial_statements_data(
    company_id: str | None = None,
    db_path: Path = DB_PATH,
    conn: sqlite3.Connection | None = None,
) -> pd.DataFrame:
    """Extract joined annual financial statement records using exact (company_id, year) matching."""
    should_close = False
    if conn is None:
        conn = sqlite3.connect(str(db_path))
        should_close = True

    try:
        where_clause = f"WHERE pl.company_id = '{company_id}'" if company_id else ""
        query = f"""
            SELECT pl.company_id, pl.year, 
                   pl.sales, pl.expenses, pl.operating_profit, pl.opm_percentage, 
                   pl.other_income, pl.interest, pl.depreciation, pl.profit_before_tax, 
                   pl.tax_percentage, pl.net_profit, pl.eps,
                   bs.equity_capital, bs.reserves, bs.borrowings, bs.other_liabilities, 
                   bs.total_liabilities, bs.fixed_assets, bs.cwip, bs.investments, 
                   bs.other_asset, bs.total_assets,
                   s.broad_sector
            FROM profitandloss pl
            LEFT JOIN balancesheet bs ON pl.company_id = bs.company_id AND pl.year = bs.year
            LEFT JOIN sectors s ON pl.company_id = s.company_id
            {where_clause}
            ORDER BY pl.company_id, pl.year;
        """
        return pd.read_sql_query(query, conn)
    except (sqlite3.Error, OSError) as exc:
        logger.error(f"Failed to query financial statements data: {exc}")
        return pd.DataFrame()
    finally:
        if should_close and conn is not None:
            conn.close()


def calculate_profitability_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all profitability, leverage, and efficiency ratios across a joined financial statements DataFrame."""
    if df.empty:
        return pd.DataFrame()

    out_df = df.copy()

    # Profitability lists
    npm_list: list[float | None] = []
    opm_list: list[float | None] = []
    roe_list: list[float | None] = []
    roce_list: list[float | None] = []
    roce_sec_list: list[bool] = []
    roa_list: list[float | None] = []
    norm_status_list: list[str] = []
    extreme_flag_list: list[bool] = []

    # Leverage & Efficiency lists (Day 9)
    de_list: list[float | None] = []
    high_lev_list: list[bool] = []
    icr_list: list[float | None] = []
    icr_label_list: list[str] = []
    icr_risk_list: list[bool] = []
    net_debt_list: list[float | None] = []
    asset_turnover_list: list[float | None] = []

    for _, row in out_df.iterrows():
        comp_id = row.get("company_id")
        broad_sector = row.get("broad_sector")
        norm = normalize_pl_statement(
            sales=row.get("sales"),
            expenses=row.get("expenses"),
            operating_profit=row.get("operating_profit"),
            opm_percentage=row.get("opm_percentage"),
            other_income=row.get("other_income"),
            depreciation=row.get("depreciation"),
            profit_before_tax=row.get("profit_before_tax"),
            net_profit=row.get("net_profit"),
            company_id=comp_id,
            broad_sector=broad_sector,
        )

        true_sales = norm["true_sales"]
        true_op = norm["true_operating_profit"]
        true_oth = norm["true_other_income"]
        true_depr = norm["true_depreciation"]
        true_net_profit = norm["true_net_profit"]
        is_banking_template = norm["is_banking_template"]
        norm_status_list.append(norm["status"])

        # 1. NPM
        npm_val = compute_npm(true_net_profit, true_sales)
        npm_list.append(npm_val)

        # 2. OPM
        source_opm = (
            norm["true_other_income"]
            if norm["is_shifted"]
            else row.get("opm_percentage")
        )
        opm_val = compute_opm(
            true_op,
            true_sales,
            source_opm=source_opm,
            company_id=comp_id,
            year=row.get("year"),
            is_banking_template=is_banking_template,
        )
        opm_list.append(opm_val)

        # 3. ROE
        roe_val = compute_roe(
            true_net_profit,
            row.get("equity_capital"),
            row.get("reserves"),
        )
        roe_list.append(roe_val)

        # 4. ROCE
        roce_dict = compute_roce(
            true_op,
            true_depr,
            row.get("equity_capital"),
            row.get("reserves"),
            row.get("borrowings"),
            broad_sector=broad_sector,
            is_banking_template=is_banking_template,
        )
        roce_val = roce_dict["value"]
        roce_list.append(roce_val)
        roce_sec_list.append(roce_dict["sector_relative"])

        # 5. ROA
        roa_val = compute_roa(true_net_profit, row.get("total_assets"))
        roa_list.append(roa_val)

        # 6. Extreme magnitude flag
        extreme_flag = check_extreme_magnitude_flag(roe_val, roce_val, roa_val)
        extreme_flag_list.append(extreme_flag)

        # 7. Debt-to-Equity
        de_val = compute_debt_to_equity(
            borrowings=row.get("borrowings"),
            equity_capital=row.get("equity_capital"),
            reserves=row.get("reserves"),
        )
        de_list.append(de_val)

        # 8. High Leverage Flag
        high_lev_flag = check_high_leverage_flag(
            debt_to_equity=de_val,
            broad_sector=broad_sector,
            company_id=comp_id,
        )
        high_lev_list.append(high_lev_flag)

        # 9. Interest Coverage Ratio (ICR)
        icr_dict = compute_interest_coverage(
            operating_profit=true_op,
            other_income=true_oth,
            interest=row.get("interest"),
            company_id=comp_id,
            is_banking_template=is_banking_template,
        )
        icr_list.append(icr_dict["value"])
        icr_label_list.append(icr_dict["label"])
        icr_risk_list.append(icr_dict["risk_flag"])

        # 10. Net Debt
        net_debt_val = compute_net_debt(
            borrowings=row.get("borrowings"),
            investments=row.get("investments"),
        )
        net_debt_list.append(net_debt_val)

        # 11. Asset Turnover
        at_val = compute_asset_turnover(
            sales=true_sales,
            total_assets=row.get("total_assets"),
        )
        asset_turnover_list.append(at_val)

    # Attach columns to DataFrame
    out_df["npm_pct"] = npm_list
    out_df["opm_pct"] = opm_list
    out_df["roe_pct"] = roe_list
    out_df["roce_pct"] = roce_list
    out_df["roce_sector_relative"] = roce_sec_list
    out_df["roa_pct"] = roa_list
    out_df["extreme_magnitude_flag"] = extreme_flag_list
    out_df["pl_normalization_status"] = norm_status_list

    # Leverage & Efficiency columns
    out_df["debt_to_equity"] = de_list
    out_df["high_leverage_flag"] = high_lev_list
    out_df["icr"] = icr_list
    out_df["icr_label"] = icr_label_list
    out_df["icr_risk_flag"] = icr_risk_list
    out_df["net_debt"] = net_debt_list
    out_df["asset_turnover"] = asset_turnover_list

    return out_df
