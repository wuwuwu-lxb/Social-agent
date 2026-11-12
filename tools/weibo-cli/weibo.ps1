$taskCliEntry = Join-Path $PSScriptRoot 'node_modules/@weibo-ai/weibo-cli/dist/index.js'
if (-not (Test-Path -LiteralPath $taskCliEntry)) {
    Write-Error 'Weibo CLI is missing. Install dependencies in tools/weibo-cli first.'
    exit 1
}

$taskNodeCommand = Get-Command node -CommandType Application -ErrorAction SilentlyContinue
$taskNodeCandidates = @()
if ($taskNodeCommand) {
    $taskNodeCandidates += $taskNodeCommand.Source
}

# Desktop terminals may not inherit Codex's bundled runtime PATH.
if ($env:ProgramFiles) {
    $taskNodeCandidates += Join-Path $env:ProgramFiles 'nodejs/node.exe'
}
if ($env:LOCALAPPDATA) {
    $taskNodeCandidates += Join-Path $env:LOCALAPPDATA 'Programs/nodejs/node.exe'
}
if ($env:USERPROFILE) {
    $taskNodeCandidates += Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
}

$taskNodePath = $null
foreach ($taskNodeCandidate in ($taskNodeCandidates | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $taskNodeCandidate -PathType Leaf)) {
        continue
    }
    try {
        $taskNodeVersion = & $taskNodeCandidate --version 2>$null
        if ($LASTEXITCODE -eq 0 -and "$taskNodeVersion" -match '^v(\d+)\.' -and [int]$Matches[1] -ge 18) {
            $taskNodePath = $taskNodeCandidate
            break
        }
    } catch {
        continue
    }
}

if (-not $taskNodePath) {
    Write-Error 'Node.js 18 or newer was not found in PATH or known installation locations.'
    exit 1
}

& $taskNodePath (Join-Path $PSScriptRoot 'entry.mjs') @args
exit $LASTEXITCODE
