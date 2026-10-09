<#
Runs at Windows login. Fires the digest catch-up if the last one is stale.
Silent no-op when the last digest is < 20h old, so it's safe to run every login.

Paths and thresholds come from config/digest.json rather than being hardcoded,
so this file survives the repo moving and the automation id changing.
tools/check-staleness.ps1 is the CLI equivalent and does the same thing.
#>

$ErrorActionPreference = 'SilentlyContinue'

$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot 'config\digest.json'
if (-not (Test-Path $configPath)) { exit 0 }

$cfg = Get-Content $configPath -Raw | ConvertFrom-Json

$AutomationId    = $cfg.automation.id
$StaleAfterHours = [double] $cfg.schedule.catchupAfterHours

# Ledger moved to /ledger/ because /output/ is gitignored and each run checks out
# a fresh worktree. Fall back to the old location just in case.
$ledger = if ($cfg.digest.indexFile) { $cfg.digest.indexFile } else { 'ledger/INDEX.md' }
$indexPath = Join-Path $repoRoot $ledger
if (-not (Test-Path $indexPath)) {
    $indexPath = Join-Path $repoRoot 'ledger\INDEX.md'
}
if (-not $AutomationId) { exit 0 }

if (Test-Path $indexPath) {
    # Newest date = first YYYY-MM-DD table row found in the ledger (rows are newest-first).
    $match = Select-String -Path $indexPath -Pattern '^\|\s*(\d{4}-\d{2}-\d{2})\s*\|' |
        ForEach-Object { $_.Matches[0].Groups[1].Value } |
        Select-Object -First 1
} else {
    $match = $null   # no ledger = never run = maximally stale
}

if ($match) {
    $lastRun = [datetime]::ParseExact($match, 'yyyy-MM-dd', $null)
    $ageHours = ((Get-Date) - $lastRun).TotalHours
    if ($ageHours -lt $StaleAfterHours) { exit 0 }
}

orca automations run $AutomationId --json | Out-Null