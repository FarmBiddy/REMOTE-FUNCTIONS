"""Cost formulas. All amounts are annual EUR."""

COST_CATEGORIES = (
    "feed",
    "fertiliser",
    "vet",
    "contractor",
    "labour",
    "insurance",
    "loan_repayments",
    "fuel",
    "electricity",
)


def total_costs(
    feed: float = 0,
    fertiliser: float = 0,
    vet: float = 0,
    contractor: float = 0,
    labour: float = 0,
    insurance: float = 0,
    loan_repayments: float = 0,
    fuel: float = 0,
    electricity: float = 0,
) -> float:
    """Sum of the standard farm cost lines. Missing lines count as 0."""
    return (
        float(feed)
        + float(fertiliser)
        + float(vet)
        + float(contractor)
        + float(labour)
        + float(insurance)
        + float(loan_repayments)
        + float(fuel)
        + float(electricity)
    )
