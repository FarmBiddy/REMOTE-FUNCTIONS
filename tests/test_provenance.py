from farm_functions.calcs.costs import COST_CATEGORIES, total_costs
from farm_functions.calcs.profit import net_profit, profit_margin
from farm_functions.calcs.revenue import milk_revenue, other_revenue, scheme_revenue, total_revenue
from farm_functions.domain import FinancialInput, FinancialModel, calculate_annual_pnl
from farm_functions.loaders.json_loader import load_sample_inputs
from farm_functions.provenance import SUPPORTED_CALCULATIONS, explain_annual_pnl
from farm_functions.runner import run_function
from farm_functions.schemas import FIELD_UNITS


def _sample_provenance():
    return explain_annual_pnl(FinancialInput.model_validate(load_sample_inputs()))


def test_provenance_covers_supported_annual_pnl_calculations():
    provenance = _sample_provenance()
    assert tuple(provenance) == SUPPORTED_CALCULATIONS
    assert set(provenance) == {
        "revenue.milk",
        "revenue.schemes",
        "revenue.other",
        "revenue.total",
        "costs.total",
        "profit.net",
        "profit.margin",
    }


def test_provenance_values_match_calculation_functions():
    data = load_sample_inputs()
    provenance = explain_annual_pnl(FinancialInput.model_validate(data))
    milk = milk_revenue(data["milking_cows"], data["litres_per_cow"], data["milk_price"])
    schemes = scheme_revenue(biss=data["biss"], acres=data["acres"], other_grants=data["other_grants"])
    other = other_revenue(cattle_sales=data["cattle_sales"])
    revenue = total_revenue(
        milking_cows=data["milking_cows"],
        litres_per_cow=data["litres_per_cow"],
        milk_price=data["milk_price"],
        biss=data["biss"],
        acres=data["acres"],
        cattle_sales=data["cattle_sales"],
    )
    costs = total_costs(
        feed=data["feed"],
        fertiliser=data["fertiliser"],
        vet=data["vet"],
        contractor=data["contractor"],
        labour=data["labour"],
        insurance=data["insurance"],
        loan_repayments=data["loan_repayments"],
        fuel=data["fuel"],
        electricity=data["electricity"],
    )
    assert provenance["revenue.milk"].value == milk == 200_000
    assert provenance["revenue.schemes"].value == schemes == 25_000
    assert provenance["revenue.other"].value == other == 15_000
    assert provenance["revenue.total"].value == revenue == 240_000
    assert provenance["costs.total"].value == costs == 175_000
    assert provenance["profit.net"].value == net_profit(revenue, costs) == 65_000
    assert provenance["profit.margin"].value == profit_margin(revenue, costs)


def test_provenance_inputs_used_and_formulas():
    provenance = _sample_provenance()
    milk = provenance["revenue.milk"]
    assert milk.formula == "milking_cows * litres_per_cow * milk_price"
    assert [item.name for item in milk.inputs_used] == [
        "milking_cows",
        "litres_per_cow",
        "milk_price",
    ]
    assert [item.value for item in milk.inputs_used] == [100, 5000, 0.40]
    assert [item.unit for item in milk.inputs_used] == [
        FIELD_UNITS["milking_cows"],
        FIELD_UNITS["litres_per_cow"],
        FIELD_UNITS["milk_price"],
    ]

    schemes = provenance["revenue.schemes"]
    assert schemes.formula == "biss + acres + other_grants"
    assert [item.name for item in schemes.inputs_used] == ["biss", "acres", "other_grants"]

    other = provenance["revenue.other"]
    assert other.formula == "cattle_sales + lamb_sales + wool + other"
    assert [item.name for item in other.inputs_used] == [
        "cattle_sales",
        "lamb_sales",
        "wool",
        "other",
    ]

    total = provenance["revenue.total"]
    assert total.formula == "revenue.milk + revenue.schemes + revenue.other"
    assert [item.name for item in total.inputs_used] == [
        "revenue.milk",
        "revenue.schemes",
        "revenue.other",
    ]
    assert [item.value for item in total.inputs_used] == [200_000, 25_000, 15_000]

    costs = provenance["costs.total"]
    assert costs.formula == " + ".join(COST_CATEGORIES)
    assert [item.name for item in costs.inputs_used] == list(COST_CATEGORIES)

    profit = provenance["profit.net"]
    assert profit.formula == "revenue.total - costs.total"
    assert [item.name for item in profit.inputs_used] == ["revenue.total", "costs.total"]

    margin = provenance["profit.margin"]
    assert "revenue.total" in margin.formula
    assert [item.name for item in margin.inputs_used] == ["revenue.total", "costs.total"]


def test_provenance_output_units():
    provenance = _sample_provenance()
    for key in (
        "revenue.milk",
        "revenue.schemes",
        "revenue.other",
        "revenue.total",
        "costs.total",
        "profit.net",
    ):
        assert provenance[key].unit == "EUR/year"
        assert provenance[key].calculation == key
    assert provenance["profit.margin"].unit == "ratio"


def test_demo_profit_provenance_explains_65000_from_revenue_minus_costs():
    provenance = _sample_provenance()
    profit = provenance["profit.net"]
    assert profit.value == 65_000
    assert profit.formula == "revenue.total - costs.total"
    by_name = {item.name: item for item in profit.inputs_used}
    assert by_name["revenue.total"].value == 240_000
    assert by_name["costs.total"].value == 175_000
    assert by_name["revenue.total"].unit == "EUR/year"
    assert by_name["costs.total"].unit == "EUR/year"
    assert profit.value == by_name["revenue.total"].value - by_name["costs.total"].value

    milk = provenance["revenue.milk"]
    cows, litres, price = milk.inputs_used
    assert cows.value * litres.value * price.value == milk.value == 200_000

    total = provenance["revenue.total"]
    assert sum(item.value for item in total.inputs_used) == total.value == 240_000
    assert provenance["costs.total"].value == 175_000


def test_explain_annual_pnl_accepts_financial_model():
    model = FinancialModel(inputs=FinancialInput.model_validate(load_sample_inputs()))
    provenance = explain_annual_pnl(model)
    typed = calculate_annual_pnl(model)
    assert provenance["profit.net"].value == typed.profit.net
    assert provenance["revenue.total"].value == typed.revenue.total
    assert provenance["costs.total"].value == typed.costs.total
