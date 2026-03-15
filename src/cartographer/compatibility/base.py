"""Base compatibility checker interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from cartographer.config.loader import CartographerConfig
from cartographer.models import CheckResult


class CompatibilityChecker(ABC):
    """Base class for tool-specific compatibility checkers."""

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """The stack tool this checker validates against."""

    @abstractmethod
    def check(self, config: CartographerConfig, base_dir: Path) -> list[CheckResult]:
        """Run compatibility checks.

        Args:
            config: Cartographer configuration.
            base_dir: Root directory of the project being checked.

        Returns:
            List of check results.
        """
