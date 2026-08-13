from __future__ import annotations

import re


class InvalidAppUrlError(ValueError):
    """Raised when an App Store URL cannot be parsed."""


def extract_app_id(app_url: str) -> str:
    if not app_url or not app_url.strip():
        raise InvalidAppUrlError("App Store URL is empty")

    match = re.search(r"/id(\d+)\b", app_url)
    if match:
        return match.group(1)

    match = re.search(r"[?&]id=(\d+)\b", app_url)
    if match:
        return match.group(1)

    if re.fullmatch(r"\d{5,}", app_url.strip()):
        return app_url.strip()

    raise InvalidAppUrlError(f"Could not extract app id from URL: {app_url}")
