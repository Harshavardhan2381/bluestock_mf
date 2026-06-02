from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests


BASE_URL = "https://api.mfapi.in"
MF_BASE = f"{BASE_URL}/mf"


@dataclass(frozen=True)
class SchemeSpec:
    scheme_code: int
    label: str


KEY_SCHEMES: List[SchemeSpec] = [
    SchemeSpec(125497, "HDFC_Top_100_Direct_Growth"),
    SchemeSpec(119551, "SBI_Bluechip"),
    SchemeSpec(120503, "ICICI_Bluechip"),
    SchemeSpec(118632, "Nippon_Large_Cap"),
    SchemeSpec(119092, "Axis_Bluechip"),
    SchemeSpec(120841, "Kotak_Bluechip"),
