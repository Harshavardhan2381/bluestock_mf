- [x] Inspect repo for data_ingestion.py
- [x] Replace corrupted data_ingestion.py with clean version (syntax error fix)
- [x] Create/activate venv and install requirements (pip install -r requirements.txt)
- [x] Update data_ingestion.py to call scripts/live_nav_fetch.py pipeline after dataset validation
- [x] Run data_ingestion.py and confirm MFAPI ingestion messages/output
- [x] Verify output files in data/raw/master and data/raw/nav_history

- [ ] Day 2: Update SQL schema (sql/schema.sql)
- [x] Day 2: Build cleaned/merged outputs + load SQLite
      - data/processed/nav_history_combined.csv
      - data/db/bluestock_mf.db
- [x] Day 2: Create notebook notebooks/02_data_cleaning.ipynb
- [x] Day 2: Run a quick verification (row counts, schema sanity)
- [ ] Day 2: git add/commit/push


