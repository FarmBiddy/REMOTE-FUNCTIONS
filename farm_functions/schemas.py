"""Explicit input fields for each callable function."""

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class MilkRevenueInput(_StrictModel):
    milking_cows: float
    litres_per_cow: float
    milk_price: float


class SchemeRevenueInput(_StrictModel):
    biss: float = 0
    acres: float = 0
    other_grants: float = 0


class OtherRevenueInput(_StrictModel):
    cattle_sales: float = 0
    lamb_sales: float = 0
    wool: float = 0
    other: float = 0


class TotalRevenueInput(MilkRevenueInput, SchemeRevenueInput, OtherRevenueInput):
    pass


class TotalCostsInput(_StrictModel):
    feed: float = 0
    fertiliser: float = 0
    vet: float = 0
    contractor: float = 0
    labour: float = 0
    insurance: float = 0
    loan_repayments: float = 0
    fuel: float = 0
    electricity: float = 0


class ProfitInput(_StrictModel):
    revenue: float
    costs: float


class PlSummaryInput(TotalRevenueInput, TotalCostsInput):
    pass


REQUIRED_FIELDS = {
    "revenue.milk": ("milking_cows", "litres_per_cow", "milk_price"),
    "revenue.schemes": (),
    "revenue.other": (),
    "revenue.total": ("milking_cows", "litres_per_cow", "milk_price"),
    "costs.total": (),
    "profit.net": ("revenue", "costs"),
    "profit.margin": ("revenue", "costs"),
    "pl.summary": ("milking_cows", "litres_per_cow", "milk_price"),
}

OPTIONAL_FIELDS = {
    "revenue.milk": (),
    "revenue.schemes": ("biss", "acres", "other_grants"),
    "revenue.other": ("cattle_sales", "lamb_sales", "wool", "other"),
    "revenue.total": (
        "biss",
        "acres",
        "other_grants",
        "cattle_sales",
        "lamb_sales",
        "wool",
        "other",
    ),
    "costs.total": (
        "feed",
        "fertiliser",
        "vet",
        "contractor",
        "labour",
        "insurance",
        "loan_repayments",
        "fuel",
        "electricity",
    ),
    "profit.net": (),
    "profit.margin": (),
    "pl.summary": (
        "biss",
        "acres",
        "other_grants",
        "cattle_sales",
        "lamb_sales",
        "wool",
        "other",
        "feed",
        "fertiliser",
        "vet",
        "contractor",
        "labour",
        "insurance",
        "loan_repayments",
        "fuel",
        "electricity",
    ),
}

INPUT_MODELS = {
    "revenue.milk": MilkRevenueInput,
    "revenue.schemes": SchemeRevenueInput,
    "revenue.other": OtherRevenueInput,
    "revenue.total": TotalRevenueInput,
    "costs.total": TotalCostsInput,
    "profit.net": ProfitInput,
    "profit.margin": ProfitInput,
    "pl.summary": PlSummaryInput,
}
