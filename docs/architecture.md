# Architecture notes

## Day 1
Scaffold: FastAPI job API + fake multi-stage pipeline + React polling UI.

## Day 2
- `url_parser.py`: extract App Store app id
- `collect.py`: US review collection (`live` RSS XML + MZStore fallback), cached `sample`, JSON/CSV `import`
- Pipeline `scope` + `collect` are real; `clean` was a lightweight placeholder; later stages remain placeholders
- Preview endpoint: `POST /api/collect/preview`

## Day 3
- `clean.py`: deterministic normalize / filter / dedupe + `cleaning_report`
- Pipeline `clean` is real; analyze/plan/testcases still placeholders
- Preview endpoint: `POST /api/clean/preview`
- Docs: `docs/cleaning.md`

## Day 4
- `moonshot_client.py` + `analyze.py` + `prompts/findings.py`
- Analyze stage: deterministic stats + Moonshot findings + evidence validation
- Docs: `docs/ai-design.md`
- Requires `MOONSHOT_API_KEY` in `backend/.env`

## Day 5
- `plan.py` + `prompts/prd.py` + `Requirement` schema
- Plan stage: Moonshot PRD + version split (`vNext-1` / `vNext-2` / `Research`) + finding/review link validation
- Docs: `docs/prd-planning.md`
- testcases / validate remain placeholders until Day6
