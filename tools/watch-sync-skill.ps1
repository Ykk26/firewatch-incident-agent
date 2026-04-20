$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Source = Resolve-Path (Join-Path $ProjectRoot "skill\firewatch-incident-agent")
$SyncScript = Join-Path $PSScriptRoot "sync-skill.ps1"

& $SyncScript

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $Source.Path
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true
$watcher.NotifyFilter = [System.IO.NotifyFilters]'FileName, DirectoryName, LastWrite, Size'

$lastRun = Get-Date "2000-01-01"
$action = {
    $now = Get-Date
    if (($now - $script:lastRun).TotalMilliseconds -lt 500) {
        return
    }
    $script:lastRun = $now
    Start-Sleep -Milliseconds 250
    & $using:SyncScript
}

Register-ObjectEvent $watcher Changed -Action $action | Out-Null
Register-ObjectEvent $watcher Created -Action $action | Out-Null
Register-ObjectEvent $watcher Deleted -Action $action | Out-Null
Register-ObjectEvent $watcher Renamed -Action $action | Out-Null

Write-Host "Watching FireWatch skill source for changes."
Write-Host "Source: $Source"
Write-Host "Press Ctrl+C to stop."

while ($true) {
    Start-Sleep -Seconds 1
}
