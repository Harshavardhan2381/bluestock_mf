#!/usr/bin/env python3
"""Export dashboard PNG pages and combined PDF (macOS-friendly; no Power BI Desktop)."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
ASSETS = ROOT / "powerbi" / "assets"

NAVY = "#003366"
BLUE = "#0057B8"
CYAN = "#00A3E0"
BG = "#F4F7FB"
WHITE = "#FFFFFF"


def ensure_logo() -> Path:
    logo = ASSETS / "bluestock_logo.png"
    if logo.exists():
        return logo
    ASSETS.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (220, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, 219, 47), radius=8, fill=NAVY)
    draw.rectangle((12, 10, 28, 38), fill=CYAN)
    draw.polygon([(28, 10), (44, 24), (28, 38)], fill=BLUE)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 20)
    except OSError:
        font = ImageFont.load_default()
    draw.text((54, 12), "Bluestock", fill=WHITE, font=font)
    img.save(logo)
    return logo


def load_data() -> dict[str, pd.DataFrame]:
    data: dict[str, pd.DataFrame] = {}
    for name in [
        "clean_aum",
        "clean_sip_inflows",
        "clean_category_inflows",
        "clean_folio_count",
        "clean_performance",
        "clean_transactions",
        "fund_scorecard",
        "returns_computed",
        "clean_fund_master",
    ]:
        path = PROCESSED / f"{name}.csv"
        df = pd.read_csv(path)
        for col in df.columns:
            if col in ("report_date", "month", "date"):
                df[col] = pd.to_datetime(df[col], errors="coerce")
        data[name] = df
    return data


def kpis(data: dict[str, pd.DataFrame]) -> dict[str, float]:
    aum = data["clean_aum"]
    latest_aum = aum["report_date"].max()
    total_aum = aum.loc[aum["report_date"] == latest_aum, "aum_crore"].sum()

    sip = data["clean_sip_inflows"]
    latest_sip_month = sip["month"].max()
    total_sip = sip.loc[sip["month"] == latest_sip_month, "sip_inflow_crore"].sum()

    folio = data["clean_folio_count"]
    latest_folio = folio["month"].max()
    total_folios = folio.loc[folio["month"] == latest_folio, "total_folios_crore"].iloc[0]

    schemes = data["clean_performance"]["scheme_code"].nunique()

    sip_sorted = sip.sort_values("month")
    yoy = (sip_sorted.iloc[-1]["sip_inflow_crore"] - sip_sorted.iloc[-13]["sip_inflow_crore"]) / sip_sorted.iloc[-13]["sip_inflow_crore"] * 100

    return {
        "total_aum": total_aum,
        "total_sip": total_sip,
        "total_folios": total_folios,
        "total_schemes": schemes,
        "yoy_sip": yoy,
    }


def style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(WHITE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BLUE)
    ax.spines["bottom"].set_color(BLUE)
    ax.tick_params(colors=NAVY)
    ax.title.set_color(NAVY)


def add_header(fig: plt.Figure, title: str, logo_path: Path) -> None:
    fig.patch.set_facecolor(BG)
    fig.text(0.03, 0.95, title, fontsize=18, fontweight="bold", color=NAVY)
    logo = plt.imread(logo_path)
    ax_logo = fig.add_axes([0.86, 0.91, 0.12, 0.06])
    ax_logo.imshow(logo)
    ax_logo.axis("off")


def draw_kpi_card(ax: plt.Axes, label: str, value: str) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    patch = FancyBboxPatch(
        (0.02, 0.08), 0.96, 0.84, boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1, edgecolor=BLUE, facecolor=WHITE,
    )
    ax.add_patch(patch)
    ax.text(0.5, 0.68, value, ha="center", va="center", fontsize=20, fontweight="bold", color=NAVY)
    ax.text(0.5, 0.28, label, ha="center", va="center", fontsize=11, color=BLUE)


def page_industry_overview(fig: plt.Figure, data: dict[str, pd.DataFrame], kpi: dict[str, float]) -> None:
    cards = fig.add_gridspec(1, 4, left=0.06, right=0.94, top=0.88, bottom=0.72, wspace=0.12)
    gs = GridSpec(2, 2, figure=fig, left=0.06, right=0.94, top=0.68, bottom=0.08, hspace=0.35, wspace=0.25)
    labels = [
        ("Total AUM", f"{kpi['total_aum']:,.0f} Cr"),
        ("Total SIP", f"{kpi['total_sip']:,.0f} Cr"),
        ("Total Folios", f"{kpi['total_folios']:.2f} Cr"),
        ("Total Schemes", f"{int(kpi['total_schemes'])}"),
    ]
    for i, (label, value) in enumerate(labels):
        draw_kpi_card(fig.add_subplot(cards[i]), label, value)

    aum = data["clean_aum"].copy()
    trend = aum.groupby("report_date", as_index=False)["aum_crore"].sum()
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(trend["report_date"], trend["aum_crore"], color=CYAN, linewidth=2.5, marker="o", markersize=4)
    ax1.set_title("Industry AUM Trend (2022–2025)")
    ax1.set_ylabel("AUM (Cr)")
    style_axes(ax1)

    latest = aum["report_date"].max()
    top = (
        aum.loc[aum["report_date"] == latest]
        .groupby("fund_house", as_index=False)["aum_crore"]
        .sum()
        .sort_values("aum_crore", ascending=True)
        .tail(10)
    )
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.barh(top["fund_house"], top["aum_crore"], color=BLUE)
    ax2.set_title("Top 10 AMCs by AUM")
    ax2.set_xlabel("AUM (Cr)")
    style_axes(ax2)


def page_fund_performance(fig: plt.Figure, data: dict[str, pd.DataFrame]) -> None:
    gs = GridSpec(2, 2, figure=fig, left=0.06, right=0.94, top=0.86, bottom=0.08, hspace=0.35, wspace=0.28)
    perf = data["clean_performance"]
    master = data["clean_fund_master"][["scheme_code", "scheme_name"]].rename(
        columns={"scheme_name": "fund_name"}
    )
    score = data["fund_scorecard"].merge(master, on="scheme_code", how="left")
    score["fund_name"] = score["fund_name"].fillna(score["scheme_name"].astype(str))

    ax1 = fig.add_subplot(gs[0, 0])
    colors = {"Low": CYAN, "Moderate": BLUE, "High": NAVY}
    for grade, grp in perf.groupby("risk_grade"):
        ax1.scatter(
            grp["return_3yr_pct"], grp["std_dev_ann_pct"],
            s=np.clip(grp["aum_crore"] / 80, 20, 400),
            alpha=0.75, label=grade, color=colors.get(grade, BLUE),
        )
    ax1.set_xlabel("3Y Return (%)")
    ax1.set_ylabel("Risk (Std Dev %)")
    ax1.set_title("Risk vs Return")
    ax1.legend(frameon=False)
    style_axes(ax1)

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis("off")
    table_df = score.sort_values("score", ascending=False).head(12)[
        ["fund_name", "score", "rank_3yr_cagr", "rank_sharpe", "rank_alpha"]
    ]
    table_df = table_df.rename(columns={"fund_name": "scheme_name"})
    display = table_df.copy()
    for col in display.columns:
        if col != "scheme_name":
            display[col] = display[col].map(lambda v: f"{float(v):.1f}")
    table = ax2.table(
        cellText=display.values,
        colLabels=display.columns,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.4)
    ax2.set_title("Fund Scorecard", color=NAVY, pad=20)

    ret = data["returns_computed"]
    sample = ret["scheme_name"].value_counts().index[0]
    nav = ret.loc[ret["scheme_name"] == sample].sort_values("date")
    ax3 = fig.add_subplot(gs[1, :])
    ax3.plot(nav["date"], nav["nav"], color=BLUE, linewidth=2)
    ax3.set_title(f"NAV Trend — {sample[:50]}")
    ax3.set_ylabel("NAV")
    style_axes(ax3)


def page_investor_analytics(fig: plt.Figure, data: dict[str, pd.DataFrame]) -> None:
    gs = GridSpec(2, 2, figure=fig, left=0.06, right=0.94, top=0.86, bottom=0.08, hspace=0.35, wspace=0.28)
    txn = data["clean_transactions"]

    ax1 = fig.add_subplot(gs[0, 0])
    by_type = txn.groupby("transaction_type")["amount_inr"].sum()
    ax1.pie(by_type.values, labels=by_type.index, autopct="%1.1f%%", colors=[CYAN, BLUE, NAVY])
    ax1.set_title("Transaction Type")

    ax2 = fig.add_subplot(gs[0, 1])
    pay = txn.groupby("payment_mode")["amount_inr"].sum().sort_values(ascending=True)
    ax2.barh(pay.index, pay.values, color=BLUE)
    ax2.set_title("Payment Mode")
    style_axes(ax2)

    ax3 = fig.add_subplot(gs[1, 0])
    kyc = txn.groupby("kyc_status")["amount_inr"].sum()
    ax3.bar(kyc.index, kyc.values, color=CYAN)
    ax3.set_title("KYC Status")
    style_axes(ax3)

    monthly = txn.copy()
    monthly["month"] = monthly["date"].dt.to_period("M").dt.to_timestamp()
    trend = monthly.groupby("month")["amount_inr"].sum()
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(trend.index, trend.values, color=BLUE, linewidth=2)
    ax4.set_title("Monthly Transactions")
    ax4.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M"))
    style_axes(ax4)


def page_sip_market_trends(fig: plt.Figure, data: dict[str, pd.DataFrame], kpi: dict[str, float]) -> None:
    cards = fig.add_gridspec(1, 1, left=0.06, right=0.3, top=0.88, bottom=0.72)
    gs = GridSpec(2, 2, figure=fig, left=0.06, right=0.94, top=0.68, bottom=0.08, hspace=0.35, wspace=0.28)
    draw_kpi_card(fig.add_subplot(cards[0]), "YoY SIP Growth %", f"{kpi['yoy_sip']:.2f}%")

    sip = data["clean_sip_inflows"].sort_values("month")
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(sip["month"], sip["sip_inflow_crore"], color=CYAN, linewidth=2.5, marker="o", markersize=3)
    ax1.set_title("SIP Trend")
    ax1.set_ylabel("SIP Inflow (Cr)")
    style_axes(ax1)

    cat = data["clean_category_inflows"]
    pivot = cat.pivot_table(index="category", columns="month", values="net_inflow_crore", aggfunc="sum")
    pivot = pivot.iloc[:, -12:]
    ax2 = fig.add_subplot(gs[0, 1])
    im = ax2.imshow(pivot.values, aspect="auto", cmap="Blues")
    ax2.set_yticks(range(len(pivot.index)), pivot.index, fontsize=7)
    ax2.set_xticks(range(len(pivot.columns)), [c.strftime("%Y-%m") for c in pivot.columns], rotation=45, ha="right", fontsize=7)
    ax2.set_title("Category Net Inflow Heatmap")
    fig.colorbar(im, ax=ax2, fraction=0.046, pad=0.04)

    fy = cat[(cat["month"] >= "2024-04-01") & (cat["month"] <= "2025-03-31")]
    top5 = fy.groupby("category")["net_inflow_crore"].sum().sort_values(ascending=True).tail(5)
    ax3 = fig.add_subplot(gs[1, :])
    ax3.barh(top5.index, top5.values, color=BLUE)
    ax3.set_title("Top 5 Categories (FY25)")
    ax3.set_xlabel("Net Inflow (Cr)")
    style_axes(ax3)


def export_all() -> list[Path]:
    logo = ensure_logo()
    data = load_data()
    kpi = kpis(data)

    pages = [
        ("Industry Overview", "Industry_Overview.png", lambda fig: page_industry_overview(fig, data, kpi)),
        ("Fund Performance", "Fund_Performance.png", lambda fig: page_fund_performance(fig, data)),
        ("Investor Analytics", "Investor_Analytics.png", lambda fig: page_investor_analytics(fig, data)),
        ("SIP & Market Trends", "SIP_Market_Trends.png", lambda fig: page_sip_market_trends(fig, data, kpi)),
    ]

    outputs: list[Path] = []
    pdf_path = ROOT / "Dashboard.pdf"
    with PdfPages(pdf_path) as pdf:
        for title, filename, draw_fn in pages:
            fig = plt.figure(figsize=(12.8, 7.2), dpi=150)
            add_header(fig, title, logo)
            draw_fn(fig)
            png_path = ROOT / filename
            fig.savefig(png_path, facecolor=BG, bbox_inches="tight")
            pdf.savefig(fig, facecolor=BG, bbox_inches="tight")
            plt.close(fig)
            outputs.append(png_path)
    outputs.append(pdf_path)
    return outputs


if __name__ == "__main__":
    paths = export_all()
    for p in paths:
        print(f"Exported: {p}")
