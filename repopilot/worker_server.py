"""Single-process loopback worker service; separate from the FastAPI owner process.

Uses a private SQLite journal to prevent replay across controller crashes. No model or
GitHub credentials belong here. The owner app does not activate this experimental runtime.
"""

import asyncio
import importlib
import json
import os
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from repopilot.policy import PolicyError, digest
from repopilot.sandbox import LinuxSandbox
from repopilot.worker_contract import Envelope, VerificationJob, authenticate, sign, validate_job


class WorkerManager:
    def __init__(self, database: Path, key: bytes, runtime: LinuxSandbox):
        if len(key) < 32:
            raise PolicyError("worker_auth_key_too_short")
        self.database, self.key, self.runtime = database, key, runtime
        self.events: dict[str, threading.Event] = {}
        self.lock = threading.Lock()
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS jobs "
                "(id TEXT PRIMARY KEY, digest TEXT NOT NULL, job TEXT NOT NULL, "
                "state TEXT NOT NULL, receipt TEXT)"
            )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.database, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def recover(self) -> None:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE state IN ('running','cancelling','interrupted')"
            ).fetchall()
        for row in rows:
            self.runtime.cleanup(VerificationJob.model_validate_json(row["job"]))
            with self.connect() as conn:
                conn.execute("UPDATE jobs SET state='recovered' WHERE id=?", (row["id"],))

    def execute(self, envelope: Envelope) -> Envelope:
        job = validate_job(envelope, self.key)
        fingerprint = digest(job.model_dump())
        with self.lock, self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT * FROM jobs WHERE id=?", (job.run_id,)).fetchone()
            if existing:
                if existing["digest"] != fingerprint:
                    raise PolicyError("worker_replay_conflict")
                if existing["receipt"]:
                    return Envelope.model_validate_json(existing["receipt"])
                raise PolicyError("worker_outcome_unknown_no_replay")
            if conn.execute(
                "SELECT 1 FROM jobs WHERE state IN ('running','cancelling','interrupted')"
            ).fetchone():
                raise PolicyError("worker_busy_or_recovery_required")
            if conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] >= 10000:
                raise PolicyError("worker_journal_capacity")
            conn.execute(
                "INSERT INTO jobs VALUES (?,?,?,'running',NULL)",
                (job.run_id, fingerprint, job.model_dump_json()),
            )
            self.events[job.run_id] = cancel = threading.Event()
        try:
            receipt = self.runtime.run(job, cancel)
            # Runtime implementation cannot accidentally sign a receipt for a different job.
            if (
                receipt.run_id != job.run_id
                or receipt.nonce != job.nonce
                or receipt.job_digest != fingerprint
            ):
                raise PolicyError("worker_runtime_receipt_mismatch")
            with self.lock, self.connect() as conn:
                if cancel.is_set() and receipt.outcome != "cancelled":
                    raise PolicyError("worker_cancel_unconfirmed")
                response = sign(receipt.model_dump(), self.key, "receipt")
                changed = conn.execute(
                    "UPDATE jobs SET state='finished',receipt=? WHERE id=? "
                    "AND state IN ('running','cancelling')",
                    (response.model_dump_json(), job.run_id),
                )
                if changed.rowcount != 1:
                    raise PolicyError("worker_execution_claim_lost")
                return response
        except Exception:
            with self.connect() as conn:
                conn.execute(
                    "UPDATE jobs SET state='interrupted' WHERE id=? "
                    "AND state IN ('running','cancelling')",
                    (job.run_id,),
                )
            raise PolicyError("worker_interrupted: operator recovery required") from None
        finally:
            with self.lock:
                self.events.pop(job.run_id, None)

    def shutdown(self) -> None:
        with self.lock:
            for event in self.events.values():
                event.set()
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            with self.lock:
                if not self.events:
                    return
            threading.Event().wait(0.05)
        raise PolicyError("worker_shutdown_unconfirmed")

    def cancel(self, envelope: Envelope) -> Envelope:
        authenticate(envelope, self.key, "cancel")
        body = envelope.payload
        if set(body) != {"run_id", "nonce", "job_digest", "expires_at"}:
            raise PolicyError("worker_cancel_identity")
        with self.lock, self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (body["run_id"],)).fetchone()
            if not row:
                raise PolicyError("worker_cancel_unknown")
            job = VerificationJob.model_validate_json(row["job"])
            if body != {
                "run_id": job.run_id,
                "nonce": job.nonce,
                "job_digest": row["digest"],
                "expires_at": job.expires_at,
            }:
                raise PolicyError("worker_cancel_identity")
            if row["receipt"]:
                return Envelope.model_validate_json(row["receipt"])
            event = self.events.get(job.run_id)
            if not event:
                raise PolicyError("worker_cancel_requires_recovery")
            conn.execute("UPDATE jobs SET state='cancelling' WHERE id=?", (job.run_id,))
            event.set()
        # Wait for runtime-confirmed teardown. A request alone is never a cancelled receipt.
        for _ in range(200):
            with self.connect() as conn:
                row = conn.execute("SELECT * FROM jobs WHERE id=?", (job.run_id,)).fetchone()
            if row["receipt"]:
                return Envelope.model_validate_json(row["receipt"])
            if row["state"] == "interrupted":
                break
            threading.Event().wait(0.05)
        raise PolicyError("worker_cancel_unconfirmed")


def routes(manager: WorkerManager) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ready", "isolation": "requires_host_validation"}

    @app.post("/v1/{operation}")
    async def dispatch(operation: str, request: Request) -> dict[str, Any]:
        if operation not in {"execute", "cancel"}:
            raise HTTPException(404)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 256000:
                raise HTTPException(413)
        try:
            envelope = Envelope.model_validate(json.loads(raw))
            method = manager.execute if operation == "execute" else manager.cancel
            return (await asyncio.to_thread(method, envelope)).model_dump()
        except (ValueError, TypeError, KeyError, sqlite3.Error):
            raise HTTPException(
                409, "Worker rejected or interrupted request; inspect private journal"
            ) from None

    return app


def create_worker_app() -> FastAPI:
    runtime = LinuxSandbox(os.environ.get("REPOPILOT_WORKER_IMAGE", ""))
    runtime.preflight()  # Fails on Windows, rootful mode, missing cgroups/image/runtime.
    state = Path(os.environ["REPOPILOT_WORKER_STATE"]).resolve()
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    if state.stat().st_mode & 0o077:
        raise PolicyError("worker_state_must_be_private")
    key_path = Path(os.environ["REPOPILOT_WORKER_KEY_FILE"])
    if key_path.stat().st_mode & 0o077:
        raise PolicyError("worker_key_must_be_private")
    key = key_path.read_bytes()
    fcntl = importlib.import_module("fcntl")
    lock = (state / "controller.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    manager = WorkerManager(state / "jobs.db", key, runtime)
    manager.recover()
    app = routes(manager)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        try:
            yield
        finally:
            await asyncio.to_thread(manager.shutdown)
            lock.close()

    app.router.lifespan_context = lifespan
    return app
