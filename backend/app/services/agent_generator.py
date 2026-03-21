from __future__ import annotations

import json

from app.models.schemas import AgentProfile
from app.services.knowledge_graph import KnowledgeGraphManager
from app.utils.llm_client import llm_client
from app.utils.logger import get_logger

logger = get_logger("mirofish.agent_generator")

# ── Prompt: entity-based (legacy) ────────────────────────────────────────
_SYSTEM_PROMPT_ENTITY = """\
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

# ── Prompt: role-based (new) ─────────────────────────────────────────────
_SYSTEM_PROMPT_ROLE = """\
You are a character designer for a multi-agent social simulation.

IMPORTANT: The document entities listed below are BACKGROUND CONTEXT — they \
describe the case, situation, or subject matter that the simulation is about. \
They are NOT the participants.

Your job is to create simulation PARTICIPANTS who will discuss, debate, or \
interact around this context. The participant roles are defined by the \
scenario and/or the explicit role list provided by the user.

For EACH participant, create a profile with these fields:
- name (string): A realistic, unique name for this participant.
- entity_type (string): Always "Person" for role-based agents.
- personality (string, 200–400 characters): A vivid personality description \
that reflects their professional background and how they approach the subject.
- goals (string): What this participant wants to achieve in the simulation.
- backstory (string): A brief professional backstory (2–3 sentences) that \
explains their expertise and perspective on the case.
- age (integer or null): Approximate age.
- profession (string): Their specific role or specialization.
- communication_style (string): e.g. formal, casual, analytical, empathetic.

Each participant must have a DISTINCT perspective and approach. Avoid making \
them all agree — create diversity of opinion and methodology.

Return ONLY valid JSON — an array of profile objects (no markdown fences):
[
  {"name": "...", "entity_type": "Person", "personality": "...", "goals": "...", \
"backstory": "...", "age": null, "profession": "...", "communication_style": "..."}
]
"""


async def generate_agents(
    graph: KnowledgeGraphManager,
    count: int,
    scenario: str,
    agent_roles: str = "",
) -> list[AgentProfile]:
    """Generate *count* :class:`AgentProfile` objects.

    Two modes:
    - **Role-based** (when *agent_roles* is provided): creates participants
      matching the requested roles, using graph entities as background context.
    - **Entity-based** (fallback): promotes graph entities to agents directly.
    """
    if agent_roles.strip():
        return await _generate_role_based(graph, count, scenario, agent_roles)
    return await _generate_entity_based(graph, count, scenario)


async def _generate_role_based(
    graph: KnowledgeGraphManager,
    count: int,
    scenario: str,
    agent_roles: str,
) -> list[AgentProfile]:
    """Create agents matching explicit roles, with graph data as context."""
    # Summarise ALL graph entities as background knowledge.
    context_blocks: list[str] = []
    for name, data in graph.graph.nodes(data=True):
        desc = data.get("description", "")
        etype = data.get("entity_type", "")
        context_blocks.append(f"- {name} ({etype}): {desc}")
    context_text = "\n".join(context_blocks) if context_blocks else "(No background data.)"

    user_prompt = (
        f"Scenario: {scenario}\n\n"
        f"Requested participant roles:\n{agent_roles}\n\n"
        f"Number of participants to create: {count}\n\n"
        f"Background context from documents (use as knowledge, NOT as participants):\n"
        f"{context_text}\n\n"
        f"Generate {count} participant profiles matching the roles above."
    )

    return await _call_llm_for_profiles(
        system_prompt=_SYSTEM_PROMPT_ROLE,
        user_prompt=user_prompt,
        fallback_fn=lambda: _fallback_role_profiles(count, agent_roles),
    )


async def _generate_entity_based(
    graph: KnowledgeGraphManager,
    count: int,
    scenario: str,
) -> list[AgentProfile]:
    """Legacy mode: promote graph entities to agents."""
    candidates = graph.get_agent_candidates(count)
    if not candidates:
        logger.warning("No candidates found in graph")
        return []

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

    return await _call_llm_for_profiles(
        system_prompt=_SYSTEM_PROMPT_ENTITY,
        user_prompt=user_prompt,
        fallback_fn=lambda: _fallback_profiles(graph, candidates),
    )


async def _call_llm_for_profiles(
    system_prompt: str,
    user_prompt: str,
    fallback_fn,
) -> list[AgentProfile]:
    """Shared LLM call + parsing logic for both generation modes."""
    try:
        raw = await llm_client.achat(
            messages=[
                {"role": "system", "content": system_prompt},
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
        return fallback_fn()


def _fallback_role_profiles(count: int, agent_roles: str) -> list[AgentProfile]:
    """Minimal fallback when role-based LLM call fails."""
    roles = [r.strip() for r in agent_roles.replace(",", "\n").splitlines() if r.strip()]
    profiles: list[AgentProfile] = []
    for i in range(count):
        role = roles[i % len(roles)] if roles else f"Participant {i + 1}"
        profiles.append(
            AgentProfile(
                name=f"Agent_{i + 1}",
                entity_type="Person",
                personality=f"A professional with expertise as {role}.",
                goals="Participate in the simulation and share professional insights.",
                backstory=f"An experienced {role} contributing to the discussion.",
                profession=role,
                communication_style="neutral",
            )
        )
    logger.info("Created %d fallback role-based profiles", len(profiles))
    return profiles


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
