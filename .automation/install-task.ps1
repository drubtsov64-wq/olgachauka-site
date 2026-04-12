$ErrorActionPreference = 'Stop'

$taskName = 'AutoSync_olgachauka-site'
$vbsPath = Join-Path $PSScriptRoot 'autosync-hidden.vbs'

if (-not (Test-Path $vbsPath)) {
    throw "Script not found: $vbsPath"
}

$action = New-ScheduledTaskAction `
    -Execute 'wscript.exe' `
    -Argument "`"$vbsPath`""

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
