"""Pact artifact drafter — generates draft contracts from discovered components."""

from __future__ import annotations

from pathlib import Path

import yaml

from cartographer.drafters.base import Drafter
from cartographer.models import DiscoveredComponent, DiscoveryResult


class PactDrafter(Drafter):
    def draft(self, result: DiscoveryResult, output_dir: Path) -> list[Path]:
        contracts_dir = output_dir / "pact" / "contracts"
        contracts_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []

        for component in result.components:
            contract = _build_contract(component)
            path = contracts_dir / f"{_slugify(component.name)}_draft.yaml"
            with open(path, "w") as f:
                yaml.dump(contract, f, default_flow_style=False, sort_keys=False)
            written.append(path)

        # Task draft
        if result.components:
            task_path = output_dir / "pact" / "task_draft.md"
            task_path.parent.mkdir(parents=True, exist_ok=True)
            with open(task_path, "w") as f:
                f.write(_build_task(result))
            written.append(task_path)

        return written


def _build_contract(component: DiscoveredComponent) -> dict:
    return {
        "_draft": True,
        "_generated_by": "cartographer",
        "component_id": _slugify(component.name),
        "name": component.name,
        "type": component.type.value,
        "source_file": component.source_file,
        "interface": {
            method: {
                "_confidence": component.confidence.value,
                "_note": "Derived from public method signature",
                "params": {},
                "returns": {},
            }
            for method in component.public_methods
        },
        "data_access": {
            "_confidence": "low",
            "_note": "Must be filled by human — cannot be inferred from source",
            "reads": [],
            "writes": [],
            "rationale": "",
        },
        "authority": {
            "_confidence": "low",
            "_note": "Must be filled by human — cannot be inferred from source",
            "domains": [],
            "rationale": "",
        },
        "dependencies": component.dependencies,
    }


def _build_task(result: DiscoveryResult) -> str:
    component_names = [c.name for c in result.components[:20]]
    return (
        "# Task\n\n"
        "## System\n\n"
        f"Discovered {len(result.components)} components, "
        f"{len(result.models)} data models, "
        f"{len(result.routes)} API routes.\n\n"
        "## Components\n\n"
        + "\n".join(f"- {name}" for name in component_names)
        + "\n\n## Goal\n\n(Fill in the specific implementation goal)\n"
    )


def _slugify(name: str) -> str:
    import re
    # Convert CamelCase to snake_case
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    return re.sub(r"[^a-z0-9_]", "_", s)
