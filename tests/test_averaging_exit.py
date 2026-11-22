"""tax.averaging_exit (s.657(8), ADR-0055 §8b): leaving income averaging.

Revenue TDM 23-01-34 Example 2: final averaged profit 17,380; the four years
before were assessed 12,000 / 12,400 / 12,467 / 12,850 and are each raised to
17,380: extra 5,380 + 4,980 + 4,913 + 4,530 = 19,803. Afterwards the total
assessed over the five years (5 × 17,380 = 86,900) equals the profits made.
"""

from farm_functions.runner import run_function

EXAMPLE_2 = {"final_averaged_year": 2026, "final_averaged_profit": 17_380,
             "prior_assessed_profits": [12_000, 12_400, 12_467, 12_850]}


def _run(**overrides):
    return run_function("tax.averaging_exit", {**EXAMPLE_2, **overrides})


def test_revenue_example_2():
    body = _run()["result"]
    assert [(y["tax_year"], y["additional_assessable"]) for y in body["years"]] == [
        (2022, 5_380), (2023, 4_980), (2024, 4_913), (2025, 4_530),
    ]
    assert {y["topped_up_to"] for y in body["years"]} == {17_380}
    assert body["total_additional_assessable"] == 19_803
    assert body["normal_basis_from"] == 2027
    assert body["rules_applied"][0]["rule_id"] == "income_averaging_years"


def test_years_above_the_average_are_not_lowered():
    body = _run(prior_assessed_profits=[20_000, 12_400, 18_000, 12_850])["result"]
    assert [y["additional_assessable"] for y in body["years"]] == [0, 4_980, 0, 4_530]


def test_deferred_step_out_tax_falls_due():
    assert _run(deferred_step_out_tax=2_720)["result"]["deferred_step_out_tax_due_now"] == 2_720


def test_needs_the_four_years_and_a_rule():
    short = _run(prior_assessed_profits=[1, 2, 3])
    assert short["errors"][0]["details"]["reason"] == "averaging_years_invalid"
    assert _run(final_averaged_year=2023)["errors"][0]["details"]["reason"] == "rule_not_available"
