"""Unit tests for peer analytics engine and intra-group percentiles.

Sprint 3, Day 17: Peer Analytics Module
Tests intra-group percentile ranks, benchmark gaps, classification tiers,
null handling, and SQLite persistence across 11 peer groups and 20 metrics.
"""

from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from src.analytics.peer import (
    calculate_peer_percentiles,
    populate_peer_percentiles,
)
from src.screener.engine import DEFAULT_DB_PATH


@pytest.fixture(scope="module")
def peer_results() -> pd.DataFrame:
    """Fixture providing computed peer percentiles for all 11 peer groups."""
    return calculate_peer_percentiles()


def test_peer_percentiles_span_0_to_100(peer_results: pd.DataFrame) -> None:
    """Verify that within each peer group, percentile ranks span 0-100 (min ~0, max ~100)."""
    for (group_name, metric_name), group_data in peer_results.groupby(
        ["peer_group_name", "metric_name"]
    ):
        valid_pcts = group_data["percentile_rank"].dropna()
        if len(valid_pcts) > 1:
            min_pct = float(valid_pcts.min())
            max_pct = float(valid_pcts.max())
            assert min_pct == pytest.approx(
                0.0, abs=1e-2
            ), f"Min percentile in {group_name} - {metric_name} was {min_pct}, expected ~0"
            assert max_pct == pytest.approx(
                100.0, abs=1e-2
            ), f"Max percentile in {group_name} - {metric_name} was {max_pct}, expected ~100"
            assert (
                valid_pcts >= 0.0
            ).all(), f"Found negative percentiles in {group_name} - {metric_name}"
            assert (
                valid_pcts <= 100.0
            ).all(), f"Found percentiles > 100 in {group_name} - {metric_name}"


def test_benchmark_company_gap_is_zero_for_all_metrics(
    peer_results: pd.DataFrame,
) -> None:
    """Verify that designated benchmark companies have benchmark_gap_pct = 0 for all metrics."""
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    bench_df = pd.read_sql_query(
        "SELECT peer_group_name, company_id FROM peer_groups WHERE is_benchmark = 1;",
        conn,
    )
    conn.close()

    benchmarks = set(
        zip(bench_df["peer_group_name"], bench_df["company_id"], strict=False)
    )

    for (group_name, comp_id), comp_data in peer_results.groupby(
        ["peer_group_name", "company_id"]
    ):
        if (group_name, comp_id) in benchmarks:
            # Benchmark company gap must be exactly 0.0 for every metric
            for _, row in comp_data.iterrows():
                gap = row["benchmark_gap_pct"]
                assert (
                    gap == 0.0
                ), f"Expected gap 0.0 for benchmark {comp_id} ({group_name}) in {row['metric_name']}, got {gap}"


def test_none_metric_values_produce_none_percentile(peer_results: pd.DataFrame) -> None:
    """Verify that None metric values produce None percentile (not 0 or error)."""
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    benchmarks = set(
        pd.read_sql_query(
            "SELECT company_id FROM peer_groups WHERE is_benchmark = 1;", conn
        )["company_id"]
    )
    conn.close()

    null_rows = peer_results[peer_results["metric_value"].isna()]

    assert (
        len(null_rows) > 0
    ), "Expected at least some null metrics in peer groups (e.g. Bank OPM/ICR/ROCE)"

    for _, row in null_rows.iterrows():
        # Core prompt requirement: None metric produces None percentile (not 0 or error)
        assert pd.isna(
            row["percentile_rank"]
        ), f"Expected None percentile for null metric in {row['company_id']} - {row['metric_name']}, got {row['percentile_rank']}"
        assert pd.isna(
            row["classification"]
        ), f"Expected None classification for null metric in {row['company_id']} - {row['metric_name']}, got {row['classification']}"
        # If company is not benchmark, gap must also be None
        if row["company_id"] not in benchmarks:
            assert pd.isna(
                row["benchmark_gap_pct"]
            ), f"Expected None gap for null metric in {row['company_id']} - {row['metric_name']}, got {row['benchmark_gap_pct']}"


def test_all_11_peer_groups_represented_in_peer_percentiles() -> None:
    """Verify all 11 peer groups are persisted in peer_percentiles table with expected row count."""
    count = populate_peer_percentiles()
    assert (
        count == 1120
    ), f"Expected exactly 1,120 rows in peer_percentiles (56 cos x 20 metrics), got {count}"

    conn = sqlite3.connect(DEFAULT_DB_PATH)
    cursor = conn.cursor()

    groups = [
        r[0]
        for r in cursor.execute(
            "SELECT DISTINCT peer_group_name FROM peer_percentiles ORDER BY peer_group_name;"
        ).fetchall()
    ]
    total_in_db = cursor.execute("SELECT COUNT(*) FROM peer_percentiles;").fetchone()[0]
    conn.close()

    expected_groups = [
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
    assert sorted(groups) == sorted(expected_groups)
    assert total_in_db == 1120


def test_best_in_class_count_reasonable_per_group(peer_results: pd.DataFrame) -> None:
    """Verify 'Best in Class' count per group is reasonable (not 0, not all companies)."""
    valid_classes = {"Best in Class", "In Line", "Watch List"}

    for group_name, group_data in peer_results.groupby("peer_group_name"):
        rated_rows = group_data[group_data["classification"].notna()]
        assert len(rated_rows) > 0, f"No rated metrics in peer group {group_name}"

        # Check only valid classifications exist
        assigned_classes = set(rated_rows["classification"].unique())
        assert assigned_classes.issubset(
            valid_classes
        ), f"Unexpected classifications found in {group_name}: {assigned_classes - valid_classes}"

        best_in_class_count = int(
            (rated_rows["classification"] == "Best in Class").sum()
        )
        total_rated = len(rated_rows)

        assert (
            best_in_class_count > 0
        ), f"Expected at least one 'Best in Class' in {group_name}, got 0"
        assert (
            best_in_class_count < total_rated
        ), f"All rated rows were 'Best in Class' in {group_name} ({best_in_class_count}/{total_rated})"
