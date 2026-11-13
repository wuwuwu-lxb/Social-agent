# 正式微博插件设计

更新：2026-11-13。本文描述完整目标，未标注完成的部分仍属设计。
v0.1.0 已实现并部署一个草稿预演模型工具、SQLite 草稿任务及查询命令，
真实后端加载与工具注册已确认。尚无用户确认或真实发布入口，
微信端待测；当前实测与用法见 [插件说明](../astrbot_plugin_social_agent/README.md)。
近期目标：从微信提出文本发帖请求，收到草稿，确认后发布至微博并得到链接。

## 接口以官方 CLI 为参照

当前 `@weibo-ai/weibo-cli@0.9.8` 返回 75 个接口，保留原始分组、动作、
方法、参数名称、类型、必填项、枚举、用法说明与目录版本。
全量快照在 `specs/weibo/official-cli-catalog.json`，逐项覆盖关系在
[对照表](../research/weibo-tool-matrix.md)。

“对齐”分三个层次：

| 层次 | 规则 |
| --- | --- |
| 名称与输入 | `statuses update` -> `weibo_statuses_update`，仍用 `status`；分组动作中的空格和 `/` 转为 `_` |
| 执行能力 | 显式记录后端、支持的参数与验证级别；不把相关网页操作当作官方接口的完整等价实现 |
| 结果 | 项目统一结果封装，保存来源和平台证据；不捏造与官方响应相同的字段 |

完整设计覆盖 75 项，但不一次性把 75 个占位函数暴露给模型。
每个操作从 planned 到 implemented，再到 verified 后，才按配置启用。
未实现操作通过能力查询明确显示 `unsupported_operation`。

webmcp 目前没有表态/点赞工具，回复指定 `cid`、删除、图文、关系、
统计、短链、指数及文章高级功能没有验证。它们仍保留在全量契约中，
后续选择浏览器扩展或官方后端逐项实现，不伪装成已有能力。
不因某项浏览器不支持就自动调用可能消耗额度的官方 CLI；
未来加入官方后端时需独立配置并说明使用条件。

## 参数差异不能隐藏

`statuses update` 的官方必填参数是 `status`，其他参数包括
`visible`、`mblog_statement`、`is_longtext`、`lat`、`long`、
`list_id`、`annotations`。现有浏览器 `post.create` 只有文本与预演，
不能声称已经覆盖这些选项。

第一版只启用经过测试的文本子集；工具说明和能力查询需列出该子集。
用户传入未支持的选项必须返回 `unsupported_parameter`，
不能忽略 `visible=1` 后按公开内容发布。
生成内容需要怎样在当前页面声明 AI，以及声明是否生效，应在正式
发布测试前实现并核对；不能因追加一段文字就声称等价于官方声明字段。
暂不能实现时，将对应场景阻塞并解释实际缺口。

微博 ID、评论 ID、用户 ID 在项目边界统一使用十进制字符串，
避免 Node 将大整数转成 `Number` 丢精度。官方批量参数若是逗号分隔，
保留外部表示；内部解析成字符串列表并逐项校验。
参数依赖（例如 `visible=3` 需要 `list_id`）与枚举规则从快照核对，
不能只验证必填项。

例如，拟用接口：

```json
{
  "tool": "weibo_statuses_update",
  "arguments": {"status": "今天完成了第一次联调。"}
}
```

目标版本中，该模型工具创建一项待确认发布任务，不立即产生平台写入。
返回 `awaiting_confirmation`、`task_id`、待发布原文及已支持设置；
工具描述必须明确这一行为。用户明确确认后才调用同一操作的内部执行逻辑。
这是项目的任务封装，不是官方接口本身的同步响应。

## 模块与分发目录

以下为目标目录，v0.1.0 实际文件以插件目录为准：

```text
astrbot_plugin_social_agent/
  main.py                    # 命令入口与 llm_tool 注册
  metadata.yaml
  _conf_schema.json
  social_agent/
    service.py               # 草稿、任务与发布流程
    contracts.py             # 输入校验、错误与结果类型
    store.py                 # SQLite 状态与幂等记录
    capabilities.py          # 仅声明真实实现的能力
    adapters/browser.py      # 固定操作的异步子进程调用
  node/
    package.json
    pnpm-lock.yaml
    executor.mjs             # JSON 输入输出、固定操作路由
    auth-evidence.mjs
  specs/
    tool-contract.json
```

正式包应自带执行器源文件和依赖清单，使用配置指定 Node、浏览器及专用
profile 目录，不依赖 `runtime/experiments/...` 或另一条 Git 分支。
本地依赖按锁文件安装；不把 node_modules、浏览器会话或账号证据塞进 ZIP。
安装和启动时检查实际环境，缺依赖就报明确错误，不偷偷改系统。

插件业务层不调用任意 Shell。Python 通过参数列表启动固定 Node 入口，
结构化请求经标准输入传递，避免文案被解释为命令或暴露在进程参数中。
标准输出只写 JSON，日志写标准错误。
浏览器账号共用一个跨进程互斥机制；仅靠每个插件实例内的 asyncio.Lock
不足以防止命令行、重载后的实例和登录窗口同时占用同一 profile。
超时需关闭浏览器上下文、回收进程并记录任务，不遗留占用。

## 首版给模型和用户的入口

以下是目标入口；当前 v0.1.0 仅有 `weibo_statuses_update` 的草稿预演子集、
`/weibo_draft` 和 `/weibo_status` 可用，其余仍待实现：

| 入口 | 承担的事 |
| --- | --- |
| 模型工具 `weibo_capabilities` | 返回已实现操作、参数子集、登录状态与验证级别 |
| 模型工具 `weibo_statuses_update` | 当前按 `status` 创建草稿并预演；确认发布流程待实现 |
| 模型工具 `weibo_task_get` | 查询某个任务，校验所属用户与会话 |
| 用户命令 `/weibo_confirm <task_id>` | 确认展示过的草稿，检查版本和归属后提交 |
| 用户命令 `/weibo_status <task_id>` | 不依赖模型查询结果 |
| 自然语言“确认发布 Txxx” | 在消息入口解析为同样的确认动作，不由模型自行授权 |

草稿内容可由 AstrBot 当前模型生成，无需插件再内置一个模型客户端。
模型需支持工具调用，且当前会话能够使用这些工具。
对于用户直接给定的文案，第一版仍显示最终内容并确认，先把流程做稳定。
将来允许明确的直接发布请求时，也必须在可信用户消息入口建立授权，
不能只由模型工具参数中的 `confirmed=true` 代替。

入口按配置限制允许操作的微信用户/会话；任何群成员都能要求发到
同一个微博账号不是合理默认值。该控制发生在程序层，页面、微博正文、
评论和模型文本都不能授予发布权限。

## 任务与返回结果

目标状态流转（当前只保存草稿和预演结果）：

```text
draft -> awaiting_confirmation -> executing -> succeeded
                                  |       -> failed
                                  |       -> unknown
draft / awaiting_confirmation -> cancelled
```

保存任务编号、消息来源、用户与会话、草稿版本和内容哈希、操作名、
目标账号、确认时间、提交时间、平台返回及核验结果。
同一任务只能成功提交一次；重复确认返回已有任务结果。
平台提交后超时为 `unknown`，需先核对，禁止直接再次发布。

拟用统一返回格式，以下是结构示意，不是已发布结果：

```json
{
  "ok": true,
  "operation": "statuses update",
  "backend": "browser",
  "status": "awaiting_confirmation",
  "task_id": "T-example",
  "data": {"status": "今天完成了第一次联调。"},
  "verification": {"submitted": false, "confirmed": false},
  "error": null
}
```

只有取得可核对的微博标识/链接，且读回或页面证据确认正文匹配，
才标记 `succeeded`。按钮点击、HTTP 200、模型回复“已发布”都不充分。
错误包括 `auth_required`、`unsupported_operation`、
`unsupported_parameter`、`busy`、`permission_denied`、
`validation_error`、`upstream_changed`、`action_unconfirmed`。
明确失败与结果未知分开，不把未知结果包装为可以重试的普通失败。

## 开发顺序与验收门槛

1. 提取实验执行器到正式包，保留导航前捕获、登录防护和预演默认值；
   让 `/weibo_probe bridge` 的已验证读取可迁移，不再依赖实验目录。
2. 实现任务存储、能力查询与参数校验；以真实 SDK 验证工具注册和配置注入。
3. 注册发帖工具，完成“微信请求 -> 草稿 -> 任务编号”，仍不提交。
4. 实现用户确认、单次提交、内容声明、结果查询；本人提供测试文案后做真实发布。
5. 从微信走完整闭环并打开微博链接核对；测试重复确认、登录失效、
   未支持参数和提交后超时。
6. 单独验收评论创建与指定评论回复，再实现点赞扩展；其余接口逐组推进。

当前已完成实验读取、正式预演执行器、草稿存储和归属查询、
真实插件管理器及注册工具调用测试，以及本机后端加载。
用户确认、完整任务状态流转、微信消息触发与实际提交仍未完成。

## 资料更新方式

```powershell
# 查询官方目录，只读取定义，不执行任何业务接口
.\tools\sync-weibo-catalog.ps1

# 不联网，用当前快照及人工映射重新生成工具契约和对照表
.\tools\sync-weibo-catalog.ps1 -Offline
```

生成脚本检查接口数量、工具名唯一性及映射中的操作名。
快照排除账号访问权限、服务状态、价格与账号资料，只保留接口定义。
一次更新修改映射及契约，实际实现仍需独立验证，不自动开放新工具。
