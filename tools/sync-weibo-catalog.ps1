param(
    [switch]$Offline
)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskSpecRoot = Join-Path $taskRoot 'specs/weibo'
$taskSnapshotPath = Join-Path $taskSpecRoot 'official-cli-catalog.json'
$taskMappingPath = Join-Path $taskSpecRoot 'browser-mapping.json'
$taskUtf8 = [System.Text.UTF8Encoding]::new($false)

if ($Offline) {
    $taskSnapshot = Get-Content -LiteralPath $taskSnapshotPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $taskRaw = & (Join-Path $PSScriptRoot 'weibo-cli/weibo.ps1') commands list --all --output json
    if ($LASTEXITCODE -ne 0) { throw 'Official CLI catalog query failed.' }
    $taskResponse = ($taskRaw -join "`n") | ConvertFrom-Json
    if (-not $taskResponse.commands -or $taskResponse.total -ne @($taskResponse.commands).Count) {
        throw 'Official catalog count is inconsistent.'
    }
    # Keep API definitions only; exclude account access, service state and pricing.
    $taskDefinitions = @($taskResponse.commands | ForEach-Object {
        [ordered]@{
            name = $_.name
            group = $_.group
            action = $_.action
            api_path = $_.api_path
            invocation_path = $_.invocation_path
            method = $_.method
            title = $_.title
            description = $_.description
            required_fields = @($_.required_fields)
            input_schema = $_.input_schema
            flags = @($_.flags)
            usage_notes = @($_.usage_notes)
            schema_version = $_.schema_version
        }
    })
    $taskSnapshot = [ordered]@{
        schema_version = 1
        captured_at = [DateTimeOffset]::UtcNow.ToString('o')
        cli_package = '@weibo-ai/weibo-cli'
        cli_version = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'weibo-cli/node_modules/@weibo-ai/weibo-cli/package.json') -Raw | ConvertFrom-Json).version
        source_command = 'commands list --all --output json'
        source_url = 'https://open.weibo.com/cli/quickstart'
        catalog_version = $taskResponse.catalog_version
        total = $taskDefinitions.Count
        commands = $taskDefinitions
    }
}

$taskMapping = Get-Content -LiteralPath $taskMappingPath -Raw -Encoding UTF8 | ConvertFrom-Json
$taskOfficialNames = @($taskSnapshot.commands | ForEach-Object { $_.name })
foreach ($taskMappedName in $taskMapping.operations.PSObject.Properties.Name) {
    if ($taskMappedName -notin $taskOfficialNames) { throw "Mapping references an unknown command: $taskMappedName" }
}
$taskToolNames = @()
$taskOperations = @($taskSnapshot.commands | Sort-Object { $_.name } | ForEach-Object {
    $taskName = $_.name
    $taskToolName = 'weibo_' + ($taskName -replace '[ /]', '_')
    if ($taskToolName -in $taskToolNames) { throw "Duplicate tool name: $taskToolName" }
    $taskToolNames += $taskToolName
    $taskCoverage = $taskMapping.operations.PSObject.Properties[$taskName]
    $taskRoute = if ($taskCoverage) { $taskCoverage.Value } else { $taskMapping.default }
    if ($taskRoute.coverage -notin @('partial', 'unsupported', 'equivalent')) {
        throw "Invalid coverage for $taskName"
    }
    [ordered]@{
        official_command = $taskName
        proposed_tool_name = $taskToolName
        official_method = $_.method
        title = $_.title
        required_fields = @($_.required_fields)
        official_flags = @($_.flags)
        registration = $(if ($taskRoute.registration) { $taskRoute.registration } else { 'planned' })
        browser_coverage = $taskRoute.coverage
        browser_tools = @($taskRoute.tools)
        verification = $taskRoute.verification
        notes = $taskRoute.notes
    }
})
$taskContract = [ordered]@{
    schema_version = 1
    catalog_version = $taskSnapshot.catalog_version
    scope = 'tool_contract_with_explicit_registration_state'
    parameter_policy = 'preserve_official_names_reject_unsupported_fields'
    id_policy = 'decimal_string_no_javascript_number'
    browser_adapter = "$($taskMapping.adapter_package)@$($taskMapping.adapter_version)"
    operations = $taskOperations
    browser_only = $taskMapping.browser_only
}

$taskLines = [System.Collections.Generic.List[string]]::new()
$taskLines.Add('# 官方 CLI 与插件工具全量对照')
$taskLines.Add('')
$taskLines.Add('此表由 `tools/sync-weibo-catalog.ps1` 生成；修改映射请编辑 `specs/weibo/browser-mapping.json`，再用 `-Offline` 重建。')
$taskLines.Add('')
$taskLines.Add("官方目录版本：``$($taskSnapshot.catalog_version)``。共 $($taskOperations.Count) 项，CLI $($taskSnapshot.cli_version)。")
$taskLines.Add('快照时间及完整参数、枚举、说明见 [官方目录 JSON](../specs/weibo/official-cli-catalog.json)；[插件契约 JSON](../specs/weibo/tool-contract.json)保留所有拟用工具名及官方参数。')
$taskLines.Add('')
$taskLines.Add('除 statuses update 已注册为仅草稿预演工具（enabled_preview_only）外，其余工具状态为 planned。下表的浏览器验证结果不等于正式插件已实现。partial 表示参数、权限、分页或返回语义不完全等价；unsupported 表示当前没有实现。GET/POST 为官方方法，不直接代表业务副作用。')
$taskLines.Add('')
$taskLines.Add('已验证：read_passed=真实读取；single_read_passed=只验证单条；dry_run_passed=只验证预演；not_tested=尚未验证。')
$taskLines.Add('')
$taskLines.Add('| 官方命令 / 用途 | 拟用模型工具名 | 方法 | 必填参数 | 浏览器对应 | 验证 | 差异与范围 |')
$taskLines.Add('| --- | --- | --- | --- | --- | --- | --- |')
foreach ($taskOperation in $taskOperations) {
    $taskRequired = if ($taskOperation.required_fields.Count) { $taskOperation.required_fields -join ', ' } else { '无' }
    $taskTools = if ($taskOperation.browser_tools.Count) { $taskOperation.browser_tools -join ', ' } else { '无' }
    $taskNote = $taskOperation.notes -replace '\|', '\|' -replace '[\r\n]+', ' '
    $taskTitle = $taskOperation.title -replace '\|', '\|' -replace '[\r\n]+', ' '
    $taskLines.Add("| ``$($taskOperation.official_command)`` / $taskTitle | ``$($taskOperation.proposed_tool_name)`` | $($taskOperation.official_method) | $taskRequired | $($taskOperation.browser_coverage): $taskTools | $($taskOperation.verification) | $taskNote |")
}
$taskLines.Add('')
$taskLines.Add('## 浏览器补充能力')
$taskLines.Add('')
$taskLines.Add('以下单独命名，避免冒充官方等价接口。')
$taskLines.Add('')
$taskLines.Add('| 适配器工具 | 用途 | 验证 |')
$taskLines.Add('| --- | --- | --- |')
foreach ($taskBrowserTool in $taskMapping.browser_only) {
    $taskLines.Add("| ``$($taskBrowserTool.name)`` | $($taskBrowserTool.purpose) | $($taskBrowserTool.verification) |")
}
$taskLines.Add('')
$taskLines.Add('契约、参数差异处理和开发顺序见 [正式插件设计](../docs/plugin-design.md)。诊断命令来源与复现见 [探测命令说明](weibo-probe.md)。')

if (-not $Offline) {
    [IO.File]::WriteAllText($taskSnapshotPath, ($taskSnapshot | ConvertTo-Json -Depth 40) + "`n", $taskUtf8)
}
[IO.File]::WriteAllText((Join-Path $taskSpecRoot 'tool-contract.json'), ($taskContract | ConvertTo-Json -Depth 40) + "`n", $taskUtf8)
[IO.File]::WriteAllText((Join-Path $taskRoot 'research/weibo-tool-matrix.md'), ($taskLines -join "`n") + "`n", $taskUtf8)
Write-Output "Validated and generated $($taskOperations.Count) unique tool contracts."
