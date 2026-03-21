from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_session, Project, Document, Simulation
from app.services.document_processor import process_file
from app.services.entity_extractor import extract_entities
from app.services.knowledge_graph import KnowledgeGraphManager
from app.utils.logger import get_logger

logger = get_logger("mirofish.api.graph")

router = APIRouter()


@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
    scenario: str = Form(...),
    project_name: str = Form("New Project"),
    session: AsyncSession = Depends(get_session),
):
    """Upload documents, extract entities, and build a knowledge graph."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Process each uploaded file.
    texts: list[str] = []
    filenames: list[str] = []
    for f in files:
        try:
            text = await process_file(f)
            texts.append(text)
            filenames.append(f.filename or "unknown")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    combined_text = "\n\n".join(texts)

    # Extract entities and build graph.
    kg = await extract_entities(combined_text, scenario)
    graph = KnowledgeGraphManager.from_extraction(kg)

    # Persist project.
    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        name=project_name,
        scenario=scenario,
        status="graph_ready",
        graph_json=graph.to_json(),
    )
    session.add(project)

    # Persist documents.
    for filename, text in zip(filenames, texts):
        doc = Document(
            id=str(uuid.uuid4()),
            project_id=project_id,
            filename=filename,
            content_text=text,
        )
        session.add(doc)

    await session.flush()

    graph_dict = graph.to_dict()
    return {
        "project_id": project_id,
        "graph": graph_dict,
        "entity_count": len(graph_dict["nodes"]),
        "relationship_count": len(graph_dict["edges"]),
    }


@router.get("/history")
async def get_history(session: AsyncSession = Depends(get_session)):
    """List all projects with their latest simulation info."""
    # Get all projects ordered by most recent first
    result = await session.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    history = []
    for project in projects:
        # Get simulations for this project
        sim_result = await session.execute(
            select(Simulation).where(Simulation.project_id == project.id).order_by(Simulation.created_at.desc())
        )
        sims = sim_result.scalars().all()

        # Count entities from graph
        entity_count = 0
        if project.graph_json:
            try:
                graph_data = json.loads(project.graph_json)
                entity_count = len(graph_data.get("nodes", []))
            except Exception:
                pass

        sim_list = []
        for sim in sims:
            config = json.loads(sim.config_json) if sim.config_json else {}
            action_count = 0
            if sim.action_log_json:
                try:
                    action_count = len(json.loads(sim.action_log_json))
                except Exception:
                    pass
            has_report = bool(sim.result_summary)
            sim_list.append({
                "id": sim.id,
                "status": sim.status,
                "num_rounds": config.get("num_rounds", 0),
                "agent_count": config.get("agent_count", 0),
                "action_count": action_count,
                "has_report": has_report,
                "created_at": str(sim.created_at),
            })

        history.append({
            "id": project.id,
            "name": project.name,
            "scenario": project.scenario or "",
            "status": project.status,
            "entity_count": entity_count,
            "simulations": sim_list,
            "created_at": str(project.created_at),
        })

    return {"projects": history}


@router.delete("/history/{project_id}")
async def delete_project(project_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a project and all associated data."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete simulations
    await session.execute(sa_delete(Simulation).where(Simulation.project_id == project_id))
    # Delete documents
    await session.execute(sa_delete(Document).where(Document.project_id == project_id))
    # Delete project
    await session.delete(project)
    await session.flush()

    return {"deleted": project_id}


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a project with its knowledge graph data."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    graph_dict = None
    if project.graph_json:
        graph = KnowledgeGraphManager.from_json(project.graph_json)
        graph_dict = graph.to_dict()

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "scenario": project.scenario,
            "created_at": str(project.created_at),
        },
        "graph": graph_dict,
    }


@router.get("/{project_id}/status")
async def get_project_status(
    project_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Lightweight status check for a project."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"status": project.status}
