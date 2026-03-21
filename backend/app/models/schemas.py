from __future__ import annotations

from pydantic import BaseModel


class EntityNode(BaseModel):
    name: str
    entity_type: str
    description: str
    attributes: dict = {}


class EntityEdge(BaseModel):
    source: str
    target: str
    relation_type: str
    description: str


class KnowledgeGraph(BaseModel):
    entities: list[EntityNode]
    relationships: list[EntityEdge]


class AgentProfile(BaseModel):
    name: str
    entity_type: str
    personality: str
    goals: str
    backstory: str
    age: int | None = None
    profession: str = ""
    communication_style: str = "neutral"


class SimulationConfig(BaseModel):
    project_id: str
    num_rounds: int = 10
    agent_count: int = 5
    scenario: str = ""


class SimulationAction(BaseModel):
    round: int
    agent_name: str
    action_type: str
    content: str
    target_message_id: str | None = None
    reasoning: str = ""
    timestamp: str = ""


class SimulationState(BaseModel):
    simulation_id: str
    status: str
    current_round: int
    total_rounds: int
    total_actions: int
    recent_actions: list[SimulationAction] = []


class ChatMessage(BaseModel):
    role: str
    content: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    status: str
    created_at: str


class ReportResponse(BaseModel):
    simulation_id: str
    report: str
    generated_at: str
