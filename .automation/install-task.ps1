$ErrorActionPreference = 'Stop'

$scriptRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptRoot
$projectName = Split-Path -Leaf $projectRoot
$safeProjectName = ($projectName -replace '[\\/:*?"<>|]', '_')
$taskName = "AutoSync_$safeProjectName"
$autosyncScript = Join-Path $scriptRoot 'autosync.ps1'

if (-not (Test-Path -LiteralPath $autosyncScript)) {
    throw "Script not found: $autosyncScript"
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$autosyncScript`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 3650)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description "Git auto sync every 10 minutes for $projectName" -Force | Out-Null

Write-Host "Scheduled task created: $taskName"
Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State, Description
