"""Canonical Operating Statement characterisation (ADR-0009).

Locks permanent invariants: pl.summary is the authoritative annual view; atomic
published schedules reconcile to it; loans stay in finance. Intentionally thin —
broader cross-layer coverage remains in test_contract_reconciliation.py and
test_operating_surplus.py.
"""

from __future__ import annotations

from farm_functions.calcs.costs import OPERATING_COST_CATEGORIES
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.registry import OPTIONAL_FIELDS, REQUIRED_FIELDS
from farm_functions.runner import run_function


def _ok(calculation_id: str, payload: dict) -> dict:
    result = run_function(calculation_id, payload)
    assert result["status"] == "ok", (calculation_id, result)
    return result["result"]


def _revenue_total_payload(payload: dict) -> dict:
    keys = REQUIRED_FIELDS["revenue.total"] + OPTIONAL_FIELDS["revenue.total"]
    return {k: payload[k] for k in keys if k in payload}


def _costs_payload(payload: dict) -> dict:
    return {k: payload[k] for k in OPERATING_COST_CATEGORIES if k in payload}


def test_reference_farm_operating_statement() -> None:
    """Sample farm: €240k income − €163k costs = €77k surplus; loans €12k in finance."""
    pl = _ok("pl.summary", load_sample_inputs())
    assert pl["revenue"]["total"] == 240_000
    assert pl["costs"]["total"] == 163_000
    assert pl["profit"]["net"] == 77_000
    assert pl["finance"]["loan_repayments"] == 12_000
    assert "loan_repayments" not in pl["costs"]["lines"]


def test_pl_summary_matches_atomic_published_schedules() -> None:
    """Same inputs: atomic runners match corresponding pl.summary published fields."""
    payload = load_sample_inputs()
    milk_keys = REQUIRED_FIELDS["revenue.milk"]
    scheme_keys = OPTIONAL_FIELDS["revenue.schemes"]
    other_keys = OPTIONAL_FIELDS["revenue.other"]

    milk = _ok("revenue.milk", {k: payload[k] for k in milk_keys})
    schemes = _ok(
        "revenue.schemes",
        {k: payload[k] for k in scheme_keys if k in payload},
    )
    other = _ok(
        "revenue.other",
        {k: payload[k] for k in other_keys if k in payload},
    )
    revenue_total = _ok("revenue.total", _revenue_total_payload(payload))
    costs_total = _ok("costs.total", _costs_payload(payload))
    profit = _ok(
        "profit.net",
        {"revenue": revenue_total["amount"], "costs": costs_total["amount"]},
    )
    margin = _ok(
        "profit.margin",
        {"revenue": revenue_total["amount"], "costs": costs_total["amount"]},
    )
    pl = _ok("pl.summary", payload)

    assert pl["revenue"]["milk"] == milk["amount"]
    assert pl["revenue"]["schemes"] == schemes["amount"]
    assert pl["revenue"]["other"] == other["amount"]
    assert pl["revenue"]["total"] == revenue_total["amount"]
    assert pl["costs"]["total"] == costs_total["amount"]
    assert pl["profit"]["net"] == profit["amount"]
    assert pl["profit"]["margin"] == margin["margin"]
    assert pl["profit"]["margin_pct"] == margin["margin_pct"]
    assert pl["profit"]["net"] == pl["revenue"]["total"] - pl["costs"]["total"]


def test_loan_change_does_not_change_operating_surplus_or_costs() -> None:
    base = load_sample_inputs()
    zero = _ok("pl.summary", {**base, "loan_repayments": 0})
    high = _ok("pl.summary", {**base, "loan_repayments": 50_000})
    assert zero["profit"]["net"] == high["profit"]["net"]
    assert zero["costs"]["total"] == high["costs"]["total"]
    assert zero["finance"]["loan_repayments"] == 0
    assert high["finance"]["loan_repayments"] == 50_000


def test_zero_revenue_and_loss_cases_reconcile() -> None:
    zero_rev = _ok(
        "pl.summary",
        {
            "milking_cows": 0,
            "litres_per_cow": 0,
            "milk_price": 0,
            "feed": 5_000,
        },
    )
    assert zero_rev["revenue"]["total"] == 0
    assert zero_rev["profit"]["net"] == -5_000
    assert zero_rev["profit"]["margin"] == 0
    assert zero_rev["profit"]["margin_pct"] == 0

    loss = _ok(
        "pl.summary",
        {
            "milking_cows": 100,
            "litres_per_cow": 5_000,
            "milk_price": 0.10,
            "feed": 80_000,
            "labour": 40_000,
        },
    )
    assert loss["costs"]["total"] > loss["revenue"]["total"]
    assert loss["profit"]["net"] == loss["revenue"]["total"] - loss["costs"]["total"]
    assert loss["profit"]["net"] < 0
