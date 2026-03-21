from __future__ import annotations

import asyncio
from typing import Any

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("mirofish.llm")


class LLMClient:
    """Async OpenAI wrapper with retry logic and token usage tracking."""

    MAX_RETRIES: int = 3
    BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0)

    # Rough pricing per 1K tokens (USD) — adjust as models change.
    _COST_PER_1K: dict[str, dict[str, float]] = {
        "default": {"input": 0.0005, "output": 0.0015},
    }

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0

    def _resolve_model(self, model: str | None) -> str:
        """Map the convenience aliases *heavy* / *light* to real model names."""
        if model == "heavy":
            return settings.OPENAI_MODEL_HEAVY
        if model == "light" or model is None:
            return settings.OPENAI_MODEL_LIGHT
        return model

    async def achat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 2000,
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion request with automatic retries.

        Args:
            messages: OpenAI-style message list.
            model: ``"heavy"``, ``"light"``, an explicit model name, or
                *None* (defaults to ``"light"``).
            max_tokens: Maximum tokens in the response.
            json_mode: If *True*, request structured JSON output.

        Returns:
            The assistant's response text.
        """
        resolved_model = self._resolve_model(model)

        # GPT-5 mini/nano are reasoning models:
        # - Use max_completion_tokens (includes reasoning + output tokens)
        # - No temperature support (only 1.0)
        # - Use reasoning_effort="low" to minimize reasoning token usage
        kwargs: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "max_completion_tokens": max_tokens,
            "reasoning_effort": "low",
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_exc: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response: ChatCompletion = await self._client.chat.completions.create(**kwargs)
                self._track_usage(response, resolved_model)
                choice = response.choices[0]
                logger.debug("finish_reason=%s", choice.finish_reason)
                content = choice.message.content or ""
                return content
            except (openai.APIConnectionError, openai.RateLimitError, openai.APIStatusError) as exc:
                last_exc = exc
                wait = self.BACKOFF_SECONDS[attempt] if attempt < len(self.BACKOFF_SECONDS) else self.BACKOFF_SECONDS[-1]
                logger.warning(
                    "LLM request failed (attempt %d/%d): %s — retrying in %.1fs",
                    attempt + 1,
                    self.MAX_RETRIES,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

        raise RuntimeError(
            f"LLM request failed after {self.MAX_RETRIES} attempts"
        ) from last_exc

    def _track_usage(self, response: ChatCompletion, model: str) -> None:
        """Accumulate token counts from the API response and log them."""
        usage = response.usage
        if usage is None:
            return

        self.total_input_tokens += usage.prompt_tokens
        self.total_output_tokens += usage.completion_tokens

        logger.debug(
            "Tokens [%s]: in=%d out=%d | cumulative: in=%d out=%d",
            model,
            usage.prompt_tokens,
            usage.completion_tokens,
            self.total_input_tokens,
            self.total_output_tokens,
        )

    def get_usage_summary(self) -> dict[str, Any]:
        """Return aggregate token usage and estimated cost."""
        cost_rates = self._COST_PER_1K.get("default", {"input": 0.0, "output": 0.0})
        estimated_cost = (
            (self.total_input_tokens / 1000) * cost_rates["input"]
            + (self.total_output_tokens / 1000) * cost_rates["output"]
        )
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
        }


# Module-level singleton
llm_client = LLMClient()
