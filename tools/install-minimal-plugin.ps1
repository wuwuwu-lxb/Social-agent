param(
    [string]$AstrBotRoot = (Join-Path $env:USERPROFILE '.astrbot')
)
$ErrorActionPreference = 'Stop'
$taskProject = Split-Path $PSScriptRoot -Parent
$taskName = 'astrbot_plugin_social_agent'
$taskSource = Join-Path $taskProject $taskName
$taskDestination = Join-Path $AstrBotRoot "data/plugins/$taskName"
$taskFiles = @(
    'main.py', 'metadata.yaml', '_conf_schema.json', 'README.md',
    'social_agent/__init__.py', 'social_agent/service.py',
    'node/package.json', 'node/pnpm-lock.yaml', 'node/executor.mjs'
)
$taskNodeCommand = Get-Command node -CommandType Application -ErrorAction SilentlyContinue
$taskNode = if ($taskNodeCommand) { $taskNodeCommand.Source } else {
    Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
}
$taskPnpm = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pnpm/bin/pnpm.mjs'
if (-not (Test-Path -LiteralPath $taskNode) -or -not (Test-Path -LiteralPath $taskPnpm)) {
    throw 'Node or pnpm runtime not found. Install the package dependencies manually.'
}
foreach ($taskFile in $taskFiles) {
    $taskTarget = Join-Path $taskDestination $taskFile
    New-Item -ItemType Directory -Path (Split-Path $taskTarget -Parent) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $taskSource $taskFile) -Destination $taskTarget -Force
}
Push-Location (Join-Path $taskDestination 'node')
try {
    & $taskNode $taskPnpm install --offline --frozen-lockfile --ignore-scripts --no-optional --store-dir (Join-Path $taskProject 'runtime/pnpm-store')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
} finally {
    Pop-Location
}
$taskConfig = Join-Path $AstrBotRoot "data/config/${taskName}_config.json"
if (-not (Test-Path -LiteralPath $taskConfig)) {
    New-Item -ItemType Directory -Path (Split-Path $taskConfig -Parent) -Force | Out-Null
    $taskSettings = [ordered]@{
        node_path = $taskNode
        browser_profile = (Join-Path $taskProject 'runtime/weibo-browser-profile')
        allowed_user_ids = @()
    }
    [IO.File]::WriteAllText($taskConfig, ($taskSettings | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
}
$taskPackages = Join-Path $taskProject 'runtime/packages'
New-Item -ItemType Directory -Path $taskPackages -Force | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$taskZipPath = Join-Path $taskPackages "$taskName-v0.1.1.zip"
$taskZipStream = [IO.File]::Open($taskZipPath, [IO.FileMode]::Create)
$taskArchive = [IO.Compression.ZipArchive]::new($taskZipStream, [IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($taskFile in $taskFiles) {
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $taskArchive, (Join-Path $taskSource $taskFile), "$taskName/$taskFile"
        ) | Out-Null
    }
} finally {
    $taskArchive.Dispose()
    $taskZipStream.Dispose()
}
Write-Output "Installed to $taskDestination"
Write-Output "Source package: $taskZipPath (install Node dependencies separately on another computer)."
Write-Output 'Open or reload AstrBot to load the plugin. Existing plugin configuration was preserved.'
