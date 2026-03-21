from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..config import settings
from ..models.schemas import AgentProfileLite, ResearchBrief, RoundEvent, SimulationConfigModel
from ..services.llm_service import LLMService


class SimSubagent:
    @staticmethod
    def run_round(
        *,
        round_index: int,
        config: SimulationConfigModel,
        requirement: str,
        active_agents: list[AgentProfileLite],
        research_brief: ResearchBrief,
        previous_summary: str,
    ) -> tuple[list[RoundEvent], str]:
        fallback = SimSubagent._fallback_events(round_index, active_agents, requirement)
        payload = LLMService.generate_json(
            system_prompt=(
                "You are a simulation subagent. "
                "Return only JSON with keys summary and events. "
                "events must be a list of objects containing event_type, actor_agent_id, target_agent_id, content, sentiment, impact_score."
            ),
            user_prompt=(
                f"Round: {round_index}\n"
                f"Requirement: {requirement or 'General scenario evolution.'}\n"
                f"Previous summary: {previous_summary or 'No previous rounds.'}\n"
                f"Research brief: {research_brief.model_dump()}\n"
                f"Active agents: {[agent.model_dump() for agent in active_agents]}\n"
                "Constraints: produce 2 to 5 concise, plausible social events; keep them grounded in the evidence.\n"
                "Example shape:\n"
                '{'
                '"summary":"Round summary",'
                '"events":[{"event_type":"post","actor_agent_id":1,"target_agent_id":null,"content":"...","sentiment":"mixed","impact_score":0.55}]'
                '}'
            ),
            model=settings.llm_fast_model,
            temperature=config.temperature,
            max_output_tokens=1200,
            fallback=fallback,
        )
        normalized = SimSubagent._normalize_payload(payload, fallback)
        summary = normalized["summary"]
        events_payload = normalized["events"]
        events: list[RoundEvent] = []
        for raw_event in events_payload[:5]:
            events.append(
                RoundEvent(
                    round_index=round_index,
                    event_type=str(raw_event.get("event_type", "post")),
                    actor_agent_id=raw_event.get("actor_agent_id"),
                    target_agent_id=raw_event.get("target_agent_id"),
                    content=str(raw_event.get("content", "")).strip(),
                    sentiment=str(raw_event.get("sentiment", "neutral")),
                    impact_score=float(raw_event.get("impact_score", 0.45)),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        if not events:
            events = [
                RoundEvent(
                    round_index=round_index,
                    event_type="post",
                    actor_agent_id=active_agents[0].agent_id if active_agents else None,
                    target_agent_id=None,
                    content="The round remained quiet due to weak signals.",
                    sentiment="neutral",
                    impact_score=0.2,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            ]
        return events, summary

    @staticmethod
    def _fallback_events(
        round_index: int,
        active_agents: list[AgentProfileLite],
        requirement: str,
    ) -> dict[str, Any]:
        if not active_agents:
            return {
                "summary": "No active agents were available in this round.",
                "events": [],
            }
        events = []
        for index, agent in enumerate(active_agents[:3]):
            target = active_agents[(index + 1) % len(active_agents)] if len(active_agents) > 1 else None
            events.append(
                {
                    "event_type": "post" if index == 0 else "reaction",
                    "actor_agent_id": agent.agent_id,
                    "target_agent_id": target.agent_id if target else None,
                    "content": (
                        f"{agent.name} comments on {requirement or 'the scenario'} from a "
                        f"{agent.stance_hint.lower()} position."
                    ),
                    "sentiment": "mixed" if index == 0 else "neutral",
                    "impact_score": max(0.2, min(0.9, agent.influence_score * 0.75)),
                }
            )
        return {
            "summary": f"Round {round_index} focused on reactions among {len(active_agents)} active agents.",
            "events": events,
        }

    @staticmethod
    def _normalize_payload(payload: dict[str, Any] | list[Any], fallback: dict[str, Any]) -> dict[str, Any]:
        if isinstance(payload, list):
            payload = {"events": payload}
        if not isinstance(payload, dict):
            return fallback

        summary = str(
            payload.get("summary")
            or payload.get("round_summary")
            or payload.get("roundSummary")
            or fallback["summary"]
        ).strip()
        events_raw = (
            payload.get("events")
            or payload.get("round_events")
            or payload.get("roundEvents")
            or payload.get("actions")
            or []
        )
        normalized_events = SimSubagent._normalize_events(events_raw)
        return {
            "summary": summary or fallback["summary"],
            "events": normalized_events or fallback["events"],
        }

    @staticmethod
    def _normalize_events(raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "event_type": str(
                        item.get("event_type")
                        or item.get("type")
                        or item.get("action")
                        or "post"
                    ).lower(),
                    "actor_agent_id": SimSubagent._coerce_int(
                        item.get("actor_agent_id") or item.get("actor") or item.get("agent_id")
                    ),
                    "target_agent_id": SimSubagent._coerce_int(
                        item.get("target_agent_id") or item.get("target") or item.get("target_id")
                    ),
                    "content": str(item.get("content") or item.get("message") or "").strip(),
                    "sentiment": str(item.get("sentiment") or item.get("tone") or "neutral").lower(),
                    "impact_score": SimSubagent._coerce_float(item.get("impact_score") or item.get("impact") or 0.45),
                }
            )
        return [event for event in normalized if event["content"]][:5]

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.45
