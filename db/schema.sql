-- N100 Financial Intelligence Platform - Database Schema (SQLite 3.x)
-- 10 Core & Supporting Tables per Project Specification

PRAGMA foreign_keys = ON;

-- 1. companies (Master Company Reference)
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR(20) PRIMARY KEY,
    company_logo TEXT,
    company_name VARCHAR(255) NOT NULL,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value NUMERIC,
    book_value NUMERIC,
    roce_percentage NUMERIC,
    roe_percentage NUMERIC
);

-- 2. profitandloss (Annual Profit & Loss Statements)
CREATE TABLE IF NOT EXISTS profitandloss (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(20) NOT NULL,
    year VARCHAR(10) NOT NULL,
    sales NUMERIC,
    expenses NUMERIC,
    operating_profit NUMERIC,
    opm_percentage NUMERIC,
    other_income NUMERIC,
    interest NUMERIC,
    depreciation NUMERIC,
    profit_before_tax NUMERIC,
    tax_percentage NUMERIC,
    net_profit NUMERIC,
    eps NUMERIC,
    dividend_payout NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (company_id, year)
);

-- 3. balancesheet (Annual Balance Sheet Statements)
CREATE TABLE IF NOT EXISTS balancesheet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(20) NOT NULL,
    year VARCHAR(10) NOT NULL,
    equity_capital NUMERIC,
    reserves NUMERIC,
    borrowings NUMERIC,
    other_liabilities NUMERIC,
    total_liabilities NUMERIC,
    fixed_assets NUMERIC,
    cwip NUMERIC,
    investments NUMERIC,
    other_asset NUMERIC,
    total_assets NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (company_id, year)
);

-- 4. cashflow (Annual Cash Flow Statements)
CREATE TABLE IF NOT EXISTS cashflow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(20) NOT NULL,
    year VARCHAR(10) NOT NULL,
    operating_activity NUMERIC,
    investing_activity NUMERIC,
    financing_activity NUMERIC,
    net_cash_flow NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (company_id, year)
);

-- 5. analysis (Multi-period Growth Analysis & Qualitative Comments)
CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(20) NOT NULL,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- 6. documents (Corporate Filings & Annual Report Links)
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(20) NOT NULL,
    year VARCHAR(10) NOT NULL,
    annual_report TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- 7. prosandcons (Automated Pros & Cons Text Summaries)
CREATE TABLE IF NOT EXISTS prosandcons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(20) NOT NULL,
    pros TEXT,
    cons TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- 8. sectors (Sector Classification & Index Weightings)
CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(20) NOT NULL UNIQUE,
    broad_sector VARCHAR(100),
    sub_sector VARCHAR(100),
    index_weight_pct NUMERIC,
    market_cap_category VARCHAR(50),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- 9. stock_prices (Monthly Stock Price History)
CREATE TABLE IF NOT EXISTS stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(20) NOT NULL,
    date VARCHAR(20) NOT NULL,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    volume INTEGER,
    adjusted_close NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (company_id, date)
);

-- 10. market_cap (Annual Market Cap & Valuation Multiples)
CREATE TABLE IF NOT EXISTS market_cap (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id VARCHAR(20) NOT NULL,
    year VARCHAR(10) NOT NULL,
    market_cap_crore NUMERIC,
    enterprise_value_crore NUMERIC,
    pe_ratio NUMERIC,
    pb_ratio NUMERIC,
    ev_ebitda NUMERIC,
    dividend_yield_pct NUMERIC,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (company_id, year)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_pl_company_year ON profitandloss(company_id, year);
CREATE INDEX IF NOT EXISTS idx_bs_company_year ON balancesheet(company_id, year);
CREATE INDEX IF NOT EXISTS idx_cf_company_year ON cashflow(company_id, year);
CREATE INDEX IF NOT EXISTS idx_docs_company_year ON documents(company_id, year);
CREATE INDEX IF NOT EXISTS idx_prices_company_date ON stock_prices(company_id, date);
CREATE INDEX IF NOT EXISTS idx_mcap_company_year ON market_cap(company_id, year);
CREATE INDEX IF NOT EXISTS idx_sectors_broad ON sectors(broad_sector);
