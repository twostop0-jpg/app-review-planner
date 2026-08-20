# App Review Planner

Runnable tool for App Store review analysis → findings → PRD → test cases → traceability check.

> Assessment prompt (original): see [`ASSESSMENT.md`](./ASSESSMENT.md).

## Stack

- Backend / product UI: FastAPI (Python) — open `/` after starting the server (no Node required)
- Optional UI: React (Vite) under `frontend/`
- LLM: Moonshot (analyze / plan / testcases)

## Current status (Day 7 — submission ready)

- Full pipeline: scope → collect → clean → analyze → plan → testcases → validate
- Python-served product UI at backend `/`
- Data sources: `live` / `sample` / `import`
- Model stages use evidence validation + rule fallbacks when needed

## Configure environment

```bat
cd backend
copy .env.example .env
```

Edit `backend/.env` and set:

```text
MOONSHOT_API_KEY=your_key_here
```

Do not commit secrets. Never put real API keys in the repository.

## Run (recommended)

```bat
cd backend
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Then open the **product UI**:

http://127.0.0.1:8001/

Also available:

- Health: http://127.0.0.1:8001/health
- Swagger: http://127.0.0.1:8001/docs
- User guide: [`docs/user-guide.md`](./docs/user-guide.md)

> On Windows, if port 8000 fails with WinError 10013, keep using **8001**.

## Optional React frontend

Only needed if you prefer the Vite React app:

```bat
cd frontend
npm install
npm run dev
```

## Recommended demo (offline)

In the UI (or Swagger `POST /api/jobs`):

```json
{
  "app_url": "https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684",
  "goal": "improve retention and billing clarity",
  "source": "sample",
  "import_path": null
}
```

Then poll `GET /api/jobs/{job_id}` until `succeeded`.

Expect:

- `artifacts.findings`
- `artifacts.prd.requirements`
- `artifacts.testcases`
- `artifacts.validation.ok == true`

## Import example

```json
{
  "app_url": "https://apps.apple.com/us/app/id839285684",
  "goal": "billing clarity",
  "source": "import",
  "import_path": "data/imports/example_reviews.csv"
}
```

Import formats are documented in [`docs/data-collection.md`](./docs/data-collection.md).

## Example App Store URL

```text
https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684
```

## AI-assisted development disclosure

This project was built with assistance from Cursor (AI coding assistant). Scaffolding, iteration, and mechanical wiring were accelerated by the assistant. Pipeline design choices, evidence validation rules, prompt constraints, fallbacks, and local verification were reviewed and driven by the candidate. Runtime semantic analysis uses Moonshot via the application's own prompts and validators; using an AI coding assistant alone does not satisfy the assessment AI requirements.

## Docs

- [`docs/project-delivery.md`](./docs/project-delivery.md) — 项目产出总文档
- [`docs/submission/`](./docs/submission/) — **分阶段提交材料（01–06）**
- [`docs/user-guide.md`](./docs/user-guide.md) — product guide (Chinese)
- [`docs/architecture.md`](./docs/architecture.md)
- [`docs/data-collection.md`](./docs/data-collection.md)
- [`docs/cleaning.md`](./docs/cleaning.md)
- [`docs/ai-design.md`](./docs/ai-design.md)
- [`docs/prd-planning.md`](./docs/prd-planning.md)
- [`docs/testcases-traceability.md`](./docs/testcases-traceability.md)
