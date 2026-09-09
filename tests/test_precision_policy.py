"""Characterise Phase 1 numeric precision and publish-time rounding (ADR-0006 / ADR-0005).

These tests document current behaviour. They do not redesign the numeric type.
"""

from __future__ import annotations

from farm_functions.calcs.costs import COST_CATEGORIES, total_costs
from farm_functions.calcs.profit import profit_margin, profit_margin_pct
from farm_functions.calcs.revenue import milk_revenue
from farm_functions.domain import FinancialInput
from farm_functions.provenance import explain_annual_pnl
from farm_functions.rounding import round_margin_pct, round_margin_ratio, round_money
from farm_functions.runner import run_function
from farm_functions.schemas import PlSummaryInput


def test_a_integer_inputs_publish_expected_money() -> None:
    result = run_function(
        "revenue.milk",
        {"milking_cows": 100, "litres_per_cow": 5000, "milk_price": 0.40},
    )
    assert result["status"] == "ok"
    assert result["result"] == {"amount": 200000.0, "currency": "EUR"}
    assert isinstance(result["result"]["amount"], float)


def test_b_fractional_milk_price_unrounded_vs_published_vs_provenance() -> None:
    payload = {"milking_cows": 100, "litres_per_cow": 5000, "milk_price": 0.333}
    raw = milk_revenue(100, 5000, 0.333)
    published = run_function("revenue.milk", payload)["result"]["amount"]
    provenance = explain_annual_pnl(FinancialInput.model_validate(payload))

    assert raw == 166500.0
    assert published == round_money(raw) == 166500.0
    assert provenance["revenue.milk"].value == raw
    assert isinstance(raw, float)
    assert isinstance(published, float)


def test_c_binary_float_artefact_contained_by_publish_rounding() -> None:
    # Classic IEEE-754 artefact: 0.1 + 0.2 is not exactly 0.3 in binary float.
    internal = 0.1 + 0.2
    assert internal != 0.3
    assert round_money(internal) == 0.3

    # Realistic money path: scheme cents that sum via float, then publish.
    raw_schemes = 0.1 + 0.2
    assert run_function(
        "revenue.schemes",
        {"biss": 0.1, "acres": 0.2, "other_grants": 0},
    )["result"]["amount"] == round_money(raw_schemes) == 0.3


def test_d_half_even_money_boundaries() -> None:
    assert round_money(1.225) == 1.22
    assert round_money(1.235) == 1.24
    assert round_money(1.005) == 1.00
    assert round_money(1.015) == 1.02


def test_e_aggregate_total_authoritative_vs_rounded_lines() -> None:
    payload = {
        "milking_cows": 100,
        "litres_per_cow": 5000,
        "milk_price": 0.333,
        "feed": 10_000.125,
        "labour": 1.225,
    }
    drivers = PlSummaryInput.model_validate(payload).model_dump()
    raw_total = total_costs(**{name: drivers[name] for name in COST_CATEGORIES})
    pl = run_function("pl.summary", payload)["result"]
    costs = run_function("costs.total", {k: payload[k] for k in ("feed", "labour")})

    assert pl["costs"]["lines"]["feed"] == round_money(10_000.125) == 10_000.12
    assert pl["costs"]["lines"]["labour"] == round_money(1.225) == 1.22
    assert sum(pl["costs"]["lines"].values()) == 10_001.34
    assert pl["costs"]["total"] == costs["result"]["amount"] == round_money(raw_total) == 10_001.35
    assert sum(pl["costs"]["lines"].values()) != pl["costs"]["total"]


def test_f_margin_rounding_and_zero_revenue() -> None:
    assert round_margin_ratio(0.12345) == 0.1234
    assert round_margin_pct(27.085) == 27.08

    zero = run_function("profit.margin", {"revenue": 0, "costs": 1000})
    assert zero["status"] == "ok"
    assert zero["result"]["margin"] == 0
    assert zero["result"]["margin_pct"] == 0
    assert profit_margin(0, 1000) == 0
    assert profit_margin_pct(0, 1000) == 0

    sample = run_function("profit.margin", {"revenue": 240_000, "costs": 175_000})
    assert sample["result"]["margin"] == 0.2708
    assert sample["result"]["margin_pct"] == 27.08


def test_g_provenance_stays_unrounded_when_publish_rounds() -> None:
    payload = {
        "milking_cows": 100,
        "litres_per_cow": 5000,
        "milk_price": 0.40,
        "biss": 12_345.678,
    }
    raw_schemes = 12_345.678
    published = run_function("revenue.schemes", {"biss": 12_345.678})["result"]["amount"]
    provenance = explain_annual_pnl(FinancialInput.model_validate(payload))

    assert provenance["revenue.schemes"].value == raw_schemes
    assert published == round_money(raw_schemes) == 12_345.68
    assert provenance["revenue.schemes"].value != published
