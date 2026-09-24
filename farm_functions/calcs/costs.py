"""Operating cost formulas — compatibility re-export from ``farm_functions.dairy``.

``OPERATING_COST_CATEGORIES`` remains the Dairy-owned Phase 1 catalogue
(ADR-0013 / ADR-0015). Loan repayments are finance/debt service and are not
included.
"""

from farm_functions.dairy.costs import (
    COST_CATEGORIES,
    OPERATING_COST_CATEGORIES,
    total_costs,
)

__all__ = [
    "COST_CATEGORIES",
    "OPERATING_COST_CATEGORIES",
    "total_costs",
]
