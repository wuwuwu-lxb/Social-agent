import asyncio
import json
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


class DraftStore:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "tasks.sqlite3"
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS drafts ("
                "id TEXT PRIMARY KEY, owner TEXT NOT NULL, session TEXT NOT NULL, "
                "content TEXT NOT NULL, created_at TEXT NOT NULL, result TEXT NOT NULL)"
            )

    def save(self, owner: str, session: str, content: str, result: dict) -> str:
        task_id = "T" + uuid.uuid4().hex[:16]
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT INTO drafts VALUES (?, ?, ?, ?, ?, ?)",
                (task_id, owner, session, content, datetime.now(timezone.utc).isoformat(),
                 json.dumps(result, ensure_ascii=False)),
            )
        return task_id

    def get(self, task_id: str, owner: str, session: str) -> dict | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT id, content, result FROM drafts WHERE id=? AND owner=? AND session=?",
                (task_id, owner, session),
            ).fetchone()
        if not row:
            return None
        return {"task_id": row[0], "content": row[1], **json.loads(row[2])}

    def update_result(self, task_id: str, owner: str, session: str, result: dict):
        with sqlite3.connect(self.path) as db:
            db.execute(
                "UPDATE drafts SET result=? WHERE id=? AND owner=? AND session=?",
                (json.dumps(result, ensure_ascii=False), task_id, owner, session),
            )

    def recent(self, owner: str, session: str) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                "SELECT id, content, result FROM drafts WHERE owner=? AND session=? "
                "ORDER BY created_at DESC, rowid DESC LIMIT 5", (owner, session),
            ).fetchall()
        return [{"task_id": row[0], "content": row[1], **json.loads(row[2])} for row in rows]


class BrowserRunner:
    def __init__(self, package: Path, config: dict):
        self.package = package
        self.config = config
        self._lock = asyncio.Lock()

    def _node(self) -> str | None:
        configured = str(self.config.get("node_path", "")).strip()
        if configured:
            return configured if Path(configured).is_file() else None
        candidates = [
            shutil.which("node"),
            Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "nodejs/node.exe",
        ]
        return next((str(item) for item in candidates if item and Path(item).is_file()), None)

    async def preview(self, status: str) -> dict:
        node = self._node()
        profile = str(self.config.get("browser_profile", "")).strip()
        if not profile or not Path(profile).is_absolute():
            return {"ok": False, "status": "not_configured"}
        if not node or not (self.package / "node/node_modules").is_dir():
            return {"ok": False, "status": "missing_runtime"}
        request = {
            "operation": "statuses.update.preview",
            "status": status,
            "profile": profile,
        }
        async with self._lock:
            process = await asyncio.create_subprocess_exec(
                node, str(self.package / "node/executor.mjs"),
                cwd=self.package / "node",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(json.dumps(request).encode("utf-8")), 75,
                )
            except asyncio.TimeoutError:
                await self._stop(process)
                await process.communicate()
                return {"ok": False, "status": "timeout"}
            except BaseException:
                if process.returncode is None:
                    await self._stop(process)
                    await process.communicate()
                raise
        try:
            result = json.loads(stdout)
            if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
                raise ValueError("Invalid result")
        except (ValueError, UnicodeDecodeError):
            return {"ok": False, "status": "invalid_response"}
        if process.returncode != 0 and result.get("ok"):
            return {"ok": False, "status": "invalid_response"}
        return result

    @staticmethod
    async def _stop(process):
        if os.name == "nt":
            cleanup = await asyncio.create_subprocess_exec(
                "taskkill.exe", "/PID", str(process.pid), "/T", "/F",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await cleanup.wait()
        elif process.returncode is None:
            process.kill()


class DraftService:
    def __init__(self, store: DraftStore, runner: BrowserRunner):
        self.store = store
        self.runner = runner

    async def prepare(self, owner: str, session: str, status: str) -> dict:
        if not isinstance(status, str) or not status.strip() or len(status) > 140:
            return {"ok": False, "status": "validation_error",
                    "message": "This first version accepts 1-140 characters of text."}
        result = {"ok": False, "status": "preview_pending", "draft_saved": True,
                  "operation": "statuses update", "backend": "browser",
                  "submitted": False, "publish_available": False}
        task_id = await asyncio.to_thread(self.store.save, owner, session, status, result)
        try:
            preview = await self.runner.preview(status)
        except Exception:
            preview = {"ok": False, "status": "browser_error"}
        result.update(preview)
        result.update(draft_saved=True, submitted=False, publish_available=False)
        await asyncio.to_thread(self.store.update_result, task_id, owner, session, result)
        return {"task_id": task_id, "content": status, **result}
