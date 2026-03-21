from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from app.models.schemas import AgentProfile, SimulationAction, SimulationState
from app.services.memory_manager import MemoryManager
from app.utils.llm_client import llm_client
from app.utils.logger import get_logger

logger = get_logger("mirofish.simulation_engine")

_VALID_ACTIONS = {"POST_MESSAGE", "REPLY", "REACT", "FORM_OPINION", "DO_NOTHING"}


class SimulationEngine:
    """Core multi-agent simulation loop.

    Each round, every agent is given a turn (in random order) to observe the
    shared discussion feed and choose an action via an LLM call.
    """

    def __init__(
        self,
        agents: list[AgentProfile],
        scenario: str,
        graph_context: str = "",
    ) -> None:
        self.agents = agents
        self.scenario = scenario
        self.graph_context = graph_context
        self.memory = MemoryManager()
        self.action_log: list[SimulationAction] = []
        self.shared_feed: list[dict[str, Any]] = []
        self.current_round = 0
        self.total_rounds = 0
        self.status = "idle"  # idle | running | completed | error
        self.simulation_id: str = str(uuid.uuid4())
        self._event_callbacks: list[Callable] = []

    # ------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------

    def add_event_callback(self, callback: Callable) -> None:
        self._event_callbacks.append(callback)

    async def _emit(self, event: dict[str, Any]) -> None:
        for cb in self._event_callbacks:
            await cb(event)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self, num_rounds: int) -> None:
        """Execute the simulation for *num_rounds* rounds."""
        self.total_rounds = num_rounds
        self.status = "running"
        try:
            for round_num in range(1, num_rounds + 1):
                self.current_round = round_num
                await self._emit({"type": "round_start", "round": round_num, "total_rounds": num_rounds})

                shuffled = random.sample(self.agents, len(self.agents))
                for agent in shuffled:
                    action = await self._agent_turn(agent, round_num, num_rounds)
                    self.action_log.append(action)

                    if action.action_type != "DO_NOTHING":
                        feed_entry: dict[str, Any] = {
                            "id": f"msg_{len(self.shared_feed)}",
                            "agent": action.agent_name,
                            "content": action.content,
                            "type": action.action_type,
                            "round": round_num,
                            "target": action.target_message_id,
                        }
                        self.shared_feed.append(feed_entry)

                    self.memory.add_event(
                        agent.name,
                        self._format_action_as_memory(action),
                    )
                    await self._emit({"type": "action", "action": action.model_dump()})

                await self._emit({"type": "round_end", "round": round_num})

            self.status = "completed"
            await self._emit({"type": "simulation_end"})
        except Exception as exc:
            self.status = "error"
            await self._emit({"type": "error", "message": str(exc)})
            raise

    # ------------------------------------------------------------------
    # Agent turn
    # ------------------------------------------------------------------

    async def _agent_turn(
        self,
        agent: AgentProfile,
        round_num: int,
        total_rounds: int,
    ) -> SimulationAction:
        """Execute a single agent's turn and return the resulting action."""
        system_prompt = self._build_system_prompt(agent)
        user_prompt = self._build_user_prompt(agent, round_num, total_rounds)

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            logger.debug(
                "Agent %s prompt lengths: system=%d user=%d",
                agent.name,
                len(system_prompt),
                len(user_prompt),
            )
            raw = await llm_client.achat(
                messages=messages,
                model="light",
                json_mode=True,
                max_tokens=1000,
            )
            logger.debug("Agent %s raw response: %r", agent.name, raw[:200] if raw else "(empty)")

            data = json.loads(raw)
            action_type = data.get("action", "DO_NOTHING").upper()
            if action_type not in _VALID_ACTIONS:
                action_type = "DO_NOTHING"

            return SimulationAction(
                round=round_num,
                agent_name=agent.name,
                action_type=action_type,
                content=data.get("content", ""),
                target_message_id=data.get("target_message_id"),
                reasoning=data.get("reasoning", ""),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as exc:
            logger.warning(
                "Agent %s turn failed (round %d): %s — defaulting to DO_NOTHING",
                agent.name,
                round_num,
                exc,
            )
            return SimulationAction(
                round=round_num,
                agent_name=agent.name,
                action_type="DO_NOTHING",
                content="",
                reasoning=f"Error: {exc}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_system_prompt(self, agent: AgentProfile) -> str:
        lines = [
            f"You are {agent.name}, a {agent.profession}.",
            f"Personality: {agent.personality}",
            f"Goals: {agent.goals}",
            f"Backstory: {agent.backstory}",
            f"Communication style: {agent.communication_style}",
            "",
            f"You are participating in a social simulation about: {self.scenario}",
        ]
        return "\n".join(lines)

    def _build_user_prompt(
        self,
        agent: AgentProfile,
        round_num: int,
        total_rounds: int,
    ) -> str:
        memory_ctx = self.memory.get_context(agent.name)
        recent_feed = self.shared_feed[-10:]
        feed_lines = []
        for item in recent_feed:
            prefix = f"[{item['type']}] {item['agent']}"
            if item.get("target"):
                prefix += f" (re: {item['target']})"
            feed_lines.append(f"{prefix}: {item['content']}")
        feed_text = "\n".join(feed_lines) if feed_lines else "(No messages yet.)"

        return (
            f"Your recent memories:\n{memory_ctx}\n\n"
            f"Current discussion feed (most recent messages):\n{feed_text}\n\n"
            f"It is round {round_num} of {total_rounds}. Choose ONE action and respond in JSON:\n"
            "Available actions: POST_MESSAGE, REPLY, REACT, FORM_OPINION, DO_NOTHING\n"
            "- POST_MESSAGE: Share a new thought or statement\n"
            "- REPLY: Respond to a specific message (set target_message_id)\n"
            "- REACT: Express agreement/disagreement/surprise to a message\n"
            "- FORM_OPINION: Form an internal opinion (not shared publicly)\n"
            "- DO_NOTHING: Observe without acting\n\n"
            "Respond ONLY with valid JSON:\n"
            '{"action": "...", "content": "...", "target_message_id": null, '
            '"reasoning": "brief 1-sentence reasoning"}'
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_action_as_memory(action: SimulationAction) -> str:
        """Convert an action into a short memory string."""
        if action.action_type == "DO_NOTHING":
            return f"Round {action.round}: I observed without acting."
        if action.action_type == "FORM_OPINION":
            return f"Round {action.round}: I formed an opinion — {action.content}"
        target = f" (replying to {action.target_message_id})" if action.target_message_id else ""
        return f"Round {action.round}: I {action.action_type.lower().replace('_', ' ')}{target} — {action.content}"

    def get_state(self) -> SimulationState:
        """Return the current simulation state snapshot."""
        return SimulationState(
            simulation_id=self.simulation_id,
            status=self.status,
            current_round=self.current_round,
            total_rounds=self.total_rounds,
            total_actions=len(self.action_log),
            recent_actions=self.action_log[-10:],
        )

    def get_actions(self) -> list[SimulationAction]:
        """Return the full action log."""
        return list(self.action_log)
