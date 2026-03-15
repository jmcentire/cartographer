"""Postgres live introspection — read-only schema discovery."""

from __future__ import annotations

from cartographer.models import (
    Confidence,
    DiscoveredField,
    DiscoveredModel,
)


def introspect_postgres(connection_hint: str, backend_id: str) -> list[DiscoveredModel]:
    """Introspect a Postgres database using information_schema.

    Uses read-only SELECT queries only. Never writes to the database.
    """
    try:
        import psycopg2
    except ImportError:
        raise ImportError("Install postgres support: pip install cartographer[postgres]")

    models: list[DiscoveredModel] = []

    conn = psycopg2.connect(connection_hint)
    try:
        conn.set_session(readonly=True)
        with conn.cursor() as cur:
            # Get all tables in public schema
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]

            for table in tables:
                cur.execute("""
                    SELECT column_name, data_type, is_nullable,
                           character_maximum_length, numeric_precision
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = %s
                    ORDER BY ordinal_position
                """, (table,))

                fields: list[DiscoveredField] = []
                for col_name, data_type, nullable, max_len, precision in cur.fetchall():
                    type_str = data_type
                    if max_len:
                        type_str = f"{data_type}({max_len})"
                    elif precision:
                        type_str = f"{data_type}({precision})"

                    fields.append(DiscoveredField(
                        name=col_name,
                        type=type_str,
                        confidence=Confidence.HIGH,
                        note=f"nullable={nullable}",
                    ))

                models.append(DiscoveredModel(
                    name=table,
                    source_file=f"postgres://{backend_id}/{table}",
                    line=0,
                    orm="postgres",
                    fields=fields,
                    confidence=Confidence.HIGH,
                ))
    finally:
        conn.close()

    return models
