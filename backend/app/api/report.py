from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_session, Simulation
from app.models.schemas import AgentProfile, ChatMessage, SimulationAction
from app.services.report_generator import generate_report, chat_with_report
from app.api.simulation import simulation_data, active_simulations
from app.utils.logger import get_logger

logger = get_logger("mirofish.api.report")

router = APIRouter()

# In-memory store for generated reports.
reports: dict[str, dict] = {}


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []


@router.post("/{sim_id}/generate")
async def generate_sim_report(
    sim_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Generate an analysis report for a completed simulation."""
    # Gather actions and agents from in-memory data or DB.
    actions: list[SimulationAction] = []
    agents: list[AgentProfile] = []
    scenario: str = ""

    engine = active_simulations.get(sim_id)
    data = simulation_data.get(sim_id)

    if engine:
        actions = engine.get_actions()
    if data:
        agents = data["agents"]
        scenario = data["scenario"]

    # Fall back to DB if not in memory.
    if not actions or not agents:
        sim = await session.get(Simulation, sim_id)
        if not sim:
            raise HTTPException(status_code=404, detail="Simulation not found")

        if not actions and sim.action_log_json:
            raw_actions = json.loads(sim.action_log_json)
            actions = [SimulationAction(**a) for a in raw_actions]

        if not agents and data:
            agents = data["agents"]
        elif not agents:
            raise HTTPException(
                status_code=400,
                detail="No agent data available for this simulation",
            )

        if not scenario:
            if sim.config_json:
                config = json.loads(sim.config_json)
                scenario = config.get("scenario", "")

    if not actions:
        raise HTTPException(
            status_code=400,
            detail="No actions recorded for this simulation",
        )

    report_text = await generate_report(actions, agents, scenario)
    generated_at = datetime.now(timezone.utc).isoformat()

    reports[sim_id] = {
        "simulation_id": sim_id,
        "report": report_text,
        "generated_at": generated_at,
    }

    # Persist to DB.
    sim = await session.get(Simulation, sim_id)
    if sim:
        sim.result_summary = report_text

    return {
        "simulation_id": sim_id,
        "report": report_text,
        "generated_at": generated_at,
    }


@router.post("/{sim_id}/chat")
async def chat_with_sim_report(
    sim_id: str,
    request: ChatRequest,
):
    """Chat with the report agent about a simulation's results."""
    report_data = reports.get(sim_id)
    if not report_data:
        raise HTTPException(
            status_code=404,
            detail="Report not found. Generate a report first.",
        )

    answer = await chat_with_report(
        report=report_data["report"],
        question=request.question,
        history=request.history,
    )

    return {"answer": answer}


@router.get("/{sim_id}")
async def get_report(
    sim_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a previously generated report."""
    report_data = reports.get(sim_id)
    if report_data:
        return report_data

    # Try loading from DB.
    sim = await session.get(Simulation, sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if not sim.result_summary:
        raise HTTPException(status_code=404, detail="No report generated yet")

    report_data = {
        "simulation_id": sim_id,
        "report": sim.result_summary,
        "generated_at": str(sim.created_at),
    }
    reports[sim_id] = report_data
    return report_data
