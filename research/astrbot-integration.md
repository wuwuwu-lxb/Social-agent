# AstrBot 接入：微信对话到微博操作

更新：2026-11-13。采用 Python 插件，复用已经接入 AstrBot 的微信消息通道。
浏览器执行使用 webmcp-bridge 的微博适配器模块，不要求先启动 MCP 服务。

2026-11-17 更新：v0.2.0 已在真实后端加载，`/weibo_confirm <编号>` 触发实际发布。
浏览器预演复用适配器，提交和正文读回使用项目 Playwright 固定操作。
发布前检查及夹具测试通过，首次真实提交验收仍待本人确认，见 [发布记录](publishing-2026-11-17.md)。

## 接入结构

```text
微信消息
  -> 已配置的 AstrBot 平台适配器
  -> 模型理解请求，调用插件注册的工具
  -> 插件检查用户、参数、草稿与任务状态
  -> Node 执行器
  -> @webmcp-bridge/adapter-weibo
  -> 专用 Edge 会话 -> 微博
  -> 核对结果 -> AstrBot -> 微信回复
```

2026-11-13 用户已确认微信端工具验证通过，依据为本人实测反馈。
v0.1.0 已安装到真实 AstrBot，后端日志确认加载及模型工具注册。
真实 SDK 注册表调用和浏览器预演通过，微信端触发由用户确认通过。
安装、配置、实测范围及微信测试指令见 [插件说明](../astrbot_plugin_social_agent/README.md)。

## 插件入口分为命令和模型工具

本机 AstrBot 4.29.4 的 SDK 已核对：

| 机制 | 用途 | 当前情况 |
| --- | --- | --- |
| `Star` 子类 | 被插件管理器加载 | v0.1.0 真实插件管理器加载及本机后端加载通过 |
| `@filter.command("weibo_probe")` | 用户明确发送诊断命令 | 已实现；仅在 SDK 测试中直接调用方法 |
| `@filter.llm_tool(name=...)` | 模型根据自然语言选择并调用工具 | 已注册 `weibo_statuses_update`，仅草稿预演；模型选择待验 |
| `_conf_schema.json` | 向插件注入配置 | 正式插件配置 Node、浏览器目录和用户限制 |
| `event.plain_result(...)` | 命令返回消息结果 | 使用测试事件对象验证；真实微信发送待验 |

当前 `/weibo_probe bridge` 是项目自定义诊断入口，不是 AstrBot 或
webmcp 自带命令；`bridge` 也不是 MCP 地址。来源和测试方法见
[探测命令说明](weibo-probe.md)。

正式工具按官方 CLI 接口命名。例如 `statuses update` 对应已注册工具
`weibo_statuses_update`，文本参数仍叫 `status`，再由执行器转换成
`post.create` 的 `text`。75 项完整设计见 [接口对照](weibo-tool-matrix.md)。
只有实现并验收过的工具才能启用；接口清单不是运行时注册清单。

## 历史实验插件怎么装、怎么用

以下保留早期诊断插件的复现方式；当前使用正式 v0.1.0，
请按上方插件说明安装与测试，不需要先安装此实验插件。

插件源码在本机 `codex/experiment-playwright` 分支：

```text
runtime/experiments/playwright/astrbot_plugin_social_probe/
  main.py
  metadata.yaml
  _conf_schema.json
```

安装包：`runtime/packages/astrbot_plugin_social_probe.zip`。
AstrBot 插件管理提供本地文件上传安装；在该入口选此 ZIP，
安装后检查插件日志和启用状态。本文未通过界面验证安装成功。

插件设置中把 `project_root` 填为：

```text
C:\Users\27528\Downloads\创新实践
```

在 AstrBot 已接入的聊天中发送 `/weibo_probe bridge`。
若全局配置要求唤醒前缀、群聊提及或其他唤醒条件，应先满足这些条件。
不应把未触发命令直接判断为微博故障。

成功返回应包括 `authenticated=true`、`post_count`、
`timeline_source`、`dry_run_ok` 等摘要；实际值以本次运行结果为准。
此命令会读取动态和评论、填入临时发帖文案并预演，但不会提交。
没有任何正式发帖入口，不会因微信说“发微博”就自动发布。

本机插件目录实际为：

```text
C:\Users\27528\.astrbot\data\plugins
```

它是 AstrBot 运行数据，不应把整个目录或 AstrBot 本体纳入项目 Git。
当前实验插件依赖两处实验工作树，不是可独立分发的正式插件。

## 正式插件的最小验收

1. 在微信发送“帮我写条微博，记录今天的学习内容”。
2. 模型调用插件工具创建草稿；微信收到文案和任务编号。
3. 用户确认该任务；程序校验确认者、会话和草稿版本。
4. 插件执行发布，读取实际平台结果并核对。
5. 微信收到微博链接；本人打开链接确认正文一致。
6. 重复确认同一任务，返回原结果，不重复发布。

若已提交但结果不明，状态为 `unknown`，不能回复“发布成功”，也不能
自动再次提交。第一版固定单账号、文本、同一台电脑，优先跑通这条链路。
评论、回复、点赞逐项增加，不延后发帖闭环。

正式模块、参数兼容范围、任务状态与开发顺序见
[插件设计](../docs/plugin-design.md)。

## 依据

- AstrBot 官方插件文档：https://docs.astrbot.app/dev/star/plugin-new.html
- 官方模型与工具文档：https://docs.astrbot.app/dev/star/guides/ai.html
- 本机 `astrbot/api/event/filter/__init__.py` 导出 `llm_tool`。
- 本机 `astrbot/core/star/register/star_handler.py` 的 `register_llm_tool`
  解析工具函数及参数文档，并将返回字符串交给模型。
- 本机 `astrbot/core/star/star_manager.py` 读取元数据、配置并实例化插件。
- 本机 `astrbot/dashboard/api/plugins.py` 提供插件文件上传安装路由。

以上源码核对范围为本机安装的 4.29.4，不表示其他版本已做兼容测试。
