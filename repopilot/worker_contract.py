"""Authenticated worker protocol and durable lifecycle; contains no code executor.

The production route remains disabled. A signed message authenticates its sender,
not the sender's sandbox. Resource fields are requirements, not enforcement evidence.
"""

import hashlib
import hmac
import json
import re
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from repopilot.policy import SECRET, PolicyError, digest
from repopilot.private_service import PrivateService
from repopilot.store import now

COMMANDS = {
    "pytest": [
        "python",
        "-I",
        "-B",
        "-m",
        "pytest",
        "-q",
        "--noconftest",
        "-p",
        "no:cacheprovider",
        "tests",
    ],
    "lint": ["python", "-I", "-m", "ruff", "check", "--isolated", "--no-cache", "."],
    "format": ["python", "-I", "-m", "ruff", "format", "--isolated", "--no-cache", "--check", "."],
}


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, hide_input_in_errors=True)


class VerificationJob(Contract):
    run_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    nonce: str = Field(pattern=r"^[a-f0-9]{32}$")
    baseline_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    approval_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    profile: Literal["python-checks-v1"] = "python-checks-v1"
    files: dict[str, str] = Field(min_length=1, max_length=32)
    issued_at: int
    expires_at: int
    timeout_seconds: int = Field(default=60, ge=1, le=60)
    memory_mib: int = Field(default=512, ge=64, le=512)
    disk_mib: int = Field(default=64, ge=8, le=64)
    cpu_millis: int = Field(default=1000, ge=100, le=1000)
    process_limit: int = Field(default=32, ge=1, le=32)
    network: Literal["deny"] = "deny"
    uid: Literal[65532] = 65532

    @model_validator(mode="after")
    def safe_job(self) -> "VerificationJob":
        if not 0 < self.expires_at - self.issued_at <= 300:
            raise ValueError("worker_lease_limit")
        if sum(len(v.encode()) for v in self.files.values()) > 128000:
            raise ValueError("worker_source_limit")
        for path, content in self.files.items():
            if (
                not re.fullmatch(r"[A-Za-z0-9_/-]+\.py", path)
                or any(part in {"", ".", ".."} for part in path.split("/"))
                or path.startswith("/")
                or SECRET.search(content)
                or any(
                    part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL"}
                    for part in path.split("/")
                )
            ):
                raise ValueError("worker_source_policy")
        return self


class WorkerCheck(Contract):
    name: Literal["pytest", "lint", "format"]
    command: list[str]
    exit_code: int = Field(ge=0, le=255)
    output: str = Field(max_length=16000)
    duration_seconds: float = Field(ge=0, le=60, allow_inf_nan=False)
    timed_out: bool = False
    cancelled: bool = False

    @model_validator(mode="after")
    def check_command(self) -> "WorkerCheck":
        if self.command != COMMANDS[self.name] or SECRET.search(self.output):
            raise ValueError("worker_check_policy")
        return self


class ExecutionReceipt(Contract):
    run_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    nonce: str = Field(pattern=r"^[a-f0-9]{32}$")
    job_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    outcome: Literal["completed", "failed", "cancelled"]
    checks: list[WorkerCheck] = Field(max_length=3)

    @model_validator(mode="after")
    def complete_evidence(self) -> "ExecutionReceipt":
        names = [c.name for c in self.checks]
        if len(names) != len(set(names)):
            raise ValueError("worker_duplicate_check")
        if self.outcome == "completed" and set(names) != set(COMMANDS):
            raise ValueError("worker_checks_missing")
        if sum(len(c.output.encode()) for c in self.checks) > 64000:
            raise ValueError("worker_output_limit")
        return self


class Envelope(Contract):
    payload: dict[str, Any]
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")


def sign(payload: dict[str, Any], key: bytes, kind: Literal["job", "receipt"]) -> Envelope:
    if len(key) < 32:
        raise PolicyError("worker_auth_key_too_short")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    if len(encoded) > 256000:
        raise PolicyError("worker_message_limit")
    message = ("repopilot-worker-v1:" + kind + ":").encode() + encoded
    return Envelope(payload=payload, signature=hmac.new(key, message, hashlib.sha256).hexdigest())


def authenticate(envelope: Envelope, key: bytes, kind: Literal["job", "receipt"]) -> None:
    expected = sign(envelope.payload, key, kind)
    if not hmac.compare_digest(expected.signature, envelope.signature):
        raise PolicyError("worker_authentication_failed")


def validate_job(envelope: Envelope, key: bytes) -> VerificationJob:
    authenticate(envelope, key, "job")
    job = VerificationJob.model_validate(envelope.payload)
    if not job.issued_at <= time.time() <= job.expires_at:
        raise PolicyError("worker_lease_expired")
    return job


class DisabledWorker:
    available = False

    def require_available(self) -> None:
        raise PolicyError("isolated_worker_unavailable: no code was executed")


class WorkerLedger:
    """Persistence contract only. No production route instantiates or dispatches this ledger."""

    def __init__(self, service: PrivateService, key: bytes):
        if len(key) < 32:
            raise PolicyError("worker_auth_key_too_short")
        self.service, self._key = service, key

    def prepare(self, identity: str) -> Envelope:
        data = self.service.get(identity)
        if data["status"] == "worker_queued":
            envelope = sign(data["worker_job"], self._key, "job")
            validate_job(envelope, self._key)
            return envelope
        if data["status"] != "approved":
            raise PolicyError("worker_approval_required")
        if data.get("approval_expires", 0) < time.time() or self.service.approval_digest(
            data
        ) != data.get("approval_digest"):
            raise PolicyError("worker_approval_invalid")
        planner = self.service.selected(data.get("model_profile"))
        if planner.binding(data["selection"]["run_micro"]) != data["selection"]:
            raise PolicyError("model_configuration_changed")
        files = dict(data["snapshot"]["files"])
        files.update({edit["path"]: edit["content"] for edit in data["plan"]["edits"]})
        stamp = int(time.time())
        job = VerificationJob(
            run_id=identity,
            nonce=uuid.uuid4().hex,
            baseline_sha=data["snapshot"]["base_sha"],
            approval_digest=data["approval_digest"],
            files=files,
            issued_at=stamp,
            expires_at=min(stamp + 300, data["approval_expires"]),
        )
        data["worker_job"] = job.model_dump()
        data["events"].append({"at": now(), "name": "worker_queued"})
        if not self.service.transition(identity, ["approved"], "worker_queued", data):
            raise PolicyError("worker_state_conflict")
        return sign(job.model_dump(), self._key, "job")

    def claim(self, envelope: Envelope) -> VerificationJob:
        job = validate_job(envelope, self._key)
        data = self.service.get(job.run_id)
        if data.get("worker_job") != job.model_dump():
            raise PolicyError("worker_job_mismatch")
        if self.service.approval_digest(data) != job.approval_digest:
            raise PolicyError("worker_approval_invalid")
        if (
            self.service.selected(data.get("model_profile")).binding(data["selection"]["run_micro"])
            != data["selection"]
        ):
            raise PolicyError("model_configuration_changed")
        if not self.service.transition(job.run_id, ["worker_queued"], "executing"):
            raise PolicyError("worker_state_conflict")
        return job

    def accept(self, envelope: Envelope) -> dict[str, Any]:
        authenticate(envelope, self._key, "receipt")
        receipt = ExecutionReceipt.model_validate(envelope.payload)
        data = self.service.get(receipt.run_id)
        saved = data.get("worker_job", {})
        if receipt.job_digest != digest(saved) or receipt.nonce != saved.get("nonce"):
            raise PolicyError("worker_receipt_mismatch")
        receipt_digest = digest(receipt.model_dump())
        if data.get("worker_receipt_digest") == receipt_digest:
            return data  # Lost acknowledgement: no duplicate transition or evidence append.
        if saved.get("expires_at", 0) < time.time():
            raise PolicyError("worker_lease_expired")
        if sum(c.duration_seconds for c in receipt.checks) > saved["timeout_seconds"]:
            raise PolicyError("worker_reported_time_limit")
        state = data["status"]
        if state not in {"executing", "cancel_requested"}:
            raise PolicyError("worker_state_conflict")
        if state == "cancel_requested" and receipt.outcome != "cancelled":
            raise PolicyError("worker_cancel_pending")
        passed = receipt.outcome == "completed" and all(
            c.exit_code == 0 and not c.timed_out and not c.cancelled for c in receipt.checks
        )
        status = (
            "cancelled"
            if receipt.outcome == "cancelled"
            else ("verification_passed" if passed else "verification_failed")
        )
        data["worker_receipt"] = receipt.model_dump()
        data["worker_receipt_digest"] = receipt_digest
        data["events"].append({"at": now(), "name": status})
        if not self.service.transition(receipt.run_id, [state], status, data):
            raise PolicyError("worker_state_conflict")
        return self.service.get(receipt.run_id)

    def cancel(self, identity: str) -> dict[str, Any]:
        for _ in range(4):
            data = self.service.get(identity)
            state = data["status"]
            if state not in {"worker_queued", "executing"}:
                return data
            data["events"].append({"at": now(), "name": "cancel_requested"})
            if self.service.transition(identity, [state], "cancel_requested", data):
                return self.service.get(identity)
        raise PolicyError("worker_state_conflict")

    def recover(self) -> None:
        # Never replay an uncertain dispatch. Cleanup and reconciliation remain an operator task.
        self.service.recover()
