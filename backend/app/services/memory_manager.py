from __future__ import annotations

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("mirofish.memory_manager")


class MemoryManager:
    """Per-agent episodic memory store.

    Each agent maintains an ordered list of event strings.  The list is
    automatically trimmed to :pyattr:`settings.AGENT_MEMORY_LIMIT` entries.
    """

    def __init__(self) -> None:
        self.memories: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def add_event(self, agent_name: str, event: str) -> None:
        """Append *event* to the agent's memory, trimming old entries."""
        if agent_name not in self.memories:
            self.memories[agent_name] = []
        self.memories[agent_name].append(event)
        # Keep only the most recent entries.
        limit = settings.AGENT_MEMORY_LIMIT
        if len(self.memories[agent_name]) > limit:
            self.memories[agent_name] = self.memories[agent_name][-limit:]

    def get_memories(self, agent_name: str) -> list[str]:
        """Return the agent's memory list (empty list if none)."""
        return self.memories.get(agent_name, [])

    def get_context(self, agent_name: str) -> str:
        """Format the agent's memories as a numbered list for prompts."""
        mems = self.get_memories(agent_name)
        if not mems:
            return "No memories yet."
        return "\n".join(f"{i}. {m}" for i, m in enumerate(mems, 1))

    def clear(self, agent_name: str) -> None:
        """Clear all memories for *agent_name*."""
        self.memories.pop(agent_name, None)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, list[str]]:
        """Return a plain-dict copy suitable for JSON serialisation."""
        return {k: list(v) for k, v in self.memories.items()}

    @classmethod
    def from_dict(cls, data: dict[str, list[str]]) -> MemoryManager:
        """Reconstruct a :class:`MemoryManager` from serialised data."""
        mgr = cls()
        mgr.memories = {k: list(v) for k, v in data.items()}
        return mgr
