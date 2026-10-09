<#
Shared helper: which config file is authoritative.

Precedence: config/digest.local.json (gitignored, yours) > config/digest.json
(the committed template). That is what lets the repo ship a neutral template
while your real setup - machine paths, automation id, your stack - stays private.
#>

function Resolve-Config {
    <#
    .SYNOPSIS
        Absolute path to the config this machine should use.
    #>
    param([string] $RepoRoot)

    $local = Join-Path $RepoRoot 'config\digest.local.json'
    if (Test-Path $local) { return $local }
    return (Join-Path $RepoRoot 'config\digest.json')
}

function Get-DigestConfig {
    <#
    .SYNOPSIS
        The parsed config, from whichever file Resolve-Config picks.
    .OUTPUTS
        PSCustomObject
    #>
    param([string] $RepoRoot)

    $path = Resolve-Config -RepoRoot $RepoRoot
    if (-not (Test-Path $path)) {
        throw "No config at $path. Copy config\digest.example.json to config\digest.local.json."
    }
    return (Get-Content $path -Raw | ConvertFrom-Json)
}