from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Issue(StrictModel):
    number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=500)
    body: str = Field(max_length=12000)
    repository: str = "naraya07pedro-spec/repopilot-ai"
    url: str | None = None


class Edit(StrictModel):
    path: str = Field(min_length=1, max_length=200)
    content: str = Field(max_length=24000)


class Plan(StrictModel):
    interpretation: str = Field(min_length=1, max_length=2000)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=10)
    relevant_files: list[str] = Field(min_length=1, max_length=8)
    proposed_changes: list[str] = Field(min_length=1, max_length=10)
    tests: list[str] = Field(min_length=1, max_length=10)
    risks: list[str] = Field(max_length=10)
    assumptions: list[str] = Field(max_length=10)
    edits: list[Edit] = Field(min_length=1, max_length=4)


class RunRequest(StrictModel):
    scenario: Literal["bug", "feature", "failure"]
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")
    issue_number: int | None = Field(default=None, ge=1)


class Approval(StrictModel):
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class Check(StrictModel):
    name: str
    command: list[str]
    exit_code: int
    output: str
    duration_seconds: float
    timed_out: bool = False
    cancelled: bool = False
