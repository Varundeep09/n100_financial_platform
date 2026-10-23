"""N100 Financial Intelligence Platform — Presentation Generator.

Generates an institutional 12-slide executive presentation in 16:9 widescreen PPTX
format documenting platform architecture, sprint deliverables, analytical findings,
and quality benchmarks for Bluestock Fintech.
"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

# ==============================================================================
# DESIGN SYSTEM & COLOR PALETTE
# ==============================================================================
BG_DARK = RGBColor(15, 23, 42)  # #0F172A Slate 900
BG_CARD = RGBColor(30, 41, 59)  # #1E293B Slate 800
BG_CARD_ALT = RGBColor(24, 33, 47)  # #18212F Slightly darker slate
BORDER_CARD = RGBColor(51, 65, 85)  # #334155 Slate 700

ACCENT_BLUE = RGBColor(59, 130, 246)  # #3B82F6 Blue 500
ACCENT_TEAL = RGBColor(16, 185, 129)  # #10B981 Emerald 500
ACCENT_GOLD = RGBColor(245, 158, 11)  # #F59E0B Amber 500
ACCENT_PURPLE = RGBColor(139, 92, 246)  # #8B5CF6 Violet 500
ACCENT_CYAN = RGBColor(6, 182, 212)  # #06B6D4 Cyan 500
ACCENT_RED = RGBColor(239, 68, 68)  # #EF4444 Red 500

TEXT_TITLE = RGBColor(248, 250, 252)  # #F8FAFC Crisp White
TEXT_BODY = RGBColor(203, 213, 225)  # #CBD5E1 Slate 300
TEXT_MUTED = RGBColor(148, 163, 184)  # #94A3B8 Slate 400
TEXT_DARK = RGBColor(100, 116, 139)  # #64748B Slate 500

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def create_base_slide(
    prs: Presentation,
    category_tag: str,
    title: str,
    subtitle: str,
    slide_num: int,
    total_slides: int = 12,
):
    """Create a standardized widescreen slide with dark background, header, and footer."""
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)

    # 1. Dark Background Fill
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_DARK
    bg.line.fill.background()

    # 2. Top Blue Accent Bar
    top_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.06)
    )
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = ACCENT_BLUE
    top_bar.line.fill.background()

    # 3. Header Container
    header_box = slide.shapes.add_textbox(
        Inches(0.8), Inches(0.4), Inches(11.7), Inches(1.05)
    )
    tf = header_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    # Category Pill Tag
    p_tag = tf.paragraphs[0]
    p_tag.text = category_tag.upper()
    p_tag.font.name = FONT_HEADING
    p_tag.font.size = Pt(9.5)
    p_tag.font.bold = True
    p_tag.font.color.rgb = ACCENT_BLUE

    # Slide Title
    p_title = tf.add_paragraph()
    p_title.text = title
    p_title.font.name = FONT_HEADING
    p_title.font.size = Pt(22)
    p_title.font.bold = True
    p_title.font.color.rgb = TEXT_TITLE

    # Subtitle
    p_sub = tf.add_paragraph()
    p_sub.text = subtitle
    p_sub.font.name = FONT_BODY
    p_sub.font.size = Pt(11.5)
    p_sub.font.color.rgb = TEXT_MUTED

    # 4. Footer Line & Metadata
    footer_line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(7.0), Inches(11.733), Inches(0.02)
    )
    footer_line.fill.solid()
    footer_line.fill.fore_color.rgb = BORDER_CARD
    footer_line.line.fill.background()

    footer_box = slide.shapes.add_textbox(
        Inches(0.8), Inches(7.05), Inches(11.733), Inches(0.35)
    )
    ftf = footer_box.text_frame
    ftf.word_wrap = True
    ftf.margin_left = ftf.margin_top = ftf.margin_right = ftf.margin_bottom = 0
    p_foot = ftf.paragraphs[0]
    r_left = p_foot.add_run()
    r_left.text = "N100 Financial Intelligence Platform  •  Bluestock Fintech  •  Varundeep Sengar"
    r_left.font.name = FONT_BODY
    r_left.font.size = Pt(9)
    r_left.font.color.rgb = TEXT_DARK

    p_right = ftf.add_paragraph()
    p_right.alignment = PP_ALIGN.RIGHT
    r_right = p_right.add_run()
    r_right.text = f"Slide {slide_num} of {total_slides}  |  Production v1.0"
    r_right.font.name = FONT_BODY
    r_right.font.size = Pt(9)
    r_right.font.color.rgb = TEXT_DARK

    return slide


def add_card(
    slide,
    left,
    top,
    width,
    height,
    title=None,
    border_color=BORDER_CARD,
    bg_color=BG_CARD,
):
    """Add a modern dark rounded card container to a slide."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1.2)

    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.2)
    tf.margin_right = Inches(0.2)
    tf.margin_top = Inches(0.18)
    tf.margin_bottom = Inches(0.18)

    if title:
        p = tf.paragraphs[0]
        p.text = title
        p.font.name = FONT_HEADING
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = TEXT_TITLE

    return card


def add_badge(
    slide,
    left,
    top,
    width,
    height,
    text,
    bg_color=ACCENT_BLUE,
    text_color=TEXT_TITLE,
    font_size=10,
):
    """Add a small pill-shaped stat badge."""
    badge = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    badge.fill.solid()
    badge.fill.fore_color.rgb = bg_color
    badge.line.fill.background()

    tf = badge.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = text
    p.font.name = FONT_HEADING
    p.font.size = Pt(font_size)
    p.font.bold = True
    p.font.color.rgb = text_color
    return badge


# ==============================================================================
# SLIDE BUILDERS (SLIDES 1 TO 12)
# ==============================================================================


def build_slide_1(prs: Presentation) -> None:
    """Slide 1: Title Slide — N100 Financial Intelligence Platform."""
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)

    # Dark background
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = RGBColor(11, 15, 25)
    bg.line.fill.background()

    # Top accent line
    top_bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.08)
    )
    top_bar.fill.solid()
    top_bar.fill.fore_color.rgb = ACCENT_BLUE
    top_bar.line.fill.background()

    # Top badge
    add_badge(
        slide,
        Inches(1.0),
        Inches(0.9),
        Inches(3.8),
        Inches(0.35),
        "BLUESTOCK FINTECH • RESEARCH & DATA ENGINEERING",
        bg_color=RGBColor(30, 41, 59),
        text_color=ACCENT_BLUE,
        font_size=9,
    )

    # Hero Title & Subtitle Box
    title_box = slide.shapes.add_textbox(
        Inches(1.0), Inches(1.4), Inches(11.3), Inches(2.2)
    )
    tf = title_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_main = tf.paragraphs[0]
    p_main.text = "N100 FINANCIAL INTELLIGENCE PLATFORM"
    p_main.font.name = FONT_HEADING
    p_main.font.size = Pt(36)
    p_main.font.bold = True
    p_main.font.color.rgb = TEXT_TITLE

    p_sub = tf.add_paragraph()
    p_sub.text = (
        "Institutional-Grade Analytics, Multi-Factor Screening & Intrinsic Valuation "
        "Engine for Nifty 100 Non-Financial Equities (FY2015–FY2024)"
    )
    p_sub.font.name = FONT_BODY
    p_sub.font.size = Pt(15)
    p_sub.font.color.rgb = TEXT_MUTED

    # 4 Metadata Cards
    meta_info = [
        (
            "AUTHOR & ARCHITECT",
            "Varundeep Sengar",
            "Platform Engineering",
            ACCENT_BLUE,
        ),
        (
            "ORGANIZATION",
            "Bluestock Fintech",
            "Equity Intelligence Unit",
            ACCENT_TEAL,
        ),
        (
            "MILESTONE & DATE",
            "Production Release v1.0",
            "October 2026 (Ahead of Sched.)",
            ACCENT_GOLD,
        ),
        (
            "QUALITY BENCHMARK",
            "245 / 245 Tests Passing",
            "100% CI/CD Verified",
            ACCENT_PURPLE,
        ),
    ]

    card_w = Inches(2.65)
    card_h = Inches(1.5)
    card_y = Inches(3.8)
    spacing = Inches(0.24)

    for i, (tag, val1, val2, acc_col) in enumerate(meta_info):
        card_x = Inches(1.0) + i * (card_w + spacing)
        card = add_card(
            slide,
            card_x,
            card_y,
            card_w,
            card_h,
            border_color=acc_col,
            bg_color=BG_CARD,
        )
        ctf = card.text_frame
        p_tag = ctf.paragraphs[0]
        p_tag.text = tag
        p_tag.font.name = FONT_HEADING
        p_tag.font.size = Pt(9.5)
        p_tag.font.bold = True
        p_tag.font.color.rgb = acc_col

        p_v1 = ctf.add_paragraph()
        p_v1.text = val1
        p_v1.font.name = FONT_HEADING
        p_v1.font.size = Pt(13)
        p_v1.font.bold = True
        p_v1.font.color.rgb = TEXT_TITLE

        p_v2 = ctf.add_paragraph()
        p_v2.text = val2
        p_v2.font.name = FONT_BODY
        p_v2.font.size = Pt(9.5)
        p_v2.font.color.rgb = TEXT_MUTED

    # Bottom Highlight Stat Pills
    pill_y = Inches(5.7)
    pills = [
        ("92 Companies Ingested", ACCENT_BLUE),
        ("10 Audited Fiscal Years", ACCENT_TEAL),
        ("50+ Financial KPIs", ACCENT_GOLD),
        ("23 Verified Deliverables", ACCENT_PURPLE),
        ("16 FastAPI Endpoints", ACCENT_CYAN),
    ]
    p_w = Inches(2.1)
    p_gap = Inches(0.2)
    for i, (txt, col) in enumerate(pills):
        px = Inches(1.0) + i * (p_w + p_gap)
        add_badge(
            slide,
            px,
            pill_y,
            p_w,
            Inches(0.42),
            txt,
            bg_color=BG_CARD_ALT,
            text_color=col,
            font_size=10,
        )


def build_slide_2(prs: Presentation) -> None:
    """Slide 2: Problem Statement — Why This Platform Exists."""
    slide = create_base_slide(
        prs,
        category_tag="Project Motivation & Problem Statement",
        title="Why This Platform Exists: Institutional Investment Bottlenecks",
        subtitle="Addressing structural data fragmentation and manual analysis hurdles in Indian equity research",
        slide_num=2,
    )

    problems = [
        (
            "1. Fragmented Financial Data",
            "Raw regulatory disclosures across BSE, NSE, and Screener.in are siloed across disparate Excel spreadsheets with conflicting schemas, inconsistent line items, and shifting fiscal definitions.",
            ACCENT_BLUE,
        ),
        (
            "2. No Unified Equity Screener",
            "Fundamental analysts lack a multi-factor quantitative screening engine capable of filtering across balance sheet solvency, cash flow quality, DuPont returns, and valuation percentiles simultaneously.",
            ACCENT_TEAL,
        ),
        (
            "3. Manual Ratio & Margin Computations",
            "Analysts spend hundreds of hours manually recalculating DuPont models, CAGR trajectories, and working capital cycles across 10 fiscal years, introducing high operational and calculation error risk.",
            ACCENT_GOLD,
        ),
        (
            "4. Absence of Peer Group Benchmarking",
            "Valuation and efficiency metrics cannot be interpreted in a vacuum. Lack of normalized percentile rankings, industry-specific peer groups, and dynamic radar charts obscures true competitive moats.",
            ACCENT_PURPLE,
        ),
        (
            "5. No Automated Reporting & Deliverables",
            "Production of executive tearsheets, sector deep-dives, and audit-ready financial models requires days of repetitive desktop publishing instead of automated, reproducible reporting pipelines.",
            ACCENT_CYAN,
        ),
    ]

    card_w = Inches(5.7)
    card_h = Inches(1.5)

    # Top row: 2 cards
    card_coords = [
        (Inches(0.8), Inches(1.6)),
        (Inches(6.8), Inches(1.6)),
        (Inches(0.8), Inches(3.3)),
        (Inches(6.8), Inches(3.3)),
        (Inches(0.8), Inches(5.0)),
    ]

    for i, (title, desc, color) in enumerate(problems):
        cx, cy = card_coords[i]
        w = Inches(11.7) if i == 4 else card_w
        card = add_card(slide, cx, cy, w, card_h, border_color=color)
        tf = card.text_frame
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(12.5)
        p_t.font.bold = True
        p_t.font.color.rgb = color

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = TEXT_BODY


def build_slide_3(prs: Presentation) -> None:
    """Slide 3: Architecture — 7-Layer Platform Diagram & Tech Stack."""
    slide = create_base_slide(
        prs,
        category_tag="System Architecture & Technical Specification",
        title="Platform Architecture: 7-Layer Production Stack",
        subtitle="A decoupled, audit-grade data pipeline from raw unstructured filings to low-latency APIs",
        slide_num=3,
    )

    layers = [
        (
            "L1",
            "Raw Ingestion",
            "12 raw source Excel workbooks, SHA-256 checksum tracking, metadata manifest",
            "pandas, openpyxl",
            ACCENT_BLUE,
        ),
        (
            "L2",
            "ETL & Normalization",
            "Schema unification, banking-statement separation, column shift recovery",
            "numpy, regex",
            ACCENT_TEAL,
        ),
        (
            "L3",
            "Data Warehouse",
            "10 normalized relational SQLite tables (db/nifty100.db, 1,155 ratio rows)",
            "sqlite3, sql",
            ACCENT_GOLD,
        ),
        (
            "L4",
            "Analytics Engine",
            "50+ KPIs, 3/5/10-yr CAGR, capital allocation, DuPont decomposition",
            "scipy, numpy",
            ACCENT_PURPLE,
        ),
        (
            "L5",
            "Screener & Ranking",
            "6 production presets, multi-pillar composite percentile ranking score",
            "screener_config.yaml",
            ACCENT_CYAN,
        ),
        (
            "L6",
            "Intelligence & ML",
            "KMeans 5-cluster market segmentation, rule-based NLP pros/cons generator",
            "scikit-learn, nltk",
            RGBColor(236, 72, 153),
        ),
        (
            "L7",
            "Delivery & APIs",
            "8-screen Streamlit dashboard, 16 FastAPI endpoints, 92 PDF tearsheets",
            "fastapi, streamlit",
            RGBColor(249, 115, 22),
        ),
    ]

    card_y = Inches(1.6)
    card_h = Inches(0.68)
    spacing = Inches(0.06)

    for i, (lvl, name, desc, tech, col) in enumerate(layers):
        cy = card_y + i * (card_h + spacing)
        card = add_card(
            slide,
            Inches(0.8),
            cy,
            Inches(11.7),
            card_h,
            border_color=BORDER_CARD,
            bg_color=BG_CARD,
        )
        tf = card.text_frame
        p = tf.paragraphs[0]

        # Badge pill
        r_lvl = p.add_run()
        r_lvl.text = f"[{lvl}] {name.upper()}: "
        r_lvl.font.name = FONT_HEADING
        r_lvl.font.size = Pt(11)
        r_lvl.font.bold = True
        r_lvl.font.color.rgb = col

        # Desc
        r_desc = p.add_run()
        r_desc.text = f"{desc}  "
        r_desc.font.name = FONT_BODY
        r_desc.font.size = Pt(9.5)
        r_desc.font.color.rgb = TEXT_BODY

        # Tech tag
        r_tech = p.add_run()
        r_tech.text = f"({tech})"
        r_tech.font.name = FONT_BODY
        r_tech.font.size = Pt(8.5)
        r_tech.font.color.rgb = TEXT_MUTED


def build_slide_4(prs: Presentation) -> None:
    """Slide 4: Data Foundation (Sprint 1)."""
    slide = create_base_slide(
        prs,
        category_tag="Sprint 1 • Data Foundation & Forensic Ingestion",
        title="Sprint 1: Data Foundation & Integrity Audit",
        subtitle="Forensic normalization across 92 companies, 10 tables, and 16 automated DQ rules",
        slide_num=4,
    )

    # Top 4 Badges
    stat_badges = [
        ("12 Source Files Ingested", ACCENT_BLUE),
        ("92 Unified Companies", ACCENT_TEAL),
        ("10 SQLite Relational Tables", ACCENT_GOLD),
        ("16 Automated DQ Rules", ACCENT_PURPLE),
    ]
    bw = Inches(2.75)
    bgap = Inches(0.24)
    for i, (txt, col) in enumerate(stat_badges):
        bx = Inches(0.8) + i * (bw + bgap)
        add_badge(
            slide,
            bx,
            Inches(1.6),
            bw,
            Inches(0.4),
            txt,
            bg_color=BG_CARD_ALT,
            text_color=col,
            font_size=10,
        )

    # 3 Detailed Pillars
    pillars = [
        (
            "Relational Database Schema",
            "Designed a clean SQLite data warehouse (db/nifty100.db) with 10 tables: companies, financial_statements, quarterly_statements, financial_ratios, capital_allocation, peer_groups, peer_percentiles, documents, screener_runs, and cluster_labels. Strict primary and foreign key constraints enforce referential integrity across all queries.",
            ACCENT_BLUE,
        ),
        (
            "16 Forensic Data Quality Rules",
            "Implemented automated auditing verifying the fundamental accounting identity (Assets = Liabilities + Equity), checking for non-negative revenues, detecting cash flow reconciliation imbalances, and validating corporate filing links. Automated audit reports generated at reports/load_audit.csv and validation_failures.csv.",
            ACCENT_TEAL,
        ),
        (
            "Key Forensic Breakthroughs",
            "1. Orphan Ticker Harmonization: Resolved mismatched company identifiers across files (e.g. M&M, L&T, MCDOWELL-N, BAJAJ-AUTO) preventing silent data loss.\n2. Banking Template Shift Discovery: Uncovered that commercial banks follow RBI-mandated schedules where standard industrial P&L/BS columns shift; built dedicated banking normalizers and audit exemptions.",
            ACCENT_GOLD,
        ),
    ]

    card_w = Inches(3.7)
    card_h = Inches(4.5)
    c_gap = Inches(0.3)

    for i, (title, desc, col) in enumerate(pillars):
        cx = Inches(0.8) + i * (card_w + c_gap)
        card = add_card(
            slide, cx, Inches(2.2), card_w, card_h, border_color=BORDER_CARD
        )
        tf = card.text_frame
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(12.5)
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_BODY


def build_slide_5(prs: Presentation) -> None:
    """Slide 5: Financial Ratio Engine (Sprint 2)."""
    slide = create_base_slide(
        prs,
        category_tag="Sprint 2 • Financial Ratio Engine & Edge Cases",
        title="Sprint 2: Financial Ratio Engine & Edge Cases",
        subtitle="50+ institutional KPIs computed across 1,155 historical annual records",
        slide_num=5,
    )

    # Top Badges
    badges = [
        ("50+ Institutional KPIs", ACCENT_BLUE),
        ("1,155 Historical Rows in DB", ACCENT_TEAL),
        ("10 Audited Years (FY15-FY24)", ACCENT_GOLD),
        ("Full DuPont 5-Stage Model", ACCENT_PURPLE),
    ]
    bw = Inches(2.75)
    bgap = Inches(0.24)
    for i, (txt, col) in enumerate(badges):
        bx = Inches(0.8) + i * (bw + bgap)
        add_badge(
            slide,
            bx,
            Inches(1.6),
            bw,
            Inches(0.4),
            txt,
            bg_color=BG_CARD_ALT,
            text_color=col,
            font_size=10,
        )

    cards = [
        (
            "Comprehensive 50+ KPI Suite",
            "• Profitability: ROE, ROCE, Operating Margin (OPM), Net Margin (NPM), Return on Assets (ROA).\n• Solvency & Capital: Debt-to-Equity (D/E), Interest Coverage Ratio (ICR), Net Debt, Net Debt/EBITDA.\n• Operating Efficiency: Debtor Days, Inventory Days, Working Capital Days, Cash Conversion Cycle (CCC).\n• Valuation Multiples: PE, PB, EV/EBITDA, Dividend Yield.",
            ACCENT_BLUE,
        ),
        (
            "DuPont 3-Stage & 5-Stage Decompositions",
            "• 3-Stage DuPont: Breaks down Return on Equity into Net Margin × Asset Turnover × Financial Leverage.\n• 5-Stage DuPont: Isolates Tax Burden × Interest Burden × Operating Margin × Asset Turnover × Leverage.\n• Reveals whether ROE expansion is driven by genuine operating moat vs. aggressive financial leverage.",
            ACCENT_TEAL,
        ),
        (
            "Critical Analytical Edge Cases Solved",
            "• CAGR Windowing Bug: Resolved strict multi-year period offset logic ensuring exact geometric compound growth rates across leap years and fiscal alignments.\n• BEL / HAL Scale Discrepancies: Identified order-of-magnitude source scale errors in public balance sheets; neutralized corrupt ratios.\n• Banking Model Isolation: Segregated banking business models from industrial debt and margin calculations.",
            ACCENT_GOLD,
        ),
    ]

    card_w = Inches(3.7)
    card_h = Inches(4.5)
    c_gap = Inches(0.3)

    for i, (title, desc, col) in enumerate(cards):
        cx = Inches(0.8) + i * (card_w + c_gap)
        card = add_card(
            slide, cx, Inches(2.2), card_w, card_h, border_color=BORDER_CARD
        )
        tf = card.text_frame
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_BODY


def build_slide_6(prs: Presentation) -> None:
    """Slide 6: Screener & Peer Comparison (Sprint 3)."""
    slide = create_base_slide(
        prs,
        category_tag="Sprint 3 • Multi-Factor Screener & Peer Benchmarking",
        title="Sprint 3: Screener Engine & Peer Benchmarking",
        subtitle="Automated multi-factor filtering, composite ranking, and 92 radar visualizations",
        slide_num=6,
    )

    boxes = [
        (
            "6 Production Screener Presets",
            (
                "Configured via screener_config.yaml:\n"
                "• Quality Compounders: ROE > 15%, D/E < 0.5, OPM > 15%\n"
                "• Value Picks: Low PE, high interest coverage, positive FCF\n"
                "• Dividend Aristocrats: Consistent payouts, low debt\n"
                "• Growth Rockets: Accelerating 3-yr revenue & EBITDA CAGR\n"
                "• Asset-Light Champions: High ROCE (>20%), low capex/CFO\n"
                "• Financial Health Fortress: Net debt negative, ICR > 5.0x"
            ),
            ACCENT_BLUE,
        ),
        (
            "Composite Ranking Engine",
            (
                "Multi-Pillar Weighted Percentile Scoring:\n"
                "• Profitability (30%): ROE, ROCE, Operating Margin\n"
                "• Solvency & Health (25%): Debt-to-Equity, Net Debt\n"
                "• Growth Momentum (25%): 3-Year Revenue & PAT CAGR\n"
                "• Valuation Prudence (20%): Trailing PE & PB multiples\n\n"
                "Features automated Winsorization (1st–99th percentiles) to prevent extreme outlier score distortions."
            ),
            ACCENT_TEAL,
        ),
        (
            "92 Vector Radar Charts",
            (
                "Benchmarking each company against peer median:\n"
                "• 6 Standardized Axes: ROE, ROCE, OPM, 3-Yr CAGR, ICR, Cash Flow Conversion\n"
                "• Visualizes economic moat asymmetry in single glance\n"
                "• Generated as high-resolution PNGs at reports/radar_charts/\n"
                "• Embedded directly into PDF tearsheets and Streamlit"
            ),
            ACCENT_GOLD,
        ),
        (
            "11 Curated Peer Groups",
            (
                "Cross-Sectional Benchmark Workbooks:\n"
                "• Sectors: IT Services, Automobiles, Pharma, FMCG, Oil & Gas, Capital Goods, Metals, Power, Telecom, Chemicals, Diversified\n"
                "• Multi-tab Excel workbook (reports/peer_comparison.xlsx)\n"
                "• Full intra-sector percentile rankings (1–100) and automated 'Best in Class' and 'Watch List' flags"
            ),
            ACCENT_PURPLE,
        ),
    ]

    card_w = Inches(5.7)
    card_h = Inches(2.25)
    coords = [
        (Inches(0.8), Inches(1.8)),
        (Inches(6.8), Inches(1.8)),
        (Inches(0.8), Inches(4.3)),
        (Inches(6.8), Inches(4.3)),
    ]

    for i, (title, desc, col) in enumerate(boxes):
        cx, cy = coords[i]
        card = add_card(slide, cx, cy, card_w, card_h, border_color=BORDER_CARD)
        tf = card.text_frame
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_BODY


def build_slide_7(prs: Presentation) -> None:
    """Slide 7: Dashboard (Sprint 4)."""
    slide = create_base_slide(
        prs,
        category_tag="Sprint 4 • Interactive Dashboard & Valuation Engine",
        title="Sprint 4: Streamlit Financial Intelligence Dashboard",
        subtitle="8 feature-rich interactive screens engineered for fundamental equity research",
        slide_num=7,
    )

    screens = [
        (
            "1. Home / Universe",
            "Macro aggregates, sector distribution, and real-time data recency timestamp (2024-09).",
            ACCENT_BLUE,
        ),
        (
            "2. Company Profile",
            "Core KPI cards, DuPont decomposition, peer benchmarking, transparent DQ warnings for SBIN/BEL/HAL.",
            ACCENT_TEAL,
        ),
        (
            "3. Financial Screener",
            "Custom threshold sliders, preset execution, and one-click formatted Excel report export.",
            ACCENT_GOLD,
        ),
        (
            "4. Peer Comparison",
            "Interactive 6-axis radar charts, intra-industry percentile heatmap, best-in-class badges.",
            ACCENT_PURPLE,
        ),
        (
            "5. Sector Analytics",
            "ROCE vs. OPM cross-sector scatter plots, margin distributions, and sector capital allocation.",
            ACCENT_CYAN,
        ),
        (
            "6. Cash Flow Intelligence",
            "10-year capital allocation stacked bars (Capex vs. Dividends), CFO/PAT ratio stress testing.",
            RGBColor(236, 72, 153),
        ),
        (
            "7. Trend & Growth",
            "3/5/10-year revenue and PAT CAGR analysis, YoY trajectory tracking across 10 audited years.",
            RGBColor(249, 115, 22),
        ),
        (
            "8. Valuation Engine",
            "Historical PE/PB valuation bands, 2-stage DCF intrinsic valuation model with sensitivity matrices.",
            RGBColor(168, 85, 247),
        ),
    ]

    card_w = Inches(2.75)
    card_h = Inches(2.15)
    gap_x = Inches(0.24)
    gap_y = Inches(0.3)

    for i, (name, desc, col) in enumerate(screens):
        row = i // 4
        col_idx = i % 4
        cx = Inches(0.8) + col_idx * (card_w + gap_x)
        cy = Inches(1.8) + row * (card_h + gap_y)

        card = add_card(slide, cx, cy, card_w, card_h, border_color=BORDER_CARD)
        tf = card.text_frame
        p_t = tf.paragraphs[0]
        p_t.text = name
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(11.5)
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_BODY


def build_slide_8(prs: Presentation) -> None:
    """Slide 8: Intelligence & Reports (Sprint 5)."""
    slide = create_base_slide(
        prs,
        category_tag="Sprint 5 • Executive Publications & NLP Intelligence",
        title="Sprint 5: Executive Reports & NLP Intelligence",
        subtitle="Automated camera-ready PDF publications and algorithmic qualitative sentiment synthesis",
        slide_num=8,
    )

    reports = [
        (
            "92 Single-Page PDF Tearsheets",
            (
                "Institutional Investment Briefs (reports/tearsheets/{ticker}_tearsheet.pdf):\n"
                "• Full 10-year audited financial history table (P&L, Balance Sheet, Cash Flow)\n"
                "• Embedded vector radar chart benchmarking company against sector peer median\n"
                "• Visual capital allocation breakdown: Operating Cash Flow vs. Organic Capex\n"
                "• Composite Score badge and auto-generated qualitative Pros & Cons bullets"
            ),
            ACCENT_BLUE,
        ),
        (
            "11 Sector Deep-Dive Research Reports",
            (
                "Comprehensive 6-Page Industry Publications (reports/sector_reports/):\n"
                "• Detailed competitive landscape analysis covering all 11 non-financial sectors\n"
                "• Aggregate sector financial statements, historical margin trends, and return distributions\n"
                "• Intra-sector percentile ranking tables identifying Best-in-Class vs. Watch List\n"
                "• Valuation multiple dispersion analysis across market cycles"
            ),
            ACCENT_TEAL,
        ),
        (
            "Macro Portfolio Summary Report",
            (
                "Cross-Universe Executive Study (reports/portfolio_summary.pdf):\n"
                "• Macro-level Nifty 100 non-financial index overview across 10 fiscal years\n"
                "• Universe-wide aggregate capital returns, operating margin trends, and leverage evolution\n"
                "• Cross-sector capital allocation breakdown isolating shareholder returns from debt paydown\n"
                "• High-risk exposure analysis and systemic balance sheet stress testing"
            ),
            ACCENT_GOLD,
        ),
        (
            "Algorithmic Pros & Cons Generator",
            (
                "Audited Qualitative Synthesis (data/processed/pros_cons_generated.csv):\n"
                "• Rule-based NLP heuristics synthesizing balance sheet strength and earnings quality\n"
                "• Produces 2-4 verified strengths and 1-3 risk watchpoints per company\n"
                "• 100% universe coverage (all 92 companies have high-confidence pros and cons)\n"
                "• Confidence scoring algorithm verifying statements against numeric ratios"
            ),
            ACCENT_PURPLE,
        ),
    ]

    card_w = Inches(5.7)
    card_h = Inches(2.25)
    coords = [
        (Inches(0.8), Inches(1.8)),
        (Inches(6.8), Inches(1.8)),
        (Inches(0.8), Inches(4.3)),
        (Inches(6.8), Inches(4.3)),
    ]

    for i, (title, desc, col) in enumerate(reports):
        cx, cy = coords[i]
        card = add_card(slide, cx, cy, card_w, card_h, border_color=BORDER_CARD)
        tf = card.text_frame
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_BODY


def build_slide_9(prs: Presentation) -> None:
    """Slide 9: API & Clustering (Sprint 6)."""
    slide = create_base_slide(
        prs,
        category_tag="Sprint 6 • REST API & Machine Learning Clustering",
        title="Sprint 6: REST API & Machine Learning Clustering",
        subtitle="Sub-50ms quantitative microservices and structural market archetypes",
        slide_num=9,
    )

    items = [
        (
            "16 High-Performance FastAPI Endpoints",
            "• Full RESTful Suite: Company profiles, multi-year ratio histories, financial statements, screener presets, peer rankings, and direct PDF downloads.\n• High Concurrency: Asynchronous architecture with LRU memory caching ensuring sub-50ms response times for quantitative trading workflows.\n• Strict Data Contracts: Powered by Pydantic v2 validation models with strict schema typing.",
            ACCENT_BLUE,
        ),
        (
            "Interactive OpenAPI / Swagger Integration",
            "• Interactive Developer Portal: Fully documented Swagger UI and ReDoc accessible at http://localhost:8000/docs.\n• Machine-Readable OpenAPI 3.1: Exported schema at docs/openapi.json enabling automated client generation across Python, TypeScript, and R.\n• Error Standards: Standardized HTTP status codes (200, 404, 422, 500) with detailed error diagnostics.",
            ACCENT_TEAL,
        ),
        (
            "KMeans 5-Cluster Market Segmentation",
            (
                "Unsupervised fundamental clustering across 89 non-distorted companies:\n"
                "• Cluster 0: High-Margin Moat Champions (IT Services & FMCG; ROCE > 35%, zero net debt)\n"
                "• Cluster 1: Capital-Intensive Industrial Compounds (Power & Steel; high asset base, leverage)\n"
                "• Cluster 2: High-Growth Scalers (Accelerating revenue CAGR, reinvesting CFO)\n"
                "• Cluster 3: Leverage-Sensitive Turnarounds (Elevated debt, recovery potential)\n"
                "• Cluster 4: Cash-Rich Defensive Cash Cows (Mature cash generators, dividend focus)"
            ),
            ACCENT_GOLD,
        ),
    ]

    card_w = Inches(3.7)
    card_h = Inches(4.2)
    c_gap = Inches(0.3)

    for i, (title, desc, col) in enumerate(items):
        cx = Inches(0.8) + i * (card_w + c_gap)
        card = add_card(
            slide, cx, Inches(1.8), card_w, card_h, border_color=BORDER_CARD
        )
        tf = card.text_frame
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.name = FONT_HEADING
        p_t.font.size = Pt(12)
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.name = FONT_BODY
        p_d.font.size = Pt(9.5)
        p_d.font.color.rgb = TEXT_BODY

    # Bottom Banner for 245 Tests
    banner = add_card(
        slide,
        Inches(0.8),
        Inches(6.15),
        Inches(11.7),
        Inches(0.65),
        border_color=ACCENT_TEAL,
        bg_color=BG_CARD_ALT,
    )
    btf = banner.text_frame
    bp = btf.paragraphs[0]
    r1 = bp.add_run()
    r1.text = "✓ QUALITY ASSURANCE BENCHMARK:  "
    r1.font.bold = True
    r1.font.size = Pt(10.5)
    r1.font.color.rgb = ACCENT_TEAL
    r2 = bp.add_run()
    r2.text = (
        "245 / 245 Automated Tests Passing across ETL, Data Quality, KPI Engine, Screener, "
        "and API Endpoints (100% Pass Rate in Pytest HTML Report)."
    )
    r2.font.size = Pt(10)
    r2.font.color.rgb = TEXT_BODY


def build_slide_10(prs: Presentation) -> None:
    """Slide 10: Key Analytical Findings."""
    slide = create_base_slide(
        prs,
        category_tag="Empirical Discoveries & Data Intelligence",
        title="Analytical Breakthroughs: 5 Discoveries from N100 Data",
        subtitle="Empirical insights uncovered through forensic data engineering and financial ratio analysis",
        slide_num=10,
    )

    findings = [
        (
            "1. IT Sector Valuation Moat",
            "Indian IT Services companies exhibit median ROCE > 40% and negligible net debt, sustaining 10-year median valuation premiums exceeding 25x PE across all market cycles.",
            ACCENT_BLUE,
        ),
        (
            "2. Scarcity of Quality Compounders",
            "Only 14 of 92 companies met all criteria for the rigorous Quality Compounder preset (ROE > 15%, D/E < 0.5, OPM > 15%), demonstrating true competitive scarcity.",
            ACCENT_TEAL,
        ),
        (
            "3. Banking Template Duality",
            "Banking institutions represent ~25% of index market cap but follow statutory RBI schedules. Forcing industrial manufacturing ratios onto banks creates artificial distortion.",
            ACCENT_GOLD,
        ),
        (
            "4. The IRFC Capital Dynamic",
            "Indian Railway Finance Corp maintains extreme leverage (D/E > 8.0x) paired with sovereign-backed receivables and near-100% CFO/PAT conversion, operating as a sovereign financing utility.",
            ACCENT_PURPLE,
        ),
        (
            "5. Public Data Quality Traps",
            "Uncovered that commercial data feeds harbor 10x or 100x scale errors in specific Balance Sheet line items (e.g. BEL and HAL). Algorithmic forensic DQ rules are mandatory before quant modeling.",
            ACCENT_CYAN,
        ),
    ]

    card_w = Inches(11.7)
    card_h = Inches(0.85)
    spacing = Inches(0.12)
    start_y = Inches(1.8)

    for i, (title, desc, col) in enumerate(findings):
        cy = start_y + i * (card_h + spacing)
        card = add_card(
            slide,
            Inches(0.8),
            cy,
            card_w,
            card_h,
            border_color=BORDER_CARD,
            bg_color=BG_CARD,
        )
        tf = card.text_frame
        p = tf.paragraphs[0]

        r_t = p.add_run()
        r_t.text = f"{title}:  "
        r_t.font.name = FONT_HEADING
        r_t.font.size = Pt(11.5)
        r_t.font.bold = True
        r_t.font.color.rgb = col

        r_d = p.add_run()
        r_d.text = desc
        r_d.font.name = FONT_BODY
        r_d.font.size = Pt(10)
        r_d.font.color.rgb = TEXT_BODY


def build_slide_11(prs: Presentation) -> None:
    """Slide 11: Results Summary & Delivery Timeline Table."""
    slide = create_base_slide(
        prs,
        category_tag="Project Delivery & Acceptance Summary",
        title="Results Summary: 6 Sprints Delivered Ahead of Schedule",
        subtitle="Uncompromising execution quality and zero-defect delivery across all 23 platform commitments",
        slide_num=11,
    )

    # Summary Table
    rows = 7
    cols = 5
    table_shape = slide.shapes.add_table(
        rows, cols, Inches(0.8), Inches(1.8), Inches(11.7), Inches(3.2)
    )
    table = table_shape.table

    # Column Widths
    table.columns[0].width = Inches(1.5)
    table.columns[1].width = Inches(3.2)
    table.columns[2].width = Inches(1.6)
    table.columns[3].width = Inches(1.6)
    table.columns[4].width = Inches(3.8)

    headers = [
        "Sprint",
        "Phase / Core Focus",
        "Target Due",
        "Actual Date",
        "Key Deliverable & Status",
    ]
    for c_idx, h_text in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(37, 99, 235)  # #2563EB Blue
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        p.text = h_text
        p.font.name = FONT_HEADING
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = TEXT_TITLE

    timeline_data = [
        (
            "Sprint 1",
            "Data Foundation & SQLite ETL",
            "Sept 20, 2026",
            "Sept 19, 2026",
            "db/nifty100.db, 16 DQ Rules (COMPLETE)",
        ),
        (
            "Sprint 2",
            "Ratio Engine & Edge Cases",
            "Sept 27, 2026",
            "Sept 26, 2026",
            "50+ KPIs, 1,155 Rows (COMPLETE)",
        ),
        (
            "Sprint 3",
            "Screener & Peer Benchmarking",
            "Oct 04, 2026",
            "Oct 03, 2026",
            "6 Presets, 92 Radar PNGs (COMPLETE)",
        ),
        (
            "Sprint 4",
            "Streamlit Interactive Dashboard",
            "Oct 11, 2026",
            "Oct 10, 2026",
            "8 Live Screens, DCF Engine (COMPLETE)",
        ),
        (
            "Sprint 5",
            "Executive Reports & NLP",
            "Oct 18, 2026",
            "Oct 16, 2026",
            "92 Tearsheets, 11 Sector PDFs (COMPLETE)",
        ),
        (
            "Sprint 6",
            "FastAPI, Clustering & QA",
            "Oct 24, 2026",
            "Oct 18, 2026",
            "16 Endpoints, 245 Tests (COMPLETE)",
        ),
    ]

    for r_idx, row_data in enumerate(timeline_data, start=1):
        bg_col = BG_CARD if r_idx % 2 == 1 else BG_CARD_ALT
        for c_idx, val in enumerate(row_data):
            cell = table.cell(r_idx, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = bg_col
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.name = FONT_BODY
            p.font.size = Pt(9.5)
            if c_idx == 0:
                p.font.bold = True
                p.font.color.rgb = ACCENT_BLUE
            elif c_idx == 4:
                p.font.color.rgb = ACCENT_TEAL
            else:
                p.font.color.rgb = TEXT_BODY

    # 3 Stat Cards Below Table
    stat_cards = [
        ("23 / 23 DELIVERABLES", "100% COMPLETE & AUDITED", ACCENT_BLUE),
        ("245 AUTOMATED TESTS", "0 FAILURES, 0 REGRESSIONS", ACCENT_TEAL),
        ("SUBMISSION TIMELINE", "TAGGED v1.0 AHEAD OF SCHEDULE", ACCENT_GOLD),
    ]
    sw = Inches(3.7)
    sgap = Inches(0.3)
    sy = Inches(5.3)

    for i, (t1, t2, col) in enumerate(stat_cards):
        sx = Inches(0.8) + i * (sw + sgap)
        sc = add_card(
            slide,
            sx,
            sy,
            sw,
            Inches(1.2),
            border_color=col,
            bg_color=BG_CARD,
        )
        stf = sc.text_frame
        p1 = stf.paragraphs[0]
        p1.text = t1
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = col

        p2 = stf.add_paragraph()
        p2.text = t2
        p2.font.name = FONT_BODY
        p2.font.size = Pt(13)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_TITLE


def build_slide_12(prs: Presentation) -> None:
    """Slide 12: Thank You & Platform Access."""
    slide = create_base_slide(
        prs,
        category_tag="Production Release & Access Verification",
        title="Thank You: N100 Financial Intelligence Platform",
        subtitle="Full institutional equity research infrastructure built for Bluestock Fintech",
        slide_num=12,
    )

    # 4 Highlight Stat Boxes
    highlights = [
        (
            "92",
            "COMPANIES INGESTED",
            "10 Audited Years (FY15–FY24)",
            ACCENT_BLUE,
        ),
        (
            "50+",
            "FINANCIAL RATIOS & KPIS",
            "Standardized & Winsorized",
            ACCENT_TEAL,
        ),
        (
            "245",
            "TESTS PASSING (100%)",
            "CI/CD Verified via Pytest",
            ACCENT_GOLD,
        ),
        (
            "23",
            "PLATFORM DELIVERABLES",
            "100% Production Ready",
            ACCENT_PURPLE,
        ),
    ]

    hw = Inches(2.75)
    hgap = Inches(0.24)
    hy = Inches(1.8)

    for i, (big_num, tag, sub, col) in enumerate(highlights):
        hx = Inches(0.8) + i * (hw + hgap)
        card = add_card(
            slide, hx, hy, hw, Inches(1.8), border_color=col, bg_color=BG_CARD
        )
        tf = card.text_frame
        p_num = tf.paragraphs[0]
        p_num.text = big_num
        p_num.font.name = FONT_HEADING
        p_num.font.size = Pt(36)
        p_num.font.bold = True
        p_num.font.color.rgb = col

        p_tag = tf.add_paragraph()
        p_tag.text = tag
        p_tag.font.name = FONT_HEADING
        p_tag.font.size = Pt(10)
        p_tag.font.bold = True
        p_tag.font.color.rgb = TEXT_TITLE

        p_sub = tf.add_paragraph()
        p_sub.text = sub
        p_sub.font.name = FONT_BODY
        p_sub.font.size = Pt(8.5)
        p_sub.font.color.rgb = TEXT_MUTED

    # Bottom Access & Repository Details Card
    access_card = add_card(
        slide,
        Inches(0.8),
        Inches(3.9),
        Inches(11.7),
        Inches(2.7),
        border_color=BORDER_CARD,
        bg_color=BG_CARD,
    )
    atf = access_card.text_frame
    ap0 = atf.paragraphs[0]
    ap0.text = "PLATFORM RESOURCES & VERIFICATION PORTALS"
    ap0.font.name = FONT_HEADING
    ap0.font.size = Pt(13)
    ap0.font.bold = True
    ap0.font.color.rgb = ACCENT_BLUE

    links = [
        (
            "• GitHub Repository:",
            "https://github.com/Varundeep09/n100_financial_platform (Release Tag: v1.0)",
        ),
        (
            "• FastAPI Interactive Documentation:",
            "http://localhost:8000/docs (OpenAPI 3.1 specification at docs/openapi.json)",
        ),
        (
            "• Streamlit 8-Screen Live Dashboard:",
            "http://localhost:8501 (Run via: streamlit run src/dashboard/app.py)",
        ),
        (
            "• Complete Platform Documentation:",
            "docs/demo_script.md  •  reports/analyst_guide.pdf  •  reports/acceptance_checklist.pdf",
        ),
        (
            "• Author & Technical Contact:",
            "Varundeep Sengar (Platform Engineering & Quantitative Research, Bluestock Fintech)",
        ),
    ]

    for label, val in links:
        p = atf.add_paragraph()
        r1 = p.add_run()
        r1.text = f"{label} "
        r1.font.name = FONT_HEADING
        r1.font.size = Pt(10.5)
        r1.font.bold = True
        r1.font.color.rgb = TEXT_TITLE

        r2 = p.add_run()
        r2.text = val
        r2.font.name = FONT_BODY
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = TEXT_BODY


# ==============================================================================
# MAIN GENERATION ENTRYPOINT
# ==============================================================================
def generate_presentation(output_path: str = "reports/N100_Presentation.pptx") -> Path:
    """Generate the complete 12-slide institutional presentation.

    Args:
        output_path: Path string where the PowerPoint presentation will be saved.

    Returns:
        Path object pointing to the generated PPTX file.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    # 16:9 Widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    print("Building Slide 1: Title...")
    build_slide_1(prs)
    print("Building Slide 2: Problem Statement...")
    build_slide_2(prs)
    print("Building Slide 3: Architecture...")
    build_slide_3(prs)
    print("Building Slide 4: Data Foundation (Sprint 1)...")
    build_slide_4(prs)
    print("Building Slide 5: Financial Ratio Engine (Sprint 2)...")
    build_slide_5(prs)
    print("Building Slide 6: Screener & Peer Comparison (Sprint 3)...")
    build_slide_6(prs)
    print("Building Slide 7: Interactive Dashboard (Sprint 4)...")
    build_slide_7(prs)
    print("Building Slide 8: Intelligence & Reports (Sprint 5)...")
    build_slide_8(prs)
    print("Building Slide 9: API & Clustering (Sprint 6)...")
    build_slide_9(prs)
    print("Building Slide 10: Key Analytical Findings...")
    build_slide_10(prs)
    print("Building Slide 11: Results Summary & Delivery Timeline...")
    build_slide_11(prs)
    print("Building Slide 12: Thank You & Platform Access...")
    build_slide_12(prs)

    prs.save(str(out_file))
    print(
        f"Successfully generated presentation with {len(prs.slides)} slides at {out_file.resolve()}"
    )
    return out_file


if __name__ == "__main__":
    generate_presentation()
