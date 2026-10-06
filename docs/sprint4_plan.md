# Sprint 4 Planning Document: Interactive Dashboard & Valuation Engine

**Document Version:** 1.0  
**Date of Preparation:** October 6, 2026  
**Execution Window:** October 8 – October 14, 2026 (Days 22–28)  
**Author:** Antigravity (Data Analytics & Visualization Specialist)  
**Target Modules:** Module 5 (Interactive Streamlit Dashboard) & Module 6 (Valuation & Market Data Engine)

---

## 1. Executive Summary & Sprint Objectives

Sprint 4 marks the transition of the N100 Financial Intelligence Platform from analytical pipelines and batch export artifacts into an interactive, visual, and institutional-grade decision platform.

The primary objectives for Sprint 4 are:
1. **Interactive Streamlit Web Dashboard (Module 5):** Build an 8-screen institutional financial analysis web application powered by Streamlit and Plotly. The application connects directly to the validated SQLite database (`db/nifty100.db`), providing interactive filtering, rich dynamic visualizations, side-by-side benchmarking, trend decomposition, and annual report document retrieval.
2. **Valuation & Multiples Analytics Engine (Module 6):** Deliver a quantitative valuation module leveraging historical market capitalization data (`market_cap` table, 2019–2024). This module computes 5-year median valuation multiples (P/E, P/B, EV/EBITDA), FCF yields, and dividend yields, and establishes an automated valuation anomaly detection framework (`Caution` / `Discount` badges).
3. **Institutional Reporting Artifacts:** Generate `reports/valuation_summary.xlsx` and `reports/valuation_flags.csv`, fully documenting current and median multiples, sector rankings, and valuation flags for all 92 Nifty 100 constituents.

---

## 2. Day-by-Day Task Breakdown (Days 22–28)

### **Day 22 (Oct 08): Dashboard Scaffolding & Core Architecture (`src/dashboard/app.py`)**
- **Core Objectives:**
  - Establish the Streamlit application structure in `src/dashboard/app.py`.
  - Configure global page layout (`wide`), institutional dark/navy theme, custom CSS styling, and Bluestock platform branding.
  - Implement sidebar navigation routing across all 8 functional screens.
  - Build a high-performance cached database loader (`load_db()`) leveraging `@st.cache_data` to ensure zero redundant disk queries.
  - Establish error-boundary wrappers and graceful fallback components for missing or partial data records.
- **Deliverables:** `src/dashboard/app.py`, `src/dashboard/__init__.py`, basic multi-screen router.

### **Day 23 (Oct 09): Home Overview (Screen 5.1) & Company Tearsheet Profile (Screen 5.2)**
- **Core Objectives:**
  - **Screen 5.1 (Home / Overview):**
    - High-level Nifty 100 market summary cards: Index Average ROE, Median P/E, Median D/E, Total Market Cap.
    - Broad sector distribution donut / breakdown chart.
    - Market breadth and data quality banner (100% audited ETL coverage, 92 companies, 1,155 fiscal years).
  - **Screen 5.2 (Company Profile):**
    - Ticker search box with autocomplete across company name and ticker ID.
    - Company header banner: Sector, Sub-industry, BSE Code, NSE Symbol, Current Market Cap.
    - 6 core KPI metric tiles (ROE, ROCE, P/E, D/E, FCF, 3yr Revenue CAGR) with color-coded benchmark badges.
    - 10-year interactive financial charts: Revenue & Operating Profit (Bar/Line), Balance Sheet Composition, Cash Flow Bridge.
    - Embedded 8-axis intra-group radar chart loaded from `reports/radar_charts/{ticker}_radar.png`.
- **Deliverables:** Screens 5.1 & 5.2 operational with interactive Plotly charts.

### **Day 24 (Oct 10): Financial Screener (Screen 5.3) & Peer Comparison (Screen 5.4)**
- **Core Objectives:**
  - **Screen 5.3 (Financial Screener):**
    - Sidebar interactive sliders and input boxes for 10 core fundamental thresholds (ROE, D/E, FCF, Revenue CAGR, OPM, P/E, P/B, CapEx Intensity, CFO Score, Dividend Payout).
    - Quick-load buttons for the 6 production presets (Quality Compounder, Value Pick, Dividend Aristocrat, Growth Rocket, Asset Light Champion, Financial Health).
    - Live-filtered interactive table showing matching companies, sector badges, key metrics, and composite ranking scores.
    - One-click CSV export button for filtered results.
  - **Screen 5.4 (Peer Comparison):**
    - Dropdown selector for the 11 granular peer groups (56 mapped companies).
    - Interactive 8-axis radar chart comparison (Company vs. Peer Average vs. Benchmark Leader).
    - Side-by-side comparative matrix of 20 metrics and 20 benchmark gaps with 3-tier conditional color formatting (Best in Class, In Line, Watch List).
    - Visual highlighting of designated group benchmark leaders (e.g. TCS, HDFCBANK).
- **Deliverables:** Screens 5.3 & 5.4 fully operational with live filtering and peer benchmarking.

### **Day 25 (Oct 11): Advanced Analytics Screens (Screens 5.5 – 5.8)**
- **Core Objectives:**
  - **Screen 5.5 (Trend & Growth Analysis):**
    - Interactive 10-year trajectory visualizer: Company + metric selector with YoY growth annotations and CAGR trend lines.
    - Multi-metric overlay mode (e.g., comparing Revenue growth vs. PAT growth, or Operating Cash Flow vs. Net Profit).
  - **Screen 5.6 (Sector Analytics):**
    - Sector selector and cross-sector comparison bubble chart (X = Revenue, Y = ROE, Bubble Size = Market Cap, Color = Sector).
    - Sector median bar charts across P/E, ROE, ROCE, and Operating Margins.
  - **Screen 5.7 (Capital Allocation Map):**
    - Treemap categorization of all 92 companies into the 8 Capital Allocation archetypes based on 10-year cumulative CFO/CFI/CFF signs.
    - Interactive drill-down to constituent company lists with cash flow reinvestment metrics.
  - **Screen 5.8 (Annual Reports & Document Intelligence):**
    - Company and fiscal year selector displaying annual report filing metadata.
    - Direct clickable links to official BSE annual report PDF filings and local report artifacts.
- **Deliverables:** Screens 5.5, 5.6, 5.7, and 5.8 complete and integrated into navigation.

### **Day 26 (Oct 12): Valuation & Market Multiples Module (`src/analytics/valuation.py`)**
- **Core Objectives:**
  - Ingest `market_cap` table (552 rows, 2019–2024) and compute:
    1. Historical 5-year median multiples per company (P/E, P/B, EV/EBITDA).
    2. Sector median multiples for relative valuation benchmarking.
    3. FCF Yield ($	ext{FCF} / 	ext{Market Cap} 	imes 100$) and Dividend Yield ranking.
    4. Automated Overvaluation & Undervaluation Flags:
       - `Caution (Overvalued)`: $	ext{Current P/E} > 1.5 	imes 	ext{Sector Median P/E}$.
       - `Discount (Undervalued)`: $	ext{Current P/E} < 0.7 	imes 	ext{Sector Median P/E}$.
  - Generate publication-ready Excel report: `reports/valuation_summary.xlsx` (all 92 companies with current vs. 5yr median multiples, sector ranks, and badges).
  - Generate `reports/valuation_flags.csv`.
  - Embed Valuation analytics cards into the Company Profile and Sector screens.
- **Deliverables:** `src/analytics/valuation.py`, `reports/valuation_summary.xlsx`, `reports/valuation_flags.csv`.

### **Day 27 (Oct 13): Comprehensive Dashboard QA & Edge-Case Validation**
- **Core Objectives:**
  - Execute systematic testing across all 8 screens using 15 diverse company tickers (representing banks, NBFCs, IT services, heavy industrials, capital-light FMCG, and turnaround cases).
  - Verify layout responsiveness, chart container scaling, table sorting, and pagination.
  - Validate defensive UI rendering against all known data edge cases (banking nulls, BEL/HAL scale error notes, SBIN missing cash flows).
  - Document all testing results and visual inspection logs in `reports/dashboard_qa.md`.
- **Deliverables:** `reports/dashboard_qa.md`, zero UI runtime exceptions.

### **Day 28 (Oct 14): Sprint Retrospective, Documentation & Sprint 4 Sign-Off**
- **Core Objectives:**
  - Update `README.md` with explicit dashboard execution instructions (`streamlit run src/dashboard/app.py`).
  - Run the full automated test suite (ensure 207+ tests green with 0 regressions).
  - Author formal retrospective document `reports/sprint4_retro.md`.
  - Conduct final code quality pass with `black` and `ruff`.
  - Git tag release `sprint4-complete` and push to remote.
- **Deliverables:** `reports/sprint4_retro.md`, updated `README.md`, release tag `sprint4-complete`.

---

## 3. Explicit Sprint 4 Deliverables Checklist

| # | Deliverable | Target Path / Artifact | Description |
|:---:|:---|:---|:---|
| **1** | **Streamlit Application Core** | `src/dashboard/app.py` | Main Streamlit application entry point with sidebar navigation and global theme. |
| **2** | **Home / Overview Screen** | Screen 5.1 in `src/dashboard/app.py` | Macro Nifty 100 summary cards, sector breakdown donut, and index breadth banner. |
| **3** | **Company Tearsheet Profile** | Screen 5.2 in `src/dashboard/app.py` | Ticker search, 6 KPI tiles, 10yr P&L / BS / CF charts, and 8-axis radar visualization. |
| **4** | **Financial Screener Screen** | Screen 5.3 in `src/dashboard/app.py` | Multi-slider fundamental filter, 6 presets quick-load, live table, and CSV export. |
| **5** | **Peer Comparison Screen** | Screen 5.4 in `src/dashboard/app.py` | Peer group selector, 8-axis radar overlay, and 20-metric comparative heatmap matrix. |
| **6** | **Trend Analysis Screen** | Screen 5.5 in `src/dashboard/app.py` | 10-year sparklines, YoY % annotations, multi-metric overlay, and CAGR trends. |
| **7** | **Sector Analysis Screen** | Screen 5.6 in `src/dashboard/app.py` | Cross-sector bubble charts (Revenue vs. ROE vs. Mkt Cap) and median KPI bar charts. |
| **8** | **Capital Allocation Screen** | Screen 5.7 in `src/dashboard/app.py` | Treemap of 92 companies across the 8 CFO/CFI/CFF capital allocation archetypes. |
| **9** | **Annual Reports Screen** | Screen 5.8 in `src/dashboard/app.py` | Annual report filing repository with clickable BSE PDF links and filing metadata. |
| **10** | **Valuation Analytics Engine** | `src/analytics/valuation.py` | Valuation multiples calculation, 5yr medians, FCF yield, and overvaluation flags. |
| **11** | **Valuation Summary Workbook** | `reports/valuation_summary.xlsx` | Multi-tab Excel workbook with current/historical multiples, ranks, and caution badges. |
| **12** | **Valuation Flags Export** | `reports/valuation_flags.csv` | Exported list of `Caution` and `Discount` flagged companies with valuation rationale. |
| **13** | **Dashboard QA Log** | `reports/dashboard_qa.md` | Formal QA log verifying all 8 screens across diverse test tickers and edge cases. |
| **14** | **Sprint 4 Retrospective** | `reports/sprint4_retro.md` | Comprehensive retrospective covering achievements, challenges, and Sprint 5 contracts. |

---

## 4. Exit Criteria for Sprint 4 Sign-Off

To achieve formal Sprint 4 sign-off, all following criteria must be satisfied with 100% compliance:
1. **Streamlit App Operational:** Streamlit app launches locally (`streamlit run src/dashboard/app.py`) without any import, syntax, or runtime errors.
2. **8 Screens Navigable:** All 8 screens are fully accessible via sidebar navigation and render valid data from SQLite without unhandled exceptions.
3. **Interactive Visualizations:** All charts are interactive (Plotly), responsive to window resizing, and support hover tooltips.
4. **Valuation Engine Complete:** `reports/valuation_summary.xlsx` generated for all 92 companies with valid 5yr median multiples, sector ranks, and overvaluation badges.
5. **Zero Data Leaks / Corrupted Data Protection:**
   - Banking template entities render "N/A (Banking Template)" for inapplicable industrial metrics.
   - BEL and HAL display cautionary tooltips for BS-dependent ratios and are excluded from ungrounded valuation outlier flags.
   - SBIN renders explicit note for missing source cash flow data rather than erroneous zero FCF.
6. **Zero Test Regressions:** Full test suite passes with **207+ tests green** (100% pass rate).
7. **Code Standards:** 100% compliance with `black` code formatting and `ruff` linting across all new modules.
8. **Documentation:** `reports/sprint4_retro.md` and `reports/dashboard_qa.md` written and approved.

---

## 5. Data Dependencies (SQLite Tables Read by Sprint 4)

Sprint 4 consumes data exclusively from the verified SQLite database (`db/nifty100.db`):

| SQLite Table | Rows | Primary Columns Read | Target Screens / Modules |
|:---|:---:|:---|:---|
| **`companies`** | 92 | `id`, `name`, `broad_sector`, `sub_industry`, `bse_code`, `nse_symbol`, `isin`, `market_cap_cr` | Screens 5.1, 5.2, 5.4, 5.6, 5.8, Valuation |
| **`sectors`** | 11 | `id`, `name`, `broad_sector`, `description` | Screens 5.1, 5.3, 5.6, Valuation |
| **`profitandloss`** | 1,073 | `company_id`, `year`, `sales`, `expenses`, `operating_profit`, `net_profit`, `eps` | Screens 5.2, 5.5 |
| **`balancesheet`** | 1,073 | `company_id`, `year`, `equity_capital`, `reserves`, `borrowings`, `other_liabilities`, `total_assets` | Screens 5.2, 5.5 |
| **`cashflow`** | 1,073 | `company_id`, `year`, `cash_from_operations`, `cash_from_investing`, `cash_from_financing`, `net_cash_flow` | Screens 5.2, 5.5, 5.7 |
| **`financial_ratios`** | 1,155 | `company_id`, `year`, 50 computed profitability, solvency, cash flow, and growth ratios | Screens 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, Valuation |
| **`market_cap`** | 552 | `company_id`, `year`, `pe_ratio`, `pb_ratio`, `ev_ebitda`, `dividend_yield_pct`, `market_cap_cr` | Screens 5.1, 5.2, 5.3, 5.6, Module 6 Valuation |
| **`peer_groups`** | 56 | `peer_group_name`, `company_id`, `is_benchmark` | Screen 5.4 Peer Comparison |
| **`peer_percentiles`** | 1,120 | `company_id`, `peer_group_name`, `metric_name`, `metric_value`, `percentile_rank`, `classification`, `benchmark_gap_pct` | Screen 5.4 Peer Comparison |
| **`documents`** | 552 | `company_id`, `year`, `report_type`, `filing_date`, `source_url`, `local_filepath`, `pdf_available` | Screen 5.8 Annual Reports |

---

## 6. Inherited Limitations & Architectural Defenses for Sprint 4

To ensure an audit-grade user experience, the dashboard and valuation engine implement strict architectural defenses for inherited data constraints:

### 1. Banking & NBFC Template Specifics (16 Institutions)
- **Constraint:** Banks (e.g. HDFCBANK, ICICIBANK, SBIN) and NBFCs (e.g. BAJFINANCE, PFC, RECLTD) structurally lack Operating Profit Margin (OPM), ROCE, Interest Coverage Ratio (ICR), and CFO Quality Score.
- **Dashboard Defense:**
  - In Screen 5.2 (Company Profile), metric tiles for OPM and ROCE display `"N/A (Bank/NBFC Template)"` with an informational tooltip rather than `None` or `NaN`.
  - In Screen 5.3 (Screener), when filtering by OPM or ROCE, banking entities are safely bypassed unless the analyst explicitly selects an all-sector screen.
  - In Screen 5.4 (Peer Comparison), peer groups for Banks and Consumer Finance evaluate sector-relevant ratios (e.g. ROA, Net Margin, P/B) and omit irrelevant manufacturing ratios.

### 2. BEL & HAL Corrupted Balance Sheet Neutralization (~100x Scale Error)
- **Constraint:** Raw source balance sheets for BEL and HAL scaled equity and reserves down by ~100x, producing ungrounded 4,744% and 3,816% ROEs. Flagged with `extreme_magnitude_flag = 1` and `data_quality_label = 'Unreliable BS Data (Scale Error ~100x)'`.
- **Dashboard Defense:**
  - Any screen rendering ROE, ROCE, or Book Value per Share for BEL or HAL must render a prominent cautionary warning badge: `⚠️ Neutralized: Source Balance Sheet Scale Error (~100x)`.
  - In Module 6 (Valuation), BEL and HAL are excluded from P/B outlier screening to prevent spurious "Overvalued" flags resulting from false balance sheet denominators.

### 3. SBIN Missing Operating Cash Flow Data
- **Constraint:** Source `cashflow.xlsx` lacks `operating_activity` rows for SBIN, resulting in `free_cash_flow_cr = None`.
- **Dashboard Defense:**
  - Cash flow tiles and FCF Yield calculations for SBIN display `"Source Gap: Operating CF Not Reported in Source"` rather than defaulting to `₹0 Cr`.

### 4. Non-Peer Group Universe Handling (36 Companies)
- **Constraint:** Only 56 of the 92 companies are assigned to one of the 11 homogeneous peer groups in `peer_groups`. The remaining 36 companies (spanning Conglomerates, Cement, Metals, Chemicals, Retail) have no direct peer group mapping.
- **Dashboard Defense:**
  - Screen 5.4 (Peer Comparison) provides an explicit informative notice for the 36 unassigned companies: `"This company is not part of a predefined 11-member peer group. Displaying broad sector benchmark comparison."`

### 5. Multi-Year CAGR Flags (`INSUFFICIENT`, `TURNAROUND`, `DECLINE_TO_LOSS`)
- **Constraint:** Companies with non-contiguous reporting histories (e.g. AMBUJACEM missing FY22, LODHA) or short histories (JIOFIN) have CAGRs flagged with explicit quality labels.
- **Dashboard Defense:**
  - Screen 5.2 and Screen 5.5 render status chips next to CAGR numbers (e.g. `[INSUFFICIENT HISTORICAL DATA]`, `[TURNAROUND (Negative Base)]`) to ensure analysts immediately understand why a CAGR is omitted or non-standard.
