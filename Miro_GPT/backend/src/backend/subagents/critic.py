from __future__ import annotations

from ..config import settings
from ..models.schemas import CritiqueResult, ReportDraft
from ..services.llm_service import LLMService


class CriticSubagent:
    @staticmethod
    def review(*, requirement: str, draft: ReportDraft) -> CritiqueResult:
        fallback = CriticSubagent._fallback(requirement, draft)
        payload = LLMService.generate_json(
            system_prompt=(
                "You are a critic subagent. "
                "Return only JSON with needs_revision, issues, revision_instructions. "
                "Only request a single targeted revision pass when there is a real coverage gap."
            ),
            user_prompt=(
                f"Requirement: {requirement or 'No extra requirement.'}\n"
                f"Draft report: {draft.model_dump()}\n"
                "Check for missing requirement coverage, contradictions, or unsupported claims."
            ),
            model=settings.llm_fast_model,
            temperature=0.1,
            max_output_tokens=900,
            fallback=fallback.model_dump(),
        )
        try:
            return CritiqueResult.model_validate(CriticSubagent._normalize_payload(payload, fallback))
        except Exception:
            return fallback

    @staticmethod
    def _fallback(requirement: str, draft: ReportDraft) -> CritiqueResult:
        issues: list[str] = []
        if requirement and requirement.lower() not in draft.markdown_content.lower():
            issues.append("The report does not explicitly anchor itself to the simulation requirement.")
        if len(draft.sections) < settings.report_min_sections:
            issues.append("The report is too short and lacks structural coverage.")
        return CritiqueResult(
            needs_revision=bool(issues),
            issues=issues,
            revision_instructions=(
                "Add direct requirement coverage and tighten conclusions."
                if issues
                else "No revision required."
            ),
        )

    @staticmethod
    def _normalize_payload(payload: dict[str, object] | list[object], fallback: CritiqueResult) -> dict[str, object]:
        if not isinstance(payload, dict):
            return fallback.model_dump()
        needs_revision_raw = (
            payload.get("needs_revision")
            or payload.get("needsRevision")
            or payload.get("revise")
            or False
        )
        issues_raw = payload.get("issues") or payload.get("gaps") or []
        revision_instructions = str(
            payload.get("revision_instructions")
            or payload.get("revisionInstructions")
            or payload.get("instructions")
            or fallback.revision_instructions
        ).strip()
        return {
            "needs_revision": CriticSubagent._coerce_bool(needs_revision_raw),
            "issues": CriticSubagent._normalize_issues(issues_raw),
            "revision_instructions": revision_instructions or fallback.revision_instructions,
        }

    @staticmethod
    def _coerce_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "yes", "y", "1", "revise", "needs_revision"}
        if isinstance(value, (int, float)):
            return bool(value)
        return False

    @staticmethod
    def _normalize_issues(raw: object) -> list[str]:
        if isinstance(raw, str):
            return [raw.strip()] if raw.strip() else []
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]
