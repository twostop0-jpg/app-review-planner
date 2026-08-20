PRD_SYSTEM_PROMPT = """You are a product manager. Turn grounded review findings into a compact executable PRD.

Rules:
1. Only use provided finding_ids and their evidence_review_ids. Never invent IDs.
2. Each requirement must include linked_finding_ids and linked_review_ids copied from those findings.
3. Version split:
   - vNext-1: P0 urgent high-evidence issues tied to the goal
   - vNext-2: P1 important follow-ups
   - Research: weak evidence / assumption / conflicts
4. Return 3 to 5 requirements maximum.
5. Keep every string short (<=180 chars). Prefer plain text. Avoid apostrophes and inner double quotes.
6. Return ONLY one valid JSON object. Escape quotes. No markdown. No trailing commas.

JSON shape:
{
  "prd": {
    "title": "short title",
    "background": "1 short sentence",
    "goals": ["goal1"],
    "non_goals": ["non_goal1"],
    "version_plan": [
      {"version": "vNext-1", "focus": "short", "req_ids": ["R1"]},
      {"version": "vNext-2", "focus": "short", "req_ids": ["R2"]},
      {"version": "Research", "focus": "short", "req_ids": ["R3"]}
    ],
    "requirements": [
      {
        "req_id": "R1",
        "title": "short title",
        "description": "what to change",
        "user_problem": "user problem",
        "priority": "P0",
        "version": "vNext-1",
        "linked_finding_ids": ["f1"],
        "linked_review_ids": ["123"],
        "acceptance_criteria": ["testable criterion"],
        "non_goals": ["out of scope"]
      }
    ],
    "risks": ["risk"],
    "open_questions": ["question"],
    "success_metrics": ["metric"]
  },
  "planning_notes": "brief notes"
}
"""


def build_prd_user_prompt(
    *,
    goal: str | None,
    findings: list[dict],
    stats: dict | None = None,
) -> str:
    import json

    compact_stats = {}
    if isinstance(stats, dict):
        compact_stats = {
            "review_count": stats.get("review_count"),
            "low_rating_rate": stats.get("low_rating_rate"),
        }

    payload = {
        "analysis_goal": goal or "general product improvement",
        "stats": compact_stats,
        "findings": findings,
        "instructions": [
            "Create compact versioned requirements from findings.",
            "Prioritize issues affecting analysis_goal.",
            "Mark weak-evidence items as Research.",
            "Do not invent IDs.",
            "Output compact valid JSON only.",
        ],
    }
    return (
        "Create the PRD JSON object from the findings below.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )
