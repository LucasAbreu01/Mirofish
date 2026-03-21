from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from ..config import settings
from ..db import session_scope
from ..models.db_models import SimulationRecord
from ..models.schemas import AgentProfileLite, ResearchBrief, SimulationConfigModel, SimulationRunStateModel
from ..subagents.research import ResearchSubagent
from ..subagents.sim import SimSubagent
from ..utils.id_factory import prefixed_id
from ..utils.json_tools import append_jsonl, read_json, read_jsonl, write_json
from .project_service import ProjectService
from .task_service import TaskService
from .zep_graph_service import ZepGraphService


class SimulationService:
    @staticmethod
    def create_simulation(
        *,
        project_id: str,
        entity_limit: int | None,
        rounds: int | None,
        active_agents_per_round: int | None = None,
        temperature: float = 0.35,
    ) -> dict[str, Any]:
        project = ProjectService.get_project(project_id)
        if not project["graph_id"]:
            raise ValueError("Generate the project graph before creating a simulation.")

        entity_limit = entity_limit or settings.entity_cap_default
        rounds = rounds or settings.rounds_default
        active_agents_per_round = active_agents_per_round or settings.active_agents_per_round_default

        if entity_limit > settings.entity_cap_hard_max:
            raise ValueError(f"Entity limit exceeds hard max of {settings.entity_cap_hard_max}.")
        if rounds > settings.rounds_hard_max:
            raise ValueError(f"Rounds exceed hard max of {settings.rounds_hard_max}.")
        if active_agents_per_round > settings.active_agents_per_round_hard_max:
            raise ValueError(
                f"Active agents per round exceed hard max of {settings.active_agents_per_round_hard_max}."
            )

        simulation_id = prefixed_id("sim")
        config = SimulationConfigModel(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=project["graph_id"],
            entity_limit=entity_limit,
            rounds=rounds,
            active_agents_per_round=active_agents_per_round,
            temperature=temperature,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        simulation_dir = ProjectService.simulation_dir(project_id, simulation_id)
        state = SimulationRunStateModel(
            simulation_id=simulation_id,
            status="created",
            current_round=0,
            total_rounds=rounds,
            events_count=0,
            latest_summary="",
        )
        write_json(simulation_dir / "state.json", state.model_dump())
        write_json(simulation_dir / "config.json", config.model_dump())
        (simulation_dir / "events.jsonl").write_text("", encoding="utf-8")

        with session_scope() as session:
            session.add(
                SimulationRecord(
                    simulation_id=simulation_id,
                    project_id=project_id,
                    graph_id=project["graph_id"],
                    status="created",
                    entity_limit=entity_limit,
                    rounds=rounds,
                    active_agents_per_round=active_agents_per_round,
                    temperature=str(temperature),
                    config_json=SimulationService._dump(config.model_dump()),
                    profiles_path=str(simulation_dir / "profiles.json"),
                    state_path=str(simulation_dir / "state.json"),
                    research_brief_path=str(simulation_dir / "research_brief.json"),
                    events_path=str(simulation_dir / "events.jsonl"),
                )
            )
        return SimulationService.get_simulation(simulation_id)

    @staticmethod
    def prepare_simulation(simulation_id: str) -> dict[str, Any]:
        with session_scope() as session:
            record = session.get(SimulationRecord, simulation_id)
            if record is None:
                raise ValueError(f"Simulation {simulation_id} not found.")

            project = ProjectService.get_project(record.project_id)
            snapshot = ZepGraphService.get_graph_snapshot(record.project_id)
            ranked_entities = ZepGraphService.rank_entities(
                snapshot,
                limit=max(record.entity_limit * 3, record.entity_limit),
            )
            simulatable_entities = [
                entity for entity in ranked_entities if SimulationService._is_simulatable_entity(entity)
            ]
            profiles = SimulationService._build_profiles(
                simulatable_entities,
                desired_count=record.entity_limit,
                ontology=project.get("ontology"),
                requirement=project.get("simulation_requirement", ""),
            )

            profiles_path = ProjectService.simulation_dir(record.project_id, record.simulation_id) / "profiles.json"
            write_json(profiles_path, [profile.model_dump() for profile in profiles])
            record.status = "prepared"
            record.profiles_path = str(profiles_path)
            record.error = None

        return SimulationService.get_simulation(simulation_id)

    @staticmethod
    def run_simulation(simulation_id: str, task_id: str) -> dict[str, Any]:
        record = SimulationService._get_record(simulation_id)
        simulation_dir = ProjectService.simulation_dir(record.project_id, simulation_id)
        profiles_path = simulation_dir / "profiles.json"
        if not read_json(profiles_path, default=None):
            SimulationService.prepare_simulation(simulation_id)
            record = SimulationService._get_record(simulation_id)

        project = ProjectService.get_project(record.project_id)
        profiles = [
            AgentProfileLite.model_validate(item)
            for item in read_json(profiles_path, default=[]) or []
        ]
        if not profiles:
            raise ValueError("No simulation profiles are available. Prepare the simulation first.")

        config = SimulationConfigModel.model_validate(
            read_json(simulation_dir / "config.json", default={}) or {}
        )
        state_path = simulation_dir / "state.json"
        events_path = simulation_dir / "events.jsonl"
        research_path = simulation_dir / "research_brief.json"

        TaskService.update_task(task_id, progress=8, message="Building research brief for the simulation.")
        research = ResearchSubagent.build(
            graph_id=record.graph_id,
            simulation_requirement=project["simulation_requirement"],
            project_snapshot=ZepGraphService.get_graph_snapshot(record.project_id),
        )
        write_json(research_path, research.model_dump())

        state = SimulationRunStateModel(
            simulation_id=simulation_id,
            status="running",
            current_round=0,
            total_rounds=config.rounds,
            events_count=0,
            latest_summary="",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        write_json(state_path, {**state.model_dump(), "last_active_rounds": {}})

        with session_scope() as session:
            db_record = session.get(SimulationRecord, simulation_id)
            if db_record is None:
                raise ValueError(f"Simulation {simulation_id} not found.")
            db_record.status = "running"
            db_record.started_at = datetime.utcnow()
            db_record.latest_task_id = task_id
            db_record.error = None

        all_events = read_jsonl(events_path)
        for round_index in range(1, config.rounds + 1):
            progress = 10 + int((round_index - 1) / max(1, config.rounds) * 78)
            TaskService.update_task(task_id, progress=progress, message=f"Running simulation round {round_index}.")
            state_payload = read_json(state_path, default={}) or {}
            active_agents = SimulationService._select_active_agents(
                profiles=profiles,
                active_count=config.active_agents_per_round,
                last_active_rounds=state_payload.get("last_active_rounds", {}),
                round_index=round_index,
                requirement=project["simulation_requirement"],
                research_brief=research,
            )
            round_events, round_summary = SimSubagent.run_round(
                round_index=round_index,
                config=config,
                requirement=project["simulation_requirement"],
                active_agents=active_agents,
                research_brief=research,
                previous_summary=state.latest_summary,
            )

            for event in round_events:
                append_jsonl(events_path, event.model_dump())
                all_events.append(event.model_dump())
            for agent in active_agents:
                state_payload["last_active_rounds"][str(agent.agent_id)] = round_index

            state = SimulationRunStateModel(
                simulation_id=simulation_id,
                status="running",
                current_round=round_index,
                total_rounds=config.rounds,
                events_count=len(all_events),
                latest_summary=round_summary,
                started_at=state.started_at,
            )
            write_json(state_path, {**state.model_dump(), "last_active_rounds": state_payload["last_active_rounds"]})
            with session_scope() as session:
                db_record = session.get(SimulationRecord, simulation_id)
                if db_record is None:
                    raise ValueError(f"Simulation {simulation_id} not found.")
                db_record.current_round = round_index
                db_record.events_count = len(all_events)
                db_record.latest_summary = round_summary
                db_record.status = "running"

        completed_state = SimulationRunStateModel(
            simulation_id=simulation_id,
            status="completed",
            current_round=config.rounds,
            total_rounds=config.rounds,
            events_count=len(all_events),
            latest_summary=state.latest_summary,
            started_at=state.started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        final_last_active = (read_json(state_path, default={}) or {}).get("last_active_rounds", {})
        write_json(state_path, {**completed_state.model_dump(), "last_active_rounds": final_last_active})
        with session_scope() as session:
            db_record = session.get(SimulationRecord, simulation_id)
            if db_record is None:
                raise ValueError(f"Simulation {simulation_id} not found.")
            db_record.status = "completed"
            db_record.events_count = len(all_events)
            db_record.current_round = config.rounds
            db_record.latest_summary = completed_state.latest_summary
            db_record.completed_at = datetime.utcnow()
            db_record.error = None

        return {
            "simulation_id": simulation_id,
            "rounds_completed": config.rounds,
            "events_count": len(all_events),
            "research_brief_path": str(research_path),
        }

    @staticmethod
    def get_simulation(simulation_id: str) -> dict[str, Any]:
        with session_scope() as session:
            record = session.get(SimulationRecord, simulation_id)
            if record is None:
                raise ValueError(f"Simulation {simulation_id} not found.")
            return SimulationService.serialize_record(record)

    @staticmethod
    def get_feed(simulation_id: str) -> dict[str, Any]:
        record = SimulationService._get_record(simulation_id)
        simulation_dir = ProjectService.simulation_dir(record.project_id, simulation_id)
        events = read_jsonl(simulation_dir / "events.jsonl")
        state = read_json(simulation_dir / "state.json", default={}) or {}
        summaries = SimulationService._round_summaries(events)
        analytics = SimulationService.analytics_from_events(events)
        return {
            "simulation_id": simulation_id,
            "state": state,
            "events": events,
            "round_summaries": summaries,
            "analytics": analytics,
        }

    @staticmethod
    def analytics_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
        if not events:
            return {
                "events_count": 0,
                "rounds_completed": 0,
                "dominant_sentiment": "neutral",
                "top_agents": [],
                "event_types": {},
            }
        sentiment_counts = Counter(event.get("sentiment", "neutral") for event in events)
        actor_counts = Counter(str(event.get("actor_agent_id")) for event in events if event.get("actor_agent_id"))
        type_counts = Counter(event.get("event_type", "post") for event in events)
        rounds_completed = max(int(event.get("round_index", 0)) for event in events)
        return {
            "events_count": len(events),
            "rounds_completed": rounds_completed,
            "dominant_sentiment": sentiment_counts.most_common(1)[0][0],
            "top_agents": [{"agent_id": agent_id, "count": count} for agent_id, count in actor_counts.most_common(5)],
            "event_types": dict(type_counts),
        }

    @staticmethod
    def serialize_record(record: SimulationRecord) -> dict[str, Any]:
        simulation_dir = ProjectService.simulation_dir(record.project_id, record.simulation_id)
        config = read_json(simulation_dir / "config.json", default={}) or {}
        state = read_json(simulation_dir / "state.json", default={}) or {}
        profiles = read_json(simulation_dir / "profiles.json", default=[]) or []
        return {
            "simulation_id": record.simulation_id,
            "project_id": record.project_id,
            "graph_id": record.graph_id,
            "status": record.status,
            "entity_limit": record.entity_limit,
            "rounds": record.rounds,
            "active_agents_per_round": record.active_agents_per_round,
            "temperature": float(record.temperature),
            "config": config,
            "state": state,
            "profiles_count": len(profiles),
            "current_round": record.current_round,
            "events_count": record.events_count,
            "latest_summary": record.latest_summary,
            "latest_task_id": record.latest_task_id,
            "error": record.error,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        }

    @staticmethod
    def _build_profiles(
        entities: list[dict[str, Any]],
        *,
        desired_count: int | None = None,
        ontology: dict[str, Any] | None = None,
        requirement: str = "",
    ) -> list[AgentProfileLite]:
        if not entities and not (ontology or {}).get("entity_types"):
            raise ValueError("The graph snapshot does not contain enough entities for simulation.")

        entity_pool = entities[: desired_count or len(entities)]
        max_degree = max((entity.get("degree", 1) for entity in entity_pool), default=1)
        profiles: list[AgentProfileLite] = []
        for index, entity in enumerate(entity_pool, start=1):
            entity_type = entity.get("entity_type", "Entity")
            degree = entity.get("degree", 0)
            summary = entity.get("summary", "") or f"{entity.get('name', 'Entity')} is part of the current graph."
            influence = min(1.0, 0.35 + (degree / max(1, max_degree)) * 0.65)
            activity = min(1.0, 0.25 + (len(summary) / 250))
            profiles.append(
                AgentProfileLite(
                    agent_id=index,
                    entity_uuid=entity.get("uuid", f"node_{index}"),
                    name=entity.get("name", f"Entity {index}"),
                    entity_type=entity_type,
                    summary=summary[:320],
                    stance_hint=SimulationService._stance_from_type(entity_type),
                    activity_level=round(activity, 2),
                    influence_score=round(influence, 2),
                    topics=SimulationService._topics_from_entity(entity),
                )
            )

        if desired_count and len(profiles) < desired_count:
            profiles.extend(
                SimulationService._synthesize_profiles(
                    count=desired_count - len(profiles),
                    start_index=len(profiles) + 1,
                    ontology=ontology or {},
                    requirement=requirement,
                    existing_profiles=profiles,
                )
            )
        return profiles

    @staticmethod
    def _select_active_agents(
        *,
        profiles: list[AgentProfileLite],
        active_count: int,
        last_active_rounds: dict[str, int],
        round_index: int,
        requirement: str,
        research_brief: ResearchBrief,
    ) -> list[AgentProfileLite]:
        ranked: list[tuple[float, AgentProfileLite]] = []
        topic_tokens = {token.lower() for values in research_brief.topic_map.values() for token in values}
        requirement_tokens = {
            token.lower().strip(".,:;!?()[]{}")
            for token in requirement.split()
            if len(token.strip(".,:;!?()[]{}")) > 3
        }
        for profile in profiles:
            recent_round = last_active_rounds.get(str(profile.agent_id), 0)
            recency_penalty = 0.12 if recent_round and round_index - recent_round < 2 else 0.0
            topic_overlap = len(topic_tokens.intersection(token.lower() for token in profile.topics)) * 0.08
            requirement_overlap = len(requirement_tokens.intersection(token.lower() for token in profile.topics)) * 0.1
            score = (profile.influence_score * 0.6) + (profile.activity_level * 0.25) + topic_overlap + requirement_overlap - recency_penalty
            ranked.append((score, profile))
        ranked.sort(key=lambda item: (item[0], item[1].influence_score), reverse=True)
        return [profile for _, profile in ranked[:active_count]]

    @staticmethod
    def _round_summaries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            grouped[int(event.get("round_index", 0))].append(event)
        return [
            {
                "round_index": round_index,
                "events_count": len(items),
                "highlights": [item.get("content", "") for item in items[:3]],
            }
            for round_index, items in sorted(grouped.items())
        ]

    @staticmethod
    def _topics_from_entity(entity: dict[str, Any]) -> list[str]:
        summary = entity.get("summary", "")
        tokens = [
            token.strip(".,:;!?()[]{}")
            for token in summary.split()
            if len(token.strip(".,:;!?()[]{}")) > 4
        ]
        if not tokens:
            return [entity.get("entity_type", "topic").lower()]
        seen: list[str] = []
        for token in tokens:
            lower = token.lower()
            if lower not in seen:
                seen.append(lower)
            if len(seen) >= 5:
                break
        return seen

    @staticmethod
    def _stance_from_type(entity_type: str) -> str:
        normalized = entity_type.upper()
        mapping = {
            "PERSON": "Opinionated",
            "ORGANIZATION": "Strategic",
            "PARTNER": "Strategic",
            "CLIENT": "Reactive",
            "CONTRACT": "Analytical",
            "COMMISSIONRULE": "Analytical",
            "COMMISSIONPAYMENT": "Analytical",
            "EVENT": "Reactive",
            "TOPIC": "Agenda-driven",
            "POLICY_PROPOSAL": "Agenda-driven",
            "LEGAL_ISSUE": "Analytical",
            "STATISTIC": "Analytical",
        }
        return mapping.get(normalized, "Analytical")

    @staticmethod
    def _is_simulatable_entity(entity: dict[str, Any]) -> bool:
        name = str(entity.get("name", "") or "").strip().lower()
        entity_type = str(entity.get("entity_type", "") or "").strip().lower()
        if not name:
            return False
        if entity_type in {"entity", ""} and any(name.endswith(ext) for ext in (".pdf", ".txt", ".md", ".markdown")):
            return False
        return True

    @staticmethod
    def _synthesize_profiles(
        *,
        count: int,
        start_index: int,
        ontology: dict[str, Any],
        requirement: str,
        existing_profiles: list[AgentProfileLite],
    ) -> list[AgentProfileLite]:
        synthetic_profiles: list[AgentProfileLite] = []
        entity_types = ontology.get("entity_types", []) if isinstance(ontology, dict) else []
        existing_types = {profile.entity_type.lower() for profile in existing_profiles}
        existing_names = {profile.name.lower() for profile in existing_profiles}
        candidates: list[dict[str, Any]] = []

        for entity_type in entity_types:
            if not isinstance(entity_type, dict):
                continue
            if str(entity_type.get("name", "")).strip().lower() in existing_types:
                continue
            candidates.append(entity_type)
            if len(candidates) >= count:
                break

        if len(candidates) < count:
            for entity_type in entity_types:
                if not isinstance(entity_type, dict):
                    continue
                candidates.append(entity_type)
                if len(candidates) >= count:
                    break

        requirement_snippet = " ".join(requirement.split()[:24]).strip()
        for offset in range(count):
            blueprint = candidates[offset] if offset < len(candidates) else {}
            entity_type = str(blueprint.get("name") or "ScenarioAgent").strip() or "ScenarioAgent"
            base_name = f"{entity_type} Proxy"
            name = base_name
            suffix = 2
            while name.lower() in existing_names:
                name = f"{base_name} {suffix}"
                suffix += 1
            existing_names.add(name.lower())
            description = str(blueprint.get("description") or f"{entity_type} agent for the simulation.").strip()
            summary = (
                f"Synthetic {entity_type} profile added because the graph exposed fewer entities than requested. "
                f"{description}"
            )
            if requirement_snippet:
                summary = f"{summary} Requirement focus: {requirement_snippet}."
            synthetic_entity = {
                "summary": summary,
                "entity_type": entity_type,
            }
            synthetic_profiles.append(
                AgentProfileLite(
                    agent_id=start_index + offset,
                    entity_uuid=f"synthetic_{SimulationService._slug(entity_type)}_{start_index + offset}",
                    name=name,
                    entity_type=entity_type,
                    summary=summary[:320],
                    stance_hint=SimulationService._stance_from_type(entity_type),
                    activity_level=round(max(0.4, 0.62 - (offset * 0.03)), 2),
                    influence_score=round(max(0.35, 0.56 - (offset * 0.04)), 2),
                    topics=SimulationService._topics_from_entity(synthetic_entity),
                )
            )

        return synthetic_profiles

    @staticmethod
    def _slug(value: str) -> str:
        normalized = "".join(char.lower() if char.isalnum() else "_" for char in value)
        while "__" in normalized:
            normalized = normalized.replace("__", "_")
        return normalized.strip("_") or "agent"

    @staticmethod
    def _get_record(simulation_id: str) -> SimulationRecord:
        with session_scope() as session:
            record = session.get(SimulationRecord, simulation_id)
            if record is None:
                raise ValueError(f"Simulation {simulation_id} not found.")
            session.expunge(record)
            return record

    @staticmethod
    def _dump(payload: Any) -> str:
        import json

        return json.dumps(payload)
