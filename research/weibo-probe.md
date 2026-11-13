# weibo_probe bridge 的来源、执行与验证

更新：2026-11-13。这是项目自己写的临时诊断命令，不是官方 CLI 命令，
不是 AstrBot 内置能力，也不是运行中的 MCP 服务。

## 为什么有这条命令

目的是先回答三个独立问题：AstrBot 能否导入我们的插件、插件能否启动
浏览器执行器、适配器能否取得真实微博结果。它不承担正式发帖业务。

代码关系：

| 文件 | 分支及本机位置 | 职责 |
| --- | --- | --- |
| `astrbot_plugin_social_probe/main.py` | `codex/experiment-playwright`，工作树 `runtime/experiments/playwright/` | 注册并处理命令 |
| `experiments/webmcp/probe.mjs` | `codex/experiment-webmcp`，工作树 `runtime/experiments/webmcp/` | 运行浏览器和适配器 |
| `experiments/webmcp/auth-evidence.mjs` | 同上 | 独立登录判断 |
| `experiments/playwright/test_astrbot_runtime.py` | Playwright 分支 | 使用真实 SDK、测试事件对象调用命令方法 |
| `tools/browser-experiment.ps1` | 主工作树 | 从 PowerShell 直接运行探测或打开手动登录窗口 |

对应已提交版本：webmcp `64d77ba`、插件与 SDK 测试 `fb8758f`。
都是本机 Git 提交；不据此声称已推送远程仓库。

可核对真实源码，不必根据文档猜测：

```powershell
git show codex/experiment-playwright:astrbot_plugin_social_probe/main.py
git show codex/experiment-webmcp:experiments/webmcp/probe.mjs
```

## 命令每一部分是什么意思

入口简化如下，完整代码以分支文件为准：

```python
@filter.command("weibo_probe")
async def weibo_probe(self, event: AstrMessageEvent, route: str = "dom"):
    result = await self.run_probe(route)
    yield event.plain_result(json.dumps(result, ensure_ascii=False))
```

- `weibo_probe`：项目取的命令名。
- `bridge`：`route` 参数，只允许 `dom` 或 `bridge`。
- `bridge` 在插件里映射到 `webmcp` 实验目录；`dom` 映射 Playwright 实验。
- 默认参数是 `dom`；要测 webmcp 必须明确传 `bridge`。
- 函数先找 Node 与脚本，再以参数列表启动子进程，90 秒超时。
- 返回 JSON 摘要；不接受任意 Shell 文本，不调用模型生成内容。

浏览器路线用的依赖是 `@webmcp-bridge/adapter-weibo@0.8.2` 和
`playwright@1.58.2`，适配器通过 `start/listTools/callTool/stop` 调用。
名称包含 bridge 不能证明已经通过 MCP 协议连接 AstrBot。

## 一次 bridge 探测实际做什么

1. 枚举适配器工具，当前固定版本得到 16 个。
2. 用系统 Edge 启动专用持久配置，默认目录为主工作树
   `runtime/weibo-browser-profile/`。
3. 对指定业务 AJAX 路径设置写请求拦截，随后在导航前调用
   `adapter.start({page})` 安装捕获脚本。
4. 打开微博首页，等待页面输入框或登录提示，以及动态元素加载。
5. 同时执行上游 `auth.get` 和独立 DOM 登录判断；登录页优先认定未登录，
   公开动态和站点标题不能单独证明登录。
6. 独立确认登录后调用 `timeline.home.list(limit=2)`。
7. 调用 `post.create`，传固定测试文案和 `dryRun=true`，只填写临时页并
   检查提交按钮，不点击发送。
8. 从读到的第一条动态取得 ID，调用 `post.get`、`post.replies.list`。
9. 把完整 JSON 与截图存到本地忽略目录；标准输出只返回摘要。
10. 关闭适配器和浏览器；插件解析摘要并返回聊天结果。

`authenticated_probe` 只表示通过登录判断，不代表全部子操作成功。
还必须分别检查 `timeline.count/source`、`detail.present`、
`replies.count/source`、`dryRun.ok` 和各自 `error`。
没有动态时详情和评论步骤会跳过；评论数为 0 也不能单独证明请求失败。

拦截范围仅为微博域名的 `/ajax/statuses/`、`/ajax/comments/`、
`/ajax/attitudes/` 非 GET/HEAD/OPTIONS 请求；不是全站所有写操作的保证。
本探测没有调用真实发布、评论或点赞分支。它可能在本地或页面留下
预演文案，因此不能描述为“浏览器完全没有变化”。

## 验证分层及实际结果

| 层级 | 怎么验证 | 已取得的证据 | 未覆盖部分 |
| --- | --- | --- | --- |
| 纯判断逻辑 | Node 内置测试运行 `auth-evidence.test.mjs` | 4 项通过 | 不证明浏览器登录 |
| 真实网页与适配器 | PowerShell 直接运行 bridge | 已登录，2 条动态、单条详情、首轮 17 条评论，网络来源；预演通过 | 真实写入、MCP 服务 |
| 插件调用与真实 SDK | 内置 Python 导入插件并调用命令方法 | SDK 导入及方法调用通过；2 条动态、详情、下一轮 20 条评论、预演通过 | 插件管理器加载、真实消息路由、模型工具选择 |
| AstrBot 桌面/微信 | 安装启用后从聊天发送命令 | 尚未记录验证结果 | 整条真实消息链路待验 |
| 真正发布闭环 | 用户确认后发布并打开微博链接 | 尚未执行 | 正式插件下一阶段 |

SDK 测试里的 `LocalEvent` 只实现 `plain_result`。
它直接调用 `plugin.weibo_probe(...)`，断言有一条可解析 JSON 返回，
且没有进程/解析/超时错误；输出的 `command_handler=passed`
不能解释为 AstrBot 已经分发过真实微信消息。

17/20 是两次查询的实际条数，不是验收阈值，网页内容可能变化。

## 如何复现

先关闭之前的登录窗口，避免浏览器配置被占用。需要重新登录时：

```powershell
.\tools\browser-experiment.ps1 login
```

由本人扫码，完成后关闭窗口。CLI OAuth 授权不等于网页会话登录。

直接测试适配器：

```powershell
.\tools\browser-experiment.ps1 bridge
```

使用本机 AstrBot SDK 测试插件：

```powershell
& 'C:\Users\27528\AppData\Local\AstrBot\backend\python\python.exe' `
  runtime/experiments/playwright/experiments/playwright/test_astrbot_runtime.py `
  'C:\Users\27528\AppData\Local\AstrBot\backend\app' `
  'C:\Users\27528\Downloads\创新实践' bridge
```

本机结果示例，字段值来自已执行的一轮：

```json
{
  "route": "bridge",
  "status": "authenticated_probe",
  "authenticated": true,
  "tool_count": 16,
  "post_count": 2,
  "timeline_source": "network",
  "dry_run_ok": true,
  "detail_present": true,
  "reply_count": 20,
  "error": "",
  "exit_code": 0
}
```

测试登录判断：

```powershell
$nodePath = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
& $nodePath --test runtime/experiments/webmcp/experiments/webmcp/auth-evidence.test.mjs
```

真实聊天复现另见 [安装与配置](astrbot-integration.md)。
原始结果在 `runtime/experiments/webmcp/runtime/results/probe.json` 与
`page.png`；原始 JSON 会包含动态、评论和账号相关数据，不能提交 Git。
摘要文件可能被下一轮覆盖，需保留一轮证据时另存到忽略的本地目录。

## 已修正的问题与保留的缺口

初版在页面加载后才安装捕获脚本，导致 `no_template` 和空动态；先启动
适配器再导航后真实网络读取成功。发帖预演也恢复，不能继续把首轮控件
错误当作已确定的上游功能失效。

上游仍存在把登录页误认为已认证的逻辑，因此保留独立判断。
本机当前页面旧 feed 选择器匹配 0 个，网络路径成功不代表 DOM 回退可靠。
点赞工具缺失，评论提交、回复指定评论、真实发帖等仍需逐项开发验证。
