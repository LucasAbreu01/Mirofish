from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..services.ontology_service import OntologyService
from ..services.project_service import ProjectService
from ..services.task_service import TaskService
from ..services.zep_graph_service import ZepGraphService


projects_bp = Blueprint("projects", __name__)


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@projects_bp.get("")
def list_projects():
    return jsonify({"projects": ProjectService.list_projects()}), 200


@projects_bp.post("")
def create_project():
    try:
        files = request.files.getlist("files[]") or request.files.getlist("files")
        project = ProjectService.create_project(
            name=request.form.get("project_name", "").strip(),
            simulation_requirement=request.form.get("simulation_requirement", "").strip(),
            files=files,
        )
        return jsonify(project), 201
    except Exception as error:
        return _json_error(str(error))


@projects_bp.get("/<project_id>")
def get_project(project_id: str):
    try:
        return jsonify(ProjectService.get_project(project_id)), 200
    except Exception as error:
        return _json_error(str(error), 404)


@projects_bp.post("/<project_id>/ontology")
def generate_ontology(project_id: str):
    try:
        task_id = TaskService.run_async(
            "ontology",
            lambda current_task_id: OntologyService.generate_for_project(project_id, current_task_id),
            metadata={"project_id": project_id},
        )
        ProjectService.update_project(project_id, status="ontology_pending", latest_task_id=task_id, error=None)
        return jsonify({"task_id": task_id, "project_id": project_id}), 202
    except Exception as error:
        return _json_error(str(error))


@projects_bp.post("/<project_id>/graph")
def build_graph(project_id: str):
    try:
        task_id = TaskService.run_async(
            "graph_build",
            lambda current_task_id: ZepGraphService.build_graph_for_project(project_id, current_task_id),
            metadata={"project_id": project_id},
        )
        ProjectService.update_project(project_id, status="graph_pending", latest_task_id=task_id, error=None)
        return jsonify({"task_id": task_id, "project_id": project_id}), 202
    except Exception as error:
        return _json_error(str(error))


@projects_bp.get("/<project_id>/graph")
def get_project_graph(project_id: str):
    try:
        return jsonify(ZepGraphService.get_graph_snapshot(project_id)), 200
    except Exception as error:
        return _json_error(str(error), 404)
