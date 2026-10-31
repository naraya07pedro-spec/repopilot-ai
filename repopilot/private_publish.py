"""Explicit publication and read-only reconciliation; production gate stays closed."""

import re
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

from repopilot.github import GitHub
from repopilot.models import Plan
from repopilot.policy import PolicyError, digest
from repopilot.private_service import PrivateService
from repopilot.store import now
from repopilot.worker_contract import ExecutionReceipt, VerificationJob


class PrivatePublisher:
    def __init__(self, service: PrivateService, require_execution: Callable[[], None]):
        self.service, self.require_execution = service, require_execution

    def artifact(self, identity: str) -> dict[str, Any]:
        data = self.service.get(identity)
        if data["status"] != "verification_passed":
            raise PolicyError("publication_requires_verified_run")
        if self.service.approval_digest(data) != data.get("approval_digest"):
            raise PolicyError("publication_approval_changed")
        job = VerificationJob.model_validate(data["worker_job"])
        receipt = ExecutionReceipt.model_validate(data["worker_receipt"])
        if (
            receipt.outcome != "completed"
            or job.run_id != identity
            or job.approval_digest != data["approval_digest"]
            or receipt.run_id != identity
            or receipt.nonce != job.nonce
            or receipt.job_digest != digest(job.model_dump())
            or any(c.exit_code or c.timed_out or c.cancelled for c in receipt.checks)
        ):
            raise PolicyError("publication_evidence_invalid")
        snapshot, plan = data["snapshot"], Plan.model_validate(data["plan"])
        expected = {**snapshot["files"], **{e.path: e.content for e in plan.edits}}
        if job.files != expected or job.baseline_sha != snapshot["base_sha"]:
            raise PolicyError("publication_candidate_mismatch")
        prefix = snapshot.get("source_root", "")
        if prefix and not re.fullmatch(r"(?:[A-Za-z0-9_-]+/)+", prefix):
            raise PolicyError("publication_scope_invalid")
        if not re.fullmatch(r"[a-f0-9]{40}", snapshot.get("base_tree") or ""):
            raise PolicyError("publication_base_tree_missing")
        content = {
            "repository": data["repository"],
            "issue_number": data["issue_number"],
            "run_id": identity,
            "base_sha": snapshot["base_sha"],
            "base_tree": snapshot["base_tree"],
            "base_ref": snapshot["base_ref"],
            "source_root": prefix,
            "branch": "repopilot/private-" + identity,
            "files": {prefix + edit.path: edit.content for edit in plan.edits},
            "receipt_digest": digest(receipt.model_dump()),
            "approval_expires": data["approval_expires"],
            "checks": [c.model_dump() for c in receipt.checks],
        }
        return {**content, "digest": digest(content)}

    def github(self, artifact: dict[str, Any]) -> GitHub:
        app = self.service.github
        if not app or artifact["repository"] not in app.allowed:
            raise PolicyError("publication_repository_not_authorized")
        root = getattr(app, "source_roots", {}).get(artifact["repository"], "")
        if artifact["source_root"] != (root + "/" if root else ""):
            raise PolicyError("publication_scope_changed")
        return GitHub(app.client, app.token(artifact["repository"], write=True))

    def save(self, data: dict[str, Any], before: list[str], state: str) -> None:
        data["events"].append({"at": now(), "name": state})
        if not self.service.transition(data["id"], before, state, data):
            raise PolicyError("publication_state_conflict")

    def publish(self, identity: str, approved: str) -> dict[str, Any]:
        self.require_execution()  # No credential/config-only bypass of the runtime gate.
        data = self.service.get(identity)
        if data["status"] == "completed":
            if data["publication"]["digest"] != approved:
                raise PolicyError("publication_approval_changed")
            return data
        artifact = self.artifact(identity)
        if artifact["digest"] != approved or artifact["approval_expires"] < time.time():
            raise PolicyError("publication_approval_required")
        github = self.github(artifact)
        repo = artifact["repository"]
        base = github.request("GET", f"{repo}/commits/{artifact['base_ref']}")
        if base["sha"] != artifact["base_sha"]:
            raise PolicyError("publication_base_changed")
        data["publication"] = artifact
        self.save(data, ["verification_passed"], "preparing_pr")
        try:
            # Never retry writes. Persist each confirmed identity before the next write.
            tree = github.request(
                "POST",
                f"{repo}/git/trees",
                {
                    "base_tree": artifact["base_tree"],
                    "tree": [
                        {"path": p, "mode": "100644", "type": "blob", "content": c}
                        for p, c in artifact["files"].items()
                    ],
                },
            )
            artifact["tree_sha"] = tree["sha"]
            self.save(data, ["preparing_pr"], "preparing_pr")
            commit = github.request(
                "POST",
                f"{repo}/git/commits",
                {
                    "message": f"RepoPilot: issue #{artifact['issue_number']}",
                    "tree": tree["sha"],
                    "parents": [artifact["base_sha"]],
                },
            )
            artifact["commit_sha"] = commit["sha"]
            self.save(data, ["preparing_pr"], "preparing_pr")
            github.request(
                "POST",
                f"{repo}/git/refs",
                {
                    "ref": "refs/heads/" + artifact["branch"],
                    "sha": commit["sha"],
                },
            )
            self.save(data, ["preparing_pr"], "preparing_pr")
            github.request(
                "POST",
                f"{repo}/pulls",
                {
                    "title": f"RepoPilot: issue #{artifact['issue_number']}",
                    "head": artifact["branch"],
                    "base": artifact["base_ref"],
                    "draft": True,
                    "body": self.body(artifact),
                },
            )
            # Independently re-read branch, commit and PR, including after a successful POST.
            return self.reconcile(identity)
        except Exception:
            current = self.service.get(identity)
            if current["status"] == "preparing_pr":
                self.save(current, ["preparing_pr"], "publication_unknown")
            raise PolicyError(
                "publication_outcome_unknown: reconcile before any new write"
            ) from None

    @staticmethod
    def body(artifact: dict[str, Any]) -> str:
        checks = "\n".join(f"- {c['name']}: exit {c['exit_code']}" for c in artifact["checks"])
        return (
            f"Addresses #{artifact['issue_number']}.\n\n"
            f"Pinned baseline: `{artifact['base_sha']}`.\n\n{checks}\n\n"
            "Review the full diff and recorded outputs in the private owner workspace. "
            "These bounded checks do not establish general correctness. Human review required; "
            "never auto-merge.\n\n"
            f"<!-- repopilot-publication:{artifact['digest']} -->"
        )

    def reconcile(self, identity: str) -> dict[str, Any]:
        data = self.service.get(identity)
        if data["status"] == "completed":
            return data
        if data["status"] not in {"preparing_pr", "publication_unknown"}:
            raise PolicyError("publication_state_conflict")
        artifact = data["publication"]
        if not artifact.get("commit_sha") or not artifact.get("tree_sha"):
            raise PolicyError("publication_unresolved: no confirmed commit")
        github, repo = self.github(artifact), artifact["repository"]
        branch = github.request("GET", f"{repo}/git/ref/heads/{artifact['branch']}")
        if branch["object"]["sha"] != artifact["commit_sha"]:
            raise PolicyError("publication_branch_conflict")
        commit = github.request("GET", f"{repo}/git/commits/{artifact['commit_sha']}")
        if commit["tree"]["sha"] != artifact["tree_sha"] or [
            p["sha"] for p in commit["parents"]
        ] != [artifact["base_sha"]]:
            raise PolicyError("publication_commit_conflict")
        query = urlencode(
            {
                "state": "all",
                "head": repo.split("/")[0] + ":" + artifact["branch"],
                "base": artifact["base_ref"],
                "per_page": 100,
            }
        )
        pulls = github.request("GET", f"{repo}/pulls?{query}")
        if len(pulls) != 1:
            raise PolicyError("publication_unresolved: expected one matching PR")
        pr = pulls[0]
        if (
            pr["head"]["sha"] != artifact["commit_sha"]
            or pr["head"]["repo"]["full_name"] != repo
            or pr["base"]["ref"] != artifact["base_ref"]
            or f"<!-- repopilot-publication:{artifact['digest']} -->" not in (pr.get("body") or "")
        ):
            raise PolicyError("publication_pr_conflict")
        # Derive the URL from the permitted repository and validated numeric PR identity.
        if type(pr["number"]) is not int or pr["number"] < 1:
            raise PolicyError("publication_pr_identity")
        data["pr"] = {
            "number": pr["number"],
            "url": f"https://github.com/{repo}/pull/{pr['number']}",
            "commit": artifact["commit_sha"],
            "state": pr["state"],
        }
        self.save(data, [data["status"]], "completed")
        return self.service.get(identity)
