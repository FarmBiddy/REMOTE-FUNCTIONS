"""Irish capital allowances for farmers (TCA s.284, s.285D, s.658, s.658A; ADR-0053).

Allowances are given per tax year on qualifying cost (cost net of grants) from
the tax year of the spend: a full year's allowance in that year, no apportioning.
Rules are looked up by the spend date; an accelerated scheme outside its window
falls back to the normal allowance. Rates: ``docs/ie-rules.md`` §5.
"""

from __future__ import annotations

from datetime import date

from farm_functions.ie.rules import Rule

RULES: dict[str, tuple[Rule, ...]] = {
    "plant": (Rule("ca_plant_wear_tear", 12.5, date(2002, 12, 4), None, "TCA s.284(2)(ad)", "enacted"),),
    # Start of the current 7-year basis not confirmed; 2000 covers any register in use.
    "farm_buildings": (Rule("ca_farm_buildings", 15.0, date(2000, 1, 1), None, "TCA s.658", "enacted"),),
    "slurry_storage": (
        Rule("ca_slurry_storage", 50.0, date(2023, 1, 1), date(2029, 12, 31), "TCA s.658A", "enacted"),
    ),
    "farm_safety": (
        Rule("ca_farm_safety", 50.0, date(2021, 1, 1), date(2026, 12, 31), "TCA s.285D", "enacted"),
        Rule("ca_farm_safety", 50.0, date(2027, 1, 1), date(2029, 12, 31), "Finance (No. 2) Bill 2026 s.22", "announced"),
    ),
}
# Yearly rates (% of qualifying cost) from the tax year of the spend.
SCHEDULES: dict[str, tuple[float, ...]] = {
    "plant": (12.5,) * 8,
    "farm_buildings": (15.0,) * 6 + (10.0,),
    "slurry_storage": (50.0, 50.0),
    "farm_safety": (50.0, 50.0),
}


def fallback(kind: str, category: str) -> str | None:
    """Normal allowance for an accelerated scheme outside its window: slurry
    storage buildings are farm buildings, its Sch. 35A equipment and farm safety
    equipment are plant."""
    if kind == "farm_safety" or (kind == "slurry_storage" and category != "buildings"):
        return "plant"
    return "farm_buildings" if kind == "slurry_storage" else None


DEFAULT_FOR_CATEGORY = {"machinery": "plant", "buildings": "farm_buildings", "other": "none"}
# €500k tax-benefit cap per person (s.658A, s.285D): needs the tax estimate.
CAPS = {"slurry_storage": "ca_accelerated_cap", "farm_safety": "ca_accelerated_cap"}


def allowance_in_year(qualifying_cost: float, schedule: tuple[float, ...], year_number: int) -> tuple[float, float, float]:
    """(opening written-down value, allowance, closing) in year ``year_number`` (0 = spend year)."""
    cost = float(qualifying_cost)
    before = sum(schedule[: max(year_number, 0)])
    rate = schedule[year_number] if 0 <= year_number < len(schedule) else 0.0
    opening = cost * (100 - min(before, 100)) / 100
    allowance = cost * rate / 100
    return opening, allowance, opening - allowance


__all__ = ["CAPS", "DEFAULT_FOR_CATEGORY", "RULES", "SCHEDULES", "allowance_in_year", "fallback"]
