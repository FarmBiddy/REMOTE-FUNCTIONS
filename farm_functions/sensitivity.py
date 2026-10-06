"""What-if scenarios, investments and milk-price break-evens (ADR-0029, ADR-0031).

Application layer: applies investments and shocks to the caller's monthly
drivers, reruns the normal monthly statements and cash roll-forward, and solves
the linear break-evens per scenario.
"""

from __future__ import annotations

from itertools import accumulate
from typing import Any

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.loans import amortisation_schedule
from farm_functions.core.ratios import coverage_ratio, per_unit
from farm_functions.core.rounding import round_money
from farm_functions.core.sensitivity import break_even_shift, min_shift_all_non_negative
from farm_functions.dairy.cash_flow import OPERATING_CASH_INFLOW_CATEGORIES
from farm_functions.dairy.costs import HERD_LINKED_INCOME, VARIABLE_COST_CATEGORIES
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
BASE = {
    "name": "base",
    "milk_price_c": 0.0,
    "milk_volume_pct": 0.0,
    "herd_pct": 0.0,
    "lines_pct": {},
    "investments": [],
}


def _split(item: dict[str, Any]) -> tuple[MonthlyPeriodIdentity, dict[str, float]]:
    lines = {k: v for k, v in item.items() if k not in _PERIOD_KEYS}
    return MonthlyPeriodIdentity(year=item["year"], month=item["month"]), lines


def _key(item: dict[str, Any]) -> tuple[int, int]:
    return item["year"], item["month"]


def _shift(period: tuple[int, int], months: int) -> tuple[int, int]:
    index = period[0] * 12 + period[1] - 1 + months
    return index // 12, index % 12 + 1


HERD_LINES = VARIABLE_COST_CATEGORIES + HERD_LINKED_INCOME


def _scale_lines(
    lines: dict[str, Any], lines_pct: dict[str, float], herd: float
) -> dict[str, Any]:
    """Herd-linked lines move with herd size (ADR-0033), then per-line % shocks."""
    out = {}
    for k, v in lines.items():
        if k in HERD_LINES:
            v = v * herd
        if k in lines_pct:
            v = v * (1 + lines_pct[k] / 100)
        out[k] = v
    return out


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


def _apply_investments(
    pl_months: list[dict[str, Any]],
    cf_months: list[dict[str, Any]],
    investments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Capex + loan drawdown in the purchase month; instalments and monthly effects after."""
    pl = {_key(m): dict(m) for m in pl_months}
    cf = {_key(m): dict(m) for m in cf_months}
    summaries = []
    for inv in investments:
        start = _key(inv)
        cf[start][inv["cash_line"]] += inv["amount"]
        loan_payment = None
        if inv["loan"]:
            loan = inv["loan"]
            cf[start]["loan_proceeds"] += loan["amount"]
            rows = amortisation_schedule(loan["amount"], loan["annual_rate"], loan["remaining_months"])
            loan_payment = rows[0]["payment"]
            for offset, row in enumerate(rows, 1):
                period = _shift(start, offset)
                if period in cf:
                    cf[period]["interest_paid"] += row["interest"]
                    cf[period]["loan_principal_repayments"] += row["principal"]
                if period in pl:
                    pl[period]["loan_repayments"] += row["payment"]
        effects = inv["monthly_effects"]
        for months in (pl, cf):
            for period, item in months.items():
                if period > start:
                    for line, delta in effects.items():
                        if line in item:
                            item[line] = max(0.0, item[line] + delta)
        benefit = sum_amounts(
            *(d if line in OPERATING_CASH_INFLOW_CATEGORIES else -d for line, d in effects.items())
        )
        summaries.append(
            {
                "period": {"kind": "month", "year": start[0], "month": start[1]},
                "amount": round_money(inv["amount"]),
                "loan_monthly_payment": loan_payment,
                "monthly_benefit": round_money(benefit),
                "simple_payback_months": (
                    round_money(inv["amount"] / benefit) if benefit > 0 else None
                ),
            }
        )
    return list(pl.values()), list(cf.values()), summaries


def _live(period: dict[str, Any], start: tuple[int, int] | None) -> bool:
    """Shocks and break-evens apply from ``start`` on (ADR-0040); earlier months are history."""
    return start is None or _key(period) >= start


def _price_c(avg_price: float, shift: float | None) -> float | None:
    """Break-even price in c/L; floored at 0 (0 = covered even at a zero price)."""
    return None if shift is None else round_money(max(0.0, avg_price + shift) * 100)


def _break_even(
    pl_months: list[dict[str, Any]],
    statements: list[dict[str, Any]],
    cash_months: list[dict[str, Any]],
    start: tuple[int, int] | None,
) -> tuple[float, dict[str, float | None]]:
    """Average milk price of the live months and the exact prices where surplus /
    lowest live month-end cash reach 0 when only live months' price moves."""
    litres = sum_amounts(*(i["milk_litres"] for i in pl_months if _live(i, start)))
    milk_revenue = sum_amounts(*(s["revenue"]["milk"] for s in statements if _live(s["period"], start)))
    avg_price = per_unit(milk_revenue, litres) or 0.0
    surplus = sum_amounts(*(s["profit"]["net"] for s in statements))
    live_cash = [m for m in cash_months if _live(m["period"], start)]
    cumulative_milk = list(accumulate(m["operating"]["inflows"]["lines"]["milk"] for m in live_cash))
    cash_shift = (
        min_shift_all_non_negative(
            [m["closing_cash"] for m in live_cash],
            [cum / avg_price for cum in cumulative_milk],
        )
        if avg_price and live_cash
        else None
    )
    return avg_price, {
        "surplus_milk_price_c": _price_c(avg_price, break_even_shift(surplus, litres)),
        "cash_milk_price_c": _price_c(avg_price, cash_shift),
    }


def _outcome(
    scenario: dict[str, Any],
    pl_months: list[dict[str, Any]],
    cf_months: list[dict[str, Any]],
    opening_cash: float,
    base_price: float,
    start: tuple[int, int] | None,
) -> dict[str, Any]:
    pl_months, cf_months, investments = _apply_investments(
        pl_months, cf_months, scenario["investments"]
    )
    herd = 1 + scenario["herd_pct"] / 100
    # Litres move with herd size and with yield per cow (milk_volume_pct).
    volume = herd * (1 + scenario["milk_volume_pct"] / 100)
    price_shift = scenario["milk_price_c"] / 100
    # Milk cheques scale with price × volume (ADR-0029); no P&L price → no cash price effect.
    cash_milk = volume * (max(0.0, base_price + price_shift) / base_price if base_price else 1.0)

    shocked_pl = []
    for item in pl_months:
        if not _live(item, start):
            shocked_pl.append(item)
            continue
        lines = _scale_lines(item, scenario["lines_pct"], herd)
        lines["milk_price"] = max(0.0, item["milk_price"] + price_shift)
        lines["milk_litres"] = item["milk_litres"] * volume
        shocked_pl.append(lines)
    shocked_cf = [
        {**_scale_lines(item, scenario["lines_pct"], herd), "milk": item["milk"] * cash_milk}
        if _live(item, start)
        else item
        for item in cf_months
    ]

    statements = _statements(shocked_pl)
    surplus = sum_amounts(*(s["profit"]["net"] for s in statements))
    repayments = sum_amounts(*(s["finance"]["loan_repayments"] for s in statements))
    dscr = coverage_ratio(surplus, repayments)
    cash = _cash(shocked_cf, opening_cash)
    # Lowest cash / overdraft months look forward from ``start`` (history is fixed).
    live_cash = [m for m in cash["months"] if _live(m["period"], start)] or cash["months"]
    lowest = min(live_cash, key=lambda m: m["closing_cash"])
    _, break_even = _break_even(shocked_pl, statements, cash["months"], start)
    return {
        "name": scenario["name"],
        "shocks": {
            k: scenario[k] for k in ("milk_price_c", "milk_volume_pct", "herd_pct", "lines_pct")
        },
        "investments": investments,
        "surplus": round_money(surplus),
        "loan_repayments": round_money(repayments),
        "dscr": None if dscr is None else round_money(dscr),
        "closing_cash": cash["closing_cash"],
        "lowest_cash": {"period": lowest["period"], "amount": lowest["closing_cash"]},
        "overdraft_months": sum(1 for m in live_cash if m["closing_cash"] < 0),
        "break_even": break_even,
    }


def risk_sensitivity(
    *,
    pl_months: list[dict[str, Any]],
    cf_months: list[dict[str, Any]],
    opening_cash: float,
    scenarios: list[dict[str, Any]],
    shocks_from_year: int | None = None,
    shocks_from_month: int | None = None,
) -> dict[str, Any]:
    """``risk.sensitivity``: base + scenarios, each with its milk-price break-evens."""
    start = None if shocks_from_year is None else (shocks_from_year, shocks_from_month)
    base_price, _ = _break_even(
        pl_months, _statements(pl_months), _cash(cf_months, opening_cash)["months"], start
    )
    named = [{**s, "name": s["name"] or f"scenario {i}"} for i, s in enumerate(scenarios, 1)]
    return {
        "currency": "EUR",
        "shocks_from": None if start is None else {"kind": "month", "year": start[0], "month": start[1]},
        "milk_price_c": round_money(base_price * 100),
        "scenarios": [
            _outcome(s, pl_months, cf_months, opening_cash, base_price, start) for s in [BASE, *named]
        ],
    }
