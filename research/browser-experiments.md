# 微博浏览器接入实测

日期：2026-11-12。本文件只把已执行的结果标为通过。

## 实验分支

| 分支 | 本机工作树 | 已验证 | 缺口 |
| --- | --- | --- | --- |
| `codex/experiment-webmcp` | `runtime/experiments/webmcp` | Edge 启动、适配器加载、16 个工具枚举、未登录保护 | 未验证登录后的读取与写入；无点赞工具 |
| `codex/experiment-playwright` | `runtime/experiments/playwright` | Edge 启动、页面 DOM 读取、AstrBot SDK 导入与命令处理函数调用 | 未确认登录；未在 AstrBot 桌面聊天中触发 |

依赖固定为 Playwright 1.58.2、`@webmcp-bridge/adapter-weibo` 0.8.2。使用本机 Edge，无需下载另一个 Chromium。
两个工作树各自保留安装清单及锁文件。

## 现成适配器的实际问题

参考源码：<https://github.com/holon-run/webmcp-bridge>。
本机阅读的上游提交为 `33cf40d944016a91f7bbec372034a1f01f722481`。

运行时枚举到：

```text
auth.get, page.get, timeline.home.list, post.create, post.get,
comment.create, article.listDrafts, article.getDraft,
article.draftMarkdown, article.publishMarkdown,
post.replies.list, post.repost.list, user.get, user.posts.list,
search.weibo, search.ai.summary
```

工具存在不等于调用成功。适配器在 `/newlogin` 页面返回
`state=authenticated`，信号只有 `weibo-title`；源码中包含以
`lowerUrl.includes("weibo.com")` 判定已登录的分支。首轮动态结果为空
（`reason=no_template`），发帖 dry-run 报输入控件不存在。

实验入口已增加独立的保守判断：登录页优先认定未登录，不能用站点标题或公开动态证明账号会话。
未独立确认登录时跳过动态与发帖预演。四个针对误判的回归用例通过。
未修改第三方依赖。探测还拦截微博 `/ajax/statuses/`、
`/ajax/comments/`、`/ajax/attitudes/` 下的非只读请求。

当前结论：保留作工具结构参考与对比实验，不直接作为默认执行器。

## 自建 DOM 路线

探测保存页面标题、登录提示、输入框及动态数量，不提交任何内容。
未登录页面也可以显示公开动态，因此不把动态数量当成登录成功。
本机得到 `status=login_not_confirmed`，浏览器正常退出。

登录入口使用有界面的专用 Edge 配置，登录由本人完成。网页会话与官方
CLI 授权相互独立；之前 CLI 授权成功不能让这个专用浏览器自动登录。

## AstrBot 接入

本机已安装 AstrBot 桌面版 4.29.4，内置 Python 3.12.12。
已创建 `astrbot_plugin_social_probe`，位于 Playwright 分支。

测试使用实际安装的 SDK 导入插件，调用命令方法及浏览器子进程，
并检查非法路线、未配置目录两种情况。输出
`sdk_import=passed`、`command_handler=passed`，DOM 探测返回未确认登录。
测试事件对象仅实现 `plain_result`；没有测试真实消息分发、模型调用或桌面插件加载。

插件提供 `/weibo_probe dom`、`/weibo_probe bridge` 两个固定命令，
只返回状态摘要；不接受任意命令、没有发帖/评论/点赞入口，也不调用模型。
配置项 `project_root` 填本项目绝对路径。

插件 ZIP 放在本机 `runtime/packages/astrbot_plugin_social_probe.zip`，
可在 AstrBot 插件管理中使用本地插件安装入口加载；实际加载成功需检查日志，
并在聊天入口触发命令。当前没有宣称已安装或完成桌面聊天验证。
此前电脑控制工具拒绝操作 AstrBot，因此未通过该工具操作其界面。

## 本机运行

在项目根目录的 PowerShell 中：

```powershell
# 打开专用浏览器，本人扫码登录，完成后关闭该窗口
.\tools\browser-experiment.ps1 login

# 登录窗口关闭后，依次执行，避免共用配置被占用
.\tools\browser-experiment.ps1 dom
.\tools\browser-experiment.ps1 bridge
```

共享浏览器配置：`runtime/weibo-browser-profile/`。
可用环境变量 `SOCIAL_AGENT_PROFILE` 指向其他专用目录。
测试 JSON 与截图在各工作树的 `runtime/results/`，属于本地证据，
可能含账号内容，不加入 Git。不要同时启动两条路线或在登录窗口打开时运行探测。

在新的检出目录复现实验时，需先取得两个实验分支并建立同样的工作树：

```powershell
git worktree add runtime/experiments/playwright codex/experiment-playwright
git worktree add runtime/experiments/webmcp codex/experiment-webmcp
```

分别进入其 `experiments/playwright`、`experiments/webmcp` 目录，
使用 pnpm 运行 `pnpm install --frozen-lockfile --ignore-scripts`。
启动脚本可查找 PATH 或本机 Codex 内置 Node；其他电脑应安装 Node 18 以上，
并按依赖要求选择受支持版本。当前只验证 Windows 与系统 Edge。

## 下一步验收

1. 本人登录专用浏览器后，重新运行两条探测，验证登录判断与内容读取。
2. 在 AstrBot 加载插件，从聊天入口取得相同状态结果。
3. 自建执行器实现指定微博读取、草稿与预演，明确页面变化及超时的错误。
4. 确认测试文案与目标后，逐项验证发布、评论、点赞及结果查询。

暂不做定时自主互动，也没有执行真实发帖、评论或点赞。
