from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ..config import settings
from ..models.schemas import OntologyDefinition
from ..utils.logger import get_logger
from .llm_service import LLMService
from .project_service import ProjectService
from .task_service import TaskService


logger = get_logger("miro_gpt.ontology_service")


class OntologyService:
    @staticmethod
    def generate_for_project(project_id: str, task_id: str) -> dict[str, Any]:
        TaskService.update_task(task_id, progress=8, message="Loading project text.")
        text = ProjectService.load_extracted_text(project_id)
        snippet = text[:18000]
        fallback = OntologyService._fallback_ontology(snippet)

        TaskService.update_task(task_id, progress=22, message="Generating ontology with the LLM.")
        payload = LLMService.generate_json(
            system_prompt=(
                "You are building a compact social-simulation ontology from source documents. "
                "Keep it small, practical, and reusable. "
                "Return only JSON with keys entity_types, edge_types, and analysis_summary. "
                "Each entity type must include name, description, and attributes[]. "
                "Each edge type must include name, description, source_targets[], and attributes[]. "
                "Attributes must be objects with name and description."
            ),
            user_prompt=(
                f"Simulation requirement:\n{ProjectService.get_project(project_id)['simulation_requirement'] or 'Not provided.'}\n\n"
                "Create 3 to 6 entity types and 2 to 5 edge types.\n"
                "Example shape:\n"
                '{'
                '"entity_types":[{"name":"Person","description":"...","attributes":[{"name":"role","description":"..."}]}],'
                '"edge_types":[{"name":"influences","description":"...","source_targets":[{"source":"Person","target":"Organization"}],"attributes":[{"name":"mechanism","description":"..."}]}],'
                '"analysis_summary":"..."'
                '}\n\n'
                f"Source text excerpt:\n{snippet}"
            ),
            model=settings.llm_quality_model,
            temperature=0.1,
            max_output_tokens=2200,
            fallback=fallback,
        )

        try:
            ontology = OntologyDefinition.model_validate(
                OntologyService._normalize_ontology_payload(payload, fallback)
            )
        except ValidationError:
            logger.warning("Ontology payload failed validation. Falling back to heuristic ontology.")
            ontology = OntologyDefinition.model_validate(fallback)

        TaskService.update_task(task_id, progress=74, message="Persisting ontology artifacts.")
        path = ProjectService.save_ontology(project_id, ontology.model_dump())
        return {
            "project_id": project_id,
            "ontology_path": str(path),
            "analysis_summary": ontology.analysis_summary,
            "entity_type_count": len(ontology.entity_types),
            "edge_type_count": len(ontology.edge_types),
        }

    @staticmethod
    def _normalize_ontology_payload(
        payload: dict[str, Any] | list[Any],
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(payload, list):
            payload = {"entity_types": payload}
        if not isinstance(payload, dict):
            return fallback

        container = payload.get("ontology") if isinstance(payload.get("ontology"), dict) else payload
        entity_candidates = (
            container.get("entity_types")
            or container.get("entityTypes")
            or container.get("entities")
            or container.get("nodes")
            or []
        )
        edge_candidates = (
            container.get("edge_types")
            or container.get("edgeTypes")
            or container.get("relationships")
            or container.get("edges")
            or []
        )
        summary = (
            container.get("analysis_summary")
            or container.get("analysisSummary")
            or container.get("summary")
            or fallback.get("analysis_summary", "")
        )

        entity_types = OntologyService._normalize_entity_types(entity_candidates)
        edge_types = OntologyService._normalize_edge_types(edge_candidates)

        if not entity_types:
            entity_types = fallback["entity_types"]
        if not edge_types:
            edge_types = fallback["edge_types"]

        return {
            "entity_types": entity_types,
            "edge_types": edge_types,
            "analysis_summary": str(summary).strip() or fallback["analysis_summary"],
        }

    @staticmethod
    def _normalize_entity_types(items: Any) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        derived_by_type: dict[str, dict[str, Any]] = {}
        normalized: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, str):
                normalized.append(
                    {
                        "name": item.strip().replace(" ", "_").title().replace("_", ""),
                        "description": f"{item.strip()} entities in the scenario.",
                        "attributes": [],
                    }
                )
                continue
            if not isinstance(item, dict):
                continue

            # If the model returned concrete entities instead of ontology types, collapse them into type definitions.
            if "entity_type" in item or ("type" in item and "attributes" not in item):
                type_name = str(item.get("entity_type") or item.get("type") or "Entity").strip()
                entry = derived_by_type.setdefault(
                    type_name,
                    {
                        "name": type_name,
                        "description": f"{type_name} entities relevant to the scenario.",
                        "attributes": [],
                    },
                )
                item_attributes = item.get("attributes", {})
                if isinstance(item_attributes, dict):
                    for key in list(item_attributes.keys())[:4]:
                        if key and not any(attr["name"] == key for attr in entry["attributes"]):
                            entry["attributes"].append(
                                {"name": str(key), "description": f"{key} associated with {type_name}."}
                            )
                continue

            name = str(item.get("name") or item.get("label") or "").strip()
            if not name:
                continue
            normalized.append(
                {
                    "name": name,
                    "description": str(item.get("description") or f"{name} entities in the scenario.").strip(),
                    "attributes": OntologyService._normalize_attributes(item.get("attributes")),
                }
            )

        normalized.extend(derived_by_type.values())
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in normalized:
            key = item["name"].lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[:6]

    @staticmethod
    def _normalize_edge_types(items: Any) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        derived_by_type: dict[str, dict[str, Any]] = {}
        normalized: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, str):
                normalized.append(
                    {
                        "name": item.strip().replace(" ", "_").lower(),
                        "description": f"{item.strip()} relationship in the scenario.",
                        "source_targets": [{"source": "Entity", "target": "Entity"}],
                        "attributes": [],
                    }
                )
                continue
            if not isinstance(item, dict):
                continue

            if "relation_type" in item or ("source" in item and "target" in item):
                relation_type = str(item.get("relation_type") or item.get("type") or "related_to").strip()
                entry = derived_by_type.setdefault(
                    relation_type,
                    {
                        "name": relation_type,
                        "description": str(
                            item.get("description") or f"{relation_type} relationship in the scenario."
                        ).strip(),
                        "source_targets": [],
                        "attributes": [],
                    },
                )
                source = str(item.get("source_type") or item.get("source") or "Entity").strip()
                target = str(item.get("target_type") or item.get("target") or "Entity").strip()
                pair = {"source": source, "target": target}
                if pair not in entry["source_targets"]:
                    entry["source_targets"].append(pair)
                continue

            name = str(item.get("name") or item.get("label") or "").strip()
            if not name:
                continue
            source_targets = item.get("source_targets") or item.get("sourceTargets")
            normalized.append(
                {
                    "name": name,
                    "description": str(
                        item.get("description") or f"{name} relationship in the scenario."
                    ).strip(),
                    "source_targets": OntologyService._normalize_source_targets(source_targets),
                    "attributes": OntologyService._normalize_attributes(item.get("attributes")),
                }
            )

        normalized.extend(derived_by_type.values())
        for item in normalized:
            if not item["source_targets"]:
                item["source_targets"] = [{"source": "Entity", "target": "Entity"}]

        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in normalized:
            key = item["name"].lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[:5]

    @staticmethod
    def _normalize_attributes(raw_attributes: Any) -> list[dict[str, str]]:
        if isinstance(raw_attributes, list):
            normalized: list[dict[str, str]] = []
            for item in raw_attributes:
                if isinstance(item, str):
                    normalized.append(
                        {"name": item.strip(), "description": f"{item.strip()} associated with the entity type."}
                    )
                elif isinstance(item, dict):
                    name = str(item.get("name") or item.get("key") or "").strip()
                    if not name:
                        continue
                    normalized.append(
                        {
                            "name": name,
                            "description": str(item.get("description") or f"{name} attribute.").strip(),
                        }
                    )
            return normalized[:6]
        if isinstance(raw_attributes, dict):
            return [
                {
                    "name": str(key),
                    "description": f"{key} attribute.",
                }
                for key in list(raw_attributes.keys())[:6]
                if str(key).strip()
            ]
        return []

    @staticmethod
    def _normalize_source_targets(raw_source_targets: Any) -> list[dict[str, str]]:
        if not isinstance(raw_source_targets, list):
            return []
        normalized: list[dict[str, str]] = []
        for item in raw_source_targets:
            if not isinstance(item, dict):
                continue
            source = str(item.get("source") or item.get("from") or "Entity").strip()
            target = str(item.get("target") or item.get("to") or "Entity").strip()
            normalized.append({"source": source, "target": target})
        return normalized[:6]

    @staticmethod
    def _fallback_ontology(text: str) -> dict[str, Any]:
        summary = "Source corpus prepared for graph extraction and social simulation."
        keywords = sorted({token.strip(".,:;!?()[]{}").lower() for token in text.split() if len(token) > 5})
        sample_topics = keywords[:10]
        return {
            "entity_types": [
                {
                    "name": "Person",
                    "description": "A person relevant to the source material.",
                    "attributes": [
                        {"name": "role", "description": "Function or role of the person."},
                        {"name": "stance", "description": "Likely viewpoint or position."},
                    ],
                },
                {
                    "name": "Organization",
                    "description": "An institution, company, or group.",
                    "attributes": [
                        {"name": "sector", "description": "Industry or domain."},
                        {"name": "priority", "description": "Main strategic priority."},
                    ],
                },
                {
                    "name": "Topic",
                    "description": "A major theme or issue in the documents.",
                    "attributes": [
                        {"name": "keywords", "description": "Terms associated with the topic."},
                    ],
                },
                {
                    "name": "Event",
                    "description": "A key event, initiative, or milestone.",
                    "attributes": [
                        {"name": "timeframe", "description": "Approximate timing."},
                    ],
                },
            ],
            "edge_types": [
                {
                    "name": "influences",
                    "description": "One entity shapes the behavior or narrative of another.",
                    "source_targets": [
                        {"source": "Person", "target": "Organization"},
                        {"source": "Organization", "target": "Topic"},
                        {"source": "Organization", "target": "Event"},
                    ],
                    "attributes": [{"name": "mechanism", "description": "How the influence occurs."}],
                },
                {
                    "name": "reacts_to",
                    "description": "An entity reacts to another entity or event.",
                    "source_targets": [
                        {"source": "Person", "target": "Event"},
                        {"source": "Organization", "target": "Event"},
                        {"source": "Person", "target": "Topic"},
                    ],
                    "attributes": [{"name": "sentiment", "description": "Positive, negative, or mixed."}],
                },
                {
                    "name": "aligned_with",
                    "description": "Two entities share a broadly similar stance.",
                    "source_targets": [
                        {"source": "Person", "target": "Organization"},
                        {"source": "Organization", "target": "Topic"},
                    ],
                    "attributes": [{"name": "basis", "description": "Reason for the alignment."}],
                },
            ],
            "analysis_summary": (
                f"{summary} Candidate topics: {', '.join(sample_topics[:6]) or 'general discourse'}."
            ),
        }
