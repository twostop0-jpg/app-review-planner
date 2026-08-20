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
