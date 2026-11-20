"""``herd.valuation``: the herd and flock at a valuation date (ADR-0055).

Application layer: head × value per head for each group, on market value and
on Irish Revenue practice side by side, so the Platform never multiplies or
sums money. The totals are the livestock values ``pl.net``,
``tax.stock_relief`` and ``bs.summary`` take; which basis feeds which is the
Platform's choice (accounts and tax: Revenue practice; a bank's balance sheet
view: market).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.rounding import round_money
from farm_functions.ie import livestock_valuation as lv


def herd_valuation(*, year: int, month: int, groups: list[dict[str, Any]]) -> dict[str, Any]:
    on = date(year, month, 1)
    rows, rules = [], {}
    for g in groups:
        category, head = g["category"], g["head"]
        mature = lv.CATEGORIES[category][1]
        rule = lv.deemed_cost_rule(category, on)
        if not mature:
            rules[rule.rule_id] = rule
        unit = lv.revenue_practice_unit_value(category, g["unit_market_value"], g["unit_held_value"], rule.value)
        if not mature:
            basis = "deemed_cost_pct"
        elif g["unit_held_value"] > g["unit_market_value"]:
            basis = "written_down_to_market"
        else:
            basis = "held_value"
        rows.append(
            {
                "label": g["label"],
                "category": category,
                "head": head,
                "unit_market_value": round_money(g["unit_market_value"]),
                "market_value": round_money(head * g["unit_market_value"]),
                "unit_revenue_practice_value": round_money(unit),
                "revenue_practice_value": round_money(head * unit),
                "revenue_practice_basis": basis,
            }
        )
    return {
        "currency": "EUR",
        "jurisdiction": "IE",
        "as_of": {"kind": "month", "year": year, "month": month},
        "groups": rows,
        "total": {
            "head": sum(r["head"] for r in rows),
            "market_value": round_money(sum_amounts(*(r["market_value"] for r in rows))),
            "revenue_practice_value": round_money(sum_amounts(*(r["revenue_practice_value"] for r in rows))),
        },
        "rules_applied": [r.as_dict() for r in rules.values()],
    }


__all__ = ["herd_valuation"]
