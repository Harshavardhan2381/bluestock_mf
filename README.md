# bluestock_mf_capstone

Day 1 — Project Setup + Data Ingestion (ETL)

## Folder structure

```text
bluestock_mf_capstone/
├── data/
│   ├── raw/
│   │   ├── datasets/          # place the 10 provided CSV datasets here
│   │   ├── latest_nav/
│   │   ├── nav_history/
│   │   └── master/
│   ├── processed/
│   └── db/
├── notebooks/
├── scripts/
│   ├── etl_pipeline.py
│   └── live_nav_fetch.py
├── sql/
│   └── schema.sql
├── dashboard/
└── reports/
```

## Setup

```bash
pip install -r requirements.txt
```

## Run Day 1 ETL

```bash
python data_ingestion.py
```

This will:
- Scan `data/raw/datasets/*.csv` and print `shape`, `dtypes`, and `head()` per file (if any exist)
- Fetch `fund_master.csv` via MFAPI (paginated)
- Fetch NAV history for the 6 key schemes and save raw CSVs into `data/raw/nav_history/`
- Validate AMFI codes (Option A): validate only those 6 scheme codes exist in `fund_master.csv`

## Notes
- If there are currently no CSV datasets in `data/raw/datasets/`, the script will continue and only run the MFAPI ingestion steps.
