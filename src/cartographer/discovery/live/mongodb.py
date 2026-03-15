"""MongoDB live introspection — read-only collection schema inference."""

from __future__ import annotations

from cartographer.models import (
    Confidence,
    DiscoveredField,
    DiscoveredModel,
)


def introspect_mongodb(
    connection_hint: str,
    backend_id: str,
    sample_size: int = 100,
) -> list[DiscoveredModel]:
    """Introspect a MongoDB database by sampling documents.

    Uses find() with limit — equivalent to SCAN, no full collection lock.
    Never writes to MongoDB.
    """
    try:
        from pymongo import MongoClient
    except ImportError:
        raise ImportError("Install mongodb support: pip install cartographer[mongo]")

    client = MongoClient(connection_hint)
    db = client.get_default_database()
    models: list[DiscoveredModel] = []

    for collection_name in sorted(db.list_collection_names()):
        if collection_name.startswith("system."):
            continue

        collection = db[collection_name]
        field_types: dict[str, set[str]] = {}
        sampled = 0

        # Sample documents (find with limit, not aggregate)
        for doc in collection.find().limit(sample_size):
            sampled += 1
            _extract_fields(doc, field_types, prefix="")

        if sampled == 0:
            continue

        fields: list[DiscoveredField] = []
        for field_name, types in sorted(field_types.items()):
            type_str = "|".join(sorted(types))
            fields.append(DiscoveredField(
                name=field_name,
                type=type_str,
                confidence=Confidence.MEDIUM,
                note=f"Inferred from {sampled} sampled documents",
            ))

        models.append(DiscoveredModel(
            name=collection_name,
            source_file=f"mongodb://{backend_id}/{collection_name}",
            line=0,
            orm="mongodb",
            fields=fields,
            confidence=Confidence.MEDIUM,
        ))

    client.close()
    return models


def _extract_fields(doc: dict, field_types: dict[str, set[str]], prefix: str) -> None:
    """Recursively extract field names and types from a document."""
    for key, value in doc.items():
        full_key = f"{prefix}.{key}" if prefix else key
        type_name = type(value).__name__
        field_types.setdefault(full_key, set()).add(type_name)
        if isinstance(value, dict):
            _extract_fields(value, field_types, full_key)
