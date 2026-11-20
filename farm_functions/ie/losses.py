"""Irish trading losses carried forward for individuals (ADR-0055).

TCA s.382: an unused loss of a trade is set against later profits of the same
trade, earliest first, with no time limit. It reduces the profit charged to
income tax and to USC (s.531AU). PRSI Class S is charged on income "as
estimated in accordance with the Income Tax Acts" (SWCA 2005 s.2(1)), read
here as after the loss: not stated outright by Revenue or DSP, so the result
labels it. In a stock relief claim year, losses brought forward cannot be
carried on beyond that year (s.666(3)). Sources: ``docs/ie-rules.md`` §6B.
"""

from __future__ import annotations

from typing import Any

LEGAL_REFS = ("TCA s.382", "TCA s.531AU", "TCA s.666(3)", "SWCA 2005 s.2(1)")
PRSI_TREATMENT = "reduced_unconfirmed"


def apply_losses(profit: float, brought_forward: float, stock_relief_claimed: bool) -> tuple[float, dict[str, Any]]:
    """Profit after losses brought forward, and what happens to the losses.

    ``profit`` is the assessable farm profit (after averaging and capital
    allowances); a negative profit is this year's own loss, carried forward.
    """
    used = min(brought_forward, max(profit, 0.0))
    remaining = brought_forward - used
    lost = remaining if stock_relief_claimed else 0.0
    new_loss = max(-profit, 0.0)
    return profit - used, {
        "brought_forward": brought_forward,
        "used": used,
        "lost_by_stock_relief": lost,
        "this_year_loss": new_loss,
        "carried_forward": remaining - lost + new_loss,
    }


__all__ = ["LEGAL_REFS", "PRSI_TREATMENT", "apply_losses"]
