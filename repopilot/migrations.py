"""Additive, versioned migrations for owner sessions and private planning state."""

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, text
from sqlalchemy.engine import Engine

from repopilot.store import now, runs

owner_metadata = MetaData()
versions = Table(
    "schema_versions",
    owner_metadata,
    Column("version", Integer, primary_key=True),
    Column("applied_at", String(40), nullable=False),
)
sessions = Table(
    "owner_sessions",
    owner_metadata,
    Column("digest", String(64), primary_key=True),
    Column("expires", Integer, nullable=False),
)
private_runs = Table(
    "engineering_runs",
    owner_metadata,
    Column("id", String(32), primary_key=True),
    Column("created_at", String(40), nullable=False),
    Column("request_key", String(80), unique=True, nullable=False),
    Column("fingerprint", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("payload", Text, nullable=False),
)
budgets = Table(
    "model_budgets",
    owner_metadata,
    Column("day", String(10), primary_key=True),
    Column("reserved", Integer, nullable=False),
)


def migrate(engine: Engine) -> None:
    # Single service process; migrations run before accepting traffic.
    owner_metadata.create_all(engine)
    with engine.begin() as conn:
        schema = engine.get_execution_options().get("schema_translate_map", {}).get(None)
        if schema:
            # Only the explicitly selected private schema; never change shared public tables.
            quote = engine.dialect.identifier_preparer.quote
            roles: list[str] = list(
                conn.execute(
                    text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")
                ).scalars()
            )
            grantees = ", ".join(["PUBLIC", *(quote(role) for role in roles)])
            conn.exec_driver_sql(f"REVOKE ALL ON SCHEMA {quote(schema)} FROM {grantees}")
            for table in [runs, *owner_metadata.tables.values()]:
                qualified = f"{quote(schema)}.{quote(table.name)}"
                conn.exec_driver_sql(f"ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY")
                conn.exec_driver_sql(f"REVOKE ALL ON TABLE {qualified} FROM {grantees}")
        if conn.execute(versions.select().where(versions.c.version == 2)).first() is None:
            conn.execute(versions.insert().values(version=2, applied_at=now()))
