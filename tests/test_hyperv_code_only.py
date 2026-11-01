"""Windows CLI authorization guard only; no Hyper-V command or live probe is run."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell CLI guard test")
def test_all_vm_operations_are_blocked_before_hyperv_is_loaded():
    script = Path(__file__).resolve().parents[1] / "scripts/hyperv_probe_vm.ps1"
    literal = "'" + str(script).replace("'", "''") + "'"
    command = (
        "$ErrorActionPreference='Stop';"
        "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
        "$results=@();"
        "foreach($mode in @('Plan','Create','Start','Inspect','Cleanup')) {"
        "try {"
        f"$text=(& {literal} -Mode $mode "
        "-IsoPath 'unused.iso' -StateFile 'unused.json' | Out-String);"
        "$results+=@{mode=$mode;returned=$true;plan=($text|ConvertFrom-Json)}"
        "} catch {"
        "$results+=@{mode=$mode;returned=$false;error=$_.Exception.Message}"
        "}};"
        "@{results=$results;hyperv_loaded=[bool](Get-Module -Name Hyper-V)}|ConvertTo-Json -Depth 6"
    )
    executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run(
        [str(executable), "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        timeout=20,
        check=True,
    )
    report = json.loads(result.stdout.decode("utf-8-sig"))
    assert report["hyperv_loaded"] is False
    outcomes = report["results"]
    assert [r["mode"] for r in outcomes] == ["Plan", "Create", "Start", "Inspect", "Cleanup"]
    assert outcomes[0]["returned"] is True
    assert outcomes[0]["plan"]["vm_operations_enabled"] is False
    assert outcomes[0]["plan"]["isolated_execution_validated"] is False
    for outcome in outcomes[1:]:
        assert outcome["returned"] is False
        assert "REPOPILOT_VM_OPERATIONS_DISABLED" in outcome["error"]
