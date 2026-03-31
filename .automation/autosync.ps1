$ErrorActionPreference = 'Stop'

$scriptRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptRoot
$logFile = Join-Path $scriptRoot 'autosync.log'

function Write-Log {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [ValidateSet('INFO', 'ERROR')]
        [string]$Level = 'INFO'
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "$timestamp [$Level] $Message"
    Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
}

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args,
        [switch]$AllowFailure
    )

    $commandText = "git $($Args -join ' ')"
    Write-Log -Message $commandText

    $output = & git @Args 2>&1
    $exitCode = $LASTEXITCODE

    if ($output) {
        foreach ($line in $output) {
            Write-Log -Message "$line"
        }
    }

    if (-not $AllowFailure -and $exitCode -ne 0) {
        throw "$commandText failed with exit code $exitCode"
    }

    return [PSCustomObject]@{
        ExitCode = $exitCode
        Output   = $output
    }
}

try {
    Set-Location -LiteralPath $projectRoot
    Write-Log -Message "Autosync started in '$projectRoot'."

    $statusOutput = & git status --porcelain 2>&1
    $statusExitCode = $LASTEXITCODE

    if ($statusExitCode -ne 0) {
        foreach ($line in $statusOutput) {
            Write-Log -Message "$line" -Level 'ERROR'
        }
        throw "Unable to read git status (exit code: $statusExitCode)."
    }

    $hasChanges = -not [string]::IsNullOrWhiteSpace(($statusOutput | Out-String))

    if (-not $hasChanges) {
        Write-Log -Message 'No local changes detected. Running pull --rebase only.'

        $pullResult = Invoke-Git -Args @('pull', '--rebase') -AllowFailure
        if ($pullResult.ExitCode -ne 0) {
            $pullText = ($pullResult.Output | Out-String)
            if ($pullText -match 'CONFLICT') {
                Write-Log -Message 'Rebase conflict detected during pull. No local files were auto-modified by this script.' -Level 'ERROR'
            }
            throw 'git pull --rebase failed.'
        }

        Write-Log -Message 'Pull with rebase completed. Nothing to commit.'
        exit 0
    }

    Write-Log -Message 'Local changes detected. Staging all changes.'
    Invoke-Git -Args @('add', '.')

    $postAddStatus = & git status --porcelain 2>&1
    $postAddExitCode = $LASTEXITCODE
    if ($postAddExitCode -ne 0) {
        foreach ($line in $postAddStatus) {
            Write-Log -Message "$line" -Level 'ERROR'
        }
        throw "Unable to read git status after staging (exit code: $postAddExitCode)."
    }

    if ([string]::IsNullOrWhiteSpace(($postAddStatus | Out-String))) {
        Write-Log -Message 'No committable changes found after git add. Running pull --rebase only.'
        $pullOnlyResult = Invoke-Git -Args @('pull', '--rebase') -AllowFailure
        if ($pullOnlyResult.ExitCode -ne 0) {
            throw 'git pull --rebase failed after empty staging.'
        }
        Write-Log -Message 'Pull with rebase completed after empty staging.'
        exit 0
    }

    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $commitMessage = "auto-sync: $stamp"

    $commitResult = Invoke-Git -Args @('commit', '-m', $commitMessage) -AllowFailure
    if ($commitResult.ExitCode -ne 0) {
        $commitText = ($commitResult.Output | Out-String)
        if ($commitText -match 'nothing to commit') {
            Write-Log -Message 'Commit skipped: nothing to commit.'
        }
        else {
            throw 'git commit failed.'
        }
    }
    else {
        Write-Log -Message "Commit created: $commitMessage"
    }

    $rebaseResult = Invoke-Git -Args @('pull', '--rebase') -AllowFailure
    if ($rebaseResult.ExitCode -ne 0) {
        $rebaseText = ($rebaseResult.Output | Out-String)

        if ($rebaseText -match 'CONFLICT') {
            Write-Log -Message 'Rebase conflict detected. Attempting to abort rebase to keep repository consistent.' -Level 'ERROR'
            $abortResult = Invoke-Git -Args @('rebase', '--abort') -AllowFailure
            if ($abortResult.ExitCode -eq 0) {
                Write-Log -Message 'Rebase aborted successfully. Manual conflict resolution is required.' -Level 'ERROR'
            }
            else {
                Write-Log -Message 'Failed to abort rebase automatically. Manual intervention is required.' -Level 'ERROR'
            }
        }

        throw 'git pull --rebase failed.'
    }

    $pushResult = Invoke-Git -Args @('push') -AllowFailure
    if ($pushResult.ExitCode -ne 0) {
        throw 'git push failed.'
    }

    Write-Log -Message 'Autosync completed successfully.'
    exit 0
}
catch {
    Write-Log -Message $_.Exception.Message -Level 'ERROR'
    Write-Log -Message 'Autosync finished with errors.' -Level 'ERROR'
    exit 1
}
