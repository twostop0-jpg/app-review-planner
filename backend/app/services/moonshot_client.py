from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.settings import settings


class MoonshotError(Exception):
    """Raised when Moonshot API calls fail."""


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _basic_json_repair(text: str) -> str:
    """Best-effort fixes for common model JSON mistakes."""
    text = _strip_code_fence(text)
    # Normalize fancy quotes that break JSON
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def _extract_json_object(text: str) -> dict[str, Any]:
    candidates = [_strip_code_fence(text), _basic_json_repair(text)]
    match = re.search(r"\{[\s\S]*\}", _basic_json_repair(text))
    if match:
        candidates.append(match.group(0))

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
            last_error = MoonshotError("Model JSON root must be an object")
        except json.JSONDecodeError as exc:
            last_error = exc
    raise MoonshotError(f"Could not parse JSON object: {last_error}")


class MoonshotClient:
    def __init__(self) -> None:
        if not settings.moonshot_api_key.strip():
            raise MoonshotError(
                "MOONSHOT_API_KEY is missing. Copy backend/.env.example to backend/.env "
                "and set your Moonshot API key."
            )
        self.base_url = settings.moonshot_base_url.rstrip("/")
        self.model = settings.moonshot_model
        self.temperature = settings.moonshot_temperature
        self.timeout = settings.moonshot_timeout_sec
        self.api_key = settings.moonshot_api_key.strip()

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        *,
        force_json: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
        }
        if force_json:
            # Supported by Moonshot OpenAI-compatible API for many chat models.
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise MoonshotError(f"Moonshot request failed: {exc}") from exc

        if response.status_code >= 400:
            # Retry once without response_format if the model rejects it.
            if force_json and response.status_code in {400, 422}:
                return self.chat(messages, temperature=temperature, force_json=False)
            raise MoonshotError(
                f"Moonshot API error {response.status_code}: {response.text[:500]}"
            )

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise MoonshotError(f"Unexpected Moonshot response shape: {data}") from exc

    def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        retries: int = 3,
        repair_hint: str | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        previous_content = ""
        default_hint = (
            "Rules: escape all quotes inside strings; no trailing commas; "
            "no markdown fences; keep strings short and plain; "
            "return one compact JSON object only."
        )
        hint = repair_hint or default_hint

        for attempt in range(retries + 1):
            repair_messages = list(messages)
            if attempt > 0:
                snippet = previous_content[:2800] if previous_content else ""
                repair_messages = messages + [
                    {
                        "role": "user",
                        "content": (
                            "Your previous reply was invalid JSON.\n"
                            "Fix it and return ONLY one valid JSON object.\n"
                            f"{hint}\n\n"
                            f"Previous invalid reply:\n{snippet}"
                        ),
                    }
                ]
            try:
                content = self.chat(
                    repair_messages,
                    temperature=0.1 if attempt else temperature,
                    force_json=True,
                )
                previous_content = content
                return _extract_json_object(content)
            except (MoonshotError, json.JSONDecodeError) as exc:
                last_error = exc
        raise MoonshotError(f"Failed to get valid JSON from Moonshot: {last_error}")
