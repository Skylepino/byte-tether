<#
.SYNOPSIS
    Create (or repair) the digest automation from config/digest.json.
.DESCRIPTION
    Reads every knob out of config/digest.json - schedule, timezone, provider,
    repo path - and creates the Orca automation from it. The automation prompt is
    a fixed 4-line instruction to read AGENTS.md and follow the skill; all real
    customization stays in the config, so you never edit a prompt string.

    Safe to re-run: if an automation of the same name is already pointed at this
    repo it is updated in place, not duplicated. Pass -Recreate to force a new one.

    Run this after cloning on a new machine, or after changing the schedule.
.EXAMPLE
    powershell -File tools\install-automation.ps1
    powershell -File tools\install-automation.ps1 -Recreate
    powershell -File tools\install-automation.ps1 -Disabled   # install paused
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

# Patch automation.id in place rather than re-serializing, so the hand-written
# "$comment" keys and formatting in digest.json survive untouched. The current
# value may be "", null, or a stale uuid - match all three.
function _WriteAutomationId($id) {
    $text = Get-Content $configPath -Raw
    $patched = $text -replace '("id"\s*:\s*)("[^"]*"|null)', ('$1"' + $id + '"')
    if ($patched -eq $text) {
        Write-Error 'Could not locate automation.id in config/digest.json. Nothing was written.'
        exit 1
    }
    Set-Content -Path $configPath -Value $patched -Encoding utf8
    Write-Output "Wrote automation.id into config/digest.json"
}

# Reuse an existing automation when one is already pointed at this repo, so
# re-running this after a config change updates it instead of creating a second
# one that fires at the same hour every day. -Recreate opts out.
if (-not $Recreate) {
    # Orca reports paths with forward slashes ("C:/code/..."), $repoRoot has
    # backslashes. Compare normalized, trailing-slash-insensitive.
    function _samePath($a, $b) {
        if (-not $a -or -not $b) { return $false }
        $n = { param($p) (($p -replace '\\', '/').TrimEnd('/')).ToLowerInvariant() }
        (& $n $a) -eq (& $n $b)
    }
    $existing = orca automations list --json | ConvertFrom-Json |
        Select-Object -ExpandProperty result | Select-Object -ExpandProperty automations |
        Where-Object { $_.name -eq $Name -and (_samePath $_.runContext.path $repoRoot) } |
        Select-Object -First 1

    if ($existing) {
        Write-Output "Updating existing automation '$Name' ($($existing.id))"
        Write-Output "  provider : $($cfg.agent.provider)"
        Write-Output "  schedule : $($cfg.schedule.rrule) ($($cfg.schedule.timezone))"

        $editArgs = @(
            'automations', 'edit', $existing.id,
            '--prompt', $prompt,
            '--provider', $cfg.agent.provider,
            '--repo', "path:$repoRoot",
            '--trigger', $cfg.schedule.rrule,
            '--timezone', $cfg.schedule.timezone,
            '--missed-run-grace-minutes', $cfg.schedule.missedRunGraceMinutes,
            '--json'
        )
        $editArgs += $(if ($Disabled) { '--disabled' } else { '--enabled' })

        $editResult = & orca @editArgs | ConvertFrom-Json
        if (-not $editResult.ok) {
            $editResult | ConvertTo-Json -Depth 5
            exit 1
        }

        $auto = $editResult.result.automation
        Write-Output ''
        Write-Output "Updated: $($auto.id)"
        _WriteAutomationId $auto.id
        Write-Output 'Verify:  orca automations show ' + $auto.id + ' --json'
        exit 0
    }
}

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

$auto = $result.result.automation
if (-not $auto) {
    Write-Error 'Orca did not return an automation object. Nothing was written to config.'
    $result | ConvertTo-Json -Depth 5
    exit 1
}

Write-Output ''
Write-Output "Created: $($auto.id)"

# Write the id back so tools\run-digest.ps1 and check-staleness.ps1 can find it.
_WriteAutomationId $auto.id

Write-Output ''
Write-Output 'Verify:  orca automations show ' + $auto.id + ' --json'