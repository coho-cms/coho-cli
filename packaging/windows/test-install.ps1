<#
.SYNOPSIS
  Installs the Coho CLI MSI, checks what a user would get, and uninstalls it again.

.DESCRIPTION
  Needs an elevated shell, which GitHub's Windows runners are. Checks that coho.exe lands
  in Program Files\Coho CLI, that `coho` resolves from the machine PATH a new terminal
  would see and reports -Version, and that uninstalling takes both away again.

.EXAMPLE
  pwsh packaging/windows/test-install.ps1 -Msi out/coho-2026.2.4-windows-x64.msi -Version 2026.2.4
#>
param(
    [Parameter(Mandatory)] [string] $Msi,
    [Parameter(Mandatory)] [string] $Version
)

$ErrorActionPreference = 'Stop'

$Msi = (Resolve-Path $Msi).Path
$folder = Join-Path $env:ProgramFiles 'Coho CLI'
$logs = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [IO.Path]::GetTempPath() }

function Invoke-Msiexec([string] $action, [string] $log) {
    $process = Start-Process msiexec.exe -Wait -PassThru `
        -ArgumentList @($action, "`"$Msi`"", '/qn', '/norestart', '/l*v', "`"$log`"")
    if ($process.ExitCode -ne 0) {
        Get-Content $log -Tail 80
        throw "msiexec $action exited $($process.ExitCode); the log is $log"
    }
}

function Get-MachinePath {
    [Environment]::GetEnvironmentVariable('Path', 'Machine') -split ';' | Where-Object { $_ }
}

function Test-OnPath {
    @(Get-MachinePath | Where-Object { $_.TrimEnd('\') -eq $folder }).Count -gt 0
}

Invoke-Msiexec '/i' (Join-Path $logs 'coho-install.log')

if (-not (Test-Path (Join-Path $folder 'coho.exe'))) { throw "coho.exe is not in $folder" }
if (-not (Test-OnPath)) { throw "$folder is not on the machine PATH" }

# What a new terminal sees: the machine PATH plus this user's.
$env:Path = ((Get-MachinePath) + ([Environment]::GetEnvironmentVariable('Path', 'User') -split ';')) -join ';'
$coho = (Get-Command coho -CommandType Application).Source
Write-Host "coho resolves to $coho"
if ((Split-Path $coho -Parent).TrimEnd('\') -ne $folder) { throw "coho resolves to $coho, not the installed one" }

# One string: --version prints a banner over several lines, and -notmatch on an array
# filters it instead of answering yes or no.
$reported = (& coho --version) -join "`n"
Write-Host $reported
if ($reported -notmatch [regex]::Escape("v$Version")) { throw "coho --version said '$reported', not v$Version" }
& coho --help | Out-Null

$installed = Get-ItemProperty 'HKLM:\Software\Coho\CLI' -Name InstallFolder
Write-Host "HKLM\Software\Coho\CLI InstallFolder = $($installed.InstallFolder)"

Invoke-Msiexec '/x' (Join-Path $logs 'coho-uninstall.log')

if (Test-Path (Join-Path $folder 'coho.exe')) { throw "uninstalling left coho.exe in $folder" }
if (Test-OnPath) { throw "uninstalling left $folder on the machine PATH" }
Write-Host 'Installed, ran, and uninstalled cleanly.'
