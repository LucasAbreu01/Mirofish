from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..config import settings
from ..models.schemas import ResearchBrief
from ..services.llm_service import LLMService
from ..services.zep_graph_service import ZepGraphService


class ResearchSubagent:
    @staticmethod
    def build(
        *,
        graph_id: str,
        simulation_requirement: str,
        project_snapshot: dict[str, Any],
    ) -> ResearchBrief:
        ranked_entities = ZepGraphService.rank_entities(project_snapshot, limit=8)
        search_result = ZepGraphService.search_graph(
            graph_id,
            simulation_requirement or "core dynamics",
            limit=8,
            scope="both",
        )
        fallback = ResearchSubagent._fallback(ranked_entities, search_result, simulation_requirement)
        try:
            payload = LLMService.generate_json(
                system_prompt=(
                    "You are a research subagent for a social simulation. "
                    "Return only JSON with keys core_entities, key_facts, relationship_patterns, risk_signals, topic_map. "
                    "topic_map must be an object where each key maps to a list of short topic strings."
                ),
                user_prompt=(
                    f"Simulation requirement:\n{simulation_requirement or 'No extra requirement.'}\n\n"
                    f"Top entities:\n{ranked_entities}\n\n"
                    f"Graph evidence:\n{search_result}\n\n"
                    "Example shape:\n"
                    '{'
                    '"core_entities":[{"name":"...","entity_type":"...","summary":"...","degree":3}],'
                    '"key_facts":["..."],'
                    '"relationship_patterns":["..."],'
                    '"risk_signals":["..."],'
                    '"topic_map":{"Organizations":["policy","capital"]}'
                    '}'
                ),
                model=settings.llm_fast_model,
                temperature=0.2,
                max_output_tokens=1400,
                fallback=fallback.model_dump(),
            )
            return ResearchBrief.model_validate(
                ResearchSubagent._normalize_payload(payload, fallback.model_dump())
            )
        except Exception:
            return fallback

    @staticmethod
    def _fallback(
        ranked_entities: list[dict[str, Any]],
        search_result: dict[str, Any],
        requirement: str,
    ) -> ResearchBrief:
        topic_map: defaultdict[str, list[str]] = defaultdict(list)
        relationship_patterns = []
        risk_signals = []
        facts = search_result.get("facts", [])[:8]
        for entity in ranked_entities[:6]:
            label = entity.get("entity_type", "Entity")
            summary = entity.get("summary", "")
            tokens = [
                token.strip(".,:;!?()[]{}")
                for token in summary.split()
                if len(token.strip(".,:;!?()[]{}")) > 4
            ][:4]
            if tokens:
                topic_map[label].extend(tokens)
            relationship_patterns.append(
                f"{entity.get('name', 'Entity')} appears central with degree {entity.get('degree', 0)}."
            )
            if "risk" in summary.lower() or "controvers" in summary.lower():
                risk_signals.append(
                    f"{entity.get('name', 'Entity')} is associated with contested or high-risk language."
                )
        if requirement:
            risk_signals.append(f"The simulation should monitor requirement-specific pressure: {requirement}")
        compact_topic_map = {
            key: [token for token, _ in Counter(values).most_common(5)] for key, values in topic_map.items()
        }
        return ResearchBrief(
            core_entities=[
                {
                    "name": entity.get("name", "Entity"),
                    "entity_type": entity.get("entity_type", "Entity"),
                    "summary": entity.get("summary", ""),
                    "degree": entity.get("degree", 0),
                }
                for entity in ranked_entities[:6]
            ],
            key_facts=facts or ["The graph is available but explicit facts are sparse."],
            relationship_patterns=relationship_patterns[:6],
            risk_signals=risk_signals[:6],
            topic_map=compact_topic_map or {"General": ["discussion", "pressure", "narrative"]},
        )

    @staticmethod
    def _normalize_payload(payload: dict[str, Any] | list[Any], fallback: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return fallback
        core_entities = payload.get("core_entities") or payload.get("coreEntities") or payload.get("entities") or []
        key_facts = payload.get("key_facts") or payload.get("keyFacts") or payload.get("facts") or []
        relationship_patterns = (
            payload.get("relationship_patterns")
            or payload.get("relationshipPatterns")
            or payload.get("patterns")
            or []
        )
        risk_signals = payload.get("risk_signals") or payload.get("riskSignals") or payload.get("risks") or []
        topic_map = payload.get("topic_map") or payload.get("topicMap") or {}

        return {
            "core_entities": ResearchSubagent._normalize_core_entities(core_entities) or fallback["core_entities"],
            "key_facts": ResearchSubagent._to_string_list(key_facts) or fallback["key_facts"],
            "relationship_patterns": ResearchSubagent._to_string_list(relationship_patterns)
            or fallback["relationship_patterns"],
            "risk_signals": ResearchSubagent._to_string_list(risk_signals) or fallback["risk_signals"],
            "topic_map": ResearchSubagent._normalize_topic_map(topic_map) or fallback["topic_map"],
        }

    @staticmethod
    def _normalize_core_entities(raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        entities: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, str):
                entities.append({"name": item.strip(), "entity_type": "Entity", "summary": "", "degree": 0})
                continue
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("entity") or "").strip()
            if not name:
                continue
            entities.append(
                {
                    "name": name,
                    "entity_type": str(item.get("entity_type") or item.get("type") or "Entity").strip(),
                    "summary": str(item.get("summary") or item.get("description") or "").strip(),
                    "degree": int(item.get("degree", 0) or 0),
                }
            )
        return entities[:8]

    @staticmethod
    def _normalize_topic_map(raw: Any) -> dict[str, list[str]]:
        if isinstance(raw, dict):
            normalized: dict[str, list[str]] = {}
            for key, value in raw.items():
                normalized[str(key)] = ResearchSubagent._to_string_list(value)[:5]
            return normalized
        return {}

    @staticmethod
    def _to_string_list(raw: Any) -> list[str]:
        if isinstance(raw, str):
            return [raw.strip()] if raw.strip() else []
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]
