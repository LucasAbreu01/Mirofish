from __future__ import annotations

import json
from typing import Any

import networkx as nx
from networkx.readwrite import json_graph

from app.models.schemas import KnowledgeGraph
from app.utils.logger import get_logger

logger = get_logger("mirofish.knowledge_graph")


class KnowledgeGraphManager:
    """Thin wrapper around a :class:`networkx.DiGraph` that provides
    serialisation helpers and agent-oriented queries.
    """

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_extraction(cls, kg: KnowledgeGraph) -> KnowledgeGraphManager:
        """Build a :class:`KnowledgeGraphManager` from extracted entities and
        relationships.
        """
        mgr = cls()
        for entity in kg.entities:
            mgr.graph.add_node(
                entity.name,
                entity_type=entity.entity_type,
                description=entity.description,
                attributes=entity.attributes,
            )
        for edge in kg.relationships:
            # Ensure both endpoints exist.
            if edge.source not in mgr.graph:
                mgr.graph.add_node(edge.source, entity_type="Unknown", description="", attributes={})
            if edge.target not in mgr.graph:
                mgr.graph.add_node(edge.target, entity_type="Unknown", description="", attributes={})
            mgr.graph.add_edge(
                edge.source,
                edge.target,
                relation_type=edge.relation_type,
                description=edge.description,
            )
        logger.info(
            "Built graph with %d nodes and %d edges",
            mgr.graph.number_of_nodes(),
            mgr.graph.number_of_edges(),
        )
        return mgr

    # ------------------------------------------------------------------
    # Serialisation – dict / JSON
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialise the graph for frontend D3.js visualisation."""
        nodes = []
        for name, data in self.graph.nodes(data=True):
            nodes.append({
                "id": name,
                "type": data.get("entity_type", "Unknown"),
                "description": data.get("description", ""),
                "attributes": data.get("attributes", {}),
            })
        edges = []
        for source, target, data in self.graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "type": data.get("relation_type", ""),
                "description": data.get("description", ""),
            })
        return {"nodes": nodes, "edges": edges}

    def to_json(self) -> str:
        """Serialise to a JSON string using NetworkX ``node_link_data``."""
        return json.dumps(json_graph.node_link_data(self.graph))

    @classmethod
    def from_json(cls, json_str: str) -> KnowledgeGraphManager:
        """Deserialise from a JSON string produced by :meth:`to_json`."""
        mgr = cls()
        data = json.loads(json_str)
        mgr.graph = json_graph.node_link_graph(data, directed=True)
        return mgr

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_node(self, name: str) -> dict[str, Any] | None:
        """Return attributes for *name*, or ``None`` if it does not exist."""
        if name not in self.graph:
            return None
        data = dict(self.graph.nodes[name])
        data["name"] = name
        return data

    def get_neighbors(self, name: str) -> list[dict[str, Any]]:
        """Return connected entities with relationship info."""
        if name not in self.graph:
            return []

        results: list[dict[str, Any]] = []
        # Outgoing edges
        for _, target, edge_data in self.graph.out_edges(name, data=True):
            node_data = dict(self.graph.nodes[target])
            results.append({
                "name": target,
                "direction": "outgoing",
                "relation_type": edge_data.get("relation_type", ""),
                "relation_description": edge_data.get("description", ""),
                **node_data,
            })
        # Incoming edges
        for source, _, edge_data in self.graph.in_edges(name, data=True):
            node_data = dict(self.graph.nodes[source])
            results.append({
                "name": source,
                "direction": "incoming",
                "relation_type": edge_data.get("relation_type", ""),
                "relation_description": edge_data.get("description", ""),
                **node_data,
            })
        return results

    def get_context_for_agent(self, entity_name: str) -> str:
        """Build a natural-language summary of *entity_name* and its
        relationships, suitable for inclusion in an agent prompt.
        """
        node = self.get_node(entity_name)
        if node is None:
            return f"{entity_name}: no additional context available."

        lines = [
            f"Entity: {entity_name}",
            f"Type: {node.get('entity_type', 'Unknown')}",
            f"Description: {node.get('description', 'N/A')}",
        ]

        attrs = node.get("attributes", {})
        if attrs:
            lines.append("Attributes: " + ", ".join(f"{k}={v}" for k, v in attrs.items()))

        neighbors = self.get_neighbors(entity_name)
        if neighbors:
            lines.append("Relationships:")
            for n in neighbors:
                direction = "->" if n["direction"] == "outgoing" else "<-"
                lines.append(
                    f"  {direction} {n['name']} ({n.get('relation_type', '')}): "
                    f"{n.get('relation_description', '')}"
                )

        return "\n".join(lines)

    def get_agent_candidates(self, count: int) -> list[str]:
        """Return the top *count* entity names most suitable for becoming
        simulation agents.

        Priority:
        1. Person / Organisation types.
        2. Higher connection count (degree).
        """
        scored: list[tuple[str, int]] = []
        for name, data in self.graph.nodes(data=True):
            entity_type = (data.get("entity_type") or "").lower()
            priority_bonus = 1000 if entity_type in ("person", "organization", "organisation") else 0
            degree = self.graph.degree(name)  # type: ignore[arg-type]
            scored.append((name, priority_bonus + degree))

        scored.sort(key=lambda t: t[1], reverse=True)
        return [name for name, _ in scored[:count]]
