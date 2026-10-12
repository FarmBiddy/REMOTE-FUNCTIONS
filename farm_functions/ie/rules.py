"""Dated, sourced Irish rules (ADR-0053).

A rule value applies from ``start`` to ``end`` inclusive (``end`` None = until
replaced). Lookup never extrapolates: a date outside every rule has no value.
Every rule must appear in ``docs/ie-rules.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class Rule:
    rule_id: str
    value: float
    start: date
    end: date | None
    legal_ref: str
    status: Literal["enacted", "announced"]

    def as_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "value": self.value,
            "from": self.start.isoformat(),
            "to": None if self.end is None else self.end.isoformat(),
            "legal_ref": self.legal_ref,
            "status": self.status,
        }


def rule_at(rules: tuple[Rule, ...], on: date) -> Rule | None:
    """The rule in force on ``on``, or None."""
    return next((r for r in rules if r.start <= on and (r.end is None or on <= r.end)), None)


__all__ = ["Rule", "rule_at"]
