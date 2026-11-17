import asyncio
import json
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from contextlib import closing, contextmanager
from pathlib import Path


class DraftStore:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "tasks.sqlite3"
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS drafts ("
                "id TEXT PRIMARY KEY, owner TEXT NOT NULL, session TEXT NOT NULL, "
                "content TEXT NOT NULL, created_at TEXT NOT NULL, result TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS publications ("
                "task_id TEXT PRIMARY KEY, result TEXT NOT NULL)"
            )

    @contextmanager
    def _connect(self):
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                yield db

    def save(self, owner: str, session: str, content: str, result: dict) -> str:
        task_id = "T" + uuid.uuid4().hex[:16]
        with self._connect() as db:
            db.execute(
                "INSERT INTO drafts VALUES (?, ?, ?, ?, ?, ?)",
                (task_id, owner, session, content, datetime.now(timezone.utc).isoformat(),
                 json.dumps(result, ensure_ascii=False)),
            )
        return task_id

    def get(self, task_id: str, owner: str, session: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT id, content, result FROM drafts WHERE id=? AND owner=? AND session=?",
                (task_id, owner, session),
            ).fetchone()
            publication = db.execute("SELECT result FROM publications WHERE task_id=?", (task_id,)).fetchone() if row else None
        if not row:
            return None
        result = {"task_id": row[0], "content": row[1], **json.loads(row[2])}
        if publication:
            result["publication"] = json.loads(publication[0])
        return result

    def claim_publication(self, task_id: str, owner: str, session: str) -> tuple[bool, dict]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT content FROM drafts WHERE id=? AND owner=? AND session=?",
                             (task_id, owner, session)).fetchone()
            if not row:
                return False, {"ok": False, "status": "not_found"}
            previous = db.execute("SELECT result FROM publications WHERE task_id=?", (task_id,)).fetchone()
            if previous:
                return False, {"task_id": task_id, "content": row[0], **json.loads(previous[0]), "reused": True}
            result = {"ok": False, "status": "executing", "submitted": None,
                      "confirmed_at": datetime.now(timezone.utc).isoformat(),
                      "visibility": "public", "ai_declaration_required": True}
            db.execute("INSERT INTO publications VALUES (?, ?)", (task_id, json.dumps(result)))
        return True, {"task_id": task_id, "content": row[0], **result}

    def finish_publication(self, task_id: str, result: dict):
        with self._connect() as db:
            db.execute("UPDATE publications SET result=? WHERE task_id=?",
                       (json.dumps(result, ensure_ascii=False), task_id))

    def update_result(self, task_id: str, owner: str, session: str, result: dict):
        with self._connect() as db:
            db.execute(
                "UPDATE drafts SET result=? WHERE id=? AND owner=? AND session=?",
                (json.dumps(result, ensure_ascii=False), task_id, owner, session),
            )

    def recent(self, owner: str, session: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, content, result FROM drafts WHERE owner=? AND session=? "
                "ORDER BY created_at DESC, rowid DESC LIMIT 5", (owner, session),
            ).fetchall()
        return [self.get(row[0], owner, session) for row in rows]


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
        return await self._run(status, "statuses.update.preview")

    async def publish(self, status: str) -> dict:
        return await self._run(status, "statuses.update.publish")

    async def _run(self, status: str, operation: str) -> dict:
        node = self._node()
        profile = str(self.config.get("browser_profile", "")).strip()
        if not profile or not Path(profile).is_absolute():
            return {"ok": False, "status": "not_configured", "submitted": False}
        if not node or not (self.package / "node/node_modules").is_dir():
            return {"ok": False, "status": "missing_runtime", "submitted": False}
        request = {
            "operation": operation,
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
                    process.communicate(json.dumps(request).encode("utf-8")), 110,
                )
            except asyncio.TimeoutError:
                await self._stop(process)
                await process.communicate()
                return {"ok": False, "status": "unknown" if operation.endswith(".publish") else "timeout",
                        "submitted": None if operation.endswith(".publish") else False}
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
            return {"ok": False, "status": "unknown" if operation.endswith(".publish") else "invalid_response",
                    "submitted": None if operation.endswith(".publish") else False}
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
        self.config = runner.config

    def can_publish(self, owner: str) -> bool:
        return self.config.get("allow_publish") is True and owner in {
            str(item) for item in self.config.get("allowed_user_ids", [])
        }

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
        result.update(draft_saved=True, submitted=False, publish_available=self.can_publish(owner))
        if self.can_publish(owner):
            result.update(confirmation_command=f"/weibo_confirm {task_id}", visibility="public",
                          ai_declaration="内容由AI生成")
        await asyncio.to_thread(self.store.update_result, task_id, owner, session, result)
        return {"task_id": task_id, "content": status, **result}

    async def confirm(self, owner: str, session: str, task_id: str) -> dict:
        if not self.can_publish(owner):
            return {"ok": False, "status": "publish_not_enabled"}
        claimed, task = await asyncio.to_thread(self.store.claim_publication, task_id, owner, session)
        if not claimed:
            return task
        result = {key: value for key, value in task.items() if key not in {"task_id", "content"}}
        try:
            output = await self.runner.publish(task["content"])
            result.update(output)
            if output.get("ok") and output.get("verified") and output.get("post_id") and output.get("url"):
                result["status"] = "succeeded"
            elif output.get("status") == "unknown" or output.get("submitted") is not False:
                result.update(ok=False, status="unknown")
            else:
                result.update(ok=False, status="failed", reason=output.get("reason", output.get("status")))
        except BaseException as error:
            result.update(ok=False, status="unknown", submitted=None, reason="executor_interrupted")
            await asyncio.shield(asyncio.to_thread(self.store.finish_publication, task_id, result))
            if not isinstance(error, Exception):
                raise
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        await asyncio.to_thread(self.store.finish_publication, task_id, result)
        return {"task_id": task_id, "content": task["content"], **result}
