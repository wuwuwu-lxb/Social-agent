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
        """Prepare a Weibo text draft and run a browser preview. NEVER publishes.

        Use when the user asks to draft or publish a Weibo post. This version only
        saves a draft and checks the composer without clicking Send. Tell the user
        the task ID and preview result and explicitly say it has NOT been published.
        Actual publishing and confirmation are unavailable in this version.
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
                f"文案：{result['content']}\n当前版本暂不支持确认发布。"
            )
        else:
            message = f"未发布。草稿预演未通过：{result['status']}"
            if result.get("draft_saved"):
                message += f"\n草稿已保存，浏览器预演失败不会丢失文案。\n文案：{result['content']}"
            if result.get("task_id"):
                message += f"\n任务：{result['task_id']}"
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
        message = "最近 5 条草稿（均未发布）：\n" + "\n\n".join(
            f"{row['task_id']}\n{row['content']}\n预演状态：{row['status']}" for row in rows
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
