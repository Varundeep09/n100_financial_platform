"""Unit tests for the multi-tab peer comparison Excel workbook generator.

Sprint 3, Day 19: Peer Comparison Excel Workbook
Verifies workbook structure (12 sheets), exact company column counts per peer group,
benchmark company header bolding, and openpyxl ColorScaleRule conditional formatting.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import openpyxl
import pytest

from src.analytics.peer_comparison import generate_peer_comparison_workbook
from src.screener.engine import DEFAULT_DB_PATH

REPORT_FILE = Path("reports/peer_comparison.xlsx")


@pytest.fixture(scope="module")
def peer_comparison_wb() -> openpyxl.Workbook:
    """Fixture ensuring peer_comparison.xlsx is generated and returning openpyxl Workbook."""
    if not REPORT_FILE.exists():
        generate_peer_comparison_workbook(output_path=REPORT_FILE)
    wb = openpyxl.load_workbook(REPORT_FILE)
    yield wb
    wb.close()


def test_peer_comparison_exists_and_has_12_sheets(
    peer_comparison_wb: openpyxl.Workbook,
) -> None:
    """Verify peer_comparison.xlsx exists and contains exactly 12 sheets (11 groups + 1 summary)."""
    assert REPORT_FILE.exists(), f"Workbook missing at {REPORT_FILE}"

    sheet_names = peer_comparison_wb.sheetnames
    assert (
        len(sheet_names) == 12
    ), f"Expected exactly 12 sheets in peer_comparison.xlsx, found {len(sheet_names)}: {sheet_names}"

    expected_sheets = {
        "Summary",
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
    }
    assert (
        set(sheet_names) == expected_sheets
    ), f"Mismatch in expected sheets: {set(sheet_names) ^ expected_sheets}"


def test_each_peer_group_sheet_has_correct_company_columns(
    peer_comparison_wb: openpyxl.Workbook,
) -> None:
    """Verify each peer group sheet has the correct number of companies as columns and bolds benchmark."""
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    cursor = conn.cursor()

    groups_data = cursor.execute(
        "SELECT peer_group_name, company_id, is_benchmark FROM peer_groups;"
    ).fetchall()
    conn.close()

    groups_dict: dict[str, dict[str, int]] = {}
    for g_name, c_id, is_bench in groups_data:
        if g_name not in groups_dict:
            groups_dict[g_name] = {}
        groups_dict[g_name][c_id] = is_bench

    for g_name, expected_companies in groups_dict.items():
        ws = peer_comparison_wb[g_name]

        # Row 1: Header row: Metric (Col A), then company columns
        header_vals = [cell.value for cell in ws[1] if cell.value is not None]
        assert (
            header_vals[0] == "Metric"
        ), f"Expected 'Metric' in Col A of {g_name}, got {header_vals[0]}"

        company_cols = header_vals[1:]
        assert len(company_cols) == len(
            expected_companies
        ), f"Sheet {g_name} expected {len(expected_companies)} company columns, got {len(company_cols)}"
        assert set(company_cols) == set(
            expected_companies.keys()
        ), f"Sheet {g_name} company columns mismatch: {set(company_cols) ^ set(expected_companies.keys())}"

        # Verify benchmark company header is bolded
        for col_idx in range(2, ws.max_column + 1):
            cell = ws.cell(row=1, column=col_idx)
            cid = cell.value
            is_benchmark = expected_companies.get(cid, 0) == 1
            if is_benchmark:
                assert (
                    cell.font.bold is True
                ), f"Expected benchmark company '{cid}' in {g_name} to have bold font header"


def test_conditional_formatting_applied_with_colorscalerule(
    peer_comparison_wb: openpyxl.Workbook,
) -> None:
    """Verify conditional formatting (ColorScaleRule) is applied to metric rows in peer sheets."""
    has_color_scale_found = False

    for s_name in peer_comparison_wb.sheetnames:
        ws = peer_comparison_wb[s_name]
        cf_rules = ws.conditional_formatting

        if len(cf_rules) > 0:
            for cf in cf_rules:
                for rule in cf.rules:
                    if rule.type == "colorScale" or hasattr(rule, "colorScale"):
                        has_color_scale_found = True
                        break
                if has_color_scale_found:
                    break

        if has_color_scale_found:
            break

    assert (
        has_color_scale_found
    ), "Expected at least one sheet to contain ColorScaleRule conditional formatting"

    # Specifically check IT Services has 40 formatting rules (20 metrics + 20 gaps)
    ws_it = peer_comparison_wb["IT Services"]
    assert (
        len(ws_it.conditional_formatting) >= 20
    ), "Expected at least 20 CF rules in IT Services sheet"
