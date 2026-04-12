# =============================================================
#  autosync.ps1  —  safe git auto-sync for olgachauka-site
#  Runs every 10 min via Windows Task Scheduler.
#  Priority: reliability over "perfect git hygiene".
# =============================================================

$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot   = Split-Path -Parent $scriptRoot
$logPath    = Join-Path $scriptRoot 'autosync.log'
$lockPath   = Join-Path $scriptRoot 'autosync.lock'

# Max age of lock file before it is treated as stale (minutes)
$lockMaxAgeMinutes = 15

# Branches on which autosync is allowed to run
$allowedBranches = @('master', 'main')

# ── Logging ──────────────────────────────────────────────────

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = 'INFO'
    )
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$timestamp] [$Level] $Message"
    try {
        Add-Content -Path $logPath -Value $line -Encoding UTF8
    } catch {
        # If we can't write to log, there's nothing we can do safely.
    }
}

# ── Lock file ────────────────────────────────────────────────

function Acquire-Lock {
    if (Test-Path $lockPath) {
        $lockItem = Get-Item $lockPath
        $ageMinutes = ((Get-Date) - $lockItem.LastWriteTime).TotalMinutes
        if ($ageMinutes -lt $lockMaxAgeMinutes) {
            return $false   # Fresh lock — another instance is running
        }
        # Stale lock — remove and continue
        Write-Log "Stale lock file removed (age: $([int]$ageMinutes) min)." 'WARN'
        Remove-Item $lockPath -Force
    }
    # Write current PID into lock file
    [string]$PID | Set-Content -Path $lockPath -Encoding UTF8
    return $true
}

function Release-Lock {
    if (Test-Path $lockPath) {
        Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
    }
}

# ── Git helpers ───────────────────────────────────────────────

# Run a git command, log its output, return exit code.
# If -Fatal is set and git exits non-zero → throw.
function Invoke-Git {
    param(
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [switch]$Fatal
    )
    $output = & git -C $repoRoot @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    if ($output) {
        $output | ForEach-Object { Write-Log "  git> $_" }
    }
    if ($Fatal -and $exitCode -ne 0) {
        throw "git $($Arguments -join ' ') failed (exit $exitCode)"
    }
    return $exitCode
}

# Run a git command silently, return output lines (no logging).
function Get-GitOutput {
    param([Parameter(Mandatory=$true)][string[]]$Arguments)
    $result = & git -C $repoRoot @Arguments 2>&1
    # Expose exit code via script-scope variable
    $script:lastGitExit = $LASTEXITCODE
    return $result
}

# ── Safety checks ─────────────────────────────────────────────

function Test-RepoSafe {
    # 1. Is this folder a git repository?
    Get-GitOutput @('rev-parse', '--git-dir') | Out-Null
    if ($script:lastGitExit -ne 0) {
        Write-Log "ABORT: '$repoRoot' is not a git repository." 'ERROR'
        return $false
    }

    $gitDir = Join-Path $repoRoot '.git'

    # 2. Detached HEAD (no branch checked out)?
    Get-GitOutput @('symbolic-ref', '--quiet', 'HEAD') | Out-Null
    if ($script:lastGitExit -ne 0) {
        Write-Log 'ABORT: Detached HEAD. Check out a branch before autosync can run.' 'ERROR'
        return $false
    }

    # 3. Rebase in progress?
    if ((Test-Path (Join-Path $gitDir 'rebase-merge')) -or
        (Test-Path (Join-Path $gitDir 'rebase-apply'))) {
        Write-Log 'ABORT: Rebase in progress. Run "git rebase --abort" or finish the rebase first.' 'ERROR'
        return $false
    }

    # 4. Merge in progress?
    if (Test-Path (Join-Path $gitDir 'MERGE_HEAD')) {
        Write-Log 'ABORT: Merge in progress. Resolve the merge and commit, then autosync will resume.' 'ERROR'
        return $false
    }

    # 5. Cherry-pick in progress?
    if (Test-Path (Join-Path $gitDir 'CHERRY_PICK_HEAD')) {
        Write-Log 'ABORT: Cherry-pick in progress. Finish or abort it first.' 'ERROR'
        return $false
    }

    # 6. Unresolved conflict files?
    $conflicts = Get-GitOutput @('diff', '--name-only', '--diff-filter=U')
    if ($script:lastGitExit -eq 0 -and $conflicts) {
        Write-Log "ABORT: Unresolved conflict(s): $($conflicts -join ', '). Resolve them first." 'ERROR'
        return $false
    }

    return $true
}

# ── Main ──────────────────────────────────────────────────────

$lockAcquired = $false

try {
    # ── 1. Prevent parallel runs ──
    if (-not (Acquire-Lock)) {
        Write-Log 'SKIP: Another autosync instance is already running (lock exists).' 'WARN'
        exit 0
    }
    $lockAcquired = $true

    Write-Log '========== Autosync started =========='
    Write-Log "Repo : $repoRoot"

    # ── 2. Safety checks ──
    if (-not (Test-RepoSafe)) {
        exit 1
    }

    # ── 3. Verify branch ──
    $branch = (Get-GitOutput @('rev-parse', '--abbrev-ref', 'HEAD')) -join ''
    Write-Log "Branch: $branch"

    if ($allowedBranches -notcontains $branch) {
        Write-Log "SKIP: Branch '$branch' is not in the allowed list ($($allowedBranches -join ', ')). Autosync only runs on main branches." 'WARN'
        exit 0
    }

    # ── 4. Check for local changes ──
    $statusLines = Get-GitOutput @('status', '--porcelain')
    $hasChanges  = ($script:lastGitExit -eq 0) -and
                   (-not [string]::IsNullOrWhiteSpace(($statusLines -join '')))

    if ($hasChanges) {
        Write-Log "Changes detected. Running: add → commit → pull → push."

        # Stage all changes
        Write-Log 'Running: git add .'
        Invoke-Git -Arguments @('add', '.') -Fatal

        # Commit
        $commitMsg = 'auto-sync: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        Write-Log "Running: git commit -m `"$commitMsg`""
        Invoke-Git -Arguments @('commit', '-m', $commitMsg) -Fatal

        # Pull (fast-forward only — no rebase, no merge commits).
        # If remote has diverged this will fail safely without touching local history.
        Write-Log 'Running: git pull --ff-only'
        $pullExit = Invoke-Git -Arguments @('pull', '--ff-only')
        if ($pullExit -ne 0) {
            Write-Log 'WARNING: git pull --ff-only failed. Remote branch may have diverged.' 'WARN'
            Write-Log 'Continuing with push of local commit. If push is rejected, manual resolution is needed.' 'WARN'
        }

        # Push
        Write-Log 'Running: git push'
        Invoke-Git -Arguments @('push') -Fatal

        Write-Log 'Sync done: local changes committed and pushed.'
    }
    else {
        Write-Log 'No local changes. Running: pull --ff-only only.'

        Write-Log 'Running: git pull --ff-only'
        $pullExit = Invoke-Git -Arguments @('pull', '--ff-only')
        if ($pullExit -ne 0) {
            Write-Log 'WARNING: git pull --ff-only failed. Remote may have diverged. Skipping pull.' 'WARN'
            Write-Log 'Manual resolution required (e.g. git pull, then git push).' 'WARN'
        }
        else {
            Write-Log 'Pull completed. Repo is up to date.'
        }
    }

    Write-Log '========== Autosync finished OK =========='
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)" 'ERROR'
    exit 1
}
finally {
    if ($lockAcquired) {
        Release-Lock
    }
}