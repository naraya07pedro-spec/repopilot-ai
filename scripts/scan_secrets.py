"""Scan tracked text for configured credential patterns. This is not exhaustive."""

import subprocess
from pathlib import Path

from repopilot.policy import SECRET

names = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
findings = []
for name in names:
    path = Path(name)
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeError, OSError):
        continue
    if SECRET.search(text):
        findings.append(name)
if findings:
    raise SystemExit("Credential pattern found in: " + ", ".join(findings))
print(f"Checked {len(names)} tracked files; no configured credential patterns found.")
