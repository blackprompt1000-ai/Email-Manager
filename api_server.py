"""
api_server.py  -- FastAPI server for OpenEnv compliance.

Exposes:
    POST /reset    -- Reset the environment (accepts task_id)
    POST /step     -- Take an action on current email
    GET  /state    -- Get current environment state
    GET  /         -- Health check (returns HTTP 200)
    GET  /tasks    -- List available tasks
"""

import os
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from email_rectifier import EmailEnv
from models import EmailAction

# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Email Rectifier  -- OpenEnv API",
    description="OpenEnv-compatible API for AI email triage RL environment.",
    version="3.0.0",
)

# ── Global Environment Instance ─────────────────────────────────────────────
env = EmailEnv()
_initialized = False


# ── Request Models ───────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: str = "hard"

class StepRequest(BaseModel):
    action: dict


# ── Task Definitions ─────────────────────────────────────────────────────────

TASKS = [
    {
        "id": "easy",
        "name": "Spam Detection",
        "description": "Binary classification: spam vs non-spam.",
        "difficulty": "easy",
        "num_emails": 20,
        "objective": "Correctly identify spam emails from legitimate ones.",
    },
    {
        "id": "medium",
        "name": "Category + Priority Classification",
        "description": "Classify emails into category and priority level.",
        "difficulty": "medium",
        "num_emails": 20,
        "objective": "Correctly classify email category and assign appropriate priority.",
    },
    {
        "id": "hard",
        "name": "Full Email Triage",
        "description": "Full triage: category + priority + action type + optional reply.",
        "difficulty": "hard",
        "num_emails": 20,
        "objective": "Correctly classify, prioritize, decide action, and optionally generate reply.",
    },
]


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    """Health check  -- returns HTTP 200."""
    return JSONResponse(
        content={
            "status": "ok",
            "service": "Email Rectifier  -- OpenEnv API",
            "version": "3.0.0",
            "endpoints": ["/reset", "/step", "/state", "/tasks"],
        },
        status_code=200,
    )


@app.get("/tasks")
def list_tasks():
    """List all available tasks."""
    return JSONResponse(content={"tasks": TASKS}, status_code=200)


@app.post("/reset")
def reset_env(req: ResetRequest = ResetRequest()):
    """
    Reset the environment for a new episode.

    Args:
        task_id: 'easy', 'medium', or 'hard' (default: 'hard')
    """
    global _initialized

    if req.task_id not in {"easy", "medium", "hard"}:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task_id '{req.task_id}'. Must be: easy, medium, hard",
        )

    state = env.reset(task_id=req.task_id)
    _initialized = True

    return JSONResponse(
        content={"success": True, "state": state, "message": f"Environment reset for task: {req.task_id}"},
        status_code=200,
    )


@app.post("/step")
def step_env(req: StepRequest):
    """
    Take an action on the current email.

    Action dict must contain: category, priority, action_type.
    Optional: reply_text (for hard task).
    """
    global _initialized

    if not _initialized:
        env.reset(task_id="hard")
        _initialized = True

    action = req.action

    # Validate required keys
    required_keys = {"category", "priority", "action_type"}
    missing = required_keys - set(action.keys())
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required action keys: {', '.join(missing)}. "
                   f"Action must include: category, priority, action_type",
        )

    state, reward, done, info = env.step(action)

    return JSONResponse(
        content={
            "success": True,
            "state": state,
            "reward": reward,
            "done": done,
            "info": info,
        },
        status_code=200,
    )


@app.get("/state")
def get_state():
    """Get current environment state."""
    global _initialized

    if not _initialized:
        env.reset(task_id="hard")
        _initialized = True

    return JSONResponse(
        content={"success": True, "state": env.state()},
        status_code=200,
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Console entrypoint used by uv and package installs."""
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
