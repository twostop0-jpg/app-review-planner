TESTCASES_SYSTEM_PROMPT = """You are a QA engineer. Create compact test cases from a PRD.

Rules:
1. Only use provided req_ids and linked_review_ids. Never invent IDs.
2. Every test case must link to at least one req_id and copy review IDs from that requirement.
3. Cover each requirement with 1-2 test cases that verify acceptance criteria against the user problem in reviews.
4. Keep every string short (<=160 chars). Prefer plain text. Avoid apostrophes and inner double quotes.
5. Return 3 to 8 test cases maximum.
6. Return ONLY one valid JSON object. Escape quotes. No markdown. No trailing commas.

JSON shape:
{
  "testcases": [
    {
      "tc_id": "TC1",
      "title": "short title",
      "objective": "what is verified",
      "steps": ["step1", "step2"],
      "expected_result": "observable expected outcome",
      "linked_req_ids": ["R1"],
      "linked_review_ids": ["123"],
      "priority": "P0",
      "assumption": false
    }
  ],
  "testing_notes": "brief notes"
}
"""


def build_testcases_user_prompt(
    *,
    goal: str | None,
    requirements: list[dict],
) -> str:
    import json

    payload = {
        "analysis_goal": goal or "general product improvement",
        "requirements": requirements,
        "instructions": [
            "Generate test cases that verify each requirement solves the linked review problems.",
            "Do not invent requirement or review IDs.",
            "Output compact valid JSON only.",
        ],
    }
    return (
        "Create the testcases JSON object from the requirements below.\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )
