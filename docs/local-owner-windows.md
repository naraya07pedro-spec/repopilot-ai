# Local owner workspace on Windows

This starts the authenticated planning UI without paid hosting. It does not activate code
execution. The public Pages site is separate and remains available without this setup.
Use Python 3.12+, Git, and Node 22.12+. Run these commands from the repository root.
First run `./scripts/audit-local-windows.ps1` and read [local feasibility](local-feasibility.md).
The audited machine has 4 GB RAM, not the approximate 8 GB estimate; no heavy install is automatic.

## Install the locked development environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements.lock -e ".[dev,postgres]"
Push-Location frontend
npm.cmd ci
npm.cmd run build
Pop-Location
```

No PowerShell activation or execution-policy change is needed. This installs application tools,
not dependencies from an untrusted task repository. Keep environment files outside Git.

## Start the private API

In the first PowerShell terminal:

```powershell
$env:REPOPILOT_MODE = 'owner'
$env:REPOPILOT_ORIGIN = 'http://127.0.0.1:3000'
$env:REPOPILOT_COOKIE_SECURE = 'false'
$env:REPOPILOT_ALLOW_PAID_MODELS = 'false'
$env:REPOPILOT_DAILY_USD = '0'
$env:REPOPILOT_RUN_USD = '0'
$env:REPOPILOT_OWNER_PASSWORD_HASH = (& .\.venv\Scripts\python.exe scripts/hash_owner_password.py).Trim()
$env:REPOPILOT_REPOSITORIES = 'naraya07pedro-spec/repopilot-ai'
$env:REPOPILOT_SOURCE_ROOTS = '{"naraya07pedro-spec/repopilot-ai":"fixtures/bug"}'
.\.venv\Scripts\python.exe -m repopilot.doctor
.\.venv\Scripts\python.exe -m uvicorn repopilot.api:create_app --factory --host 127.0.0.1 --port 8000
```

The password helper prompts without echo. No model API key is required; keep the App private key outside chat.
The diagnostic prints only presence/status, never credential values; it makes no network calls
and does not modify the database. Without credentials, login/history and truthful unavailable
states work; real planning remains unavailable. SQLite is the no-service local default.

## Start the owner frontend

In a second terminal, from the repository root:

```powershell
$env:REPOPILOT_ORIGIN = 'http://127.0.0.1:3000'
$env:REPOPILOT_BACKEND = 'http://127.0.0.1:8000'
Set-Location frontend
npm.cmd run start
```

Open http://127.0.0.1:3000/owner and sign in. The origin must match in both processes. HTTP
cookies are allowed only for loopback development. Do not expose these local HTTP services
publicly. Production still requires HTTPS, private PostgreSQL and a reviewed worker boundary.

When credentials become available, follow [private workspace](private-workspace.md) and
[provider profiles](providers.md). The server-approved source root selects only the fixture
subdirectory; it is included in request identity and the approved immutable snapshot. Remote
publication maps relative edited paths back under that root. The browser cannot select a
wider scope. No source-root setting grants access to another repository.

## Verify locally without credentials

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest --cov
.\.venv\Scripts\python.exe scripts/scan_secrets.py
.\.venv\Scripts\python.exe -m pip_audit -r requirements.lock
Push-Location frontend
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
$env:PUBLIC_BASE_PATH = '/repopilot-ai'
npm.cmd run build:public
npx.cmd playwright install chromium
$env:PATH = (Resolve-Path ..\.venv\Scripts).Path + ';' + $env:PATH
npm.cmd run test:browser
Pop-Location
```

Browser tests start temporary synthetic services on ports 8011/3011/4173. These are separate
from the owner's processes and credentials. PostgreSQL tests skip locally unless a disposable
test database is explicitly configured; never point TEST_POSTGRES_URL at a shared database.
Windows symlink tests may skip for missing privileges. CI runs those cases on Linux.

## What remains blocked

Execution and private publication remain default-deny with no environment enable switch.
The bounded dispatcher/HTTP transport and publication reconciliation are independently tested,
but a trusted runtime must enforce isolation and supply real authenticated receipts before
being wired into the owner execution route. There is no fallback to host subprocesses.

The worker controller must run in a dedicated Linux environment with a reviewed sandbox,
secret-free guest, network denial, CPU/memory/disk/process limits, process-tree cancellation
and reliable teardown. Both gVisor configurations tested in PR #8 failed before guest execution;
see [runtime requirements and costs](runtime-options.md). Neither
WSL nor Docker alone establishes adequate isolation. No Linux worker is available here.

External gates: GitHub App installation/key, sufficient memory for a genuinely local model,
and verified WSL2/sandbox prerequisites. Paid APIs and rented workers are excluded. No cloud resources or spending
are required to inspect the local workspace and execute deterministic/contract tests.
