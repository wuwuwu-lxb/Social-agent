# AstrBot 如何接入，插件具体如何做

核对日期：2026-11-12。本文是基于当前官方文档的实施说明，尚未在本机运行。

## 1. 当前接入方式

采用 Python 插件调用微博官方 CLI。插件承载命令入口、账号策略、草稿与任务记录；CLI 承担官方平台请求。

CLI 已在本项目安装，账号授权与实际操作权限待验证。插件被加载不会自动获得微博操作能力。

官方资料：

- 插件入门：https://docs.astrbot.app/dev/star/plugin-new.html
- 最小实例：https://docs.astrbot.app/dev/star/guides/simple.html
- AI 调用：https://docs.astrbot.app/dev/star/guides/ai.html
- 官方模板：https://github.com/Soulter/helloworld

## 2. 先验证 CLI，再接插件

1. 按 [落地路线](implementation.md) 完成 CLI 登录、诊断和命令发现。
2. 固定一个实际可用的只读命令，记录其 JSON 返回字段。
3. 插件适配器通过参数列表启动 Node 和 `dist/index.js`，传入固定操作。
4. 设置超时，检查退出码，解析响应并向聊天入口返回结果。
5. 只读链路成功后，逐项增加已验证的写操作。

第一轮建议在同一 Windows 用户下运行 CLI 与 AstrBot，避免登录态在不同用户、容器间不可见。若后续采用 Docker，需要在运行插件的容器内另行安装 Node/CLI 并配置授权；宿主机安装不会自动进入容器。

## 3. 自己写插件时的真实文件位置

官方文档将插件放在：

```text
AstrBot/
└── data/plugins/
    └── astrbot_plugin_social_agent/
        ├── metadata.yaml
        ├── main.py
        ├── _conf_schema.json     # 需要配置界面时增加
        └── social_agent/        # 项目自己的业务模块
            ├── service.py
            ├── store.py
            └── adapters/
```

这是拟采用的运行目录，尚未创建业务代码。Social-agent 保持自己的 Git 仓库，开发时将插件目录复制或挂载到 AstrBot 的上述位置，不需要把整个 AstrBot 本体纳入本仓库。

`metadata.yaml` 是官方说明要求的元数据文件；`main.py` 中定义继承 `Star` 的类，通过 `Context` 调用底座。命令方法使用 `@filter.command(...)`，接收 `AstrMessageEvent`，通过 `yield event.plain_result(...)` 返回文本。

插件如何算加载成功：在 AstrBot 插件页安装或重新加载，确认日志没有导入异常，再从测试聊天入口触发一个明确命令。不能仅检查目录存在。

## 4. 第一段业务代码应该完成什么

先做 `/social_probe`，它只检查当前会话是否能取得模型并生成一段草稿，不接社交平台。下面是依据 SDK 编写的实现示意，未安装 AstrBot，因此没有运行验证：

```python
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star


class SocialAgentPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("social_probe")
    async def social_probe(self, event: AstrMessageEvent):
        provider_id = await self.context.get_current_chat_provider_id(
            umo=event.unified_msg_origin
        )
        if not provider_id:
            yield event.plain_result("请先为当前会话配置聊天模型。")
            return
        response = await self.context.llm_generate(
            chat_provider_id=provider_id,
            prompt="为大学生学习 Python 写一条简短社交帖子草稿。",
        )
        yield event.plain_result(response.completion_text)
```

这些模型调用接口在官方文档标为自 v4.5.7 引入；这只是 API 最低信息，不能代替选定版本的兼容测试。示例省略了生产环境异常处理，不能直接视为完整插件。

通过后再实现自己的业务入口，以下名字是项目设计，不是 AstrBot 内置接口：

| 入口 | 程序实际需要做的事 |
| --- | --- |
| `/social_draft` | 读取主题和人设，调用模型，保存草稿与任务编号 |
| `/social_confirm` | 校验任务归属和状态，只执行已展示的草稿，保存执行结果 |
| `/social_status` | 查询任务，明确显示成功、失败或结果未知 |

CLI 子进程放到 `adapters/`；命令处理函数只负责入口与返回结果。调用 CLI 时用独立参数列表，不把模型生成的文字拼成 Shell 命令。

## 5. 为什么初期用命令，后期再开放模型工具

明确命令方便定位“没触发、模型失败、平台失败”分别发生在哪里。主链路稳定后，再按官方 AI 文档的工具注册机制让模型选择读取、草稿与任务查询工具。

确认写入应校验任务状态和实际用户来源；不能只在提示词写“请先确认”，也不能让模型自己调用确认工具冒充用户确认。第一版可以只提供生成草稿工具，写操作保留给明确命令。

平台适配器直接调用已验证的官方 CLI 操作，当前不引入额外 MCP 服务。
