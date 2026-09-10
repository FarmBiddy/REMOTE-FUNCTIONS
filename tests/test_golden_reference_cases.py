"""Canonical annual P&L reference cases: lock published outputs against regression.

Expected values are stored in test-data/golden/annual_pnl_cases.json. They are not
re-derived from the engine at runtime. Golden outputs describe current software
behaviour, not final Workstream B financial semantics.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from farm_functions.domain import FinancialInput, FinancialModel, calculate_annual_pnl
from farm_functions.runner import run_function

GOLDEN_PATH = (
    Path(__file__).resolve().parents[1] / "test-data" / "golden" / "annual_pnl_cases.json"
)


def _load_cases() -> list[dict]:
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    cases = payload["cases"]
    assert cases, f"no golden cases in {GOLDEN_PATH}"
    return cases


CASES = _load_cases()
CASE_IDS = [case["name"] for case in CASES]


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_golden_calculate_annual_pnl_matches_expected(case: dict) -> None:
    model = FinancialModel(inputs=FinancialInput.model_validate(case["input"]))
    assert calculate_annual_pnl(model).model_dump() == case["expected"]


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_golden_runner_pl_summary_matches_expected(case: dict) -> None:
    result = run_function("pl.summary", case["input"])
    assert result["status"] == "ok"
    assert result["function"] == "pl.summary"
    assert result["result"] == case["expected"]
