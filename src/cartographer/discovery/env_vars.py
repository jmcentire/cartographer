"""Environment variable scanner — detects backend connection hints."""

from __future__ import annotations

import re
from pathlib import Path

from cartographer.models import Confidence, DiscoveredEnvVar

# Patterns suggesting backend connections
BACKEND_ENV_PATTERNS: dict[str, str] = {
    r"DATABASE_URL": "postgres",
    r"DB_HOST": "postgres",
    r"DB_NAME": "postgres",
    r"POSTGRES_": "postgres",
    r"PG_": "postgres",
    r"MYSQL_": "mysql",
    r"REDIS_URL": "redis",
    r"REDIS_HOST": "redis",
    r"KAFKA_BROKERS?": "kafka",
    r"KAFKA_BOOTSTRAP": "kafka",
    r"RABBITMQ_URL": "rabbitmq",
    r"AMQP_URL": "rabbitmq",
    r"MONGO_URI": "mongodb",
    r"MONGODB_URI": "mongodb",
    r"MONGO_URL": "mongodb",
    r"AWS_S3_BUCKET": "s3",
    r"S3_BUCKET": "s3",
    r"DYNAMODB_": "dynamodb",
    r"SQS_QUEUE": "sqs",
    r"ELASTICSEARCH_": "elasticsearch",
    r"MEMCACHED_": "memcached",
}

# Generic env var access patterns per language
ENV_ACCESS_RE = re.compile(
    r"(?:"
    r"os\.environ(?:\.get)?\s*\[\s*['\"](\w+)['\"]"  # Python bracket
    r"|os\.environ\.get\s*\(\s*['\"](\w+)['\"]"  # Python .get()
    r"|os\.getenv\s*\(\s*['\"](\w+)['\"]"  # Python getenv
    r"|process\.env\.(\w+)"  # Node.js
    r"|ENV\[['\"](\w+)['\"]\]"  # Ruby
    r"|os\.Getenv\s*\(\s*\"(\w+)\""  # Go
    r"|System\.getenv\s*\(\s*\"(\w+)\""  # Java
    r")"
)


class EnvVarScanner:
    def scan(self, file_path: Path, content: str) -> list[DiscoveredEnvVar]:
        results: list[DiscoveredEnvVar] = []
        seen: set[str] = set()

        for i, line in enumerate(content.split("\n"), 1):
            for match in ENV_ACCESS_RE.finditer(line):
                # Extract the matched group (whichever alternative matched)
                name = next(g for g in match.groups() if g is not None)
                if name in seen:
                    continue
                seen.add(name)

                backend_hint = _match_backend(name)
                if backend_hint:
                    results.append(
                        DiscoveredEnvVar(
                            name=name,
                            source_file=str(file_path),
                            line=i,
                            backend_hint=backend_hint,
                            confidence=Confidence.MEDIUM,
                        )
                    )

        return results


def _match_backend(name: str) -> str | None:
    for pattern, backend in BACKEND_ENV_PATTERNS.items():
        if re.match(pattern, name, re.IGNORECASE):
            return backend
    return None
