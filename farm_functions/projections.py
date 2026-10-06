"""Multi-year annual projection (ADR-0042).

Application layer: totals the 12-month base, applies per-year assumptions with
the Dairy line policy, then reuses loan amortisation, the asset register and
the period P&L composition. Cash, debt and net worth roll year to year.
"""

from __future__ import annotations

from typing import Any

from farm_functions.assets import assets_schedule, month_index
from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.growth import carry_forward, compound_indexes
from farm_functions.core.loans import amortisation_schedule, repricing_schedule
from farm_functions.core.ratios import coverage_ratio, per_unit
from farm_functions.core.rounding import round_money
from farm_functions.dairy.costs import HERD_LINKED_INCOME, OPERATING_COST_CATEGORIES, VARIABLE_COST_CATEGORIES
from farm_functions.dairy.monthly_statement import monthly_pl_summary
from farm_functions.schemas import PROJECTION_AMOUNT_LINES

_HERD_LINES = VARIABLE_COST_CATEGORIES + HERD_LINKED_INCOME


def _period(index: int) -> dict[str, Any]:
    return {"kind": "month", "year": index // 12, "month": index % 12 + 1}


def _debt_by_year(
    loans: list[tuple[int, int, list[dict[str, float]], float]], windows: list[tuple[int, int]]
) -> list[dict[str, float]]:
    """Interest, principal and closing balance per year for (drawn, first instalment, rows, balance).

    A loan owes nothing before its drawdown month (investment loans start later).
    """
    out = []
    for start, end in windows:
        interest = principal = balance = 0.0
        for drawn, first, rows, opening in loans:
            if end < drawn:
                continue
            interest += sum(r["interest"] for i, r in enumerate(rows) if start <= first + i <= end)
            principal += sum(r["principal"] for i, r in enumerate(rows) if start <= first + i <= end)
            paid = [r for i, r in enumerate(rows) if first + i <= end]
            balance += paid[-1]["closing_balance"] if paid else opening
        out.append({"interest": interest, "principal": principal, "balance": balance})
    return out


def plan_projection(
    *,
    base_pl_months: list[dict[str, Any]],
    opening_cash: float,
    milking_cows: float,
    years: int = 5,
    assumptions: dict[str, Any] | None = None,
    loans: list[dict[str, Any]] | None = None,
    assets: list[dict[str, Any]] | None = None,
    investments: list[dict[str, Any]] | None = None,
    land: float = 0.0,
    livestock: float = 0.0,
    min_cover: float | None = None,
) -> dict[str, Any]:
    """``plan.projection``: per-year P&L, cash, debt, balance sheet and flags."""
    a = assumptions or {}
    loans, assets, investments = loans or [], assets or [], investments or []

    # Base year: line totals of the 12 actual months.
    lines = [k for k in base_pl_months[0] if k not in ("year", "month", "milk_price", "loan_repayments")]
    base = {k: sum_amounts(*(m[k] for m in base_pl_months)) for k in lines}
    base_milk = sum_amounts(*(m["milk_litres"] * m["milk_price"] for m in base_pl_months))
    base_price = per_unit(base_milk, base["milk_litres"]) or 0.0
    last = max(month_index(m["year"], m["month"]) for m in base_pl_months)
    windows = [(last + 1 + 12 * k, last + 12 * (k + 1)) for k in range(years)]

    herd = compound_indexes(a.get("herd_pct", []), years)
    yield_ = compound_indexes(a.get("yield_pct", []), years)
    general = a.get("cost_inflation_pct", [])
    inflation = {
        c: compound_indexes(
            [
                (a.get("lines_inflation_pct", {}).get(c) or [])[y]
                if y < len((a.get("lines_inflation_pct", {}).get(c) or []))
                else (general[y] if y < len(general) else 0.0)
                for y in range(years)
            ],
            years,
        )
        for c in OPERATING_COST_CATEGORIES
    }
    price = carry_forward(a.get("milk_price", []), years, base_price)
    amounts = {k: carry_forward(v, years, 0.0) for k, v in a.get("lines_amount", {}).items()}
    drawings = carry_forward(a.get("drawings", []), years, 0.0)
    tax = carry_forward(a.get("tax", []), years, 0.0)
    off_farm = carry_forward(a.get("off_farm_income", []), years, 0.0)
    rate_shift = carry_forward(a.get("interest_rate_shift_pp", []), years, 0.0)

    def existing_rows(loan: dict[str, Any]) -> list[dict[str, float]]:
        """Variable loans reprice at the start of each projection year (ADR-0043)."""
        if not loan["variable"]:
            return amortisation_schedule(loan["balance"], loan["annual_rate"], loan["remaining_months"])
        first = month_index(loan["year"], loan["month"])
        steps = [(0, loan["annual_rate"])] + [
            (max(0, start - first), max(0.0, loan["annual_rate"] + shift / 100))
            for (start, _), shift in zip(windows, rate_shift)
        ]
        return repricing_schedule(loan["balance"], loan["remaining_months"], steps)

    # Debt: existing loans + investment loans (first instalment the month after purchase).
    # Existing loans are already drawn: they owe their balance from the start.
    loan_rows = [
        (
            windows[0][0] - 1,
            month_index(l["year"], l["month"]),
            existing_rows(l),
            l["balance"],
        )
        for l in loans
    ]
    new_assets = []
    capex = [0.0] * years
    proceeds = [0.0] * years
    effects = [dict.fromkeys(PROJECTION_AMOUNT_LINES, 0.0) for _ in range(years)]
    for inv in investments:
        y = inv["year"] - 1
        bought = windows[y][0]
        capex[y] += inv["amount"]
        new_assets.append(
            {
                "category": inv["category"], "cost": inv["amount"], "year": bought // 12,
                "month": bought % 12 + 1, "method": "straight_line",
                "life_months": inv["life_months"], "residual_value": 0.0, "annual_rate": None,
            }
        )
        if inv["loan"]:
            loan = inv["loan"]
            proceeds[y] += loan["amount"]
            rows = amortisation_schedule(loan["amount"], loan["annual_rate"], loan["remaining_months"])
            loan_rows.append((bought, bought + 1, rows, loan["amount"]))
        for later in range(y + 1, years):
            for line, delta in inv["annual_effects"].items():
                effects[later][line] += delta
    debt = _debt_by_year(loan_rows, windows)
    register = assets + new_assets

    cash = opening_cash
    out_years = []
    for y, (start, end) in enumerate(windows):
        drivers = {}
        for k in lines:
            value = base[k]
            if k in _HERD_LINES:
                value *= herd[y]
            if k in inflation:
                value *= inflation[k][y]
            if k in amounts:
                value = amounts[k][y]
            if k in effects[y]:
                value = max(0.0, value + effects[y][k])
            drivers[k] = value
        drivers["milk_litres"] = base["milk_litres"] * herd[y] * yield_[y]
        debt_service = debt[y]["interest"] + debt[y]["principal"]
        pl = monthly_pl_summary(milk_price=price[y], loan_repayments=debt_service, **drivers)
        surplus = pl["profit"]["net"]

        fixed = (
            assets_schedule(
                assets=register, from_year=start // 12, from_month=start % 12 + 1,
                to_year=end // 12, to_month=end % 12 + 1,
            )["total"]
            if register
            else {"depreciation": 0.0, "closing_nbv": 0.0}
        )
        net_cash = (
            surplus + off_farm[y] - drawings[y] - tax[y] - debt_service - capex[y] + proceeds[y]
        )
        opening, cash = cash, cash + net_cash
        cows = milking_cows * herd[y]
        dscr = coverage_ratio(surplus, debt_service)
        cover = coverage_ratio(surplus + off_farm[y] - drawings[y] - tax[y], debt_service)
        livestock_value = livestock * herd[y]
        net_worth = cash + fixed["closing_nbv"] + land + livestock_value - debt[y]["balance"]
        out_years.append(
            {
                "year": y + 1,
                "period": {"from": _period(start), "to": _period(end)},
                "assumptions_used": {
                    "milk_price": price[y],
                    "herd_index": round(herd[y], 4),
                    "yield_index": round(yield_[y], 4),
                    "cost_inflation_pct": general[y] if y < len(general) else 0.0,
                    "drawings": drawings[y],
                    "tax": tax[y],
                    "off_farm_income": off_farm[y],
                    "interest_rate_shift_pp": rate_shift[y],
                },
                "pl": {
                    "milk_litres": round_money(drivers["milk_litres"]),
                    "revenue": pl["revenue"],
                    "costs": pl["costs"],
                    "operating_surplus": round_money(surplus),
                    "depreciation": fixed["depreciation"],
                    "interest": round_money(debt[y]["interest"]),
                    "net_profit_before_tax": round_money(surplus - fixed["depreciation"] - debt[y]["interest"]),
                },
                "cash": {
                    "opening": round_money(opening),
                    "operating_surplus": round_money(surplus),
                    "off_farm_income": round_money(off_farm[y]),
                    "drawings": round_money(drawings[y]),
                    "tax": round_money(tax[y]),
                    "interest": round_money(debt[y]["interest"]),
                    "principal": round_money(debt[y]["principal"]),
                    "capex": round_money(capex[y]),
                    "new_loans": round_money(proceeds[y]),
                    "net": round_money(net_cash),
                    "closing": round_money(cash),
                },
                "debt": {
                    "closing_balance": round_money(debt[y]["balance"]),
                    "debt_service": round_money(debt_service),
                    "dscr": None if dscr is None else round_money(dscr),
                    "repayment_cover": None if cover is None else round_money(cover),
                },
                "balance_sheet": {
                    "cash": round_money(cash),
                    "fixed_assets": fixed["closing_nbv"],
                    "land": round_money(land),
                    "livestock": round_money(livestock_value),
                    "debt": round_money(debt[y]["balance"]),
                    "net_worth": round_money(net_worth),
                },
                "kpis": {
                    "milking_cows": round_money(cows),
                    "milk_price_c": round_money(price[y] * 100),
                    "costs_per_litre_c": _cents(pl["costs"]["total"], drivers["milk_litres"]),
                    "surplus_per_cow": _per(surplus, cows),
                },
                "flags": {
                    "negative_cash": cash < 0,
                    "below_min_cover": None if min_cover is None or dscr is None else dscr < min_cover,
                },
            }
        )
    first, last_month = last - 11, last
    return {
        "currency": "EUR",
        "base": {
            "period": {"from": _period(first), "to": _period(last_month)},
            "milk_litres": round_money(base["milk_litres"]),
            "milk_price_c": round_money(base_price * 100),
            "opening_cash": round_money(opening_cash),
        },
        "years": out_years,
    }


def _cents(amount: float, litres: float) -> float | None:
    value = per_unit(amount, litres)
    return None if value is None else round_money(value * 100)


def _per(amount: float, units: float) -> float | None:
    value = per_unit(amount, units)
    return None if value is None else round_money(value)
