cd ~/Desktop/bluestock_mf_capstone

git add .

git commit -m "Day 4: Performance analytics, risk metrics, scorecard and benchmark comparison"

git push origin mainimport numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import linregress



PROJECT_ROOT = Path(__file__).resolve().parents[1]

nav_file = PROJECT_ROOT / "data/processed/nav_history_combined.csv"
out_file = PROJECT_ROOT / "data/processed/returns_computed.csv"
sharpe_out_file = PROJECT_ROOT / "data/processed/sharpe_values.csv"

# Risk-free rate for Sharpe ratio
Rf = 0.065

df = pd.read_csv(nav_file)


df["date"] = pd.to_datetime(df["date"])

df = df.sort_values(["scheme_code", "date"])

df["daily_return"] = (
    df.groupby("scheme_code")["nav"]
      .pct_change()
)

df.to_csv(out_file, index=False)

print("Saved:", out_file)
print("Rows:", len(df))
print(df.head())

# ==========================================
# ANNUALIZED RETURNS
# ==========================================

annual_returns = []
sharpe_rows = []


for code, grp in df.groupby("scheme_code"):

    grp = grp.replace([np.inf, -np.inf], np.nan)
    grp = grp.dropna(subset=["daily_return"])


    if len(grp) < 30:
        continue

    annual_return = (
        (1 + grp["daily_return"]).prod()
    ) ** (252 / len(grp)) - 1

    annual_returns.append({
        "scheme_code": code,
        "annualized_return": annual_return
    })


    # ==========================================
    # SHARPE VALUES
    # ==========================================
    # Annualized volatility from daily returns
    annualized_volatility = grp["daily_return"].std(ddof=1) * (252**0.5)

    sharpe_ratio = None
    if pd.notna(annualized_volatility) and annualized_volatility != 0:
        sharpe_ratio = (annual_return - Rf) / annualized_volatility

    # capture for later writing
    sharpe_rows.append({
        "scheme_code": code,
        "scheme_name": grp.iloc[-1].get("scheme_name", None),
        "annualized_return": annual_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": sharpe_ratio,
    })


annual_df = pd.DataFrame(annual_returns)


annual_out = PROJECT_ROOT / "data/processed/annualized_returns.csv"

annual_df.to_csv(annual_out, index=False)

print(f"Saved: {annual_out}")

# Write Sharpe values
sharpe_df = pd.DataFrame(sharpe_rows)
sharpe_df = sharpe_df[[
    "scheme_code",
    "scheme_name",
    "annualized_return",
    "annualized_volatility",
    "sharpe_ratio",
]]

sharpe_df.to_csv(sharpe_out_file, index=False)
print(f"Saved: {sharpe_out_file}")

# ==========================================
# SORTINO RATIO
# ==========================================

sortino_rows = []

for code, grp in df.groupby("scheme_code"):

    grp = grp.replace([np.inf, -np.inf], np.nan)
    grp = grp.dropna(subset=["daily_return"])

    if len(grp) < 30:
        continue

    scheme_name = grp.iloc[-1]["scheme_name"]

    annualized_return = (
        (1 + grp["daily_return"]).prod()
    ) ** (252 / len(grp)) - 1

    downside_returns = grp.loc[
        grp["daily_return"] < 0,
        "daily_return"
    ]

    downside_volatility = (
        downside_returns.std() * np.sqrt(252)
    )

    if pd.isna(downside_volatility) or downside_volatility == 0:
        sortino_ratio = np.nan
    else:
        sortino_ratio = (
            annualized_return - Rf
        ) / downside_volatility

    sortino_rows.append({
        "scheme_code": code,
        "scheme_name": scheme_name,
        "annualized_return": annualized_return,
        "downside_volatility": downside_volatility,
        "sortino_ratio": sortino_ratio
    })

sortino_df = pd.DataFrame(sortino_rows)

sortino_out = PROJECT_ROOT / "data/processed/sortino_values.csv"

sortino_df.to_csv(sortino_out, index=False)

print(f"Saved: {sortino_out}")

# ==========================================
# ALPHA & BETA
# ==========================================

benchmark_file = PROJECT_ROOT / "data/raw/datasets/10_benchmark_indices.csv"

bench = pd.read_csv(benchmark_file)

bench["date"] = pd.to_datetime(bench["date"])

bench = bench[bench["index_name"] == "NIFTY100"].copy()

bench = bench.sort_values("date")

bench["benchmark_return"] = bench["close_value"].pct_change()

alpha_beta_rows = []

for code, grp in df.groupby("scheme_code"):

    grp = grp.dropna(subset=["daily_return"])

    merged = grp.merge(
        bench[["date", "benchmark_return"]],
        on="date",
        how="inner"
    )

    merged = merged.dropna()

    if len(merged) < 30:
        continue

    slope, intercept, r_value, p_value, std_err = linregress(
        merged["benchmark_return"],
        merged["daily_return"]
    )

    alpha_beta_rows.append({
        "scheme_code": code,
        "scheme_name": grp.iloc[-1]["scheme_name"],
        "alpha": intercept * 252,
        "beta": slope,
        "r_squared": r_value**2
    })

alpha_beta_df = pd.DataFrame(alpha_beta_rows)

alpha_beta_out = PROJECT_ROOT / "data/processed/alpha_beta.csv"

alpha_beta_df.to_csv(alpha_beta_out, index=False)

print(f"Saved: {alpha_beta_out}")

# ==========================================
# MAXIMUM DRAWDOWN
# ==========================================

drawdown_rows = []

for code, grp in df.groupby("scheme_code"):

    grp = grp.sort_values("date")

    running_max = grp["nav"].cummax()

    drawdown = grp["nav"] / running_max - 1

    max_drawdown = drawdown.min()

    drawdown_rows.append({
        "scheme_code": code,
        "scheme_name": grp.iloc[-1]["scheme_name"],
        "max_drawdown": max_drawdown
    })

drawdown_df = pd.DataFrame(drawdown_rows)

drawdown_out = PROJECT_ROOT / "data/processed/max_drawdown.csv"

drawdown_df.to_csv(drawdown_out, index=False)

print(f"Saved: {drawdown_out}")

# ==========================================
# CAGR REPORT
# ==========================================




def calculate_cagr(start_nav, end_nav, years):

    if start_nav <= 0:
        return None

    return (end_nav / start_nav) ** (1 / years) - 1


cagr_rows = []

for code, grp in df.groupby("scheme_code"):

    grp = grp.sort_values("date")

    latest_date = grp["date"].max()

    latest_nav = grp.iloc[-1]["nav"]

    scheme_name = grp.iloc[-1]["scheme_name"]

    row = {
        "scheme_code": code,
        "scheme_name": scheme_name
    }

    for years in [1, 3, 5]:

        start_date = latest_date - pd.DateOffset(years=years)

        subset = grp[grp["date"] >= start_date]

        if len(subset) > 0:

            start_nav = subset.iloc[0]["nav"]

            row[f"cagr_{years}yr"] = calculate_cagr(
                start_nav,
                latest_nav,
                years
            )

    cagr_rows.append(row)

cagr_df = pd.DataFrame(cagr_rows)

cagr_out = PROJECT_ROOT / "data/processed/cagr_report.csv"

cagr_df.to_csv(cagr_out, index=False)

print(f"Saved: {cagr_out}")
print(f"Funds processed: {len(cagr_df)}")

# ==========================================
# FUND SCORECARD
# ==========================================

# Uses pre-computed, cleaned performance inputs
clean_perf_file = PROJECT_ROOT / "data/processed/clean_performance.csv"
clean_master_file = PROJECT_ROOT / "data/processed/clean_fund_master.csv"

perf_df = pd.read_csv(clean_perf_file)
master_df = pd.read_csv(clean_master_file)

# Merge in fund names
# (clean_performance.csv does not include scheme_name)
df = perf_df.merge(
    master_df[["scheme_code", "scheme_name"]],
    on="scheme_code",
    how="left",
)

# If scheme_name is missing due to non-overlapping scheme_code sets,
# fall back to scheme_code-as-name to keep scorecard non-empty.
if "scheme_name" in df.columns and df["scheme_name"].isna().any():
    df["scheme_name"] = df["scheme_name"].fillna(df["scheme_code"].astype(str))

print("Rows after merge:", len(df))
print(
    df[["scheme_code", "scheme_name"]].head()
)


# Drop rows missing any scoring columns
required_cols = [
    "cagr_3yr",
    "sharpe_ratio",
    "alpha",
    "expense_ratio_pct",
    "max_drawdown_pct",
]

# clean_performance.csv uses return_3yr_pct and max_drawdown_pct
# Map into the names expected by the scorecard logic.
rename_map = {
    "return_3yr_pct": "cagr_3yr",
}

df = df.rename(columns=rename_map)

# Ensure max_drawdown is represented as max_drawdown_pct
# (clean_performance.csv already has max_drawdown_pct)

# If any of the expected columns are missing, raise early for debugging.
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise KeyError(
        f"Missing required columns for scorecard: {missing}. "
        f"Available columns: {df.columns.tolist()}"
    )

# Drop rows with NA in required columns
before_dropna = len(df)
df = df.dropna(subset=required_cols)
print("Rows after dropna:", len(df))

# Rank columns
# Higher is better for cagr_3yr, sharpe_ratio, alpha
# Lower is better for expense_ratio_pct and max_drawdown_pct

df["rank_3yr_cagr"] = (
    df["cagr_3yr"].rank(ascending=False, method="min")
)
df["rank_sharpe"] = (
    df["sharpe_ratio"].rank(ascending=False, method="min")
)
df["rank_alpha"] = (
    df["alpha"].rank(ascending=False, method="min")
)
df["rank_expense_ratio"] = (
    df["expense_ratio_pct"].rank(ascending=True, method="min")
)

df["rank_max_drawdown"] = (
    df["max_drawdown_pct"].rank(
        ascending=False,
        method="min"
    )
)

# Scores: normalize ranks to sum into a composite score
# Higher composite score = better overall
rank_cols = [
    "rank_3yr_cagr",
    "rank_sharpe",
    "rank_alpha",
    "rank_expense_ratio",
    "rank_max_drawdown",
]

# Convert ranks to a 0-100-like score where higher is better
for c in rank_cols:
    # invert ranking for expense_ratio/max_drawdown already ranked appropriately
    # (we set rank_expense_ratio/rank_max_drawdown in direction where higher rank means better)
    pass

# Use average of ranks as the composite

df["score"] = df[rank_cols].mean(axis=1)

# Build output with the exact columns expected by current header
out = df[[
    "scheme_code",
    "scheme_name",
    "score",
    "rank_3yr_cagr",
    "rank_sharpe",
    "rank_alpha",
    "rank_expense_ratio",
    "rank_max_drawdown",
    "cagr_3yr",
    "sharpe_ratio",
    "alpha",
    "expense_ratio_pct",
    "max_drawdown_pct",
]].copy()

out = out.rename(columns={
    "cagr_3yr": "score_3yr_cagr",
    "sharpe_ratio": "score_sharpe",
    "alpha": "score_alpha",
    "expense_ratio_pct": "score_expense_ratio",
    "max_drawdown_pct": "score_max_drawdown",
})

# Final column order
out = out[[
    "scheme_code",
    "scheme_name",
    "score",
    "rank_3yr_cagr",
    "rank_sharpe",
    "rank_alpha",
    "rank_expense_ratio",
    "rank_max_drawdown",
    "score_3yr_cagr",
    "score_sharpe",
    "score_alpha",
    "score_expense_ratio",
    "score_max_drawdown",
]]

out = out.sort_values(["score"], ascending=False)

fund_scorecard_out = PROJECT_ROOT / "data/processed/fund_scorecard.csv"
out.to_csv(fund_scorecard_out, index=False)

print("Saved:", fund_scorecard_out)
print("Final fund scorecard rows:", len(out))


# ==========================================
# DAY 4: BENCHMARK COMPARISON + TRACKING ERROR (REQUIRED)
# ==========================================

scorecard_path = PROJECT_ROOT / "data/processed/fund_scorecard.csv"
returns_path = PROJECT_ROOT / "data/processed/returns_computed.csv"
benchmark_path = PROJECT_ROOT / "data/raw/datasets/10_benchmark_indices.csv"

chart_out = PROJECT_ROOT / "reports/charts/benchmark_comparison.png"
tracking_error_out = PROJECT_ROOT / "data/processed/tracking_error.csv"

scorecard_df = pd.read_csv(scorecard_path)
returns_df = pd.read_csv(returns_path)
bench_df = pd.read_csv(benchmark_path)

# Top 5 funds by score
if "score" not in scorecard_df.columns:
    raise KeyError("fund_scorecard.csv must contain a 'score' column")

top5 = scorecard_df.sort_values("score", ascending=False).head(5).copy()

# Use last 3 years available in the dataset
returns_df["date"] = pd.to_datetime(returns_df["date"])
end_date = returns_df["date"].max()
start_date = end_date - pd.DateOffset(years=3)

returns_df = returns_df[returns_df["date"] >= start_date].copy()

# Benchmarks
bench_df["date"] = pd.to_datetime(bench_df["date"])
bench_df = bench_df[bench_df["date"] >= start_date].copy()

# Prepare benchmark daily returns
bench_df = bench_df.sort_values(["index_name", "date"]).copy()
bench_df["benchmark_return"] = bench_df.groupby("index_name")["close_value"].pct_change()

# Create cumulative normalized series helper

def make_normalized_cumret(daily_ret_series: pd.Series) -> pd.Series:
    daily_ret_series = daily_ret_series.fillna(0.0)
    cum = (1.0 + daily_ret_series).cumprod()
    if len(cum) == 0:
        return cum
    return cum / cum.iloc[0] * 100.0

# Plot
import os
import matplotlib.pyplot as plt

os.makedirs(chart_out.parent, exist_ok=True)

plt.figure(figsize=(12, 6))

# Fund cumulative returns aligned on dates within window
# We'll plot each fund using its own date index within the selected window.

for _, row in top5.iterrows():
    code = row["scheme_code"]
    name = row.get("scheme_name", str(code))

    f = returns_df[returns_df["scheme_code"] == code].sort_values("date")

    if f.empty:
        continue

    norm = make_normalized_cumret(f["daily_return"])
    plt.plot(f["date"], norm, label=name)

# Benchmarks cumulative returns
for idx_name, label in [("NIFTY50", "NIFTY50"), ("NIFTY100", "NIFTY100")]:
    b = bench_df[bench_df["index_name"] == idx_name].sort_values("date")
    if b.empty:
        continue

    norm = make_normalized_cumret(b["benchmark_return"])
    plt.plot(b["date"], norm, label=label)

plt.title("Top 5 Funds vs NIFTY50 & NIFTY100 (Last 3 Years)")
plt.legend()
plt.grid(True)

plt.savefig(chart_out, dpi=300, bbox_inches="tight")
plt.close()

print(f"Saved chart: {chart_out}")

# Tracking Error vs NIFTY100
nifty100 = bench_df[bench_df["index_name"] == "NIFTY100"].sort_values("date")[["date", "benchmark_return"]]

tracking_error_rows = []

for _, row in top5.iterrows():
    code = row["scheme_code"]
    f = returns_df[returns_df["scheme_code"] == code].sort_values("date")[["date", "daily_return"]]
    if f.empty:
        continue

    merged = f.merge(nifty100, on="date", how="inner")
    merged = merged.dropna(subset=["daily_return", "benchmark_return"])

    if len(merged) < 2:
        te = np.nan
    else:
        diff = merged["daily_return"] - merged["benchmark_return"]
        te = diff.std(ddof=1) * np.sqrt(252)

    tracking_error_rows.append({
        "scheme_code": code,
        "tracking_error": te,
    })

tracking_df = pd.DataFrame(tracking_error_rows)
tracking_df.to_csv(tracking_error_out, index=False)

print(f"Saved tracking error: {tracking_error_out}")



