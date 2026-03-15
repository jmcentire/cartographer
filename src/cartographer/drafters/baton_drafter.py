"""Baton artifact drafter — generates draft topology from discovered routes and components."""

from __future__ import annotations

from pathlib import Path

import yaml

from cartographer.drafters.base import Drafter
from cartographer.models import DiscoveryResult


class BatonDrafter(Drafter):
    def draft(self, result: DiscoveryResult, output_dir: Path) -> list[Path]:
        baton_dir = output_dir / "baton"
        baton_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []

        nodes = []
        edges = []
        seen_nodes: set[str] = set()

        # Build nodes from routes (these are services with HTTP endpoints)
        route_groups: dict[str, list] = {}
        for route in result.routes:
            key = route.framework + ":" + route.source_file
            route_groups.setdefault(key, []).append(route)

        for key, routes in route_groups.items():
            framework = routes[0].framework
            source = routes[0].source_file
            name = _derive_node_name(source)
            if name in seen_nodes:
                continue
            seen_nodes.add(name)
            nodes.append({
                "_draft": True,
                "_generated_by": "cartographer",
                "name": name,
                "type": "service",
                "port": None,
                "protocol": "http",
                "framework": framework,
                "source_file": source,
                "_confidence": "high",
                "_note": f"Detected {len(routes)} {framework} routes",
                "routes": [
                    {"path": r.path, "method": r.method}
                    for r in routes
                ],
                "data_access": {
                    "_note": "Must be filled by human",
                },
                "authority": {
                    "_note": "Must be filled by human",
                },
            })

        # Build nodes from components that aren't already route-based services
        for component in result.components:
            name = component.name.lower()
            if name in seen_nodes:
                continue
            seen_nodes.add(name)
            nodes.append({
                "_draft": True,
                "_generated_by": "cartographer",
                "name": name,
                "type": component.type.value,
                "port": None,
                "protocol": None,
                "source_file": component.source_file,
                "_confidence": component.confidence.value,
            })

            # Infer edges from dependencies
            for dep in component.dependencies:
                dep_lower = dep.lower()
                if dep_lower in seen_nodes:
                    edges.append({
                        "from": name,
                        "to": dep_lower,
                        "protocol": None,
                        "_confidence": "medium",
                        "_note": "Inferred from constructor parameter",
                    })

        topology = {
            "_draft": True,
            "_generated_by": "cartographer",
            "version": "2.0",
            "nodes": nodes,
            "edges": edges,
        }

        path = baton_dir / "baton_draft.yaml"
        with open(path, "w") as f:
            yaml.dump(topology, f, default_flow_style=False, sort_keys=False)
        written.append(path)

        return written


def _derive_node_name(source_file: str) -> str:
    """Derive a node name from a source file path."""
    import re
    from pathlib import Path as P

    stem = P(source_file).stem
    # Remove common suffixes
    for suffix in ("_controller", "_handler", "_router", "_routes", "_api", "_view"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return re.sub(r"[^a-z0-9_]", "_", stem.lower())
