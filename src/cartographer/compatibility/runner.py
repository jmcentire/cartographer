"""Compatibility check runner — orchestrates all checkers."""

from __future__ import annotations

from pathlib import Path

from cartographer.compatibility.base import CompatibilityChecker
from cartographer.compatibility.pact_checker import PactChecker
from cartographer.compatibility.baton_checker import BatonChecker
from cartographer.compatibility.ledger_checker import LedgerChecker
from cartographer.compatibility.arbiter_checker import ArbiterChecker
from cartographer.compatibility.sentinel_checker import SentinelChecker
from cartographer.config.loader import CartographerConfig
from cartographer.models import CheckResult


ALL_CHECKERS: list[type[CompatibilityChecker]] = [
    PactChecker,
    BatonChecker,
    LedgerChecker,
    ArbiterChecker,
    SentinelChecker,
]


def run_checks(
    config: CartographerConfig,
    base_dir: Path,
    tools: list[str] | None = None,
) -> list[CheckResult]:
    """Run compatibility checks for the specified tools (or all)."""
    results: list[CheckResult] = []

    for checker_cls in ALL_CHECKERS:
        checker = checker_cls()
        if tools and checker.tool_name not in tools:
            continue
        results.extend(checker.check(config, base_dir))

    return results
