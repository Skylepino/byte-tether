<#
Runs at Windows login. Fires the digest catch-up if the last one is stale.
Silent no-op when the last digest is < 20h old, so it's safe to run every login.
#>

$ErrorActionPreference = 'SilentlyContinue'
$OutputDir = 'C:\code\Personal\Byte-Tether\output'
$AutomationId = 'a2ec657e-9fb7-4d61-a4a1-a88341cac94d'
$StaleAfterHours = 20

if (-not (Test-Path $OutputDir)) { exit 0 }

$indexPath = Join-Path $OutputDir 'INDEX.md'
if (Test-Path $indexPath) {
    # Newest date = first YYYY-MM-DD date heading or table row found in the ledger.
    $match = Select-String -Path $indexPath -Pattern '(\d{4}-\d{2}-\d{2})' |
        ForEach-Object { $_.Matches[0].Groups[1].Value } |
        Select-Object -First 1
} else {
    $match = $null
}

if ($match) {
    $lastRun = [datetime]::ParseExact($match, 'yyyy-MM-dd', $null)
    $ageHours = ((Get-Date) - $lastRun).TotalHours
    if ($ageHours -lt $StaleAfterHours) { exit 0 }
}

orca automations run $AutomationId --json | Out-Null

