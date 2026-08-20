# App Review Planner

Runnable tool for App Store review analysis → findings → PRD → test cases.

> Assessment prompt (original): see [`ASSESSMENT.md`](./ASSESSMENT.md).

## Stack

- Backend: FastAPI (Python)
- Frontend: React (Vite)
- LLM: Moonshot (Day4+ analyze stage)

## Current status (Day 4)

Available now:

- Create analysis jobs via API
- React page to start a job and poll status
- Real US review collection (`live` / `sample` / `import`)
- Deterministic cleaning + cleaning report
- **Moonshot evidence-grounded findings** (`artifacts.findings`)
- PRD / testcases still placeholders

## Configure environment

```powershell
cd backend
copy .env.example .env
# Required for Day4+ analyze stage:
# set MOONSHOT_API_KEY=your_key_here
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
- [`docs/cleaning.md`](./docs/cleaning.md)
- [`docs/ai-design.md`](./docs/ai-design.md)
