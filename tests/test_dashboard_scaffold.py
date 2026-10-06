"""Unit tests for Sprint 4 Streamlit Dashboard scaffolding and navigation router.

Sprint 4 Pre-Kickoff: Dashboard Scaffolding Verification
Verifies the multi-screen architecture, 8 defined screens, and DB loader.
"""

from __future__ import annotations

from src.dashboard.app import SCREENS, load_query


def test_dashboard_eight_screens_configured() -> None:
    """Verify that all 8 required screens are defined in the dashboard navigation."""
    assert (
        len(SCREENS) == 8
    ), f"Expected exactly 8 dashboard screens, found {len(SCREENS)}"

    expected_screen_keywords = [
        "Home",
        "Company Profile",
        "Financial Screener",
        "Peer Comparison",
        "Trend Analysis",
        "Sector Analysis",
        "Capital Allocation",
        "Annual Reports",
    ]

    for keyword in expected_screen_keywords:
        assert any(
            keyword in screen for screen in SCREENS
        ), f"Missing expected screen matching keyword '{keyword}' in {SCREENS}"

    # Verify basic query functionality
    companies_df = load_query("SELECT COUNT(*) as cnt FROM companies;")
    assert (
        not companies_df.empty
    ), "load_query returned empty DataFrame for companies count"
    assert int(companies_df.iloc[0]["cnt"]) == 92, "Expected 92 companies in database"
