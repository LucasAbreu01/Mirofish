from __future__ import annotations

import json

from app.models.schemas import AgentProfile
from app.services.knowledge_graph import KnowledgeGraphManager
from app.utils.llm_client import llm_client
from app.utils.logger import get_logger

logger = get_logger("mirofish.agent_generator")

_SYSTEM_PROMPT = """\
You are a character designer for a multi-agent social simulation.
Given a set of entity descriptions extracted from a knowledge graph and a \
simulation scenario, generate rich agent profiles.

For EACH entity provided, create a profile with these fields:
- name (string): The entity's name.
- entity_type (string): Person, Organization, Concept, etc.
- personality (string, 200–400 characters): A vivid personality description.
- goals (string): What the agent wants to achieve in the simulation.
- backstory (string): A brief backstory (2–3 sentences).
- age (integer or null): Approximate age if applicable.
- profession (string): Role or profession.
- communication_style (string): e.g. formal, casual, aggressive, diplomatic.

Return ONLY valid JSON — an array of profile objects (no markdown fences):
[
  {"name": "...", "entity_type": "...", "personality": "...", "goals": "...", \
"backstory": "...", "age": null, "profession": "...", "communication_style": "..."}
]
"""


async def generate_agents(
    graph: KnowledgeGraphManager,
    count: int,
    scenario: str,
) -> list[AgentProfile]:
    """Generate *count* :class:`AgentProfile` objects from the knowledge graph.

    A single batched LLM call creates all profiles at once.  If the call
    fails, basic fallback profiles are constructed from graph node attributes.
    """
    candidates = graph.get_agent_candidates(count)
    if not candidates:
        logger.warning("No candidates found in graph")
        return []

    # Build context block for every candidate.
    context_blocks: list[str] = []
    for name in candidates:
        ctx = graph.get_context_for_agent(name)
        context_blocks.append(ctx)

    user_prompt = (
        f"Scenario: {scenario}\n\n"
        "Entity contexts:\n"
        + "\n---\n".join(context_blocks)
        + "\n\nGenerate a profile for EACH entity above."
    )

    try:
        raw = await llm_client.achat(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model="heavy",
            json_mode=True,
            max_tokens=4000,
        )

        profiles_data = json.loads(raw)

        # The model may wrap the array in a key; handle both cases.
        if isinstance(profiles_data, dict):
            profiles_data = (
                profiles_data.get("agents")
                or profiles_data.get("profiles")
                or next(iter(profiles_data.values()))
            )

        profiles: list[AgentProfile] = []
        for p in profiles_data:
            profiles.append(
                AgentProfile(
                    name=p["name"],
                    entity_type=p.get("entity_type", "Unknown"),
                    personality=p.get("personality", ""),
                    goals=p.get("goals", ""),
                    backstory=p.get("backstory", ""),
                    age=p.get("age"),
                    profession=p.get("profession", ""),
                    communication_style=p.get("communication_style", "neutral"),
                )
            )

        logger.info("Generated %d agent profiles via LLM", len(profiles))
        return profiles

    except Exception as exc:
        logger.error("Agent generation LLM call failed: %s — using fallback profiles", exc)
        return _fallback_profiles(graph, candidates)


def _fallback_profiles(
    graph: KnowledgeGraphManager,
    candidates: list[str],
) -> list[AgentProfile]:
    """Create minimal profiles from graph node attributes when the LLM fails."""
    profiles: list[AgentProfile] = []
    for name in candidates:
        node = graph.get_node(name)
        if node is None:
            continue
        profiles.append(
            AgentProfile(
                name=name,
                entity_type=node.get("entity_type", "Unknown"),
                personality=node.get("description", "A participant in the simulation."),
                goals="Participate in the simulation and interact with others.",
                backstory=node.get("description", ""),
                profession=node.get("attributes", {}).get("profession", "Unknown"),
                communication_style="neutral",
            )
        )
    logger.info("Created %d fallback agent profiles", len(profiles))
    return profiles
