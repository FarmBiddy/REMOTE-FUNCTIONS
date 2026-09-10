"""Cross-layer contract reconciliation: public IDs, domain, runner, HTTP, provenance.

Compares outputs from independent paths. Does not reimplement financial formulas.
Provenance values are intentionally unrounded; published pl.summary / money results use
banker's rounding (ADR-0005).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app
from farm_functions.calcs.costs import COST_CATEGORIES, total_costs
from farm_functions.calcs.profit import net_profit, profit_margin
from farm_functions.calcs.revenue import milk_revenue, other_revenue, scheme_revenue, total_revenue
from farm_functions.domain import FinancialInput, FinancialModel, calculate_annual_pnl
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.provenance import SUPPORTED_CALCULATIONS, explain_annual_pnl
from farm_functions.registry import OPTIONAL_FIELDS, REQUIRED_FIELDS
from farm_functions.rounding import round_money
from farm_functions.runner import run_function
from farm_functions.schemas import FIELD_UNITS, PlSummaryInput

client = TestClient(app)

SAMPLE = load_sample_inputs()

SAMPLE_MILK = {
    "milking_cows": SAMPLE["milking_cows"],
    "litres_per_cow": SAMPLE["litres_per_cow"],
    "milk_price": SAMPLE["milk_price"],
}

HTTP_RECONCILE_IDS = (
    "revenue.milk",
    "revenue.total",
    "costs.total",
    "profit.net",
    "profit.margin",
    "pl.summary",
)


def _ok(calculation_id: str, payload: dict) -> dict:
    result = run_function(calculation_id, payload)
    assert result["status"] == "ok", (calculation_id, result)
    assert result["function"] == calculation_id
    return result["result"]


def _pl(payload: dict) -> dict:
    return _ok("pl.summary", payload)


def _validated_drivers(payload: dict) -> dict:
    return PlSummaryInput.model_validate(payload).model_dump()


def _revenue_parts(payload: dict) -> tuple[dict, dict, dict]:
    milk_keys = REQUIRED_FIELDS["revenue.milk"]
    scheme_keys = OPTIONAL_FIELDS["revenue.schemes"]
    other_keys = OPTIONAL_FIELDS["revenue.other"]
    return (
        _ok("revenue.milk", {k: payload[k] for k in milk_keys}),
        _ok("revenue.schemes", {k: payload[k] for k in scheme_keys if k in payload}),
        _ok("revenue.other", {k: payload[k] for k in other_keys if k in payload}),
    )


def _revenue_total_payload(payload: dict) -> dict:
    keys = REQUIRED_FIELDS["revenue.total"] + OPTIONAL_FIELDS["revenue.total"]
    return {k: payload[k] for k in keys if k in payload}


def _costs_payload(payload: dict) -> dict:
    return {k: payload[k] for k in COST_CATEGORIES if k in payload}


@pytest.fixture(
    params=[
        pytest.param(SAMPLE, id="sample_farm"),
        pytest.param(SAMPLE_MILK, id="optionals_omitted"),
        pytest.param(
            {name: 0 for name in REQUIRED_FIELDS["pl.summary"] + OPTIONAL_FIELDS["pl.summary"]},
            id="all_explicit_zeros",
        ),
        pytest.param(
            {
                **SAMPLE_MILK,
                "milk_price": 0.333,
                "biss": 12_345.678,
                "feed": 10_000.125,
                "labour": 1.225,
            },
            id="fractional_prices",
        ),
    ]
)
def farm_payload(request) -> dict:
    return dict(request.param)


# --- 1. Revenue ---


def test_revenue_total_equals_sum_of_atomic_runners(farm_payload: dict) -> None:
    milk, schemes, other = _revenue_parts(farm_payload)
    total = _ok("revenue.total", _revenue_total_payload(farm_payload))
    assert total["amount"] == milk["amount"] + schemes["amount"] + other["amount"]


def test_pl_summary_revenue_matches_atomic_runners(farm_payload: dict) -> None:
    milk, schemes, other = _revenue_parts(farm_payload)
    total = _ok("revenue.total", _revenue_total_payload(farm_payload))
    pl = _pl(farm_payload)
    assert pl["revenue"]["milk"] == milk["amount"]
    assert pl["revenue"]["schemes"] == schemes["amount"]
    assert pl["revenue"]["other"] == other["amount"]
    assert pl["revenue"]["total"] == total["amount"]


# --- 2. Costs ---
# Published cost lines are independently round_money'd presentation values.
# Aggregate costs.total / pl.summary.costs.total is round_money(sum of raw
# validated inputs) and is authoritative — lines need not re-sum to total.


def test_costs_total_matches_pl_summary_and_lines(farm_payload: dict) -> None:
    drivers = _validated_drivers(farm_payload)
    costs = _ok("costs.total", _costs_payload(farm_payload))
    pl = _pl(farm_payload)
    raw_total = total_costs(**{name: drivers[name] for name in COST_CATEGORIES})
    assert pl["costs"]["total"] == costs["amount"]
    assert costs["amount"] == round_money(raw_total)
    assert list(pl["costs"]["lines"]) == list(COST_CATEGORIES)
    for name in COST_CATEGORIES:
        assert pl["costs"]["lines"][name] == round_money(drivers[name])


def test_fractional_cost_lines_need_not_resum_to_published_total() -> None:
    """Published lines are presentation; published total is authoritative."""
    payload = {
        **SAMPLE_MILK,
        "milk_price": 0.333,
        "biss": 12_345.678,
        "feed": 10_000.125,
        "labour": 1.225,
    }
    pl = _pl(payload)
    costs = _ok("costs.total", _costs_payload(payload))
    assert pl["costs"]["lines"]["feed"] == 10_000.12
    assert pl["costs"]["lines"]["labour"] == 1.22
    assert sum(pl["costs"]["lines"].values()) == 10_001.34
    assert pl["costs"]["total"] == costs["amount"] == 10_001.35
    assert sum(pl["costs"]["lines"].values()) != pl["costs"]["total"]


# --- 3–4. Profit and margin ---


def test_profit_and_margin_reconcile_with_pl_summary(farm_payload: dict) -> None:
    pl = _pl(farm_payload)
    revenue_total = pl["revenue"]["total"]
    costs_total = pl["costs"]["total"]
    profit = _ok("profit.net", {"revenue": revenue_total, "costs": costs_total})
    margin = _ok("profit.margin", {"revenue": revenue_total, "costs": costs_total})
    assert pl["profit"]["net"] == profit["amount"]
    assert margin["profit"] == pl["profit"]["net"]
    assert margin["margin"] == pl["profit"]["margin"]
    assert margin["margin_pct"] == pl["profit"]["margin_pct"]
    assert margin["revenue"] == revenue_total
    assert margin["costs"] == costs_total


def test_zero_revenue_margin_is_zero() -> None:
    margin = _ok("profit.margin", {"revenue": 0, "costs": 10_000})
    assert margin["margin"] == 0
    assert margin["margin_pct"] == 0
    assert margin["profit"] == round_money(-10_000)


def test_costs_greater_than_revenue_reconciles() -> None:
    payload = {
        **SAMPLE_MILK,
        "milk_price": 0.10,
        "feed": 80_000,
        "labour": 40_000,
    }
    pl = _pl(payload)
    assert pl["costs"]["total"] > pl["revenue"]["total"]
    profit = _ok(
        "profit.net",
        {"revenue": pl["revenue"]["total"], "costs": pl["costs"]["total"]},
    )
    assert pl["profit"]["net"] == profit["amount"]
    assert pl["profit"]["net"] < 0
    margin = _ok(
        "profit.margin",
        {"revenue": pl["revenue"]["total"], "costs": pl["costs"]["total"]},
    )
    assert margin["margin"] == pl["profit"]["margin"]
    assert margin["margin_pct"] == pl["profit"]["margin_pct"]


# --- 5. Domain ---


def test_domain_calculate_annual_pnl_matches_pl_summary(farm_payload: dict) -> None:
    via_runner = _pl(farm_payload)
    model = FinancialModel(inputs=FinancialInput.model_validate(farm_payload))
    typed = calculate_annual_pnl(model)
    assert typed.model_dump() == via_runner
    assert typed.currency == "EUR"
    assert typed.period == "annual"
    assert typed.revenue.model_dump() == via_runner["revenue"]
    assert typed.costs.model_dump() == via_runner["costs"]
    assert typed.profit.model_dump() == via_runner["profit"]


# --- 6. Runner / HTTP ---


@pytest.mark.parametrize("calculation_id", HTTP_RECONCILE_IDS)
def test_http_matches_runner_for_main_calculations(calculation_id: str) -> None:
    if calculation_id == "revenue.milk":
        payload = dict(SAMPLE_MILK)
    elif calculation_id == "revenue.total":
        payload = _revenue_total_payload(SAMPLE)
    elif calculation_id == "costs.total":
        payload = _costs_payload(SAMPLE)
    elif calculation_id in ("profit.net", "profit.margin"):
        pl = _pl(SAMPLE)
        payload = {"revenue": pl["revenue"]["total"], "costs": pl["costs"]["total"]}
    else:
        payload = dict(SAMPLE)

    via_runner = run_function(calculation_id, payload)
    response = client.post(f"/v1/functions/{calculation_id}/run", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == via_runner["status"] == "ok"
    assert body["function"] == calculation_id
    assert body["result"] == via_runner["result"]


# --- 7. Provenance (unrounded) ---


def test_provenance_reconciles_with_unrounded_calcs(farm_payload: dict) -> None:
    drivers = _validated_drivers(farm_payload)
    provenance = explain_annual_pnl(FinancialInput.model_validate(farm_payload))
    assert set(provenance) == set(SUPPORTED_CALCULATIONS)

    milk = milk_revenue(
        drivers["milking_cows"], drivers["litres_per_cow"], drivers["milk_price"]
    )
    schemes = scheme_revenue(
        biss=drivers["biss"],
        acres=drivers["acres"],
        other_grants=drivers["other_grants"],
    )
    other = other_revenue(
        cattle_sales=drivers["cattle_sales"],
        lamb_sales=drivers["lamb_sales"],
        wool=drivers["wool"],
        other=drivers["other"],
    )
    revenue = total_revenue(**{k: drivers[k] for k in _revenue_total_payload(drivers)})
    costs = total_costs(**{name: drivers[name] for name in COST_CATEGORIES})
    profit = net_profit(revenue, costs)
    margin = profit_margin(revenue, costs)

    expected_values = {
        "revenue.milk": milk,
        "revenue.schemes": schemes,
        "revenue.other": other,
        "revenue.total": revenue,
        "costs.total": costs,
        "profit.net": profit,
        "profit.margin": margin,
    }
    for calculation_id, expected in expected_values.items():
        entry = provenance[calculation_id]
        assert entry.calculation == calculation_id
        assert entry.value == expected

    milk_inputs = {item.name: item.value for item in provenance["revenue.milk"].inputs_used}
    assert milk_inputs == {
        "milking_cows": drivers["milking_cows"],
        "litres_per_cow": drivers["litres_per_cow"],
        "milk_price": drivers["milk_price"],
    }
    assert all(
        item.unit == FIELD_UNITS[item.name]
        for item in provenance["revenue.milk"].inputs_used
    )

    assert [item.name for item in provenance["costs.total"].inputs_used] == list(
        COST_CATEGORIES
    )
    cost_inputs = {item.name: item.value for item in provenance["costs.total"].inputs_used}
    for name in COST_CATEGORIES:
        assert cost_inputs[name] == drivers[name]

    # Provenance stays unrounded; published pl.summary lines use round_money.
    pl = _pl(farm_payload)
    assert provenance["revenue.milk"].value == milk
    assert pl["revenue"]["milk"] == round_money(milk)


def test_provenance_has_formula_metadata() -> None:
    provenance = explain_annual_pnl(FinancialInput.model_validate(SAMPLE))
    assert provenance["revenue.milk"].formula == (
        "milking_cows * litres_per_cow * milk_price"
    )
    assert provenance["revenue.total"].formula == (
        "revenue.milk + revenue.schemes + revenue.other"
    )
    assert provenance["profit.net"].formula == (
        "operating_income - operating_costs (revenue.total - costs.total)"
    )
    assert "operating_income" in provenance["profit.margin"].formula
