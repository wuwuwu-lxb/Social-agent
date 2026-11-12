# 相关案例与复用判断

更新日期：2026-11-12。当前只推进微博官方 CLI 接入。

## 微博官方 CLI

- 官方手册：https://open.weibo.com/cli/quickstart
- npm 元数据：https://registry.npmjs.org/@weibo-ai%2Fweibo-cli/latest
- 本项目已安装版本：`@weibo-ai/weibo-cli@0.9.8`。
- 实机验证记录：[CLI 验证](weibo-cli-validation.md)。

这是当前平台执行入口。先通过官方命令完成账号授权和能力发现，再把确实可用的命令封装为 AstrBot 插件中的固定操作。

已验证本地启动、版本、帮助和未登录诊断；平台命令目录要求登录，尚未拿到账号实际能力清单。不预设发帖、评论、点赞均可用。

## astrbot_plugin_weibo_push：读取与底座组织参考

- 仓库：https://github.com/ZASENJC/astrbot_plugin_weibo_push
- 插件入口：https://github.com/ZASENJC/astrbot_plugin_weibo_push/blob/main/main.py
- 功能模块：https://github.com/ZASENJC/astrbot_plugin_weibo_push/tree/main/astrbot_weibo_push
- 前身：https://github.com/jiantoucn/astrbot_plugin_weibo_monitor

此前已读取维护者 README 与目录，未运行、未完成入口源码审查。

维护者展示微博监控、订阅、关注列表同步、关键词过滤、内容解析及向聊天会话推送。可参考插件模块组织和读取结果如何返回聊天会话；不以它承担账号写入操作。

我们自行实现人设、草稿、任务状态和执行记录；实际平台操作先使用官方 CLI。
