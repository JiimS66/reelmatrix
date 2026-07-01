import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict


router = APIRouter(tags=["health"])

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _commit_sha() -> str:
    """The deployed git commit — from the environment (compose/CI) or a VERSION file
    stamped into the release archive at packaging time. A deploy marker: lets a test
    loop confirm the fix is actually live before rerunning against the app."""
    env = os.environ.get("COMMIT_SHA", "").strip()
    if env:
        return env
    try:
        return (_REPO_ROOT / "VERSION").read_text().strip() or "unknown"
    except OSError:
        return "unknown"


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    commit: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", commit=_commit_sha())
