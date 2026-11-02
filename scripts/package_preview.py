"""Package a verified wheel and committed source for an explicitly unverified-model preview.

No build, inference, credential access or publication happens here. Output must be new.
The CI artifact is an online installer bundle, not an offline dependency wheelhouse.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from check_distribution import verify_wheel

ROOT = Path(__file__).resolve().parents[1]


def package(wheel: Path, output: Path) -> dict:
    wheel = wheel.resolve(strict=True)
    verified_files = verify_wheel(wheel)
    subprocess.run(
        [
            "git",
            "diff",
            "--exit-code",
            "HEAD",
            "--",
            "repopilot",
            "pyproject.toml",
            "requirements.lock",
            "docs/self-hosted.md",
            "docs/preview-release.md",
            "scripts/package_preview.py",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=15,
    )
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "repopilot"],
        cwd=ROOT,
        timeout=15,
    )
    if untracked:
        raise ValueError("Untracked package source cannot claim committed provenance")
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=15
    ).strip()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(wheel, output / wheel.name)
    shutil.copyfile(ROOT / "requirements.lock", output / "requirements.lock")
    shutil.copyfile(ROOT / "docs/preview-release.md", output / "INSTALL.md")
    shutil.copyfile(ROOT / "LICENSE", output / "LICENSE")
    subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "archive",
            "--format=zip",
            "--output=" + str(output / "source.zip"),
            revision,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    )
    record = {
        "edition": "proposal-preview",
        "source_repository": "naraya07pedro-spec/repopilot-ai",
        "source_commit": revision,
        "wheel": wheel.name,
        "package_source_files_verified": verified_files,
        "dependency_constraints": "requirements.lock",
        "tested_python": "3.12",
        "requires_internet_for_dependencies": True,
        "real_model_through_workspace_acceptance": "unverified",
        "generated_code_execution_enabled": False,
        "autonomous_publication_enabled": False,
    }
    (output / "preview.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    files = sorted(output.iterdir())
    checksums = "".join(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n" for path in files
    )
    (output / "SHA256SUMS").write_text(checksums, encoding="ascii")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("output", type=Path, help="New output directory; never overwritten")
    args = parser.parse_args()
    print(json.dumps(package(args.wheel, args.output)))
