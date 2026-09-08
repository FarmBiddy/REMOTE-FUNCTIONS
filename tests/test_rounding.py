from farm_functions.rounding import round_margin_pct, round_margin_ratio, round_money


def test_money_rounds_half_to_even():
    assert round_money(1.225) == 1.22
    assert round_money(1.235) == 1.24
    assert round_money(2.5) == 2.5
    assert round_money(1.005) == 1.00
    assert round_money(1.015) == 1.02


def test_margin_ratio_and_pct_use_bankers_rounding():
    assert round_margin_ratio(0.12345) == 0.1234
    assert round_margin_ratio(0.12355) == 0.1236
    assert round_margin_pct(27.085) == 27.08
    assert round_margin_pct(27.075) == 27.08
