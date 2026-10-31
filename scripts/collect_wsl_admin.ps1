# Read-only elevated diagnostics. Writes only a new local report directory on D:.
# Does not restart/stop services or distros, enable logs, collect raw dumps, or edit settings.
param(
    [string] $Distribution = 'OpenClawGateway',
    [string] $OutputDirectory = 'D:\Projects\repopilot-local\wsl-diagnosis-2026-10-31'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($Distribution -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$') { throw 'Invalid distro identifier.' }
$rpIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$rpElevated = ([Security.Principal.WindowsPrincipal]$rpIdentity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $rpElevated) { throw 'Run this read-only collector from an Administrator PowerShell terminal.' }
$rpOutput = [IO.Path]::GetFullPath($OutputDirectory)
if (-not $rpOutput.StartsWith('D:\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be on D:.' }
$rpReportDirectory = Join-Path $rpOutput ('admin-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $rpReportDirectory | Out-Null

function Invoke-ReadOnlyClient([string] $rpExecutable, [string[]] $rpArguments, [string] $rpInput = '') {
    # Arguments are fixed ASCII tokens or the validated distro identifier; no shell is involved.
    $rpStartInfo = [Diagnostics.ProcessStartInfo]::new()
    $rpStartInfo.FileName = $rpExecutable
    $rpStartInfo.Arguments = $rpArguments -join ' '
    $rpStartInfo.UseShellExecute = $false
    $rpStartInfo.CreateNoWindow = $true
    $rpStartInfo.RedirectStandardInput = $true
    $rpStartInfo.RedirectStandardOutput = $true
    $rpStartInfo.RedirectStandardError = $true
    $rpClient = [Diagnostics.Process]::new()
    $rpClient.StartInfo = $rpStartInfo
    $rpStdout = [IO.MemoryStream]::new()
    $rpStderr = [IO.MemoryStream]::new()
    try {
        [void]$rpClient.Start()
        $rpOutTask = $rpClient.StandardOutput.BaseStream.CopyToAsync($rpStdout)
        $rpErrTask = $rpClient.StandardError.BaseStream.CopyToAsync($rpStderr)
        if ($rpInput) { $rpClient.StandardInput.Write($rpInput.Replace([string][char]13,'')) }
        $rpClient.StandardInput.Close()
        $rpTimedOut = -not $rpClient.WaitForExit(25000)
        if ($rpTimedOut) {
            # Preserve the connection: forcibly closing clients may aggravate init/interop bugs.
            [ordered]@{client_pid=$rpClient.Id;executable=$rpExecutable;deadline_exceeded=$true;client_terminated=$false} |
                ConvertTo-Json | Set-Content -LiteralPath (Join-Path $rpReportDirectory 'pending-client.json')
            $rpClient.WaitForExit()
        }
        $rpOutputReady = [Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]@($rpOutTask,$rpErrTask),5000)
        if (-not $rpOutputReady) {
            return [ordered]@{exit_code=$rpClient.ExitCode;timed_out=$true;stdout='';stderr='Diagnostic output did not close before the read deadline.'}
        }
        $rpDecoded = @()
        foreach ($rpBytes in @($rpStdout.ToArray(), $rpStderr.ToArray())) {
            $rpHasNull = $false
            for ($rpIndex=0; $rpIndex -lt [Math]::Min(100,$rpBytes.Length); $rpIndex++) {
                if ($rpBytes[$rpIndex] -eq 0) { $rpHasNull=$true; break }
            }
            $rpEncoding = if ($rpHasNull) { [Text.Encoding]::Unicode } else { [Text.Encoding]::UTF8 }
            $rpDecoded += $rpEncoding.GetString($rpBytes).Trim([char]0xFEFF).Trim()
        }
        return [ordered]@{exit_code=$rpClient.ExitCode;timed_out=$rpTimedOut;stdout=$rpDecoded[0];stderr=$rpDecoded[1]}
    } finally {
        $rpClient.Dispose()
        $rpStdout.Dispose()
        $rpStderr.Dispose()
    }
}

$rpWsl = Join-Path $env:WINDIR 'System32\wsl.exe'
$rpRegistration = @(Get-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Lxss\*' -ErrorAction SilentlyContinue |
    Select-Object DistributionName,Version,BasePath,DefaultUid,State,Flags)
$rpServices = @(Get-Service WslService,vmcompute,hns,HvHost -ErrorAction SilentlyContinue |
    Select-Object Name,Status,StartType)
$rpEvents = @{}
foreach ($rpChannel in @(
    'Microsoft-Windows-Hyper-V-Compute-Admin',
    'Microsoft-Windows-Hyper-V-Worker-Admin',
    'Microsoft-Windows-Host-Network-Service-Admin',
    'Microsoft-Windows-Hyper-V-Hypervisor-Admin'
)) {
    try {
        $rpEntries = @(Get-WinEvent -FilterHashtable @{LogName=$rpChannel;StartTime=(Get-Date).AddHours(-24);Level=1,2,3} -MaxEvents 40 -ErrorAction Stop |
            Select-Object TimeCreated,Id,ProviderName,LevelDisplayName,Message)
        $rpEvents[$rpChannel] = [ordered]@{read_completed=$true;events=$rpEntries}
    } catch {
        $rpEvents[$rpChannel] = [ordered]@{read_completed=$false;error=$_.Exception.Message}
    }
}
$rpEvents | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $rpReportDirectory 'local-event-messages.json')
# Fixed read-only VM commands. No process command lines, environment values, or credential files.
$rpCommands = @'
uname -r
cat /proc/uptime
ps -o pid,ppid,comm
dmesg | grep -E 'init: Interop|executable: !init|LxMessageResultBool|SocketChannel.h|Broken pipe|CreateLoginSession|hvsocket|accept4|SIGABRT|Out of memory|oom-kill|Killed process' | tail -n 60
exit
'@
$rpRunning = Invoke-ReadOnlyClient $rpWsl @('--list','--running','--quiet')
$rpRunningNames = @($rpRunning.stdout -split '\r?\n' | ForEach-Object { $_.Trim() })
if ($rpRunning.exit_code -ne 0 -or $Distribution -notin $rpRunningNames) {
    throw 'The selected distro is not reported running; no VM shell or Linux command was started.'
}
$rpDebug = Invoke-ReadOnlyClient $rpWsl @('--debug-shell') ($rpCommands + [char]10)
$rpHcs = Invoke-ReadOnlyClient (Join-Path $env:WINDIR 'System32\hcsdiag.exe') @('list')
$rpEcho = Invoke-ReadOnlyClient $rpWsl @('--distribution',$Distribution,'--user','root','--cd','/','--exec','/bin/echo','repopilot-linux-validation')
$rpLinuxWorks = $rpEcho.exit_code -eq 0 -and $rpEcho.stdout -match 'repopilot-linux-validation'
$rpResult = [ordered]@{
    measured_at=(Get-Date).ToString('o')
    elevated=$true
    distribution=$Distribution
    registration=$rpRegistration
    running_distribution_check=$rpRunning
    services=$rpServices
    volumes=@(Get-Volume -DriveLetter C,D | Select-Object DriveLetter,Size,SizeRemaining)
    memory=Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory
    debug_shell=$rpDebug
    compute_inventory=$rpHcs
    real_distro_linux_probe=$rpEcho
    real_distro_linux_command_passed=$rpLinuxWorks
    service_or_distro_stop_restart=$false
    settings_changed=$false
    distributions_created_removed_relocated=$false
    raw_crash_memory_collected=$false
    event_messages_file='local-event-messages.json'
}
$rpResult | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $rpReportDirectory 'admin-result.json')
[ordered]@{
    report_directory=$rpReportDirectory
    real_distro_linux_command_passed=$rpLinuxWorks
    debug_shell_exit=$rpDebug.exit_code
    no_stop_restart_or_settings_change=$true
    note='Inspect local reports for cause. Do not publish raw logs or claim recovery from status alone.'
} | ConvertTo-Json
