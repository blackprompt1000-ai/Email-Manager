"""
models.py  -- Pydantic models for the OpenEnv Email Triage environment.

Defines typed schemas for:
  - Observation: what the agent sees at each step
  - Action: what the agent submits
  - Reward: feedback from the environment
  - TaskResult: grading output per step
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ── Enumerations ─────────────────────────────────────────────────────────────

class EmailCategory(str, Enum):
    """All valid email categories."""
    SPAM = "spam"
    SUPPORT = "support"
    SALES = "sales"
    PERSONAL = "personal"
    FINANCIAL = "financial"
    PROFESSIONAL = "professional"
    EDUCATIONAL = "educational"
    TRAVEL = "travel"
    HEALTHCARE = "healthcare"
    GOVERNMENT = "government"
    TRANSACTIONAL = "transactional"
    PROMOTIONAL = "promotional"
    SOCIAL = "social"
    SYSTEM = "system"
    COMMUNITY = "community"
    SERVICE = "service"


class Priority(str, Enum):
    """Email priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    """Agent action types."""
    IGNORE = "ignore"
    REPLY = "reply"
    ESCALATE = "escalate"


class EmailState(str, Enum):
    """Processing state of an email."""
    PENDING = "pending"
    PROCESSED = "processed"


# ── Observation Model ────────────────────────────────────────────────────────

class EmailObservation(BaseModel):
    """What the agent observes at each environment step."""
    email_id: str = Field(..., description="Unique identifier for the email")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body text")
    sender: str = Field(..., description="Sender email address")
    current_state: EmailState = Field(
        default=EmailState.PENDING,
        description="Whether this email has been processed",
    )


class EnvironmentObservation(BaseModel):
    """Full environment observation including metadata."""
    current_email: Optional[EmailObservation] = Field(
        None, description="The email currently presented to the agent"
    )
    step_number: int = Field(0, description="Current step in the episode")
    total_emails: int = Field(0, description="Total emails in the queue")
    processed_count: int = Field(0, description="Number of emails already processed")
    remaining_count: int = Field(0, description="Number of emails left to process")
    episode_done: bool = Field(False, description="Whether the episode has ended")
    total_reward: float = Field(0.0, description="Accumulated reward so far")
    task_id: str = Field("", description="Identifier of the current task")


# ── Action Model ─────────────────────────────────────────────────────────────

class EmailAction(BaseModel):
    """The action the agent takes on a single email."""
    category: str = Field(
        ...,
        description="Predicted category (spam, support, sales, personal, etc.)",
    )
    priority: str = Field(
        ...,
        description="Predicted priority: low, medium, or high",
    )
    action_type: str = Field(
        ...,
        description="Action to take: ignore, reply, or escalate",
    )
    reply_text: Optional[str] = Field(
        None,
        description="Optional reply text when action_type is 'reply'",
    )


# ── Reward Model ─────────────────────────────────────────────────────────────

class StepReward(BaseModel):
    """Reward breakdown returned at each step."""
    total: float = Field(0.0, description="Total reward for this step")
    category_score: float = Field(0.0, description="Points for correct category")
    priority_score: float = Field(0.0, description="Points for correct priority")
    action_score: float = Field(0.0, description="Points for correct action_type")
    reply_bonus: float = Field(0.0, description="Bonus for good reply text")
    penalty: float = Field(0.0, description="Penalty for errors")
    details: str = Field("", description="Human-readable explanation")


# ── Task Result ──────────────────────────────────────────────────────────────

class TaskResult(BaseModel):
    """Result from grading a single task step."""
    score: float = Field(..., ge=0.0, le=1.0, description="Score in [0, 1]")
    max_score: float = Field(1.0, description="Maximum possible score")
    breakdown: dict = Field(
        default_factory=dict,
        description="Component-wise score breakdown",
    )
    feedback: str = Field("", description="Human-readable feedback")


# ── Step Response ────────────────────────────────────────────────────────────

class StepResponse(BaseModel):
    """Complete response from environment.step()."""
    observation: EnvironmentObservation
    reward: StepReward
    done: bool = Field(False, description="Whether the episode is over")
    info: dict = Field(default_factory=dict, description="Additional metadata")
