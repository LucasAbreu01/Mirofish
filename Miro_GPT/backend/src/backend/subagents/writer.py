from __future__ import annotations

from typing import Any

from ..config import settings
from ..models.schemas import ReportDraft, ReportSection
from ..services.llm_service import LLMService


class WriterSubagent:
    @staticmethod
    def write(
        *,
        requirement: str,
        research_brief: dict[str, Any],
        analytics: dict[str, Any],
        critique: str = "",
    ) -> ReportDraft:
        fallback = WriterSubagent._fallback(requirement, research_brief, analytics, critique)
        payload = LLMService.generate_json(
            system_prompt=(
                "You are the writer subagent for a local intelligence report. "
                "Return only JSON with title, summary, sections, and markdown_content. "
                "sections must be a list of objects with title and content."
            ),
            user_prompt=(
                f"Requirement: {requirement or 'Produce an analytical report.'}\n"
                f"Research brief: {research_brief}\n"
                f"Simulation analytics: {analytics}\n"
                f"Revision guidance: {critique or 'None'}\n"
                "Write 3 or 4 compact sections with concrete findings, scenario dynamics, and implications.\n"
                "Example shape:\n"
                '{'
                '"title":"...",'
                '"summary":"...",'
                '"sections":[{"title":"Situation","content":"..."},{"title":"Dynamics","content":"..."}],'
                '"markdown_content":"# ...\\n\\n## Situation\\n..."'
                '}'
            ),
            model=settings.llm_quality_model,
            temperature=0.3,
            max_output_tokens=2200,
            fallback=fallback.model_dump(),
        )
        try:
            return ReportDraft.model_validate(WriterSubagent._normalize_payload(payload, fallback))
        except Exception:
            return fallback

    @staticmethod
    def _fallback(
        requirement: str,
        research_brief: dict[str, Any],
        analytics: dict[str, Any],
        critique: str,
    ) -> ReportDraft:
        sections = [
            ReportSection(
                title="Situation",
                content=(
                    f"The simulation addressed: {requirement or 'a general scenario'}. "
                    f"Core entities were {', '.join(entity['name'] for entity in research_brief.get('core_entities', [])[:4]) or 'limited'}."
                ),
            ),
            ReportSection(
                title="Dynamics",
                content=(
                    f"The run produced {analytics.get('events_count', 0)} events across "
                    f"{analytics.get('rounds_completed', 0)} rounds. "
                    f"Dominant sentiment was {analytics.get('dominant_sentiment', 'mixed')}."
                ),
            ),
            ReportSection(
                title="Implications",
                content=(
                    f"Risk signals included: {', '.join(research_brief.get('risk_signals', [])[:3]) or 'none explicit'}. "
                    f"{critique or 'The report remains a first-pass synthesis.'}"
                ),
            ),
        ]
        markdown = "\n\n".join(
            [f"# Mini MiroFish Report", ""]
            + [f"## {section.title}\n{section.content}" for section in sections]
        )
        return ReportDraft(
            title="Mini MiroFish Report",
            summary=sections[0].content,
            sections=sections,
            markdown_content=markdown,
        )

    @staticmethod
    def _normalize_payload(payload: dict[str, Any] | list[Any], fallback: ReportDraft) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return fallback.model_dump()
        container = payload.get("report") if isinstance(payload.get("report"), dict) else payload
        title = str(container.get("title") or container.get("headline") or fallback.title).strip()
        summary = str(container.get("summary") or container.get("executive_summary") or fallback.summary).strip()
        sections_raw = container.get("sections") or container.get("section_list") or []
        sections = WriterSubagent._normalize_sections(sections_raw) or [section.model_dump() for section in fallback.sections]
        markdown_content = str(
            container.get("markdown_content")
            or container.get("markdown")
            or container.get("content")
            or ""
        ).strip()
        if not markdown_content:
            markdown_content = WriterSubagent._sections_to_markdown(title or fallback.title, sections)
        return {
            "title": title or fallback.title,
            "summary": summary or fallback.summary,
            "sections": sections,
            "markdown_content": markdown_content,
        }

    @staticmethod
    def _normalize_sections(raw: Any) -> list[dict[str, str]]:
        if isinstance(raw, dict):
            raw = [{"title": key, "content": value} for key, value in raw.items()]
        if not isinstance(raw, list):
            return []
        sections: list[dict[str, str]] = []
        for item in raw:
            if isinstance(item, str):
                sections.append({"title": "Section", "content": item.strip()})
                continue
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("heading") or "Section").strip()
            content = str(item.get("content") or item.get("body") or "").strip()
            if content:
                sections.append({"title": title, "content": content})
        return sections[:4]

    @staticmethod
    def _sections_to_markdown(title: str, sections: list[dict[str, str]]) -> str:
        return "\n\n".join([f"# {title}", ""] + [f"## {section['title']}\n{section['content']}" for section in sections])
