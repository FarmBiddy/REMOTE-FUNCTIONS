"""Banker's rounding (round half to even) for annual P&L outputs.

Formulas in farm_functions.calcs remain full precision. These helpers are applied
only when publishing money or margin on the API / pl.summary payload.
"""

from decimal import ROUND_HALF_EVEN, Decimal

MONEY_PLACES = Decimal("0.01")
MARGIN_RATIO_PLACES = Decimal("0.0001")
MARGIN_PCT_PLACES = Decimal("0.01")


def _quantize(value: float, places: Decimal) -> float:
    return float(Decimal(str(value)).quantize(places, rounding=ROUND_HALF_EVEN))


def round_money(value: float) -> float:
    """EUR amounts: 2 decimal places, round half to even."""
    return _quantize(value, MONEY_PLACES)


def round_margin_ratio(value: float) -> float:
    """Profit margin as a 0–1 ratio: 4 decimal places, round half to even."""
    return _quantize(value, MARGIN_RATIO_PLACES)


def round_margin_pct(value: float) -> float:
    """Profit margin as a percentage: 2 decimal places, round half to even."""
    return _quantize(value, MARGIN_PCT_PLACES)
