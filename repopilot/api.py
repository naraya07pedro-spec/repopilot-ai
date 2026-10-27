import hmac
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from repopilot.engine import Engine
from repopilot.models import Approval, RunRequest
from repopilot.policy import PolicyError
from repopilot.store import Store


class DemoRequest(BaseModel):
    scenario: Literal["bug", "feature", "failure"]
    idempotency_key: str


def create_app(
    database_url: str | None = None,
    workspace: Path | None = None,
    api_key: str | None = None,
) -> FastAPI:
    root = workspace or Path(os.environ.get("REPOPILOT_DATA", ".repopilot")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    store = Store(database_url or os.environ.get("DATABASE_URL", f"sqlite:///{root / 'runs.db'}"))
    engine = Engine(store, root / "workspaces")
    key = api_key if api_key is not None else os.environ.get("REPOPILOT_API_KEY", "")
    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="repopilot")
    slots = threading.BoundedSemaphore(2)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
        store.recover()
        yield
        pool.shutdown(wait=True)
        store.engine.dispose()

    app = FastAPI(title="RepoPilot AI", version="0.1.0", lifespan=lifespan)
    app.state.store, app.state.engine = store, engine

    def authorized(authorization: Annotated[str | None, Header()] = None) -> None:
        if not key or not hmac.compare_digest(authorization or "", "Bearer " + key):
            raise HTTPException(401, "Operator authentication required")

    def lookup(identity: str, public: bool = False) -> dict[str, Any]:
        try:
            data = store.get(identity)
        except KeyError:
            raise HTTPException(404, "Run not found") from None
        if public and not data["public"]:
            raise HTTPException(404, "Run not found")
        return data

    def dispatch(identity: str, action: str) -> None:
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "Two runs are already active; retry later")

        def work() -> None:
            try:
                if action == "prepare":
                    engine.prepare(identity)
                else:
                    engine.execute(identity)
            finally:
                slots.release()

        pool.submit(work)

    def create(request: RunRequest, public: bool) -> dict[str, Any]:
        if request.issue_number is not None:
            raise HTTPException(422, "Live issue ingestion is available through the operator CLI")
        try:
            data, fresh = store.create(
                ("demo:" if public else "operator:") + request.idempotency_key,
                request.model_dump(),
                public,
            )
        except PolicyError as exc:
            raise HTTPException(409, str(exc)) from None
        if fresh or data["status"] == "queued":
            dispatch(data["id"], "prepare")
        return store.get(data["id"])

    def approve(identity: str, approval: Approval, public: bool) -> dict[str, Any]:
        lookup(identity, public)
        # Acquire capacity first; a saturated service must not strand an approved run.
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "Execution capacity exhausted")
        try:
            engine.approve(identity, approval.digest)
        except PolicyError as exc:
            slots.release()
            raise HTTPException(409, str(exc)) from None

        def work() -> None:
            try:
                engine.execute(identity)
            finally:
                slots.release()

        pool.submit(work)
        return store.get(identity)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "execution_scope": "audited-fixtures-only"}

    @app.get("/api/demo/runs")
    def demo_runs() -> list[dict[str, Any]]:
        return store.list(public_only=True)

    @app.post("/api/demo/runs", status_code=202)
    def demo_create(request: RunRequest) -> dict[str, Any]:
        return create(request, True)

    @app.get("/api/demo/runs/{identity}")
    def demo_read(identity: str) -> dict[str, Any]:
        return lookup(identity, True)

    @app.post("/api/demo/runs/{identity}/approve")
    def demo_approve(identity: str, approval: Approval) -> dict[str, Any]:
        return approve(identity, approval, True)

    @app.post("/api/demo/runs/{identity}/cancel")
    def demo_cancel(identity: str) -> dict[str, Any]:
        lookup(identity, True)
        store.cancel(identity)
        return store.get(identity)

    @app.get("/api/runs", dependencies=[Depends(authorized)])
    def operator_runs() -> list[dict[str, Any]]:
        return store.list()

    @app.post("/api/runs", dependencies=[Depends(authorized)], status_code=202)
    def operator_create(request: RunRequest) -> dict[str, Any]:
        return create(request, False)

    @app.post("/api/runs/{identity}/approve", dependencies=[Depends(authorized)])
    def operator_approve(identity: str, approval: Approval) -> dict[str, Any]:
        return approve(identity, approval, False)

    @app.get("/api/runs/{identity}", dependencies=[Depends(authorized)])
    def operator_read(identity: str) -> dict[str, Any]:
        return lookup(identity)

    @app.post("/api/runs/{identity}/cancel", dependencies=[Depends(authorized)])
    def operator_cancel(identity: str) -> dict[str, Any]:
        lookup(identity)
        store.cancel(identity)
        return store.get(identity)

    return app
