"""Dairy operating-cost catalogue and totals. All amounts are annual EUR.

``OPERATING_COST_CATEGORIES`` is the authoritative Phase 1 operating-cost
catalogue (Dairy-owned Phase 1 input vocabulary; ADR-0013 / ADR-0015). Loan
repayments are finance/debt service and are not included.
"""

from farm_functions.core.aggregate import sum_amounts

OPERATING_COST_CATEGORIES = (
    "feed",
    "fertiliser",
    "vet",
    "contractor",
    "labour",
    "insurance",
    "fuel",
    "electricity",
    "water",
    "repairs_maintenance",
    "rent_lease",
    "professional_fees",
    "levies",
    "other_operating_costs",
)

# Alias kept for call sites that still import COST_CATEGORIES.
COST_CATEGORIES = OPERATING_COST_CATEGORIES


def total_costs(
    feed: float = 0,
    fertiliser: float = 0,
    vet: float = 0,
    contractor: float = 0,
    labour: float = 0,
    insurance: float = 0,
    fuel: float = 0,
    electricity: float = 0,
    water: float = 0,
    repairs_maintenance: float = 0,
    rent_lease: float = 0,
    professional_fees: float = 0,
    levies: float = 0,
    other_operating_costs: float = 0,
) -> float:
    """Sum of Phase 1 operating cost lines. Missing lines count as 0.

    Does not include loan repayments / debt service.
    """
    return sum_amounts(
        feed,
        fertiliser,
        vet,
        contractor,
        labour,
        insurance,
        fuel,
        electricity,
        water,
        repairs_maintenance,
        rent_lease,
        professional_fees,
        levies,
        other_operating_costs,
    )


__all__ = [
    "COST_CATEGORIES",
    "OPERATING_COST_CATEGORIES",
    "total_costs",
]
