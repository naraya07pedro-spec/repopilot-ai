# Read-only hardware audit. No installation, downloads, services, credentials or process inventory.
$ErrorActionPreference = 'Stop'
$rpSystem = Get-CimInstance Win32_ComputerSystem
$rpOs = Get-CimInstance Win32_OperatingSystem
$rpCpu = Get-CimInstance Win32_Processor
$rpModules = Get-CimInstance Win32_PhysicalMemory
$rpFeatures = Get-CimInstance Win32_OptionalFeature -Filter "Name='VirtualMachinePlatform' OR Name='Microsoft-Windows-Subsystem-Linux'"
[ordered]@{
    measured_at = (Get-Date).ToString('o')
    installed_memory_module_bytes = @($rpModules | ForEach-Object { $_.Capacity })
    visible_memory_bytes = $rpSystem.TotalPhysicalMemory
    available_memory_kib = $rpOs.FreePhysicalMemory
    windows_version = $rpOs.Version
    windows_build = $rpOs.BuildNumber
    cpu = $rpCpu.Name
    cpu_cores = $rpCpu.NumberOfCores
    logical_processors = $rpCpu.NumberOfLogicalProcessors
    firmware_virtualization = $rpCpu.VirtualizationFirmwareEnabled
    slat = $rpCpu.SecondLevelAddressTranslationExtensions
    hypervisor_present = $rpSystem.HypervisorPresent
    drive_c_free_bytes = (Get-PSDrive C).Free
    features = @($rpFeatures | Select-Object Name,InstallState)
    tools = @(foreach ($rpName in @('wsl', 'ollama', 'podman', 'docker')) {
        [ordered]@{ name = $rpName; available = [bool](Get-Command $rpName -ErrorAction SilentlyContinue) }
    })
    admin_session = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    installs_or_network_calls = $false
} | ConvertTo-Json -Depth 4
