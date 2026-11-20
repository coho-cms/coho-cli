<#
.SYNOPSIS
  Packages a frozen coho folder for Windows: coho-<version>-windows-x64.zip and .msi.

.DESCRIPTION
  -Frozen is the folder PyInstaller made, named coho and holding coho.exe. Sign coho.exe
  before running this, so the zip and the MSI both carry the signed one; sign the MSI after.

  The MSI is built with WiX v7 (coho.wxs beside this script). Running this accepts WiX's
  Open Source Maintenance Fee EULA (wix7) on Coho's behalf: see CONTRIBUTING.md.

.EXAMPLE
  pwsh packaging/windows/build.ps1 -Version 2026.2.4 -Frozen frozen/coho -OutDir out
#>
param(
    [Parameter(Mandatory)] [string] $Version,
    [Parameter(Mandatory)] [string] $Frozen,
    [Parameter(Mandatory)] [string] $OutDir
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

# Bump deliberately: a new WiX major brings a new EULA id to accept, and its own notes.
$WixVersion = '7.0.1'

$Frozen = (Resolve-Path $Frozen).Path
if ((Split-Path $Frozen -Leaf) -ne 'coho' -or -not (Test-Path (Join-Path $Frozen 'coho.exe'))) {
    throw "$Frozen is not a frozen coho folder: expected a folder named coho holding coho.exe"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path
$name = "coho-$Version-windows-x64"

# The version, product code and upgrade code, from the one place that defines them.
$identity = @{}
python (Join-Path $PSScriptRoot 'msi_version.py') $Version | ForEach-Object {
    $key, $value = $_ -split '=', 2
    $identity[$key] = $value
}
Write-Host "coho-cli $Version is ProductVersion $($identity.product_version), ProductCode $($identity.product_code)"

# The zip: the folder itself at the top, as coho\coho.exe.
$zip = Join-Path $OutDir "$name.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
7z a -tzip $zip $Frozen | Out-Null

# WiX, in a folder of its own rather than on the global tool path.
$tools = Join-Path $env:RUNNER_TEMP 'wix-tools'
if (-not $env:RUNNER_TEMP) { $tools = Join-Path ([IO.Path]::GetTempPath()) 'coho-wix-tools' }
$wix = Join-Path $tools 'wix.exe'
if (-not (Test-Path $wix)) {
    dotnet tool install wix --version $WixVersion --tool-path $tools
}
& $wix --version
# WiX v7 refuses to run (WIX7015) until its OSMF EULA is accepted for this user.
& $wix eula accept wix7

$msi = Join-Path $OutDir "$name.msi"
& $wix build (Join-Path $PSScriptRoot 'coho.wxs') `
    -arch x64 `
    -d "BinDir=$Frozen" `
    -d "Version=$Version" `
    -d "ProductVersion=$($identity.product_version)" `
    -d "ProductCode=$($identity.product_code)" `
    -d "UpgradeCode=$($identity.upgrade_code)" `
    -out $msi

# Windows Installer's own consistency checks (ICE). Warnings print; errors fail the build.
& $wix msi validate $msi

Get-ChildItem $OutDir | Format-Table Name, Length
