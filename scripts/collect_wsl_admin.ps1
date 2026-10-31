# Retired after a confirmed live-client hang. Do not use this script for collection.
# No elevation, WSL call, process wait, or configuration change is performed.
param(
    [string] $Distribution = 'OpenClawGateway',
    [string] $OutputDirectory = 'D:\Projects\repopilot-local\wsl-diagnosis-2026-10-31'
)
throw 'This live collector is retired. Do not rerun it. Use scripts/analyze_wsl_evidence.py on the saved evidence directory; see docs/pc-wsl-diagnosis.md.'
