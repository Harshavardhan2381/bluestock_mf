import pandas as pd
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    tx_file = PROJECT_ROOT / "data/processed/clean_transactions.csv"
    out_file = PROJECT_ROOT / "data/processed/cohort_analysis.csv"

    df = pd.read_csv(tx_file)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["investor_id", "date"])

    # First transaction date per investor
    first_txn = (
        df.groupby("investor_id")["date"].min().reset_index(name="first_date")
    )
    first_txn["cohort_year"] = first_txn["first_date"].dt.year

    df = df.merge(
        first_txn[["investor_id", "cohort_year"]],
        on="investor_id",
        how="left",
    )

    rows = []

    for cohort, grp in df.groupby("cohort_year"):
        sip_grp = grp[grp["transaction_type"] == "SIP"]

        mode_series = grp["transaction_type"].mode()
        favorite = mode_series.iloc[0] if not mode_series.empty else None

        rows.append(
            {
                "cohort_year": cohort,
                "investor_count": grp["investor_id"].nunique(),
                "avg_sip_amount": sip_grp["amount_inr"].mean(),
                "total_invested": grp["amount_inr"].sum(),
                "favorite_transaction_type": favorite,
            }
        )

    cohort_df = pd.DataFrame(rows)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cohort_df.to_csv(out_file, index=False)

    print("Saved:", out_file)
    print(cohort_df)


if __name__ == "__main__":
    main()

