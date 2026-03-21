from __future__ import annotations

import json
import re
import time
from typing import Any

import openai
from openai import OpenAI

from ..config import settings
from ..utils.logger import get_logger


logger = get_logger("miro_gpt.llm_service")


class LLMService:
    _client: OpenAI | None = None
    MAX_RETRIES = 3
    BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0)

    @classmethod
    def client(cls) -> OpenAI:
        settings.require_llm()
        if cls._client is None:
            cls._client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        return cls._client

    @classmethod
    def generate_text(
        cls,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.2,
        max_output_tokens: int = 2000,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(cls.MAX_RETRIES):
            try:
                response = cls.client().responses.create(
                    model=model,
                    instructions=system_prompt,
                    input=user_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
                text = cls._extract_text(response)
                if not text.strip():
                    raise ValueError("LLM returned an empty response.")
                return text.strip()
            except (
                openai.APIConnectionError,
                openai.RateLimitError,
                openai.APIStatusError,
                openai.APITimeoutError,
            ) as error:
                last_error = error
                if attempt < cls.MAX_RETRIES - 1:
                    time.sleep(cls.BACKOFF_SECONDS[min(attempt, len(cls.BACKOFF_SECONDS) - 1)])
                    continue
                raise
        assert last_error is not None
        raise last_error

    @classmethod
    def generate_json(
        cls,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.2,
        max_output_tokens: int = 2000,
        fallback: dict[str, Any] | list[Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        try:
            text = cls._generate_json_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                max_output_tokens=max_output_tokens,
            )
            return cls.parse_json_payload(text)
        except Exception as error:
            if isinstance(error, ValueError) and "LLM_API_KEY" in str(error):
                raise
            if fallback is not None:
                logger.warning("Falling back to local JSON after LLM error: %s", error)
                return fallback
            raise

    @staticmethod
    def parse_json_payload(text: str) -> dict[str, Any] | list[Any]:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
            stripped = re.sub(r"```$", "", stripped).strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            extracted = LLMService._extract_balanced_json(stripped)
            if extracted is None:
                raise
            return json.loads(extracted)

    @classmethod
    def _generate_json_text(
        cls,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_output_tokens: int,
    ) -> str:
        last_error: Exception | None = None
        messages = [
            {
                "role": "system",
                "content": (
                    f"{system_prompt}\n\n"
                    "Return ONLY valid JSON. Do not use markdown fences. "
                    "Do not include commentary before or after the JSON."
                ),
            },
            {"role": "user", "content": user_prompt},
        ]
        for attempt in range(cls.MAX_RETRIES):
            try:
                response = cls.client().chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_completion_tokens=max_output_tokens,
                    reasoning_effort="low",
                )
                content = response.choices[0].message.content or ""
                if not content.strip():
                    raise ValueError("LLM returned an empty JSON response.")
                return content.strip()
            except TypeError:
                return cls.generate_text(
                    system_prompt=messages[0]["content"],
                    user_prompt=user_prompt,
                    model=model,
                    temperature=0.1,
                    max_output_tokens=max_output_tokens,
                )
            except (
                openai.APIConnectionError,
                openai.RateLimitError,
                openai.APIStatusError,
                openai.APITimeoutError,
            ) as error:
                last_error = error
                if attempt < cls.MAX_RETRIES - 1:
                    time.sleep(cls.BACKOFF_SECONDS[min(attempt, len(cls.BACKOFF_SECONDS) - 1)])
                    continue
                raise
        assert last_error is not None
        raise last_error

    @staticmethod
    def _extract_balanced_json(text: str) -> str | None:
        start_positions = [index for index, char in enumerate(text) if char in "[{"]
        for start in start_positions:
            opening = text[start]
            closing = "}" if opening == "{" else "]"
            depth = 0
            in_string = False
            escape = False
            for index in range(start, len(text)):
                char = text[index]
                if escape:
                    escape = False
                    continue
                if char == "\\":
                    escape = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == opening:
                    depth += 1
                elif char == closing:
                    depth -= 1
                    if depth == 0:
                        return text[start : index + 1]
        return None

    @staticmethod
    def _extract_text(response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return str(output_text)
        chunks: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    chunks.append(str(text))
        return "\n".join(chunks)
