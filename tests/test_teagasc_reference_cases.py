"""Published Teagasc figures as reference cases (Teagasc NFS 2023-2025, Outlook 2026).

Cases live in test-data/golden/teagasc_reference_cases.json. Each case maps the
published lines onto engine inputs, runs kpi.summary (and pl.net), and asserts
that engine result - published figure equals the documented `known_differences`
for that figure, to the cent. A difference is either a definition the engine
does not have yet or a published table that does not add up; both are named in
the JSON. When the engine changes a definition, these tests say exactly which
published figure moved and by how much.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from farm_functions.rounding import round_money
from farm_functions.runner import run_function

CASES_PATH = (
    Path(__file__).resolve().parents[1] / "test-data" / "golden" / "teagasc_reference_cases.json"
)
PAYLOAD = json.loads(CASES_PATH.read_text(encoding="utf-8"))
WHOLE_FARM = PAYLOAD["nfs_whole_farm_cases"]
PER_LITRE = PAYLOAD["nfs_per_litre_cases"]

# Per-litre cases run on a scaled farm: c/L results do not depend on the volume.
SCALED_LITRES = 1_000_000

# NFS per-litre groups → one engine line of the same class (direct = engine variable cost).
PER_LITRE_LINES = {
    "concentrates": "feed",
    "pasture_forage": "fertiliser",
    "other_direct": "vet",
    "electricity_fuel": "electricity",
    "hired_labour": "labour",
    "rent": "rent_lease",
    "remaining_fixed": "other_operating_costs",
}


def _spread(amount: float) -> list[float]:
    """An annual amount in whole cents over Jan–Dec: equal months, the remainder in December.

    Every month is an exact cent amount, so the monthly statements' publish rounding
    cannot move the annual figures and the cases test definitions only.
    """
    cents = round(amount * 100)
    month = cents // 12
    return [month / 100] * 11 + [(cents - 11 * month) / 100]


def _months(year: int, milk_value: float, milk_price: float, annual: dict[str, float]) -> list[dict]:
    """Annual figures as 12 calendar months; the engine sums them back.

    Litres Jan–Nov are a multiple of 100 (x a 4-decimal price = whole cents);
    December's litres make the year's milk value exact.
    """
    litres = [100 * int(milk_value / milk_price / 12 // 100)] * 11
    litres.append((milk_value - sum(litres) * milk_price) / milk_price)
    lines = {name: _spread(amount) for name, amount in annual.items()}
    return [
        {
            "year": year,
            "month": month,
            "milk_litres": litres[month - 1],
            "milk_price": milk_price,
            **{name: values[month - 1] for name, values in lines.items()},
        }
        for month in range(1, 13)
    ]


def _expected_difference(case: dict, figure: str) -> float:
    return round_money(sum(d["amount"] for d in case["known_differences"].get(figure, [])))


def _ok(function: str, payload: dict) -> dict:
    response = run_function(function, payload)
    assert response["status"] == "ok", response
    return response["result"]


# --- Whole farm (NFS Appendix 1) -------------------------------------------------


def _whole_farm_inputs(case: dict) -> tuple[list[dict], dict]:
    data = case["input"]
    months = _months(data["year"], data["milk_value"], data["milk_price"], data["annual"])
    return months, data["period_totals"]


@pytest.mark.parametrize("case", WHOLE_FARM, ids=[c["name"] for c in WHOLE_FARM])
@pytest.mark.parametrize(
    "figure", ["gross_output", "direct_costs", "overhead_costs", "family_farm_income"]
)
def test_whole_farm_figure_differs_from_published_only_by_known_differences(
    case: dict, figure: str
) -> None:
    months, totals = _whole_farm_inputs(case)
    result = _ok(
        "kpi.summary",
        {
            "months": months,
            "milking_cows": case["input"]["milking_cows"],
            "hectares": case["input"]["hectares"],
            **totals,
        },
    )
    engine = result["teagasc"][figure]
    assert round_money(engine - case["published"][figure]) == _expected_difference(case, figure)


@pytest.mark.parametrize("case", WHOLE_FARM, ids=[c["name"] for c in WHOLE_FARM])
def test_whole_farm_family_farm_income_is_net_profit_before_tax(case: dict) -> None:
    """ADR-0054: Teagasc family farm income = pl.net net profit before tax."""
    months, totals = _whole_farm_inputs(case)
    kpis = _ok(
        "kpi.summary",
        {"months": months, "milking_cows": case["input"]["milking_cows"], **totals},
    )
    net = _ok("pl.net", {"months": months, **totals})
    assert kpis["teagasc"]["family_farm_income"] == net["net_profit_before_tax"]


@pytest.mark.parametrize("case", WHOLE_FARM, ids=[c["name"] for c in WHOLE_FARM])
def test_whole_farm_known_differences_are_explained(case: dict) -> None:
    for figure, differences in case["known_differences"].items():
        assert figure in case["published"], figure
        for difference in differences:
            assert difference["reason"].strip(), (figure, difference)


# --- Per litre (NFS dairy enterprise factsheet, Outlook Table A5) ----------------


def _per_litre_result(case: dict) -> dict:
    lines = case["lines_c"]
    euros = lambda cents: cents * SCALED_LITRES / 100  # noqa: E731
    gross_output = euros(lines["gross_output"])
    if case["milk_price_c"] is None:
        milk_price = lines["gross_output"] / 100
        annual: dict[str, float] = {}
    else:
        # Output beyond milk (calves, culls) goes on the livestock sales line.
        milk_price = case["milk_price_c"] / 100
        annual = {"cattle_sales": gross_output - euros(case["milk_price_c"])}
    annual.update({engine: euros(lines[nfs]) for nfs, engine in PER_LITRE_LINES.items()})
    return _ok(
        "kpi.summary",
        {
            "months": _months(2024, SCALED_LITRES * milk_price, milk_price, annual),
            "milking_cows": 100,
            "depreciation": euros(lines["depreciation"]),
        },
    )


PER_LITRE_FIGURES = {
    "direct_costs": lambda r: r["teagasc"]["per_litre_c"]["direct_costs"],
    "fixed_costs": lambda r: r["teagasc"]["per_litre_c"]["fixed_costs"],
    "total_costs": lambda r: r["teagasc"]["per_litre_c"]["total_costs"],
    "net_margin": lambda r: r["teagasc"]["per_litre_c"]["net_margin"],
    "gross_margin": lambda r: r["per_litre_c"]["gross_margin"],
}


@pytest.mark.parametrize("case", PER_LITRE, ids=[c["name"] for c in PER_LITRE])
@pytest.mark.parametrize("figure", sorted(PER_LITRE_FIGURES))
def test_per_litre_figure_differs_from_published_only_by_known_differences(
    case: dict, figure: str
) -> None:
    if figure not in case["published"]:
        pytest.skip(f"{case['name']} does not publish {figure}")
    engine = PER_LITRE_FIGURES[figure](_per_litre_result(case))
    assert round_money(engine - case["published"][figure]) == _expected_difference(case, figure)


@pytest.mark.parametrize("case", PER_LITRE, ids=[c["name"] for c in PER_LITRE])
def test_per_litre_gross_output_matches_published(case: dict) -> None:
    result = _per_litre_result(case)
    assert result["teagasc"]["per_litre_c"]["gross_output"] == case["lines_c"]["gross_output"]
