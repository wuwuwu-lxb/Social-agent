param(
    [ValidateSet('dom', 'bridge', 'login')]
    [string]$Mode = 'dom'
)

$taskProjectRoot = Split-Path $PSScriptRoot -Parent
$taskBranch = if ($Mode -eq 'bridge') { 'webmcp' } else { 'playwright' }
$taskScript = Join-Path $taskProjectRoot "runtime/experiments/$taskBranch/experiments/$taskBranch/probe.mjs"
$taskNode = Get-Command node -CommandType Application -ErrorAction SilentlyContinue
$taskNodePath = if ($taskNode) { $taskNode.Source } else {
    Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
}
if (-not (Test-Path -LiteralPath $taskNodePath) -or -not (Test-Path -LiteralPath $taskScript)) {
    Write-Error 'Node or experiment checkout is missing.'
    exit 1
}
if ($Mode -eq 'login') {
    & $taskNodePath $taskScript --login
} else {
    & $taskNodePath $taskScript
}
exit $LASTEXITCODE
