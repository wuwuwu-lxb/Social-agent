"""Load with the installed PluginManager, then call its registered model tool."""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
project = Path(__file__).resolve().parents[1]
backend = Path(sys.argv[1])
run_root = Path(tempfile.mkdtemp(prefix="plugin-sdk-", dir=project / "runtime"))
os.environ["ASTRBOT_ROOT"] = str(run_root)
sys.path.insert(0, str(backend))
sys.path.insert(0, str(run_root))
plugin_name = "astrbot_plugin_social_agent"
destination = run_root / "data/plugins" / plugin_name
shutil.copytree(project / plugin_name, destination,
                ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
node_root = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
subprocess.run([
    str(node_root / "bin/node.exe"),
    str(node_root / "node_modules/pnpm/bin/pnpm.mjs"),
    "install", "--offline", "--frozen-lockfile", "--ignore-scripts", "--no-optional",
    "--store-dir", str(project / "runtime/pnpm-store"),
], cwd=destination / "node", check=True, capture_output=True)
config_dir = run_root / "data/config"
config_dir.mkdir(parents=True, exist_ok=True)
(config_dir / f"{plugin_name}_config.json").write_text(json.dumps({
    "node_path": str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"),
    "browser_profile": str(project / "runtime/weibo-browser-profile"),
    "allowed_user_ids": ["local-test"],
}), encoding="utf-8")

from astrbot.core import astrbot_config, db_helper, sp
from astrbot.core.provider.register import llm_tools
from astrbot.core.star.star import star_registry
from astrbot.core.star.star_manager import PluginManager
from astrbot.core.star.star_handler import star_handlers_registry
from astrbot.core.star.filter.command import CommandFilter


class LocalEvent:
    unified_msg_origin = "local-test:private"

    def get_sender_id(self):
        return "local-test"

    def is_private_chat(self):
        return True

    def plain_result(self, text):
        return text


async def main():
    await db_helper.initialize()
    context = SimpleNamespace()
    manager = PluginManager(context, astrbot_config)
    loaded, error = await manager.load(specified_dir_name=plugin_name)
    assert loaded, error
    metadata = next(item for item in star_registry if item.name == plugin_name)
    assert metadata.star_cls is not None
    handlers = star_handlers_registry.get_handlers_by_module_name(metadata.module_path)
    assert any(item.handler_name == "weibo_confirm" for item in handlers)
    draft_handler = next(item for item in handlers if item.handler_name == "weibo_draft")
    command_filter = next(item for item in draft_handler.event_filters if isinstance(item, CommandFilter))
    assert command_filter.validate_and_convert_params(
        ["a", "text", "with", "spaces"], command_filter.handler_params,
    )["status"] == "a text with spaces"
    tool = next(item for item in llm_tools.func_list if item.name == "weibo_statuses_update")
    assert tool.handler is not None
    plugin = metadata.star_cls
    invalid = json.loads(await plugin.weibo_statuses_update(LocalEvent(), ""))
    assert invalid["status"] == "validation_error"
    denied_event = LocalEvent()
    denied_event.get_sender_id = lambda: "other-user"
    denied = json.loads(await plugin.weibo_statuses_update(denied_event, "test"))
    assert denied["status"] == "permission_denied"
    event = LocalEvent()
    text = "Social-agent plugin preview test. Do not publish."
    # Invoke the registry-bound callable, not just an independently created plugin.
    result = json.loads(await tool.handler(event, status=text))
    assert result["ok"] is True, result
    assert result["status"] == "preview_ready" and result["submitted"] is False
    assert result["publish_available"] is False
    stored = plugin.service.store.get(result["task_id"], event.get_sender_id(), event.unified_msg_origin)
    assert stored["content"] == text
    assert plugin.service.store.get(result["task_id"], "other-user", event.unified_msg_origin) is None
    assert plugin.service.store.get(result["task_id"], event.get_sender_id(), "other-session") is None
    replies = [item async for item in plugin.weibo_status(event, result["task_id"])]
    assert json.loads(replies[0])["task_id"] == result["task_id"]
    runner = plugin.service.runner

    class FailedBrowser:
        async def preview(self, status):
            raise OSError("simulated browser startup failure")

    plugin.service.runner = FailedBrowser()
    failed = json.loads(await tool.handler(event, status="浏览器故障时仍保存这条草稿。"))
    assert failed["draft_saved"] is True and failed["ok"] is False
    assert failed["status"] == "browser_error" and failed["submitted"] is False
    recent = plugin.service.store.recent(event.get_sender_id(), event.unified_msg_origin)
    assert recent[0]["task_id"] == failed["task_id"]
    assert plugin.service.store.recent("other-user", event.unified_msg_origin) == []
    assert plugin.service.store.recent(event.get_sender_id(), "other-session") == []
    listing = [item async for item in plugin.weibo_drafts(event)]
    assert failed["task_id"] in listing[0] and failed["content"] in listing[0]
    denied_listing = [item async for item in plugin.weibo_drafts(denied_event)]
    assert failed["task_id"] not in denied_listing[0]
    plugin.service.runner = runner
    plugin.config["allow_publish"] = True

    class FakePublisher:
        calls = 0

        async def publish(self, status):
            self.calls += 1
            return {"ok": True, "status": "succeeded", "submitted": True, "verified": True,
                    "post_id": "1234567890123456", "url": "https://weibo.com/detail/1234567890123456"}

    publisher = FakePublisher()
    plugin.service.runner = publisher
    confirmed = [item async for item in plugin.weibo_confirm(event, failed["task_id"])]
    repeated = [item async for item in plugin.weibo_confirm(event, failed["task_id"])]
    assert "正文读回核验通过" in confirmed[0]
    assert "没有再次提交" in repeated[0] and publisher.calls == 1
    plugin.service.runner = runner
    print(json.dumps({
        "plugin_manager_load": "passed",
        "registered_tool_call": "passed",
        "parameter_and_owner_checks": "passed",
        "command_text_parsing": "passed",
        "task_query": "passed",
        "draft_survives_browser_failure": "passed",
        "draft_list_and_isolation": "passed",
        "confirmation_command_with_fake_publisher": "passed",
        "preview": result,
        "scope": "isolated_plugin_manager_and_registry_not_live_wechat",
    }))
    await sp.flush()
    await db_helper.engine.dispose()


asyncio.run(main())
