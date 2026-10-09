"""
TrailMate AI - Outdoor Plan Request / Response Schemas
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


# ── Request ───────────────────────────────────────────────────────────────────

class PlanRequest(BaseModel):
    time_available: int = Field(
        ...,
        ge=15,
        le=480,
        description="Available time in minutes (15 – 480).",
        examples=[90],
    )
    activity: str = Field(
        ...,
        min_length=2,
        max_length=64,
        description="Type of outdoor activity, e.g. walking, cycling, hiking.",
        examples=["walking"],
    )
    intensity: Literal["low", "moderate", "high"] = Field(
        ...,
        description="Desired effort level.",
        examples=["moderate"],
    )
    budget: float = Field(
        0,
        ge=0,
        description="Budget in local currency. 0 means free activities only.",
        examples=[0],
    )
    location: str = Field(
        ...,
        min_length=2,
        max_length=128,
        description="City or neighbourhood used as a planning hint (not verified map data).",
        examples=["Mumbai"],
    )


# ── Response ──────────────────────────────────────────────────────────────────

class PlanResponse(BaseModel):
    title: str = Field(..., description="Short, catchy mission title.")
    summary: str = Field(..., description="2-3 sentence overview of the adventure.")
    duration_minutes: int = Field(..., description="Total planned duration in minutes.")
    activity: str = Field(..., description="Primary activity type.")
    difficulty: str = Field(..., description="Effort level (mirrors the requested intensity).")
    mission: str = Field(..., description="The main outdoor mission description.")
    route_idea: str = Field(
        ...,
        description=(
            "General route suggestion. "
            "Does not claim specific trails or landmarks exist."
        ),
    )
    things_to_carry: List[str] = Field(..., description="Recommended items to bring.")
    challenge: str = Field(..., description="A small 'touch grass' style bonus challenge.")
    safety_tips: List[str] = Field(..., description="Safety reminders for the activity.")
