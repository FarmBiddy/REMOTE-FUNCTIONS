"""Compatibility re-exports. Canonical implementation: ``farm_functions.core.rounding``."""

from farm_functions.core.rounding import (
    MARGIN_PCT_PLACES,
    MARGIN_RATIO_PLACES,
    MONEY_PLACES,
    round_margin_pct,
    round_margin_ratio,
    round_money,
)

__all__ = [
    "MARGIN_PCT_PLACES",
    "MARGIN_RATIO_PLACES",
    "MONEY_PLACES",
    "round_margin_pct",
    "round_margin_ratio",
    "round_money",
]
