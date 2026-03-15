"""Base scanner plugin interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from cartographer.models import DiscoveryResult


class ScannerPlugin(ABC):
    """Base class for language-specific source code scanners."""

    @abstractmethod
    def scan(self, file_path: Path, content: str) -> DiscoveryResult:
        """Scan a single file and return discovered items.

        Args:
            file_path: Path to the source file.
            content: File content as a string.

        Returns:
            DiscoveryResult with models, routes, and components found.
        """
