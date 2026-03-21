from __future__ import annotations

from app.models.schemas import AgentProfile, ChatMessage, SimulationAction
from app.utils.llm_client import llm_client
from app.utils.logger import get_logger

logger = get_logger("mirofish.report_generator")

_REPORT_SYSTEM_PROMPT = """\
You are an expert analyst reviewing a multi-agent social simulation.
Given the scenario, agent profiles, and the full action log, produce a \
structured markdown report.

The report MUST contain these sections:
## Executive Summary
## Key Findings
## Agent Behavior Analysis
## Emergent Patterns
## Conclusions

Be insightful, specific, and reference concrete actions from the log.
"""

_CHAT_SYSTEM_PROMPT = """\
You are a helpful analyst assistant.  You have access to a simulation report \
and can answer questions about it.  Be concise and reference the report where \
relevant.
"""


async def generate_report(
    actions: list[SimulationAction],
    agents: list[AgentProfile],
    scenario: str,
) -> str:
    """Summarise the simulation into a structured markdown report.

    Makes a single LLM call using the *heavy* model.
    """
    # Build agent summary.
    agent_lines = []
    for a in agents:
        agent_lines.append(f"- {a.name} ({a.profession}): {a.personality[:120]}")
    agent_summary = "\n".join(agent_lines)

    # Build readable action log.
    log_lines = []
    for act in actions:
        target = f" -> {act.target_message_id}" if act.target_message_id else ""
        log_lines.append(
            f"[Round {act.round}] {act.agent_name} ({act.action_type}{target}): {act.content}"
        )
    action_text = "\n".join(log_lines)

    user_prompt = (
        f"Scenario: {scenario}\n\n"
        f"Agents:\n{agent_summary}\n\n"
        f"Action Log ({len(actions)} actions):\n{action_text}"
    )

    try:
        report = await llm_client.achat(
            messages=[
                {"role": "system", "content": _REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model="heavy",
            max_tokens=4000,
        )
        logger.info("Report generated (%d chars)", len(report))
        return report
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        return (
            "## Report Generation Failed\n\n"
            f"An error occurred while generating the report: {exc}\n\n"
            f"The simulation ran {len(actions)} actions across "
            f"{agents[-1].name if agents else 'unknown'} agents."
        )


async def chat_with_report(
    report: str,
    question: str,
    history: list[ChatMessage],
) -> str:
    """Answer a follow-up question about a simulation report.

    Uses the *light* model with the report as context and prior conversation
    history.
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _CHAT_SYSTEM_PROMPT + f"\n\nReport:\n{report}"},
    ]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": question})

    try:
        answer = await llm_client.achat(
            messages=messages,
            model="light",
            max_tokens=1500,
        )
        return answer
    except Exception as exc:
        logger.error("Chat with report failed: %s", exc)
        return f"Sorry, I was unable to answer your question: {exc}"
