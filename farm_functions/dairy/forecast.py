"""Dairy forecast line policy (ADR-0026): which lines recur, carry, or are known-only.

Operating lines recur seasonally. Prices carry the latest observed value.
Finance, investing and financing lines are one-offs: projected only when given,
except household drawings, which recur monthly (ADR-0030).
"""

from farm_functions.dairy.cash_flow import (
    OPERATING_CASH_INFLOW_CATEGORIES,
    OPERATING_CASH_OUTFLOW_CATEGORIES,
)

PL_PRICE_LINES = ("milk_price",)
PL_KNOWN_ONLY_LINES = ("loan_repayments",)
CASH_RECURRING_LINES = (
    OPERATING_CASH_INFLOW_CATEGORIES + OPERATING_CASH_OUTFLOW_CATEGORIES + ("household_drawings",)
)

__all__ = ["CASH_RECURRING_LINES", "PL_KNOWN_ONLY_LINES", "PL_PRICE_LINES"]
