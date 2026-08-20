"""Model-driven review analysis with evidence grounding."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.prompts.findings import FINDINGS_SYSTEM_PROMPT, build_findings_user_prompt
from app.services.moonshot_client import MoonshotClient, MoonshotError


def build_deterministic_stats(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    ratings = Counter()
    versions = Counter()
    for review in reviews:
        rating = review.get("rating")
        ratings[str(rating) if rating is not None else "null"] += 1
        versions[str(review.get("version") or "unknown")] += 1

    total = len(reviews)
    low = sum(1 for r in reviews if isinstance(r.get("rating"), int) and r["rating"] <= 2)
    return {
        "origin": "stat",
        "review_count": total,
        "low_rating_count": low,
        "low_rating_rate": round(low / total, 3) if total else 0.0,
        "rating_histogram": dict(ratings),
        "top_versions": [
            {"version": version, "count": count}
            for version, count in versions.most_common(8)
        ],
    }


def _compact_reviews(reviews: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for review in reviews[:limit]:
        content = str(review.get("content") or "")
        compact.append(
            {
                "id": str(review.get("id")),
                "rating": review.get("rating"),
                "title": str(review.get("title") or "")[:120],
                "content": content[:500],
                "version": review.get("version"),
                "date": review.get("date"),
            }
        )
    return compact


def _validate_findings(
    raw_findings: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {str(r.get("id")): r for r in reviews}
    validated: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for index, item in enumerate(raw_findings):
        if not isinstance(item, dict):
            rejected.append({"reason": "not_an_object", "raw": item})
            continue

        evidence_ids = item.get("evidence_review_ids") or []
        if not isinstance(evidence_ids, list):
            evidence_ids = []

        valid_ids = []
        excerpts = []
        for rid in evidence_ids:
            rid_s = str(rid)
            if rid_s in by_id and rid_s not in valid_ids:
                valid_ids.append(rid_s)
                review = by_id[rid_s]
                snippet = (review.get("title") or "") + " — " + (review.get("content") or "")
                excerpts.append(snippet[:180])

        provided_excerpts = item.get("evidence_excerpts") or []
        if isinstance(provided_excerpts, list):
            # Keep model excerpts only when ids are valid; otherwise replace with grounded ones
            if valid_ids and provided_excerpts:
                excerpts = [str(x)[:180] for x in provided_excerpts[: len(valid_ids)]]

        if not valid_ids:
            rejected.append(
                {
                    "reason": "no_valid_evidence_review_ids",
                    "title": item.get("title"),
                    "claimed_ids": evidence_ids,
                }
            )
            continue

        severity = str(item.get("severity") or "medium").lower()
        if severity not in {"high", "medium", "low"}:
            severity = "medium"

        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        conflicts = item.get("conflicts") or []
        if not isinstance(conflicts, list):
            conflicts = [str(conflicts)]

        finding_id = str(item.get("finding_id") or f"f{index + 1}")
        validated.append(
            {
                "finding_id": finding_id,
                "title": str(item.get("title") or "Untitled finding"),
                "summary": str(item.get("summary") or ""),
                "severity": severity,
                "evidence_review_ids": valid_ids,
                "evidence_excerpts": excerpts[:5],
                "support_count": len(valid_ids),
                "confidence": confidence,
                "conflicts": [str(c) for c in conflicts][:5],
                "uncertainty_notes": str(item.get("uncertainty_notes") or ""),
                "assumption": bool(item.get("assumption", False)),
                "origin": "model",
            }
        )

    return validated, rejected


def analyze_reviews(
    reviews: list[dict[str, Any]],
    goal: str | None = None,
) -> dict[str, Any]:
    if not reviews:
        return {
            "stats": build_deterministic_stats([]),
            "findings": [],
            "analysis_notes": "No cleaned reviews available for analysis.",
            "validation": {
                "accepted": 0,
                "rejected": 0,
                "rejected_items": [],
            },
            "model": None,
            "error": None,
        }

    stats = build_deterministic_stats(reviews)
    compact = _compact_reviews(reviews)

    client = MoonshotClient()
    messages = [
        {"role": "system", "content": FINDINGS_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_findings_user_prompt(
                goal=goal,
                reviews=compact,
                stats=stats,
            ),
        },
    ]

    raw = client.chat_json(messages, temperature=0.2, retries=2)
    raw_findings = raw.get("findings") or []
    if not isinstance(raw_findings, list):
        raise MoonshotError("Model JSON missing findings array")

    findings, rejected = _validate_findings(raw_findings, reviews)
    analysis_notes = str(raw.get("analysis_notes") or "")
    if rejected:
        analysis_notes = (
            (analysis_notes + " " if analysis_notes else "")
            + f"Rejected {len(rejected)} unsupported finding(s) after evidence validation."
        ).strip()

    return {
        "stats": stats,
        "findings": findings,
        "analysis_notes": analysis_notes,
        "validation": {
            "accepted": len(findings),
            "rejected": len(rejected),
            "rejected_items": rejected[:10],
        },
        "model": {
            "provider": "moonshot",
            "model": client.model,
            "temperature": 0.2,
        },
        "error": None,
    }
