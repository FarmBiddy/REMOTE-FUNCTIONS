"""Typed result models for every public ID (ADR-0051).

Describe the ``result`` of an ``ok`` envelope so OpenAPI publishes it and the
Platform can generate types. They do not drive the calculations: tests validate
real outputs against them, so a shape change that forgets its model fails.
Statement results reuse the Domain models.
"""

from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, create_model

from farm_functions.domain import (
    FinancialResult,
    MonthlyDairyCashFlowResult,
    MonthlyDairyStatementResult,
    MonthlyPeriodIdentity,
    MultiMonthDairyCashFlowResult,
    YtdDairyStatementResult,
)

Currency = Literal["EUR"]


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --- shared pieces -----------------------------------------------------------


class Money(_Out):
    amount: float
    currency: Currency


class Span(_Out):
    from_: MonthlyPeriodIdentity = Field(alias="from")
    to: MonthlyPeriodIdentity
    month_count: int


class FromTo(_Out):
    from_: MonthlyPeriodIdentity = Field(alias="from")
    to: MonthlyPeriodIdentity


class Variance(_Out):
    actual: float
    comparison: float
    change: float
    change_pct: float | None


class Note(_Out):
    opening_nbv: float
    additions: float
    depreciation: float
    closing_nbv: float


# --- simple IDs --------------------------------------------------------------


class ProfitMarginResult(_Out):
    margin: float
    margin_pct: float
    profit: float
    revenue: float
    costs: float
    currency: Currency


class PlMonthsResult(_Out):
    currency: Currency
    months: list[MonthlyDairyStatementResult]
    ytd: YtdDairyStatementResult | None


# --- loans, assets, capacity ---------------------------------------------------


class LoanRow(_Out):
    period: MonthlyPeriodIdentity
    opening_balance: float
    payment: float
    interest: float
    principal: float
    closing_balance: float


class LoanResult(_Out):
    currency: Currency
    balance: float
    annual_rate: float
    remaining_months: int
    monthly_payment: float
    total_interest: float
    total_payments: float
    repaid_pct: float | None
    variable: bool
    months: list[LoanRow]


class DebtServiceRow(_Out):
    period: MonthlyPeriodIdentity
    payment: float
    interest: float
    principal: float


class LoanScheduleResult(_Out):
    currency: Currency
    loans: list[LoanResult]
    total_balance: float
    total_monthly_payment: float
    total_interest: float
    months: list[DebtServiceRow]


class AssetNote(Note):
    category: Literal["machinery", "buildings", "other"]


class ByCategory(_Out):
    machinery: Note
    buildings: Note
    other: Note


class AssetsScheduleResult(_Out):
    currency: Currency
    from_: MonthlyPeriodIdentity = Field(alias="from")
    to: MonthlyPeriodIdentity
    assets: list[AssetNote]
    by_category: ByCategory
    total: Note


class NewLoanResult(_Out):
    annual_rate: float
    term_months: int
    max_monthly_payment: float
    max_principal: float
    monthly_payment_at_max: float


class DebtCapacityResult(Span):
    currency: Currency
    operating_surplus: float
    off_farm_income: float
    drawings: float
    tax: float
    repayment_capacity: float
    debt_service: float
    repayment_cover: float | None
    min_cover: float
    new_loan: NewLoanResult | None


# --- KPIs, net profit, balance sheet ----------------------------------------


class KpiTotals(_Out):
    milk_litres: float
    revenue: float
    costs: float
    operating_surplus: float
    loan_repayments: float


class PerLitre(_Out):
    revenue: float | None
    costs: float | None
    variable_costs: float | None
    fixed_costs: float | None
    gross_margin: float | None
    operating_surplus: float | None
    cost_lines: dict[str, float | None]


class PerUnitMoney(_Out):
    revenue: float | None
    costs: float | None
    gross_margin: float | None
    operating_surplus: float | None


class PerUnitWithLitres(PerUnitMoney):
    milk_litres: float | None


class DebtKpis(_Out):
    balance: float
    per_cow: float | None
    per_hectare: float | None


class KpiSummaryResult(Span):
    currency: Currency
    milking_cows: float
    totals: KpiTotals
    per_litre_c: PerLitre
    per_cow: PerUnitWithLitres
    per_kg_ms: PerUnitMoney | None
    per_hectare: PerUnitWithLitres | None
    debt: DebtKpis | None
    dscr: float | None


class PlNetResult(Span):
    currency: Currency
    revenue: float
    operating_surplus: float
    livestock_value_change: float
    stock_value_change: float
    adjusted_surplus: float
    depreciation: float
    ebit: float
    interest: float
    net_profit_before_tax: float
    net_margin_pct: float | None


class CurrentAssets(_Out):
    cash: float
    debtors: float
    stock: float
    total: float


class NonCurrentAssets(_Out):
    land: float
    buildings: float
    machinery: float
    other_fixed_assets: float
    livestock: float
    total: float


class CurrentLiabilities(_Out):
    overdraft: float
    creditors: float
    loans_due_within_12_months: float
    total: float


class NonCurrentLiabilities(_Out):
    loans_due_after_12_months: float
    other_long_term_liabilities: float
    total: float


class Assets(_Out):
    current: CurrentAssets
    non_current: NonCurrentAssets
    total: float


class Liabilities(_Out):
    current: CurrentLiabilities
    non_current: NonCurrentLiabilities
    total: float


class BalanceRatios(_Out):
    equity_pct: float | None
    debt_to_assets_pct: float | None
    current_ratio: float | None
    working_capital: float


class BsSummaryResult(_Out):
    currency: Currency
    as_of: MonthlyPeriodIdentity
    assets: Assets
    liabilities: Liabilities
    net_worth: float
    ratios: BalanceRatios


# --- variance --------------------------------------------------------------------


class RevenueVariance(_Out):
    milk: Variance
    schemes: Variance
    other: Variance
    total: Variance


class CostsVariance(_Out):
    lines: dict[str, Variance]
    total: Variance


class MarginChange(_Out):
    actual: float
    comparison: float
    change_pp: float


class PriceChange(_Out):
    actual: float
    comparison: float
    change: float


class MilkVariance(_Out):
    litres: Variance
    price_c: PriceChange
    volume_effect: float
    price_effect: float


class PlCompareResult(_Out):
    currency: Currency
    actual: Span
    comparison: Span
    revenue: RevenueVariance
    costs: CostsVariance
    profit: dict[Literal["net"], Variance]
    finance: dict[Literal["loan_repayments"], Variance]
    margin_pct: MarginChange
    milk: MilkVariance


class CashGroupVariance(_Out):
    lines: dict[str, Variance]
    total: Variance


class CashSectionVariance(_Out):
    inflows: CashGroupVariance
    outflows: CashGroupVariance
    net: Variance


class CfCompareResult(_Out):
    currency: Currency
    actual: Span
    comparison: Span
    operating: CashSectionVariance
    investing: CashSectionVariance
    financing: CashSectionVariance
    cash_in: Variance
    cash_out: Variance
    net_cash_flow: Variance


# --- risk ------------------------------------------------------------------------


class Shocks(_Out):
    milk_price_c: float
    milk_volume_pct: float
    herd_pct: float
    rate_shift_pp: float
    lines_pct: dict[str, float]


class InvestmentSummary(_Out):
    period: MonthlyPeriodIdentity
    amount: float
    loan_monthly_payment: float | None
    monthly_benefit: float
    simple_payback_months: float | None


class LowestCash(_Out):
    period: MonthlyPeriodIdentity
    amount: float


class BreakEven(_Out):
    surplus_milk_price_c: float | None
    cash_milk_price_c: float | None


class ScenarioOutcome(_Out):
    name: str
    shocks: Shocks
    investments: list[InvestmentSummary]
    operating_surplus: float
    loan_repayments: float
    dscr: float | None
    closing_cash: float
    lowest_cash: LowestCash
    overdraft_months: int
    break_even: BreakEven


class RiskSensitivityResult(_Out):
    currency: Currency
    shocks_from: MonthlyPeriodIdentity | None
    milk_price_c: float
    scenarios: list[ScenarioOutcome]


class TornadoPoint(_Out):
    operating_surplus: float
    closing_cash: float
    lowest_cash: float
    dscr: float | None


class TornadoSwing(_Out):
    operating_surplus: float
    closing_cash: float
    lowest_cash: float


class TornadoDriver(_Out):
    driver: str
    shock: Literal["milk_price_c", "milk_volume_pct", "herd_pct", "lines_pct", "rate_shift_pp"]
    low_change: float
    high_change: float
    low: TornadoPoint
    high: TornadoPoint
    swing: TornadoSwing


class RiskTornadoResult(_Out):
    currency: Currency
    step_pct: float
    rate_step_pp: float
    rank_by: Literal["operating_surplus", "closing_cash", "lowest_cash"]
    base: TornadoPoint
    drivers: list[TornadoDriver]


# --- decisions -------------------------------------------------------------------


class BudgetItem(_Out):
    label: str
    amount: float


class BudgetSection(_Out):
    items: list[BudgetItem]
    total: float


class CapitalResult(_Out):
    amount: float
    life_years: float
    annual_rate: float
    depreciation: float
    interest: float
    annual_charge: float
    simple_payback_years: float | None
    return_on_investment_pct: float | None


class PartialBudgetResult(_Out):
    currency: Currency
    added_income: BudgetSection
    reduced_costs: BudgetSection
    added_costs: BudgetSection
    reduced_income: BudgetSection
    gains: float
    losses: float
    operating_change: float
    capital: CapitalResult | None
    net_change: float
    worthwhile: bool


class AppraisalYear(_Out):
    year: int
    cash_flow: float
    discount_factor: float
    present_value: float
    cumulative_present_value: float


class InvestmentAppraisalResult(_Out):
    currency: Currency
    amount: float
    discount_rate: float
    life_years: int
    residual_value: float
    npv: float
    irr_pct: float | None
    simple_payback_years: float | None
    discounted_payback_years: float | None
    profitability_index: float | None
    worthwhile: bool
    years: list[AppraisalYear]


# --- forecasts and projection -----------------------------------------------------


class PlForecastMonth(_Out):
    period: MonthlyPeriodIdentity
    inputs: dict[str, float]
    statement: MonthlyDairyStatementResult


class PlForecastResult(_Out):
    currency: Currency
    as_of: MonthlyPeriodIdentity
    run_rate: dict[str, float]
    months: list[PlForecastMonth]


class CfForecastMonth(_Out):
    period: MonthlyPeriodIdentity
    inputs: dict[str, float]
    cash_flow: MonthlyDairyCashFlowResult


class CfForecastResult(_Out):
    currency: Currency
    as_of: MonthlyPeriodIdentity
    run_rate: dict[str, float]
    months: list[CfForecastMonth]


class ProjectionBase(_Out):
    period: FromTo
    milk_litres: float
    milk_price_c: float
    opening_cash: float


class AssumptionsUsed(_Out):
    milk_price: float
    herd_index: float
    yield_index: float
    cost_inflation_pct: float
    drawings: float
    tax: float
    off_farm_income: float
    interest_rate_shift_pp: float


class ProjectionRevenue(_Out):
    milk: float
    schemes: float
    other: float
    total: float


class ProjectionCosts(_Out):
    lines: dict[str, float]
    total: float


class ProjectionPl(_Out):
    milk_litres: float
    revenue: ProjectionRevenue
    costs: ProjectionCosts
    operating_surplus: float
    depreciation: float
    interest: float
    net_profit_before_tax: float


class ProjectionCash(_Out):
    opening: float
    operating_surplus: float
    off_farm_income: float
    drawings: float
    tax: float
    interest: float
    principal: float
    capex: float
    new_loans: float
    net: float
    closing: float


class ProjectionDebt(_Out):
    closing_balance: float
    debt_service: float
    dscr: float | None
    repayment_cover: float | None


class ProjectionBalanceSheet(_Out):
    cash: float
    fixed_assets: float
    land: float
    livestock: float
    debt: float
    net_worth: float


class ProjectionKpis(_Out):
    milking_cows: float
    milk_price_c: float
    costs_per_litre_c: float | None
    surplus_per_cow: float | None


class ProjectionFlags(_Out):
    negative_cash: bool
    below_min_cover: bool | None


class ProjectionTax(_Out):
    tax_year: int
    rules_basis: Literal["in_force", "latest_held_constant"]
    rules_status: Literal["enacted", "announced"]
    profit_before_allowances: float
    livestock_increase: float
    stock_relief_regime: Literal["general", "young_trained_farmer", "registered_partnership"]
    stock_relief: float
    capital_allowances: float
    averaging: Literal["off", "applied", "insufficient_history"]
    averaged_profit: float
    assessable_profit: float
    total_tax: float
    effective_rate_pct: float | None


class ProjectionYear(_Out):
    year: int
    period: FromTo
    assumptions_used: AssumptionsUsed
    pl: ProjectionPl
    cash: ProjectionCash
    debt: ProjectionDebt
    balance_sheet: ProjectionBalanceSheet
    tax: ProjectionTax | None
    kpis: ProjectionKpis
    flags: ProjectionFlags


class PlanProjectionResult(_Out):
    currency: Currency
    base: ProjectionBase
    years: list[ProjectionYear]


# --- milk quality ------------------------------------------------------------------


class QualityPeriod(_Out):
    milk_litres: float
    fat_pct: float | None
    protein_pct: float | None
    scc_k: float | None
    tbc_k: float | None
    milk_solids_kg: float
    kg_ms_per_cow: float | None
    kg_ms_per_ha: float | None


class QualityMonth(_Out):
    period: MonthlyPeriodIdentity
    milk_litres: float
    fat_pct: float
    protein_pct: float
    scc_k: float
    tbc_k: float
    milk_solids_kg: float
    scc_rolling_k: float
    scc_breach: bool
    tbc_rolling_k: float
    tbc_breach: bool


class QualityCompliance(_Out):
    scc_limit_k: float
    tbc_limit_k: float
    scc_breach_months: list[MonthlyPeriodIdentity]
    tbc_breach_months: list[MonthlyPeriodIdentity]


class BenchmarkComparison(_Out):
    farm: float
    average: float | None
    average_basis: Literal["fixed", "litre_weighted_monthly"] | None
    gap_to_average: float | None
    position: Literal["above", "below", "about"] | None
    better_than_average: bool | None
    best20: float | None
    gap_to_best20: float | None
    better_than_best20: bool | None
    top10: float | None
    gap_to_top10: float | None
    better_than_top10: bool | None


class QualityPriceBreakdown(_Out):
    fat: float | None
    protein: float | None
    volume_charge: float | None
    scc_adjustment: float | None
    tbc_adjustment: float | None
    total: float | None


class QualityValue(_Out):
    currency: Currency
    fat_eur: float
    protein_eur: float
    volume_charge_eur: float
    scc_adjustment_eur: float
    tbc_adjustment_eur: float
    total_eur: float
    price_c_per_l: QualityPriceBreakdown
    gain_to_average_eur: float | None
    gain_to_best20_eur: float | None
    gain_to_top10_eur: float | None
    gain_at_best_band_eur: float


class MilkQualityResult(Span):
    period: QualityPeriod
    months: list[QualityMonth]
    compliance: QualityCompliance
    vs_benchmarks: dict[Literal["scc_k", "tbc_k", "fat_pct", "protein_pct"], BenchmarkComparison] | None
    value: QualityValue | None


# --- Irish rules (ADR-0053) ------------------------------------------------------


class RuleApplied(_Out):
    rule_id: str
    value: float
    from_: str = Field(alias="from")
    to: str | None
    legal_ref: str
    status: Literal["enacted", "announced"]


class VatMonth(_Out):
    period: MonthlyPeriodIdentity
    milk: float
    cattle_sales: float
    base: float
    rate_pct: float | None
    addition: float


class VatTotal(_Out):
    milk: float
    cattle_sales: float
    base: float
    addition: float


class VatFlatRateResult(Span):
    currency: Currency
    jurisdiction: Literal["IE"]
    vat_registered: bool
    months: list[VatMonth]
    total: VatTotal
    rules_applied: list[RuleApplied]


class TaxStockReliefResult(_Out):
    currency: Currency
    jurisdiction: Literal["IE"]
    business_type: Literal["sole_trader", "partnership", "company"]
    period_end: MonthlyPeriodIdentity
    regime: Literal["general", "young_trained_farmer", "registered_partnership"]
    opening_stock: float
    closing_stock: float
    stock_increase: float
    rate_pct: float
    relief_before_profit_limit: float
    trading_profit: float
    relief: float
    profit_after_relief: float
    restricted_by_profit: bool
    losses_forward_restricted: bool
    caps_not_applied: list[str]
    rules_applied: list[RuleApplied]


AllowanceType = Literal["plant", "farm_buildings", "slurry_storage", "farm_safety", "none"]


class AllowanceAsset(_Out):
    category: Literal["machinery", "buildings", "other"]
    allowance_type: AllowanceType
    allowance_applied: AllowanceType
    qualifying_cost: float
    opening_twdv: float
    allowance: float
    closing_twdv: float


class AllowanceTotals(_Out):
    opening_twdv: float
    allowance: float
    closing_twdv: float


class AllowanceByType(_Out):
    plant: float
    farm_buildings: float
    slurry_storage: float
    farm_safety: float


class ProfitBridge(_Out):
    accounting_profit: float
    add_back_depreciation: float
    capital_allowances: float
    taxable_profit: float


class TaxCapitalAllowancesResult(_Out):
    currency: Currency
    jurisdiction: Literal["IE"]
    tax_year: int
    period_end_month: int
    assets: list[AllowanceAsset]
    by_type: AllowanceByType
    total: AllowanceTotals
    profit_bridge: ProfitBridge | None
    caps_not_applied: list[str]
    rules_applied: list[RuleApplied]


class TaxIncome(_Out):
    farm_profit: float
    other_income: float
    spouse_paye_income: float
    total: float


class IncomeTaxLines(_Out):
    standard_rate_band: float
    at_standard_rate: float
    at_higher_rate: float
    gross: float
    credits: float
    net: float


class PerPerson(_Out):
    farmer: float
    spouse: float
    total: float


class CorporationTaxLines(_Out):
    trading: float
    non_trading: float
    total: float


class StockReliefCap(_Out):
    regime: Literal["young_trained_farmer", "registered_partnership"]
    relief: float
    tax_value: float
    cap: float
    clawback: float


class TaxEstimateResult(_Out):
    currency: Currency
    jurisdiction: Literal["IE"]
    business_type: Literal["sole_trader", "partnership", "company"]
    tax_year: int
    assessment: Literal["single", "joint", "company"]
    income: TaxIncome
    income_tax: IncomeTaxLines | None
    usc: PerPerson | None
    prsi: PerPerson | None
    corporation_tax: CorporationTaxLines | None
    stock_relief_cap: StockReliefCap | None
    total_tax: float
    effective_rate_pct: float | None
    rules_applied: list[RuleApplied]


class PartnerResult(_Out):
    label: str
    profit_share_pct: float
    profit_share: float
    stock_increase_share: float
    stock_relief_regime: Literal["general", "young_trained_farmer", "registered_partnership"]
    stock_relief: float
    taxable_profit: float
    succession_credit: float
    tax: TaxEstimateResult


class PartnershipTotals(_Out):
    stock_relief: float
    succession_credit: float
    total_tax: float


class TaxPartnershipResult(_Out):
    currency: Currency
    jurisdiction: Literal["IE"]
    tax_year: int
    registered_partnership: bool
    succession_credit_total: float
    trading_profit: float
    stock_increase: float
    partners: list[PartnerResult]
    total: PartnershipTotals
    rules_applied: list[RuleApplied]


# --- reports ---------------------------------------------------------------------


class ReportHeader(_Out):
    currency: Currency
    as_of: MonthlyPeriodIdentity
    period: Span


class ReportCash(_Out):
    actual: MultiMonthDairyCashFlowResult
    projection: MultiMonthDairyCashFlowResult | None


class ReportBankResult(ReportHeader):
    report: Literal["bank"]
    profit: PlNetResult
    kpis: KpiSummaryResult
    loans: LoanScheduleResult | None
    capacity: DebtCapacityResult
    balance_sheet: BsSummaryResult
    cash: ReportCash


class ReportAdvisorResult(ReportHeader):
    report: Literal["advisor"]
    kpis: KpiSummaryResult
    profit: PlNetResult
    comparison: PlCompareResult | None
    sensitivity: RiskSensitivityResult


class AccountantPl(_Out):
    revenue: ProjectionRevenue
    costs: ProjectionCosts
    profit: dict[Literal["net"], float]
    finance: dict[Literal["loan_repayments"], float]
    margin_pct: float


class CashGroupTotals(_Out):
    lines: dict[str, float]
    total: float


class CashSectionTotals(_Out):
    inflows: CashGroupTotals
    outflows: CashGroupTotals
    net: float


class AccountantCashFlow(_Out):
    operating: CashSectionTotals
    investing: CashSectionTotals
    financing: CashSectionTotals
    cash_in: float
    cash_out: float
    net_cash_flow: float
    opening_cash: float
    closing_cash: float


class ReportAccountantResult(ReportHeader):
    report: Literal["accountant"]
    profit_and_loss: AccountantPl
    net_profit: PlNetResult
    fixed_assets: AssetsScheduleResult | None
    balance_sheet: BsSummaryResult
    cash_flow: AccountantCashFlow


OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    **dict.fromkeys(
        ("revenue.milk", "revenue.schemes", "revenue.other", "revenue.total", "costs.total", "profit.net"),
        Money,
    ),
    "profit.margin": ProfitMarginResult,
    "pl.summary": FinancialResult,
    "pl.monthly": MonthlyDairyStatementResult,
    "pl.months": PlMonthsResult,
    "cf.monthly": MonthlyDairyCashFlowResult,
    "cf.months": MultiMonthDairyCashFlowResult,
    "loan.schedule": LoanScheduleResult,
    "assets.schedule": AssetsScheduleResult,
    "debt.capacity": DebtCapacityResult,
    "kpi.summary": KpiSummaryResult,
    "pl.net": PlNetResult,
    "milk.quality": MilkQualityResult,
    "vat.flat_rate": VatFlatRateResult,
    "tax.stock_relief": TaxStockReliefResult,
    "tax.capital_allowances": TaxCapitalAllowancesResult,
    "tax.estimate": TaxEstimateResult,
    "tax.partnership": TaxPartnershipResult,
    "bs.summary": BsSummaryResult,
    "pl.compare": PlCompareResult,
    "cf.compare": CfCompareResult,
    "risk.sensitivity": RiskSensitivityResult,
    "risk.tornado": RiskTornadoResult,
    "decision.partial_budget": PartialBudgetResult,
    "decision.investment": InvestmentAppraisalResult,
    "report.bank": ReportBankResult,
    "report.advisor": ReportAdvisorResult,
    "report.accountant": ReportAccountantResult,
    "plan.projection": PlanProjectionResult,
    "pl.forecast": PlForecastResult,
    "cf.forecast": CfForecastResult,
}


# --- envelopes ---------------------------------------------------------------------


class Meta(_Out):
    engine_version: str


class Issue(BaseModel):
    """One structured problem (ADR-0004 / error contract); optional keys vary by code."""

    model_config = ConfigDict(extra="allow")

    code: str
    message: str
    field: str | None = None
    details: dict | None = None


class MissingField(_Out):
    field: str
    unit: str
    path: str | None = None


class NeedsInputEnvelope(_Out):
    status: Literal["needs_input"]
    function: str
    missing: list[MissingField]
    provided: list[str]
    error: Issue
    errors: list[Issue]
    meta: Meta


class ErrorEnvelope(_Out):
    status: Literal["error"]
    function: str | None = None
    message: str
    error: Issue
    errors: list[Issue]
    meta: Meta


def _type_name(key: str) -> str:
    return "".join(part.capitalize() for part in key.replace("_", ".").split("."))


def ok_envelope(key: str) -> type[BaseModel]:
    """``{status: ok, function, result: <typed>, meta}`` for one ID."""
    return create_model(
        _type_name(key) + "Ok",
        __base__=_Out,
        status=(Literal["ok"], ...),
        function=(Literal[key], ...),  # type: ignore[valid-type]
        result=(OUTPUT_MODELS[key], ...),
        meta=(Meta, ...),
    )


def envelope_model(key: str) -> type[RootModel]:
    """Any answer of ``POST /v1/functions/{key}/run``: ok | needs_input | error."""
    root = RootModel[Union[ok_envelope(key), NeedsInputEnvelope, ErrorEnvelope]]  # type: ignore[valid-type]
    return type(_type_name(key) + "Response", (root,), {})
