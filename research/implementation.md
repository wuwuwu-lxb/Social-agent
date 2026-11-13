# 当前落地路线与 CLI 历史

更新日期：2026-11-12。当前主线是微博浏览器自动化。
CLI 授权和命令目录探索已完成，考虑额度限制不再作为接入前置条件。
两个浏览器分支和 AstrBot 探测插件已运行；2026-11-13 webmcp
路线已通过登录后真实读取和发帖预演，下一步是桌面聊天验证与任务封装，
详见 [分支实测](browser-experiments.md)。

以下保留早期 CLI 操作步骤作为历史参考，其中“下一步”描述不代表当前进度。

## 1. 已完成的本地准备

- 安装 `@weibo-ai/weibo-cli@0.9.8` 到 `tools/weibo-cli/`。
- `package.json` 固定直接依赖，`pnpm-lock.yaml` 锁定依赖树。
- 本机 Node `v24.22.1`，满足包声明的 Node `>=18`。
- 已运行版本、帮助、诊断与未登录命令查询，结果见 [验证记录](weibo-cli-validation.md)。

依赖目录被 Git 忽略，安装清单、锁文件和启动脚本保留。没有修改全局 Node 包，也未注册账号或购买服务。

## 2. 本地运行

在项目根目录的 PowerShell 中：

```powershell
.\tools\weibo-cli\weibo.ps1 version
.\tools\weibo-cli\weibo.ps1 --help
.\tools\weibo-cli\weibo.ps1 doctor --output json
```

启动脚本定位项目内的入口并传递参数，不修改 CLI 的登录存储。优先使用 PATH 中的 Node，再检查标准安装位置和当前用户的 Codex 内置 Node，验证版本至少为 18；无需手动修改系统 PATH。

重新安装依赖：有 pnpm 的环境可进入 `tools/weibo-cli` 后执行 `pnpm install --frozen-lockfile`；只有 npm 时可执行 `npm install --ignore-scripts`，但后者不使用 pnpm 锁文件，依赖树不保证完全一致。

## 3. 下一步：浏览器授权

```powershell
.\tools\weibo-cli\weibo.ps1 auth login --browser
```

由账号持有人在打开的官方页面完成登录和授权。CLI 默认使用用户目录的 `.weibo-cli/`，按自身实现使用系统凭据存储或本地加密文件，不应将这些文件放入仓库。不要在聊天中粘贴访问令牌。

登录后执行：

```powershell
.\tools\weibo-cli\weibo.ps1 doctor --output json
.\tools\weibo-cli\weibo.ps1 commands list --all --output json
.\tools\weibo-cli\weibo.ps1 commands list --available --output json
```

`doctor` 将登录、开发者认证和服务状态分别列出。未登录输出中的认证和服务为 false 不能证明账号未认证或没有套餐。

若要求开发者认证或付费服务，先查看实际要求与价格，再决定是否开通；不自动购买。

## 4. 登录后核实能力

从实际命令目录中找出读取、发布、评论、点赞的命令，使用：

```text
weibo.ps1 commands show <实际分组> <实际动作>
```

尖括号内容是待查询的占位符，不是可直接执行的命令。记录必填参数、权限、计费、返回格式、AI 内容声明和结果查询方式。实际写入命令确定前不猜测接口。

先完成一次只读请求，再使用明确的测试内容逐项尝试写入，并核对平台页面。收到成功响应和实际生效应分别记录。

## 5. 再接入 AstrBot

链路：聊天命令 → 插件业务逻辑 → 微博 CLI 适配器 → 官方服务 → 结果记录。

适配器只接受已验证的固定操作，通过 `asyncio.create_subprocess_exec` 启动 Node 和 CLI，以参数列表传值，解析实际 JSON 格式。不要把模型输出作为任意 Shell 命令执行。

第一版实现草稿、任务编号、确认与状态查询，再增加人设和近期互动记忆。超时可能已经产生写入，应标记结果未知并核对，不直接重试发布。

## 6. 接入完成标准

1. CLI 能查询当前账号状态和可用命令。
2. 至少一个真实只读调用成功。
3. 每个写入动作都有真实命令说明和平台结果证据。
4. AstrBot 触发固定动作并返回真实结果。
5. 最后验证重复触发、登录失效和超时。
