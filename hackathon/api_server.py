"""
api_server.py — FastAPI server for OpenEnv compliance.

Exposes:
    POST /reset   — Reset the environment
    POST /step    — Take an action on current email
    GET  /state   — Get current environment state
    GET  /        — Health check (returns HTTP 200)

Uses the existing EmailEnv from openenv_agent.py with synthetic
demo data for standalone operation.
"""

import os
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from email_rectifier import EmailEnv
from ai_processor import process_email

# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Email Rectifier — OpenEnv API",
    description="OpenEnv-compatible API for AI email decision-making environment.",
    version="2.0.0",
)

# ── Global Environment Instance ─────────────────────────────────────────────
env = EmailEnv()
_initialized = False


# ── Demo Email Data ──────────────────────────────────────────────────────────
def _get_demo_emails() -> list[dict]:
    """Return deterministic demo emails for standalone API mode."""
    raw_emails = [
        {
            "id": "demo-001",
            "sender": "noreply@paypal.com",
            "subject": "Your payment of $49.99 was received",
            "body": "Hi User, your payment of $49.99 to Acme Corp has been successfully processed. Transaction ID: TXN-9812374. Your current balance is $1,204.56.",
            "date": "Apr 09, 2026 10:00 AM",
        },
        {
            "id": "demo-002",
            "sender": "hr@techcorp.com",
            "subject": "Performance Review Scheduled - Q1 2026",
            "body": "Dear Team, your quarterly performance review has been scheduled for next Monday at 10 AM. Please prepare your self-assessment. Attendance is mandatory.",
            "date": "Apr 09, 2026 09:30 AM",
        },
        {
            "id": "demo-003",
            "sender": "winner.lottery@lucky.xyz",
            "subject": "CONGRATULATIONS!!! You Won $5,000,000!!!",
            "body": "Dear Beneficiary, you have been selected as the winner of the International Lottery. Send a processing fee of $500 via wire transfer to claim your prize.",
            "date": "Apr 09, 2026 08:00 AM",
        },
        {
            "id": "demo-004",
            "sender": "notifications@linkedin.com",
            "subject": "You have 5 new connection requests",
            "body": "Hi User, you have 5 new connection requests waiting. John Doe, Senior Engineer at Google, wants to connect. Jane Smith endorsed you for Python.",
            "date": "Apr 09, 2026 07:45 AM",
        },
        {
            "id": "demo-005",
            "sender": "security@google.com",
            "subject": "New sign-in from Windows device",
            "body": "A new sign-in was detected on your Google Account. Device: Windows PC. Location: New York, USA. If you don't recognize this sign-in, change your password immediately.",
            "date": "Apr 09, 2026 07:00 AM",
        },
        {
            "id": "demo-006",
            "sender": "appointments@mayoclinic.org",
            "subject": "Appointment Confirmation - Dr. Johnson",
            "body": "Your appointment with Dr. Sarah Johnson is confirmed for April 14, 2026 at 2:30 PM. Fasting required for blood test. Bring your insurance card.",
            "date": "Apr 08, 2026 04:00 PM",
        },
        {
            "id": "demo-007",
            "sender": "deals@bestbuy.com",
            "subject": "Flash Sale! 50% OFF Electronics",
            "body": "Don't miss our biggest sale! 50% off all laptops and accessories. Use promo code SPRING50. Free shipping on orders over $35. Limited time offer. Unsubscribe.",
            "date": "Apr 08, 2026 02:00 PM",
        },
        {
            "id": "demo-008",
            "sender": "john.doe@gmail.com",
            "subject": "Catching up - long time no see!",
            "body": "Hey! Hope you're doing well. It's been ages since we caught up. Let's meet for coffee this weekend. Miss you! Let me know when you're free.",
            "date": "Apr 08, 2026 11:00 AM",
        },
    ]

    # Process each email through the AI processor for realistic data
    processed = []
    for em in raw_emails:
        ai_result = process_email(em)
        processed.append({**em, "ai": ai_result})

    return processed


def _get_demo_preferences() -> dict:
    """Return default preferences for standalone mode."""
    return {
        "life_mode": "Work",
        "fraud_sensitivity": "MEDIUM",
        "focus_mode": False,
        "priority_preferences": {},
        "action_preferences": {},
        "important_senders": [],
    }


# ── Request Models ───────────────────────────────────────────────────────────

class StepRequest(BaseModel):
    action: str = "FYI"

class ResetRequest(BaseModel):
    emails: Optional[list] = None
    preferences: Optional[dict] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    """Health check — returns HTTP 200."""
    return JSONResponse(
        content={
            "status": "ok",
            "service": "Email Rectifier — OpenEnv API",
            "version": "2.0.0",
        },
        status_code=200,
    )


@app.post("/reset")
def reset_env(req: ResetRequest = ResetRequest()):
    """
    Reset the environment.
    If no emails/preferences provided, uses demo data.
    """
    global _initialized

    emails = req.emails if req.emails else _get_demo_emails()
    preferences = req.preferences if req.preferences else _get_demo_preferences()

    state = env.reset(emails, preferences)
    _initialized = True

    return JSONResponse(
        content={"success": True, "state": state, "message": "Environment reset."},
        status_code=200,
    )


@app.post("/step")
def step_env(req: StepRequest):
    """
    Take an action on the current email.
    Valid actions: FYI, ACT_NOW, NEEDS_REPLY, IGNORE, DELETE, BLOCK
    """
    global _initialized

    if not _initialized:
        # Auto-initialize with demo data
        emails = _get_demo_emails()
        prefs = _get_demo_preferences()
        env.reset(emails, prefs)
        _initialized = True

    valid_actions = {"FYI", "ACT_NOW", "NEEDS_REPLY", "IGNORE", "DELETE", "BLOCK"}
    action = req.action.upper().strip()
    if action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{action}'. Must be one of: {', '.join(sorted(valid_actions))}",
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
        # Auto-initialize with demo data
        emails = _get_demo_emails()
        prefs = _get_demo_preferences()
        env.reset(emails, prefs)
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
