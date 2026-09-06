from farm_functions.calcs.costs import total_costs
from farm_functions.calcs.profit import net_profit, profit_margin, profit_margin_pct
from farm_functions.calcs.revenue import milk_revenue, other_revenue, scheme_revenue, total_revenue


def test_milk_revenue():
    assert milk_revenue(100, 5000, 0.40) == 200_000


def test_scheme_and_other_revenue():
    assert scheme_revenue(biss=20_000, acres=5_000) == 25_000
    assert other_revenue(cattle_sales=15_000) == 15_000


def test_total_revenue():
    assert total_revenue(
        milking_cows=100,
        litres_per_cow=5000,
        milk_price=0.40,
        biss=20_000,
        acres=5_000,
        cattle_sales=15_000,
    ) == 240_000


def test_total_costs():
    assert total_costs(
        feed=80_000,
        fertiliser=15_000,
        vet=5_000,
        contractor=10_000,
        labour=40_000,
        insurance=4_000,
        loan_repayments=12_000,
        fuel=6_000,
        electricity=3_000,
    ) == 175_000


def test_missing_cost_lines_are_zero():
    assert total_costs(feed=80_000) == 80_000


def test_net_profit_and_margin():
    assert net_profit(240_000, 175_000) == 65_000
    assert profit_margin(240_000, 175_000) == 65_000 / 240_000
    assert profit_margin_pct(240_000, 175_000) == (65_000 / 240_000) * 100


def test_margin_is_zero_when_revenue_is_zero():
    assert profit_margin(0, 10) == 0
    assert profit_margin_pct(0, 10) == 0
