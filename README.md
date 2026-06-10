# Bluestock MF Capstone

## Project Overview
Bluestock MF Capstone analyzes mutual fund transaction and holdings data to produce risk and investor-behavior insights (VaR/CVaR, rolling Sharpe, cohorts, SIP continuity, recommendations, and sector concentration via HHI). Outputs are written to `data/processed/` and visualizations to `reports/charts/`.

## Folder Structure
- `data/`
  - `processed/` — cleaned and computed CSVs used by analytics scripts
- `scripts/`
  - Day-based ETL/analytics scripts (Python)
- `notebooks/`
  - Jupyter notebooks for reporting
- `reports/`
  - `charts/` — PNG outputs used in notebooks and final report
- `run_pipeline.py`
  - Master runner to execute key pipeline steps

## Installation
From project root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## How to Run ETL
Run the day-based scripts that generate cleaned datasets (e.g., day4/day5/day6 depending on your workflow).

## How to Run Analytics
Typical Day 6 analytics run:

```bash
.venv/bin/python3 scripts/day6_cohort_analysis.py
.venv/bin/python3 scripts/day6_sip_continuity.py
.venv/bin/python3 scripts/day6_sector_hhi.py
.venv/bin/python3 scripts/day6_advanced_analytics.py
```

Recommendation:

```bash
.venv/bin/python3 scripts/recommender.py
```

## Dashboard Information
Power BI / Tableau assets (if used) live alongside the project. Refer to the project deliverables for publishing steps.

## Results & Findings
Outputs created during Day 6:
- `data/processed/var_cvar_report.csv`
- `data/processed/cohort_analysis.csv`
- `data/processed/sip_continuity.csv`
- `data/processed/sector_hhi.csv`
- `reports/charts/rolling_sharpe_chart.png`
- `reports/charts/sector_hhi.png`
- `notebooks/Advanced_Analytics.ipynb`

Key limitations:
- Low-risk recommendations may be empty if the low-risk schemes are not present in the Sharpe-return universe (`sharpe_values.csv`).

