import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, Column, MetaData, String, Table, Text, create_engine, select, update
from sqlalchemy.exc import IntegrityError

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

    def __init__(self, url: str):
        self.engine = create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 30}
            if url.startswith("sqlite")
            else {},
        )
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
        query = select(runs.c.id)
        if public_only:
            query = query.where(runs.c.public.is_(True))
        with self.engine.connect() as conn:
            ids: list[str] = list(conn.execute(query).scalars().all())
        return sorted((self.get(i) for i in ids), key=lambda r: r["created_at"], reverse=True)[:100]

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
        for data in self.list():
            if data["status"] in {"queued", "planning", "running", "approved"}:
                data["failure_category"] = "process_interrupted"
                self.save(data, "interrupted")
