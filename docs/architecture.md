# Architecture notes

## Day 1
Scaffold: FastAPI job API + fake multi-stage pipeline + React polling UI.

## Day 2
- `url_parser.py`: extract App Store app id
- `collect.py`: US review collection (`live` RSS XML + MZStore fallback), cached `sample`, JSON/CSV `import`
- Pipeline `scope` + `collect` are real; `clean` is a lightweight placeholder; later stages remain placeholders
- Preview endpoint: `POST /api/collect/preview`
