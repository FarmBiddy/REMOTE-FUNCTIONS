"""Layer import boundaries: Core / Agriculture / Dairy dependency direction."""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FARM = REPO / "farm_functions"

_ORCHESTRATION_FORBIDDEN = (
    "farm_functions.calcs",
    "farm_functions.domain",
    "farm_functions.schemas",
    "farm_functions.provenance",
    "farm_functions.simulation",
    "farm_functions.scenarios",
    "farm_functions.loaders",
    "farm_functions.registry",
    "farm_functions.runner",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _py_files(package: Path) -> list[Path]:
    return sorted(p for p in package.rglob("*.py") if p.is_file())


def _assert_no_forbidden(package: Path, forbidden_prefixes: tuple[str, ...]) -> None:
    for path in _py_files(package):
        for name in _imported_modules(path):
            assert not any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in forbidden_prefixes
            ), f"{path.relative_to(REPO)} imports {name}"


def test_core_does_not_import_agriculture_or_dairy_or_calcs() -> None:
    _assert_no_forbidden(
        FARM / "core",
        ("farm_functions.agriculture", "farm_functions.dairy", *_ORCHESTRATION_FORBIDDEN),
    )


def test_agriculture_does_not_import_dairy_or_calcs() -> None:
    _assert_no_forbidden(
        FARM / "agriculture",
        ("farm_functions.dairy", *_ORCHESTRATION_FORBIDDEN),
    )


def test_dairy_does_not_import_orchestration() -> None:
    _assert_no_forbidden(FARM / "dairy", _ORCHESTRATION_FORBIDDEN)


def test_agriculture_scheme_revenue_matches_legacy_sum() -> None:
    from farm_functions.agriculture import scheme_revenue
    from farm_functions.calcs.revenue import scheme_revenue as via_calcs

    assert scheme_revenue(biss=20_000, acres=5_000, other_grants=0) == 25_000
    assert via_calcs(biss=20_000, acres=5_000) == 25_000
    assert scheme_revenue is via_calcs


def test_core_surplus_matches_calcs_profit_reexport() -> None:
    from farm_functions.calcs.profit import net_profit as via_calcs
    from farm_functions.core import net_profit

    assert net_profit(240_000, 163_000) == 77_000
    assert via_calcs(240_000, 163_000) == 77_000
    assert net_profit is via_calcs


def test_dairy_milk_revenue_is_canonical_calcs_reexport() -> None:
    from farm_functions.calcs.revenue import milk_revenue as via_calcs
    from farm_functions.dairy.revenue import milk_revenue

    assert milk_revenue(100, 5000, 0.40) == 200_000
    assert via_calcs(100, 5000, 0.40) == 200_000
    assert milk_revenue is via_calcs


def test_dairy_costs_and_statement_reexport_identity() -> None:
    from farm_functions.calcs.costs import OPERATING_COST_CATEGORIES as via_calcs_cats
    from farm_functions.calcs.costs import total_costs as via_calcs_costs
    from farm_functions.calcs.summary import pl_summary as via_calcs_pl
    from farm_functions.dairy.costs import OPERATING_COST_CATEGORIES, total_costs
    from farm_functions.dairy.statement import pl_summary

    assert OPERATING_COST_CATEGORIES is via_calcs_cats
    assert total_costs is via_calcs_costs
    assert pl_summary is via_calcs_pl
    assert "water" in OPERATING_COST_CATEGORIES
    assert "feed" in OPERATING_COST_CATEGORIES


def test_sample_pl_summary_reference_unchanged() -> None:
    from farm_functions.loaders.json_loader import load_sample_inputs
    from farm_functions.runner import run_function

    result = run_function("pl.summary", load_sample_inputs())["result"]
    assert result["revenue"]["total"] == 240_000.0
    assert result["costs"]["total"] == 163_000.0
    assert result["profit"]["net"] == 77_000.0
    assert result["profit"]["margin_pct"] == 32.08
    assert result["finance"]["loan_repayments"] == 12_000.0
