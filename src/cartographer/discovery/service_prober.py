"""Service prober — discovers API structure from running services and OpenAPI specs."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import yaml

from cartographer.models import (
    Confidence,
    ComponentType,
    DiscoveredComponent,
    DiscoveredRoute,
    DiscoveryResult,
)


OPENAPI_PATHS = [
    "/openapi.json",
    "/api/openapi.json",
    "/docs/openapi.json",
    "/swagger.json",
    "/api-docs",
    "/v1/openapi.json",
    "/v2/openapi.json",
]


def probe_service(base_url: str) -> DiscoveryResult:
    """Probe a running service for its OpenAPI spec.

    Tries common OpenAPI spec paths. Read-only HTTP GET requests only.
    """
    result = DiscoveryResult()

    spec = None
    for path in OPENAPI_PATHS:
        url = base_url.rstrip("/") + path
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                content = resp.read().decode("utf-8")
                spec = json.loads(content)
                break
        except Exception:
            continue

    if spec is None:
        return result

    return _parse_openapi(spec, base_url)


def load_openapi_file(path: Path) -> DiscoveryResult:
    """Load and parse an OpenAPI spec file."""
    content = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        spec = yaml.safe_load(content)
    else:
        spec = json.loads(content)

    return _parse_openapi(spec, f"file://{path}")


def probe_services(
    base_urls: list[str],
    openapi_paths: list[str],
) -> DiscoveryResult:
    """Probe all configured services and OpenAPI spec files."""
    result = DiscoveryResult()

    for url in base_urls:
        service_result = probe_service(url)
        result.routes.extend(service_result.routes)
        result.components.extend(service_result.components)

    for spec_path in openapi_paths:
        p = Path(spec_path)
        if p.exists():
            spec_result = load_openapi_file(p)
            result.routes.extend(spec_result.routes)
            result.components.extend(spec_result.components)

    return result


def _parse_openapi(spec: dict, source: str) -> DiscoveryResult:
    """Parse an OpenAPI spec into routes and components."""
    result = DiscoveryResult()

    info = spec.get("info", {})
    title = info.get("title", "unknown")

    # Extract routes from paths
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.startswith("x-") or method == "parameters":
                continue
            if not isinstance(operation, dict):
                continue

            handler = operation.get("operationId", f"{method}_{path}")
            result.routes.append(DiscoveredRoute(
                path=path,
                method=method.upper(),
                handler=handler,
                source_file=source,
                line=0,
                framework="openapi",
                confidence=Confidence.HIGH,
            ))

    # Create a component for the service
    servers = spec.get("servers", [])
    port = None
    if servers:
        server_url = servers[0].get("url", "")
        if ":" in server_url.split("/")[-1]:
            try:
                port = int(server_url.split(":")[-1].split("/")[0])
            except ValueError:
                pass

    result.components.append(DiscoveredComponent(
        name=title,
        source_file=source,
        line=0,
        type=ComponentType.SERVICE,
        public_methods=[r.handler for r in result.routes],
        confidence=Confidence.HIGH,
        note=f"Discovered from OpenAPI spec: {info.get('version', 'unknown')}",
    ))

    return result
