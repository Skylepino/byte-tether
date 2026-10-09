<#
.SYNOPSIS
    Print every item inside the dedup window. These are BANNED.
.DESCRIPTION
    Reads the ledger at config/digest.json -> digest.indexFile (ledger/INDEX.md) and
    prints the Date | Category | Item | URL rows that fall inside
    digest.dedupWindowDays, newest first.
    Run this BEFORE selecting anything. Selecting first is how digests repeat.
.EXAMPLE
    powershell -File tools/banned-items.ps1
#>

[CmdletBinding()]
param(
    [int] $WindowDays = 0
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot 'config\digest.json'
$indexPath  = Join-Path $repoRoot 'ledger\INDEX.md'

if (-not (Test-Path $configPath)) {
    Write-Error "Missing config: $configPath"
    exit 1
}

# The ledger location is config-driven, not hardcoded, so moving it stays a one-line change.
$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
if ($cfg.digest.indexFile) {
    $indexPath = Join-Path $repoRoot $cfg.digest.indexFile
}
if ($WindowDays -le 0) {
    $WindowDays = [int] $cfg.digest.dedupWindowDays
    if ($WindowDays -le 0) { $WindowDays = 90 }
}

if (-not (Test-Path $indexPath)) {
    Write-Output "No ledger yet at $indexPath - nothing is banned. First run."
    exit 0
}

# Last day of the window is today; anything older than that falls out.
$cutoff = (Get-Date).Date.AddDays(-($WindowDays - 1))
$rows = Select-String -Path $indexPath -Pattern '^\|\s*(\d{4}-\d{2}-\d{2})\s*\|' |
    ForEach-Object {
        $cells = ($_.Line -split '\|') | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
        if ($cells.Count -ge 4) {
            [pscustomobject]@{
                Date     = [datetime]::ParseExact($cells[0], 'yyyy-MM-dd', $null)
                Category = $cells[1]
                Item     = $cells[2]
                Url      = $cells[3]
            }
        }
    } |
    Where-Object { $_.Date -ge $cutoff } |
    Sort-Object Date -Descending

if (-not $rows) {
    Write-Output "Ledger has no rows inside the $WindowDays-day window."
    exit 0
}

Write-Output "BANNED - $WindowDays-day window starting $($cutoff.ToString('yyyy-MM-dd')) - $($rows.Count) item(s)"
Write-Output ''
foreach ($r in $rows) {
    Write-Output ("  {0}  {1,-14} {2}  {3}" -f $r.Date.ToString('yyyy-MM-dd'), $r.Category, $r.Item, $r.Url)
}