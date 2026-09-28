# Sprint 3 Planning Document: Screener & Peer Comparison Engine

**Document Version:** 1.0  
**Date of Preparation:** September 28, 2026  
**Execution Window:** September 30 - October 7, 2026 (Days 15-21)  
**Author:** Gemini (Advanced Analytics & Screener Specialist)  
**Target Modules:** Module 3 (Company Screener & Filter Engine) & Module 4 (Peer Comparison Engine)

---

## 1. Executive Summary & Sprint Objectives

Sprint 3 bridges fundamental ratio computation (Sprint 2) with interactive visual consumption (Sprint 4 Dashboard) and institutional reporting (Sprint 5 Tearsheets). The primary objective is to empower financial analysts to filter, rank, and benchmark all 92 Nifty 100 companies through:
1. A **declarative, multi-criteria screener engine** driven by YAML configuration, supporting 6 production preset templates, dynamic thresholding, multi-year trend logic, and sector-relative composite ranking.
2. An **institutional peer comparison engine** covering all 11 predefined peer groups (56 mapped companies), computing intra-group percentile distributions across 20 metrics, generating 92 company radar charts, and exporting a formatted Excel comparison workbook.

---

## 2. Day-by-Day Task Breakdown (Days 15-21)

### **Day 15 (Sep 30): Custom Filter & Query Engine (`src/screener/engine.py`)**
- **Core Objectives:**
  - Build `src/screener/engine.py` to evaluate arbitrary combinations of financial criteria.
  - Implement YAML configuration loader for `screener_config.yaml`.
  - Ingest pre-computed ratios from `db/nifty100.db` (`financial_ratios` joined with `companies`, `sectors`, and `market_cap`).
  - Support comparison operators (`>`, `<`, `>=`, `<=`, `==`, `!=`, `BETWEEN`, `IN`).
  - Implement multi-year trend filters (e.g., metric strictly increasing for $N$ consecutive years, or FCF positive for 5 consecutive periods).
  - Ensure robust handling of `None` / `NaN` values to prevent runtime crashes when evaluating companies with data gaps.
- **Deliverable:** `src/screener/engine.py`

### **Day 16 (Oct 01): 6 Preset Screeners & Universe Validation**
- **Core Objectives:**
  - Formalize the 6 preset screener definitions inside `screener_config.yaml`:
    1. **Quality Compounder:** ROE > 15%, D/E < 1.0, FCF > 0, Revenue 5yr CAGR > 10% (Expected: 15-35 companies).
    2. **Value Pick:** P/E < 20, P/B < 3.0, D/E < 2.0, Dividend Yield > 1% (Expected: 10-25 companies).
    3. **Growth Accelerator:** PAT 5yr CAGR > 20%, Revenue 5yr CAGR > 15%, D/E < 2.0 (Expected: 8-20 companies).
    4. **Dividend Champion:** Dividend Yield > 2%, Dividend Payout Ratio < 80%, FCF > 0 (Expected: 10-20 companies).
    5. **Debt-Free Blue Chip:** D/E == 0 (borrowings = 0), ROE > 12%, Revenue > 5,000 Cr (Expected: 15-30 companies).
    6. **Turnaround Watch:** Revenue 3yr CAGR > 10%, FCF improving (positive in latest year), D/E declining (Expected: 5-15 companies).
  - Execute presets against the 92-company universe; verify candidate outputs make fundamental economic sense and fall within expected count boundaries.
- **Deliverable:** `screener_config.yaml` populated with 6 tested presets.

### **Day 17 (Oct 02): Multi-Dimensional Ranking Engine & Export (`screener_output.xlsx`)**
- **Core Objectives:**
  - Implement the multi-factor composite scoring engine based on spec weighting:
    - **Profitability (35%):** ROE (15%), ROCE (10%), Net Profit Margin (10%).
    - **Cash Quality (30%):** FCF 5yr CAGR (15%), CFO/PAT Ratio (10%), FCF > 0 flag (5%).
    - **Growth (20%):** Revenue 5yr CAGR (10%), PAT 5yr CAGR (10%).
    - **Leverage & Solvency (15%):** Debt-to-Equity score (10%), Interest Coverage score (5%).
  - Apply statistical Winsorisation at P10 / P90 percentiles to prevent extreme values from distorting rankings.
  - Implement sector-relative normalisation (ranking within `sectors.broad_sector`).
  - Build automated exporter to generate `screener_output.xlsx` (and CSV companion) displaying top-N ranked companies with 20+ KPIs, sector context, and score breakdowns.
- **Deliverable:** `screener_output.xlsx` & ranking module.

### **Day 18 (Oct 03): Peer Group Percentile Module (`src/analytics/peer.py`)**
- **Core Objectives:**
  - Ingest `peer_groups` table (11 peer groups, 56 company mappings).
  - Compute intra-group percentile ranks ($0.00$ to $1.00$) for 20 metrics using `scipy.stats.percentileofscore` or SQL `PERCENT_RANK() OVER (PARTITION BY peer_group_name ORDER BY metric)`.
  - Persist results into the SQLite table `peer_percentiles`: `(company_id, peer_group_name, metric, value, percentile_rank, year)`.
  - Implement classification flags:
    - **Best in Class:** Company in top quartile ($\ge 75$th percentile) for $\ge 6$ of 10 primary metrics.
    - **Watch List:** Company in bottom quartile ($\le 25$th percentile) for $\ge 4$ of 10 primary metrics.
  - Compute benchmark gap metrics relative to the group leader (e.g. TCS for IT Services, HDFCBANK for Private Banks).
- **Deliverable:** `src/analytics/peer.py` & `peer_percentiles` SQLite table.

### **Day 19 (Oct 04): Radar Chart Generation Suite (`reports/radar_charts/`)**
- **Core Objectives:**
  - Develop 8-axis radar visualization engine using Plotly (with Matplotlib fallback for static reporting).
  - Standardize the 8 comparative axes:
    1. Return on Equity (ROE)
    2. Return on Capital Employed (ROCE)
    3. Net Profit Margin (NPM)
    4. Debt-to-Equity (Inverted or Solvency Score)
    5. Free Cash Flow (FCF)
    6. PAT 5-Year CAGR
    7. Revenue 5-Year CAGR
    8. EPS 5-Year CAGR
  - Plot company percentile rank vs. peer group average and benchmark leader.
  - Batch-generate and verify 92 high-resolution radar PNGs in `reports/radar_charts/` named `<TICKER>_peer_radar.png`.
- **Deliverable:** `reports/radar_charts/` (92 PNG artifacts).

### **Day 20 (Oct 05): Peer Comparison Workbook Generator (`peer_comparison.xlsx`)**
- **Core Objectives:**
  - Create `peer_comparison.xlsx` using `openpyxl` with 11 dedicated sheets (one per peer group).
  - Display side-by-side matrices comparing member companies across 20 metrics, 5yr CAGRs, and Capital Allocation classifications.
  - Implement 3-tier conditional color formatting:
    - Green ($\ge 75$th percentile)
    - Yellow ($25$th to $75$th percentile)
    - Soft Red ($\le 25$th percentile)
  - Visually distinguish benchmark leaders and embed "Best in Class" / "Watch List" status indicators.
- **Deliverable:** `peer_comparison.xlsx`.

### **Day 21 (Oct 06-07): DQ Validation, Full Regression Suite & Retrospective**
- **Core Objectives:**
  - Execute automated tests covering all screener query paths, preset count thresholds, peer percentiles, and Excel exports.
  - Ensure 0 regressions across Sprint 1 ETL, Sprint 2 Ratio Engine, and Sprint 3 modules.
  - Verify code formatting with `black` and linting with `ruff` across all new modules.
  - Write detailed Sprint 3 retrospective in `reports/sprint3_retro.md`.
  - Tag release `sprint3-complete`.
- **Deliverables:** All tests green, `reports/sprint3_retro.md`.

---

## 3. Explicit Sprint 3 Deliverables Checklist

| # | Deliverable | Path / Artifact | Description |
|:---:|:---|:---|:---|
| 1 | Screener Query Engine | `src/screener/engine.py` | Vectorized screening engine supporting thresholding, boolean logic, and multi-year trend filters. |
| 2 | Screener Preset Config | `screener_config.yaml` | YAML configuration file defining the 6 screening templates and composite scoring parameters. |
| 3 | Screener Output Report | `screener_output.xlsx` | Excel workbook containing top-N ranked results across all 6 presets with 20+ KPIs and composite scores. |
| 4 | Peer Analytics Engine & DB Table | `src/analytics/peer.py` & `peer_percentiles` (DB) | Module calculating intra-group percentiles, benchmark gaps, and badges; stored in SQLite table. |
| 5 | Peer Radar Charts Suite | `reports/radar_charts/` (92 PNGs) | 92 high-resolution 8-axis radar charts comparing companies to their peer group averages. |
| 6 | Peer Comparison Workbook | `peer_comparison.xlsx` | Multi-tab Excel workbook (11 peer groups) with conditional percentile heatmaps and benchmark comparisons. |
| 7 | Sprint 3 Retrospective & Tests | `reports/sprint3_retro.md` & `tests/screener/` | Comprehensive retrospective document and 100% green test suite covering Modules 3 & 4. |

---

## 4. Exit Criteria for Sprint 3 Sign-Off

To achieve formal Sprint 3 sign-off, the following criteria must be met with 100% compliance:
1. **6 Presets Operational:** All 6 preset screeners execute without error and return candidate counts within spec ranges:
   - Quality Compounder: 15-35 companies
   - Value Pick: 10-25 companies
   - Growth Accelerator: 8-20 companies
   - Dividend Champion: 10-20 companies
   - Debt-Free Blue Chip: 15-30 companies
   - Turnaround Watch: 5-15 companies
2. **Peer Percentiles Complete:** `peer_percentiles` SQLite table populated for all 11 peer groups and 20 metrics, with 0 null percentiles for populated metrics.
3. **Peer Comparison Workbook Validated:** `peer_comparison.xlsx` generated with 11 sheets, correct column alignments, and valid conditional formatting rules.
4. **Radar Charts Generated:** Exactly 92 radar chart PNG files generated in `reports/radar_charts/`.
5. **Data Quality & Regression Tests:** Full pytest test suite (Sprint 1 ETL + Sprint 2 KPIs + Sprint 3 Screener/Peers) passes with zero errors and zero warnings.
6. **Code Standards:** 100% compliance with `black` formatting and `ruff` linting across all new modules.
7. **Documentation:** `reports/sprint3_retro.md` written and approved.

---

## 5. Upstream Data Dependencies from Sprints 1 & 2

Sprint 3 directly consumes database tables and modules established and verified in Sprints 1 & 2:
- **`financial_ratios` table (`db/nifty100.db`):** 1,155 annual rows $	imes$ 50 columns. Provides pre-computed profitability margins (NPM, OPM, ROE, ROCE, ROA), leverage ratios (D/E, ICR, Net Debt), growth rates (1Y, 3Y, 5Y, 10Y CAGRs for Revenue, PAT, EPS), and cash flow KPIs (FCF, CFO Quality Score, CapEx Intensity, Capital Allocation patterns).
- **`peer_groups` table (`db/nifty100.db`):** 11 distinct peer groups, 56 company mappings, and designated `is_benchmark` flags.
- **`companies` table (`db/nifty100.db`):** Master company universe (92 companies) for ticker validation, full legal names, and metadata.
- **`sectors` table (`db/nifty100.db`):** 11 broad sectors used for sector-relative ranking, benchmark normalization, and Financials sector carve-outs.
- **`market_cap` table (`db/nifty100.db`):** 552 rows (2019-2024) providing annual P/E, P/B, EV/EBITDA, and Dividend Yield multiples for valuation screens.

---

## 6. Inherited Constraints & Edge Cases from Sprint 2

Sprint 3 implementations must defensively account for known data characteristics established in Sprint 2:
1. **16 Banking-Template Companies:**
   - Banks do not report traditional Cost of Goods Sold, Gross Profit, or standard Borrowings/Debt-to-Equity.
   - ROCE, D/E, Working Capital, Gross Margin, and FCF Conversion are structurally `None`.
   - *Impact on Screener:* Screener filters on D/E or ROCE must not discard banks as "missing data"; instead, filters must either exclude Financials or evaluate sector-specific metrics (e.g. ROA, NIM).
2. **23 Financials Sector Companies:**
   - NBFCs (e.g. IRFC, RECLTD, PFC) structurally operate with high leverage (D/E 3-8x) and negative operating cash flows due to loan disbursements.
   - Handled in Sprint 2 with `high_leverage_flag = 0` exemption and `cfo_quality_score = None` ("Financials Sector Carve-Out").
   - *Impact on Screener:* Leverage and Cash Quality filters must respect the sector carve-out.
3. **Corrupted Source Scale Errors (BEL & HAL):**
   - Source data scaled equity capital and balance sheet values by ~100x.
   - Neutralized in Sprint 2: all BS-dependent ratios set to `None`, `extreme_magnitude_flag = 1`, and `data_quality_label = 'Unreliable BS Data (Scale Error ~100x)'`.
   - *Impact on Screener:* Screener must automatically filter out rows where `extreme_magnitude_flag == 1` from balance sheet screens.
4. **SBIN Cash Flow Reporting Gap:**
   - Source `cashflow.xlsx` lacks `operating_activity` for SBIN, resulting in `free_cash_flow_cr = None`.
   - *Impact on Screener:* SBIN must be treated as `None` for FCF screens rather than defaulting to 0 or failing.
5. **Exact-Year Gap CAGR Flags:**
   - Companies with non-contiguous reporting years (e.g. AMBUJACEM missing FY22, LODHA) or short histories (JIOFIN) have CAGR set to `None` with explicit flags (`INSUFFICIENT`, `TURNAROUND`, `DECLINE_TO_LOSS`, `BOTH_NEGATIVE`).
   - *Impact on Screener:* Screener CAGR filters must check that `cagr_flag` is clean (or handle `None` gracefully) rather than assuming all 92 companies have numeric 3yr/5yr CAGRs.
