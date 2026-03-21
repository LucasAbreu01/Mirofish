from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OntologyAttribute(BaseModel):
    name: str
    description: str


class OntologyEntityType(BaseModel):
    name: str
    description: str
    attributes: list[OntologyAttribute] = Field(default_factory=list)


class OntologyEdgeType(BaseModel):
    name: str
    description: str
    source_targets: list[dict[str, str]] = Field(default_factory=list)
    attributes: list[OntologyAttribute] = Field(default_factory=list)


class OntologyDefinition(BaseModel):
    entity_types: list[OntologyEntityType]
    edge_types: list[OntologyEdgeType]
    analysis_summary: str


class AgentProfileLite(BaseModel):
    agent_id: int
    entity_uuid: str
    name: str
    entity_type: str
    summary: str
    stance_hint: str
    activity_level: float
    influence_score: float
    topics: list[str] = Field(default_factory=list)


class SimulationConfigModel(BaseModel):
    simulation_id: str
    project_id: str
    graph_id: str
    entity_limit: int
    rounds: int
    active_agents_per_round: int
    temperature: float
    created_at: str


class RoundEvent(BaseModel):
    round_index: int
    event_type: str
    actor_agent_id: int | None = None
    target_agent_id: int | None = None
    content: str
    sentiment: str
    impact_score: float
    timestamp: str


class SimulationRunStateModel(BaseModel):
    simulation_id: str
    status: str
    current_round: int
    total_rounds: int
    events_count: int
    latest_summary: str
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


class ResearchBrief(BaseModel):
    core_entities: list[dict[str, Any]] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    relationship_patterns: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    topic_map: dict[str, list[str]] = Field(default_factory=dict)


class ReportSection(BaseModel):
    title: str
    content: str


class ReportDraft(BaseModel):
    title: str
    summary: str
    sections: list[ReportSection]
    markdown_content: str


class CritiqueResult(BaseModel):
    needs_revision: bool
    issues: list[str] = Field(default_factory=list)
    revision_instructions: str = ""


class GraphSnapshot(BaseModel):
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: dict[str, int]
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
