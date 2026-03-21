from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    debug: bool = os.environ.get("FLASK_DEBUG", "0") == "1"
    llm_api_key: str = os.environ.get("LLM_API_KEY", "")
    llm_base_url: str = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_fast_model: str = os.environ.get("LLM_FAST_MODEL", "gpt-5.4-nano")
    llm_quality_model: str = os.environ.get("LLM_QUALITY_MODEL", "gpt-5.4-mini")
    zep_api_key: str = os.environ.get("ZEP_API_KEY", "")
    database_url: str = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'data' / 'app.db').as_posix()}",
    )
    data_dir: Path = BASE_DIR / "data"
    projects_dir: Path = BASE_DIR / "data" / "projects"
    entity_cap_default: int = int(os.environ.get("ENTITY_CAP_DEFAULT", "25"))
    entity_cap_hard_max: int = int(os.environ.get("ENTITY_CAP_HARD_MAX", "40"))
    rounds_default: int = int(os.environ.get("ROUNDS_DEFAULT", "12"))
    rounds_hard_max: int = int(os.environ.get("ROUNDS_HARD_MAX", "24"))
    active_agents_per_round_default: int = int(
        os.environ.get("ACTIVE_AGENTS_PER_ROUND_DEFAULT", "4")
    )
    active_agents_per_round_hard_max: int = int(
        os.environ.get("ACTIVE_AGENTS_PER_ROUND_HARD_MAX", "6")
    )
    report_max_sections: int = int(os.environ.get("REPORT_MAX_SECTIONS", "4"))
    report_min_sections: int = int(os.environ.get("REPORT_MIN_SECTIONS", "3"))
    critic_max_passes: int = int(os.environ.get("CRITIC_MAX_PASSES", "1"))
    max_content_length: int = 50 * 1024 * 1024
    allowed_extensions: tuple[str, ...] = ("pdf", "txt", "md", "markdown")

    def require_llm(self) -> None:
        if not self.llm_api_key:
            raise ValueError("LLM_API_KEY is not configured.")

    def require_zep(self) -> None:
        if not self.zep_api_key:
            raise ValueError("ZEP_API_KEY is not configured.")


settings = Settings()
