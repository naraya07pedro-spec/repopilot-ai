import base64
import re
from typing import Any

import httpx

from repopilot.models import Issue
from repopilot.policy import PolicyError, repository_name

APPROVED_REPO = "naraya07pedro-spec/repopilot-ai"


class GitHub:
    def __init__(self, client: httpx.Client, token: str | None = None):
        self.client = client
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            self.headers["Authorization"] = "Bearer " + token

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        # All paths are internally constructed. No redirects or remote clone URLs.
        for attempt in range(2 if method == "GET" else 1):
            try:
                response = self.client.request(
                    method,
                    "https://api.github.com/repos/" + path,
                    headers=self.headers,
                    json=payload,
                    timeout=20,
                    follow_redirects=False,
                )
            except httpx.HTTPError as exc:
                if method == "GET" and attempt == 0:
                    continue
                raise PolicyError(
                    "github_transport_unknown" if method != "GET" else "github_transport"
                ) from exc
            if response.status_code == 429 or (
                response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"
            ):
                raise PolicyError("github_rate_limited")
            if response.status_code >= 500 and method == "GET" and attempt == 0:
                continue
            if response.status_code >= 300:
                raise PolicyError(f"github_http_{response.status_code}")
            if len(response.content) > 250000:
                raise PolicyError("github_response_limit")
            return response.json()
        raise PolicyError("github_retry_exhausted")

    def issue(self, repository: str, number: int) -> Issue:
        repository_name(repository)
        if number < 1:
            raise PolicyError("invalid_issue")
        data = self.request("GET", f"{repository}/issues/{number}")
        if "pull_request" in data:
            raise PolicyError("pull_request_is_not_issue")
        return Issue(
            number=data["number"],
            title=data["title"],
            body=data.get("body") or "",
            repository=repository,
            url=f"https://github.com/{repository}/issues/{number}",
        )

    def snapshot(self, repository: str, ref: str, scenario: str) -> dict[str, str]:
        repository_name(repository)
        if scenario not in {"bug", "feature", "failure"}:
            raise PolicyError("unknown_fixture")
        if not re.fullmatch(r"[a-f0-9]{40}", ref):
            raise PolicyError("immutable_ref_required")
        files = {}
        for name in ("app.py", "test_app.py"):
            data = self.request(
                "GET", f"{repository}/contents/fixtures/{scenario}/{name}?ref={ref}"
            )
            if data.get("type") != "file" or data.get("size", 0) > 24000:
                raise PolicyError("github_file_limit_or_type")
            files[name] = base64.b64decode(data["content"], validate=False).decode("utf-8")
        return files

    def prepare_publish(self, artifact: dict[str, Any], approved_digest: str) -> dict[str, Any]:
        from repopilot.policy import digest

        if artifact["repository"] != APPROVED_REPO or artifact["digest"] != approved_digest:
            raise PolicyError("publish_not_authorized")
        content = {k: v for k, v in artifact.items() if k != "digest"}
        if digest(content) != approved_digest or artifact["status"] != "verified":
            raise PolicyError("artifact_tampered")
        from repopilot.fixtures import CATALOG

        files = content.get("files", {})
        allowed = {
            f"fixtures/{name}/{path}": text
            for name, fixture in CATALOG.items()
            for path, text in fixture.edits.items()
        }
        if not files or any(p not in allowed or allowed[p] != text for p, text in files.items()):
            raise PolicyError("publish_file_scope")
        if not re.fullmatch(r"repopilot/[a-z0-9_-]{1,64}", content["branch"]):
            raise PolicyError("publish_branch_scope")
        return content

    def publish(self, artifact: dict[str, Any], approved_digest: str) -> dict[str, Any]:
        data = self.prepare_publish(artifact, approved_digest)
        repo, base, branch = data["repository"], data["base_ref"], data["branch"]
        if data["base_sha"] != self.request("GET", f"{repo}/commits/{base}")["sha"]:
            raise PolicyError("base_changed")
        # No write retries: a timeout requires manual reconciliation.
        tree = self.request(
            "POST",
            f"{repo}/git/trees",
            {
                "base_tree": data["base_tree"],
                "tree": [
                    {"path": p, "mode": "100644", "type": "blob", "content": c}
                    for p, c in data["files"].items()
                ],
            },
        )
        commit = self.request(
            "POST",
            f"{repo}/git/commits",
            {
                "message": data["title"],
                "tree": tree["sha"],
                "parents": [data["base_sha"]],
            },
        )
        self.request(
            "POST",
            f"{repo}/git/refs",
            {
                "ref": "refs/heads/" + branch,
                "sha": commit["sha"],
            },
        )
        return dict(
            self.request(
                "POST",
                f"{repo}/pulls",
                {
                    "title": data["title"],
                    "body": data["body"],
                    "head": branch,
                    "base": base,
                    "draft": True,
                },
            )
        )
