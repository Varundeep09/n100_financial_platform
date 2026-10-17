"""KMeans Clustering and Institutional Archetype Profiling (Module 12 / Sprint 6).

Performs unsupervised clustering (k=5) across the Nifty 100 universe using
multivariate financial KPIs (profitability, margin, growth, leverage, cash flow,
and composite health score). Assigns dynamic institutional archetype labels
based on centroid profiles.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("n100_clustering")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "nifty100.db"
DEFAULT_OUTPUT_CSV = REPO_ROOT / "data" / "processed" / "cluster_labels.csv"
REPORT_OUTPUT_CSV = REPO_ROOT / "reports" / "cluster_labels.csv"

EXCLUDED_TICKERS = ("SBIN", "BEL", "HAL")

FEATURE_COLUMNS = [
    "roe",
    "opm",
    "revenue_cagr_3yr",
    "debt_to_equity",
    "free_cash_flow_cr",
    "composite_score",
]


def load_clustering_dataset(db_path: Path | str | None = None) -> pd.DataFrame:
    """Extract latest fiscal year ratios per company, excluding SBIN, BEL, and HAL.

    Handles March-ending fiscal years (91 constituents) and Siemens September-ending
    fiscal year to assemble the complete 89 non-excluded company universe.
    """
    resolved_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    if not resolved_db.exists():
        raise FileNotFoundError(f"Database not found at {resolved_db}")

    conn = sqlite3.connect(resolved_db)
    query = """
    WITH march_latest AS (
        SELECT company_id, MAX(year) AS max_year
        FROM financial_ratios
        WHERE year LIKE '%-03'
        GROUP BY company_id
    ),
    siemens_latest AS (
        SELECT company_id, MAX(year) AS max_year
        FROM financial_ratios
        WHERE company_id = 'SIEMENS'
        GROUP BY company_id
    ),
    latest_years AS (
        SELECT * FROM march_latest
        UNION ALL
        SELECT * FROM siemens_latest
    )
    SELECT 
        fr.company_id,
        fr.year,
        fr.return_on_equity_pct AS roe,
        fr.operating_profit_margin_pct AS opm,
        fr.revenue_cagr_3yr,
        fr.debt_to_equity,
        fr.free_cash_flow_cr,
        fr.composite_quality_score AS composite_score
    FROM financial_ratios fr
    INNER JOIN latest_years ly 
        ON fr.company_id = ly.company_id AND fr.year = ly.max_year
    WHERE fr.company_id NOT IN ('SBIN', 'BEL', 'HAL')
    ORDER BY fr.company_id ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def assign_dynamic_archetype_labels(centroids: pd.DataFrame) -> dict[int, str]:
    """Assign meaningful institutional archetype labels based on centroid metrics.

    Evaluates relative rankings and extreme characteristics across the 5 centroids:
    1. Maximum ROE outlier -> 'High Growth & Momentum' (turnaround/hyper-ROE)
    2. Maximum OPM -> 'High Margin Infrastructure' (high-margin utilities/capex)
    3. Maximum Composite Score -> 'Quality Compounders' (top health & cash generation)
    4. Lowest / Most Negative FCF -> 'Financials & Credit Heavy' (banking/lending)
    5. Balance -> 'Value & Cyclicals' (mature, moderate leverage compounders)
    """
    assigned: dict[int, str] = {}
    remaining = set(centroids.index)

    # 1. Outlier / High Momentum ROE
    max_roe_id = centroids.loc[list(remaining), "roe"].idxmax()
    assigned[int(max_roe_id)] = "High Growth & Momentum"
    remaining.remove(max_roe_id)

    # 2. Capital Intensive / Maximum OPM
    max_opm_id = centroids.loc[list(remaining), "opm"].idxmax()
    assigned[int(max_opm_id)] = "High Margin Infrastructure"
    remaining.remove(max_opm_id)

    # 3. Quality Compounders (Highest Composite Health Score)
    max_score_id = centroids.loc[list(remaining), "composite_score"].idxmax()
    assigned[int(max_score_id)] = "Quality Compounders"
    remaining.remove(max_score_id)

    # 4. Financials / Credit Heavy (Lowest / Most Negative Free Cash Flow)
    min_fcf_id = centroids.loc[list(remaining), "free_cash_flow_cr"].idxmin()
    assigned[int(min_fcf_id)] = "Financials & Credit Heavy"
    remaining.remove(min_fcf_id)

    # 5. Remaining cluster -> Value & Cyclicals
    for rem in remaining:
        assigned[int(rem)] = "Value & Cyclicals"

    return assigned


def run_clustering(
    db_path: Path | str | None = None,
    output_path: Path | str | None = None,
    k: int = 5,
    random_state: int = 42,
) -> pd.DataFrame:
    """Execute end-to-end unsupervised KMeans clustering on 89 constituents.

    Steps:
    1. Load financial_ratios for latest fiscal year.
    2. Impute missing/None values using feature column medians (for clustering only).
    3. Normalize features using StandardScaler.
    4. Fit KMeans(n_clusters=5).
    5. Profile centroid values and assign dynamic archetype labels.
    6. Export results to CSV.
    """
    df = load_clustering_dataset(db_path)
    logger.info("Loaded %d company records for clustering analysis.", len(df))

    # Feature matrix imputation with column medians
    X = df[FEATURE_COLUMNS].copy()
    for col in FEATURE_COLUMNS:
        X[col] = pd.to_numeric(X[col], errors="coerce")
        col_median = float(X[col].median())
        X[col] = X[col].fillna(col_median)

    # Feature scaling
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # KMeans clustering
    kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    df["cluster_id"] = kmeans.fit_predict(X_scaled)

    # Profile centroids in unscaled space
    centroids = df.groupby("cluster_id")[FEATURE_COLUMNS].mean()
    label_map = assign_dynamic_archetype_labels(centroids)
    df["cluster_label"] = df["cluster_id"].map(label_map)

    # Structure export dataframe
    export_cols = [
        "company_id",
        "cluster_id",
        "cluster_label",
        "roe",
        "opm",
        "revenue_cagr_3yr",
        "debt_to_equity",
        "free_cash_flow_cr",
        "composite_score",
    ]
    result_df = df[export_cols].copy()

    # Determine destination paths
    primary_out = Path(output_path) if output_path else DEFAULT_OUTPUT_CSV
    primary_out.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(primary_out, index=False)
    logger.info("Saved cluster labels (%d rows) to %s", len(result_df), primary_out)

    # Also save to reports/ for cross-deliverable consistency
    try:
        REPORT_OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        result_df.to_csv(REPORT_OUTPUT_CSV, index=False)
        logger.info("Synchronized cluster labels to %s", REPORT_OUTPUT_CSV)
    except Exception as exc:
        logger.warning("Could not write to reports/cluster_labels.csv: %s", exc)

    return result_df


if __name__ == "__main__":
    res = run_clustering()
    print("\n--- Cluster Archetype Distribution ---")
    print(res["cluster_label"].value_counts())