# Bluestock MF Capstone (Day 2)

## Project overview
Bluestock MF Capstone builds a small **star schema in SQLite** to support quick analytics over mutual fund data:
- `dim_fund`, `dim_category`
- `fact_nav`
- `fact_transactions` (investor transactions)
- `fact_performance` (scheme performance snapshot)

This repository’s ETL runs in Python and produces cleaned CSVs + a SQLite database for SQL exploration.

## Architecture
- **Raw datasets** live under `data/raw/datasets/`
- **Processed (cleaned) outputs** are written to `data/processed/`
- **SQLite database** is created at `data/db/bluestock_mf.db`
- **Schema** is defined in `sql/schema.sql`
- **ETL (Day 2)** is implemented in `scripts/day2_build_sqlite.py`

## Datasets used (Day 2)
- `07_scheme_performance.csv`
- `08_investor_transactions.csv`
- `fund_master.csv` (from `data/raw/master/`)
- NAV history CSVs (from `data/raw/nav_history/`)

## ETL pipeline (Day 2)
`scripts/day2_build_sqlite.py` performs:
1. Clean `fund_master` → load into `dim_fund` and `dim_category`
2. Clean/merge NAV history → load into `fact_nav`
3. Clean investor transactions → write `data/processed/clean_transactions.csv` → load into `fact_transactions`
4. Clean scheme performance → write `data/processed/clean_performance.csv` → load into `fact_performance`
5. Create SQLite schema from `sql/schema.sql`

### Fact table schemas
- `fact_transactions`:
  - one row per investor transaction
  - columns: `transaction_id`, `investor_id`, `scheme_code`, `date`, `amount_inr`, `transaction_type`, `kyc_status`, `payment_mode`
- `fact_performance`:
  - one row per scheme (snapshot)
  - columns: returns/benchmark, alpha/beta/sharpe/sortino, risk/stats, `computed_on`

## Schema diagram (logical)
```
            +------------------+
            |     dim_fund     |
            | scheme_code (PK)|
            +---------+--------+
                      |
                      | scheme_code
                      |
+---------------------v---------------------+
|                   facts                  |
|                                           |
|  fact_nav (scheme_code, date, nav, ...) |
|  fact_performance (scheme_code, ...)    |
|  fact_transactions (transaction_id, ...) |
+-------------------------------------------+
```

## Sample SQL queries
SQL lives in `sql/queries.sql`.
Run queries by opening the file in an SQLite client or via Python.

## How to run Day 2
```bash
python bluestock_mf_capstone/scripts/day2_build_sqlite.py
```

## Outputs
- `data/processed/clean_transactions.csv`
- `data/processed/clean_performance.csv`
- `data/db/bluestock_mf.db`

## Notes
- Day 2 refreshes the SQLite DB each run to keep schema/data aligned.

