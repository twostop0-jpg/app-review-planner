FINDINGS_SYSTEM_PROMPT = """You are a product analyst. Analyze App Store user reviews and extract grounded product findings.

Rules:
1. Only use the provided reviews. Never invent review IDs or quotes.
2. Findings must be dynamic topics discovered from the reviews, NOT a fixed keyword taxonomy.
3. Respect the user's analysis goal when prioritizing, but you may include closely related issues.
4. Every finding MUST include evidence_review_ids that exist in the input.
5. Include confidence (0-1), conflicts, and uncertainty_notes when evidence is weak or mixed.
6. Distinguish assumptions: set assumption=true if evidence is thin.
7. Return ONLY a JSON object with this shape:
{
  "findings": [
    {
      "finding_id": "f1",
      "title": "short title",
      "summary": "1-3 sentence summary grounded in evidence",
      "severity": "high|medium|low",
      "evidence_review_ids": ["id1", "id2"],
      "evidence_excerpts": ["short quote 1", "short quote 2"],
      "support_count": 2,
      "confidence": 0.0,
      "conflicts": ["optional conflicting feedback"],
      "uncertainty_notes": "optional",
      "assumption": false
    }
  ],
  "analysis_notes": "brief notes about coverage, data limits, or goal focus"
}
"""


def build_findings_user_prompt(
    *,
    goal: str | None,
    reviews: list[dict],
    stats: dict,
) -> str:
    payload = {
        "analysis_goal": goal or "general product issues and opportunities",
        "deterministic_stats": stats,
        "reviews": reviews,
        "instructions": [
            "Discover and consolidate issues from reviews.",
            "Prefer findings that matter for the analysis_goal.",
            "If evidence is insufficient, say so in uncertainty_notes or analysis_notes.",
            "Do not fabricate reviews.",
        ],
    }
    return (
        "Analyze the following review dataset and return the JSON object.\n\n"
        + json_dumps(payload)
    )


def json_dumps(data: dict) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, indent=2)
