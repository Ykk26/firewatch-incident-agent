param(
    [switch]$Mirror
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$WorkspaceRoot = Resolve-Path (Join-Path $ProjectRoot "..\..")
$Source = Resolve-Path (Join-Path $ProjectRoot "skill\firewatch-incident-agent")
$Target = Join-Path $WorkspaceRoot "skills\firewatch-incident-agent"

if (-not (Test-Path $Source)) {
    throw "Source skill does not exist: $Source"
}

$TargetParent = Split-Path -Parent $Target
if (-not (Test-Path $TargetParent)) {
    New-Item -ItemType Directory -Force -Path $TargetParent | Out-Null
}

if ($Mirror -and (Test-Path $Target)) {
    $resolvedTarget = Resolve-Path $Target
    $skillsRoot = Resolve-Path (Join-Path $WorkspaceRoot "skills")
    if (-not $resolvedTarget.Path.StartsWith($skillsRoot.Path)) {
        throw "Refusing to mirror outside skills root: $resolvedTarget"
    }
    Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null

$ExcludeDirectories = @("__pycache__", "outputs")
$ExcludeFilePatterns = @("*.pyc", "*.pyo", "*.tmp", "*.log")
$ExcludeRelativePatterns = @(
    "knowledge\observations.jsonl",
    "knowledge\incident_cases.jsonl",
    "knowledge\lessons_learned.jsonl",
    "knowledge\pending_review.jsonl",
    "knowledge\camera_profiles.json"
)

Get-ChildItem -LiteralPath $Source -Recurse -Force | ForEach-Object {
    $relative = $_.FullName.Substring($Source.Path.Length).TrimStart("\", "/")
    $normalizedRelative = $relative -replace "/", "\"

    if ($_.PSIsContainer -and ($ExcludeDirectories -contains $_.Name)) {
        return
    }
    foreach ($pattern in $ExcludeFilePatterns) {
        if (-not $_.PSIsContainer -and $_.Name -like $pattern) {
            return
        }
    }
    foreach ($pattern in $ExcludeRelativePatterns) {
        if ($normalizedRelative -eq $pattern) {
            return
        }
    }

    $destination = Join-Path $Target $relative

    if ($_.PSIsContainer) {
        New-Item -ItemType Directory -Force -Path $destination | Out-Null
    } else {
        $destinationParent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
    }
}

Write-Host "Synced FireWatch skill"
Write-Host "  Source: $Source"
Write-Host "  Target: $Target"
