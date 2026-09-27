"""Agricultural income calculations shared across farm enterprises.

Field names ``biss``, ``acres``, ``other_grants`` remain the Phase 1 Dairy
public contract identifiers (no rename). Semantics are agricultural schemes/
grants, not Dairy-operational.
"""

from farm_functions.core.aggregate import sum_amounts


def scheme_revenue(
    biss: float = 0,
    acres: float = 0,
    other_grants: float = 0,
) -> float:
    """Operating agri-scheme / subsidy income for the statement period.

    Amounts are EUR for that period (annual or monthly callers supply
    period-scoped floats). ``acres`` is ACRES scheme money, not land area.
    """
    return sum_amounts(biss, acres, other_grants)
