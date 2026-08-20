from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.settings import settings


class MoonshotError(Exception):
    """Raised when Moonshot API calls fail."""


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise MoonshotError("Model response did not contain a JSON object")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise MoonshotError("Model JSON root must be an object")
    return data


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

    def chat(self, messages: list[dict[str, str]], temperature: float | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
        }
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
        retries: int = 2,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            repair_messages = list(messages)
            if attempt > 0:
                repair_messages = messages + [
                    {
                        "role": "user",
                        "content": (
                            "Your previous reply was invalid. "
                            "Return ONLY one valid JSON object. No markdown, no commentary."
                        ),
                    }
                ]
            try:
                content = self.chat(repair_messages, temperature=temperature)
                return _extract_json_object(content)
            except (MoonshotError, json.JSONDecodeError) as exc:
                last_error = exc
        raise MoonshotError(f"Failed to get valid JSON from Moonshot: {last_error}")
