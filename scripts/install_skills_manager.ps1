param(
    [string]$TargetPath = "",
    [switch]$Update
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/lite-milkfrog/skills-manager.git"
$WacRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Resolve-Target {
    if ($TargetPath) {
        return [IO.Path]::GetFullPath($TargetPath)
    }
    if ($env:SKILLS_MANAGER_HOME) {
        return [IO.Path]::GetFullPath($env:SKILLS_MANAGER_HOME)
    }

    $workspace = Split-Path $WacRoot -Parent
    $workspaceParent = Split-Path $workspace -Parent
    $candidates = @(
        (Join-Path $workspace "skills-manager"),
        (Join-Path $workspaceParent "skills-manager")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path (Join-Path $candidate ".git")) {
            return [IO.Path]::GetFullPath($candidate)
        }
    }
    return [IO.Path]::GetFullPath((Join-Path $workspace "skills-manager"))
}

function Invoke-Git([string[]]$Arguments, [string]$WorkingDirectory = "") {
    if ($WorkingDirectory) {
        Push-Location $WorkingDirectory
    }
    try {
        & git @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        if ($WorkingDirectory) {
            Pop-Location
        }
    }
}

$ResolvedTarget = Resolve-Target
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is required to install Skills Manager."
}

if (-not (Test-Path $ResolvedTarget)) {
    New-Item -ItemType Directory -Path (Split-Path $ResolvedTarget -Parent) -Force | Out-Null
    Invoke-Git @("clone", "--branch", "main", "--single-branch", $RepoUrl, $ResolvedTarget)
}
elseif (-not (Test-Path (Join-Path $ResolvedTarget ".git"))) {
    throw "Target exists but is not a Git repository: $ResolvedTarget"
}
elseif ($Update) {
    $dirty = (& git -C $ResolvedTarget status --porcelain)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect Skills Manager Git status."
    }
    if ($dirty) {
        throw "Skills Manager has local changes; refusing automatic update: $ResolvedTarget"
    }
    Invoke-Git @("-C", $ResolvedTarget, "fetch", "origin", "main", "--prune")
    Invoke-Git @("-C", $ResolvedTarget, "checkout", "main")
    Invoke-Git @("-C", $ResolvedTarget, "merge", "--ff-only", "origin/main")
}

$VenvPython = Join-Path $ResolvedTarget ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    & py -3 -m venv (Join-Path $ResolvedTarget ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Python >= 3.11 is required to create the Skills Manager environment."
    }
}

& $VenvPython -m pip install --disable-pip-version-check -q -e $ResolvedTarget
if ($LASTEXITCODE -ne 0) {
    throw "Skills Manager editable install failed."
}

& $VenvPython (Join-Path $ResolvedTarget "scripts\workflows\import-production.py") --archive-older
if ($LASTEXITCODE -ne 0) {
    throw "Skills Manager production Workflow import failed."
}

$Integration = Join-Path $ResolvedTarget "scripts\desktop\install-integration.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Integration
if ($LASTEXITCODE -ne 0) {
    throw "Skills Manager WAC integration failed."
}

[pscustomobject]@{
    ok = $true
    repository = $RepoUrl
    target = $ResolvedTarget
    component_id = "skills-control-plane"
    mcp = "http://127.0.0.1:8943/mcp"
    manager = "http://127.0.0.1:8955/"
    update_requested = [bool]$Update
    source_of_truth = "standalone-skills-manager-repository"
} | ConvertTo-Json -Depth 4
