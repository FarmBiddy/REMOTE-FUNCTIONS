"""Generic monetary aggregation. No sector field names."""


def sum_amounts(*values: float) -> float:
    """Sum already-monetary amounts. Missing callers should pass 0 explicitly."""
    total = 0.0
    for value in values:
        total += float(value)
    return total
