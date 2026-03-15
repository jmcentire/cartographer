"""Redis live introspection — read-only key pattern discovery."""

from __future__ import annotations

from collections import Counter

from cartographer.models import (
    Confidence,
    DiscoveredField,
    DiscoveredModel,
)


def introspect_redis(connection_hint: str, backend_id: str, sample_size: int = 1000) -> list[DiscoveredModel]:
    """Introspect a Redis instance by sampling keys with SCAN.

    Uses SCAN (not KEYS) to avoid blocking. Never writes to Redis.
    """
    try:
        import redis as redis_lib
    except ImportError:
        raise ImportError("Install redis support: pip install cartographer[redis]")

    client = redis_lib.from_url(connection_hint)

    # Sample keys using SCAN (non-blocking)
    patterns: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    sampled = 0

    for key in client.scan_iter(count=100):
        if sampled >= sample_size:
            break
        sampled += 1

        key_str = key.decode("utf-8", errors="replace") if isinstance(key, bytes) else str(key)
        pattern = _generalize_key(key_str)
        patterns[pattern] += 1

        try:
            key_type = client.type(key)
            type_str = key_type.decode() if isinstance(key_type, bytes) else str(key_type)
            type_counts[type_str] += 1
        except Exception:
            pass

    # Build models from key patterns
    models: list[DiscoveredModel] = []
    for pattern, count in patterns.most_common(50):
        fields = [
            DiscoveredField(
                name="key_pattern",
                type="string",
                confidence=Confidence.MEDIUM,
                note=f"Sampled {count} keys matching this pattern",
            ),
        ]
        models.append(DiscoveredModel(
            name=pattern,
            source_file=f"redis://{backend_id}",
            line=0,
            orm="redis",
            fields=fields,
            confidence=Confidence.MEDIUM,
        ))

    return models


def _generalize_key(key: str) -> str:
    """Generalize a Redis key by replacing numeric/UUID segments with wildcards."""
    import re
    parts = key.split(":")
    generalized = []
    for part in parts:
        if re.match(r"^\d+$", part):
            generalized.append("*")
        elif re.match(r"^[0-9a-f-]{36}$", part, re.IGNORECASE):
            generalized.append("*")
        elif re.match(r"^[0-9a-f]{24}$", part, re.IGNORECASE):
            generalized.append("*")
        else:
            generalized.append(part)
    return ":".join(generalized)
