"""Fixed asset register: depreciation and net book value over a period (ADR-0037).

Application layer: maps calendar months to months held and builds the fixed
asset note (opening NBV + additions − depreciation = closing NBV) per asset,
per category and in total.
"""

from __future__ import annotations

from typing import Any

from farm_functions.core.depreciation import reducing_balance_nbv, straight_line_nbv
from farm_functions.core.rounding import round_money

CATEGORIES = ("machinery", "buildings", "other")
_FIELDS = ("opening_nbv", "additions", "depreciation", "closing_nbv")


def _index(year: int, month: int) -> int:
    return year * 12 + month - 1


def _nbv(asset: dict[str, Any], end_index: int) -> float:
    """NBV at the end of month ``end_index`` (cost before any month is depreciated)."""
    held = end_index - _index(asset["year"], asset["month"]) + 1
    if asset["method"] == "straight_line":
        return straight_line_nbv(asset["cost"], asset["residual_value"], asset["life_months"], held)
    return reducing_balance_nbv(asset["cost"], asset["annual_rate"], held)


def _note(asset: dict[str, Any], start: int, end: int) -> dict[str, float]:
    acquired = _index(asset["year"], asset["month"])
    if acquired > end:  # bought after the period: not held yet
        return dict.fromkeys(_FIELDS, 0.0)
    opening = round_money(_nbv(asset, start - 1)) if acquired < start else 0.0
    additions = round_money(asset["cost"]) if acquired >= start else 0.0
    closing = round_money(_nbv(asset, end))
    # Derived from published figures so the note reconciles to the cent.
    depreciation = round_money(opening + additions - closing)
    return {"opening_nbv": opening, "additions": additions, "depreciation": depreciation, "closing_nbv": closing}


def _total(notes: list[dict[str, float]]) -> dict[str, float]:
    return {f: round_money(sum(n[f] for n in notes)) for f in _FIELDS}


def assets_schedule(
    *,
    assets: list[dict[str, Any]],
    from_year: int,
    from_month: int,
    to_year: int,
    to_month: int,
) -> dict[str, Any]:
    """``assets.schedule``: fixed asset note per asset (input order), category and total."""
    start, end = _index(from_year, from_month), _index(to_year, to_month)
    notes = [_note(asset, start, end) for asset in assets]
    return {
        "currency": "EUR",
        "from": {"kind": "month", "year": from_year, "month": from_month},
        "to": {"kind": "month", "year": to_year, "month": to_month},
        "assets": [{"category": a["category"], **n} for a, n in zip(assets, notes)],
        "by_category": {
            c: _total([n for a, n in zip(assets, notes) if a["category"] == c]) for c in CATEGORIES
        },
        "total": _total(notes),
    }
