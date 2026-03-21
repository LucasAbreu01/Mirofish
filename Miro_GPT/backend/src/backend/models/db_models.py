from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class ProjectRecord(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="created")
    simulation_requirement: Mapped[str] = mapped_column(Text, default="")
    graph_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    analysis_summary: Mapped[str] = mapped_column(Text, default="")
    ontology_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extracted_text_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    graph_snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class TaskRecord(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class SimulationRecord(Base):
    __tablename__ = "simulations"

    simulation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(32), index=True)
    graph_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="created")
    entity_limit: Mapped[int] = mapped_column(Integer)
    rounds: Mapped[int] = mapped_column(Integer)
    active_agents_per_round: Mapped[int] = mapped_column(Integer)
    temperature: Mapped[str] = mapped_column(String(16), default="0.5")
    profiles_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_brief_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    events_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    events_count: Mapped[int] = mapped_column(Integer, default=0)
    latest_summary: Mapped[str] = mapped_column(Text, default="")
    latest_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ReportRecord(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    simulation_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    title: Mapped[str] = mapped_column(String(255), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    sections_json: Mapped[str] = mapped_column(Text, default="[]")
    markdown_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
