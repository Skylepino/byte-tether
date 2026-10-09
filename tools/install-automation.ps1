<#
.SYNOPSIS
    Create (or repair) the digest automation from config/digest.json.
.DESCRIPTION
    Reads every knob out of config/digest.json - schedule, timezone, provider,
    repo path - and creates the Orca automation from it. The automation prompt is
    a fixed 4-line instruction to read AGENTS.md and follow the skill; all real
    customization stays in the config, so you never edit a prompt string.

    Run this after cloning on a new machine, or after changing the schedule.
.EXAMPLE
    powershell -File tools\install-automation.ps1
    powershell -File tools\install-automation.ps1 -Name "my-digest"
#>

[CmdletBinding()]
param(
    [string] $Name,
    [switch] $Disabled,
    [switch] $Recreate
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot 'config\digest.json'

$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
if (-not $Name) { $Name = $cfg.automation.name }

# The prompt stays stable on purpose. Everything tunable is in the config.
$prompt = @(
    'Read AGENTS.md in this repo and follow it exactly.',
    'Then load the daily-digest skill and run the procedure for the real current date.',
    'config/digest.json is authoritative - it decides categories, counts, sources and the dedup window.',
    'Never list an item you did not actually fetch from a live source.'
) -join ' '

Write-Output "Creating automation '$Name'"
Write-Output "  provider : $($cfg.agent.provider)"
Write-Output "  schedule : $($cfg.schedule.rrule) ($($cfg.schedule.timezone))"
Write-Output "  repo     : $repoRoot"

$args = @(
    'automations', 'create',
    '--name', $Name,
    '--prompt', $prompt,
    '--provider', $cfg.agent.provider,
    '--repo', "path:$repoRoot",
    '--trigger', $cfg.schedule.rrule,
    '--timezone', $cfg.schedule.timezone,
    '--missed-run-grace-minutes', $cfg.schedule.missedRunGraceMinutes,
    '--json'
)
if ($Disabled) { $args += '--disabled' }

$result = & orca @args | ConvertFrom-Json

if (-not $result.ok) {
    $result | ConvertTo-Json -Depth 5
    exit 1
}

$auto = $result.result.automations | Select-Object -Last 1
Write-Output ''
Write-Output "Created: $($auto.id)"

# Write the id back so tools\run-digest.ps1 and check-staleness.ps1 can find it.
$cfg.automation.id = $auto.id
$cfg | ConvertTo-Json -Depth 12 | Set-Content $configPath -Encoding utf8

Write-Output "Wrote automation.id into config/digest.json"
Write-Output ''
Write-Output 'Verify:  orca automations show ' + $auto.id + ' --json'