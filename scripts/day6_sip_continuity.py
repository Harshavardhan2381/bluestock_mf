import pandas as pd
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

tx_file = PROJECT_ROOT / "data/processed/clean_transactions.csv"
out_file = PROJECT_ROOT / "data/processed/sip_continuity.csv"


def main() -> None:
    df = pd.read_csv(tx_file)

    if "date" not in df.columns:
        raise KeyError("clean_transactions.csv must contain 'date'")
    if "investor_id" not in df.columns:
        raise KeyError("clean_transactions.csv must contain 'investor_id'")
    if "transaction_type" not in df.columns:
        raise KeyError("clean_transactions.csv must contain 'transaction_type'")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["investor_id", "date"])

    sip = df[df["transaction_type"] == "SIP"].copy()

    rows = []

    for investor, grp in sip.groupby("investor_id"):
        grp = grp.sort_values("date")

        if len(grp) < 6:
            continue

        gaps = grp["date"].diff().dt.days.dropna()
        if gaps.empty:
            continue

        avg_gap = gaps.mean()

        rows.append(
            {
                "investor_id": investor,
                "sip_count": len(grp),
                "avg_gap_days": round(float(avg_gap), 2),
                "risk_flag": "At Risk" if avg_gap > 35 else "Healthy",
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv(out_file, index=False)

    print("Saved:", out_file)
    if not out.empty:
        print(out.head())


if __name__ == "__main__":
    main()

