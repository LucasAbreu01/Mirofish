from __future__ import annotations

from flask import Blueprint, jsonify

from ..services.task_service import TaskService


tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.get("")
def list_tasks():
    return jsonify({"tasks": TaskService.list_recent()}), 200


@tasks_bp.get("/<task_id>")
def get_task(task_id: str):
    try:
        return jsonify(TaskService.get_task(task_id)), 200
    except Exception as error:
        return jsonify({"error": str(error)}), 404
