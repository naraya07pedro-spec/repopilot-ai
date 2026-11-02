"""Bounded Windows metadata only; never starts a WSL client or changes its state."""

import base64
import json
import os
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

DEADLINE_SECONDS = 15
CLEANUP_SECONDS = 2
MAX_OUTPUT_BYTES = 256 * 1024

# Fixed local queries. No external commands, event bodies, environment or full command lines
# are emitted. A timeout may end only this script's own metadata PowerShell worker.
METADATA_QUERY = r"""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
function Emit($section, $data) {
    [Console]::WriteLine((@{section=$section; data=$data} | ConvertTo-Json -Depth 6 -Compress))
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
Emit 'token' @{elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)}
$registrations = @()
try {
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
    $registrations = @(Get-ChildItem -LiteralPath $key |
        Select-Object -First 32 | ForEach-Object {
            $v = Get-ItemProperty -LiteralPath $_.PSPath
            @{id=$_.PSChildName; name=$v.DistributionName;
                version=$v.Version; default_uid=$v.DefaultUid}
        })
    Emit 'registrations' @{status='read'; entries=$registrations}
} catch { Emit 'registrations' @{status='unavailable'} }
try {
    $filter = "Name='WslService' OR Name='vmcompute' OR Name='hns' OR Name='HvHost'"
    $services = @(Get-CimInstance Win32_Service -OperationTimeoutSec 2 -Filter $filter |
        ForEach-Object {
            $account = 'other'
            if ($_.StartName -eq 'LocalSystem') { $account = 'LocalSystem' }
            @{name=$_.Name; state=$_.State; pid=$_.ProcessId; exit_code=$_.ExitCode;
              configured_account=$account}
        })
    Emit 'services' @{status='read'; entries=$services}
} catch { Emit 'services' @{status='unavailable'; error_kind=$_.Exception.GetType().Name} }
try {
    $filter = "Name='wsl.exe' OR Name='wslservice.exe' OR Name='wslhost.exe' OR " +
        "Name='wslrelay.exe' OR Name='vmmemWSL' OR Name='vmcompute.exe' OR " +
        "Name='OpenClaw.Tray.WinUI.exe' OR ProcessId=28432 OR ProcessId=24704"
    $processes = @(Get-CimInstance Win32_Process -Filter $filter -OperationTimeoutSec 2 |
        Select-Object -First 32)
    foreach ($p in $processes) {
        $owner = 'unavailable'
        $ownerCode = $null
        try {
            $o = Invoke-CimMethod -InputObject $p -MethodName GetOwner -OperationTimeoutSec 2
            $ownerCode = $o.ReturnValue
            if ($o.ReturnValue -eq 0) {
                $owner = if (($o.Domain + '\' + $o.User) -ieq $identity.Name) {
                    'current_windows_user'}
                    elseif ($o.User -eq 'SYSTEM' -and $o.Domain -eq 'NT AUTHORITY') {'LocalSystem'}
                    else {'other_account'}
            }
        } catch { $owner = 'query_failed' }
        $mapped = @($registrations | Where-Object {
            $p.CommandLine -and $p.CommandLine.IndexOf($_.id.Trim('{}'),
                [StringComparison]::OrdinalIgnoreCase) -ge 0
        } | ForEach-Object {$_.name})
        Emit 'process' @{name=$p.Name; pid=$p.ProcessId; parent_pid=$p.ParentProcessId;
            created_utc=$p.CreationDate.ToUniversalTime().ToString('o'); owner=$owner;
            owner_result=$ownerCode; command_line_readable=($null -ne $p.CommandLine);
            image_path_readable=($null -ne $p.ExecutablePath);
            registered_distro_ids_in_arguments=$mapped}
    }
    Emit 'process_query' @{status='read'; count=$processes.Count}
} catch { Emit 'process_query' @{status='unavailable'} }
try {
    $v = Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 2
    Emit 'resources' @{available_ram_bytes=([long]$v.FreePhysicalMemory * 1024);
        c_free_bytes=([IO.DriveInfo]::new('C:\').AvailableFreeSpace);
        d_free_bytes=([IO.DriveInfo]::new('D:\').AvailableFreeSpace)}
} catch { Emit 'resources' @{status='unavailable'} }
Emit 'completed' $true
"""


def collect() -> dict:
    """Return partial evidence on deadline; never wait indefinitely or kill a WSL PID."""
    if os.name != "nt":
        raise RuntimeError("Windows metadata inspection requires Windows")
    started = time.monotonic()
    executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    encoded = base64.b64encode(METADATA_QUERY.encode("utf-16-le")).decode("ascii")
    result = {
        "captured_utc": datetime.now(UTC).isoformat(),
        "mode": "windows_metadata_only",
        "deadline_seconds": DEADLINE_SECONDS,
        "cleanup_deadline_seconds": CLEANUP_SECONDS,
        "wsl_clients_started": 0,
        "recovery_executed": False,
        "current_linux_health": "not_tested",
        "records": [],
    }
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        worker = subprocess.Popen(
            [
                str(executable),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                encoded,
            ],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=errors,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        result["metadata_worker_pid"] = worker.pid
        try:
            worker.wait(timeout=DEADLINE_SECONDS)
            result["deadline_exceeded"] = False
        except subprocess.TimeoutExpired:
            result["deadline_exceeded"] = True
            # Only the Popen handle created above, never any enumerated/existing process.
            try:
                worker.kill()
            except OSError:
                result["metadata_worker_cleanup_error"] = True
            try:
                worker.wait(timeout=CLEANUP_SECONDS)
            except subprocess.TimeoutExpired:
                result["metadata_worker_exit_unconfirmed"] = True
        result["metadata_worker_exit_code"] = worker.returncode
        output.seek(0)
        raw = output.read(MAX_OUTPUT_BYTES + 1)
        result["output_limit_exceeded"] = len(raw) > MAX_OUTPUT_BYTES
        if not result["output_limit_exceeded"]:
            for line in raw.decode("utf-8-sig", errors="replace").splitlines():
                try:
                    record = json.loads(line)
                    if isinstance(record, dict):
                        result["records"].append(record)
                except ValueError:
                    result["incomplete_output_line"] = True
        # Error text is deliberately excluded from the public report.
        errors.seek(0)
        result["stderr_present"] = bool(errors.read(1))
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


if __name__ == "__main__":
    print(json.dumps(collect(), indent=2))
