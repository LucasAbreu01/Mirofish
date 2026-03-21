from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.models.database import get_session, async_session_factory, Project, Simulation
from app.models.schemas import AgentProfile, SimulationConfig
from app.services.agent_generator import generate_agents
from app.services.knowledge_graph import KnowledgeGraphManager
from app.services.simulation_engine import SimulationEngine
from app.utils.logger import get_logger

logger = get_logger("mirofish.api.simulation")

router = APIRouter()

# In-memory stores for active simulations.
active_simulations: dict[str, SimulationEngine] = {}
simulation_data: dict[str, dict] = {}


@router.post("/create")
async def create_simulation(
    config: SimulationConfig,
    session: AsyncSession = Depends(get_session),
):
    """Create a new simulation from a project's knowledge graph."""
    project = await session.get(Project, config.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.graph_json:
        raise HTTPException(status_code=400, detail="Project has no knowledge graph")

    graph = KnowledgeGraphManager.from_json(project.graph_json)

    scenario = config.scenario or project.scenario or ""
    agents = await generate_agents(graph, config.agent_count, scenario)

    sim_id = str(uuid.uuid4())
    sim = Simulation(
        id=sim_id,
        project_id=config.project_id,
        config_json=json.dumps(config.model_dump()),
        status="created",
    )
    session.add(sim)
    await session.flush()

    simulation_data[sim_id] = {
        "agents": agents,
        "graph": graph,
        "scenario": scenario,
        "config": config.model_dump(),
    }

    return {
        "simulation_id": sim_id,
        "agents": [a.model_dump() for a in agents],
        "config": config.model_dump(),
    }


@router.get("/{sim_id}/agents")
async def get_agents(sim_id: str):
    """Get agent profiles for a simulation."""
    data = simulation_data.get(sim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return {"agents": [a.model_dump() for a in data["agents"]]}


@router.put("/{sim_id}/agents/{agent_name}")
async def update_agent(
    sim_id: str,
    agent_name: str,
    agent: AgentProfile,
):
    """Edit an agent profile before running the simulation."""
    data = simulation_data.get(sim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Simulation not found")

    agents: list[AgentProfile] = data["agents"]
    for i, a in enumerate(agents):
        if a.name == agent_name:
            agents[i] = agent
            return {"agent": agent.model_dump()}

    raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")


@router.get("/{sim_id}/run")
async def run_simulation(sim_id: str):
    """Start a simulation and stream events via SSE."""
    data = simulation_data.get(sim_id)
    if not data:
        raise HTTPException(status_code=404, detail="Simulation not found")

    agents: list[AgentProfile] = data["agents"]
    scenario: str = data["scenario"]
    graph: KnowledgeGraphManager = data["graph"]
    config: dict = data["config"]
    num_rounds: int = config.get("num_rounds", 10)

    engine = SimulationEngine(
        agents=agents,
        scenario=scenario,
        graph_context=json.dumps(graph.to_dict()),
        graph_manager=graph,
    )
    active_simulations[sim_id] = engine

    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(event: dict):
        await queue.put(event)

    engine.add_event_callback(on_event)

    async def run_in_background():
        try:
            await engine.run(num_rounds)
        except Exception as exc:
            logger.error("Simulation %s failed: %s", sim_id, exc)
        finally:
            # Persist action log to DB BEFORE sending sentinel
            # (sentinel causes generator to exit, which may cancel this task).
            try:
                async with async_session_factory() as db:
                    async with db.begin():
                        sim = await db.get(Simulation, sim_id)
                        if sim:
                            sim.action_log_json = json.dumps(
                                [a.model_dump() for a in engine.get_actions()]
                            )
                            sim.status = engine.status
                            logger.info("Saved %d actions for simulation %s", len(engine.get_actions()), sim_id)
                        # Also update the graph in DB with new action nodes
                        project = await db.get(Project, data["config"]["project_id"])
                        if project and graph:
                            project.graph_json = graph.to_json()
            except Exception as db_exc:
                logger.error("Failed to save simulation results: %s", db_exc)
            await queue.put(None)  # Sentinel to end the stream.

    async def event_generator():
        task = asyncio.create_task(run_in_background())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield {
                    "data": json.dumps(event),
                }
        finally:
            if not task.done():
                task.cancel()

    return EventSourceResponse(event_generator())


@router.get("/{sim_id}/status")
async def get_simulation_status(
    sim_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get the current state of a simulation."""
    engine = active_simulations.get(sim_id)
    if engine:
        return engine.get_state().model_dump()

    sim = await session.get(Simulation, sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    config = json.loads(sim.config_json) if sim.config_json else {}
    actions = json.loads(sim.action_log_json) if sim.action_log_json else []
    return {
        "simulation_id": sim.id,
        "status": sim.status,
        "current_round": config.get("num_rounds", 0),
        "total_rounds": config.get("num_rounds", 0),
        "total_actions": len(actions),
        "recent_actions": actions[-10:] if actions else [],
    }


@router.get("/{sim_id}/actions")
async def get_actions(
    sim_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get the full action log for a simulation."""
    engine = active_simulations.get(sim_id)
    if engine:
        return {"actions": [a.model_dump() for a in engine.get_actions()]}

    sim = await session.get(Simulation, sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if sim.action_log_json:
        return {"actions": json.loads(sim.action_log_json)}

    return {"actions": []}
