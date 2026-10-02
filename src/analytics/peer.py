"""Peer comparison and intra-group percentile analytics engine.

Sprint 3, Day 17: Peer Analytics Module
Ingests 11 predefined peer groups (56 mapped companies), calculates
intra-group percentiles across 20 financial metrics, classifies relative performance,
computes benchmark gaps, and persists results to SQLite.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from src.screener.engine import DEFAULT_DB_PATH, load_screener_universe
from src.screener.ranking import add_composite_scores

logger = logging.getLogger(__name__)

# 20 metrics specified for peer analysis
PEER_METRICS: list[tuple[str, str]] = [
    ("ROE", "return_on_equity_pct"),
    ("ROCE", "return_on_capital_employed_pct"),
    ("NPM", "net_profit_margin_pct"),
    ("OPM", "operating_profit_margin_pct"),
    ("D/E", "debt_to_equity"),
    ("ICR", "interest_coverage"),
    ("Revenue CAGR 3yr", "revenue_cagr_3yr"),
    ("PAT CAGR 3yr", "pat_cagr_3yr"),
    ("EPS CAGR 3yr", "eps_cagr_3yr"),
    ("FCF", "free_cash_flow_cr"),
    ("CFO Quality Score", "cfo_quality_score"),
    ("Asset Turnover", "asset_turnover"),
    ("CapEx Intensity", "capex_intensity_pct"),
    ("Net Profit Margin", "net_profit_margin_pct"),
    ("Composite Score", "composite_ranking_score"),
    ("PE ratio", "pe_ratio"),
    ("PB ratio", "pb_ratio"),
    ("EV/EBITDA", "ev_ebitda"),
    ("Dividend Yield", "dividend_yield_pct"),
    ("Book Value per Share", "book_value_per_share"),
]


def classify_percentile(percentile: float | None) -> str | None:
    """Classify a percentile rank into performance tiers.

    Tiers:
      - >= 75.0: "Best in Class"
      - 25.0 - 74.99: "In Line"
      - < 25.0: "Watch List"
      - None / NaN: None

    Args:
        percentile: Percentile rank (0.0 to 100.0) or None.

    Returns:
        Classification string or None if unrated.
    """
    if percentile is None or pd.isna(percentile):
        return None
    if percentile >= 75.0:
        return "Best in Class"
    if percentile >= 25.0:
        return "In Line"
    return "Watch List"


def calculate_benchmark_gap(
    company_val: float | None,
    benchmark_val: float | None,
    is_benchmark: bool = False,
) -> float | None:
    """Compute percentage gap relative to the peer group benchmark.

    Formula:
      ((company_val - benchmark_val) / abs(benchmark_val)) * 100

    Args:
        company_val: Metric value for the company.
        benchmark_val: Metric value for the designated benchmark company.
        is_benchmark: True if company is itself the benchmark.

    Returns:
        Gap percentage rounded to 2 decimal places, 0.0 for benchmark (gap vs itself), or None if uncomputable.
    """
    if is_benchmark:
        return 0.0
    if company_val is None or pd.isna(company_val):
        return None
    if benchmark_val is None or pd.isna(benchmark_val):
        return None
    if benchmark_val == 0.0:
        return 0.0 if company_val == 0.0 else None

    # Financial gap percentage relative to benchmark magnitude
    gap = ((company_val - benchmark_val) / abs(benchmark_val)) * 100.0
    return round(float(gap), 2)


def calculate_peer_percentiles(
    universe_df: pd.DataFrame | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Compute intra-group percentiles, classifications, and benchmark gaps for all peer groups.

    Args:
        universe_df: Optional pre-loaded screener universe with composite scores.
        db_path: Path to SQLite database.

    Returns:
        DataFrame containing 8 columns:
        [company_id, peer_group_name, metric_name, metric_value,
         percentile_rank, classification, benchmark_gap_pct, year]
    """
    resolved_db = Path(db_path).resolve()
    if not resolved_db.exists():
        raise FileNotFoundError(f"Database not found at: {resolved_db}")

    # Load peer_groups
    conn = sqlite3.connect(f"file:{resolved_db.as_posix()}?mode=ro", uri=True)
    try:
        peer_groups_df = pd.read_sql_query(
            "SELECT peer_group_name, company_id, is_benchmark FROM peer_groups ORDER BY peer_group_name, company_id;",
            conn,
        )
    finally:
        conn.close()

    if peer_groups_df.empty:
        raise ValueError("peer_groups table is empty in database")

    # Load or prepare universe
    if universe_df is None:
        universe_df = load_screener_universe(db_path=resolved_db)
        if "composite_ranking_score" not in universe_df.columns:
            universe_df = add_composite_scores(universe_df)
    elif "composite_ranking_score" not in universe_df.columns:
        universe_df = add_composite_scores(universe_df)

    # Merge peer group metadata with universe ratios
    merged = pd.merge(peer_groups_df, universe_df, on="company_id", how="left")

    records: list[dict] = []

    for group_name, group_data in merged.groupby("peer_group_name"):
        # Identify benchmark company
        benchmark_rows = group_data[group_data["is_benchmark"] == 1]
        benchmark_row = benchmark_rows.iloc[0] if not benchmark_rows.empty else None

        for metric_name, col_name in PEER_METRICS:
            if col_name not in group_data.columns:
                logger.warning("Column %s not found in universe data", col_name)
                continue

            values = pd.to_numeric(group_data[col_name], errors="coerce")
            valid_mask = values.notna()
            n_valid = int(valid_mask.sum())

            # Intra-group percent rank: (rank - 1) / (N - 1) * 100
            # Matches SQL PERCENT_RANK() OVER (PARTITION BY peer_group ORDER BY val ASC)
            percentiles = pd.Series(index=group_data.index, dtype=float)

            if n_valid > 1:
                ranks = values[valid_mask].rank(method="min", ascending=True)
                pct_ranks = ((ranks - 1.0) / (n_valid - 1.0)) * 100.0
                percentiles.loc[valid_mask] = pct_ranks.round(2)
            elif n_valid == 1:
                percentiles.loc[valid_mask] = 100.0

            benchmark_val = None
            if benchmark_row is not None:
                bench_raw = pd.to_numeric(
                    pd.Series([benchmark_row[col_name]]), errors="coerce"
                ).iloc[0]
                if pd.notna(bench_raw):
                    benchmark_val = float(bench_raw)

            for idx, row in group_data.iterrows():
                cid = row["company_id"]
                is_bench = bool(row["is_benchmark"])
                val = values.loc[idx]
                metric_val = float(val) if pd.notna(val) else None

                pct = percentiles.loc[idx]
                pct_rank = float(pct) if pd.notna(pct) else None
                classification = classify_percentile(pct_rank)

                gap = calculate_benchmark_gap(
                    company_val=metric_val,
                    benchmark_val=benchmark_val,
                    is_benchmark=is_bench,
                )

                year_val = str(row["year"]) if pd.notna(row.get("year")) else "2024-03"

                records.append(
                    {
                        "company_id": cid,
                        "peer_group_name": group_name,
                        "metric_name": metric_name,
                        "metric_value": metric_val,
                        "percentile_rank": pct_rank,
                        "classification": classification,
                        "benchmark_gap_pct": gap,
                        "year": year_val,
                    }
                )

    result_df = pd.DataFrame(records)
    logger.info(
        "Computed %d peer percentile records across %d peer groups",
        len(result_df),
        len(peer_groups_df["peer_group_name"].unique()),
    )
    return result_df


def populate_peer_percentiles(
    df: pd.DataFrame | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> int:
    """Populate the SQLite table peer_percentiles.

    Args:
        df: Optional pre-computed peer percentiles DataFrame.
        db_path: Path to database.

    Returns:
        Number of rows inserted into peer_percentiles table.
    """
    resolved_db = Path(db_path).resolve()
    if df is None:
        df = calculate_peer_percentiles(db_path=resolved_db)

    conn = sqlite3.connect(resolved_db)
    try:
        cursor = conn.cursor()

        # Create table if not present
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS peer_percentiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id VARCHAR(20) NOT NULL,
                peer_group_name VARCHAR(100) NOT NULL,
                metric_name VARCHAR(50) NOT NULL,
                metric_value NUMERIC,
                percentile_rank NUMERIC,
                classification VARCHAR(20),
                benchmark_gap_pct NUMERIC,
                year VARCHAR(10) NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT,
                UNIQUE (company_id, peer_group_name, metric_name, year)
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_peer_percentiles_lookup ON peer_percentiles(peer_group_name, metric_name);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_peer_percentiles_company ON peer_percentiles(company_id, metric_name);"
        )

        # Clear existing rows to prevent duplicate primary key conflicts
        cursor.execute("DELETE FROM peer_percentiles;")

        # Insert computed records
        insert_sql = """
            INSERT INTO peer_percentiles (
                company_id, peer_group_name, metric_name, metric_value,
                percentile_rank, classification, benchmark_gap_pct, year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        rows_to_insert = [
            (
                r["company_id"],
                r["peer_group_name"],
                r["metric_name"],
                r["metric_value"],
                r["percentile_rank"],
                r["classification"],
                r["benchmark_gap_pct"],
                r["year"],
            )
            for _, r in df.iterrows()
        ]

        cursor.executemany(insert_sql, rows_to_insert)
        conn.commit()
        count = len(rows_to_insert)
        logger.info("Successfully populated peer_percentiles table with %d rows", count)
        return count
    finally:
        conn.close()


def get_peer_percentiles(
    peer_group_name: str | None = None,
    company_id: str | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Retrieve peer percentile data from SQLite.

    Args:
        peer_group_name: Optional peer group filter.
        company_id: Optional company ID filter.
        db_path: Path to SQLite database.

    Returns:
        Filtered peer percentiles DataFrame.
    """
    resolved_db = Path(db_path).resolve()
    conn = sqlite3.connect(f"file:{resolved_db.as_posix()}?mode=ro", uri=True)
    try:
        query = "SELECT * FROM peer_percentiles WHERE 1=1"
        params: list[str] = []
        if peer_group_name:
            query += " AND peer_group_name = ?"
            params.append(peer_group_name)
        if company_id:
            query += " AND company_id = ?"
            params.append(company_id)
        query += " ORDER BY peer_group_name, company_id, metric_name;"
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rows = populate_peer_percentiles()
    print(f"Populated {rows} rows into peer_percentiles table.")
