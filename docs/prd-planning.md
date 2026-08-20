# PRD / version planning

## Input

- Grounded `findings` from the analyze stage
- Optional analysis `goal`
- Deterministic `analysis_stats` (context only)

## Output artifacts

| Key | Meaning |
|-----|---------|
| `prd` | Title, background, goals/non-goals, version plan, requirements, risks, metrics |
| `planning_notes` | Short model/backend notes |
| `planning_validation` | Accepted/rejected requirement counts + rejected samples |
| `planning_model` | Provider/model/temperature used |

## Version split

| Version | Intent |
|---------|--------|
| `vNext-1` | P0, high-evidence, goal-critical |
| `vNext-2` | P1 important follow-ups |
| `Research` | Weak evidence, assumptions, or conflicts |

## Validation rules

1. Each requirement must link to at least one existing `finding_id`.
2. `linked_review_ids` are taken from those findings (model-claimed IDs are filtered).
3. Requirements with no valid finding or review links are rejected.
4. `version_plan.req_ids` is rebuilt from validated requirements.

## Prompt location

- `backend/app/prompts/prd.py`

## Failure handling

- Empty findings → empty PRD with explicit insufficient-evidence notes (no model call)
- Missing API key / Moonshot errors → job fails at plan stage only if fallback cannot build requirements
- Invalid JSON → repair retries, then deterministic rule-based PRD fallback (still linked to findings)
- Hallucinated finding/review links → requirement rejected
