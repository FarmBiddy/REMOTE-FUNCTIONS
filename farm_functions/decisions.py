"""Farm decision tools, independent of the enterprise (ADR-0045, ADR-0046).

Application layer: partial budget for a change to the farm (rent land, contract
rearing, buy vs grow feed …) and investment appraisal (NPV, IRR, discounted
payback). Inputs are plain amounts, so the tools serve any enterprise.
"""

from __future__ import annotations

from typing import Any

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.investment import annual_capital_charge, discounted_payback, irr, npv
from farm_functions.core.ratios import per_unit
from farm_functions.core.rounding import round_margin_pct, round_money

_SIDES = {
    "gains": ("added_income", "reduced_costs"),
    "losses": ("added_costs", "reduced_income"),
}


def _items(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "items": [{"label": i["label"], "amount": round_money(i["amount"])} for i in items],
        "total": round_money(sum_amounts(*(i["amount"] for i in items))),
    }


def partial_budget(
    *,
    added_income: list[dict[str, Any]] | None = None,
    reduced_costs: list[dict[str, Any]] | None = None,
    added_costs: list[dict[str, Any]] | None = None,
    reduced_income: list[dict[str, Any]] | None = None,
    capital: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """``decision.partial_budget``: annual net effect of a change (gains − losses)."""
    groups = {
        "added_income": added_income or [],
        "reduced_costs": reduced_costs or [],
        "added_costs": added_costs or [],
        "reduced_income": reduced_income or [],
    }
    sections = {name: _items(items) for name, items in groups.items()}
    gains = sum_amounts(*(sections[n]["total"] for n in _SIDES["gains"]))
    operating_losses = sum_amounts(*(sections[n]["total"] for n in _SIDES["losses"]))
    operating_change = gains - operating_losses

    capital_out = None
    capital_charge = 0.0
    if capital:
        depreciation, interest = annual_capital_charge(
            capital["amount"], capital["life_years"], capital["annual_rate"]
        )
        capital_charge = depreciation + interest
        payback = per_unit(capital["amount"], operating_change) if operating_change > 0 else None
        roi = per_unit(operating_change - depreciation, capital["amount"])
        capital_out = {
            "amount": round_money(capital["amount"]),
            "life_years": capital["life_years"],
            "annual_rate": capital["annual_rate"],
            "depreciation": round_money(depreciation),
            "interest": round_money(interest),
            "annual_charge": round_money(capital_charge),
            "simple_payback_years": None if payback is None else round_money(payback),
            "return_on_investment_pct": None if roi is None else round_margin_pct(roi * 100),
        }

    net = operating_change - capital_charge
    return {
        "currency": "EUR",
        **sections,
        "gains": round_money(gains),
        "losses": round_money(operating_losses + capital_charge),
        "operating_change": round_money(operating_change),
        "capital": capital_out,
        "net_change": round_money(net),
        "worthwhile": net > 0,
    }


def investment_appraisal(
    *,
    amount: float,
    discount_rate: float,
    annual_benefit: float | None = None,
    life_years: int | None = None,
    cash_flows: list[float] | None = None,
    residual_value: float = 0.0,
) -> dict[str, Any]:
    """``decision.investment``: NPV, IRR, paybacks and the discounted schedule."""
    benefits = list(cash_flows) if cash_flows else [annual_benefit] * life_years
    benefits[-1] += residual_value
    flows = [-amount, *benefits]
    value = npv(discount_rate, flows)
    rate = irr(flows)
    payback = discounted_payback(discount_rate, flows)
    simple = discounted_payback(0.0, flows)
    present_benefits = value + amount
    schedule, cumulative = [], -amount
    for year, flow in enumerate(benefits, 1):
        factor = 1 / (1 + discount_rate) ** year
        cumulative += flow * factor
        schedule.append(
            {
                "year": year,
                "cash_flow": round_money(flow),
                "discount_factor": round(factor, 6),
                "present_value": round_money(flow * factor),
                "cumulative_present_value": round_money(cumulative),
            }
        )
    index = per_unit(present_benefits, amount)
    return {
        "currency": "EUR",
        "amount": round_money(amount),
        "discount_rate": discount_rate,
        "life_years": len(benefits),
        "residual_value": round_money(residual_value),
        "npv": round_money(value),
        "irr_pct": None if rate is None else round_margin_pct(rate * 100),
        "simple_payback_years": None if simple is None else round_money(simple),
        "discounted_payback_years": None if payback is None else round_money(payback),
        "profitability_index": None if index is None else round(index, 4),
        "worthwhile": value > 0,
        "years": schedule,
    }
