"""Agriculture layer: reusable agricultural financial calculations.

Must not import Dairy-specific modules. May use Core money primitives.
"""

from farm_functions.agriculture.revenue import scheme_revenue

__all__ = ["scheme_revenue"]
