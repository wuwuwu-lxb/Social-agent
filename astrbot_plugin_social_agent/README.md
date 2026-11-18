# Social Agent v0.2.0

AstrBot 的最小微博工具插件：创建文本草稿、保存任务、使用已登录 Edge
预演填写发帖框，支持本人确认后实际发布公开文本微博。
预演通过不等于已发布，只有提交响应和详情正文核验通过才返回发布成功。

## 当前可用入口

| 入口 | 作用 |
| --- | --- |
| 模型工具 `weibo_statuses_update(status)` | 自然语言请求创建微博草稿并预演，返回任务编号、原文与结果 |
| `/weibo_draft <文案>` | 不经过模型，直接执行相同的草稿预演 |
| `/weibo_status <任务编号>` | 查询当前用户、当前会话的任务 |
| `/weibo_drafts` | 列出当前用户、当前会话最近 5 条草稿 |
| `/weibo_confirm <任务编号>` | 本人确认原文后实际发布，重复确认仅返回已有结果 |

2026-11-17：先保存草稿，再运行浏览器预演。即使浏览器启动失败、登录失效或
配置缺失，已保存的文案仍可查询。返回的 `draft_saved` 表示本地保存成功，
`ok` 和 `status` 表示网页预演结果，两者分别核对。
草稿保存在本机 SQLite，不能声称已同步到微博官方草稿箱。

当前只支持 1-140 个字符的公开文本微博，发布时选择网页“内容由AI生成”。
图片、其他可见性、评论、点赞尚未实现；不要把这个工具当作完整官方 `statuses update`。
自然语言工具名称按官方操作规划，返回行为是项目的草稿任务封装。

默认只允许私聊；`allowed_user_ids` 非空时再限制发送者。
空列表允许私聊用户预演，不允许群聊，且始终不能发布。
实际发布同时要求 `allow_publish=true` 和非空的用户白名单。
模型工具只准备草稿，实际提交只能由本人发送确认命令触发。

## 本机已部署情况

2026-11-13 已部署到：

```text
C:\Users\27528\.astrbot\data\plugins\astrbot_plugin_social_agent
```

已启动真实 AstrBot，后端日志确认插件加载、模型工具注册，微信平台
适配器加载正常。2026-11-13 用户在会话中进一步确认微信端验证通过。
该结论依据本人实测反馈。2026-11-17 新增真实发布实现及确认入口，
实际提交及结果读回的首次平台验收仍需本人发送确认命令，不以模拟测试冒充平台发帖。

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

检查回复中的最终文案与发布设置。确定发布后，本人发送：

```text
/weibo_confirm T实际任务编号
```

发布目标为配置的专用 Edge 当前登录的微博账号，固定公开，选择“内容由AI生成”。
成功时回复详情链接；`unknown` 表示可能已提交但核验未完成，应先打开微博核对。
不要重新创建相同文案来绕过未知状态。所有发起过发布的任务均不会自动重试，
包括平台拒绝和进程异常退出；再次确认仅查询已有记录。

命令需满足 AstrBot 全局唤醒规则。命令通过但自然语言没调用时，
检查当前会话工具启用状态与模型工具调用能力。
工具返回结果和最终模型回复分开核对，不能凭模型说“发布了”判断平台生效。

用 `/weibo_drafts` 找回最近的任务编号，再使用 `/weibo_status <编号>` 查看全文和预演结果。
`preview_pending` 表示已保存但预演尚未结束，或执行中途被中断，不能解释为预演成功。

## 配置与依赖

插件设置：

- `node_path`：Node 可执行文件，空时自动查找；Node 22 以上。
- `browser_profile`：专用 Edge 配置目录的绝对路径；本机复用项目
  `runtime/weibo-browser-profile`，登录由本人完成。
- `allowed_user_ids`：允许的私聊发送者 ID；不要粘贴到公开仓库。
- `allow_publish`：默认 false，开启且白名单包含本人时才允许确认发布。

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
& 'C:\Users\27528\AppData\Local\AstrBot\backend\python\python.exe' tests/test_publication.py

# 在有 Node 依赖的插件目录运行，浏览器请求全部由测试夹具拦截
node --test astrbot_plugin_social_agent/node/publish.test.mjs

& 'C:\Users\27528\AppData\Local\AstrBot\backend\python\python.exe' `
  tests/test_minimal_plugin.py `
  'C:\Users\27528\AppData\Local\AstrBot\backend\app'
```

在项目根目录运行。测试在忽略的 `runtime/plugin-sdk-*` 中创建独立
AstrBot 环境，用真实 `PluginManager` 加载插件、读取工具注册表，
调用已绑定工具并启动真实浏览器预演。还检查空参数、用户限制、
命令多词参数、保存查询及跨用户/会话隔离。
不测试真实微信消息、不调用模型、不提交微博。

发布测试分别覆盖数据库原子认领、并发及重启防重复、权限和归属、
未知状态禁止重试；浏览器夹具覆盖 UI 点击、发布响应、正文读回、平台拒绝和
正文不匹配。所有夹具请求在 Playwright 路由中直接返回，不访问真实微博。
真实页面另已通过内容声明、公开设置和发送控件的发布前检查，没有点击发送。

2026-11-17 再次通过真实 SDK 和网页测试，并新增浏览器启动失败时草稿保留、
列表查询与隔离测试。实际浏览器返回：

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

Node 具有预演、发布前检查和真实发布三个固定操作。
真实发布仅放行一条由页面生成、正文匹配的 `/ajax/statuses/update` POST。
请求正文按 JSON、URL 编码表单或 multipart 表单解析；无法精确匹配文案时拒绝发送。
其他微博写请求均拦截。正文通过平台详情网络响应完整比对。
选择网页声明与平台声明字段读回核验分别记录，不把两者混为同一证据。
Node 内使用互斥锁文件和浏览器原有 profile 独占防止并行访问；
锁仅覆盖此包，旧实验入口不共享该锁，仍需顺序运行。
异常中断可能留下 `.social-agent.lock`；先确认相关进程已退出，
再处理该锁，不在运行中强行重开。
超时会尝试回收浏览器进程树；错误只返回概要，不把账号原始数据发到日志。
预演可能留下网页草稿，不等于网页状态完全未改变。

此版本在 Windows、AstrBot 4.29.4、Node 24.22.1 和 Edge 验证。
进程中断可能留下 executing 记录或浏览器锁，需人工核对平台后处理，程序不会自动重发。
目前不会自动恢复未知提交或补做核验，也不支持同文任务之间的全局去重。
