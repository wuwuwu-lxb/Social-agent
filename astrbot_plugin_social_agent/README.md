# Social Agent v0.1.0

AstrBot 的最小微博工具插件：创建文本草稿、保存任务、使用已登录 Edge
预演填写发帖框。当前没有发布或确认发布入口，预演通过不等于已发布。

## 当前可用入口

| 入口 | 作用 |
| --- | --- |
| 模型工具 `weibo_statuses_update(status)` | 自然语言请求创建微博草稿并预演，返回任务编号、原文与结果 |
| `/weibo_draft <文案>` | 不经过模型，直接执行相同的草稿预演 |
| `/weibo_status <任务编号>` | 查询当前用户、当前会话的任务 |

首版只支持 1-140 个字符的文本。图片、可见性、AI 声明、真实发布、
评论、点赞尚未实现；不要把这个工具当作完整官方 `statuses update`。
自然语言工具名称按官方操作规划，返回行为是项目的草稿任务封装。

默认只允许私聊；`allowed_user_ids` 非空时再限制发送者。
空列表允许私聊用户预演，不允许群聊，且始终不能发布。
正式增加写入能力之前必须配置账号操作人并实现确认流程。

## 本机已部署情况

2026-11-13 已部署到：

```text
C:\Users\27528\.astrbot\data\plugins\astrbot_plugin_social_agent
```

已启动真实 AstrBot，后端日志确认插件加载、模型工具注册，微信平台
适配器加载正常。2026-11-13 用户在会话中进一步确认微信端验证通过。
该结论依据本人实测反馈，未附聊天截图或调用轨迹。当前仍无真实发布入口。

在微信私聊里先发送：

```text
请调用微博工具，为以下文案创建草稿并预演，不要发布：今天完成了社交机器人的首次联调。
```

应得到任务编号、文案与“尚未发布”的说明。若模型没有调用工具，
用命令排查：

```text
/weibo_draft 今天完成了社交机器人的首次联调。
/weibo_status T实际任务编号
```

命令需满足 AstrBot 全局唤醒规则。命令通过但自然语言没调用时，
检查当前会话工具启用状态与模型工具调用能力。
工具返回结果和最终模型回复分开核对，不能凭模型说“发布了”判断平台生效。

## 配置与依赖

插件设置：

- `node_path`：Node 可执行文件，空时自动查找；Node 22 以上。
- `browser_profile`：专用 Edge 配置目录的绝对路径；本机复用项目
  `runtime/weibo-browser-profile`，登录由本人完成。
- `allowed_user_ids`：允许的私聊发送者 ID；不要粘贴到公开仓库。

Python 无额外依赖，使用 AstrBot SDK 和标准库。
Node 依赖固定为 adapter-weibo 0.8.2、Playwright 1.58.2。
在插件 `node/` 中安装：

```powershell
pnpm install --frozen-lockfile --ignore-scripts --no-optional
```

系统需要已安装 Edge。首次使用前由本人在对应专用配置中登录微博，
关闭登录窗口再执行预演；不要在多处同时使用该配置。

本项目本机安装脚本为 `tools/install-minimal-plugin.ps1`，
使用已有本地 pnpm store 离线安装，保留已存在的插件配置。
打包 ZIP 只含源文件和依赖清单，不含 node_modules、登录态、任务数据库。
其他电脑从 ZIP 安装后仍需安装 Node 依赖并配置自己的浏览器会话。

## 如何验证

```powershell
& 'C:\Users\27528\AppData\Local\AstrBot\backend\python\python.exe' `
  tests/test_minimal_plugin.py `
  'C:\Users\27528\AppData\Local\AstrBot\backend\app'
```

在项目根目录运行。测试在忽略的 `runtime/plugin-sdk-*` 中创建独立
AstrBot 环境，用真实 `PluginManager` 加载插件、读取工具注册表，
调用已绑定工具并启动真实浏览器预演。还检查空参数、用户限制、
命令多词参数、保存查询及跨用户/会话隔离。
不测试真实微信消息、不调用模型、不提交微博。

2026-11-13 上述检查通过，实际浏览器返回：

```json
{
  "ok": true,
  "status": "preview_ready",
  "authenticated": true,
  "dry_run": true,
  "submit_visible": true,
  "submitted": false,
  "blocked_mutations": 0
}
```

草稿和任务保存在 AstrBot `data/plugin_data/astrbot_plugin_social_agent/tasks.sqlite3`，
不在代码目录。任务查询同时检查用户与会话。
浏览器执行通过固定 Node 入口和 stdin JSON 传参，不拼接 Shell 命令。

## 已知边界

此包的 JSON 输入输出仅支持预演操作，没有隐藏的真实发布开关。
Node 内使用互斥锁文件和浏览器原有 profile 独占防止并行访问；
锁仅覆盖此包，旧实验入口不共享该锁，仍需顺序运行。
异常中断可能留下 `.social-agent.lock`；先确认相关进程已退出，
再处理该锁，不在运行中强行重开。
超时会尝试回收浏览器进程树；错误只返回概要，不把账号原始数据发到日志。
预演可能留下网页草稿，不等于网页状态完全未改变。

此版本在 Windows、AstrBot 4.29.4、Node 24.22.1 和 Edge 验证。
下一步是微信端工具触发，再增加用户确认、内容声明与真实发布核验。
