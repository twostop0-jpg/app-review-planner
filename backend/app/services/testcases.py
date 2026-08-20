"""Generate test cases from PRD requirements."""

from __future__ import annotations

from typing import Any

from app.prompts.testcases import TESTCASES_SYSTEM_PROMPT, build_testcases_user_prompt
from app.services.moonshot_client import MoonshotClient, MoonshotError


def _compact_requirements(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for req in requirements[:8]:
        compact.append(
            {
                "req_id": req.get("req_id"),
                "title": str(req.get("title") or "")[:80],
                "description": str(req.get("description") or "")[:160],
                "user_problem": str(req.get("user_problem") or "")[:120],
                "priority": req.get("priority"),
                "version": req.get("version"),
                "linked_finding_ids": (req.get("linked_finding_ids") or [])[:4],
                "linked_review_ids": [str(r) for r in (req.get("linked_review_ids") or [])][
                    :6
                ],
                "acceptance_criteria": [
                    str(x)[:120] for x in (req.get("acceptance_criteria") or [])
                ][:3],
            }
        )
    return compact


def _fallback_testcases(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for index, req in enumerate(requirements[:6]):
        req_id = str(req.get("req_id") or f"R{index + 1}")
        review_ids = [str(r) for r in (req.get("linked_review_ids") or [])]
        if not review_ids:
            continue
        criteria = req.get("acceptance_criteria") or []
        criterion = str(criteria[0]) if criteria else "Requirement acceptance criteria met"
        priority = str(req.get("priority") or "P1")
        if priority not in {"P0", "P1", "P2"}:
            priority = "P1"
        cases.append(
            {
                "tc_id": f"TC{index + 1}",
                "title": f"Verify {str(req.get('title') or req_id)}"[:100],
                "objective": str(req.get("user_problem") or req.get("description") or "")[
                    :160
                ],
                "steps": [
                    f"Identify the user problem linked to {req_id}",
                    "Apply the proposed product change for this requirement",
                    "Check against linked review complaints",
                ],
                "expected_result": criterion[:180],
                "linked_req_ids": [req_id],
                "linked_review_ids": review_ids,
                "priority": priority,
                "assumption": False,
                "origin": "rule",
            }
        )
    return cases


def _validate_testcases(
    raw_cases: list[Any],
    requirements: list[dict[str, Any]],
    *,
    origin_default: str = "model",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    req_by_id = {
        str(r.get("req_id")): r for r in requirements if r.get("req_id")
    }
    rejected: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []

    for index, item in enumerate(raw_cases):
        if not isinstance(item, dict):
            rejected.append({"reason": "not_an_object", "raw": item})
            continue

        linked_reqs = [
            str(rid)
            for rid in (item.get("linked_req_ids") or [])
            if str(rid) in req_by_id
        ]
        if not linked_reqs:
            rejected.append(
                {
                    "reason": "no_valid_linked_req_ids",
                    "title": item.get("title"),
                    "claimed": item.get("linked_req_ids"),
                }
            )
            continue

        allowed_reviews: list[str] = []
        for rid in linked_reqs:
            for review_id in req_by_id[rid].get("linked_review_ids") or []:
                review_s = str(review_id)
                if review_s not in allowed_reviews:
                    allowed_reviews.append(review_s)

        claimed_reviews = [str(r) for r in (item.get("linked_review_ids") or [])]
        linked_reviews = [r for r in claimed_reviews if r in allowed_reviews]
        if not linked_reviews:
            linked_reviews = allowed_reviews
        if not linked_reviews:
            rejected.append(
                {
                    "reason": "no_linked_review_ids_after_validation",
                    "title": item.get("title"),
                    "linked_req_ids": linked_reqs,
                }
            )
            continue

        priority = str(item.get("priority") or req_by_id[linked_reqs[0]].get("priority") or "P1")
        if priority not in {"P0", "P1", "P2"}:
            priority = "P1"

        steps = item.get("steps") or []
        if not isinstance(steps, list):
            steps = [str(steps)]
        steps = [str(s)[:160] for s in steps][:6] or ["Execute the requirement scenario"]

        accepted.append(
            {
                "tc_id": str(item.get("tc_id") or f"TC{index + 1}"),
                "title": str(item.get("title") or "Untitled test case")[:120],
                "objective": str(item.get("objective") or "")[:200],
                "steps": steps,
                "expected_result": str(item.get("expected_result") or "")[:220],
                "linked_req_ids": linked_reqs,
                "linked_review_ids": linked_reviews,
                "priority": priority,
                "assumption": bool(item.get("assumption", False)),
                "origin": str(item.get("origin") or origin_default),
            }
        )

    return accepted, rejected


def generate_testcases(
    prd: dict[str, Any] | None,
    goal: str | None = None,
) -> dict[str, Any]:
    requirements = []
    if isinstance(prd, dict):
        requirements = prd.get("requirements") or []
    if not isinstance(requirements, list):
        requirements = []

    if not requirements:
        return {
            "testcases": [],
            "testing_notes": "Skipped testcase generation because PRD requirements were empty.",
            "validation": {"accepted": 0, "rejected": 0, "rejected_items": []},
            "model": None,
            "error": None,
        }

    client = MoonshotClient()
    messages = [
        {"role": "system", "content": TESTCASES_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_testcases_user_prompt(
                goal=goal,
                requirements=_compact_requirements(requirements),
            ),
        },
    ]

    try:
        raw = client.chat_json(
            messages,
            temperature=0.1,
            retries=3,
            repair_hint=(
                "Keep at most 8 testcases; keep every string under 160 chars; "
                "escape quotes; no markdown; include testcases array."
            ),
        )
        raw_cases = raw.get("testcases")
        if not isinstance(raw_cases, list):
            raise MoonshotError("Model JSON missing testcases array")

        cases, rejected = _validate_testcases(
            raw_cases, requirements, origin_default="model"
        )
        if not cases:
            raise MoonshotError("Model returned zero valid testcases after validation")

        notes = str(raw.get("testing_notes") or "")
        if rejected:
            notes = (
                (notes + " " if notes else "")
                + f"Rejected {len(rejected)} unsupported testcase(s) after validation."
            ).strip()

        return {
            "testcases": cases,
            "testing_notes": notes,
            "validation": {
                "accepted": len(cases),
                "rejected": len(rejected),
                "rejected_items": rejected[:10],
            },
            "model": {
                "provider": "moonshot",
                "model": client.model,
                "temperature": 0.1,
            },
            "error": None,
        }
    except MoonshotError as exc:
        fallback = _fallback_testcases(requirements)
        cases, rejected = _validate_testcases(
            fallback, requirements, origin_default="rule"
        )
        return {
            "testcases": cases,
            "testing_notes": (
                "Used deterministic fallback testcases because Moonshot JSON failed: "
                f"{exc}"
            ),
            "validation": {
                "accepted": len(cases),
                "rejected": len(rejected),
                "rejected_items": rejected[:10],
            },
            "model": {
                "provider": "moonshot",
                "model": client.model,
                "temperature": 0.1,
                "fallback": "rule",
            },
            "error": str(exc),
        }
