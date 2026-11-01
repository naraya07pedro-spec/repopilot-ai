"""Authenticated loopback workspace, using the existing provider and planning contracts."""

import hmac
import secrets
import threading
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from importlib.resources import files
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from repopilot.local_agent import LocalAgent, LocalRepository
from repopilot.local_lock import WorkspaceLease
from repopilot.migrations import migrate
from repopilot.model_adapters import ModelProfile
from repopilot.model_registry import ModelRegistry
from repopilot.policy import PolicyError
from repopilot.store import Store


class TaskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: str = Field(min_length=8, max_length=6000)
    paths: list[str] = Field(default_factory=list, max_length=8)
    profile: str = Field(max_length=40)
    fallback: str | None = Field(default=None, max_length=40)
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")
    paid_approved: bool = False


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class ClarificationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paths: list[str] = Field(min_length=1, max_length=8)


def create_local_app(
    root: Path,
    data: Path,
    profiles: tuple[ModelProfile, ...],
    *,
    port: int = 8765,
    token: str | None = None,
    client: httpx.Client | None = None,
    paid_enabled: bool = False,
    run_micro: int = 0,
    daily_micro: int = 0,
) -> FastAPI:
    session_token = token or secrets.token_urlsafe(32)
    if len(session_token) < 32:
        raise ValueError("local_session_token_too_short")
    repository = LocalRepository(root)
    repository.revision()  # Fail with an actionable error before accepting traffic.
    if any(p.is_symlink() or p.is_junction() for p in (data.absolute(), *data.absolute().parents)):
        raise PolicyError("data_directory_reparse_point")
    data.mkdir(parents=True, exist_ok=True)
    for name in (
        "local-agent.db",
        "local-agent.db-wal",
        "local-agent.db-shm",
        "local-agent.db-journal",
    ):
        if (data / name).is_symlink() or (data / name).is_junction():
            raise PolicyError("database_reparse_point")
    lease = WorkspaceLease(data)
    store = Store(f"sqlite:///{data.resolve() / 'local-agent.db'}")
    migrate(store.engine)
    transport = client or httpx.Client(trust_env=False)
    registry = ModelRegistry(
        transport, store.engine, profiles, daily_micro, run_micro, paid_enabled
    )
    agent = LocalAgent(store.engine, None, None, registry.planners)
    agent.repository = repository
    agent.recover()
    origin = f"http://127.0.0.1:{port}"
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="repopilot-model")
    slots = threading.BoundedSemaphore(1)
    lock = threading.Lock()
    pending: set[str] = set()

    def work(identity: str) -> None:
        try:
            agent.prepare(identity)
        finally:
            with lock:
                pending.discard(identity)
            slots.release()

    def schedule(identity: str) -> None:
        with lock:
            if identity in pending or agent.get(identity)["status"] != "queued":
                return
            if not slots.acquire(blocking=False):
                raise PolicyError("model_busy_task_saved_queued_resume_after_current_request")
            pending.add(identity)
            try:
                pool.submit(work, identity)
            except Exception:
                pending.discard(identity)
                slots.release()
                raise

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        pool.shutdown(wait=True, cancel_futures=False)
        if client is None:
            transport.close()
        store.engine.dispose()
        lease.close()

    app = FastAPI(
        title="RepoPilot local workspace",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.agent = agent
    app.state.session_token = session_token

    @app.middleware("http")
    async def boundary(request: Request, call_next: Any) -> Response:
        if request.headers.get("host") != f"127.0.0.1:{port}":
            return JSONResponse({"error": "literal_loopback_host_required"}, status_code=403)
        if request.headers.get("origin") not in (None, origin):
            return JSONResponse(
                {"error": "same_origin_only_no_public_connections"}, status_code=403
            )
        if request.url.path.startswith("/api/"):
            supplied = request.headers.get("authorization", "")
            if not hmac.compare_digest(supplied, "Bearer " + session_token):
                return JSONResponse(
                    {"error": "local_session_required_use_the_link_printed_by_repopilot"},
                    status_code=401,
                )
            if request.method == "POST":
                length = request.headers.get("content-length", "")
                if not length.isdigit() or int(length) > 16384:
                    return JSONResponse({"error": "request_body_limit_16384"}, status_code=413)
                if request.headers.get("origin") != origin:
                    return JSONResponse({"error": "same_origin_required"}, status_code=403)
        response: Response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": (
                    "default-src 'none'; script-src 'self'; style-src 'self'; "
                    "connect-src 'self'; img-src 'self'; base-uri 'none'; "
                    "form-action 'none'; frame-ancestors 'none'"
                ),
            }
        )
        return response

    @app.exception_handler(PolicyError)
    async def policy_error(request: Request, error: PolicyError) -> JSONResponse:
        return JSONResponse({"error": str(error)}, status_code=409)

    @app.exception_handler(KeyError)
    async def missing(request: Request, error: KeyError) -> JSONResponse:
        return JSONResponse({"error": "task_not_found"}, status_code=404)

    @app.get("/")
    def index() -> Response:
        return Response(
            files("repopilot").joinpath("web/index.html").read_text(encoding="utf-8"),
            media_type="text/html",
        )

    @app.get("/workspace.js")
    def javascript() -> Response:
        return Response(
            files("repopilot").joinpath("web/workspace.js").read_text(encoding="utf-8"),
            media_type="text/javascript",
        )

    @app.get("/workspace.css")
    def stylesheet() -> Response:
        return Response(
            files("repopilot").joinpath("web/workspace.css").read_text(encoding="utf-8"),
            media_type="text/css",
        )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "mode": "local_proposal_review_patch",
            "execution_enabled": False,
            "publication_enabled": False,
        }

    @app.get("/api/local/settings")
    def settings() -> dict[str, Any]:
        return {
            "repository": repository.root.name,
            "profiles": registry.catalog(),
            "limits": {
                "selected_files": 8,
                "edited_files": 4,
                "context_bytes": 32000,
                "model_calls": 2,
                "concurrent_requests": 1,
            },
            "quality_note": (
                "Quality depends on your model. A 0.5B model is suitable for narrow "
                "experiments, not frontier-level coding."
            ),
            "execution_enabled": False,
            "publication_enabled": False,
        }

    @app.get("/api/local/files")
    def source_files() -> list[str]:
        return repository.files()

    @app.post("/api/local/models/{profile}/check")
    def check_model(profile: str) -> dict[str, Any]:
        return registry.discover(profile)

    @app.get("/api/local/tasks")
    def history() -> list[dict[str, Any]]:
        return [
            {key: row[key] for key in ("id", "task", "status", "created_at", "model_profile")}
            for row in agent.history()
        ]

    @app.post("/api/local/tasks")
    def create(body: TaskInput) -> dict[str, Any]:
        row, _ = agent.create_task(**body.model_dump())
        schedule(row["id"])
        return agent.get(row["id"])

    @app.get("/api/local/tasks/{identity}")
    def task(identity: str) -> dict[str, Any]:
        return agent.get(identity)

    @app.post("/api/local/tasks/{identity}/clarify")
    def clarify(identity: str, body: ClarificationInput) -> dict[str, Any]:
        row = agent.clarify(identity, body.paths)
        schedule(identity)
        return row

    @app.post("/api/local/tasks/{identity}/start")
    def start(identity: str) -> dict[str, Any]:
        schedule(identity)
        return agent.get(identity)

    @app.post("/api/local/tasks/{identity}/cancel")
    def cancel(identity: str) -> dict[str, Any]:
        return agent.stop(identity, "cancelled")

    @app.post("/api/local/tasks/{identity}/approve")
    def approve(identity: str, body: ReviewInput) -> dict[str, Any]:
        return agent.approve(identity, body.digest)

    @app.get("/api/local/tasks/{identity}/patch")
    def patch(identity: str) -> Response:
        value = agent.export_patch(identity)
        return Response(
            value,
            media_type="text/plain",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="repopilot-{uuid_safe(identity)}.patch"'
                )
            },
        )

    return app


def uuid_safe(value: str) -> str:
    # IDs come from the database, never allow untrusted content-disposition text.
    import uuid

    return uuid.UUID(value).hex
