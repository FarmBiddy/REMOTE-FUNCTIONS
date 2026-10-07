"""Interest-rate shocks on variable-rate loans (ADR-0043).

Reference: €12,000 at 0% over 12 months (1,000/month). At +12 pp from month 1
it reprices to the standard 12% annuity: €1,066.19/month.
"""

from farm_functions.core.loans import amortisation_schedule, repricing_schedule
from farm_functions.runner import run_function

LOAN = {"balance": 12_000, "annual_rate": 0, "remaining_months": 12, "year": 2026, "month": 1, "variable": True}
PL = [
    {"year": 2026, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 10_000, "loan_repayments": 1_000}
    for m in (1, 2, 3)
]
CF = [{"year": 2026, "month": m, "milk": 16_000, "feed": 10_000, "loan_principal_repayments": 1_000} for m in (1, 2, 3)]


def _sensitivity(loan=LOAN, **extra):
    return run_function(
        "risk.sensitivity",
        {"pl_months": PL, "cf_months": CF, "opening_cash": 0, "loans": [loan],
         "scenarios": [{"name": "+12pp", "rate_shift_pp": 12}], **extra},
    )["result"]["scenarios"]


def test_repricing_keeps_history_and_clears_the_loan():
    base = amortisation_schedule(10_000, 0.12, 12)
    assert repricing_schedule(10_000, 12, [(0, 0.12)]) == base
    repriced = repricing_schedule(10_000, 12, [(0, 0.12), (6, 0.18)])
    assert repriced[:6] == base[:6]
    assert repriced[6]["interest"] == round(base[5]["closing_balance"] * 0.18 / 12, 2)
    assert repriced[-1]["closing_balance"] == 0


def test_variable_loan_reprices_in_sensitivity():
    base, shocked = _sensitivity()
    assert shocked["shocks"]["rate_shift_pp"] == 12
    assert shocked["loan_repayments"] == 3 * 1_066.19
    assert shocked["closing_cash"] == base["closing_cash"] - (3 * 1_066.19 - 3_000)
    assert shocked["operating_surplus"] == base["operating_surplus"]  # interest is finance, not operating cost
    assert shocked["dscr"] < base["dscr"]


def test_fixed_loan_ignores_the_shock():
    base, shocked = _sensitivity(loan={**LOAN, "variable": False})
    assert shocked["loan_repayments"] == base["loan_repayments"]


def test_shock_starts_at_shocks_from():
    base, shocked = _sensitivity(shocks_from_year=2026, shocks_from_month=3)
    # Jan and Feb unchanged; March reprices the remaining 10,000 over 10 months at 12%.
    march = repricing_schedule(12_000, 12, [(0, 0), (2, 0.12)])[2]["payment"]
    assert shocked["loan_repayments"] == round(2_000 + march, 2)


def test_projection_reprices_variable_loans_per_year():
    base = [
        {"year": 2025 if m >= 10 else 2026, "month": m, "milk_litres": 40_000, "milk_price": 0.40, "feed": 8_000}
        for m in [10, 11, 12, *range(1, 10)]
    ]
    loan = {"balance": 60_000, "annual_rate": 0.04, "remaining_months": 60, "year": 2026, "month": 10}

    def service(variable):
        body = run_function(
            "plan.projection",
            {"base_pl_months": base, "opening_cash": 0, "milking_cows": 100, "years": 3,
             "loans": [{**loan, "variable": variable}], "assumptions": {"interest_rate_shift_pp": [0, 2]}},
        )["result"]
        return [y["debt"]["debt_service"] for y in body["years"]]

    fixed, variable = service(False), service(True)
    assert fixed[0] == variable[0]
    assert variable[1] > fixed[1] and variable[2] == variable[1]  # +2 pp carried into year 3
