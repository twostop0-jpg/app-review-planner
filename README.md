# App Review Planner

Runnable tool for App Store review analysis → findings → PRD → test cases.

> Assessment prompt (original): see [`ASSESSMENT.md`](./ASSESSMENT.md).

## Stack

- Backend: FastAPI (Python)
- Frontend: React (Vite)
- LLM: Moonshot (wired in later days)

## Current status (Day 3)

Available now:

- Create analysis jobs via API
- React page to start a job and poll status
- Real US review collection (`live` / `sample` / `import`)
- **Deterministic cleaning**: normalize, filter empty/low-signal, id+content dedupe, cleaning report
- Later stages (analyze / PRD / testcases) still placeholders

Moonshot-powered analysis, full PRD, and traceable test cases come in later days.

## Prerequisites

- Python 3.10+
- Node.js 18+

## Configure environment

```powershell
cd backend
copy .env.example .env
# Later: set MOONSHOT_API_KEY in .env (not required for Day1 fake pipeline)
```

## Run backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check: http://127.0.0.1:8000/health  
API docs: http://127.0.0.1:8000/docs

## Run frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173).

## Example App Store URL

```text
https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684
```

## AI-assisted development disclosure

This repository is being built with assistance from an AI coding assistant (Cursor). Day1 scaffold code was generated and then reviewed for structure and local runnability. Core product logic (collection strategy, evidence validation, prompts, and traceability rules) will be designed and verified by the candidate in later commits. A final disclosure section will be updated before submission.

## Docs

- [`docs/architecture.md`](./docs/architecture.md)
- [`docs/data-collection.md`](./docs/data-collection.md)
- [`docs/ai-design.md`](./docs/ai-design.md)
