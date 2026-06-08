#!/usr/bin/env python3
"""Build bluestock_mf_dashboard.pbix from processed CSVs (no Power BI Desktop required)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd
from pbix_mcp.builder import PBIXBuilder

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT_PBIX = ROOT / "bluestock_mf_dashboard.pbix"
THEME_PATH = ROOT / "powerbi" / "bluestock_theme.json"

TABLES = [
    "clean_aum",
    "clean_sip_inflows",
    "clean_category_inflows",
    "clean_folio_count",
    "clean_performance",
    "clean_transactions",
    "fund_scorecard",
    "returns_computed",
    "tracking_error",
    "clean_fund_master",
]

DATE_COLS = {
    "clean_aum": ["report_date"],
    "clean_sip_inflows": ["month"],
    "clean_category_inflows": ["month"],
    "clean_folio_count": ["month"],
    "clean_transactions": ["date"],
    "returns_computed": ["date"],
}

INT_COLS = {
    "tracking_error": ["scheme_code"],
    "fund_scorecard": ["scheme_code"],
    "clean_fund_master": ["scheme_code"],
    "clean_performance": ["scheme_code"],
    "clean_transactions": ["scheme_code"],
    "returns_computed": ["scheme_code"],
}


def df_to_pbix_table(df: pd.DataFrame, table: str) -> tuple[list[dict], list[dict]]:
    work = df.copy()
    for col in DATE_COLS.get(table, []):
        if col in work.columns:
            work[col] = pd.to_datetime(work[col], errors="coerce")
    for col in INT_COLS.get(table, []):
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce").astype("Int64")

    columns: list[dict] = []
    for col in work.columns:
        dtype = str(work[col].dtype)
        if col in DATE_COLS.get(table, []) or "datetime" in dtype:
            data_type = "DateTime"
        elif dtype in ("int64", "Int64"):
            data_type = "Int64"
        elif dtype in ("float64", "Float64"):
            data_type = "Double"
        elif dtype == "bool":
            data_type = "Boolean"
        else:
            data_type = "String"
        columns.append({"name": col, "data_type": data_type})

    rows: list[dict] = []
    for record in work.where(pd.notnull(work), None).to_dict(orient="records"):
        clean: dict = {}
        for key, value in record.items():
            if value is None or (isinstance(value, float) and pd.isna(value)):
                clean[key] = None
            elif hasattr(value, "isoformat"):
                clean[key] = value.isoformat()
            elif isinstance(value, pd.Timestamp):
                clean[key] = value.isoformat()
            else:
                clean[key] = value
        rows.append(clean)
    return columns, rows


def inject_theme(pbix_path: Path, theme_path: Path) -> None:
    """Embed Bluestock theme JSON into the PBIX package."""
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    tmp = pbix_path.with_suffix(".pbix.tmp")
    with zipfile.ZipFile(pbix_path, "r") as zin, zipfile.ZipFile(tmp, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "Report/Layout":
                layout = json.loads(data.decode("utf-16-le"))
                layout["theme"] = theme
                data = json.dumps(layout, ensure_ascii=False).encode("utf-16-le")
            zout.writestr(item, data)
    tmp.replace(pbix_path)


def build() -> Path:
    builder = PBIXBuilder("Bluestock MF Dashboard")
    builder.add_table(
        "_Measures",
        [{"name": "Placeholder", "data_type": "Int64"}],
        rows=[{"Placeholder": 1}],
        hidden=True,
    )

    for name in TABLES:
        path = PROCESSED / f"{name}.csv"
        df = pd.read_csv(path)
        columns, rows = df_to_pbix_table(df, name)
        builder.add_table(
            name,
            columns,
            rows=rows,
            source_csv=str(path.resolve()),
        )

    for child in (
        "clean_performance",
        "fund_scorecard",
        "returns_computed",
        "tracking_error",
    ):
        builder.add_relationship(child, "scheme_code", "clean_fund_master", "scheme_code")

    measures = [
        (
            "Total AUM",
            "VAR LatestDate = MAX ( clean_aum[report_date] ) "
            "RETURN CALCULATE ( SUM ( clean_aum[aum_crore] ), clean_aum[report_date] = LatestDate )",
        ),
        (
            "Total SIP",
            "VAR LatestMonth = MAX ( clean_sip_inflows[month] ) "
            "RETURN CALCULATE ( SUM ( clean_sip_inflows[sip_inflow_crore] ), "
            "clean_sip_inflows[month] = LatestMonth )",
        ),
        (
            "Total Folios",
            "VAR LatestMonth = MAX ( clean_folio_count[month] ) "
            "RETURN CALCULATE ( MAX ( clean_folio_count[total_folios_crore] ), "
            "clean_folio_count[month] = LatestMonth )",
        ),
        ("Total Schemes", "DISTINCTCOUNT ( clean_performance[scheme_code] )"),
        ("Industry AUM Trend", "SUM ( clean_aum[aum_crore] )"),
        ("Transaction Amount", "SUM ( clean_transactions[amount_inr] )"),
        (
            "Category Net Inflow",
            "SUM ( clean_category_inflows[net_inflow_crore] )",
        ),
        ("SIP Inflow", "SUM ( clean_sip_inflows[sip_inflow_crore] )"),
        ("Current SIP", "[Total SIP]"),
        (
            "Previous SIP",
            "VAR LatestMonth = MAX ( clean_sip_inflows[month] ) "
            "VAR PriorYearMonth = EDATE ( LatestMonth, -12 ) "
            "RETURN CALCULATE ( SUM ( clean_sip_inflows[sip_inflow_crore] ), "
            "clean_sip_inflows[month] = PriorYearMonth )",
        ),
        ("YoY SIP Growth %", "DIVIDE ( [Current SIP] - [Previous SIP], [Previous SIP] )"),
        ("Fund Score", "AVERAGE ( fund_scorecard[score] )"),
    ]
    for measure_name, expression in measures:
        builder.add_measure("_Measures", measure_name, expression)

    builder.add_page(
        "Industry Overview",
        [
            {"name": "kpi_aum", "type": "card", "x": 20, "y": 20, "width": 290, "height": 110,
             "config": {"measure": "Total AUM"}},
            {"name": "kpi_sip", "type": "card", "x": 330, "y": 20, "width": 290, "height": 110,
             "config": {"measure": "Total SIP"}},
            {"name": "kpi_folios", "type": "card", "x": 640, "y": 20, "width": 290, "height": 110,
             "config": {"measure": "Total Folios"}},
            {"name": "kpi_schemes", "type": "card", "x": 950, "y": 20, "width": 290, "height": 110,
             "config": {"measure": "Total Schemes"}},
            {"name": "aum_trend", "type": "lineChart", "x": 20, "y": 150, "width": 600, "height": 320,
             "config": {"category": {"table": "clean_aum", "column": "report_date"},
                        "measure": "Industry AUM Trend"}},
            {"name": "top_amc", "type": "clusteredBarChart", "x": 640, "y": 150, "width": 600, "height": 320,
             "config": {"category": {"table": "clean_aum", "column": "fund_house"},
                        "measure": "Industry AUM Trend"}},
        ],
    )

    builder.add_page(
        "Fund Performance",
        [
            {"name": "slicer_house", "type": "slicer", "x": 20, "y": 20, "width": 250, "height": 100,
             "config": {"column": {"table": "returns_computed", "column": "fund_house"}}},
            {"name": "slicer_category", "type": "slicer", "x": 290, "y": 20, "width": 250, "height": 100,
             "config": {"column": {"table": "returns_computed", "column": "scheme_category"}}},
            {"name": "slicer_risk", "type": "slicer", "x": 560, "y": 20, "width": 250, "height": 100,
             "config": {"column": {"table": "clean_performance", "column": "risk_grade"}}},
            {"name": "scorecard", "type": "table", "x": 20, "y": 140, "width": 1220, "height": 520,
             "config": {"columns": [
                 {"table": "clean_fund_master", "column": "scheme_name"},
                 {"table": "fund_scorecard", "column": "score"},
                 {"table": "fund_scorecard", "column": "rank_3yr_cagr"},
                 {"table": "fund_scorecard", "column": "rank_sharpe"},
                 {"table": "fund_scorecard", "column": "rank_alpha"},
             ]}},
        ],
    )

    builder.add_page(
        "Investor Analytics",
        [
            {"name": "donut_txn", "type": "pieChart", "x": 20, "y": 20, "width": 400, "height": 320,
             "config": {"category": {"table": "clean_transactions", "column": "transaction_type"},
                        "measure": "Transaction Amount"}},
            {"name": "bar_payment", "type": "clusteredBarChart", "x": 440, "y": 20, "width": 400, "height": 320,
             "config": {"category": {"table": "clean_transactions", "column": "payment_mode"},
                        "measure": "Transaction Amount"}},
            {"name": "bar_kyc", "type": "clusteredBarChart", "x": 860, "y": 20, "width": 380, "height": 320,
             "config": {"category": {"table": "clean_transactions", "column": "kyc_status"},
                        "measure": "Transaction Amount"}},
            {"name": "slicer_txn", "type": "slicer", "x": 20, "y": 360, "width": 250, "height": 100,
             "config": {"column": {"table": "clean_transactions", "column": "transaction_type"}}},
            {"name": "slicer_payment", "type": "slicer", "x": 290, "y": 360, "width": 250, "height": 100,
             "config": {"column": {"table": "clean_transactions", "column": "payment_mode"}}},
            {"name": "slicer_kyc", "type": "slicer", "x": 560, "y": 360, "width": 250, "height": 100,
             "config": {"column": {"table": "clean_transactions", "column": "kyc_status"}}},
        ],
    )

    builder.add_page(
        "SIP & Market Trends",
        [
            {"name": "kpi_yoy", "type": "card", "x": 20, "y": 20, "width": 300, "height": 110,
             "config": {"measure": "YoY SIP Growth %"}},
            {"name": "sip_trend", "type": "lineChart", "x": 20, "y": 150, "width": 600, "height": 320,
             "config": {"category": {"table": "clean_sip_inflows", "column": "month"},
                        "measure": "SIP Inflow"}},
            {"name": "category_matrix", "type": "matrix", "x": 640, "y": 150, "width": 600, "height": 320,
             "config": {"columns": [
                 {"table": "clean_category_inflows", "column": "category"},
                 {"table": "clean_category_inflows", "column": "month"},
                 {"measure": "Category Net Inflow"},
             ]}},
            {"name": "top_categories", "type": "clusteredBarChart", "x": 20, "y": 490, "width": 1220, "height": 210,
             "config": {"category": {"table": "clean_category_inflows", "column": "category"},
                        "measure": "Category Net Inflow"}},
        ],
    )

    builder.add_page(
        "Fund Details",
        [
            {"name": "fund_score", "type": "card", "x": 20, "y": 20, "width": 280, "height": 110,
             "config": {"measure": "Fund Score"}},
        ],
    )

    builder.save(str(OUT_PBIX))
    if THEME_PATH.exists():
        inject_theme(OUT_PBIX, THEME_PATH)
    return OUT_PBIX


if __name__ == "__main__":
    path = build()
    print(f"Created: {path} ({path.stat().st_size:,} bytes)")
