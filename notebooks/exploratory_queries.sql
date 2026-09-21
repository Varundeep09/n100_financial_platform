-- ============================================================================
-- N100 FINANCIAL INTELLIGENCE PLATFORM — EXPLORATORY SQL QUERIES (DAY 7)
-- Database: db/nifty100.db (SQLite 3.x)
-- ============================================================================

-- 1. Row counts across all 10 platform tables
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'market_cap', COUNT(*) FROM market_cap;

-- 2. Null counts for critical columns across primary tables
SELECT 'companies' AS tbl, 'company_name' AS col, SUM(CASE WHEN company_name IS NULL THEN 1 ELSE 0 END) AS nulls FROM companies
UNION ALL SELECT 'profitandloss', 'sales', SUM(CASE WHEN sales IS NULL THEN 1 ELSE 0 END) FROM profitandloss
UNION ALL SELECT 'profitandloss', 'net_profit', SUM(CASE WHEN net_profit IS NULL THEN 1 ELSE 0 END) FROM profitandloss
UNION ALL SELECT 'balancesheet', 'total_assets', SUM(CASE WHEN total_assets IS NULL THEN 1 ELSE 0 END) FROM balancesheet
UNION ALL SELECT 'cashflow', 'net_cash_flow', SUM(CASE WHEN net_cash_flow IS NULL THEN 1 ELSE 0 END) FROM cashflow
UNION ALL SELECT 'sectors', 'broad_sector', SUM(CASE WHEN broad_sector IS NULL THEN 1 ELSE 0 END) FROM sectors;

-- 3. Fiscal year annual coverage distribution per company
SELECT pl_count AS annual_years_coverage, COUNT(*) AS company_count
FROM (
    SELECT company_id, COUNT(DISTINCT year) AS pl_count
    FROM profitandloss
    GROUP BY company_id
)
GROUP BY pl_count
ORDER BY pl_count DESC;

-- 4. Companies with short history (< 5 years coverage per DQ-16)
SELECT c.id, c.company_name,
       COUNT(DISTINCT pl.year) AS pl_years,
       COUNT(DISTINCT bs.year) AS bs_years,
       COUNT(DISTINCT cf.year) AS cf_years,
       CASE 
         WHEN c.id = 'JIOFIN' THEN 'Recent IPO (Aug 2023 demerger from RIL)'
         WHEN c.id = 'SBIN' THEN 'Known raw Balance Sheet source gap'
         ELSE 'Normal'
       END AS explanation
FROM companies c
LEFT JOIN profitandloss pl ON c.id = pl.company_id
LEFT JOIN balancesheet bs ON c.id = bs.company_id
LEFT JOIN cashflow cf ON c.id = cf.company_id
GROUP BY c.id, c.company_name
HAVING pl_years < 5 OR bs_years < 5 OR cf_years < 5;

-- 5. Top 10 companies by latest annual revenue (FY24 / 2024-03)
SELECT pl.company_id, c.company_name, s.broad_sector, pl.sales AS sales_crore
FROM profitandloss pl
JOIN companies c ON pl.company_id = c.id
LEFT JOIN sectors s ON pl.company_id = s.company_id
WHERE pl.year = '2024-03'
ORDER BY pl.sales DESC
LIMIT 10;

-- 6. Sector composition & aggregated index weight
SELECT COALESCE(s.broad_sector, 'Unclassified') AS broad_sector,
       COUNT(c.id) AS company_count,
       ROUND(SUM(COALESCE(s.index_weight_pct, 0)), 2) AS total_index_weight
FROM companies c
LEFT JOIN sectors s ON c.id = s.company_id
GROUP BY s.broad_sector
ORDER BY company_count DESC;

-- 7. Unprofitable companies in latest fiscal year (2024-03)
SELECT pl.company_id, c.company_name, pl.sales, pl.operating_profit, pl.net_profit
FROM profitandloss pl
JOIN companies c ON pl.company_id = c.id
WHERE pl.year = '2024-03' AND pl.net_profit < 0
ORDER BY pl.net_profit ASC;

-- 8. Average operating profit margin (OPM %) by sector in FY24
SELECT COALESCE(s.broad_sector, 'Unclassified') AS broad_sector,
       COUNT(pl.company_id) AS sample_count,
       ROUND(AVG(pl.opm_percentage), 2) AS avg_opm_pct,
       ROUND(MIN(pl.opm_percentage), 2) AS min_opm_pct,
       ROUND(MAX(pl.opm_percentage), 2) AS max_opm_pct
FROM profitandloss pl
LEFT JOIN sectors s ON pl.company_id = s.company_id
WHERE pl.year = '2024-03'
GROUP BY s.broad_sector
ORDER BY avg_opm_pct DESC;

-- 9. Verification of zero duplicate annual records (DQ-02 integrity check)
SELECT 'profitandloss' AS tbl, company_id, year, COUNT(*) AS dup_count
FROM profitandloss GROUP BY company_id, year HAVING COUNT(*) > 1
UNION ALL
SELECT 'balancesheet', company_id, year, COUNT(*)
FROM balancesheet GROUP BY company_id, year HAVING COUNT(*) > 1
UNION ALL
SELECT 'cashflow', company_id, year, COUNT(*)
FROM cashflow GROUP BY company_id, year HAVING COUNT(*) > 1;

-- 10. Demonstration of '%-03' annual filter rule for Balance Sheet joins
SELECT 'All Balance Sheet Rows' AS filter_state, COUNT(*) AS total_rows, COUNT(DISTINCT company_id) AS companies FROM balancesheet
UNION ALL
SELECT 'Annual FY-End Only (year LIKE %-03)', COUNT(*), COUNT(DISTINCT company_id) FROM balancesheet WHERE year LIKE '%-03'
UNION ALL
SELECT 'Interim H1 Only (year LIKE %-09)', COUNT(*), COUNT(DISTINCT company_id) FROM balancesheet WHERE year LIKE '%-09';
