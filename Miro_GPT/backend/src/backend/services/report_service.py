from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..config import settings
from ..db import session_scope
from ..models.db_models import ReportRecord, SimulationRecord
from ..subagents.critic import CriticSubagent
from ..subagents.research import ResearchSubagent
from ..subagents.writer import WriterSubagent
from ..utils.id_factory import prefixed_id
from ..utils.json_tools import read_json, read_jsonl, write_json
from .project_service import ProjectService
from .simulation_service import SimulationService
from .zep_graph_service import ZepGraphService


class ReportService:
    @staticmethod
    def create_report(simulation_id: str) -> dict[str, Any]:
        simulation = SimulationService.get_simulation(simulation_id)
        report_id = prefixed_id("rep")
        project_dir = ProjectService.report_dir(simulation["project_id"], report_id)
        with session_scope() as session:
            session.add(
                ReportRecord(
                    report_id=report_id,
                    simulation_id=simulation_id,
                    status="pending",
                    markdown_path=str(project_dir / "full_report.md"),
                )
            )
        return ReportService.get_report(report_id)

    @staticmethod
    def generate_report(report_id: str, task_id: str) -> dict[str, Any]:
        report = ReportService._get_record(report_id)
        simulation = SimulationService.get_simulation(report.simulation_id)
        project = ProjectService.get_project(simulation["project_id"])
        simulation_dir = ProjectService.simulation_dir(project["project_id"], simulation["simulation_id"])
        events = read_jsonl(simulation_dir / "events.jsonl")
        if not events:
            raise ValueError("Run the simulation before generating a report.")

        from .task_service import TaskService

        TaskService.update_task(task_id, progress=10, message="Loading research context.")
        research_payload = read_json(simulation_dir / "research_brief.json", default=None)
        if research_payload is None:
            research = ResearchSubagent.build(
                graph_id=simulation["graph_id"],
                simulation_requirement=project["simulation_requirement"],
                project_snapshot=ZepGraphService.get_graph_snapshot(project["project_id"]),
            )
            research_payload = research.model_dump()
            write_json(simulation_dir / "research_brief.json", research_payload)

        analytics = SimulationService.analytics_from_events(events)
        analytics["round_summaries"] = SimulationService.get_feed(simulation["simulation_id"])["round_summaries"]

        TaskService.update_task(task_id, progress=36, message="Writing report draft.")
        draft = WriterSubagent.write(
            requirement=project["simulation_requirement"],
            research_brief=research_payload,
            analytics=analytics,
        )
        TaskService.update_task(task_id, progress=66, message="Running critic pass.")
        critique = CriticSubagent.review(
            requirement=project["simulation_requirement"],
            draft=draft,
        )
        if critique.needs_revision and settings.critic_max_passes > 0:
            TaskService.update_task(task_id, progress=84, message="Applying revision pass.")
            draft = WriterSubagent.write(
                requirement=project["simulation_requirement"],
                research_brief=research_payload,
                analytics=analytics,
                critique=critique.revision_instructions,
            )

        report_dir = ProjectService.report_dir(project["project_id"], report_id)
        markdown_path = report_dir / "full_report.md"
        markdown_path.write_text(draft.markdown_content, encoding="utf-8")
        write_json(report_dir / "report.json", draft.model_dump())
        write_json(report_dir / "critique.json", critique.model_dump())

        with session_scope() as session:
            db_record = session.get(ReportRecord, report_id)
            if db_record is None:
                raise ValueError(f"Report {report_id} not found.")
            db_record.status = "completed"
            db_record.title = draft.title
            db_record.summary = draft.summary
            db_record.sections_json = ReportService._dump([section.model_dump() for section in draft.sections])
            db_record.markdown_path = str(markdown_path)
            db_record.completed_at = datetime.utcnow()
            db_record.error = None

        return {
            "report_id": report_id,
            "title": draft.title,
            "summary": draft.summary,
            "sections": [section.model_dump() for section in draft.sections],
            "markdown_path": str(markdown_path),
        }

    @staticmethod
    def get_report(report_id: str) -> dict[str, Any]:
        with session_scope() as session:
            record = session.get(ReportRecord, report_id)
            if record is None:
                raise ValueError(f"Report {report_id} not found.")
            return ReportService.serialize_record(record)

    @staticmethod
    def list_reports_for_project(project_id: str) -> list[dict[str, Any]]:
        with session_scope() as session:
            rows = session.scalars(
                select(ReportRecord)
                .join(SimulationRecord, ReportRecord.simulation_id == SimulationRecord.simulation_id)
                .where(SimulationRecord.project_id == project_id)
                .order_by(ReportRecord.created_at.desc())
            ).all()
            return [ReportService.serialize_record(row) for row in rows]

    @staticmethod
    def serialize_record(record: ReportRecord) -> dict[str, Any]:
        sections = ReportService._load(record.sections_json) or []
        markdown_content = ""
        if record.markdown_path:
            markdown_path = Path(record.markdown_path)
            if markdown_path.exists():
                markdown_content = markdown_path.read_text(encoding="utf-8")
        return {
            "report_id": record.report_id,
            "simulation_id": record.simulation_id,
            "status": record.status,
            "title": record.title,
            "summary": record.summary,
            "sections": sections,
            "markdown_content": markdown_content,
            "latest_task_id": record.latest_task_id,
            "error": record.error,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        }

    @staticmethod
    def _get_record(report_id: str) -> ReportRecord:
        with session_scope() as session:
            record = session.get(ReportRecord, report_id)
            if record is None:
                raise ValueError(f"Report {report_id} not found.")
            session.expunge(record)
            return record

    @staticmethod
    def _dump(payload: Any) -> str:
        import json

        return json.dumps(payload)

    @staticmethod
    def _load(payload: str | None) -> Any:
        import json

        if not payload:
            return []
        return json.loads(payload)
