"""Layer import boundaries: Core and Agriculture must not depend on Dairy."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FARM = REPO / "farm_functions"


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


def test_core_does_not_import_agriculture_or_dairy_or_calcs() -> None:
    forbidden_prefixes = (
        "farm_functions.agriculture",
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
    for path in _py_files(FARM / "core"):
        for name in _imported_modules(path):
            assert not any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in forbidden_prefixes
            ), f"{path.name} imports {name}"


def test_agriculture_does_not_import_dairy_or_calcs() -> None:
    forbidden_prefixes = (
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
    for path in _py_files(FARM / "agriculture"):
        for name in _imported_modules(path):
            assert not any(
                name == prefix or name.startswith(prefix + ".")
                for prefix in forbidden_prefixes
            ), f"{path.name} imports {name}"
            assert not name.startswith("farm_functions.dairy"), f"{path.name} imports {name}"


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
