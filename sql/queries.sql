-- =============================
-- bluestock_mf_capstone queries
-- Required + additional warehouse analytics queries
-- =============================

-- 1) Top 5 funds by AUM (latest report date)
WITH latest AS (
  SELECT MAX(report_date) AS max_date FROM fact_aum
)
SELECT
  fund_house,
  SUM(aum_crore) AS total_aum_crore
FROM fact_aum
WHERE report_date = (SELECT max_date FROM latest)
GROUP BY fund_house
ORDER BY total_aum_crore DESC
LIMIT 5;

-- 2) Average NAV per month
SELECT
  strftime('%Y-%m', date) AS year_month,
  AVG(nav) AS avg_nav
FROM fact_nav
GROUP BY year_month
ORDER BY year_month;

-- 3) SIP inflow YoY growth (uses stored yoy_growth_pct when present)
SELECT
  month,
  sip_inflow_crore,
  yoy_growth_pct AS sip_inflow_yoy_growth_pct
FROM fact_sip_inflows
ORDER BY month
LIMIT 24;

-- 4) Transactions by state
SELECT
  (kyc_status) AS state,
  SUM(amount_inr) AS total_amount_inr,
  COUNT(*) AS transaction_count
FROM fact_transactions
GROUP BY state
ORDER BY total_amount_inr DESC
LIMIT 20;

-- 5) Funds with expense_ratio < 1%
SELECT
  d.scheme_name,
  f.expense_ratio_pct
FROM fact_performance f
JOIN dim_fund d
  ON f.scheme_code = d.scheme_code
WHERE f.expense_ratio_pct < 1
ORDER BY f.expense_ratio_pct ASC
LIMIT 25;

-- 6) Top categories by inflow (latest report date)
WITH latest AS (
  SELECT MAX(report_date) AS max_date FROM fact_aum
)
SELECT
  category,
  SUM(aum_crore) AS total_inflow_crore
FROM fact_aum
WHERE report_date = (SELECT max_date FROM latest)
GROUP BY category
ORDER BY total_inflow_crore DESC
LIMIT 10;

-- 7) Highest Sharpe ratio funds
SELECT
  d.scheme_name,
  f.sharpe_ratio
FROM fact_performance f
JOIN dim_fund d
  ON f.scheme_code = d.scheme_code
WHERE f.sharpe_ratio IS NOT NULL
ORDER BY f.sharpe_ratio DESC
LIMIT 10;

-- 8) Monthly transaction trends
SELECT
  strftime('%Y-%m', date) AS year_month,
  transaction_type,
  SUM(amount_inr) AS total_amount_inr
FROM fact_transactions
GROUP BY year_month, transaction_type
ORDER BY year_month, total_amount_inr DESC;

-- 9) Benchmark vs fund return comparison (latest snapshot)
SELECT
  d.scheme_name,
  f.return_3yr_pct AS fund_return_3yr_pct,
  f.benchmark_3yr_pct AS benchmark_return_3yr_pct,
  (f.return_3yr_pct - f.benchmark_3yr_pct) AS excess_return_3yr_pct
FROM fact_performance f
JOIN dim_fund d
  ON f.scheme_code = d.scheme_code
ORDER BY excess_return_3yr_pct DESC
LIMIT 10;

-- 10) Top funds by redemption volume (from transactions)
SELECT
  d.scheme_name,
  SUM(CASE WHEN lower(transaction_type) LIKE 'redemption%' THEN amount_inr ELSE 0 END) AS redemption_amount_inr
FROM fact_transactions t
JOIN dim_fund d
  ON t.scheme_code = d.scheme_code
GROUP BY d.scheme_name
HAVING redemption_amount_inr > 0
ORDER BY redemption_amount_inr DESC
LIMIT 10;





