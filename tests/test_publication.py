"""Publication orchestration tests. No real platform writes."""
import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "astrbot_plugin_social_agent/social_agent/service.py"
spec = importlib.util.spec_from_file_location("publication_service", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Runner:
    config = {"allow_publish": True, "allowed_user_ids": ["owner"]}

    def __init__(self, result=None):
        self.calls = 0
        self.result = result or {"ok": True, "status": "succeeded", "submitted": True,
                                 "verified": True, "post_id": "1234567890123456",
                                 "url": "https://weibo.com/detail/1234567890123456"}

    async def preview(self, text):
        return {"ok": True, "status": "preview_ready", "submitted": False}

    async def publish(self, text):
        self.calls += 1
        await asyncio.sleep(0.02)
        return self.result


class PublicationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = module.DraftStore(Path(self.tmp.name))
        self.runner = Runner()
        self.service = module.DraftService(self.store, self.runner)
        self.draft = await self.service.prepare("owner", "private", "测试文案")

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_concurrent_confirm_and_restart_submit_once(self):
        task_id = self.draft["task_id"]
        outputs = await asyncio.gather(*[self.service.confirm("owner", "private", task_id) for _ in range(3)])
        self.assertEqual(self.runner.calls, 1)
        self.assertTrue(any(item["status"] == "succeeded" for item in outputs))
        other = module.DraftService(module.DraftStore(Path(self.tmp.name)), self.runner)
        repeated = await other.confirm("owner", "private", task_id)
        self.assertEqual(repeated["status"], "succeeded")
        self.assertTrue(repeated["reused"])
        self.assertEqual(self.runner.calls, 1)
        self.assertEqual(self.store.get(task_id, "owner", "private")["publication"]["status"], "succeeded")

    async def test_permission_and_ownership(self):
        task_id = self.draft["task_id"]
        denied = await self.service.confirm("other", "private", task_id)
        self.assertEqual(denied["status"], "publish_not_enabled")
        foreign = await self.service.confirm("owner", "other-session", task_id)
        self.assertEqual(foreign["status"], "not_found")
        self.service.config = {"allow_publish": True, "allowed_user_ids": []}
        disabled = await self.service.confirm("owner", "private", task_id)
        self.assertEqual(disabled["status"], "publish_not_enabled")
        self.assertEqual(self.runner.calls, 0)

    async def test_unknown_and_failed_never_retry(self):
        for output in [
            {"ok": False, "status": "unknown", "submitted": None},
            {"ok": False, "status": "failed", "submitted": False, "reason": "platform_rejected"},
            {"ok": True, "status": "succeeded", "submitted": True},
        ]:
            draft = await self.service.prepare("owner", "private", "另一条测试")
            self.runner.result = output
            first = await self.service.confirm("owner", "private", draft["task_id"])
            before = self.runner.calls
            repeated = await self.service.confirm("owner", "private", draft["task_id"])
            self.assertEqual(self.runner.calls, before)
            self.assertIn(first["status"], {"unknown", "failed"})
            self.assertEqual(repeated["status"], first["status"])

    async def test_process_interruption_keeps_claim(self):
        task_id = self.draft["task_id"]
        claimed, _ = self.store.claim_publication(task_id, "owner", "private")
        self.assertTrue(claimed)
        restarted = module.DraftService(module.DraftStore(Path(self.tmp.name)), self.runner)
        result = await restarted.confirm("owner", "private", task_id)
        self.assertEqual(result["status"], "executing")
        self.assertEqual(self.runner.calls, 0)


if __name__ == "__main__":
    unittest.main()
