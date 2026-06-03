-- SQLite star-schema for NAV analytics

PRAGMA foreign_keys=OFF;

DROP TABLE IF EXISTS dim_category;
DROP TABLE IF EXISTS dim_fund;
DROP TABLE IF EXISTS fact_performance;
DROP TABLE IF EXISTS fact_transactions;
DROP TABLE IF EXISTS fact_nav;
DROP TABLE IF EXISTS fact_aum;
DROP TABLE IF EXISTS dim_date;


-- dim_fund: descriptive attributes
CREATE TABLE IF NOT EXISTS dim_fund (
  scheme_code INTEGER PRIMARY KEY,
  scheme_name TEXT,
  fund_house TEXT,
  scheme_category TEXT,
  raw_json TEXT
);

-- dim_category: category lookup (one row per scheme)
CREATE TABLE IF NOT EXISTS dim_category (
  scheme_code INTEGER,
  scheme_category TEXT
);

-- fact_nav: one row per scheme per NAV date
CREATE TABLE IF NOT EXISTS fact_nav (
  scheme_code INTEGER,
  date TEXT,
  nav REAL,
  fund_house TEXT,
  scheme_category TEXT,
  scheme_name TEXT
);

CREATE INDEX IF NOT EXISTS idx_nav_scheme_date
ON fact_nav(scheme_code, date);


-- fact_transactions: one row per investor transaction
CREATE TABLE IF NOT EXISTS fact_transactions (
  transaction_id TEXT PRIMARY KEY,
  investor_id TEXT,
  scheme_code INTEGER,
  date TEXT,
  amount_inr REAL,
  transaction_type TEXT,
  kyc_status TEXT,
  payment_mode TEXT
);

CREATE INDEX IF NOT EXISTS idx_txn_scheme
ON fact_transactions(scheme_code);


-- fact_aum: aggregated AUM snapshot by fund house + category
CREATE TABLE IF NOT EXISTS fact_aum (
  fund_house TEXT,
  category TEXT,
  aum_crore REAL,
  report_date DATE
);

CREATE INDEX IF NOT EXISTS idx_aum_house_date
ON fact_aum(fund_house, report_date);

-- dim_date: calendar dimension
CREATE TABLE IF NOT EXISTS dim_date (
  date_key DATE PRIMARY KEY,
  year INTEGER,
  month INTEGER,
  quarter INTEGER,
  weekday TEXT
);

-- fact_performance: one row per scheme (latest snapshot from 07_scheme_performance)

CREATE TABLE IF NOT EXISTS fact_performance (
  scheme_code INTEGER PRIMARY KEY,
  return_1yr_pct REAL,
  return_3yr_pct REAL,
  return_5yr_pct REAL,
  benchmark_3yr_pct REAL,
  alpha REAL,
  beta REAL,
  sharpe_ratio REAL,
  sortino_ratio REAL,
  std_dev_ann_pct REAL,
  max_drawdown_pct REAL,
  aum_crore REAL,
  expense_ratio_pct REAL,
  morningstar_rating INTEGER,
  risk_grade TEXT,
  computed_on TEXT
);




