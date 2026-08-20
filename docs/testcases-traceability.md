# Test cases and traceability

## Testcases stage

### Input
- PRD `requirements` (with linked finding/review IDs)
- Optional analysis goal

### Output artifacts
| Key | Meaning |
|-----|---------|
| `testcases` | Executable cases with steps, expected results, req/review links |
| `testing_notes` | Model/backend notes |
| `testcase_validation` | Accepted/rejected counts |
| `testcase_model` | Provider/model used (or rule fallback) |

### Validation rules
1. Each test case must link to existing `req_id`s.
2. Review IDs must come from the linked requirements.
3. Invalid cases are rejected; if the model returns none valid, use rule fallback.

## Validate stage

Deterministic check of the full chain:

`reviews → findings → requirements → testcases`

### Checks
- Finding evidence review IDs exist in cleaned reviews
- Requirement finding/review links resolve
- Test case req/review links resolve and stay within linked requirements
- Requirement coverage by at least one test case
- Assumptions and gaps recorded in `validation.revisions`

### Output
`artifacts.validation` with `ok`, `summary`, `issues`, `revisions`, `notes`

## Prompts
- `backend/app/prompts/testcases.py`
