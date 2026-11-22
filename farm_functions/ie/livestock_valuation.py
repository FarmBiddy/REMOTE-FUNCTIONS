"""Irish farm livestock valuation practice (ADR-0055).

Trading stock is valued at the lower of cost and market value. For livestock
Revenue accepts a deemed cost (Revenue practice, not statute: "Taxation issues
for milk production partnerships", Appendix 2, reproduced in the SCSI Farm
Stocktaking Valuations paper 2020, Appendix 3; IFAC practice notes):

- immature animals, home-bred or bought young: a % of market value at the
  accounting date (cattle 60%, sheep and pigs 75%), revalued each year;
- mature breeding animals: held at the value fixed when they matured
  (home-bred: the % of market value at the first accounting date after
  maturity; bought: purchase price), written down to market value if lower.

The held value is Platform history. Sources: ``docs/ie-rules.md`` §4A. ``from``
dates mark the start of the researched window (2024).
"""

from __future__ import annotations

from datetime import date

from farm_functions.ie.rules import Rule, rule_at

_START, _END = date(2024, 1, 1), date(2027, 12, 31)
_REF = "Revenue practice (milk production partnerships guidance App. 2; SCSI 2020 App. 3)"

DEEMED_COST: dict[str, tuple[Rule, ...]] = {
    "cattle": (Rule("livestock_deemed_cost_cattle_pct", 60.0, _START, _END, _REF, "practice"),),
    "sheep": (Rule("livestock_deemed_cost_sheep_pct", 75.0, _START, _END, _REF, "practice"),),
    "pigs": (Rule("livestock_deemed_cost_pigs_pct", 75.0, _START, _END, _REF, "practice"),),
}

# category: (species, mature breeding stock?)
CATEGORIES: dict[str, tuple[str, bool]] = {
    "dairy_cows": ("cattle", True),
    "suckler_cows": ("cattle", True),
    "stock_bulls": ("cattle", True),
    "heifers": ("cattle", False),
    "calves": ("cattle", False),
    "weanlings": ("cattle", False),
    "stores": ("cattle", False),
    "finishing_cattle": ("cattle", False),
    "breeding_ewes": ("sheep", True),
    "rams": ("sheep", True),
    "lambs": ("sheep", False),
    "other_sheep": ("sheep", False),
    "pigs": ("pigs", False),
}
MATURE = tuple(c for c, (_, mature) in CATEGORIES.items() if mature)


def deemed_cost_rule(category: str, on: date) -> Rule | None:
    return rule_at(DEEMED_COST[CATEGORIES[category][0]], on)


def revenue_practice_unit_value(category: str, unit_market_value: float, unit_held_value: float | None, pct: float) -> float:
    """Value per head on Revenue practice: held value capped at market for
    mature breeding stock, else the deemed-cost % of market value."""
    if CATEGORIES[category][1]:
        return min(unit_held_value, unit_market_value)
    return unit_market_value * pct / 100


__all__ = ["CATEGORIES", "DEEMED_COST", "MATURE", "deemed_cost_rule", "revenue_practice_unit_value"]
