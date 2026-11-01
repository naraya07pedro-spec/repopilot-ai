"""Installed-wheel smoke from outside the checkout. No model, code execution or credentials.

Creates a new test-owned Git repository and app state below the specified new directory,
launches only the installed local CLI, verifies its HTTP/assets/auth/errors, then stops it.
For Windows, also verifies startup with a legacy cp1252 console encoding.
"""

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def run(output: Path) -> dict:
    import repopilot

    output.mkdir(parents=True, exist_ok=False)
    root = output / "starter"
    root.mkdir()
    (root / "app.py").write_text(
        "def mean(values):\n    return sum(values) // len(values)\n", encoding="utf-8"
    )
    commands = [
        ["init", "--initial-branch=main", "--template="],
        [
            "-c",
            "user.name=RepoPilot Smoke",
            "-c",
            "user.email=smoke@example.invalid",
            "add",
            "app.py",
        ],
        [
            "-c",
            "user.name=RepoPilot Smoke",
            "-c",
            "user.email=smoke@example.invalid",
            "commit",
            "-m",
            "Known smoke input",
        ],
    ]
    for command in commands:
        subprocess.run(
            ["git", "-c", "core.hooksPath=" + os.devnull, "-c", "commit.gpgsign=false", *command],
            cwd=root,
            capture_output=True,
            timeout=15,
            check=True,
        )
    with socket.socket() as selected:
        selected.bind(("127.0.0.1", 0))
        port = selected.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    missing_runtime = socket.socket()
    missing_runtime.bind(("127.0.0.1", 0))
    missing_port = missing_runtime.getsockname()[1]  # Reserved, deliberately not listening.
    entrypoint = Path(sys.executable).with_name("repopilot.exe" if os.name == "nt" else "repopilot")
    if not entrypoint.is_file():
        raise RuntimeError("installed_repopilot_console_entrypoint_missing")
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONPATH", "REPOPILOT_ENABLE_PAID"}
        and not k.startswith(("OPENAI_", "ANTHROPIC_", "GEMINI_", "GITHUB_"))
    }
    env.update(PYTHONIOENCODING="cp1252", TEMP=str(output), TMP=str(output))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    log_path = output / "private-launcher.log"
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            [
                str(entrypoint),
                "local",
                "--repo",
                str(root),
                "--data",
                str(output / "state"),
                "--model",
                "missing-model-for-install-smoke",
                "--provider",
                "compatible",
                "--endpoint",
                f"http://127.0.0.1:{missing_port}/v1",
                "--port",
                str(port),
            ],
            cwd=output,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}),
        )
        try:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("installed_launcher_exited_before_ready")
                try:
                    with opener.open(origin + "/health", timeout=1) as response:
                        health = json.load(response)
                    break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.2)
            else:
                raise RuntimeError("installed_launcher_startup_timeout")
            # Token remains only in the private log and in memory, never in the report.
            token = re.search(
                r"#session=([A-Za-z0-9_-]+)", log_path.read_text(encoding="cp1252")
            ).group(1)
            headers = {"Authorization": "Bearer " + token, "Origin": origin}

            def get(path, authenticated=False):
                with opener.open(
                    urllib.request.Request(origin + path, headers=headers if authenticated else {}),
                    timeout=5,
                ) as response:
                    return response.status, response.read()

            assets = {}
            for path in ("/", "/workspace.js", "/workspace.css"):
                status, raw = get(path)
                assert status == 200 and raw
                assets[path] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            status, raw = get("/api/local/settings", True)
            settings = json.loads(raw)
            assert status == 200 and settings["execution_enabled"] is False
            assert settings["publication_enabled"] is False
            assert json.loads(get("/api/local/files", True)[1]) == ["app.py"]
            try:
                get("/api/local/settings")
                raise AssertionError("Unauthenticated API request succeeded")
            except urllib.error.HTTPError as error:
                assert error.code == 401
            try:
                request = urllib.request.Request(
                    origin + "/api/local/models/local/check",
                    data=b"{}",
                    headers={**headers, "Content-Type": "application/json"},
                )
                opener.open(request, timeout=5)
                raise AssertionError("Missing runtime was reported available")
            except urllib.error.HTTPError as error:
                assert error.code == 409
                assert json.load(error)["error"] == "provider_transport_unknown"
            assert not health["execution_enabled"] and not health["publication_enabled"]
            return {
                "status": "passed",
                "platform": sys.platform,
                "python": sys.version.split()[0],
                "installed_package": str(Path(repopilot.__file__).resolve()),
                "legacy_console_encoding": "cp1252",
                "assets": assets,
                "authentication_verified": True,
                "missing_runtime_error_verified": True,
                "model_invoked": False,
                "code_executed": False,
                "sandbox_or_publication_enabled": False,
                "test_process_tree_cleanup_verified": True,
            }
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    # Only the live Popen process created above and its children. Windows
                    # console/venv launchers may spawn a Python child; killing just the
                    # launcher can otherwise leave the test listener and its lease alive.
                    taskkill = Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"
                    subprocess.run(
                        [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        timeout=10,
                        check=True,
                    )
                else:
                    process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            missing_runtime.close()
            with socket.socket() as listener:
                listener.settimeout(0.5)
                if listener.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(
                        "test_listener_survived_cleanup_no_broader_cleanup_attempted"
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = run(args.output.resolve())
    (args.output / "installed-smoke.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result))
