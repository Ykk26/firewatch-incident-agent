param(
    [string]$RequestPath = "examples\local\patrol_live.json",
    [switch]$PlanOnly
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ResolvedRequest = Resolve-Path (Join-Path $ProjectRoot $RequestPath)
$Orchestrator = Join-Path $ProjectRoot "skill\firewatch-incident-agent\scripts\orchestrator.py"
$Planner = Join-Path $ProjectRoot "skill\firewatch-incident-agent\scripts\predict_planner.py"

if ($PlanOnly) {
    python $Planner $ResolvedRequest
} else {
    python $Orchestrator $ResolvedRequest
}
