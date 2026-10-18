"""Portfolio Summary PDF Generator (Module 10 / Deliverable D-18).

Generates the institutional portfolio summary PDF covering all 92 companies
in the Nifty 100 universe sorted by composite ranking score, with summary KPIs,
universe benchmark charts, preset memberships, and valuation flags.
"""

from __future__ import annotations

import io
import logging
import sqlite3
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image as RLImage,
)
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
DEFAULT_OUTPUT_PDF = DEFAULT_REPORTS_DIR / "portfolio_summary.pdf"


class NumberedLandscapeCanvas(canvas.Canvas):
    """Two-pass landscape canvas adding running header, footer, and page numbers."""

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

        # Top running header line (Landscape A4: width 841.89, height 595.27)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 565, 805, 565)

        # Top header text
        self.drawString(
            36,
            572,
            "N100 FINANCIAL INTELLIGENCE PLATFORM  |  PORTFOLIO SUMMARY REPORT (DELIVERABLE D-18)",
        )

        # Bottom running footer line
        self.line(36, 30, 805, 30)

        # Footer text
        footer_text = "Institutional Equity Research | All 92 Nifty 100 Constituents | Strict Fundamental Triage"
        self.drawString(36, 20, footer_text)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(805, 20, page_str)
        self.restoreState()


def load_portfolio_dataset(db_path: Path | str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Load all 92 companies joined with fundamental ratios, screener presets, and valuation flags."""
    conn = sqlite3.connect(str(db_path))

    query = """
    SELECT 
        c.id as company_id,
        c.company_name,
        s.broad_sector,
        s.sub_sector,
        fr.return_on_equity_pct as roe,
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

    # Load peer group
    pg_query = "SELECT company_id, peer_group_name FROM peer_groups"
    df_pg = pd.read_sql_query(pg_query, conn)
    conn.close()

    df = df.merge(df_pg, on="company_id", how="left")
    df["peer_group"] = (
        df["peer_group_name"].fillna(df["broad_sector"]).fillna("General")
    )

    # Load screener summary (composite ranking score & preset memberships)
    screener_path = REPO_ROOT / "screener_output.xlsx"
    if not screener_path.exists():
        screener_path = DEFAULT_REPORTS_DIR / "screener_output.xlsx"

    preset_cols = [
        ("in_quality_compounder", "Quality"),
        ("in_value_pick", "Value"),
        ("in_dividend_aristocrat", "Dividend"),
        ("in_growth_rocket", "Growth"),
        ("in_asset_light_champion", "Asset-Light"),
        ("in_financial_health", "Fin Health"),
    ]

    if screener_path.exists():
        try:
            df_scr = pd.read_excel(screener_path, sheet_name="Summary")

            def get_presets(row: pd.Series) -> str:
                matches = [name for col, name in preset_cols if row.get(col) is True]
                return ", ".join(matches) if matches else "None"

            df_scr["preset_memberships"] = df_scr.apply(get_presets, axis=1)

            cols_to_merge = [
                "company_id",
                "composite_ranking_score",
                "preset_memberships",
            ]
            df = df.merge(df_scr[cols_to_merge], on="company_id", how="left")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not read screener_output.xlsx: %s", exc)

    if "composite_ranking_score" not in df.columns:
        df["composite_ranking_score"] = 50.0
    if "preset_memberships" not in df.columns:
        df["preset_memberships"] = "None"

    # Merge valuation flag
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

    # Sort all 92 companies by composite_ranking_score descending (nulls at the end)
    df["sort_key"] = df["composite_ranking_score"].fillna(-999.0)
    df = df.sort_values(by="sort_key", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)

    return df


def generate_universe_charts(df: pd.DataFrame) -> tuple[RLImage, RLImage]:
    """Generate high-resolution institutional summary charts for universe overview."""
    # Chart 1: Sector Aggregate Market Cap and Company Count
    sec_agg = (
        df.groupby("broad_sector")
        .agg(mcap=("market_cap_crore", "sum"), count=("company_id", "count"))
        .sort_values(by="mcap", ascending=True)
    )

    fig, ax = plt.subplots(figsize=(6.2, 2.3), dpi=200)
    bars = ax.barh(
        range(len(sec_agg)),
        sec_agg["mcap"] / 100000.0,
        color="#1E3A8A",
        edgecolor="#0F172A",
        height=0.65,
    )
    ax.set_yticks(range(len(sec_agg)))
    ax.set_yticklabels(sec_agg.index, fontsize=6.5, fontweight="bold")
    ax.set_xlabel("Market Cap (INR Lakh Crore)", fontsize=7, fontweight="bold")
    ax.set_title(
        "Nifty 100 Sector Market Cap & Constituent Count",
        fontsize=8,
        fontweight="bold",
        pad=4,
    )
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for i, (bar, cnt) in enumerate(zip(bars, sec_agg["count"])):
        w = bar.get_width()
        ax.text(
            w + 0.1,
            bar.get_y() + bar.get_height() / 2,
            f"{cnt} cos",
            va="center",
            fontsize=6,
            color="#475569",
        )

    buf1 = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf1, format="png")
    plt.close(fig)
    buf1.seek(0)
    img1 = RLImage(buf1, width=370, height=138)

    # Chart 2: Composite Ranking Score Distribution
    fig, ax = plt.subplots(figsize=(6.2, 2.3), dpi=200)
    valid_scores = df["composite_ranking_score"].dropna()
    _n, _bins, _patches = ax.hist(
        valid_scores,
        bins=10,
        color="#0D9488",
        edgecolor="#042F2E",
        rwidth=0.85,
    )
    ax.axvline(
        valid_scores.median(),
        color="#DC2626",
        linestyle="--",
        linewidth=1.5,
        label=f"Median: {valid_scores.median():.1f}",
    )
    ax.axvline(
        valid_scores.mean(),
        color="#D97706",
        linestyle=":",
        linewidth=1.5,
        label=f"Mean: {valid_scores.mean():.1f}",
    )
    ax.set_xlabel("Composite Health Score (0-100)", fontsize=7, fontweight="bold")
    ax.set_ylabel("Number of Companies", fontsize=7, fontweight="bold")
    ax.set_title(
        "Composite Financial Health Score Distribution",
        fontsize=8,
        fontweight="bold",
        pad=4,
    )
    ax.legend(fontsize=6.5, loc="upper left")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    buf2 = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf2, format="png")
    plt.close(fig)
    buf2.seek(0)
    img2 = RLImage(buf2, width=370, height=138)

    return img1, img2


def generate_portfolio_summary_pdf(
    db_path: Path | str = DEFAULT_DB_PATH,
    output_pdf: Path | str = DEFAULT_OUTPUT_PDF,
) -> Path:
    """Generate the multi-page institutional portfolio summary PDF (>50KB).

    Args:
        db_path: Path to nifty100.db SQLite database.
        output_pdf: Destination path for portfolio_summary.pdf.

    Returns:
        Path to the generated PDF.
    """
    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    df = load_portfolio_dataset(db_path=db_path)
    total_companies = len(df)

    # Universe aggregates
    u_roe = df["roe"].dropna().mean()
    u_opm = df["opm"].dropna().mean()
    u_de = df["de"].dropna().median()
    u_pe = df["pe_ratio"].dropna().median()
    u_rev = df["rev_cagr_3yr"].dropna().mean()
    u_mcap = df["market_cap_crore"].dropna().sum()

    # Landscape A4 dimensions: 841.89 x 595.27 pt
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=38,
        bottomMargin=38,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "PortTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0F172A"),
    )
    subtitle_style = ParagraphStyle(
        "PortSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )
    th_style = ParagraphStyle(
        "PortTH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8.5,
        textColor=colors.white,
        alignment=1,
    )
    cell_center = ParagraphStyle(
        "PortCC",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
        alignment=1,
    )
    cell_center_bold = ParagraphStyle(
        "PortCCBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=8,
        alignment=1,
    )
    cell_left = ParagraphStyle(
        "PortCL",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
    )
    cell_left_bold = ParagraphStyle(
        "PortCLBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=8,
    )

    story: list[Any] = []

    # Title & Subtitle Header
    story.append(
        Paragraph("NIFTY 100 PORTFOLIO SUMMARY & COMPOSITE RANKINGS", title_style)
    )
    story.append(
        Paragraph(
            f"Comprehensive Universe Coverage: {total_companies} Companies  |  "
            f"Total Universe Market Cap: INR {u_mcap:,.0f} Cr  |  "
            f"Sorted by Composite Health Score (0-100)  |  "
            f"Top 10 = Dark Green Highlight  |  Bottom 10 = Light Red Highlight",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 6))

    # Universe Summary Stats Cards (1 row x 6 columns)
    def make_kpi_cell(label: str, value: str) -> list[Any]:
        return [
            Paragraph(
                f"<font size='6' color='#64748B'><b>{label}</b></font>", cell_center
            ),
            Spacer(1, 1),
            Paragraph(
                f"<font size='10' color='#1E3A8A'><b>{value}</b></font>", cell_center
            ),
        ]

    kpi_cards = [
        [
            make_kpi_cell("TOTAL CONSTITUENTS", f"{total_companies} Cos"),
            make_kpi_cell("UNIVERSE AVG ROE", f"{u_roe:.1f}%"),
            make_kpi_cell("UNIVERSE AVG OPM", f"{u_opm:.1f}%"),
            make_kpi_cell("UNIVERSE MEDIAN D/E", f"{u_de:.2f}x"),
            make_kpi_cell("UNIVERSE MEDIAN P/E", f"{u_pe:.1f}x"),
            make_kpi_cell("AVG 3Y REV CAGR", f"{u_rev:.1f}%"),
        ]
    ]

    summary_table = Table(kpi_cards, colWidths=[128, 128, 128, 128, 128, 129])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 6))

    # Add Universe Distribution Charts
    chart1, chart2 = generate_universe_charts(df)
    charts_table = Table([[chart1, chart2]], colWidths=[385, 384])
    charts_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(charts_table)
    story.append(Spacer(1, 6))
    story.append(PageBreak())

    # 11 Columns for the 92 companies table:
    # rank, company_name, broad_sector, peer_group, composite_score, ROE, OPM, D/E, Revenue CAGR 3yr, Valuation Flag, preset memberships
    headers = [
        Paragraph("Rank", th_style),
        Paragraph("Company Name (Ticker)", th_style),
        Paragraph("Broad Sector", th_style),
        Paragraph("Peer Group", th_style),
        Paragraph("Score", th_style),
        Paragraph("ROE", th_style),
        Paragraph("OPM", th_style),
        Paragraph("D/E", th_style),
        Paragraph("Rev CAGR", th_style),
        Paragraph("Valuation Flag", th_style),
        Paragraph("Preset Memberships", th_style),
    ]

    table_data = [headers]
    table_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2027")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
    ]

    for idx, row in df.iterrows():
        rank_num = int(row["rank"])
        cname = f"{row['company_name']} ({row['company_id']})"
        bsector = str(row["broad_sector"])
        pgroup = str(row["peer_group"])

        c_score = (
            f"{row['composite_ranking_score']:.1f}"
            if pd.notna(row["composite_ranking_score"])
            else "N/A"
        )
        roe_val = f"{row['roe']:.1f}%" if pd.notna(row["roe"]) else "N/A"
        opm_val = f"{row['opm']:.1f}%" if pd.notna(row["opm"]) else "N/A"
        de_val = f"{row['de']:.2f}" if pd.notna(row["de"]) else "N/A"
        rev_val = (
            f"{row['rev_cagr_3yr']:.1f}%" if pd.notna(row["rev_cagr_3yr"]) else "N/A"
        )
        v_flag = str(row["valuation_flag"])
        presets = str(row["preset_memberships"])

        # Top 10 = Dark green / Soft green highlight; Bottom 10 = Light red
        if rank_num <= 10:
            row_bg = colors.HexColor("#DCFCE7")
        elif rank_num > total_companies - 10:
            row_bg = colors.HexColor("#FEE2E2")
        elif rank_num % 2 == 0:
            row_bg = colors.HexColor("#F8FAFC")
        else:
            row_bg = colors.white

        table_styles.append(("BACKGROUND", (0, rank_num), (-1, rank_num), row_bg))

        table_data.append(
            [
                Paragraph(f"<b>#{rank_num}</b>", cell_center_bold),
                Paragraph(cname, cell_left_bold),
                Paragraph(bsector, cell_left),
                Paragraph(pgroup, cell_left),
                Paragraph(f"<b>{c_score}</b>", cell_center_bold),
                Paragraph(roe_val, cell_center),
                Paragraph(opm_val, cell_center),
                Paragraph(de_val, cell_center),
                Paragraph(rev_val, cell_center),
                Paragraph(v_flag, cell_center),
                Paragraph(presets, cell_left),
            ]
        )

    # Available width: 841.89 - 72 = 769.89 pt
    col_widths = [28, 140, 85, 80, 38, 38, 38, 34, 46, 75, 168]
    data_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    data_table.setStyle(TableStyle(table_styles))
    story.append(data_table)

    doc.build(story, canvasmaker=NumberedLandscapeCanvas)
    logger.info("Successfully generated portfolio summary PDF: %s", output_pdf)
    return output_pdf


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    pdf = generate_portfolio_summary_pdf()
    print(
        f"Generated portfolio summary PDF: {pdf} (Size: {pdf.stat().st_size:,} bytes)"
    )
