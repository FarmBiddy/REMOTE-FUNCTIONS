"""Sector-agnostic loan amortisation (ADR-0025).

Equal monthly instalments (annuity), nominal annual rate compounded monthly.
Rows are calendar-blind; the caller attaches periods. No farm vocabulary.
"""

from typing import TypedDict

from farm_functions.core.rounding import round_money


class AmortisationRow(TypedDict):
    opening_balance: float
    payment: float
    interest: float
    principal: float
    closing_balance: float


def annuity_payment(balance: float, annual_rate: float, months: int) -> float:
    """Equal monthly instalment that repays ``balance`` over ``months``."""
    rate = annual_rate / 12
    if rate == 0:
        return balance / months
    return balance * rate / (1 - (1 + rate) ** -months)


def annuity_principal(payment: float, annual_rate: float, months: int) -> float:
    """Largest balance an equal monthly ``payment`` repays over ``months`` (inverse annuity)."""
    rate = annual_rate / 12
    if rate == 0:
        return payment * months
    return payment * (1 - (1 + rate) ** -months) / rate


def amortisation_schedule(
    balance: float, annual_rate: float, months: int
) -> list[AmortisationRow]:
    """Month-by-month schedule in cents; the last row clears the balance exactly."""
    payment = round_money(annuity_payment(balance, annual_rate, months))
    remaining = round_money(balance)
    rows: list[AmortisationRow] = []
    for index in range(months):
        interest = round_money(remaining * annual_rate / 12)
        last = index == months - 1
        principal = remaining if last else min(remaining, round_money(payment - interest))
        closing = round_money(remaining - principal)
        rows.append(
            AmortisationRow(
                opening_balance=remaining,
                payment=round_money(interest + principal),
                interest=interest,
                principal=principal,
                closing_balance=closing,
            )
        )
        remaining = closing
    return rows


__all__ = ["AmortisationRow", "amortisation_schedule", "annuity_payment", "annuity_principal"]
