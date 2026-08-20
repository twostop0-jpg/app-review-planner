"""PRD / version planning from grounded findings."""

from __future__ import annotations

from typing import Any

from app.prompts.prd import PRD_SYSTEM_PROMPT, build_prd_user_prompt
from app.services.moonshot_client import MoonshotClient, MoonshotError


def _compact_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for finding in findings:
        compact.append(
            {
                "finding_id": finding.get("finding_id"),
                "title": finding.get("title"),
                "summary": str(finding.get("summary") or "")[:400],
                "severity": finding.get("severity"),
                "support_count": finding.get("support_count"),
                "confidence": finding.get("confidence"),
                "assumption": finding.get("assumption", False),
                "evidence_review_ids": finding.get("evidence_review_ids") or [],
                "conflicts": finding.get("conflicts") or [],
                "uncertainty_notes": finding.get("uncertainty_notes") or "",
            }
        )
    return compact


def _validate_prd(
    raw_prd: dict[str, Any],
    findings: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    finding_by_id = {
        str(f.get("finding_id")): f for f in findings if f.get("finding_id")
    }
    rejected: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []

    raw_requirements = raw_prd.get("requirements") or []
    if not isinstance(raw_requirements, list):
        raise MoonshotError("PRD JSON missing requirements array")

    for index, item in enumerate(raw_requirements):
        if not isinstance(item, dict):
            rejected.append({"reason": "not_an_object", "raw": item})
            continue

        linked_findings = [
            str(fid)
            for fid in (item.get("linked_finding_ids") or [])
            if str(fid) in finding_by_id
        ]
        if not linked_findings:
            rejected.append(
                {
                    "reason": "no_valid_linked_finding_ids",
                    "title": item.get("title"),
                    "claimed": item.get("linked_finding_ids"),
                }
            )
            continue

        linked_reviews: list[str] = []
        for fid in linked_findings:
            for rid in finding_by_id[fid].get("evidence_review_ids") or []:
                rid_s = str(rid)
                if rid_s not in linked_reviews:
                    linked_reviews.append(rid_s)

        # Keep model-provided review ids only if they belong to linked findings.
        claimed_reviews = [str(r) for r in (item.get("linked_review_ids") or [])]
        claimed_reviews = [r for r in claimed_reviews if r in linked_reviews]
        if claimed_reviews:
            linked_reviews = claimed_reviews

        if not linked_reviews:
            rejected.append(
                {
                    "reason": "no_linked_review_ids_after_validation",
                    "title": item.get("title"),
                    "linked_finding_ids": linked_findings,
                }
            )
            continue

        priority = str(item.get("priority") or "P1").upper()
        if priority not in {"P0", "P1", "P2"}:
            priority = "P1"

        version = str(item.get("version") or "vNext-1")
        if version not in {"vNext-1", "vNext-2", "Research"}:
            if priority == "P0":
                version = "vNext-1"
            elif priority == "P1":
                version = "vNext-2"
            else:
                version = "Research"

        acceptance = item.get("acceptance_criteria") or []
        if not isinstance(acceptance, list):
            acceptance = [str(acceptance)]
        non_goals = item.get("non_goals") or []
        if not isinstance(non_goals, list):
            non_goals = [str(non_goals)]

        requirements.append(
            {
                "req_id": str(item.get("req_id") or f"R{index + 1}"),
                "title": str(item.get("title") or "Untitled requirement"),
                "description": str(item.get("description") or ""),
                "user_problem": str(item.get("user_problem") or ""),
                "priority": priority,
                "version": version,
                "linked_finding_ids": linked_findings,
                "linked_review_ids": linked_reviews,
                "acceptance_criteria": [str(x) for x in acceptance][:8],
                "non_goals": [str(x) for x in non_goals][:5],
                "origin": "model",
            }
        )

    # Rebuild version plan from validated requirements if needed
    version_plan = raw_prd.get("version_plan") or []
    if not isinstance(version_plan, list):
        version_plan = []

    req_ids_by_version: dict[str, list[str]] = {
        "vNext-1": [],
        "vNext-2": [],
        "Research": [],
    }
    for req in requirements:
        req_ids_by_version.setdefault(req["version"], []).append(req["req_id"])

    rebuilt_plan = []
    for version, focus_default in [
        ("vNext-1", "Highest-priority, high-evidence fixes"),
        ("vNext-2", "Important follow-ups"),
        ("Research", "Low-evidence or conflicting items to investigate"),
    ]:
        existing = next(
            (
                v
                for v in version_plan
                if isinstance(v, dict) and str(v.get("version")) == version
            ),
            None,
        )
        rebuilt_plan.append(
            {
                "version": version,
                "focus": str((existing or {}).get("focus") or focus_default),
                "req_ids": req_ids_by_version.get(version, []),
            }
        )

    prd = {
        "title": str(raw_prd.get("title") or "App Review Insights PRD"),
        "background": str(raw_prd.get("background") or ""),
        "goals": [str(x) for x in (raw_prd.get("goals") or [])][:8],
        "non_goals": [str(x) for x in (raw_prd.get("non_goals") or [])][:8],
        "version_plan": rebuilt_plan,
        "requirements": requirements,
        "risks": [str(x) for x in (raw_prd.get("risks") or [])][:8],
        "open_questions": [str(x) for x in (raw_prd.get("open_questions") or [])][:8],
        "success_metrics": [str(x) for x in (raw_prd.get("success_metrics") or [])][:8],
    }
    return prd, rejected


def plan_prd(
    findings: list[dict[str, Any]],
    goal: str | None = None,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not findings:
        return {
            "prd": {
                "title": "Insufficient findings for PRD",
                "background": "No grounded findings were available.",
                "goals": [],
                "non_goals": ["Do not invent requirements without evidence"],
                "version_plan": [],
                "requirements": [],
                "risks": ["Insufficient review evidence"],
                "open_questions": ["Collect more reviews or broaden analysis goal"],
                "success_metrics": [],
            },
            "planning_notes": "Skipped model PRD generation because findings were empty.",
            "validation": {"accepted": 0, "rejected": 0, "rejected_items": []},
            "model": None,
            "error": None,
        }

    client = MoonshotClient()
    messages = [
        {"role": "system", "content": PRD_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_prd_user_prompt(
                goal=goal,
                findings=_compact_findings(findings),
                stats=stats,
            ),
        },
    ]
    raw = client.chat_json(messages, temperature=0.1, retries=3)
    raw_prd = raw.get("prd")
    if not isinstance(raw_prd, dict):
        # Some models may return requirements at top level
        if isinstance(raw.get("requirements"), list):
            raw_prd = raw
        else:
            raise MoonshotError("Model JSON missing prd object")

    prd, rejected = _validate_prd(raw_prd, findings)
    notes = str(raw.get("planning_notes") or "")
    if rejected:
        notes = (
            (notes + " " if notes else "")
            + f"Rejected {len(rejected)} unsupported requirement(s) after validation."
        ).strip()

    return {
        "prd": prd,
        "planning_notes": notes,
        "validation": {
            "accepted": len(prd["requirements"]),
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
