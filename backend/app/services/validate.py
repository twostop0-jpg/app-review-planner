"""Validate review → finding → requirement → testcase traceability."""

from __future__ import annotations

from typing import Any


def validate_traceability(
    *,
    reviews_cleaned: list[dict[str, Any]] | None,
    findings: list[dict[str, Any]] | None,
    prd: dict[str, Any] | None,
    testcases: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    reviews = reviews_cleaned or []
    findings = findings or []
    requirements = (prd or {}).get("requirements") or [] if isinstance(prd, dict) else []
    testcases = testcases or []

    review_ids = {str(r.get("id")) for r in reviews if r.get("id")}
    finding_ids = {str(f.get("finding_id")) for f in findings if f.get("finding_id")}
    req_ids = {str(r.get("req_id")) for r in requirements if r.get("req_id")}

    issues: list[dict[str, Any]] = []
    revisions: list[dict[str, Any]] = []

    # Findings: evidence review IDs must exist
    for finding in findings:
        fid = str(finding.get("finding_id") or "")
        evidence = [str(x) for x in (finding.get("evidence_review_ids") or [])]
        missing = [rid for rid in evidence if rid not in review_ids]
        if missing:
            issues.append(
                {
                    "level": "finding",
                    "id": fid,
                    "issue": "missing_review_ids",
                    "details": missing,
                }
            )
        if not evidence:
            issues.append(
                {
                    "level": "finding",
                    "id": fid,
                    "issue": "no_evidence",
                    "details": [],
                }
            )
        if finding.get("assumption"):
            revisions.append(
                {
                    "level": "finding",
                    "id": fid,
                    "action": "marked_assumption",
                    "reason": finding.get("uncertainty_notes") or "Thin or uncertain evidence",
                }
            )

    # Requirements: finding + review links
    for req in requirements:
        rid = str(req.get("req_id") or "")
        linked_findings = [str(x) for x in (req.get("linked_finding_ids") or [])]
        linked_reviews = [str(x) for x in (req.get("linked_review_ids") or [])]
        bad_findings = [x for x in linked_findings if x not in finding_ids]
        bad_reviews = [x for x in linked_reviews if x not in review_ids]
        if bad_findings:
            issues.append(
                {
                    "level": "requirement",
                    "id": rid,
                    "issue": "missing_finding_ids",
                    "details": bad_findings,
                }
            )
        if bad_reviews:
            issues.append(
                {
                    "level": "requirement",
                    "id": rid,
                    "issue": "missing_review_ids",
                    "details": bad_reviews,
                }
            )
        if not linked_findings or not linked_reviews:
            issues.append(
                {
                    "level": "requirement",
                    "id": rid,
                    "issue": "incomplete_trace_links",
                    "details": {
                        "linked_finding_ids": linked_findings,
                        "linked_review_ids": linked_reviews,
                    },
                }
            )

    # Test cases: req + review links; reviews should belong to linked requirements
    req_by_id = {str(r.get("req_id")): r for r in requirements if r.get("req_id")}
    covered_reqs: set[str] = set()
    for case in testcases:
        tc_id = str(case.get("tc_id") or "")
        linked_reqs = [str(x) for x in (case.get("linked_req_ids") or [])]
        linked_reviews = [str(x) for x in (case.get("linked_review_ids") or [])]
        bad_reqs = [x for x in linked_reqs if x not in req_ids]
        bad_reviews = [x for x in linked_reviews if x not in review_ids]
        if bad_reqs:
            issues.append(
                {
                    "level": "testcase",
                    "id": tc_id,
                    "issue": "missing_req_ids",
                    "details": bad_reqs,
                }
            )
        if bad_reviews:
            issues.append(
                {
                    "level": "testcase",
                    "id": tc_id,
                    "issue": "missing_review_ids",
                    "details": bad_reviews,
                }
            )

        allowed: set[str] = set()
        for req_id in linked_reqs:
            covered_reqs.add(req_id)
            for review_id in (req_by_id.get(req_id) or {}).get("linked_review_ids") or []:
                allowed.add(str(review_id))
        outside = [r for r in linked_reviews if r not in allowed]
        if outside:
            issues.append(
                {
                    "level": "testcase",
                    "id": tc_id,
                    "issue": "review_ids_not_in_linked_requirements",
                    "details": outside,
                }
            )
            revisions.append(
                {
                    "level": "testcase",
                    "id": tc_id,
                    "action": "flag_out_of_scope_reviews",
                    "reason": "Some review IDs are not inherited from linked requirements",
                }
            )
        if case.get("assumption"):
            revisions.append(
                {
                    "level": "testcase",
                    "id": tc_id,
                    "action": "marked_assumption",
                    "reason": "Test case marked as assumption by generator",
                }
            )

    uncovered = sorted(req_ids - covered_reqs)
    if uncovered:
        issues.append(
            {
                "level": "coverage",
                "id": "requirements",
                "issue": "requirements_without_testcases",
                "details": uncovered,
            }
        )
        revisions.append(
            {
                "level": "coverage",
                "id": "requirements",
                "action": "needs_more_testcases",
                "reason": f"Uncovered requirements: {', '.join(uncovered)}",
            }
        )

    chain_ok = len(issues) == 0
    summary = {
        "reviews": len(review_ids),
        "findings": len(finding_ids),
        "requirements": len(req_ids),
        "testcases": len(testcases),
        "covered_requirements": len(covered_reqs),
        "issue_count": len(issues),
        "revision_count": len(revisions),
    }

    notes = []
    if chain_ok:
        notes.append("Traceability chain is complete: reviews → findings → requirements → testcases.")
    else:
        notes.append(
            "Traceability issues found; unsupported links are listed in issues. "
            "Assumptions and coverage gaps are listed in revisions."
        )

    return {
        "ok": chain_ok,
        "summary": summary,
        "issues": issues[:50],
        "revisions": revisions[:50],
        "notes": notes,
        "chains": {
            "review_to_finding": "validated",
            "finding_to_requirement": "validated",
            "requirement_to_testcase": "validated",
        },
    }
