"""Ledger artifact drafter — generates draft schemas from discovered models."""

from __future__ import annotations

from pathlib import Path

import yaml

from cartographer.drafters.base import Drafter
from cartographer.models import DiscoveredModel, DiscoveryResult


class LedgerDrafter(Drafter):
    def draft(self, result: DiscoveryResult, output_dir: Path) -> list[Path]:
        schemas_dir = output_dir / "ledger" / "schemas"
        backends_dir = output_dir / "ledger" / "backends"
        schemas_dir.mkdir(parents=True, exist_ok=True)
        backends_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []

        # Group models by ORM/backend
        by_orm: dict[str, list[DiscoveredModel]] = {}
        for model in result.models:
            orm = model.orm or "unknown"
            by_orm.setdefault(orm, []).append(model)

        # Generate backend drafts
        for orm, models in by_orm.items():
            backend = _orm_to_backend(orm)
            backend_draft = {
                "_draft": True,
                "_generated_by": "cartographer",
                "id": f"{orm}_backend",
                "type": backend,
                "description": f"Backend detected from {orm} model definitions",
                "_confidence": models[0].confidence.value,
                "_note": f"Detected {len(models)} {orm} models",
            }
            path = backends_dir / f"{orm}_backend_draft.yaml"
            with open(path, "w") as f:
                yaml.dump(backend_draft, f, default_flow_style=False, sort_keys=False)
            written.append(path)

        # Generate schema drafts per model
        for model in result.models:
            schema = _build_schema(model)
            orm = model.orm or "unknown"
            slug = model.name.lower()
            path = schemas_dir / f"{orm}_{slug}_draft.yaml"
            with open(path, "w") as f:
                yaml.dump(schema, f, default_flow_style=False, sort_keys=False)
            written.append(path)

        # Add env var hints
        if result.env_vars:
            hints = {
                "_draft": True,
                "_generated_by": "cartographer",
                "connection_hints": [
                    {
                        "env_var": ev.name,
                        "backend_hint": ev.backend_hint,
                        "source_file": ev.source_file,
                        "line": ev.line,
                        "_confidence": ev.confidence.value,
                    }
                    for ev in result.env_vars
                ],
            }
            path = backends_dir / "connection_hints_draft.yaml"
            with open(path, "w") as f:
                yaml.dump(hints, f, default_flow_style=False, sort_keys=False)
            written.append(path)

        return written


def _build_schema(model: DiscoveredModel) -> dict:
    fields = []
    for field in model.fields:
        entry: dict = {
            "name": field.name,
            "type": field.type,
            "_confidence": field.confidence.value,
        }
        if field.classification_hint:
            entry["classification"] = field.classification_hint
            entry["_classification_confidence"] = "low"
            entry["_note"] = "Classification from field name pattern — human must confirm"
        if field.note:
            entry["_note"] = field.note
        fields.append(entry)

    return {
        "_draft": True,
        "_generated_by": "cartographer",
        "model_name": model.name,
        "source_file": model.source_file,
        "line": model.line,
        "orm": model.orm,
        "_confidence": model.confidence.value,
        "fields": fields,
    }


def _orm_to_backend(orm: str) -> str:
    mapping = {
        "sqlalchemy": "postgres",
        "django": "postgres",
        "peewee": "sqlite",
        "tortoise": "postgres",
        "pydantic": "unknown",
        "prisma": "postgres",
        "typeorm": "postgres",
        "sequelize": "postgres",
        "mongoose": "mongodb",
        "drizzle": "postgres",
        "activerecord": "postgres",
        "sequel": "postgres",
        "gorm": "postgres",
        "sqlx": "postgres",
        "jpa": "postgres",
    }
    return mapping.get(orm, "unknown")
