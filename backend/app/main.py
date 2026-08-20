from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

WEB_DIR = Path(__file__).resolve().parent / "web"
STATIC_DIR = WEB_DIR / "static"

app = FastAPI(
    title="App Review Planner",
    description=(
        "US App Store review analysis: collect → clean → findings → PRD → "
        "test cases → traceability validation. Open / for the Python-served UI."
    ),
    version="0.8.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def product_ui() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
