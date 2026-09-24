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
    """Operating agri-scheme / subsidy income (EUR/year).

    ``acres`` is ACRES scheme money, not land area.
    """
    return sum_amounts(biss, acres, other_grants)
