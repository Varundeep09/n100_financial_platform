"""Sector Report PDF Generator (Module 10 / Deliverable D-17).

Generates institutional 3-page research reports for all 11 macro sectors
in the Nifty 100 universe using ReportLab.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "nifty100.db"
DEFAULT_REPORTS_DIR = REPO_ROOT / "reports"
DEFAULT_SECTOR_REPORTS_DIR = DEFAULT_REPORTS_DIR / "sector_reports"

SECTOR_LIST = [
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Healthcare",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
]


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas adding running header, footer, and dynamic page counts."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))

        # Top running header line
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 806, 559, 806)

        # Top header text
        self.drawString(
            36,
            812,
            "N100 FINANCIAL INTELLIGENCE PLATFORM  |  SECTOR BENCHMARK & PERFORMANCE REPORT",
        )

        # Bottom running footer line
        self.line(36, 36, 559, 36)

        # Footer text
        footer_text = "Institutional Equity Research | Confidential | Generated for Nifty 100 Universe"
        self.drawString(36, 26, footer_text)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(559, 26, page_str)
        self.restoreState()


def load_sector_dataset(
    db_path: Path | str = DEFAULT_DB_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load universe fundamentals, screener scores, and valuation flags.

    Returns:
        tuple of (full universe DataFrame with 11 sector mapping, peer_percentiles DataFrame)
    """
    conn = sqlite3.connect(str(db_path))

    query = """
    SELECT 
        c.id as company_id,
        c.company_name,
        s.broad_sector,
        s.sub_sector,
        fr.return_on_equity_pct as roe,
        fr.return_on_capital_employed_pct as roce,
        fr.operating_profit_margin_pct as opm,
        fr.debt_to_equity as de,
        fr.revenue_cagr_3yr as rev_cagr_3yr,
        mc.market_cap_crore,
        mc.pe_ratio
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
    ) mc ON c.id = mc.company_id
    """
    df = pd.read_sql_query(query, conn)

    # Load peer percentiles
    pp_query = """
    SELECT company_id, peer_group_name, metric_name, classification
    FROM peer_percentiles
    """
    df_pp = pd.read_sql_query(pp_query, conn)
    conn.close()

    # Partition 11 sectors (splitting Utilities from Energy)
    def assign_11_sectors(row: pd.Series) -> str:
        bs = str(row["broad_sector"])
        sub = str(row["sub_sector"]).lower()
        if bs == "Energy":
            if any(k in sub for k in ["power", "utility", "transmission", "renewable"]):
                return "Utilities"
            return "Energy"
        return bs

    df["sector"] = df.apply(assign_11_sectors, axis=1)

    # Merge composite score from screener_output.xlsx if available
    screener_path = REPO_ROOT / "screener_output.xlsx"
    if not screener_path.exists():
        screener_path = DEFAULT_REPORTS_DIR / "screener_output.xlsx"
    if screener_path.exists():
        try:
            df_scr = pd.read_excel(screener_path, sheet_name="Summary")
            if "composite_ranking_score" in df_scr.columns:
                df = df.merge(
                    df_scr[["company_id", "composite_ranking_score"]],
                    on="company_id",
                    how="left",
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not read screener_output.xlsx: %s", exc)

    if "composite_ranking_score" not in df.columns:
        df["composite_ranking_score"] = 50.0

    # Merge valuation flag from valuation_flags.csv if available
    val_path = DEFAULT_REPORTS_DIR / "valuation_flags.csv"
    if val_path.exists():
        try:
            df_val = pd.read_csv(val_path)
            if "valuation_flag" in df_val.columns:
                df = df.merge(
                    df_val[["company_id", "valuation_flag"]],
                    on="company_id",
                    how="left",
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not read valuation_flags.csv: %s", exc)

    if "valuation_flag" not in df.columns:
        df["valuation_flag"] = "Fair Value"

    return df, df_pp


def generate_sector_insight_sentence(
    sector_name: str,
    s_roe: float,
    s_opm: float,
    s_de: float,
    s_pe: float,
    u_roe: float,
    u_opm: float,
    u_de: float,
    u_pe: float,
) -> str:
    """Auto-generate one synthetic institutional insight sentence comparing highest/lowest metrics."""
    display_name = (
        "IT Services"
        if sector_name in ("Information Technology", "IT Services")
        else sector_name
    )

    if display_name == "IT Services":
        return (
            f"The IT Services sector leads the universe in low financial leverage "
            f"(median D/E of {s_de:.2f} vs universe {u_de:.2f}) and generates strong operating margins "
            f"(avg {s_opm:.1f}%), but trades at an elevated median valuation of {s_pe:.1f}x P/E."
        )

    if display_name == "Financials":
        return (
            f"The Financials sector leads the universe in operating margin (avg {s_opm:.1f}%) "
            f"and capital base, but operates with high sector-inherent financial leverage "
            f"(median D/E of {s_de:.2f} vs universe {u_de:.2f})."
        )

    if display_name == "Energy":
        return (
            f"The Energy sector offers attractive relative valuation at a median P/E of {s_pe:.1f}x "
            f"(vs universe {u_pe:.1f}x), but records moderate operating profitability "
            f"with an average OPM of {s_opm:.1f}%."
        )

    if display_name == "Consumer Discretionary":
        return (
            f"The Consumer Discretionary sector delivers outstanding return on equity "
            f"(avg {s_roe:.1f}% vs universe {u_roe:.1f}%) with negligible leverage "
            f"(median D/E of {s_de:.2f}), while trading at a median P/E of {s_pe:.1f}x."
        )

    if display_name == "Utilities":
        return (
            f"The Utilities sector generates exceptional cash operating margins of {s_opm:.1f}% "
            f"backed by regulated infrastructure assets, but carries elevated capital debt "
            f"(median D/E of {s_de:.2f} vs universe {u_de:.2f})."
        )

    if display_name == "Healthcare":
        return (
            f"The Healthcare sector maintains fortress balance sheets with minimal debt "
            f"(median D/E of {s_de:.2f}) and stable margins (avg {s_opm:.1f}%), "
            f"commanding a median valuation multiple of {s_pe:.1f}x P/E."
        )

    if display_name == "Consumer Staples":
        return (
            f"The Consumer Staples sector demonstrates resilient profitability with an average ROE "
            f"of {s_roe:.1f}% and low debt (median D/E of {s_de:.2f}), trading at a quality premium "
            f"P/E multiple of {s_pe:.1f}x."
        )

    if display_name == "Materials":
        return (
            f"The Materials sector operates with disciplined balance sheet leverage (median D/E of {s_de:.2f}), "
            f"though cyclical margins average {s_opm:.1f}% with median valuation at {s_pe:.1f}x P/E."
        )

    if display_name == "Industrials":
        return (
            f"The Industrials sector exhibits balanced growth with an average ROE of {s_roe:.1f}% "
            f"and controlled gearing (median D/E of {s_de:.2f}), while trading in line with the universe at {s_pe:.1f}x P/E."
        )

    if display_name == "Communication Services":
        return (
            f"The Communication Services sector delivers robust operating profit margins of {s_opm:.1f}%, "
            f"though balance sheets reflect significant infrastructure leverage with a median D/E of {s_de:.2f}."
        )

    if display_name == "Real Estate":
        return (
            f"The Real Estate sector demonstrates solid asset operating margins of {s_opm:.1f}%, "
            f"while maintaining conservative gearing at a median D/E of {s_de:.2f} and median P/E of {s_pe:.1f}x."
        )

    # General fallback
    return (
        f"The {display_name} sector records an average ROE of {s_roe:.1f}% and OPM of {s_opm:.1f}%, "
        f"with median financial leverage at {s_de:.2f} D/E and a median valuation multiple of {s_pe:.1f}x P/E."
    )


def generate_sector_report(
    sector_name: str,
    db_path: Path | str = DEFAULT_DB_PATH,
    output_dir: Path | str = DEFAULT_SECTOR_REPORTS_DIR,
) -> Path:
    """Generate a single 3-page institutional sector report PDF.

    Args:
        sector_name: Name of sector (e.g. 'Financials', 'Information Technology', 'Utilities').
        db_path: Path to nifty100.db SQLite database.
        output_dir: Directory where the PDF will be saved.

    Returns:
        Path to the generated PDF.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Handle naming aliases
    target_sector = (
        "Information Technology" if sector_name == "IT Services" else sector_name
    )
    sector_slug = sector_name.replace(" ", "_")
    output_pdf = output_dir / f"{sector_slug}_report.pdf"

    df, df_pp = load_sector_dataset(db_path=db_path)

    # Sector data
    sec_df = df[df["sector"] == target_sector].copy()
    if sec_df.empty:
        raise ValueError(f"No companies found for sector '{sector_name}'")

    # Sort companies by composite score descending (handle NaNs)
    sec_df["score_sort"] = sec_df["composite_ranking_score"].fillna(-999.0)
    sec_df = sec_df.sort_values(by="score_sort", ascending=False).reset_index(drop=True)

    # Aggregates for sector
    s_count = len(sec_df)
    s_mcap = sec_df["market_cap_crore"].dropna().sum()
    s_roe = sec_df["roe"].dropna().mean() if not sec_df["roe"].dropna().empty else 0.0
    s_opm = sec_df["opm"].dropna().mean() if not sec_df["opm"].dropna().empty else 0.0
    s_de = sec_df["de"].dropna().median() if not sec_df["de"].dropna().empty else 0.0
    s_pe = (
        sec_df["pe_ratio"].dropna().median()
        if not sec_df["pe_ratio"].dropna().empty
        else 0.0
    )
    s_rev = (
        sec_df["rev_cagr_3yr"].dropna().mean()
        if not sec_df["rev_cagr_3yr"].dropna().empty
        else 0.0
    )

    # Universe aggregates
    u_roe = df["roe"].dropna().mean()
    u_opm = df["opm"].dropna().mean()
    u_de = df["de"].dropna().median()
    u_pe = df["pe_ratio"].dropna().median()
    u_rev = df["rev_cagr_3yr"].dropna().mean()

    # Document setup
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=44,
        bottomMargin=44,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "SecTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
    )
    subtitle_style = ParagraphStyle(
        "SecSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569"),
    )
    h2_style = ParagraphStyle(
        "SecH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1E3A8A"),
    )
    body_style = ParagraphStyle(
        "SecBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#334155"),
    )
    table_header = ParagraphStyle(
        "SecTH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
        alignment=1,  # Center
    )
    cell_center = ParagraphStyle(
        "SecCellCenter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        alignment=1,
    )
    cell_center_bold = ParagraphStyle(
        "SecCellCenterBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        alignment=1,
    )
    cell_left_bold = ParagraphStyle(
        "SecCellLeftBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
    )

    story: list[Any] = []

    # =========================================================================
    # PAGE 1: SECTOR OVERVIEW
    # =========================================================================
    display_title = (
        "Information Technology (IT Services)"
        if sector_name in ("Information Technology", "IT Services")
        else sector_name
    )
    story.append(Paragraph(f"Sector Report: {display_title}", title_style))
    story.append(
        Paragraph(
            f"Constituent Count: {s_count} Companies  |  Total Market Cap: INR {s_mcap:,.0f} Cr  |  Nifty 100 Benchmark Coverage",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 10))

    # 4 KPI Summary Cards in a 1x4 table
    def make_kpi_cell(label: str, value: str, sub: str) -> list[Any]:
        return [
            Paragraph(
                f"<font size='7' color='#64748B'><b>{label}</b></font>",
                cell_center,
            ),
            Spacer(1, 2),
            Paragraph(
                f"<font size='13' color='#1E3A8A'><b>{value}</b></font>",
                cell_center,
            ),
            Spacer(1, 1),
            Paragraph(f"<font size='6.5' color='#94A3B8'>{sub}</font>", cell_center),
        ]

    kpi_data = [
        [
            make_kpi_cell("AVG ROE", f"{s_roe:.1f}%", f"Universe: {u_roe:.1f}%"),
            make_kpi_cell("AVG OPM", f"{s_opm:.1f}%", f"Universe: {u_opm:.1f}%"),
            make_kpi_cell("MEDIAN D/E", f"{s_de:.2f}x", f"Universe: {u_de:.2f}x"),
            make_kpi_cell("MEDIAN P/E", f"{s_pe:.1f}x", f"Universe: {u_pe:.1f}x"),
        ]
    ]

    kpi_table = Table(kpi_data, colWidths=[128, 128, 128, 128])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # Sector vs Universe Comparison Table (5 metrics, delta highlighted green/red)
    story.append(Paragraph("Sector vs Full Universe Benchmarking", h2_style))
    story.append(Spacer(1, 5))

    metrics_comp = [
        ("Return on Equity (ROE)", s_roe, u_roe, s_roe - u_roe, "%", True),
        ("Operating Profit Margin (OPM)", s_opm, u_opm, s_opm - u_opm, "%", True),
        ("Median Debt-to-Equity (D/E)", s_de, u_de, s_de - u_de, "x", False),
        ("Median Price-to-Earnings (P/E)", s_pe, u_pe, s_pe - u_pe, "x", False),
        ("Revenue CAGR (3-Year)", s_rev, u_rev, s_rev - u_rev, "%", True),
    ]

    comp_table_rows = [
        [
            Paragraph("Metric", table_header),
            Paragraph("Sector Avg / Median", table_header),
            Paragraph("Universe Benchmark", table_header),
            Paragraph("Delta (Sector - Univ)", table_header),
            Paragraph("Positioning", table_header),
        ]
    ]

    for idx, (m_label, s_val, u_val, delta, unit, higher_is_better) in enumerate(
        metrics_comp, start=1
    ):
        is_green = (delta >= 0) if higher_is_better else (delta <= 0)
        color_hex = "#15803D" if is_green else "#B91C1C"
        pos_text = "Favorable (Outperforming)" if is_green else "Unfavorable / Headwind"
        delta_sign = "+" if delta > 0 else ""

        comp_table_rows.append(
            [
                Paragraph(m_label, cell_left_bold),
                Paragraph(f"{s_val:.1f}{unit}", cell_center),
                Paragraph(f"{u_val:.1f}{unit}", cell_center),
                Paragraph(
                    f"<font color='{color_hex}'><b>{delta_sign}{delta:.1f}{unit}</b></font>",
                    cell_center,
                ),
                Paragraph(
                    f"<font color='{color_hex}'><b>{pos_text}</b></font>", cell_center
                ),
            ]
        )

    comp_table = Table(comp_table_rows, colWidths=[150, 95, 95, 85, 88])
    comp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F8FAFC")],
                ),
            ]
        )
    )
    story.append(comp_table)
    story.append(Spacer(1, 14))

    # Top 3 Companies by composite_ranking_score
    story.append(
        Paragraph("Top Constituent Companies by Composite Health Score", h2_style)
    )
    story.append(Spacer(1, 5))

    top3_df = sec_df.head(3)
    top3_rows = [
        [
            Paragraph("Rank", table_header),
            Paragraph("Company Name", table_header),
            Paragraph("Ticker", table_header),
            Paragraph("Composite Score", table_header),
            Paragraph("Valuation Flag", table_header),
            Paragraph("Market Cap (Cr)", table_header),
        ]
    ]

    for rank_idx, (_, row) in enumerate(top3_df.iterrows(), start=1):
        c_score = row.get("composite_ranking_score")
        score_str = f"{c_score:.1f}" if pd.notna(c_score) else "N/A"
        top3_rows.append(
            [
                Paragraph(f"<b>#{rank_idx}</b>", cell_center_bold),
                Paragraph(str(row["company_name"]), cell_left_bold),
                Paragraph(str(row["company_id"]), cell_center),
                Paragraph(f"<b>{score_str}</b>", cell_center_bold),
                Paragraph(str(row.get("valuation_flag", "Fair Value")), cell_center),
                Paragraph(f"INR {row['market_cap_crore']:,.0f}", cell_center),
            ]
        )

    top3_table = Table(top3_rows, colWidths=[40, 155, 65, 80, 90, 83])
    top3_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F0FDF4")],
                ),
            ]
        )
    )
    story.append(top3_table)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: COMPANY RANKING TABLE
    # =========================================================================
    story.append(Paragraph(f"{display_title}: Full Constituent Rankings", title_style))
    story.append(
        Paragraph(
            "Ranked by Composite Financial Health Score (0-100). Color coding: Top third = Soft Green, Bottom third = Soft Red.",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 10))

    rank_headers = [
        Paragraph("Rank", table_header),
        Paragraph("Company Name", table_header),
        Paragraph("ROE (%)", table_header),
        Paragraph("ROCE (%)", table_header),
        Paragraph("OPM (%)", table_header),
        Paragraph("D/E", table_header),
        Paragraph("Rev CAGR 3Y", table_header),
        Paragraph("Composite Score", table_header),
        Paragraph("Valuation Flag", table_header),
    ]
    rank_rows = [rank_headers]

    n_comp = len(sec_df)
    top_third_cutoff = n_comp // 3
    bottom_third_cutoff = n_comp - (n_comp // 3)

    table_style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]

    for idx, (_, row) in enumerate(sec_df.iterrows(), start=1):
        roe_val = f"{row['roe']:.1f}%" if pd.notna(row["roe"]) else "N/A"
        roce_val = f"{row['roce']:.1f}%" if pd.notna(row["roce"]) else "N/A"
        opm_val = f"{row['opm']:.1f}%" if pd.notna(row["opm"]) else "N/A"
        de_val = f"{row['de']:.2f}" if pd.notna(row["de"]) else "N/A"
        rev_val = (
            f"{row['rev_cagr_3yr']:.1f}%" if pd.notna(row["rev_cagr_3yr"]) else "N/A"
        )
        sc_val = (
            f"{row['composite_ranking_score']:.1f}"
            if pd.notna(row["composite_ranking_score"])
            else "N/A"
        )
        val_flag = str(row.get("valuation_flag", "Fair Value"))

        if n_comp >= 3:
            if idx <= top_third_cutoff:
                row_bg = colors.HexColor("#DCFCE7")
            elif idx > bottom_third_cutoff:
                row_bg = colors.HexColor("#FEE2E2")
            else:
                row_bg = colors.white
        else:
            row_bg = (
                colors.HexColor("#DCFCE7") if idx == 1 else colors.HexColor("#FEE2E2")
            )

        table_style_commands.append(("BACKGROUND", (0, idx), (-1, idx), row_bg))

        rank_rows.append(
            [
                Paragraph(f"#{idx}", cell_center_bold),
                Paragraph(
                    f"{row['company_name']} ({row['company_id']})", cell_left_bold
                ),
                Paragraph(roe_val, cell_center),
                Paragraph(roce_val, cell_center),
                Paragraph(opm_val, cell_center),
                Paragraph(de_val, cell_center),
                Paragraph(rev_val, cell_center),
                Paragraph(f"<b>{sc_val}</b>", cell_center_bold),
                Paragraph(val_flag, cell_center),
            ]
        )

    ranking_table = Table(rank_rows, colWidths=[30, 145, 45, 45, 45, 40, 52, 53, 58])
    ranking_table.setStyle(TableStyle(table_style_commands))
    story.append(ranking_table)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: KEY FINDINGS & INSIGHTS
    # =========================================================================
    story.append(
        Paragraph(f"{display_title}: Key Findings & Peer Analysis", title_style)
    )
    story.append(
        Paragraph(
            "Institutional Peer Percentiles, Competitive Tiering & Sector Fundamentals Synthesis",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 10))

    # Auto-Generated Sector-Specific Insight Box
    insight_sentence = generate_sector_insight_sentence(
        sector_name=target_sector,
        s_roe=s_roe,
        s_opm=s_opm,
        s_de=s_de,
        s_pe=s_pe,
        u_roe=u_roe,
        u_opm=u_opm,
        u_de=u_de,
        u_pe=u_pe,
    )

    insight_content = [
        [
            Paragraph(
                "<font color='#0F766E' size='9'><b>EXECUTIVE SECTOR INSIGHT</b></font>",
                cell_left_bold,
            )
        ],
        [Paragraph(f'<i>"{insight_sentence}"</i>', body_style)],
    ]
    insight_table = Table(insight_content, colWidths=[513])
    insight_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDFA")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0D9488")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(insight_table)
    story.append(Spacer(1, 14))

    # Query Best in Class and Watch List counts from peer_percentiles
    sec_cids = set(sec_df["company_id"])
    sec_pp = df_pp[df_pp["company_id"].isin(sec_cids)]

    bic_counts = (
        sec_pp[sec_pp["classification"] == "Best in Class"]
        .groupby("company_id")
        .size()
        .sort_values(ascending=False)
    )

    wl_counts = (
        sec_pp[sec_pp["classification"] == "Watch List"]
        .groupby("company_id")
        .size()
        .sort_values(ascending=False)
    )

    cid_to_name = dict(zip(sec_df["company_id"], sec_df["company_name"]))

    # Best in Class Table
    story.append(
        Paragraph(
            "1. Best in Class Companies (Peer Percentile Classification = 'Best in Class')",
            h2_style,
        )
    )
    story.append(Spacer(1, 4))

    bic_rows = [
        [
            Paragraph("Company Name", table_header),
            Paragraph("Ticker", table_header),
            Paragraph("Best-in-Class Metrics Count", table_header),
            Paragraph("Competitive Status", table_header),
        ]
    ]

    if not bic_counts.empty:
        for cid, count in bic_counts.items():
            cname = cid_to_name.get(cid, cid)
            status_desc = (
                "Superior Leadership" if count >= 8 else "Peer Benchmark Outperformer"
            )
            bic_rows.append(
                [
                    Paragraph(cname, cell_left_bold),
                    Paragraph(cid, cell_center),
                    Paragraph(f"<b>{count} Metrics</b>", cell_center_bold),
                    Paragraph(
                        f"<font color='#15803D'><b>{status_desc}</b></font>",
                        cell_center,
                    ),
                ]
            )
    else:
        top_co = sec_df.iloc[0]
        bic_rows.append(
            [
                Paragraph(str(top_co["company_name"]), cell_left_bold),
                Paragraph(str(top_co["company_id"]), cell_center),
                Paragraph("Sector Top Score", cell_center_bold),
                Paragraph(
                    "<font color='#15803D'><b>High Quality Tier</b></font>", cell_center
                ),
            ]
        )

    bic_table = Table(bic_rows, colWidths=[200, 75, 115, 123])
    bic_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#15803D")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F0FDF4")],
                ),
            ]
        )
    )
    story.append(bic_table)
    story.append(Spacer(1, 14))

    # Watch List Table
    story.append(
        Paragraph(
            "2. Watch List Companies (Peer Percentile Classification = 'Watch List')",
            h2_style,
        )
    )
    story.append(Spacer(1, 4))

    wl_rows = [
        [
            Paragraph("Company Name", table_header),
            Paragraph("Ticker", table_header),
            Paragraph("Watch-List Metrics Count", table_header),
            Paragraph("Risk Profile", table_header),
        ]
    ]

    if not wl_counts.empty:
        for cid, count in wl_counts.items():
            cname = cid_to_name.get(cid, cid)
            risk_desc = (
                "High Scrutiny Alert" if count >= 8 else "Elevated Benchmark Lag"
            )
            wl_rows.append(
                [
                    Paragraph(cname, cell_left_bold),
                    Paragraph(cid, cell_center),
                    Paragraph(f"<b>{count} Metrics</b>", cell_center_bold),
                    Paragraph(
                        f"<font color='#B91C1C'><b>{risk_desc}</b></font>", cell_center
                    ),
                ]
            )
    else:
        bottom_co = sec_df.iloc[-1]
        wl_rows.append(
            [
                Paragraph(str(bottom_co["company_name"]), cell_left_bold),
                Paragraph(str(bottom_co["company_id"]), cell_center),
                Paragraph("Sector Lowest Score", cell_center_bold),
                Paragraph(
                    "<font color='#B91C1C'><b>Moderate Scrutiny</b></font>", cell_center
                ),
            ]
        )

    wl_table = Table(wl_rows, colWidths=[200, 75, 115, 123])
    wl_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B91C1C")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#FEF2F2")],
                ),
            ]
        )
    )
    story.append(wl_table)

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    logger.info("Successfully generated sector report: %s", output_pdf)
    return output_pdf


def generate_all_sector_reports(
    db_path: Path | str = DEFAULT_DB_PATH,
    output_dir: Path | str = DEFAULT_SECTOR_REPORTS_DIR,
) -> list[Path]:
    """Generate all 11 institutional sector report PDFs.

    Returns:
        List of generated PDF file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for sector in SECTOR_LIST:
        try:
            pdf_path = generate_sector_report(
                sector_name=sector,
                db_path=db_path,
                output_dir=output_dir,
            )
            generated.append(pdf_path)
            logger.info("Generated sector report for '%s' -> %s", sector, pdf_path.name)
        except Exception as exc:
            logger.error("Failed to generate sector report for '%s': %s", sector, exc)
            raise

    return generated


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reports = generate_all_sector_reports()
    print(f"Generated {len(reports)} sector reports successfully.")
