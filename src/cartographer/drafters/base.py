"""Base drafter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from cartographer.models import DiscoveryResult


class Drafter(ABC):
    """Base class for artifact drafters."""

    @abstractmethod
    def draft(self, result: DiscoveryResult, output_dir: Path) -> list[Path]:
        """Generate draft artifacts from discovery results.

        Args:
            result: Aggregated discovery results.
            output_dir: Directory to write draft files.

        Returns:
            List of paths to generated draft files.
        """
