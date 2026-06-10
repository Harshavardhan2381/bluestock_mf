import os
import pandas as pd
import numpy as np
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

returns_file = PROJECT_ROOT / "data/processed/returns_computed.csv"

out_file = PROJECT_ROOT / "data/processed/var_cvar_report.csv"


def main() -> None:
    df = pd.read_csv(returns_file)

    # Ensure date column exists and is parseable (some downstream scripts may expect it)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Normalize scheme_code to something stable for grouping/output
    if "scheme_code" not in df.columns:
        raise KeyError("returns_computed.csv must contain 'scheme_code'")
    if "daily_return" not in df.columns:
        raise KeyError("returns_computed.csv must contain 'daily_return'")

    var_rows = []

    for code, grp in df.groupby("scheme_code"):
        returns = grp["daily_return"].dropna()

        # Minimum sample size to avoid noisy/empty quantiles
        if len(returns) < 30:
            continue

        # 95% VaR corresponds to 5th percentile of returns
        var_95 = float(np.percentile(returns, 5))

        # CVaR is the mean of tail losses beyond VaR
        tail = returns[returns <= var_95]
        cvar_95 = float(tail.mean()) if len(tail) > 0 else float("nan")

        scheme_name = None
        if "scheme_name" in grp.columns:
            scheme_name = grp.iloc[-1].get("scheme_name", None)

        var_rows.append(
            {
                "scheme_code": code,
                "scheme_name": scheme_name,
                "var_95": var_95,
                "cvar_95": cvar_95,
            }
        )

    var_df = pd.DataFrame(var_rows)

    # Keep exact expected column order
    if not var_df.empty:
        var_df = var_df[["scheme_code", "scheme_name", "var_95", "cvar_95"]]

    out_file.parent.mkdir(parents=True, exist_ok=True)
    var_df.to_csv(out_file, index=False)

    print(f"Saved: {out_file}")
    if not var_df.empty:
        print(var_df.head())

    # ==========================================
    # ROLLING 90-DAY SHARPE RATIO
    # ==========================================
    import matplotlib.pyplot as plt

    # Ensure we have required columns for rolling computation
    if "date" not in df.columns:
        raise KeyError("returns_computed.csv must contain 'date' for rolling sharpe")
    if "scheme_name" not in df.columns:
        # Keep plotting functional; scheme_name can be null
        df["scheme_name"] = df["scheme_code"].astype(str)

    # Choose up to top 5 funds by available observations (stable when data is uneven)
    top_funds = (
        df.groupby(["scheme_code", "scheme_name"]).size().reset_index(name="n_obs").head(5)
    )

    os.makedirs(PROJECT_ROOT / "reports/charts", exist_ok=True)

    plt.figure(figsize=(12, 6))

    for _, row in top_funds.iterrows():
        code = row["scheme_code"]
        name = str(row["scheme_name"])[:25]

        fund = df[df["scheme_code"] == code].sort_values("date").copy()

        # rolling mean/std of daily returns
        rolling_mean = fund["daily_return"].rolling(90).mean()
        rolling_std = fund["daily_return"].rolling(90).std(ddof=1)

        # Sharpe: (mean / std) * sqrt(252)
        rolling_sharpe = (rolling_mean / rolling_std) * np.sqrt(252)

        plt.plot(fund["date"], rolling_sharpe, label=name)

    plt.title("Rolling 90-Day Sharpe Ratio")
    plt.xlabel("Date")
    plt.ylabel("Sharpe Ratio")
    plt.legend(fontsize=7)
    plt.grid(True)

    chart_out = PROJECT_ROOT / "reports/charts/rolling_sharpe_chart.png"
    plt.savefig(chart_out, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {chart_out}")


if __name__ == "__main__":
    main()


