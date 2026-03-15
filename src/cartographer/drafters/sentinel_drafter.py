"""Sentinel artifact drafter — generates draft manifest from discovered PACT keys."""

from __future__ import annotations

import json
from pathlib import Path

from cartographer.drafters.base import Drafter
from cartographer.models import DiscoveryResult


class SentinelDrafter(Drafter):
    def draft(self, result: DiscoveryResult, output_dir: Path) -> list[Path]:
        sentinel_dir = output_dir / "sentinel"
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []

        entries = []
        for pk in result.pact_keys:
            parts = pk.key.split(":")
            component_id = parts[1] if len(parts) >= 2 else "unknown"
            method_id = parts[2] if len(parts) >= 3 else "unknown"
            entries.append({
                "pact_key": pk.key,
                "component_id": component_id,
                "method_id": method_id,
                "source_file": pk.source_file,
                "line": pk.line,
                "contract_path": None,
                "test_path": None,
                "_confidence": pk.confidence.value,
            })

        manifest = {
            "_draft": True,
            "_generated_by": "cartographer",
            "entries": entries,
        }
        if not entries:
            manifest["_note"] = (
                "No PACT keys found in source. PACT key emission is not yet "
                "implemented in this codebase."
            )

        path = sentinel_dir / "manifest_draft.json"
        with open(path, "w") as f:
            json.dump(manifest, f, indent=2)
        written.append(path)

        return written
