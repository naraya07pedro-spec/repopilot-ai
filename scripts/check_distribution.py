"""Install a built wheel into a NEW environment and smoke it outside the source checkout."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def verify_wheel(wheel: Path) -> int:
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        source = Path(__file__).resolve().parents[1]
        expected = [*source.joinpath("repopilot").glob("*.py"), source / "repopilot/pytest.ini"]
        expected += [
            source / "repopilot/web" / name
            for name in ("index.html", "workspace.js", "workspace.css")
        ]
        expected_names = {p.relative_to(source).as_posix() for p in expected}
        if {n for n in names if n.startswith("repopilot/")} != expected_names:
            raise ValueError(
                "Wheel package files differ from current release source; use a clean sdist"
            )
        for path in expected:
            name = path.relative_to(source).as_posix()
            if (
                hashlib.sha256(archive.read(name)).digest()
                != hashlib.sha256(path.read_bytes()).digest()
            ):
                raise ValueError("Wheel contains stale source bytes: " + name)
        forbidden = {
            "repopilot/hyperv_preparation.py",
            "repopilot/isolation_probes.py",
            "repopilot/worker_probes.json",
        }
        if names & forbidden:
            raise ValueError("Rejected stale experimental files in wheel; build from a clean sdist")
        for asset in ("index.html", "workspace.js", "workspace.css"):
            if "repopilot/web/" + asset not in names:
                raise ValueError("Installed local workspace asset missing: " + asset)
    return len(expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("output", type=Path, help="New directory, existing paths refused")
    parser.add_argument("--record", type=Path, help="New sanitized JSON report file")
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    verified_files = verify_wheel(wheel)
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONPATH", "PYTHONHOME"} and not k.startswith("PIP_")
    }
    env.update(
        TEMP=str(root),
        TMP=str(root),
        PIP_CONFIG_FILE=os.devnull,
        PIP_CACHE_DIR=str(root / "pip-cache"),
    )
    subprocess.run(
        [sys.executable, "-m", "venv", str(root / "venv")],
        cwd=root,
        env=env,
        check=True,
        timeout=120,
    )
    executable = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        [
            str(executable),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--index-url",
            "https://pypi.org/simple",
            "--constraint",
            str(Path(__file__).resolve().parents[1] / "requirements.lock"),
            str(wheel),
        ],
        cwd=root,
        env=env,
        check=True,
        timeout=240,
    )
    subprocess.run(
        [str(executable), "-m", "pip", "check"], cwd=root, env=env, check=True, timeout=30
    )
    smoke = Path(__file__).resolve().with_name("smoke_installed_local.py")
    subprocess.run(
        [str(executable), str(smoke), str(root / "http-smoke")],
        cwd=root,
        env=env,
        check=True,
        timeout=75,
    )
    result = json.loads((root / "http-smoke/installed-smoke.json").read_text(encoding="utf-8"))
    assert Path(result["installed_package"]).is_relative_to(root / "venv")
    result["fresh_environment"] = True
    result["wheel"] = wheel.name
    result["package_source_files_verified"] = verified_files
    if args.record:
        with args.record.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
    print(
        json.dumps(
            {"fresh_installation": "passed", "platform": sys.platform, "model_invoked": False}
        )
    )


if __name__ == "__main__":
    main()
