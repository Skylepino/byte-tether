<#
.SYNOPSIS
    Fire the digest automation now and report where it landed.
.EXAMPLE
    powershell -File tools\run-digest.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'lib.ps1')
$configPath = Resolve-Config -RepoRoot $repoRoot

$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
$automationId = $cfg.automation.id

if (-not $automationId) {
    Write-Error 'No automation.id in config/digest.json. Run tools\install-automation.ps1 first.'
    exit 1
}

Write-Output "Firing $automationId ..."
$run = orca automations run $automationId --json | ConvertFrom-Json

if (-not $run.ok) {
    $run | ConvertTo-Json -Depth 5
    exit 1
}

$run.result | ConvertTo-Json -Depth 5
Write-Output ''
Write-Output "History: orca automations runs --id $automationId --json"