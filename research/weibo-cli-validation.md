# 微博官方 CLI 实机验证

日期：2026-11-12。运行环境：Windows、PowerShell、Node v24.22.1。

## 安装

- npm 官方元数据核对包名：`@weibo-ai/weibo-cli`。
- 本次查询到版本 `0.9.8`，声明 Node `>=18`。
- 安装位置：`tools/weibo-cli/node_modules/`，未全局安装。
- 使用本机已提供的 pnpm 11.25.0，指定项目内 store/cache/state，禁用安装脚本。
- 安装结果：31 个依赖包，退出码 0。
- 安装配置：`tools/weibo-cli/package.json` 与 `pnpm-lock.yaml`。
- npm 元数据：https://registry.npmjs.org/@weibo-ai%2Fweibo-cli/latest
- 官方入口：https://open.weibo.com/cli/quickstart

## 实际命令与结果

以下入口均为已安装包的 `dist/index.js`，由 Node 运行；可用本项目 `weibo.ps1` 简写。

| 参数 | 结果 | 退出码 |
| --- | --- | --- |
| `version` | `0.9.8` | 0 |
| `--help` | 显示命令组、JSON 输出和 Agent 标识等帮助 | 0 |
| `doctor --output json` | `ready: false`，下一步要求登录 | 0 |
| `commands --help` | 支持 `list`、`show`、`--available`、`--all` | 0 |
| `auth login --help` | 支持浏览器授权和设备码授权 | 0 |
| `commands list --all --output json` | 缺少登录令牌，未取得命令目录 | 1 |

诊断摘要：

```json
{
  "ready": false,
  "steps": {
    "login": false,
    "developer_verification": false,
    "service": false
  }
}
```

这里只能确认尚未登录；其余 false 来自未登录时的诊断结果，不代表已经查询了账号实际认证或套餐。

## 已核对的实现细节

安装包的 `dist/config.js` 在生产模式使用 `https://open.weibo.com/cli/api`，默认配置目录为用户主目录的 `.weibo-cli/`。

登录帮助说明系统凭据存储与本地加密文件回退。此次未启动登录、未导出令牌，未执行任何真实内容操作。

帮助中明确提供 `--output json`；具体平台操作的输出结构仍需登录后逐项采样，不假设所有命令返回同一结构。

## 下一步

账号持有人在项目根目录运行：

```powershell
.\tools\weibo-cli\weibo.ps1 auth login --browser
```

完成授权后重新运行诊断和命令查询，确认服务要求以及发帖、评论、点赞是否实际开放，再实现适配器。

## Windows 浏览器授权问题与本地修复

后续用户实际登录时，浏览器显示缺少 `redirect_uri` 和 `code_challenge`。

核对 0.9.8 的 `dist/oauth.js`：生成的 URL 包含两者，但 Windows 打开方式是 `execFile("cmd", ["/c", "start", '""', url])`。本机用无网络的 `cmd /c echo` 探针复现：URL 在第一个 `&` 处被截断，后续参数被解释为命令。该缺陷与用户错误相符；实际授权结果仍需重试确认。

项目新增 `entry.mjs`，仅替换上述特定浏览器打开调用，改为 PowerShell 的 `Start-Process -FilePath`；URL 使用单引号转义并以 UTF-16LE EncodedCommand 传递。仍使用官方 CLI 的 URL 生成、回调、PKCE、state 检查和令牌存储，不修改 node_modules。

`browser-open.test.mjs` 使用替身 Start-Process 验证完整 OAuth URL（包含 `&`、引号及编码字符）能到达打开函数，不实际打开浏览器；同时验证其他子进程调用原样透传。启动脚本还验证了 Node 不在 PATH 时的已知位置回退。

重试前在原授权终端按 Ctrl+C 结束旧会话，重新运行浏览器登录，避免复用已经失效的授权链接。如仍不能登录，可用官方 `auth login --device` 方式进一步排查。

## 授权后的实际检查

2026-11-12 用户完成授权后，在沙箱外调用 CLI 检查（沙箱内无法取得同一系统凭据，曾返回未登录；不应据此让用户重复授权）。

- 登录：已成功，`steps.login = true`。
- 开发者认证：官方返回 `unverified`，需要本人使用微博客户端完成认证。
- 服务：`kind = none`，未开通。
- 官方服务提示：可以免费领取 7 天体验包，或购买正式充值包。领取条件和额度以页面实际显示为准。
- 完整命令目录：75 项。
- 当前账号可用命令：0 项；已查询的核心操作锁定原因为 `service`。

只记录状态，不在版本库保存账号 ID、昵称、令牌或人脸认证数据。

### 已确认存在的核心命令

| 目的 | 官方命令 | 必填参数 | 目录标记 |
| --- | --- | --- | --- |
| 当前用户信息 | `users show/biz` | 无 | 支持体验服务，当前锁定 |
| 文本发帖 | `statuses update` | `status` | 支持体验服务，当前锁定 |
| 评论微博 | `comments create` | `id`、`comment` | 支持体验服务，当前锁定 |
| 回复评论 | `comments reply` | `id`、`cid`、`comment` | 支持体验服务，当前锁定 |
| 点赞/表态 | `attitudes create` | `id` | 支持体验服务，当前锁定 |

`attitudes create` 默认 `attitude=heart`、`attitude_type=1` 表示赞。`statuses update` 对 AI 生成内容提供 `mblog_statement=1`；调用后应保存 `id/idstr`。官方说明仅自己可见的微博不保证能通过列表或批量接口回读，超时或空响应应先核对，避免重复发布。

“目录中存在且支持体验”不等于本账号已成功调用。完成认证和服务开通后，先运行 `doctor` 和 `commands list --available`，再以 `users show/biz` 做第一个业务只读请求。尚未发帖、评论或点赞。
