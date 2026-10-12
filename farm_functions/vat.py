"""``vat.flat_rate``: Irish flat-rate VAT addition on milk and cattle sales (ADR-0053).

Application layer: takes the same months as ``pl.months`` (prices ex-VAT) and
returns the addition a flat-rate farmer receives on top, month by month, with
the rule applied. VAT-registered farmers get none.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.rounding import round_money
from farm_functions.dairy.revenue import milk_revenue_from_litres
from farm_functions.ie import FLAT_RATE_ADDITION, flat_rate_addition, rule_at


def vat_flat_rate(*, months: list[dict[str, Any]], vat_registered: bool = False) -> dict[str, Any]:
    rows, rules = [], {}
    totals = {"milk": 0.0, "cattle_sales": 0.0, "addition": 0.0}
    for item in sorted(months, key=lambda m: (m["year"], m["month"])):
        milk = milk_revenue_from_litres(item["milk_litres"], item["milk_price"])
        cattle = float(item.get("cattle_sales", 0))
        base = sum_amounts(milk, cattle)
        rule = None if vat_registered else rule_at(FLAT_RATE_ADDITION, date(item["year"], item["month"], 1))
        addition = 0.0 if rule is None else flat_rate_addition(base, rule.value)
        if rule is not None:
            rules[rule.start] = rule
        totals["milk"] += milk
        totals["cattle_sales"] += cattle
        totals["addition"] += addition
        rows.append(
            {
                "period": {"kind": "month", "year": item["year"], "month": item["month"]},
                "milk": round_money(milk),
                "cattle_sales": round_money(cattle),
                "base": round_money(base),
                "rate_pct": None if rule is None else rule.value,
                "addition": round_money(addition),
            }
        )
    return {
        "currency": "EUR",
        "jurisdiction": "IE",
        "from": rows[0]["period"],
        "to": rows[-1]["period"],
        "month_count": len(rows),
        "vat_registered": vat_registered,
        "months": rows,
        "total": {
            "milk": round_money(totals["milk"]),
            "cattle_sales": round_money(totals["cattle_sales"]),
            "base": round_money(totals["milk"] + totals["cattle_sales"]),
            "addition": round_money(totals["addition"]),
        },
        "rules_applied": [rules[k].as_dict() for k in sorted(rules)],
    }


__all__ = ["vat_flat_rate"]
