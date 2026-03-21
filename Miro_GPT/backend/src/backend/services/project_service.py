from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from ..config import settings
from ..db import session_scope
from ..models.db_models import ProjectRecord, ReportRecord, SimulationRecord
from ..utils.file_parser import allowed_file, extract_text
from ..utils.id_factory import prefixed_id
from ..utils.json_tools import read_json, write_json


class ProjectService:
    @staticmethod
    def create_project(
        *,
        name: str,
        simulation_requirement: str,
        files: list[FileStorage],
    ) -> dict[str, Any]:
        if not files:
            raise ValueError("At least one file is required.")

        project_id = prefixed_id("proj")
        project_dir = ProjectService.project_dir(project_id)
        raw_dir = project_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        text_chunks: list[str] = []
        saved_files: list[str] = []
        for upload in files:
            filename = secure_filename(upload.filename or "")
            if not filename:
                continue
            if not allowed_file(filename, settings.allowed_extensions):
                raise ValueError(f"Unsupported file type: {filename}")
            destination = raw_dir / filename
            upload.save(destination)
            saved_files.append(filename)
            extracted = extract_text(destination).strip()
            if extracted:
                text_chunks.append(f"# File: {filename}\n\n{extracted}")

        if not saved_files:
            raise ValueError("No valid files were uploaded.")

        full_text = "\n\n".join(text_chunks).strip()
        if len(full_text) < 40:
            raise ValueError("Extracted text is too short to analyze.")

        extracted_path = project_dir / "extracted_text.txt"
        extracted_path.write_text(full_text, encoding="utf-8")

        with session_scope() as session:
            record = ProjectRecord(
                project_id=project_id,
                name=name.strip() or project_id,
                simulation_requirement=simulation_requirement.strip(),
                status="uploaded",
                extracted_text_path=str(extracted_path),
            )
            session.add(record)

        return ProjectService.get_project(project_id)

    @staticmethod
    def list_projects(limit: int = 50) -> list[dict[str, Any]]:
        with session_scope() as session:
            records = session.scalars(
                select(ProjectRecord).order_by(ProjectRecord.updated_at.desc()).limit(limit)
            ).all()
            return [ProjectService.serialize_project(record, session=session) for record in records]

    @staticmethod
    def get_project(project_id: str) -> dict[str, Any]:
        with session_scope() as session:
            record = session.get(ProjectRecord, project_id)
            if record is None:
                raise ValueError(f"Project {project_id} not found.")
            return ProjectService.serialize_project(record, session=session)

    @staticmethod
    def get_record(project_id: str, session: Any | None = None) -> ProjectRecord:
        if session is not None:
            record = session.get(ProjectRecord, project_id)
            if record is None:
                raise ValueError(f"Project {project_id} not found.")
            return record
        with session_scope() as owned_session:
            record = owned_session.get(ProjectRecord, project_id)
            if record is None:
                raise ValueError(f"Project {project_id} not found.")
            owned_session.expunge(record)
            return record

    @staticmethod
    def serialize_project(record: ProjectRecord, session: Any | None = None) -> dict[str, Any]:
        close_after = False
        if session is None:
            close_after = True
            session_cm = session_scope()
            session = session_cm.__enter__()
        try:
            simulation_count = session.scalar(
                select(func.count())
                .select_from(SimulationRecord)
                .where(SimulationRecord.project_id == record.project_id)
            )
            report_count = session.scalar(
                select(func.count())
                .select_from(ReportRecord)
                .join(SimulationRecord, ReportRecord.simulation_id == SimulationRecord.simulation_id)
                .where(SimulationRecord.project_id == record.project_id)
            )
        except Exception:
            simulation_count = None
            report_count = None

        payload = {
            "project_id": record.project_id,
            "name": record.name,
            "status": record.status,
            "simulation_requirement": record.simulation_requirement,
            "graph_id": record.graph_id,
            "analysis_summary": record.analysis_summary,
            "has_ontology": bool(record.ontology_json),
            "ontology": read_json(ProjectService.ontology_path(record.project_id), default=None),
            "graph_snapshot": read_json(ProjectService.graph_snapshot_path(record.project_id), default=None),
            "error": record.error,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            "simulation_count": simulation_count,
            "report_count": report_count,
        }
        if close_after:
            session_cm.__exit__(None, None, None)
        return payload

    @staticmethod
    def update_project(project_id: str, **fields: Any) -> None:
        with session_scope() as session:
            record = ProjectService.get_record(project_id, session=session)
            for key, value in fields.items():
                setattr(record, key, value)

    @staticmethod
    def save_ontology(project_id: str, payload: dict[str, Any]) -> Path:
        path = ProjectService.ontology_path(project_id)
        write_json(path, payload)
        ProjectService.update_project(
            project_id,
            ontology_json=ProjectService._dump(payload),
            analysis_summary=payload.get("analysis_summary", ""),
            status="ontology_ready",
            error=None,
        )
        return path

    @staticmethod
    def save_graph_snapshot(project_id: str, snapshot: dict[str, Any], graph_id: str) -> Path:
        path = ProjectService.graph_snapshot_path(project_id)
        write_json(path, snapshot)
        ProjectService.update_project(
            project_id,
            graph_id=graph_id,
            graph_snapshot_path=str(path),
            status="graph_ready",
            error=None,
        )
        return path

    @staticmethod
    def load_extracted_text(project_id: str) -> str:
        path = ProjectService.project_dir(project_id) / "extracted_text.txt"
        if not path.exists():
            raise ValueError("Extracted text file is missing.")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def load_ontology(project_id: str) -> dict[str, Any]:
        ontology = read_json(ProjectService.ontology_path(project_id), default=None)
        if ontology is None:
            raise ValueError("Ontology has not been generated yet.")
        return ontology

    @staticmethod
    def project_dir(project_id: str) -> Path:
        return settings.projects_dir / project_id

    @staticmethod
    def ontology_path(project_id: str) -> Path:
        return ProjectService.project_dir(project_id) / "ontology.json"

    @staticmethod
    def graph_snapshot_path(project_id: str) -> Path:
        return ProjectService.project_dir(project_id) / "graph_snapshot.json"

    @staticmethod
    def simulation_dir(project_id: str, simulation_id: str) -> Path:
        path = ProjectService.project_dir(project_id) / "simulations" / simulation_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def report_dir(project_id: str, report_id: str) -> Path:
        path = ProjectService.project_dir(project_id) / "reports" / report_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _dump(payload: Any) -> str:
        import json

        return json.dumps(payload)
