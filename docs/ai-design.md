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
| plan / testcases | placeholder (Day5/6) | later |

## Analyze stage design

1. Build deterministic stats (rating histogram, low-rating rate, top versions). Origin = `stat`.
2. Send compact reviews + goal + stats to Moonshot.
3. Ask for JSON findings with evidence review IDs / excerpts / confidence / conflicts / uncertainty.
4. Backend validates every finding:
   - drop findings with zero valid review IDs
   - recompute `support_count` from valid IDs
   - mark `origin = model`
5. Keep rejected unsupported findings in `analysis_validation.rejected_items`.

## Prompt location

- `backend/app/prompts/findings.py`

## Failure handling

- Missing API key → clear `MoonshotError`, job fails at analyze stage
- HTTP / API errors → surfaced in job `error`
- Invalid JSON → retry up to 2 repair attempts asking for JSON-only output
- Hallucinated review IDs → removed by evidence validator (not shown as accepted findings)

## Anti-hallucination measures

- Low temperature
- Strict JSON-only instruction
- Evidence ID allow-list validation against cleaned reviews
- Unsupported conclusions rejected or marked via `assumption` / `uncertainty_notes`
- Deterministic stats kept separate from model findings
