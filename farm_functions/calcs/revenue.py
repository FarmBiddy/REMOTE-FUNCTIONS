"""Revenue formulas — compatibility re-exports.

Canonical ownership:
- ``milk_revenue`` / ``other_revenue`` / ``total_revenue`` → ``farm_functions.dairy``
- ``scheme_revenue`` → ``farm_functions.agriculture``
"""

from farm_functions.agriculture.revenue import scheme_revenue
from farm_functions.dairy.revenue import milk_revenue, other_revenue, total_revenue

__all__ = [
    "milk_revenue",
    "other_revenue",
    "scheme_revenue",
    "total_revenue",
]
