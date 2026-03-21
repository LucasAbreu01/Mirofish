from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..db import session_scope
from ..models.db_models import ReportRecord
from ..services.report_service import ReportService
from ..services.task_service import TaskService


reports_bp = Blueprint("reports", __name__)


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@reports_bp.post("")
def create_report():
    try:
        payload = request.get_json(silent=True) or {}
        created = ReportService.create_report(payload.get("simulation_id", ""))
        task_id = TaskService.run_async(
            "report_generation",
            lambda current_task_id: ReportService.generate_report(created["report_id"], current_task_id),
            metadata={
                "report_id": created["report_id"],
                "simulation_id": payload.get("simulation_id", ""),
            },
        )
        with session_scope() as session:
            record = session.get(ReportRecord, created["report_id"])
            if record is None:
                raise ValueError(f"Report {created['report_id']} not found.")
            record.status = "running"
            record.latest_task_id = task_id
        return jsonify({"report_id": created["report_id"], "task_id": task_id}), 202
    except Exception as error:
        return _json_error(str(error))


@reports_bp.get("/<report_id>")
def get_report(report_id: str):
    try:
        return jsonify(ReportService.get_report(report_id)), 200
    except Exception as error:
        return _json_error(str(error), 404)
