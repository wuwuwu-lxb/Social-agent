# Social-agent

面向大学创新实践的社交媒体智能体项目。计划以 AstrBot 为底座，让智能体在指定主题和账号设定下，完成内容理解、发帖草稿生成、评论回复、点赞决策和执行记录。

浏览器实验已读取真实动态、详情与评论，并完成发帖预演；两个独立实验分支保留早期代码及只读探测插件。当前进入正式插件的最小工具联调，尚未实际发帖。

2026-11-13 已实现独立插件 v0.1.0，并部署到本机 AstrBot。
真实后端加载与模型工具注册已确认；支持创建草稿、保存任务和浏览器预演，
暂不发布。微信端测试步骤见 [插件说明](astrbot_plugin_social_agent/README.md)。

## 项目目标

最小成功标准是在微信完成一次真实文本发帖，账号主题与人设后续配置：

> 微信提出请求 → AstrBot 展示草稿与任务编号 → 用户确认 → 微博发布 → 核对正文 → 微信收到微博链接

第一版聚焦微博、单账号、文本内容。CLI 0.9.8 已安装并完成授权和命令目录探索；考虑额度限制，当前转向浏览器实验。CLI 保留作行为与参数参考，不作为当前开发前置条件。

## 功能范围

| 阶段 | 功能 | 验收方式 |
| --- | --- | --- |
| 最小版本 | 微信工具调用、文本草稿、确认发布、结果记录 | 微信提出请求，确认后得到可打开核对的微博链接；重复确认不重复发布 |
| 下一阶段 | 读取指定内容、生成回复、确认评论 | 对指定测试内容完成一次评论并验证结果 |
| 下一阶段 | 点赞建议、确认点赞、重复操作检查 | 单独实现适配器缺失能力，记录目标、理由与结果 |
| 后续扩展 | 定时任务、历史记忆、简单统计 | 展示执行历史和统计，验证取消与失败处理 |
| 可选探索 | 多平台、图文、多角色对比 | 主线验收完成后再安排 |

真实平台的每项能力必须单独验证；模拟执行与真实执行在汇报中明确区分。

## 技术方案草案

- AstrBot：作为对话与模型调用入口，已找到本机 4.29.4 桌面安装及 Python SDK。
- 平台执行器：以已验证读取和预演的 webmcp 微博适配器为主线，自建 Playwright 用作补充。
- 项目插件：通过 `main.py`、`metadata.yaml` 和 `Star` 类接入底座，逐步实现任务、草稿、确认与日志。
- 平台适配层：按官方 CLI 的 75 项接口规划工具名与参数，逐项记录真实支持范围，不用占位工具冒充实现。
- SQLite：已用于草稿、任务及预演结果记录；发布幂等流程待实现，密钥单独存放。
- 平台执行：先验证浏览器读取、定位与预演，再接入写入确认流程。模型只生成结构化行动建议，由程序检查后执行。

正式结构与开发顺序见 [插件设计](docs/plugin-design.md)，完整范围见
[官方接口与工具对照](research/weibo-tool-matrix.md)。
现有 `/weibo_probe bridge` 是本项目写的诊断命令，来源、实际执行与复现
见 [探测说明](research/weibo-probe.md)，不表示微信已能真实发帖。

## 文件管理

```text
创新实践/
├── README.md
├── .gitignore
├── tools/weibo-cli/              # 官方 CLI 安装清单、锁文件和启动脚本
├── tools/sync-weibo-catalog.ps1   # 官方定义同步与离线生成
├── specs/weibo/                  # 官方目录快照、浏览器映射、拟用工具契约
├── research/                     # 技术资料、开源案例、接入步骤和文献笔记
│   ├── README.md
│   ├── cases.md
│   ├── astrbot-integration.md
│   ├── implementation.md
│   └── papers.md
├── docs/                         # 随代码同步到 GitHub
│   ├── project-outline.md        # 研究问题、架构、计划、分工
│   ├── platform-selection.md     # 平台选型依据与待验证项
│   └── weekly/
│       ├── TEMPLATE.md
│       └── W01-planning.md
└── ppt/                          # 只保存在本机，Git 忽略整个目录
    ├── README.md
    └── W01/
        └── README.md
```

实验代码位于 `codex/experiment-webmcp` 与 `codex/experiment-playwright` 分支，本机工作树在被忽略的 `runtime/experiments/`。测试证据与浏览器登录态也留在 `runtime/`，不提交。PPT、演讲稿和汇报导出文件放入本地 `ppt/Wxx/`。

浏览器实验的结果、运行命令与下一步见 [实测记录](research/browser-experiments.md)。

开发前优先阅读 [插件设计](docs/plugin-design.md)、
[全量接口对照](research/weibo-tool-matrix.md) 和
[现有探测说明](research/weibo-probe.md)。
原 [项目大纲](docs/project-outline.md) 保留为范围参考；其中八周安排是早期草案，不作为实施前提。
