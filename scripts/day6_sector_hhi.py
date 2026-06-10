import pandas as pd
import numpy as np
from pathlib import Path

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]

holdings_file = PROJECT_ROOT / "data/processed/clean_holdings.csv"
out_csv = PROJECT_ROOT / "data/processed/sector_hhi.csv"
out_chart = PROJECT_ROOT / "reports/charts/sector_hhi.png"


def main() -> None:
    df = pd.read_csv(holdings_file)

    required = {"sector", "weight_pct"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"clean_holdings.csv missing columns: {sorted(missing)}")

    # Weight should be numeric; treat NaNs as 0 (ignored later by normalization)
    df["weight_pct"] = pd.to_numeric(df["weight_pct"], errors="coerce")
    df = df.dropna(subset=["sector", "weight_pct"])

    # Convert % to weights that sum to 1 per holdings snapshot (sector concentration per fund/date)
    # We normalize within each scheme holding snapshot.
    group_cols = []
    if "amfi_code" in df.columns:
        group_cols.append("amfi_code")
    elif "scheme_code" in df.columns:
        group_cols.append("scheme_code")

    if "portfolio_date" in df.columns:
        group_cols.append("portfolio_date")

    # If we can't find a snapshot grouping, fallback to whole dataset
    if not group_cols:
        group_cols = ["__all__"]
        df = df.assign(__all__=0)

    # HHI = sum_i (w_i^2) where w_i are sector weights (sum to 1)
    def compute_hhi(g: pd.DataFrame) -> float:
        w = g["weight_pct"].astype(float).to_numpy()
        if w.sum() == 0:
            return float("nan")
        w_norm = w / w.sum()
        return float(np.sum(np.square(w_norm)))

    # First: aggregate weights by sector within each snapshot
    sector_weights = (
        df.groupby(group_cols + ["sector"], as_index=False)["weight_pct"]
        .sum()
    )

    hhi_df = (
        sector_weights.groupby(group_cols)
        .apply(lambda g: compute_hhi(g))
        .reset_index(name="hhi")
    )

    # Optional: derive a simple concentration bucket (for readability)
    # Typical interpretation: higher => more concentrated.
    # Since weights are normalized, max HHI approaches 1.
    bins = [0.0, 0.18, 0.3, 0.45, 1.0]
    labels = ["Low", "Moderate", "High", "Very High"]
    hhi_df["concentration_level"] = pd.cut(
        hhi_df["hhi"], bins=bins, labels=labels, include_lowest=True
    ).astype(str)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    hhi_df.to_csv(out_csv, index=False)

    # Chart: show HHI over portfolio_date for top 5 funds by number of snapshots
    chart_df = hhi_df.copy()
    if "portfolio_date" in chart_df.columns:
        chart_df["portfolio_date"] = pd.to_datetime(chart_df["portfolio_date"], errors="coerce")
        chart_df = chart_df.dropna(subset=["portfolio_date"])

    # If we have amfi_code/scheme_code, use it for plotting
    fund_col = None
    for c in ["amfi_code", "scheme_code"]:
        if c in chart_df.columns:
            fund_col = c
            break

    plt.figure(figsize=(12, 6))

    if fund_col and "portfolio_date" in chart_df.columns:
        top_funds = chart_df[fund_col].value_counts().head(5).index.tolist()
        for fc in top_funds:
            sub = chart_df[chart_df[fund_col] == fc].sort_values("portfolio_date")
            plt.plot(sub["portfolio_date"], sub["hhi"], marker="o", linewidth=1, label=str(fc)[:12])
        plt.legend(fontsize=8)
        plt.xlabel("Portfolio Date")
    else:
        # Fallback: bar chart of HHI values
        plt.bar(range(len(chart_df)), chart_df["hhi"])
        plt.xlabel("Snapshot")

    plt.ylabel("HHI (sector concentration)")
    plt.title("Sector Concentration (HHI)")
    plt.grid(True, alpha=0.3)

    out_chart.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_chart, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {out_csv}")
    print(f"Saved: {out_chart}")
    print(hhi_df.head())


if __name__ == "__main__":
    main()

