from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from sqlalchemy import select

from ..db import session_scope
from ..models.db_models import TaskRecord
from ..utils.id_factory import prefixed_id
from ..utils.logger import get_logger


logger = get_logger("miro_gpt.task_service")


class TaskService:
    _threads: dict[str, threading.Thread] = {}
    _lock = threading.Lock()

    @classmethod
    def create_task(cls, kind: str, metadata: dict[str, Any] | None = None) -> str:
        task_id = prefixed_id("task")
        with session_scope() as session:
            session.add(
                TaskRecord(
                    task_id=task_id,
                    kind=kind,
                    status="pending",
                    progress=0,
                    message="Task queued.",
                    metadata_json=cls._dump(metadata or {}),
                )
            )
        return task_id

    @classmethod
    def run_async(
        cls,
        kind: str,
        worker: Callable[[str], Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        task_id = cls.create_task(kind=kind, metadata=metadata)

        def _runner() -> None:
            try:
                cls.update_task(task_id, status="processing", progress=3, message="Task started.")
                result = worker(task_id)
                if cls.get_task(task_id)["status"] != "failed":
                    cls.complete_task(task_id, result=result)
            except Exception as error:  # pragma: no cover
                logger.exception("Task %s failed", task_id)
                cls.fail_task(task_id, str(error))
            finally:
                with cls._lock:
                    cls._threads.pop(task_id, None)

        thread = threading.Thread(target=_runner, daemon=True, name=f"task-{task_id}")
        with cls._lock:
            cls._threads[task_id] = thread
        thread.start()
        return task_id

    @classmethod
    def update_task(
        cls,
        task_id: str,
        *,
        status: str | None = None,
        progress: int | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
        result: Any | None = None,
        error: str | None = None,
    ) -> None:
        with session_scope() as session:
            record = session.get(TaskRecord, task_id)
            if record is None:
                raise ValueError(f"Task {task_id} not found.")
            if status is not None:
                record.status = status
            if progress is not None:
                record.progress = max(0, min(100, int(progress)))
            if message is not None:
                record.message = message
            if metadata is not None:
                current = cls._load(record.metadata_json)
                current.update(metadata)
                record.metadata_json = cls._dump(current)
            if result is not None:
                record.result_json = cls._dump(result)
            if error is not None:
                record.error = error

    @classmethod
    def complete_task(
        cls,
        task_id: str,
        *,
        result: Any | None = None,
        message: str = "Task completed.",
    ) -> None:
        cls.update_task(
            task_id,
            status="completed",
            progress=100,
            message=message,
            result=result,
            error=None,
        )

    @classmethod
    def fail_task(cls, task_id: str, error: str, *, message: str = "Task failed.") -> None:
        cls.update_task(
            task_id,
            status="failed",
            progress=100,
            message=message,
            error=error,
        )

    @classmethod
    def get_task(cls, task_id: str) -> dict[str, Any]:
        with session_scope() as session:
            record = session.get(TaskRecord, task_id)
            if record is None:
                raise ValueError(f"Task {task_id} not found.")
            return cls._serialize(record)

    @classmethod
    def list_recent(cls, limit: int = 50) -> list[dict[str, Any]]:
        with session_scope() as session:
            records = session.scalars(
                select(TaskRecord).order_by(TaskRecord.created_at.desc()).limit(limit)
            ).all()
            return [cls._serialize(record) for record in records]

    @classmethod
    def recover_incomplete_tasks(cls) -> None:
        with session_scope() as session:
            pending = session.scalars(
                select(TaskRecord).where(TaskRecord.status.in_(("pending", "processing")))
            ).all()
            for record in pending:
                record.status = "failed"
                record.progress = 100
                record.message = "Task did not complete because the backend restarted."
                record.error = "Interrupted by backend restart."

    @staticmethod
    def progress_callback(task_id: str, start: int = 0, end: int = 100) -> Callable[[float, str], None]:
        def _callback(progress: float, message: str) -> None:
            mapped = start + ((end - start) * max(0.0, min(1.0, progress)))
            TaskService.update_task(task_id, progress=int(mapped), message=message)

        return _callback

    @classmethod
    def _serialize(cls, record: TaskRecord) -> dict[str, Any]:
        return {
            "task_id": record.task_id,
            "kind": record.kind,
            "status": record.status,
            "progress": record.progress,
            "message": record.message,
            "metadata": cls._load(record.metadata_json),
            "result": cls._load(record.result_json),
            "error": record.error,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }

    @staticmethod
    def _dump(payload: Any) -> str:
        import json

        return json.dumps(payload or {})

    @staticmethod
    def _load(payload: str | None) -> Any:
        import json

        if not payload:
            return None
        return json.loads(payload)
