"""Load explicit calculation inputs from a farm JSON file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SAMPLE_FARM_PATH = Path(__file__).resolve().parents[2] / "sample_data" / "farm.json"

REVENUE_KEYS = (
    "milking_cows",
    "litres_per_cow",
    "milk_price",
    "biss",
    "acres",
    "other_grants",
    "cattle_sales",
    "lamb_sales",
    "wool",
    "other",
)
COST_KEYS = (
    "feed",
    "fertiliser",
    "vet",
    "contractor",
    "labour",
    "insurance",
    "loan_repayments",
    "fuel",
    "electricity",
)


def load_farm_json(path: str | Path | None = None) -> dict[str, Any]:
    farm_path = Path(path) if path else SAMPLE_FARM_PATH
    with farm_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Farm file must be a JSON object: {farm_path}")
    return data


def farm_to_inputs(farm: dict[str, Any]) -> dict[str, Any]:
    """Flatten the demo JSON into the explicit fields the functions expect."""
    revenue = farm.get("revenue") or {}
    costs = farm.get("costs") or {}
    inputs: dict[str, Any] = {}
    for key in REVENUE_KEYS:
        if key in revenue and revenue[key] is not None:
            inputs[key] = revenue[key]
    for key in COST_KEYS:
        if key in costs and costs[key] is not None:
            inputs[key] = costs[key]
    return inputs


def load_sample_inputs(path: str | Path | None = None) -> dict[str, Any]:
    return farm_to_inputs(load_farm_json(path))
