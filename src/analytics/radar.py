"""Radar chart visualization engine for peer benchmarking.

Sprint 3, Day 18: Radar Chart Generator (92 PNGs)
Generates 8-axis radar comparison charts across all 92 Nifty 100 companies,
plotting company percentile rank against peer group / sector average.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.screener.engine import DEFAULT_DB_PATH, load_screener_universe
from src.screener.ranking import add_composite_scores

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path("reports/radar_charts")

RADAR_AXIS_CONFIG: list[tuple[str, str, str]] = [
    ("ROE", "return_on_equity_pct", "ROE"),
    ("Revenue CAGR 3yr", "revenue_cagr_3yr", "Revenue CAGR 3yr"),
    ("OPM", "operating_profit_margin_pct", "OPM"),
    ("FCF", "free_cash_flow_cr", "FCF"),
    ("D/E", "debt_to_equity", "D/E (Inverted)"),
    ("Composite Score", "composite_ranking_score", "Composite Score"),
    ("Asset Turnover", "asset_turnover", "Asset Turnover"),
    ("CFO Quality Score", "cfo_quality_score", "CFO Quality Score"),
]


def precompute_sector_percentiles(
    universe_df: pd.DataFrame,
) -> dict[str, dict[str, pd.Series]]:
    """Precompute intra-sector percentiles for companies without designated peer groups.

    Args:
        universe_df: Screener universe DataFrame containing broad_sector and ratio columns.

    Returns:
        Dict mapping broad_sector to dict of metric percentiles.
    """
    sector_data: dict[str, dict[str, pd.Series]] = {}
    for sector, s_df in universe_df.groupby("broad_sector"):
        s_pcts: dict[str, pd.Series] = {}
        for m_key, u_col, _ in RADAR_AXIS_CONFIG:
            s_vals = pd.to_numeric(s_df[u_col], errors="coerce")
            valid_mask = s_vals.notna()
            n_valid = int(valid_mask.sum())
            p_series = pd.Series(index=s_df.index, dtype=float)
            if n_valid > 1:
                ranks = s_vals[valid_mask].rank(method="min", ascending=True)
                pct = ((ranks - 1.0) / (n_valid - 1.0)) * 100.0
                p_series.loc[valid_mask] = pct
            elif n_valid == 1:
                p_series.loc[valid_mask] = 100.0

            # Invert D/E percentile: 100 = lowest D/E in sector
            if m_key == "D/E":
                p_series = 100.0 - p_series

            s_pcts[m_key] = p_series

        sector_data[sector] = s_pcts

    return sector_data


def generate_single_radar_chart(
    company_id: str,
    company_name: str,
    peer_group_name: str,
    co_vals: list[float],
    peer_avgs: list[float],
    labels: list[str],
    has_asterisk: bool,
    output_path: Path,
    dpi: int = 150,
) -> Path:
    """Render and save an individual 8-axis polar radar chart.

    Args:
        company_id: Ticker symbol (e.g. 'TCS').
        company_name: Full company name.
        peer_group_name: Designated peer group or broad sector name.
        co_vals: 8 metric percentile values (0-100) for company.
        peer_avgs: 8 metric percentile average values for peer group.
        labels: 8 formatted axis labels (with asterisk if unpopulated).
        has_asterisk: True if any axis metric was None.
        output_path: Destination PNG file path.
        dpi: Chart resolution (default 150 DPI).

    Returns:
        Path to the saved PNG image.
    """
    n_axes = len(labels)
    angles = np.linspace(0, 2 * np.pi, n_axes, endpoint=False).tolist()

    # Close polar loop
    plot_angles = angles + angles[:1]
    plot_co = co_vals + co_vals[:1]
    plot_peer = peer_avgs + peer_avgs[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Clean radial concentric grids
    ax.set_rgrids(
        [20, 40, 60, 80, 100],
        labels=["20", "40", "60", "80", "100"],
        color="#94A3B8",
        size=8,
    )
    ax.set_ylim(0, 105)

    # Angular tick labels
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, size=9, weight="bold", color="#1E293B")

    # Company polygon: filled semi-transparent
    ax.plot(plot_angles, plot_co, color="#2563EB", linewidth=2.2, label=f"{company_id}")
    ax.fill(plot_angles, plot_co, color="#3B82F6", alpha=0.3)

    # Peer group average line
    ax.plot(
        plot_angles,
        plot_peer,
        color="#F59E0B",
        linewidth=1.8,
        linestyle="--",
        label=f"Peer Avg ({peer_group_name})",
    )

    # Header title
    title_name = company_name if len(company_name) <= 45 else company_name[:42] + "..."
    ax.set_title(f"{title_name} — {peer_group_name}\n", size=12, weight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), frameon=True, fontsize=9)

    # Footnote annotation for null metrics
    if has_asterisk:
        plt.figtext(
            0.5,
            0.01,
            "* Data not available (plotted as 0)",
            ha="center",
            fontsize=8,
            style="italic",
            color="#64748B",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return output_path


def generate_all_radar_charts(
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    db_path: Path | str = DEFAULT_DB_PATH,
    dpi: int = 150,
) -> dict[str, Any]:
    """Generate 8-axis radar chart PNG files for all 92 companies.

    Args:
        output_dir: Destination directory for PNG files.
        db_path: Path to SQLite database.
        dpi: Image resolution (default 150 DPI).

    Returns:
        Dict summarizing generation results with counts, failures, and file paths.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    resolved_db = Path(db_path).resolve()
    if not resolved_db.exists():
        raise FileNotFoundError(f"Database not found at: {resolved_db}")

    universe_df = load_screener_universe(db_path=resolved_db)
    if "composite_ranking_score" not in universe_df.columns:
        universe_df = add_composite_scores(universe_df)

    conn = sqlite3.connect(f"file:{resolved_db.as_posix()}?mode=ro", uri=True)
    try:
        pp_df = pd.read_sql_query("SELECT * FROM peer_percentiles;", conn)
        comp_df = pd.read_sql_query(
            "SELECT id, company_name FROM companies ORDER BY id;", conn
        )
        sectors_df = pd.read_sql_query(
            "SELECT company_id, broad_sector FROM sectors;", conn
        )
    finally:
        conn.close()

    sector_map = dict(
        zip(sectors_df["company_id"], sectors_df["broad_sector"], strict=False)
    )
    mapped_ids = set(pp_df["company_id"])

    # Precompute sector percentiles for unmapped companies
    sector_pcts = precompute_sector_percentiles(universe_df)

    generated_files: list[Path] = []
    failures: list[dict[str, str]] = []

    for _, c_row in comp_df.iterrows():
        ticker = str(c_row["id"])
        co_name = str(c_row["company_name"])

        try:
            co_vals: list[float] = []
            peer_avgs: list[float] = []
            labels: list[str] = []
            has_asterisk = False

            if ticker in mapped_ids:
                co_data = pp_df[pp_df["company_id"] == ticker]
                group_name = str(co_data["peer_group_name"].iloc[0])
                group_data = pp_df[pp_df["peer_group_name"] == group_name]

                for m_key, _, m_label in RADAR_AXIS_CONFIG:
                    row = co_data[co_data["metric_name"] == m_key]
                    val = row["percentile_rank"].iloc[0] if not row.empty else None

                    g_rows = group_data[group_data["metric_name"] == m_key]
                    g_vals = g_rows["percentile_rank"].dropna()

                    if m_key == "D/E":
                        val = (100.0 - val) if pd.notna(val) else None
                        g_vals = 100.0 - g_vals

                    g_avg = float(g_vals.mean()) if not g_vals.empty else 0.0
                    peer_avgs.append(g_avg)

                    if pd.isna(val):
                        co_vals.append(0.0)
                        labels.append(f"{m_label}*")
                        has_asterisk = True
                    else:
                        co_vals.append(float(val))
                        labels.append(m_label)
            else:
                sector = sector_map.get(ticker, "General")
                group_name = sector
                s_pct_dict = sector_pcts.get(sector, {})

                u_row = universe_df[universe_df["company_id"] == ticker]
                if u_row.empty:
                    raise ValueError(f"Company {ticker} not found in universe data")
                u_idx = u_row.index[0]

                for m_key, _, m_label in RADAR_AXIS_CONFIG:
                    metric_series = s_pct_dict.get(m_key, pd.Series(dtype=float))
                    val = (
                        metric_series.loc[u_idx]
                        if u_idx in metric_series.index
                        else None
                    )
                    g_vals = metric_series.dropna()
                    g_avg = float(g_vals.mean()) if not g_vals.empty else 0.0
                    peer_avgs.append(g_avg)

                    if pd.isna(val):
                        co_vals.append(0.0)
                        labels.append(f"{m_label}*")
                        has_asterisk = True
                    else:
                        co_vals.append(float(val))
                        labels.append(m_label)

            chart_file = out_path / f"{ticker}_radar.png"
            saved_path = generate_single_radar_chart(
                company_id=ticker,
                company_name=co_name,
                peer_group_name=group_name,
                co_vals=co_vals,
                peer_avgs=peer_avgs,
                labels=labels,
                has_asterisk=has_asterisk,
                output_path=chart_file,
                dpi=dpi,
            )
            generated_files.append(saved_path)

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to generate radar chart for %s: %s", ticker, exc)
            failures.append({"company_id": ticker, "error": str(exc)})

    summary = {
        "total_companies": len(comp_df),
        "total_generated": len(generated_files),
        "failed_count": len(failures),
        "failures": failures,
        "files": generated_files,
    }

    logger.info(
        "Radar chart batch generation complete: %d/%d generated successfully",
        len(generated_files),
        len(comp_df),
    )
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = generate_all_radar_charts()
    print(f"Total generated: {res['total_generated']}/{res['total_companies']}")
    if res["failures"]:
        print(f"Failures: {res['failures']}")
    else:
        sizes = [f.stat().st_size for f in res["files"]]
        print(
            f"File size min: {min(sizes)/1024:.1f} KB, max: {max(sizes)/1024:.1f} KB, avg: {sum(sizes)/len(sizes)/1024:.1f} KB"
        )
