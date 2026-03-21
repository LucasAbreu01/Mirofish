from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from typing import Any

from pydantic import Field
from zep_cloud import EpisodeData, EntityEdgeSourceTarget
from zep_cloud.client import Zep
from zep_cloud.external_clients.ontology import EdgeModel, EntityModel, EntityText

from ..config import settings
from ..models.schemas import GraphSnapshot
from ..utils.json_tools import read_json
from ..utils.logger import get_logger
from ..utils.zep_utils import fetch_all_edges, fetch_all_nodes
from .project_service import ProjectService
from .task_service import TaskService


logger = get_logger("miro_gpt.zep_graph_service")

_RESERVED_ATTRS = {"uuid", "name", "summary", "group_id", "graph_id", "created_at"}


class ZepGraphService:
    _client: Zep | None = None

    @classmethod
    def client(cls) -> Zep:
        settings.require_zep()
        if cls._client is None:
            cls._client = Zep(api_key=settings.zep_api_key)
        return cls._client

    @classmethod
    def build_graph_for_project(cls, project_id: str, task_id: str) -> dict[str, Any]:
        project = ProjectService.get_project(project_id)
        ontology = ProjectService.load_ontology(project_id)
        text = ProjectService.load_extracted_text(project_id)
        graph_id = project["graph_id"] or f"miro_gpt_{project_id}"

        TaskService.update_task(task_id, progress=10, message="Creating graph container in Zep.")
        cls._ensure_graph(graph_id, project["name"])

        TaskService.update_task(task_id, progress=24, message="Applying ontology to graph.")
        cls._set_ontology(graph_id, ontology)

        TaskService.update_task(task_id, progress=38, message="Chunking project text.")
        chunks = cls._chunk_text(text)
        if not chunks:
            raise ValueError("Source text did not produce any chunks for graph ingestion.")

        TaskService.update_task(task_id, progress=48, message="Sending episodes to Zep.")
        batch_status = cls._add_text_batches(graph_id, chunks)

        TaskService.update_task(task_id, progress=72, message="Waiting for Zep to process the graph.")
        cls._wait_for_processing(
            graph_id,
            episode_ids=batch_status["episode_ids"],
            task_ids=batch_status["task_ids"],
        )

        TaskService.update_task(task_id, progress=88, message="Fetching graph snapshot.")
        snapshot = cls.fetch_snapshot(graph_id)
        if snapshot.node_count == 0:
            raise ValueError("The graph built successfully but contains zero useful entities.")

        path = ProjectService.save_graph_snapshot(project_id, snapshot.model_dump(), graph_id)
        return {
            "project_id": project_id,
            "graph_id": graph_id,
            "snapshot_path": str(path),
            "node_count": snapshot.node_count,
            "edge_count": snapshot.edge_count,
        }

    @classmethod
    def get_graph_snapshot(cls, project_id: str) -> dict[str, Any]:
        snapshot = read_json(ProjectService.graph_snapshot_path(project_id), default=None)
        if snapshot is not None:
            return snapshot
        project = ProjectService.get_project(project_id)
        if not project["graph_id"]:
            raise ValueError("Project does not have a graph yet.")
        live_snapshot = cls.fetch_snapshot(project["graph_id"]).model_dump()
        ProjectService.save_graph_snapshot(project_id, live_snapshot, project["graph_id"])
        return live_snapshot

    @classmethod
    def fetch_snapshot(cls, graph_id: str) -> GraphSnapshot:
        nodes = fetch_all_nodes(cls.client(), graph_id)
        edges = fetch_all_edges(cls.client(), graph_id)
        normalized_nodes = [cls._normalize_node(node) for node in nodes]
        normalized_edges = [cls._normalize_edge(edge) for edge in edges]
        entity_types = Counter(
            (node["labels"][0] if node["labels"] else "Entity") for node in normalized_nodes
        )
        return GraphSnapshot(
            graph_id=graph_id,
            node_count=len(normalized_nodes),
            edge_count=len(normalized_edges),
            entity_types=dict(entity_types),
            nodes=normalized_nodes[:300],
            edges=normalized_edges[:600],
        )

    @classmethod
    def search_graph(
        cls,
        graph_id: str,
        query: str,
        *,
        limit: int = 8,
        scope: str = "edges",
    ) -> dict[str, Any]:
        try:
            result = cls.client().graph.search(
                graph_id=graph_id,
                query=query,
                limit=limit,
                scope=scope,
                reranker="cross_encoder",
            )
            return {
                "query": query,
                "facts": [
                    edge.fact
                    for edge in getattr(result, "edges", []) or []
                    if getattr(edge, "fact", None)
                ],
                "nodes": [cls._normalize_node(node) for node in getattr(result, "nodes", []) or []],
                "edges": [cls._normalize_edge(edge) for edge in getattr(result, "edges", []) or []],
            }
        except Exception as error:
            logger.warning("Graph search failed, using local fallback: %s", error)
            return cls._local_search(graph_id, query=query, limit=limit, scope=scope)

    @classmethod
    def rank_entities(cls, snapshot: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        degrees: defaultdict[str, int] = defaultdict(int)
        for edge in snapshot.get("edges", []):
            source = edge.get("source_node_uuid")
            target = edge.get("target_node_uuid")
            if source:
                degrees[source] += 1
            if target:
                degrees[target] += 1

        ranked = []
        for node in snapshot.get("nodes", []):
            labels = node.get("labels") or ["Entity"]
            degree = degrees.get(node.get("uuid", ""), 0)
            summary = node.get("summary") or cls._attributes_to_summary(node.get("attributes", {}))
            ranked.append(
                {
                    **node,
                    "entity_type": labels[0],
                    "degree": degree,
                    "summary": summary,
                }
            )
        ranked.sort(
            key=lambda item: (
                item.get("degree", 0),
                len(item.get("summary", "")),
                item.get("name", ""),
            ),
            reverse=True,
        )
        return ranked[:limit]

    @classmethod
    def _ensure_graph(cls, graph_id: str, name: str) -> None:
        client = cls.client()
        try:
            client.graph.get(graph_id=graph_id)
            return
        except Exception:
            pass
        try:
            client.graph.create(
                graph_id=graph_id,
                name=name,
                description="Miro_GPT project graph",
            )
        except TypeError:
            client.graph.create(name=name, graph_id=graph_id, description="Miro_GPT project graph")

    @classmethod
    def _set_ontology(cls, graph_id: str, ontology: dict[str, Any]) -> None:
        import warnings
        from typing import Optional

        warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
        entity_types: dict[str, Any] = {}
        edge_types: dict[str, Any] = {}

        for entity_def in ontology.get("entity_types", []):
            entity_name = cls._to_pascal_case(entity_def["name"])
            attrs: dict[str, Any] = {"__doc__": entity_def.get("description", "")}
            annotations: dict[str, Any] = {}
            entity_attributes = cls._ensure_custom_attributes(
                entity_def.get("attributes", []),
                fallback_name="context_hint",
                fallback_description=f"Additional context that helps classify {entity_name}.",
            )
            for attr in entity_attributes:
                attr_name = cls._safe_attr_name(attr.get("name", "attribute"))
                attrs[attr_name] = Field(
                    default=None,
                    description=attr.get("description", attr_name),
                )
                annotations[attr_name] = Optional[EntityText]
            attrs["__annotations__"] = annotations
            entity_types[entity_name] = type(entity_name, (EntityModel,), attrs)

        for edge_def in ontology.get("edge_types", []):
            edge_name = cls._to_screaming_snake_case(edge_def["name"])
            attrs = {"__doc__": edge_def.get("description", "")}
            annotations: dict[str, Any] = {}
            edge_attributes = cls._ensure_custom_attributes(
                edge_def.get("attributes", []),
                fallback_name="relationship_context",
                fallback_description=f"Additional context for the {edge_name} relationship.",
            )
            for attr in edge_attributes:
                attr_name = cls._safe_attr_name(attr.get("name", "attribute"))
                attrs[attr_name] = Field(
                    default=None,
                    description=attr.get("description", attr_name),
                )
                annotations[attr_name] = Optional[str]
            attrs["__annotations__"] = annotations
            class_name = "".join(part.capitalize() for part in edge_name.split("_"))
            edge_model = type(class_name, (EdgeModel,), attrs)
            source_targets = [
                EntityEdgeSourceTarget(
                    source=cls._to_pascal_case(item.get("source", "Entity")),
                    target=cls._to_pascal_case(item.get("target", "Entity")),
                )
                for item in edge_def.get("source_targets", [])
            ]
            if source_targets:
                edge_types[edge_name] = (edge_model, source_targets)

        cls.client().graph.set_ontology(
            graph_ids=[graph_id],
            entities=entity_types or None,
            edges=edge_types or None,
        )

    @classmethod
    def _add_text_batches(
        cls,
        graph_id: str,
        chunks: list[str],
        batch_size: int = 3,
    ) -> dict[str, list[str]]:
        episode_ids: list[str] = []
        task_ids: list[str] = []
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            episodes = [EpisodeData(data=chunk, type="text") for chunk in batch]
            result = cls.client().graph.add_batch(graph_id=graph_id, episodes=episodes)
            for item in result or []:
                episode_id = getattr(item, "uuid_", None) or getattr(item, "uuid", None)
                if episode_id:
                    episode_ids.append(str(episode_id))
                task_id = getattr(item, "task_id", None)
                if task_id and str(task_id) not in task_ids:
                    task_ids.append(str(task_id))
            time.sleep(0.5)
        return {"episode_ids": episode_ids, "task_ids": task_ids}

    @classmethod
    def _wait_for_processing(
        cls,
        graph_id: str,
        episode_ids: list[str],
        task_ids: list[str],
        timeout: int = 180,
    ) -> None:
        started = time.time()
        while time.time() - started < timeout:
            if task_ids:
                all_completed = True
                for task_id in task_ids:
                    task = cls.client().task.get(task_id=task_id)
                    status = str(getattr(task, "status", "") or "").strip().lower()
                    if status == "failed":
                        raise ValueError(
                            f"Zep batch ingestion failed for task {task_id}: {getattr(task, 'error', 'Unknown error')}"
                        )
                    if status not in {"completed", "succeeded"}:
                        all_completed = False
                        break
                if all_completed:
                    snapshot = cls.fetch_snapshot(graph_id)
                    if snapshot.node_count > 0:
                        return

            snapshot = cls.fetch_snapshot(graph_id)
            if snapshot.node_count > 0:
                return
            if episode_ids:
                try:
                    any_processed = False
                    for episode_id in episode_ids[:5]:
                        episode = cls.client().graph.episode.get(uuid_=episode_id)
                        if getattr(episode, "processed", False):
                            any_processed = True
                            break
                    if any_processed:
                        time.sleep(3)
                        continue
                except Exception:
                    pass
            time.sleep(4)
        logger.warning("Timed out waiting for graph processing. Continuing with current state.")

    @staticmethod
    def _chunk_text(text: str, size: int = 3500, overlap: int = 250) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return []
        chunks: list[str] = []
        index = 0
        while index < len(normalized):
            end = min(len(normalized), index + size)
            chunk = normalized[index:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == len(normalized):
                break
            index = max(end - overlap, index + 1)
        return chunks

    @classmethod
    def _local_search(cls, graph_id: str, query: str, limit: int, scope: str) -> dict[str, Any]:
        snapshot = cls.fetch_snapshot(graph_id).model_dump()
        query_lower = query.lower()
        tokens = [token for token in query_lower.replace(",", " ").split() if len(token) > 2]

        def score(text: str) -> int:
            lower = text.lower()
            total = 0
            if query_lower in lower:
                total += 100
            for token in tokens:
                if token in lower:
                    total += 8
            return total

        nodes = []
        edges = []
        facts = []
        if scope in {"nodes", "both"}:
            scored_nodes = sorted(
                (
                    (score(f"{node.get('name', '')} {node.get('summary', '')}"), node)
                    for node in snapshot.get("nodes", [])
                ),
                key=lambda item: item[0],
                reverse=True,
            )
            nodes = [item[1] for item in scored_nodes if item[0] > 0][:limit]
            facts.extend(
                f"[{node.get('name', 'Entity')}] {node.get('summary', '')}".strip() for node in nodes
            )
        if scope in {"edges", "both"}:
            scored_edges = sorted(
                (
                    (
                        score(
                            f"{edge.get('name', '')} {edge.get('fact', '')} "
                            f"{edge.get('source_name', '')} {edge.get('target_name', '')}"
                        ),
                        edge,
                    )
                    for edge in snapshot.get("edges", [])
                ),
                key=lambda item: item[0],
                reverse=True,
            )
            edges = [item[1] for item in scored_edges if item[0] > 0][:limit]
            facts.extend(edge.get("fact", "") for edge in edges if edge.get("fact"))
        return {"query": query, "facts": facts[:limit], "nodes": nodes, "edges": edges}

    @staticmethod
    def _safe_attr_name(value: str) -> str:
        clean = value.lower().replace(" ", "_").replace("-", "_")
        if clean in _RESERVED_ATTRS:
            return f"entity_{clean}"
        return clean

    @staticmethod
    def _ensure_custom_attributes(
        attributes: list[dict[str, Any]] | None,
        *,
        fallback_name: str,
        fallback_description: str,
    ) -> list[dict[str, Any]]:
        if attributes:
            return attributes
        return [{"name": fallback_name, "description": fallback_description}]

    @staticmethod
    def _to_screaming_snake_case(value: str) -> str:
        text = str(value or "ENTITY").strip()
        text = text.replace("-", "_").replace(" ", "_")
        text = text.replace("/", "_")
        text = text.replace("__", "_")
        text = "".join(f"_{char}" if char.isupper() and index > 0 and text[index - 1].islower() else char for index, char in enumerate(text))
        text = re.sub(r"[^A-Za-z0-9_]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text.upper() or "ENTITY"

    @staticmethod
    def _to_pascal_case(value: str) -> str:
        text = str(value or "Entity").strip()
        text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
        parts = re.split(r"[^A-Za-z0-9]+", text)
        normalized = "".join(part[:1].upper() + part[1:].lower() for part in parts if part)
        return normalized or "Entity"

    @staticmethod
    def _normalize_node(node: Any) -> dict[str, Any]:
        return {
            "uuid": str(getattr(node, "uuid_", None) or getattr(node, "uuid", "") or ""),
            "name": getattr(node, "name", "") or "",
            "labels": list(getattr(node, "labels", []) or []),
            "summary": getattr(node, "summary", "") or "",
            "attributes": dict(getattr(node, "attributes", {}) or {}),
        }

    @staticmethod
    def _normalize_edge(edge: Any) -> dict[str, Any]:
        return {
            "uuid": str(getattr(edge, "uuid_", None) or getattr(edge, "uuid", "") or ""),
            "name": getattr(edge, "name", "") or "",
            "fact": getattr(edge, "fact", "") or "",
            "source_node_uuid": getattr(edge, "source_node_uuid", "") or "",
            "target_node_uuid": getattr(edge, "target_node_uuid", "") or "",
            "source_name": getattr(edge, "source_name", "") or "",
            "target_name": getattr(edge, "target_name", "") or "",
            "attributes": dict(getattr(edge, "attributes", {}) or {}),
        }

    @staticmethod
    def _attributes_to_summary(attributes: dict[str, Any]) -> str:
        if not attributes:
            return ""
        parts = [f"{key}: {value}" for key, value in list(attributes.items())[:4] if value]
        return "; ".join(parts)
