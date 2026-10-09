"""
TrailMate AI - FastAPI Application Entry Point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.schemas.plan import PlanRequest, PlanResponse
from backend.app.services.llm_service import build_chat_prompt, generate_text
from backend.app.services.trailmate_service import create_plan

# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered outdoor adventure planner.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ──────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    response: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Returns a simple health status for liveness probes."""
    return {"status": "ok"}


@app.post("/api/ai/generate", response_model=GenerateResponse, tags=["AI"])
def generate(request: GenerateRequest) -> GenerateResponse:
    """
    Temporary test endpoint — invokes the local SmolLM2 model via llama-cli
    and returns the generated text.

    Using a plain ``def`` (not ``async def``) so FastAPI dispatches the
    blocking subprocess call to a thread-pool worker automatically.
    """
    try:
        text = generate_text(build_chat_prompt(request.prompt))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return GenerateResponse(response=text)


# ── TrailMate Planner ─────────────────────────────────────────────────────────

@app.post("/api/trailmate/plan", response_model=PlanResponse, tags=["TrailMate"])
def plan(request: PlanRequest) -> PlanResponse:
    """
    Generate a personalised outdoor adventure plan using the local SmolLM2 model.

    Accepts the user's available time, activity preference, intensity, budget,
    and location, and returns a structured mission plan as JSON.
    """
    try:
        return create_plan(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
