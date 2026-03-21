from __future__ import annotations

import numpy as np
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("mirofish.memory")

# Lazy-load the embedding model (only when first needed)
_model = None

def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded embedding model: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning("sentence-transformers not installed, falling back to keyword memory")
            _model = "unavailable"
    return _model if _model != "unavailable" else None


class MemoryManager:
    """Per-agent memory with semantic search capability."""

    def __init__(self) -> None:
        self.memories: dict[str, list[str]] = {}
        self._embeddings: dict[str, list[np.ndarray]] = {}

    def add_event(self, agent_name: str, event: str) -> None:
        if agent_name not in self.memories:
            self.memories[agent_name] = []
            self._embeddings[agent_name] = []

        self.memories[agent_name].append(event)

        # Compute embedding if model available
        model = _get_model()
        if model:
            embedding = model.encode(event, convert_to_numpy=True)
            self._embeddings[agent_name].append(embedding)

        # Trim to limit
        limit = settings.AGENT_MEMORY_LIMIT
        if len(self.memories[agent_name]) > limit:
            self.memories[agent_name] = self.memories[agent_name][-limit:]
            if agent_name in self._embeddings:
                self._embeddings[agent_name] = self._embeddings[agent_name][-limit:]

    def get_memories(self, agent_name: str) -> list[str]:
        return self.memories.get(agent_name, [])

    def get_context(self, agent_name: str) -> str:
        memories = self.get_memories(agent_name)
        if not memories:
            return "(No memories yet.)"
        return "\n".join(f"{i+1}. {m}" for i, m in enumerate(memories))

    def semantic_search(self, agent_name: str, query: str, top_k: int = 5) -> list[str]:
        """Search agent's memory by semantic similarity. Returns top_k most relevant memories."""
        memories = self.memories.get(agent_name, [])
        if not memories:
            return []

        model = _get_model()
        if not model or agent_name not in self._embeddings or not self._embeddings[agent_name]:
            # Fallback: return most recent memories
            return memories[-top_k:]

        query_embedding = model.encode(query, convert_to_numpy=True)
        embeddings = np.array(self._embeddings[agent_name])

        # Cosine similarity
        similarities = np.dot(embeddings, query_embedding) / (
            np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding) + 1e-8
        )

        # Get top_k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [memories[i] for i in top_indices if similarities[i] > 0.1]

    def get_relevant_context(self, agent_name: str, current_topic: str, top_k: int = 5) -> str:
        """Get memories most relevant to the current topic."""
        relevant = self.semantic_search(agent_name, current_topic, top_k)
        if not relevant:
            return self.get_context(agent_name)
        return "\n".join(f"{i+1}. {m}" for i, m in enumerate(relevant))

    def clear(self, agent_name: str) -> None:
        self.memories.pop(agent_name, None)
        self._embeddings.pop(agent_name, None)

    def to_dict(self) -> dict:
        return {"memories": self.memories}

    @classmethod
    def from_dict(cls, data: dict) -> MemoryManager:
        mgr = cls()
        mgr.memories = data.get("memories", {})
        # Re-compute embeddings from loaded memories
        model = _get_model()
        if model:
            for agent, mems in mgr.memories.items():
                if mems:
                    mgr._embeddings[agent] = [model.encode(m, convert_to_numpy=True) for m in mems]
        return mgr
