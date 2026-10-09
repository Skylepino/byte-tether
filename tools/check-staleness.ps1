<#
.SYNOPSIS
    Report how stale the digest is, and optionally fire a catch-up run.
.DESCRIPTION
    Reads the newest date in output/INDEX.md and compares it against
    config/digest.json -> schedule.catchupAfterHours.

    With -Force it triggers the automation regardless of age. Without it, the
    script is a safe no-op whenever the last digest is fresh enough - which is
    what makes it safe to wire into a login/launch hook.
.EXAMPLE
    powershell -File tools\check-staleness.ps1
    powershell -File tools\check-staleness.ps1 -Force
#>

[CmdletBinding()]
param(
    [switch] $Force,
    [switch] $Json
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot 'config\digest.json'
$indexPath  = Join-Path $repoRoot 'output\INDEX.md'

$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
$staleAfterHours = [double] $cfg.schedule.catchupAfterHours
$automationId    = $cfg.automation.id

# Newest row = first date in the ledger, since rows are prepended newest-first.
$lastRun = $null
if (Test-Path $indexPath) {
    $match = Select-String -Path $indexPath -Pattern '^\|\s*(\d{4}-\d{2}-\d{2})\s*\|' |
        ForEach-Object { $_.Matches[0].Groups[1].Value } |
        Select-Object -First 1
    if ($match) { $lastRun = [datetime]::ParseExact($match, 'yyyy-MM-dd', $null) }
}

if ($lastRun) {
    $ageHours = ((Get-Date) - $lastRun).TotalHours
    $isStale  = $ageHours -ge $staleAfterHours
} else {
    $ageHours = $null
    $isStale  = $true   # never run = maximally stale
}

$shouldRun = ($Force -or $isStale) -and $automationId

if ($Json) {
    [pscustomobject]@{
        lastRun         = if ($lastRun) { $lastRun.ToString('yyyy-MM-dd') } else { $null }
        ageHours        = if ($null -ne $ageHours) { [math]::Round($ageHours, 1) } else { $null }
        staleAfterHours = $staleAfterHours
        isStale         = $isStale
        automationId    = $automationId
        wouldRun        = [bool]$shouldRun
    } | ConvertTo-Json
    exit $(if ($shouldRun) { 0 } else { 0 })
}

Write-Output ("last digest : {0}" -f $(if ($lastRun) { $lastRun.ToString('yyyy-MM-dd') } else { '<never>' }))
Write-Output ("age         : {0}" -f $(if ($null -ne $ageHours) { "$([math]::Round($ageHours,1))h" } else { 'n/a' }))
Write-Output ("stale after : {0}h" -f $staleAfterHours)
Write-Output ("automation  : {0}" -f $(if ($automationId) { $automationId } else { '<not set in config>' }))

if (-not $shouldRun) {
    Write-Output ''
    Write-Output 'Fresh - nothing to do.'
    exit 0
}

Write-Output ''
Write-Output 'Stale - firing digest run.'
orca automations run $automationId --json | Out-Null