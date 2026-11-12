# 相关案例与复用判断

更新日期：2026-11-12。当前主线为浏览器接入，CLI 探索已经结束。

## webmcp-bridge：已运行的对比实验

- 仓库：https://github.com/holon-run/webmcp-bridge
- 使用包：`@webmcp-bridge/adapter-weibo@0.8.2`。
- 实测：16 个工具注册成功，无点赞工具；未登录页面存在登录误判，已在实验入口加独立保护。
- 详情与自建 Playwright 路线对比：[实测记录](browser-experiments.md)。

## 微博官方 CLI

- 官方手册：https://open.weibo.com/cli/quickstart
- npm 元数据：https://registry.npmjs.org/@weibo-ai%2Fweibo-cli/latest
- 本项目已安装版本：`@weibo-ai/weibo-cli@0.9.8`。
- 实机验证记录：[CLI 验证](weibo-cli-validation.md)。

这是已探索的官方入口，目前保留作行为与参数参考。

已完成授权及目录查询，列出 75 个命令，确认目录包含发帖、评论和点赞。
额度限制促使项目转向浏览器；目录存在不证明业务调用已成功。

## astrbot_plugin_weibo_push：读取与底座组织参考

- 仓库：https://github.com/ZASENJC/astrbot_plugin_weibo_push
- 插件入口：https://github.com/ZASENJC/astrbot_plugin_weibo_push/blob/main/main.py
- 功能模块：https://github.com/ZASENJC/astrbot_plugin_weibo_push/tree/main/astrbot_weibo_push
- 前身：https://github.com/jiantoucn/astrbot_plugin_weibo_monitor

此前已读取维护者 README 与目录，未运行、未完成入口源码审查。

维护者展示微博监控、订阅、关注列表同步、关键词过滤、内容解析及向聊天会话推送。可参考插件模块组织和读取结果如何返回聊天会话；不以它承担账号写入操作。

我们自行实现人设、草稿、任务状态和执行记录；实际平台操作先验证浏览器路线。
