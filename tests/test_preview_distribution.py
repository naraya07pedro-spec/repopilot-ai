"""Preview bundle provenance, byte integrity, dirty-source and overwrite boundaries."""

import hashlib
import importlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def preview(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(source / "scripts"))
    module = importlib.import_module("package_preview")
    root = tmp_path / "source"
    root.mkdir()
    wheel = tmp_path / "repopilot_ai-0.2.0-py3-none-any.whl"
    package_files = [*source.joinpath("repopilot").glob("*.py")]
    package_files += [source / "repopilot/pytest.ini", *source.joinpath("repopilot/web").glob("*")]
    with zipfile.ZipFile(wheel, "w") as archive:
        for path in package_files:
            if path.is_file():
                name = path.relative_to(source)
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                archive.writestr(name.as_posix(), path.read_bytes())
    for name in (
        "LICENSE",
        "requirements.lock",
        "pyproject.toml",
        "docs/self-hosted.md",
        "docs/preview-release.md",
        "scripts/package_preview.py",
    ):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    for args in (
        ["init", "--template="],
        ["add", "."],
        ["commit", "-m", "Audited package fixture"],
    ):
        subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=" + os.devnull,
                "-c",
                "commit.gpgsign=false",
                "-c",
                "user.name=Package Test",
                "-c",
                "user.email=package@example.invalid",
                *args,
            ],
            cwd=root,
            check=True,
            capture_output=True,
            timeout=15,
        )
    monkeypatch.setattr(module, "ROOT", root)
    return module, root, wheel, tmp_path / "bundle"


def test_bundle_checksums_and_source_match_committed_provenance(preview):
    module, root, wheel, output = preview
    # Untracked private state must never enter the source download.
    (root / "private-session.txt").write_text("test-only-do-not-archive", encoding="utf-8")
    record = module.package(wheel, output)
    assert (
        record["source_commit"]
        == subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=15
        ).strip()
    )
    assert record["real_model_through_workspace_acceptance"] == "unverified"
    assert record["generated_code_execution_enabled"] is False
    assert record["autonomous_publication_enabled"] is False
    assert json.loads((output / "preview.json").read_text()) == record
    checksums = dict(
        reversed(line.split("  ", 1)) for line in (output / "SHA256SUMS").read_text().splitlines()
    )
    assert set(checksums) == {p.name for p in output.iterdir()} - {"SHA256SUMS"}
    for name, checksum in checksums.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == checksum
    with zipfile.ZipFile(output / "source.zip") as archive:
        assert "private-session.txt" not in archive.namelist()
        assert archive.read("repopilot/web/index.html") == subprocess.check_output(
            ["git", "show", "HEAD:repopilot/web/index.html"], cwd=root, timeout=15
        )


def test_dirty_candidate_refuses_to_claim_committed_provenance(preview):
    module, root, wheel, output = preview
    (root / "requirements.lock").write_text("changed dependency constraints\n", encoding="utf-8")
    with pytest.raises(subprocess.CalledProcessError):
        module.package(wheel, output)
    assert not output.exists()


def test_stale_wheel_is_rejected_before_bundle_creation(preview):
    module, _, wheel, output = preview
    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("repopilot/worker_probes.json", "{}")
    with pytest.raises(ValueError, match="differ"):
        module.package(wheel, output)
    assert not output.exists()


def test_untracked_package_source_cannot_claim_commit(preview):
    module, root, wheel, output = preview
    (root / "repopilot/uncommitted.py").write_text("# uncommitted\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Untracked package source"):
        module.package(wheel, output)
    assert not output.exists()


def test_existing_destination_is_preserved(preview):
    module, _, wheel, output = preview
    output.mkdir()
    sentinel = output / "existing.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError):
        module.package(wheel, output)
    assert sentinel.read_text() == "preserve"
