from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..db import session_scope
from ..models.db_models import SimulationRecord
from ..services.simulation_service import SimulationService
from ..services.task_service import TaskService


simulations_bp = Blueprint("simulations", __name__)


def _json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


@simulations_bp.post("")
def create_simulation():
    try:
        payload = request.get_json(silent=True) or {}
        simulation = SimulationService.create_simulation(
            project_id=payload.get("project_id", ""),
            entity_limit=payload.get("entity_limit"),
            rounds=payload.get("rounds"),
            active_agents_per_round=payload.get("active_agents_per_round"),
            temperature=float(payload.get("temperature", 0.35)),
        )
        return jsonify(simulation), 201
    except Exception as error:
        return _json_error(str(error))


@simulations_bp.get("/<simulation_id>")
def get_simulation(simulation_id: str):
    try:
        return jsonify(SimulationService.get_simulation(simulation_id)), 200
    except Exception as error:
        return _json_error(str(error), 404)


@simulations_bp.post("/<simulation_id>/prepare")
def prepare_simulation(simulation_id: str):
    try:
        return jsonify(SimulationService.prepare_simulation(simulation_id)), 200
    except Exception as error:
        return _json_error(str(error))


@simulations_bp.post("/<simulation_id>/run")
def run_simulation(simulation_id: str):
    try:
        task_id = TaskService.run_async(
            "simulation_run",
            lambda current_task_id: SimulationService.run_simulation(simulation_id, current_task_id),
            metadata={"simulation_id": simulation_id},
        )
        with session_scope() as session:
            record = session.get(SimulationRecord, simulation_id)
            if record is None:
                raise ValueError(f"Simulation {simulation_id} not found.")
            record.status = "running"
            record.latest_task_id = task_id
        return jsonify({"task_id": task_id, "simulation_id": simulation_id}), 202
    except Exception as error:
        return _json_error(str(error))


@simulations_bp.get("/<simulation_id>/feed")
def get_feed(simulation_id: str):
    try:
        return jsonify(SimulationService.get_feed(simulation_id)), 200
    except Exception as error:
        return _json_error(str(error), 404)
