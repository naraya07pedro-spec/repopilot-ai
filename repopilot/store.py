import json
import uuid
from datetime import UTC, datetime
from heapq import nlargest
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    inspect,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from repopilot.database import validate_database
from repopilot.policy import PolicyError, digest

metadata = MetaData()
runs = Table(
    "runs",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("key", String(100), unique=True, nullable=False),
    Column("fingerprint", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("public", Boolean, nullable=False),
    Column("cancelled", Boolean, nullable=False, default=False),
    Column("payload", Text, nullable=False),
)


def now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    """One table, unique admission key and compare-and-swap transitions.

    SQLite is the zero-service local path; PostgreSQL uses the same SQLAlchemy schema.
    Schema version 1 is additive create_all; future changes require migrations.
    """

    def __init__(self, url: str, schema: str | None = None, production: bool = False):
        validate_database(url, schema, production)
        self.engine = create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 30}
            if url.startswith("sqlite")
            else {"connect_timeout": 10},
            pool_pre_ping=True,
        )
        if schema:
            if not inspect(self.engine).has_schema(schema):
                self.engine.dispose()
                raise ValueError("private_database_schema_missing")
            self.engine.update_execution_options(schema_translate_map={None: schema})
        metadata.create_all(self.engine)

    def create(
        self, key: str, request: dict[str, Any], public: bool
    ) -> tuple[dict[str, Any], bool]:
        fingerprint = digest(request)
        identity = uuid.uuid4().hex
        data = {
            "id": identity,
            "scenario": request["scenario"],
            "created_at": now(),
            "provider": "deterministic-fixture",
            "events": [],
            "checks": [],
            "attempts": 0,
            "limitations": [
                "Only audited fixture bytes execute on the host.",
                "Deterministic provider does not establish live model quality.",
                "Human review is required before merge.",
            ],
        }
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    runs.insert().values(
                        id=identity,
                        key=key,
                        fingerprint=fingerprint,
                        status="queued",
                        public=public,
                        cancelled=False,
                        payload=json.dumps(data),
                    )
                )
            return self.get(identity), True
        except IntegrityError:
            with self.engine.connect() as conn:
                row = conn.execute(select(runs).where(runs.c.key == key)).mappings().one()
            if row["fingerprint"] != fingerprint or row["public"] != public:
                raise PolicyError("idempotency_conflict") from None
            return self.get(row["id"]), False

    def get(self, identity: str) -> dict[str, Any]:
        with self.engine.connect() as conn:
            row = conn.execute(select(runs).where(runs.c.id == identity)).mappings().first()
        if row is None:
            raise KeyError(identity)
        return {
            **json.loads(row["payload"]),
            "status": row["status"],
            "public": row["public"],
            "cancel_requested": row["cancelled"],
        }

    def list(self, public_only: bool = False) -> list[dict[str, Any]]:
        # Read each persisted row once; do not issue N extra queries to show
        # the newest 100. The schema has no indexed created_at column, so
        # this still scans matching rows; it is not cursor-based pagination.
        query = select(runs.c.payload, runs.c.status, runs.c.public, runs.c.cancelled)
        if public_only:
            query = query.where(runs.c.public.is_(True))
        with self.engine.connect() as conn:
            records = (
                {
                    **json.loads(row["payload"]),
                    "status": row["status"],
                    "public": row["public"],
                    "cancel_requested": row["cancelled"],
                }
                for row in conn.execute(query).mappings()
            )
            return nlargest(100, records, key=lambda data: data["created_at"])

    def save(self, data: dict[str, Any], status: str | None = None) -> None:
        fields: dict[str, Any] = {"payload": json.dumps(data)}
        if status:
            fields["status"] = status
        with self.engine.begin() as conn:
            conn.execute(update(runs).where(runs.c.id == data["id"]).values(**fields))

    def claim(self, identity: str, before: str, after: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                update(runs)
                .where(runs.c.id == identity, runs.c.status == before, runs.c.cancelled.is_(False))
                .values(status=after)
            )
            return result.rowcount == 1

    def cancel(self, identity: str) -> None:
        self.get(identity)
        with self.engine.begin() as conn:
            conn.execute(
                update(runs)
                .where(
                    runs.c.id == identity,
                    runs.c.status.in_(
                        ["queued", "planning", "awaiting_approval", "approved", "running"]
                    ),
                )
                .values(cancelled=True)
            )
        data = self.get(identity)
        if data["status"] in {"queued", "awaiting_approval", "approved"}:
            self.save(data, "cancelled")

    def recover(self) -> None:
        # Single service process only. Interrupted work never silently retries.
        # The public list API is intentionally limited to 100 entries; recovery
        # must not inherit that presentation limit or strand older pending runs.
        pending = ("queued", "planning", "running", "approved")
        while True:
            with self.engine.connect() as conn:
                ids: list[str] = list(
                    conn.execute(
                        select(runs.c.id).where(runs.c.status.in_(pending)).limit(100)
                    ).scalars()
                )
            if not ids:
                break
            for identity in ids:
                data = self.get(identity)
                if data["status"] in pending:
                    data["failure_category"] = "process_interrupted"
                    self.save(data, "interrupted")
