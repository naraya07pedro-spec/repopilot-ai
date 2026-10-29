"""Owner-only control plane. Public static deployment contains none of these routes."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from repopilot.github_app import GitHubApp
from repopilot.migrations import migrate
from repopilot.model_adapters import ModelProfile
from repopilot.model_registry import ModelRegistry, load_profiles
from repopilot.models import Approval
from repopilot.owner_auth import OwnerAuth
from repopilot.policy import PolicyError
from repopilot.private_planner import BudgetedPlanner
from repopilot.private_service import PrivateService
from repopilot.store import Store


@dataclass
class OwnerConfig:
    mode: str = "local"
    origin: str = "http://localhost:3000"
    secure: bool = True
    password: str = field(default="", repr=False)
    app_id: str = ""
    installation: int = 0
    app_key: str = field(default="", repr=False)
    repositories: tuple[str, ...] = ()
    model_key: str = field(default="", repr=False)
    model: str = ""
    profiles: tuple[ModelProfile, ...] = ()
    paid_enabled: bool = False
    daily_micro: int = 0
    run_micro: int = 0
    input_rate: Decimal = Decimal(0)
    output_rate: Decimal = Decimal(0)

    @classmethod
    def from_env(cls) -> "OwnerConfig":
        key_path = os.environ.get("GITHUB_APP_PRIVATE_KEY_FILE", "")
        return cls(
            mode=os.environ.get("REPOPILOT_MODE", "local"),
            origin=os.environ.get("REPOPILOT_ORIGIN", "http://localhost:3000"),
            secure=os.environ.get("REPOPILOT_COOKIE_SECURE", "true") == "true",
            password=os.environ.get("REPOPILOT_OWNER_PASSWORD_HASH", ""),
            app_id=os.environ.get("GITHUB_APP_ID", ""),
            installation=int(os.environ.get("GITHUB_INSTALLATION_ID", "0")),
            app_key=Path(key_path).read_text() if key_path else "",
            repositories=tuple(
                filter(None, os.environ.get("REPOPILOT_REPOSITORIES", "").split(","))
            ),
            model_key=os.environ.get("OPENAI_API_KEY", ""),
            model=os.environ.get("REPOPILOT_MODEL", ""),
            profiles=load_profiles(os.environ.get("REPOPILOT_MODEL_PROFILES_FILE", "")),
            paid_enabled=os.environ.get("REPOPILOT_ALLOW_PAID_MODELS") == "true",
            daily_micro=int(Decimal(os.environ.get("REPOPILOT_DAILY_USD", "0")) * 1000000),
            run_micro=int(Decimal(os.environ.get("REPOPILOT_RUN_USD", "0")) * 1000000),
            input_rate=Decimal(os.environ.get("REPOPILOT_INPUT_USD_PER_MILLION", "0")),
            output_rate=Decimal(os.environ.get("REPOPILOT_OUTPUT_USD_PER_MILLION", "0")),
        )

    def validate(self) -> None:
        parsed = urlparse(self.origin)
        if (
            self.mode not in {"local", "owner", "public"}
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("invalid_owner_configuration")
        if not self.secure and (
            parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}
        ):
            raise ValueError("insecure_cookie_requires_loopback")
        if os.environ.get("REPOPILOT_ENV") == "production" and (
            self.mode != "owner" or parsed.scheme != "https" or not self.password or not self.secure
        ):
            raise ValueError("production_requires_owner_https_auth")
        if self.mode == "owner" and not self.password:
            raise ValueError("owner_password_hash_required")


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=256)


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository: str = Field(max_length=200)
    issue_number: int = Field(ge=1)
    model_profile: str | None = Field(default=None, max_length=40)
    run_limit_micro_usd: int | None = Field(default=None, ge=0, le=100000000)
    paid_approved: bool = False
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")


class OwnerRuntime:
    def __init__(
        self,
        app: FastAPI,
        store: Store,
        pool: ThreadPoolExecutor,
        slots: threading.BoundedSemaphore,
        config: OwnerConfig | None = None,
    ):
        self.config = config or OwnerConfig.from_env()
        self.config.validate()
        migrate(store.engine)
        self.client = httpx.Client(trust_env=False)
        self.auth = OwnerAuth(store.engine, self.config.password)
        cfg = self.config
        self.github = (
            GitHubApp(self.client, cfg.app_id, cfg.app_key, cfg.installation, cfg.repositories)
            if cfg.app_id and cfg.app_key and cfg.installation
            else None
        )
        self.planner = (
            BudgetedPlanner(
                self.client,
                store.engine,
                cfg.model_key,
                cfg.model,
                cfg.daily_micro,
                cfg.run_micro,
                cfg.input_rate,
                cfg.output_rate,
            )
            if cfg.paid_enabled
            and cfg.model_key
            and cfg.model
            and (
                cfg.daily_micro > 0
                and cfg.run_micro > 0
                and cfg.input_rate > 0
                and cfg.output_rate > 0
            )
            else None
        )
        self.registry = ModelRegistry(
            self.client,
            store.engine,
            cfg.profiles,
            cfg.daily_micro,
            cfg.run_micro,
            cfg.paid_enabled,
        )
        self.service = PrivateService(
            store.engine, self.github, self.planner, self.registry.planners
        )

        def origin(request: Request) -> None:
            if cfg.mode == "public":
                raise HTTPException(404, "Owner service disabled")
            if request.headers.get("origin") != cfg.origin.rstrip("/"):
                raise HTTPException(403, "Same-origin request required")

        def authorized(request: Request) -> None:
            if cfg.mode == "public" or not self.auth.valid(
                request.cookies.get("repopilot_owner", "")
            ):
                raise HTTPException(401, "Owner authentication required")

        def run(identity: str) -> dict[str, Any]:
            try:
                return self.service.get(identity)
            except KeyError:
                raise HTTPException(404, "Run not found") from None

        @app.post("/api/owner/login", dependencies=[Depends(origin)])
        def login(body: Login, response: Response) -> dict[str, bool]:
            if not cfg.password:
                raise HTTPException(503, "Owner authentication is not configured")
            try:
                token = self.auth.login(body.password)
            except ValueError:
                raise HTTPException(
                    429, "Try again after one minute", headers={"Retry-After": "60"}
                ) from None
            if not token:
                raise HTTPException(401, "Invalid credentials")
            response.set_cookie(
                "repopilot_owner",
                token,
                max_age=3600,
                httponly=True,
                secure=cfg.secure,
                samesite="strict",
                path="/",
            )
            response.headers["Cache-Control"] = "no-store"
            return {"authenticated": True}

        @app.post("/api/owner/logout", dependencies=[Depends(origin), Depends(authorized)])
        def logout(request: Request, response: Response) -> dict[str, bool]:
            self.auth.logout(request.cookies.get("repopilot_owner", ""))
            response.delete_cookie(
                "repopilot_owner", path="/", secure=cfg.secure, httponly=True, samesite="strict"
            )
            return {"authenticated": False}

        @app.get("/api/owner/settings", dependencies=[Depends(authorized)])
        def settings() -> dict[str, Any]:
            return {
                "authenticated": True,
                "github_app_configured": self.github is not None,
                "model_configured": self.planner is not None or bool(self.registry.planners),
                "models": self.registry.catalog(),
                "paid_calls_enabled": cfg.paid_enabled,
                "model": cfg.model,
                "approved_repositories": list(cfg.repositories),
                "daily_limit_micro_usd": cfg.daily_micro,
                "run_limit_micro_usd": cfg.run_micro,
                "reserved_today_micro_usd": (
                    next(iter(self.registry.planners.values())).reserved_today()
                    if self.registry.planners
                    else self.planner.reserved_today()
                    if self.planner
                    else 0
                ),
                "execution_enabled": False,
                "execution_blocker": (
                    "No independently validated isolated worker is configured. "
                    "Arbitrary code execution and private PR publication are disabled."
                ),
            }

        @app.post(
            "/api/owner/models/{profile}/discover",
            dependencies=[Depends(origin), Depends(authorized)],
        )
        def discover(profile: str) -> dict[str, Any]:
            try:
                return self.registry.discover(profile)
            except PolicyError as exc:
                raise HTTPException(409, str(exc)) from None

        @app.get("/api/owner/repositories", dependencies=[Depends(authorized)])
        def repositories() -> list[str]:
            if self.github is None:
                raise HTTPException(503, "GitHub App not configured")
            try:
                return self.github.repositories()
            except PolicyError as exc:
                raise HTTPException(409, str(exc)) from None

        @app.get("/api/owner/runs", dependencies=[Depends(authorized)])
        def history() -> list[dict[str, Any]]:
            return self.service.history()

        @app.get("/api/owner/runs/{identity}", dependencies=[Depends(authorized)])
        def detail(identity: str) -> dict[str, Any]:
            return run(identity)

        @app.post(
            "/api/owner/runs", status_code=202, dependencies=[Depends(origin), Depends(authorized)]
        )
        def create(body: PlanRequest) -> dict[str, Any]:
            if not slots.acquire(blocking=False):
                raise HTTPException(429, "Execution capacity exhausted")
            try:
                data, fresh = self.service.create(
                    body.repository,
                    body.issue_number,
                    body.idempotency_key,
                    model_profile=body.model_profile,
                    run_micro=body.run_limit_micro_usd,
                    paid_approved=body.paid_approved,
                )
            except PolicyError as exc:
                slots.release()
                raise HTTPException(409, str(exc)) from None
            if fresh:

                def work() -> None:
                    try:
                        self.service.prepare(data["id"])
                    finally:
                        slots.release()

                pool.submit(work)
            else:
                slots.release()
            return data

        @app.post(
            "/api/owner/runs/{identity}/approve",
            dependencies=[Depends(origin), Depends(authorized)],
        )
        def approve(identity: str, body: Approval) -> dict[str, Any]:
            run(identity)
            try:
                return self.service.approve(identity, body.digest)
            except PolicyError as exc:
                raise HTTPException(409, str(exc)) from None

        @app.post(
            "/api/owner/runs/{identity}/cancel", dependencies=[Depends(origin), Depends(authorized)]
        )
        def cancel(identity: str) -> dict[str, Any]:
            run(identity)
            return self.service.stop(identity, "cancelled")

        @app.post(
            "/api/owner/runs/{identity}/reject", dependencies=[Depends(origin), Depends(authorized)]
        )
        def reject(identity: str) -> dict[str, Any]:
            run(identity)
            return self.service.stop(identity, "rejected")

        @app.post(
            "/api/owner/runs/{identity}/execute",
            dependencies=[Depends(origin), Depends(authorized)],
        )
        def execute(identity: str) -> None:
            run(identity)
            raise HTTPException(409, "isolated_worker_unavailable: no code was executed")

    def close(self) -> None:
        self.client.close()
