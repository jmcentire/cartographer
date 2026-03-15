"""Live backend introspection orchestrator."""

from __future__ import annotations

import sys

from cartographer.config.loader import BackendConfig
from cartographer.models import DiscoveredModel


BACKEND_INTROSPECTORS = {
    "postgres": "cartographer.discovery.live.postgres:introspect_postgres",
    "mysql": "cartographer.discovery.live.postgres:introspect_postgres",  # Same schema approach
    "redis": "cartographer.discovery.live.redis_scanner:introspect_redis",
    "mongodb": "cartographer.discovery.live.mongodb:introspect_mongodb",
    "kafka": "cartographer.discovery.live.kafka:introspect_kafka",
}

# Backends that sample from queues and need production warnings
QUEUE_BACKENDS = {"sqs", "rabbitmq"}


def introspect_backends(backends: list[BackendConfig]) -> list[DiscoveredModel]:
    """Run introspection on all configured backends.

    All operations are read-only. Never writes to any backend.
    """
    all_models: list[DiscoveredModel] = []

    for backend in backends:
        if backend.type in QUEUE_BACKENDS:
            print(
                f"WARNING: Introspecting {backend.type} backend '{backend.id}' "
                f"involves sampling from a production queue. Messages may be "
                f"consumed and not re-queued depending on configuration. "
                f"Skipping — use --force-queue-sampling to override.",
                file=sys.stderr,
            )
            continue

        introspector_path = BACKEND_INTROSPECTORS.get(backend.type)
        if introspector_path is None:
            print(
                f"No introspector for backend type '{backend.type}' ({backend.id}). Skipping.",
                file=sys.stderr,
            )
            continue

        module_path, func_name = introspector_path.rsplit(":", 1)
        try:
            import importlib
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
        except ImportError as e:
            print(f"Cannot introspect {backend.id}: {e}", file=sys.stderr)
            continue

        try:
            kwargs: dict = {
                "connection_hint": backend.connection_hint,
                "backend_id": backend.id,
            }
            if backend.type == "kafka" and backend.schema_registry_url:
                kwargs["schema_registry_url"] = backend.schema_registry_url

            models = func(**kwargs)
            all_models.extend(models)
        except Exception as e:
            print(f"Error introspecting {backend.id}: {e}", file=sys.stderr)

    return all_models
