"""Deterministic review cleaning: normalize, filter, dedupe, report."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime
from typing import Any

from app.models.schemas import Review

_WHITESPACE_RE = re.compile(r"\s+")
_HTML_RE = re.compile(r"<[^>]+>")
_VERSION_RE = re.compile(r"(\d+(?:\.\d+)*)")
_EMOJI_OR_SYMBOL_RE = re.compile(
    r"^[\W_]+$",
    flags=re.UNICODE,
)


def _collapse_ws(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()


def _strip_html(value: str) -> str:
    return _collapse_ws(_HTML_RE.sub(" ", value))


def normalize_version(value: str | None) -> str | None:
    if value is None:
        return None
    text = _collapse_ws(str(value))
    if not text:
        return None
    text = re.sub(r"(?i)^version\s*", "", text)
    match = _VERSION_RE.search(text)
    return match.group(1) if match else text


def normalize_date(value: str | None) -> str | None:
    if value is None:
        return None
    text = _collapse_ws(str(value))
    if not text:
        return None

    candidates = [text, text.replace("Z", "+00:00")]
    # Common App Store style: "Aug 11, 2026"
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass

    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate).date().isoformat()
        except ValueError:
            continue

    return text


def normalize_rating(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return None
    if rating < 1 or rating > 5:
        return None
    return rating


def normalize_review(raw: dict[str, Any] | Review) -> Review:
    data = raw.model_dump() if isinstance(raw, Review) else dict(raw)

    title = _strip_html(str(data.get("title") or ""))
    content = _strip_html(str(data.get("content") or ""))
    author = _collapse_ws(str(data.get("author") or ""))

    return Review(
        id=str(data.get("id") or "").strip(),
        app_id=str(data.get("app_id") or "").strip(),
        rating=normalize_rating(data.get("rating")),
        title=title,
        content=content,
        author=author,
        date=normalize_date(data.get("date")),
        version=normalize_version(data.get("version")),
        country=str(data.get("country") or "us").strip().lower() or "us",
        source=data.get("source") or "live",
    )


def _is_empty(review: Review) -> bool:
    return not review.content and not review.title


def _is_low_signal(review: Review) -> bool:
    """Conservative junk filter: emoji/symbol-only short posts without rating context."""
    text = f"{review.title} {review.content}".strip()
    if not text:
        return True
    if len(text) <= 2 and _EMOJI_OR_SYMBOL_RE.match(text):
        return True
    return False


def _content_fingerprint(review: Review) -> str:
    basis = "|".join(
        [
            review.author.lower(),
            review.title.lower(),
            review.content.lower(),
        ]
    )
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


def clean_reviews(raw_reviews: list[dict[str, Any] | Review]) -> dict[str, Any]:
    """
    Clean reviews with deterministic rules (no LLM).

    Returns:
      {
        "reviews_cleaned": [dict, ...],
        "cleaning_report": {...}
      }
    """
    input_count = len(raw_reviews)
    normalized: list[Review] = []
    removed_empty = 0
    removed_low_signal = 0
    removed_invalid_id = 0
    missing_rating = 0
    missing_date = 0
    missing_version = 0

    for raw in raw_reviews:
        review = normalize_review(raw)
        if not review.id:
            removed_invalid_id += 1
            continue
        if _is_empty(review):
            removed_empty += 1
            continue
        if _is_low_signal(review):
            removed_low_signal += 1
            continue
        if review.rating is None:
            missing_rating += 1
        if review.date is None:
            missing_date += 1
        if review.version is None:
            missing_version += 1
        normalized.append(review)

    deduped: list[Review] = []
    seen_ids: set[str] = set()
    seen_fingerprints: set[str] = set()
    removed_duplicate_id = 0
    removed_duplicate_content = 0
    duplicate_examples: list[dict[str, str]] = []

    for review in normalized:
        if review.id in seen_ids:
            removed_duplicate_id += 1
            if len(duplicate_examples) < 5:
                duplicate_examples.append(
                    {"type": "id", "id": review.id, "title": review.title[:80]}
                )
            continue

        fingerprint = _content_fingerprint(review)
        if fingerprint in seen_fingerprints:
            removed_duplicate_content += 1
            if len(duplicate_examples) < 5:
                duplicate_examples.append(
                    {
                        "type": "content",
                        "id": review.id,
                        "title": review.title[:80],
                    }
                )
            continue

        seen_ids.add(review.id)
        seen_fingerprints.add(fingerprint)
        deduped.append(review)

    rating_histogram = {
        str(star): 0 for star in range(1, 6)
    }
    rating_histogram["null"] = 0
    for review in deduped:
        key = str(review.rating) if review.rating is not None else "null"
        rating_histogram[key] = rating_histogram.get(key, 0) + 1

    version_counts = Counter(r.version or "unknown" for r in deduped)
    top_versions = [
        {"version": version, "count": count}
        for version, count in version_counts.most_common(10)
    ]

    report = {
        "method": "rules",
        "note": (
            "Deterministic cleaning: whitespace/HTML normalize, empty/low-signal "
            "filter, id+content dedupe, field stats. No LLM used in this stage."
        ),
        "input_count": input_count,
        "output_count": len(deduped),
        "removed_invalid_id": removed_invalid_id,
        "removed_empty": removed_empty,
        "removed_low_signal": removed_low_signal,
        "removed_duplicate_id": removed_duplicate_id,
        "removed_duplicate_content": removed_duplicate_content,
        "missing_fields": {
            "rating": missing_rating,
            "date": missing_date,
            "version": missing_version,
        },
        "rating_histogram": rating_histogram,
        "top_versions": top_versions,
        "duplicate_examples": duplicate_examples,
    }

    return {
        "reviews_cleaned": [r.model_dump() for r in deduped],
        "cleaning_report": report,
    }
