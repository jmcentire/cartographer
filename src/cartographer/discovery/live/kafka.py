"""Kafka live introspection — read-only topic and schema discovery."""

from __future__ import annotations

from cartographer.models import (
    Confidence,
    DiscoveredField,
    DiscoveredModel,
)


def introspect_kafka(
    connection_hint: str,
    backend_id: str,
    schema_registry_url: str | None = None,
) -> list[DiscoveredModel]:
    """Introspect a Kafka cluster for topics and schemas.

    Uses AdminClient for topic listing (read-only).
    Uses Schema Registry HTTP API if available.
    Never produces or consumes messages.
    """
    try:
        from confluent_kafka.admin import AdminClient
    except ImportError:
        raise ImportError("Install kafka support: pip install cartographer[kafka]")

    # Parse bootstrap servers from connection hint
    bootstrap = connection_hint.replace("kafka://", "")
    admin = AdminClient({"bootstrap.servers": bootstrap})

    # List topics
    metadata = admin.list_topics(timeout=10)
    models: list[DiscoveredModel] = []

    for topic_name, topic_metadata in sorted(metadata.topics.items()):
        if topic_name.startswith("__"):  # Skip internal topics
            continue

        fields = [
            DiscoveredField(
                name="partitions",
                type=f"int({len(topic_metadata.partitions)})",
                confidence=Confidence.HIGH,
            ),
        ]

        # Try schema registry if available
        if schema_registry_url:
            schema_fields = _fetch_schema(schema_registry_url, topic_name)
            fields.extend(schema_fields)

        models.append(DiscoveredModel(
            name=topic_name,
            source_file=f"kafka://{backend_id}/{topic_name}",
            line=0,
            orm="kafka",
            fields=fields,
            confidence=Confidence.HIGH,
        ))

    return models


def _fetch_schema(registry_url: str, topic: str) -> list[DiscoveredField]:
    """Fetch schema fields from Confluent Schema Registry."""
    import json
    import urllib.request

    fields: list[DiscoveredField] = []
    for suffix in ["-value", "-key"]:
        url = f"{registry_url}/subjects/{topic}{suffix}/versions/latest"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                schema = json.loads(data.get("schema", "{}"))
                if schema.get("type") == "record":
                    for field_def in schema.get("fields", []):
                        field_type = field_def.get("type", "unknown")
                        if isinstance(field_type, list):
                            field_type = "|".join(str(t) for t in field_type)
                        elif isinstance(field_type, dict):
                            field_type = field_type.get("type", "complex")
                        fields.append(DiscoveredField(
                            name=field_def["name"],
                            type=str(field_type),
                            confidence=Confidence.HIGH,
                            note=f"From schema registry ({suffix})",
                        ))
        except Exception:
            pass

    return fields
