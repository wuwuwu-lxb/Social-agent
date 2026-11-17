import asyncio
import json
from pathlib import Path

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools
from astrbot.core.star.filter.command import GreedyStr

from .social_agent.service import BrowserRunner, DraftService, DraftStore


class SocialAgentPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config or {}
        self.package = Path(__file__).resolve().parent
        self.service = None

    async def initialize(self):
        directory = StarTools.get_data_dir("astrbot_plugin_social_agent")
        store = await asyncio.to_thread(DraftStore, directory)
        self.service = DraftService(store, BrowserRunner(self.package, self.config))

    def _identity(self, event: AstrMessageEvent) -> tuple[str, str] | None:
        owner = event.get_sender_id()
        session = event.unified_msg_origin
        allowed = self.config.get("allowed_user_ids", [])
        if not owner or not session or not event.is_private_chat():
            return None
        if allowed and owner not in {str(item) for item in allowed}:
            return None
        return owner, session

    async def _prepare(self, event: AstrMessageEvent, status: str) -> dict:
        identity = self._identity(event)
        if identity is None:
            return {"ok": False, "status": "permission_denied",
                    "message": "Use an allowed private chat."}
        if self.service is None:
            return {"ok": False, "status": "not_initialized"}
        try:
            return await self.service.prepare(*identity, status)
        except Exception:
            self.logger.exception("Weibo draft preview failed")
            return {"ok": False, "status": "internal_error"}

    @filter.llm_tool(name="weibo_statuses_update")
    async def weibo_statuses_update(self, event: AstrMessageEvent, status: str) -> str:
        """Prepare a Weibo text draft and preview. This tool never submits it.

        Use when the user asks to draft or publish a Weibo post. This version only
        saves a draft and checks the composer without clicking Send. Tell the user
        the task ID and preview result and explicitly say it has NOT been published.
        When publish_available is true, show the exact draft, public visibility,
        the AI-generated declaration, task ID and confirmation_command to the user.
        The user must personally send that command to publish. Do not confirm on
        their behalf or claim success based on a preview.
        A draft is saved before browser access. If draft_saved is true but ok is
        false, report that the draft exists and the browser preview failed.
        Only plain text of 1-140 characters is supported; no visibility, media or
        other official CLI options are supported.

        Args:
            status(string): Exact Weibo text to preview, 1-140 characters.
        """
        return json.dumps(await self._prepare(event, status), ensure_ascii=False)

    @filter.command("weibo_draft")
    async def weibo_draft(self, event: AstrMessageEvent, status: GreedyStr):
        result = await self._prepare(event, status)
        if result.get("ok"):
            message = (
                f"微博草稿预演通过，尚未发布。\n任务：{result['task_id']}\n"
                f"文案：{result['content']}"
            )
        else:
            message = f"未发布。草稿预演未通过：{result['status']}"
            if result.get("draft_saved"):
                message += f"\n草稿已保存，浏览器预演失败不会丢失文案。\n文案：{result['content']}"
            if result.get("task_id"):
                message += f"\n任务：{result['task_id']}"
        if result.get("publish_available"):
            message += ("\n发布设置：公开，内容由AI生成。\n确认以上文案后，由你发送：\n"
                        f"{result['confirmation_command']}")
        yield event.plain_result(message)

    @filter.command("weibo_confirm")
    async def weibo_confirm(self, event: AstrMessageEvent, task_id: str):
        identity = self._identity(event)
        if identity is None or self.service is None:
            yield event.plain_result("无权发布或插件尚未初始化。")
            return
        result = await self.service.confirm(*identity, task_id)
        if result.get("status") == "succeeded":
            message = f"微博已发布，正文读回核验通过。\n任务：{task_id}\n{result['url']}"
        elif result.get("status") in {"unknown", "executing"}:
            message = f"任务：{task_id}\n发布结果未知或仍在执行，请先在微博核对，不要重新创建同文任务发布。"
            if result.get("url"):
                message += f"\n待核对链接：{result['url']}"
        else:
            message = f"发布未成功：{result.get('reason', result['status'])}\n任务：{task_id}"
        if result.get("reused"):
            message += "\n本次仅返回已有结果，没有再次提交。"
        yield event.plain_result(message)

    @filter.command("weibo_drafts")
    async def weibo_drafts(self, event: AstrMessageEvent):
        identity = self._identity(event)
        if identity is None or self.service is None:
            yield event.plain_result("无权查询或插件尚未初始化。")
            return
        rows = await asyncio.to_thread(self.service.store.recent, *identity)
        if not rows:
            yield event.plain_result("当前会话还没有草稿。")
            return
        message = "最近 5 条任务：\n" + "\n\n".join(
            f"{row['task_id']}\n{row['content']}\n预演状态：{row['status']}\n"
            f"发布状态：{row.get('publication', {}).get('status', '尚未提交')}" for row in rows
        )
        yield event.plain_result(message)

    @filter.command("weibo_status")
    async def weibo_status(self, event: AstrMessageEvent, task_id: str):
        identity = self._identity(event)
        if identity is None or self.service is None:
            yield event.plain_result("无权查询或插件尚未初始化。")
            return
        result = await asyncio.to_thread(self.service.store.get, task_id, *identity)
        yield event.plain_result(
            json.dumps(result, ensure_ascii=False) if result else "任务不存在或不属于当前会话。"
        )
