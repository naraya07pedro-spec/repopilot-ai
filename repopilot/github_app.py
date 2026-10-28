"""Installation-scoped access; keys/tokens never belong in browser or run records."""

import base64
import re
import threading
import time
from datetime import datetime
from typing import Any

import httpx
import jwt

from repopilot.github import GitHub
from repopilot.policy import PolicyError, repository_name


class GitHubApp:
    def __init__(
        self,
        client: httpx.Client,
        app_id: str,
        private_key: str,
        installation: int,
        repositories: tuple[str, ...],
    ):
        for repo in repositories:
            repository_name(repo)
        self.client, self.app_id, self.private_key = client, app_id, private_key
        self.installation, self.allowed = installation, repositories
        self.cache: dict[str, tuple[str, float]] = {}
        self.lock = threading.Lock()

    def app_jwt(self) -> str:
        timestamp = int(time.time())
        return str(
            jwt.encode(
                {"iat": timestamp - 60, "exp": timestamp + 540, "iss": self.app_id},
                self.private_key,
                algorithm="RS256",
            )
        )

    def call(
        self, method: str, path: str, token: str, payload: dict[str, Any] | None = None
    ) -> Any:
        for attempt in range(2 if method == "GET" else 1):
            try:
                response = self.client.request(
                    method,
                    "https://api.github.com" + path,
                    json=payload,
                    headers={
                        "Authorization": "Bearer " + token,
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2026-03-10",
                    },
                    timeout=20,
                    follow_redirects=False,
                )
            except httpx.HTTPError:
                if method == "GET" and attempt == 0:
                    continue
                raise PolicyError(
                    "github_app_transport_unknown" if method != "GET" else "github_app_transport"
                ) from None
            if response.status_code == 429 or response.headers.get("x-ratelimit-remaining") == "0":
                raise PolicyError("github_app_rate_limited")
            if response.status_code >= 500 and method == "GET" and attempt == 0:
                continue
            if response.status_code >= 300:
                raise PolicyError(f"github_app_http_{response.status_code}")
            if len(response.content) > 250000:
                raise PolicyError("github_app_response_limit")
            return response.json()
        raise PolicyError("github_app_retry_exhausted")

    def token(self, repository: str, write: bool = False) -> str:
        if repository not in self.allowed:
            raise PolicyError("repository_not_allowed")
        key = repository + (":write" if write else ":read")
        with self.lock:
            if key in self.cache and self.cache[key][1] > time.time() + 90:
                return self.cache[key][0]
            app_token = self.app_jwt()
            installation = self.call("GET", f"/repos/{repository}/installation", app_token)
            if installation["id"] != self.installation or installation.get("suspended_at"):
                raise PolicyError("installation_not_authorized")
            permissions = installation.get("permissions", {})
            required = {"contents": "write" if write else "read", "issues": "read"}
            if write:
                required["pull_requests"] = "write"
            if any(
                permissions.get(k) not in ({"read", "write"} if v == "read" else {"write"})
                for k, v in required.items()
            ):
                raise PolicyError("installation_permissions")
            result = self.call(
                "POST",
                f"/app/installations/{self.installation}/access_tokens",
                app_token,
                {"repositories": [repository.split("/")[1]], "permissions": required},
            )
            expires = datetime.fromisoformat(
                result["expires_at"].replace("Z", "+00:00")
            ).timestamp()
            self.cache[key] = (result["token"], expires)
            return str(result["token"])

    def repositories(self) -> list[str]:
        # Only configured repositories are queried and returned; no account-wide discovery.
        return [repo for repo in self.allowed if self.token(repo)]

    def snapshot(self, repository: str, number: int) -> dict[str, Any]:
        github = GitHub(self.client, self.token(repository))
        issue = github.issue(repository, number)
        repo = github.request("GET", repository)
        commit = github.request("GET", f"{repository}/commits/{repo['default_branch']}")
        tree = github.request("GET", f"{repository}/git/trees/{commit['sha']}?recursive=1")
        if tree.get("truncated") or len(tree["tree"]) > 1000:
            raise PolicyError("repository_context_limit")
        paths = [
            item["path"]
            for item in tree["tree"]
            if item["type"] == "blob"
            and item.get("mode") != "120000"
            and item["path"].endswith((".py", ".ts", ".tsx"))
            and not any(
                part.startswith(".") or part in {"node_modules", "vendor", "dist"}
                for part in item["path"].split("/")
            )
        ]
        if len(paths) > 8:
            raise PolicyError("repository_profile_limit")
        files: dict[str, str] = {}
        for path in paths:
            if not re.fullmatch(r"[A-Za-z0-9_/-]+\.(py|ts|tsx)", path) or any(
                part in {"", ".", ".."} for part in path.split("/")
            ):
                raise PolicyError("repository_path_limit")
            blob = github.request("GET", f"{repository}/contents/{path}?ref={commit['sha']}")
            if blob.get("type") != "file" or blob.get("size", 0) > 12000:
                raise PolicyError("repository_file_limit")
            files[path] = base64.b64decode(blob["content"]).decode("utf-8")
        if not files or sum(len(v.encode()) for v in files.values()) > 24000:
            raise PolicyError("repository_context_limit")
        return {
            "issue": issue.model_dump(),
            "base_sha": commit["sha"],
            "base_ref": repo["default_branch"],
            "files": files,
            "profile": "small-python-typescript; inspection only",
        }
