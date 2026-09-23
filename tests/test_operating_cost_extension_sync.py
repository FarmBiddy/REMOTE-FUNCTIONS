"""Structural sync: hand-duplicated operating-cost surfaces vs catalogue.

Does not re-test B5 runtime surplus / provenance / published-line behaviour.
Authoritative list: OPERATING_COST_CATEGORIES (ADR-0007).
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from api.routes import _EXAMPLE_VALUES
from farm_functions.calcs.costs import OPERATING_COST_CATEGORIES, total_costs
from farm_functions.calcs.summary import pl_summary
from farm_functions.domain import CostLines
from farm_functions.registry import OPTIONAL_FIELDS
from farm_functions.schemas import INPUT_FIELD_METADATA, TotalCostsInput

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FARM_PATH = REPO_ROOT / "sample_data" / "farm.json"
GOLDEN_PATH = REPO_ROOT / "test-data" / "golden" / "annual_pnl_cases.json"
CATALOGUE = list(OPERATING_COST_CATEGORIES)


def test_cost_lines_fields_match_operating_cost_catalogue() -> None:
    assert list(CostLines.model_fields) == CATALOGUE


def test_total_costs_input_fields_match_operating_cost_catalogue() -> None:
    assert list(TotalCostsInput.model_fields) == CATALOGUE


def test_total_costs_signature_matches_operating_cost_catalogue() -> None:
    params = list(inspect.signature(total_costs).parameters)
    assert params == CATALOGUE


def test_pl_summary_signature_includes_every_operating_cost() -> None:
    params = list(inspect.signature(pl_summary).parameters)
    cost_params = [name for name in params if name in OPERATING_COST_CATEGORIES]
    assert cost_params == CATALOGUE
    missing = [name for name in CATALOGUE if name not in params]
    assert missing == []


def test_costs_total_optional_fields_match_operating_cost_catalogue() -> None:
    assert list(OPTIONAL_FIELDS["costs.total"]) == CATALOGUE


def test_operating_cost_metadata_matches_total_costs_input() -> None:
    metadata_names = {item.name for item in INPUT_FIELD_METADATA}
    for name in CATALOGUE:
        assert name in metadata_names, f"missing INPUT_FIELD_METADATA for {name}"
    for name in TotalCostsInput.model_fields:
        assert name in metadata_names, f"TotalCostsInput field {name} has no metadata"


def test_sample_farm_cost_keys_match_operating_cost_catalogue() -> None:
    farm = json.loads(SAMPLE_FARM_PATH.read_text(encoding="utf-8"))
    assert list(farm["costs"]) == CATALOGUE


def test_golden_expected_cost_line_keys_match_operating_cost_catalogue() -> None:
    payload = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    cases = payload["cases"]
    assert cases, f"no golden cases in {GOLDEN_PATH}"
    for case in cases:
        lines = case["expected"]["costs"]["lines"]
        assert list(lines) == CATALOGUE, f"golden case {case['name']!r} cost lines drift"


def test_example_values_cover_every_operating_cost() -> None:
    missing = [name for name in CATALOGUE if name not in _EXAMPLE_VALUES]
    assert missing == []
