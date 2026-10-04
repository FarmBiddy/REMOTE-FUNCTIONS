"""Sector-agnostic cash-flow arithmetic.

Activity classification (operating / investing / financing) is a composition /
policy concern (ADR-0022 / D-CF1). Core only sums and nets already-monetary
amounts. No farm field names and no calendar.
"""

from typing import Literal

from farm_functions.core.aggregate import sum_amounts

CashDirection = Literal["in", "out"]
CashActivity = Literal["operating", "investing", "financing"]


def cash_section_net(inflows: float, outflows: float) -> float:
    """Net cash for one activity section: inflows − outflows."""
    return float(inflows) - float(outflows)


def net_cash_flow(cash_in: float, cash_out: float) -> float:
    """Overall net cash movement: total inflows − total outflows."""
    return cash_section_net(cash_in, cash_out)


def closing_cash(opening_cash: float, net: float) -> float:
    """Cash position roll-forward: opening + net movement = closing."""
    return float(opening_cash) + float(net)


def sum_cash_amounts(*values: float) -> float:
    """Sum explicit cash line amounts (alias of ``sum_amounts`` for clarity)."""
    return sum_amounts(*values)


__all__ = [
    "CashActivity",
    "CashDirection",
    "cash_section_net",
    "closing_cash",
    "net_cash_flow",
    "sum_cash_amounts",
]
