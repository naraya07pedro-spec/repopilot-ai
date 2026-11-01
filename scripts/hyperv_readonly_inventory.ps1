# Read-only capability inventory. No Get-VM, VM operations, WSL, UAC or process command lines.
# Invoked by hyperv_preflight.py with a strict 25-second child-process timeout.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$rpOs = Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 5
$rpSystem = Get-CimInstance Win32_ComputerSystem -OperationTimeoutSec 5
$rpCpu = Get-CimInstance Win32_Processor -OperationTimeoutSec 5
$rpFeatures = @()
$rpFeatureStatus = 'collected'
try {
    $rpFeatures = Get-CimInstance Win32_OptionalFeature -OperationTimeoutSec 5 -Filter `
        "Name='Microsoft-Hyper-V-All' OR Name='Microsoft-Hyper-V-Management-PowerShell'"
} catch {
    # A slow optional-feature query must not erase the already collected host facts.
    $rpFeatureStatus = 'unconfirmed_query_failed_or_timed_out_no_retry'
}
[ordered]@{
    caption = $rpOs.Caption
    version = $rpOs.Version
    build = $rpOs.BuildNumber
    visible_ram_bytes = [long]$rpOs.TotalVisibleMemorySize * 1024
    cpu_name = @($rpCpu | ForEach-Object { $_.Name.Trim() })
    logical_processors = $rpSystem.NumberOfLogicalProcessors
    virtualization_firmware_enabled = @($rpCpu.VirtualizationFirmwareEnabled)
    hypervisor_present = $rpSystem.HypervisorPresent
    features = @($rpFeatures | Select-Object Name,InstallState)
    optional_feature_query = $rpFeatureStatus
    vmms = (Get-Service -Name vmms).Status.ToString()
    elevated = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    partitions = @(Get-Partition -DriveLetter C,D | Select-Object DriveLetter,DiskNumber,PartitionNumber)
    disks = @(Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,Size)
    hyperv_commands = @(Get-Command Get-VM,New-VM,Set-VMComPort,Remove-VM |
        Select-Object Name,Source)
    VM_inventory = 'not_attempted_prior_session_permission_denial_preserved'
    VM_operations = $false
    WSL_operations = $false
} | ConvertTo-Json -Depth 5
