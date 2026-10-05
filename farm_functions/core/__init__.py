"""Core Financial Engine: sector-agnostic money operations.

Must not import Agriculture, Dairy, or farm field catalogues.
"""

from farm_functions.core.aggregate import sum_amounts
from farm_functions.core.cash import (
    CashActivity,
    CashDirection,
    cash_section_net,
    closing_cash,
    net_cash_flow,
    sum_cash_amounts,
)
from farm_functions.core.forecast import (
    latest_non_zero,
    run_rate,
    run_rate_factors,
    seasonal_projection,
)
from farm_functions.core.loans import (
    AmortisationRow,
    amortisation_schedule,
    annuity_payment,
)
from farm_functions.core.ratios import coverage_ratio, per_unit
from farm_functions.core.rounding import (
    round_margin_pct,
    round_margin_ratio,
    round_money,
)
from farm_functions.core.surplus import net_profit, profit_margin, profit_margin_pct

__all__ = [
    "AmortisationRow",
    "CashActivity",
    "CashDirection",
    "amortisation_schedule",
    "annuity_payment",
    "cash_section_net",
    "closing_cash",
    "coverage_ratio",
    "latest_non_zero",
    "net_cash_flow",
    "net_profit",
    "profit_margin",
    "per_unit",
    "profit_margin_pct",
    "round_margin_pct",
    "round_margin_ratio",
    "round_money",
    "run_rate",
    "run_rate_factors",
    "seasonal_projection",
    "sum_amounts",
    "sum_cash_amounts",
]
