$ErrorActionPreference = 'Stop'

$taskName = 'AutoSync_olgachauka-site'
$scriptPath = Join-Path $PSScriptRoot 'autosync.ps1'
$powershellPath = (Get-Command powershell.exe).Source

if (-not (Test-Path $scriptPath)) {
    throw "Script not found: $scriptPath"
}

$action = New-ScheduledTaskAction `
    -Execute $powershellPath `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 10) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description 'Auto git sync for portfolio project every 10 minutes.' `
    -Force | Out-Null

Write-Output "Task '$taskName' has been registered/updated."
