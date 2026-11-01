# Dedicated prototype lifecycle only. This is NOT an enabled RepoPilot worker.
# Plan is read-only and does not load Hyper-V. Mutating modes require owner UAC approval.
param(
    [ValidateSet('Plan','Create','Start','Inspect','Cleanup')][string]$Mode = 'Plan',
    [string]$IsoPath = '',
    [string]$StateFile = ''
)
$ErrorActionPreference = 'Stop'
$rpRoot = 'D:\Projects\repopilot-local\hyperv-worker'
$rpIsoHash = 'cdc1bc0efc64d8d611bf3733f54868172a545888dfd726f518bf279bcb0ff1af'
$rpPlan = [ordered]@{
    status = 'prototype_only_not_a_validated_worker'
    root = $rpRoot
    generation = 1
    boot = 'hash-pinned read-only Alpine ISO; no virtual hard disk'
    memory_bytes = 536870912
    virtual_processors = 1
    network_adapters = 0
    host_shares = 0
    host_security_or_feature_changes = $false
    secure_boot_note = 'New Generation 1 guest uses BIOS; host Secure Boot is not changed.'
    guest_worker_tools_built = $false
    isolated_execution_validated = $false
}
if ($Mode -eq 'Plan') { $rpPlan | ConvertTo-Json; exit 0 }
$rpIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$rpPrincipal = [Security.Principal.WindowsPrincipal]::new($rpIdentity)
if (-not $rpPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Administrator UAC is required; no automatic elevation or fallback is attempted.'
}
Import-Module Hyper-V -ErrorAction Stop
function Assert-RpChild([string]$Value) {
    $resolved = [IO.Path]::GetFullPath($Value)
    if (-not $resolved.StartsWith($rpRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Path is outside the dedicated RepoPilot VM root.'
    }
    # Reject junctions/symlinks in every existing component, including the root.
    $part = $resolved
    while ($part -and $part.Length -gt 3) {
        if (Test-Path -LiteralPath $part) {
            $item = Get-Item -LiteralPath $part -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Reparse points are not accepted in prototype paths.'
            }
        }
        $part = [IO.Path]::GetDirectoryName($part)
    }
    return $resolved
}
function Assert-RpSettings($Vm, [string]$ExpectedFolder) {
    if ($Vm.Name -notmatch '^RepoPilot-Isolation-[a-f0-9]{32}$') { throw 'VM name mismatch.' }
    $configuration = Assert-RpChild $Vm.ConfigurationLocation
    if (-not $configuration.StartsWith($ExpectedFolder + '\',
            [StringComparison]::OrdinalIgnoreCase) -and $configuration -ne $ExpectedFolder) {
        throw 'VM configuration does not belong to this exact prototype directory.'
    }
    if ($Vm.Generation -ne 1 -or $Vm.MemoryStartup -ne 512MB -or $Vm.DynamicMemoryEnabled -or
        $Vm.ProcessorCount -ne 1 -or @(Get-VMNetworkAdapter -VM $Vm).Count -ne 0 -or
        @(Get-VMHardDiskDrive -VM $Vm).Count -ne 0) {
        throw 'VM effective settings differ from the bounded diskless proposal.'
    }
}
if ($Mode -eq 'Create') {
    $rpMedia = Assert-RpChild $IsoPath
    if ((Get-FileHash -LiteralPath $rpMedia -Algorithm SHA256).Hash -ne $rpIsoHash) {
        throw 'Boot media hash mismatch.'
    }
    $rpTag = [Guid]::NewGuid().ToString('N')
    $rpFolder = Assert-RpChild (Join-Path $rpRoot $rpTag)
    New-Item -ItemType Directory -Path $rpFolder -ErrorAction Stop | Out-Null
    $rpStatePath = Join-Path $rpFolder 'owned-vm.json'
    $rpVm = New-VM -Name ('RepoPilot-Isolation-' + $rpTag) -Generation 1 -NoVHD `
        -MemoryStartupBytes 512MB -BootDevice CD -Path $rpFolder
    # Save identity immediately. On any failure, inspect this ID; never retry creation blindly.
    [ordered]@{vm_id=$rpVm.Id.ToString(); name=$rpVm.Name; folder=$rpFolder;
        iso=$rpMedia; iso_sha256=$rpIsoHash; phase='created_off_not_validated'} |
        ConvertTo-Json | Set-Content -LiteralPath $rpStatePath -Encoding UTF8
    Set-VMMemory -VM $rpVm -DynamicMemoryEnabled $false -StartupBytes 512MB
    Set-VM -VM $rpVm -AutomaticStartAction Nothing `
        -AutomaticStopAction TurnOff -CheckpointType Disabled
    Set-VMProcessor -VM $rpVm -Count 1 -Maximum 100
    Get-VMNetworkAdapter -VM $rpVm | Remove-VMNetworkAdapter
    $rpDvd = @(Get-VMDvdDrive -VM $rpVm)
    if ($rpDvd.Count -eq 0) { Add-VMDvdDrive -VM $rpVm -Path $rpMedia | Out-Null }
    elseif ($rpDvd.Count -eq 1) { Set-VMDvdDrive -VMDvdDrive $rpDvd[0] -Path $rpMedia }
    else { throw 'Unexpected DVD topology; leave the owned VM off for inspection.' }
    $rpVm = Get-VM -Id $rpVm.Id
    Assert-RpSettings $rpVm $rpFolder
    @{state_file=$rpStatePath; state=$rpVm.State.ToString(); validated_worker=$false} |
        ConvertTo-Json
    exit 0
}
$rpStatePath = Assert-RpChild $StateFile
if ([IO.Path]::GetFileName($rpStatePath) -ne 'owned-vm.json') { throw 'Invalid state filename.' }
$rpState = Get-Content -LiteralPath $rpStatePath -Raw | ConvertFrom-Json
$rpFolder = Assert-RpChild $rpState.folder
if ([IO.Path]::GetDirectoryName($rpStatePath) -ne $rpFolder -or
    $rpState.name -notmatch '^RepoPilot-Isolation-[a-f0-9]{32}$') { throw 'State scope mismatch.' }
$rpVm = Get-VM -Id ([Guid]$rpState.vm_id)
if ($rpVm.Name -ne $rpState.name) { throw 'VM identity mismatch.' }
Assert-RpSettings $rpVm $rpFolder
if ($Mode -eq 'Inspect') {
    @{vm_id=$rpVm.Id.ToString(); state=$rpVm.State.ToString(); memory=$rpVm.MemoryStartup;
        processors=$rpVm.ProcessorCount; network_adapters=0; virtual_disks=0;
        validated_worker=$false} | ConvertTo-Json
} elseif ($Mode -eq 'Start') {
    $rpMemory = Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 2
    if ([long]$rpMemory.FreePhysicalMemory * 1024 -lt 1536MB) { throw 'Insufficient RAM headroom.' }
    $rpMedia = Assert-RpChild $rpState.iso
    if ((Get-FileHash -LiteralPath $rpMedia -Algorithm SHA256).Hash -ne $rpIsoHash) {
        throw 'Boot media changed.'
    }
    $rpDvd = @(Get-VMDvdDrive -VM $rpVm)
    if ($rpDvd.Count -ne 1 -or $rpDvd[0].Path -ne $rpMedia) { throw 'DVD media mismatch.' }
    if ($rpVm.State.ToString() -ne 'Off') { throw 'Only a confirmed stopped prototype can start.' }
    Start-VM -VM $rpVm
    @{vm_id=$rpVm.Id.ToString(); action='start_requested'; validated_worker=$false} | ConvertTo-Json
} elseif ($Mode -eq 'Cleanup') {
    # Only this new, exact, scoped VM. Never enumerate by wildcard or touch other VM disks.
    if ($rpVm.State.ToString() -ne 'Off') { Stop-VM -VM $rpVm -TurnOff -Confirm:$false }
    $rpVm = Get-VM -Id $rpVm.Id
    if ($rpVm.State.ToString() -ne 'Off') { throw 'Owned VM stop is unconfirmed; do not remove.' }
    Remove-VM -VM $rpVm -Confirm:$false
    if (@(Get-VM | Where-Object { $_.Id -eq [Guid]$rpState.vm_id }).Count -ne 0) {
        throw 'Owned VM removal is unconfirmed.'
    }
    # ISO, state and evidence files are retained. No filesystem deletion is performed.
    @{owned_vm_removed=$true; evidence_retained=$true; validated_worker=$false} | ConvertTo-Json
}
