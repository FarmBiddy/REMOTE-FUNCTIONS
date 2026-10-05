"""What-if scenarios and milk-price break-evens (ADR-0029).

Application layer: shocks the caller's monthly drivers, reruns the normal
monthly statements and cash roll-forward, and solves the linear break-evens.
"""

from __future__ import annotations

from itertools import accumulate
from typing import Any

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.ratios import coverage_ratio, per_unit
from farm_functions.core.rounding import round_money
from farm_functions.core.sensitivity import break_even_shift, min_shift_all_non_negative
from farm_functions.domain import (
    MonthlyDairyCashFlowModel,
    MonthlyDairyStatementModel,
    MonthlyPeriodIdentity,
    MultiMonthDairyCashFlowModel,
    MultiMonthDairyStatementModel,
    calculate_multi_month_dairy_cash_flow,
    calculate_multi_month_dairy_statements,
)
from farm_functions.schemas import MonthlyDairyCashFlowInput, MonthlyDairyFinancialInput

_PERIOD_KEYS = ("year", "month")
BASE = {"name": "base", "milk_price_c": 0.0, "milk_volume_pct": 0.0, "lines_pct": {}}


def _split(item: dict[str, Any]) -> tuple[MonthlyPeriodIdentity, dict[str, float]]:
    lines = {k: v for k, v in item.items() if k not in _PERIOD_KEYS}
    return MonthlyPeriodIdentity(year=item["year"], month=item["month"]), lines


def _scale_lines(lines: dict[str, float], lines_pct: dict[str, float]) -> dict[str, float]:
    return {k: v * (1 + lines_pct[k] / 100) if k in lines_pct else v for k, v in lines.items()}


def _statements(pl_months: list[dict[str, Any]]) -> list[dict[str, Any]]:
    envelopes = []
    for item in pl_months:
        period, lines = _split(item)
        envelopes.append(
            MonthlyDairyStatementModel(
                period=period, inputs=MonthlyDairyFinancialInput.model_validate(lines)
            )
        )
    result = calculate_multi_month_dairy_statements(MultiMonthDairyStatementModel(months=envelopes))
    return result.model_dump()["months"]


def _cash(cf_months: list[dict[str, Any]], opening_cash: float) -> dict[str, Any]:
    envelopes = []
    for item in cf_months:
        period, lines = _split(item)
        envelopes.append(
            MonthlyDairyCashFlowModel(
                period=period, inputs=MonthlyDairyCashFlowInput.model_validate(lines)
            )
        )
    model = MultiMonthDairyCashFlowModel(opening_cash=opening_cash, months=envelopes)
    return calculate_multi_month_dairy_cash_flow(model).model_dump()


def _outcome(
    scenario: dict[str, Any],
    pl_months: list[dict[str, Any]],
    cf_months: list[dict[str, Any]],
    opening_cash: float,
    avg_price: float,
) -> dict[str, Any]:
    volume = 1 + scenario["milk_volume_pct"] / 100
    price_shift = scenario["milk_price_c"] / 100
    # Milk cheques scale with price × volume (ADR-0029); no P&L price → no cash price effect.
    cash_milk = volume * (max(0.0, avg_price + price_shift) / avg_price if avg_price else 1.0)

    shocked_pl = []
    for item in pl_months:
        lines = _scale_lines(item, scenario["lines_pct"])
        lines["milk_price"] = max(0.0, item["milk_price"] + price_shift)
        lines["milk_litres"] = item["milk_litres"] * volume
        shocked_pl.append(lines)
    shocked_cf = [
        {**_scale_lines(item, scenario["lines_pct"]), "milk": item["milk"] * cash_milk}
        for item in cf_months
    ]

    statements = _statements(shocked_pl)
    surplus = sum_amounts(*(s["profit"]["net"] for s in statements))
    repayments = sum_amounts(*(s["finance"]["loan_repayments"] for s in statements))
    dscr = coverage_ratio(surplus, repayments)
    cash = _cash(shocked_cf, opening_cash)
    lowest = min(cash["months"], key=lambda m: m["closing_cash"])
    return {
        "name": scenario["name"],
        "shocks": {k: scenario[k] for k in ("milk_price_c", "milk_volume_pct", "lines_pct")},
        "surplus": round_money(surplus),
        "loan_repayments": round_money(repayments),
        "dscr": None if dscr is None else round_money(dscr),
        "closing_cash": cash["closing_cash"],
        "lowest_cash": {"period": lowest["period"], "amount": lowest["closing_cash"]},
        "overdraft_months": sum(1 for m in cash["months"] if m["closing_cash"] < 0),
    }


def _price_c(avg_price: float, shift: float | None) -> float | None:
    """Break-even price in c/L; floored at 0 (0 = covered even at a zero price)."""
    return None if shift is None else round_money(max(0.0, avg_price + shift) * 100)


def risk_sensitivity(
    *,
    pl_months: list[dict[str, Any]],
    cf_months: list[dict[str, Any]],
    opening_cash: float,
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    """``risk.sensitivity``: base + scenarios, and milk-price break-evens."""
    statements = _statements(pl_months)
    litres = sum_amounts(*(item["milk_litres"] for item in pl_months))
    milk_revenue = sum_amounts(*(s["revenue"]["milk"] for s in statements))
    avg_price = per_unit(milk_revenue, litres) or 0.0
    surplus = sum_amounts(*(s["profit"]["net"] for s in statements))

    cash_months = _cash(cf_months, opening_cash)["months"]
    cumulative_milk = list(accumulate(m["operating"]["inflows"]["lines"]["milk"] for m in cash_months))
    cash_shift = (
        min_shift_all_non_negative(
            [m["closing_cash"] for m in cash_months],
            [cum / avg_price for cum in cumulative_milk],
        )
        if avg_price
        else None
    )
    named = [{**s, "name": s["name"] or f"scenario {i}"} for i, s in enumerate(scenarios, 1)]
    return {
        "currency": "EUR",
        "milk_price_c": round_money(avg_price * 100),
        "break_even": {
            "surplus_milk_price_c": _price_c(avg_price, break_even_shift(surplus, litres)),
            "cash_milk_price_c": _price_c(avg_price, cash_shift),
        },
        "scenarios": [
            _outcome(s, pl_months, cf_months, opening_cash, avg_price) for s in [BASE, *named]
        ],
    }
