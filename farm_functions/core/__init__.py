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
from farm_functions.core.depreciation import reducing_balance_nbv, straight_line_nbv
from farm_functions.core.forecast import (
    latest_non_zero,
    run_rate,
    run_rate_factors,
    seasonal_projection,
)
from farm_functions.core.growth import carry_forward, compound_indexes
from farm_functions.core.loans import (
    AmortisationRow,
    amortisation_schedule,
    annuity_payment,
    annuity_principal,
)
from farm_functions.core.ratios import coverage_ratio, per_unit
from farm_functions.core.rounding import (
    round_margin_pct,
    round_margin_ratio,
    round_money,
)
from farm_functions.core.sensitivity import break_even_shift, min_shift_all_non_negative
from farm_functions.core.variance import change_pct, price_volume_effects
from farm_functions.core.surplus import net_profit, profit_margin, profit_margin_pct

__all__ = [
    "AmortisationRow",
    "CashActivity",
    "CashDirection",
    "amortisation_schedule",
    "break_even_shift",
    "carry_forward",
    "annuity_payment",
    "annuity_principal",
    "cash_section_net",
    "change_pct",
    "closing_cash",
    "compound_indexes",
    "coverage_ratio",
    "latest_non_zero",
    "min_shift_all_non_negative",
    "net_cash_flow",
    "net_profit",
    "profit_margin",
    "per_unit",
    "price_volume_effects",
    "profit_margin_pct",
    "reducing_balance_nbv",
    "round_margin_pct",
    "round_margin_ratio",
    "round_money",
    "run_rate",
    "run_rate_factors",
    "seasonal_projection",
    "straight_line_nbv",
    "sum_amounts",
    "sum_cash_amounts",
]
