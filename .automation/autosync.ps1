$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$logPath = Join-Path $scriptRoot 'autosync.log'

function Write-Log {
    param(
        [string]$Message
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -Path $logPath -Value "[$timestamp] $Message" -Encoding UTF8
}

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [switch]$ReturnOutput
    )

    if ($ReturnOutput) {
        $output = & git -C $repoRoot @Arguments 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "git $($Arguments -join ' ') failed: $($output -join [Environment]::NewLine)"
        }
        return $output
    }

    & git -C $repoRoot @Arguments 2>&1 | ForEach-Object { Write-Log "git> $_" }
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed"
    }
}

try {
    Write-Log 'Autosync started.'

    $status = Invoke-Git -Arguments @('status', '--porcelain') -ReturnOutput

    if ([string]::IsNullOrWhiteSpace(($status -join ''))) {
        Write-Log 'No local changes detected. Running pull --rebase.'
        Invoke-Git -Arguments @('pull', '--rebase')
        Write-Log 'Pull --rebase completed.'
    }
    else {
        Write-Log 'Local changes detected. Running add/commit/pull/push sequence.'
        Invoke-Git -Arguments @('add', '.')

        $commitMessage = 'auto-sync: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        Invoke-Git -Arguments @('commit', '-m', $commitMessage)

        Invoke-Git -Arguments @('pull', '--rebase')
        Invoke-Git -Arguments @('push')
        Write-Log 'Add/commit/pull/push completed.'
    }

    Write-Log 'Autosync finished successfully.'
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    exit 1
}
