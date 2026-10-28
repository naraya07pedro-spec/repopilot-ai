"""Additive, versioned migrations for owner sessions and private planning state."""

from sqlalchemy import Column, Integer, MetaData, String, Table, Text
from sqlalchemy.engine import Engine

from repopilot.store import now

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
        if conn.execute(versions.select().where(versions.c.version == 2)).first() is None:
            conn.execute(versions.insert().values(version=2, applied_at=now()))
