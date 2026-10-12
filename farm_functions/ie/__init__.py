"""Irish jurisdiction rules (ADR-0053).

Application → ie → Agriculture / Core. Core, Agriculture and Dairy never
import this package. Sources: ``docs/ie-rules.md``.
"""

from farm_functions.ie.rules import Rule, rule_at
from farm_functions.ie.vat import FLAT_RATE_ADDITION, flat_rate_addition

__all__ = ["FLAT_RATE_ADDITION", "Rule", "flat_rate_addition", "rule_at"]
