# Runs the council skill's commands the way a coordinator whose only command
# tool is PowerShell is told to: each bash command, unchanged, handed to bash as
#   & '<bash>' -c '<the bash command>'
# with single quotes only inside it (written twice), never a double quote.
#
# It answers: does that wrapper carry the time limit, the quoting, the fixed
# prompt and the snapshot commands intact, on Windows PowerShell 5.1 and on
# PowerShell 7? It launches no agent. It is a repository test, not part of the
# skill: the skill itself ships no script.
#
# On Windows the bash is Git Bash, found from where git is installed. Elsewhere
# it is the bash on PATH, which lets the quoting be checked on any system.
#
# Every check prints PASS or FAIL and the run continues. Exit status is the
# number of failed checks.

$ErrorActionPreference = 'Continue'
$script:fails = 0
function Pass([string]$name) { Write-Output "PASS  $name" }
function Fail([string]$name, [string]$why) { Write-Output "FAIL  $name -- $why"; $script:fails++ }
function Invoke-FixtureGit([string]$repo, [string[]]$arguments) {
    & git -C $repo @arguments
    if ($LASTEXITCODE -ne 0) { throw "fixture git $($arguments[0]) exited $LASTEXITCODE" }
}

$onWindows = ($env:OS -eq 'Windows_NT')
Write-Output ("system: " + $(if ($onWindows) { 'Windows' } else { 'not Windows' }))
Write-Output ("shell:  PowerShell " + $PSVersionTable.PSVersion.ToString())

# --- finding bash --------------------------------------------------------------

$bash = $null
if ($onWindows) {
    # Git Bash is bin\bash.exe under the Git installation folder that git.exe
    # sits in. C:\Windows\System32\bash.exe is WSL's launcher and is not it.
    $dir = Split-Path -Parent (Get-Command git -ErrorAction SilentlyContinue).Source
    while ($dir -and -not $bash) {
        $candidate = Join-Path $dir 'bin\bash.exe'
        if (Test-Path $candidate) { $bash = $candidate } else { $dir = Split-Path -Parent $dir }
    }
} else {
    $found = Get-Command bash -ErrorAction SilentlyContinue
    if ($found) { $bash = $found.Source }
}

if (-not $bash) {
    Fail 'bash found' 'no Git Bash beside git (Windows) or no bash on PATH'
    Write-Output "`n$script:fails check(s) failed"
    exit $script:fails
}
Pass "bash found: $bash"

# --- the wrapper leaves the bash command alone ---------------------------------

$out = & $bash -c 'echo $BASH_VERSION'
if ("$out" -match '^\d+\.') { Pass 'PowerShell expands nothing inside the wrapped command ($BASH_VERSION reached bash)' }
else { Fail 'PowerShell expands nothing inside the wrapped command' "got '$out'" }

if ($onWindows) {
    $out = & $bash -c 'uname -s'
    if ("$out" -match '^(MINGW|MSYS)') { Pass "the bash is Git Bash ($out)" }
    else { Fail 'the bash is Git Bash' "uname -s printed '$out'" }
}

foreach ($tool in 'timeout', 'env', 'git', 'jq') {
    $out = & $bash -c "command -v $tool"
    if ($LASTEXITCODE -eq 0 -and "$out") { Pass "tool on the wrapped bash's path: $tool" }
    else { Fail "tool on the wrapped bash's path: $tool" 'command -v printed nothing' }
}

& $bash -c 'command timeout -k 1 2 sleep 10'
if ($LASTEXITCODE -eq 124) { Pass 'time limit ends a wrapped turn with status 124' }
else { Fail 'time limit ends a wrapped turn with status 124' "got $LASTEXITCODE" }

$out = & $bash -c 'CLAUDECODE=1 command timeout -k 1 5 env -u CLAUDECODE bash -c ''echo ${CLAUDECODE:-unset}'''
if ("$out" -eq 'unset') { Pass 'env -u removes CLAUDECODE inside the wrapper' }
else { Fail 'env -u removes CLAUDECODE inside the wrapper' "member saw '$out'" }

# The fixed prompt, quoted with doubled single quotes, reaches a program as one
# argument, byte for byte.
$out = & $bash -c 'printf %s ''Read the brief at agent-to-agent/brief.md and follow it.'''
if ("$out" -ceq 'Read the brief at agent-to-agent/brief.md and follow it.') { Pass 'the fixed prompt reaches the program intact' }
else { Fail 'the fixed prompt reaches the program intact' "got '$out'" }

$out = & $bash -c 'printf %s%s ''Read the brief at agent-to-agent/brief.md and follow it.'' ''|second'''
if ("$out" -ceq 'Read the brief at agent-to-agent/brief.md and follow it.|second') { Pass 'the fixed prompt is one argument, not split at its spaces' }
else { Fail 'the fixed prompt is one argument, not split at its spaces' "got '$out'" }

# --- a repository whose path holds a space -------------------------------------

$work = Join-Path ([System.IO.Path]::GetTempPath()) ('council ps test ' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
try {
    $repo = Join-Path $work 'repo dir'
    $hooks = Join-Path $work 'empty hooks'
    New-Item -ItemType Directory -Path $repo, $hooks -ErrorAction Stop | Out-Null
    Invoke-FixtureGit $repo @('init', '-q')
    Invoke-FixtureGit $repo @('config', '--local', 'user.name', 'council test')
    Invoke-FixtureGit $repo @('config', '--local', 'user.email', 'council-test@example.invalid')
    # The disposable commits and worktrees need no operator keys or hooks.
    Invoke-FixtureGit $repo @('config', '--local', 'commit.gpgSign', 'false')
    Invoke-FixtureGit $repo @('config', '--local', 'core.hooksPath', $hooks)
    Set-Content -Path (Join-Path $repo 'tracked.txt') -Value 'one'
    Invoke-FixtureGit $repo @('add', 'tracked.txt')
    Invoke-FixtureGit $repo @('commit', '-q', '-m', 'base')
    Set-Content -Path (Join-Path $repo 'tracked.txt') -Value 'two'
    Set-Content -Path (Join-Path $repo 'new.txt') -Value 'new'

    # Inside the wrapper: forward slashes, and the path in single quotes.
    $r = $repo -replace '\\', '/'
    $rundir = "$r/agent-to-agent/2026-01-01-test"
    $exclude = git -C $repo rev-parse --git-path info/exclude
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent (Join-Path $repo $exclude)) | Out-Null
    Add-Content -Path (Join-Path $repo $exclude) -Value "agent-to-agent/`n.worktrees/"

    $out = & $bash -c "cd '$r' && git rev-parse --is-inside-work-tree"
    if ("$out" -eq 'true') { Pass 'a path with a space, in single quotes, reaches bash as one argument' }
    else { Fail 'a path with a space, in single quotes, reaches bash as one argument' "got '$out'" }

    # Start at the writable fixture. Under the Windows Codex sandbox,
    # mkdir -p with an absolute path walks inaccessible home ancestors.
    & $bash -c "cd '$r' && mkdir -p 'agent-to-agent/2026-01-01-test/round-1' 'agent-to-agent/2026-01-01-test/raw/round-1'"
    if ($LASTEXITCODE -ne 0) { throw "fixture run directory creation exited $LASTEXITCODE" }

    $before = (& $bash -c "cd '$r' && git rev-parse HEAD && git --no-optional-locks status --porcelain") -join "`n"

    # The four snapshot commands, one wrapped command each.
    & $bash -c "cd '$r' && GIT_INDEX_FILE='$rundir/snapshot.index' git read-tree HEAD"
    & $bash -c "cd '$r' && GIT_INDEX_FILE='$rundir/snapshot.index' git add -A"
    $tree = & $bash -c "cd '$r' && GIT_INDEX_FILE='$rundir/snapshot.index' git write-tree"
    if ($LASTEXITCODE -ne 0) { throw "fixture snapshot tree creation exited $LASTEXITCODE" }
    $snap = & $bash -c "cd '$r' && git commit-tree $tree -p HEAD -m 'council snapshot 2026-01-01-test round 1'"
    if ($LASTEXITCODE -ne 0) { throw "fixture snapshot commit exited $LASTEXITCODE" }

    $after = (& $bash -c "cd '$r' && git rev-parse HEAD && git --no-optional-locks status --porcelain") -join "`n"
    if ($before -ceq $after) { Pass 'wrapped snapshot leaves branch, index and working tree unchanged' }
    else { Fail 'wrapped snapshot leaves branch, index and working tree unchanged' 'state differs' }

    $files = & $bash -c "cd '$r' && git ls-tree -r --name-only $snap"
    if ($files -contains 'new.txt') { Pass 'wrapped snapshot includes the untracked file' }
    else { Fail 'wrapped snapshot includes the untracked file' "files: $($files -join ' ')" }
    if ($files | Where-Object { $_ -like 'agent-to-agent/*' }) { Fail 'wrapped snapshot leaves the run directory out' 'agent-to-agent/ is in the snapshot' }
    else { Pass 'wrapped snapshot leaves the run directory out' }

    $msg = & $bash -c "cd '$r' && git log -1 --format=%s $snap"
    if ("$msg" -ceq 'council snapshot 2026-01-01-test round 1') { Pass 'a quoted commit message with spaces arrives whole' }
    else { Fail 'a quoted commit message with spaces arrives whole' "got '$msg'" }

    # A member worktree, its brief copy, and a stand-in launch from inside it.
    $wt = "$r/.worktrees/council/2026-01-01-test/member-a"
    & $bash -c "cd '$r' && git worktree add -q --detach '$wt' $snap"
    if ($LASTEXITCODE -ne 0) { throw "fixture worktree creation exited $LASTEXITCODE" }
    & $bash -c "printf '%s\n' 'Reply with exactly: COUNCIL-OK' > '$rundir/brief.md'"
    & $bash -c "cd '$wt' && mkdir -p agent-to-agent"
    if ($LASTEXITCODE -ne 0) { throw "fixture member directory creation exited $LASTEXITCODE" }
    & $bash -c "command cp '$rundir/brief.md' '$wt/agent-to-agent/brief.md'"

    & $bash -c "cd '$wt' && command timeout -k 10 900 env -u CLAUDECODE cat agent-to-agent/brief.md < /dev/null > '$rundir/raw/round-1/member-a.txt'"
    $reply = & $bash -c "cat '$rundir/raw/round-1/member-a.txt'"
    if ($LASTEXITCODE -eq 0 -and "$reply" -ceq 'Reply with exactly: COUNCIL-OK') { Pass 'a wrapped launch line runs in the worktree and writes its output file' }
    else { Fail 'a wrapped launch line runs in the worktree and writes its output file' "got '$reply'" }

    # Closing.
    & $bash -c "command rm '$wt/agent-to-agent/brief.md'"
    & $bash -c "cd '$r' && git worktree remove '$wt'"
    $list = @(& $bash -c "cd '$r' && git worktree list")
    if ($list.Count -eq 1) { Pass 'wrapped closing removes the member worktree' }
    else { Fail 'wrapped closing removes the member worktree' "still listed: $($list.Count) worktrees" }

    # Windows Codex uses native Git and file commands around the wrapped launch.
    $head = Invoke-FixtureGit $repo @('rev-parse', 'HEAD')
    $branch = Invoke-FixtureGit $repo @('branch', '--show-current')
    $status = (Invoke-FixtureGit $repo @('--no-optional-locks', 'status', '--porcelain')) -join "`n"
    if (-not $branch -or -not $head) { throw 'native Git did not return the fixture branch and HEAD' }
    $member = "$r/.worktrees/council/2026-01-01-test/member-b"
    Invoke-FixtureGit $repo @('worktree', 'add', '-q', '--detach', $member, $head)
    New-Item -ItemType Directory -Path "$member/agent-to-agent" -ErrorAction Stop | Out-Null
    Copy-Item -LiteralPath "$rundir/brief.md" -Destination "$member/agent-to-agent/brief.md" -ErrorAction Stop
    & $bash -c "cd '$member' && command timeout -k 10 900 env -u CLAUDECODE cat agent-to-agent/brief.md < /dev/null > '$rundir/raw/round-1/member-b.txt'"
    if ($LASTEXITCODE -ne 0) { throw "native worktree stand-in launch exited $LASTEXITCODE" }
    $reply = Get-Content -LiteralPath "$rundir/raw/round-1/member-b.txt" -ErrorAction Stop
    if ($reply -cne 'Reply with exactly: COUNCIL-OK') { throw "native worktree reply was '$reply'" }
    if ((Invoke-FixtureGit $member @('rev-parse', 'HEAD')) -cne $head) { throw 'member used the wrong snapshot' }
    if (Invoke-FixtureGit $member @('status', '--porcelain')) { throw 'member worktree has changes' }
    Remove-Item -LiteralPath "$member/agent-to-agent/brief.md" -ErrorAction Stop
    Invoke-FixtureGit $repo @('worktree', 'remove', $member)
    if (@(Invoke-FixtureGit $repo @('worktree', 'list')).Count -ne 1) { throw 'native closing left a worktree registered' }
    $finalStatus = (Invoke-FixtureGit $repo @('--no-optional-locks', 'status', '--porcelain')) -join "`n"
    if ($finalStatus -cne $status) {
        throw 'native Council operations changed the operator checkout'
    }
    Pass 'native Git and file operations support worktree creation, wrapped launch, and cleanup'
}
catch {
    Fail 'fixture setup or execution' $_.Exception.Message
}
finally {
    Remove-Item -Recurse -Force -Path $work -ErrorAction SilentlyContinue
}

Write-Output "`n$script:fails check(s) failed"
exit $script:fails
