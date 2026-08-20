# AI design

## Provider

- Provider: Moonshot (月之暗面)
- API style: OpenAI-compatible Chat Completions
- Default model: `moonshot-v1-32k` (configurable via `MOONSHOT_MODEL`)
- Temperature: `0.2` (prefer grounded, less creative answers)
- Secrets: `backend/.env` (`MOONSHOT_API_KEY`), never committed

## Where the model is used

| Stage | Method | Why |
|------|--------|-----|
| collect | rules / HTTP | deterministic fetch |
| clean | rules / stats | deterministic normalize/dedupe |
| **analyze** | **Moonshot + stats** | dynamic issue discovery and consolidation |
| **plan** | **Moonshot + validation** | PRD + P0/P1/Research version split |
| **testcases** | **Moonshot + validation** | Requirement-linked test design |
| **validate** | **rules** | Full review→finding→req→testcase chain |

## Analyze stage design

1. Build deterministic stats (rating histogram, low-rating rate, top versions). Origin = `stat`.
2. Send compact reviews + goal + stats to Moonshot.
3. Ask for JSON findings with evidence review IDs / excerpts / confidence / conflicts / uncertainty.
4. Backend validates every finding:
   - drop findings with zero valid review IDs
   - recompute `support_count` from valid IDs
   - mark `origin = model`
5. Keep rejected unsupported findings in `analysis_validation.rejected_items`.

## Plan stage design

1. Compact findings (+ goal + stats) → Moonshot.
2. Ask for PRD JSON with versioned requirements and acceptance criteria.
3. Backend validates every requirement:
   - must link to existing finding IDs
   - review IDs inherited/filtered from linked findings
   - rebuild `version_plan` from accepted requirements
4. Reject unsupported requirements into `planning_validation`.

See also: `docs/prd-planning.md`.

## Testcases stage design

1. Compact requirements → Moonshot.
2. Ask for JSON test cases with steps, expected results, and req/review links.
3. Backend validates links against PRD requirements.
4. On JSON failure → deterministic fallback (one case per requirement from acceptance criteria).

## Validate stage design

Deterministic full-chain check. See `docs/testcases-traceability.md`.

## Prompt location

- `backend/app/prompts/findings.py`
- `backend/app/prompts/prd.py`
- `backend/app/prompts/testcases.py`

## Failure handling

- Missing API key → clear `MoonshotError`, job fails at analyze/plan stage
- HTTP / API errors → surfaced in job `error`
- Invalid JSON → retry up to 2 repair attempts asking for JSON-only output
- Hallucinated review IDs → removed by evidence validator (not shown as accepted findings)
- Hallucinated finding/review links in PRD → requirement rejected

## Anti-hallucination measures

- Low temperature
- Strict JSON-only instruction
- Evidence ID allow-list validation against cleaned reviews
- Requirement links must resolve to accepted findings
- Unsupported conclusions rejected or marked via `assumption` / `uncertainty_notes`
- Deterministic stats kept separate from model findings
