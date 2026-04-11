"""
environment.py  -- OpenEnv-compatible email triage RL environment.

Implements:
  - reset()   -> EnvironmentObservation
  - step(action)  -> (observation, reward, done, info)
  - state()  -> EnvironmentObservation

Supports three task difficulties:
  EASY    -- Spam vs non-spam binary classification
  MEDIUM  -- Category + priority classification
  HARD    -- Full triage (category + priority + action + optional reply)

Deterministic behaviour is guaranteed when using the built-in email
dataset (seeded order, no randomness).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from models import (
    EmailAction,
    EmailObservation,
    EmailState,
    EnvironmentObservation,
    StepReward,
    StepResponse,
)

# ── Ground-truth labels for the deterministic email dataset ──────────────────

GROUND_TRUTH: dict[str, dict[str, str]] = {
    "email-001": {"category": "financial",     "priority": "high",   "action_type": "escalate"},
    "email-002": {"category": "professional",  "priority": "high",   "action_type": "reply"},
    "email-003": {"category": "spam",          "priority": "low",    "action_type": "ignore"},
    "email-004": {"category": "social",        "priority": "low",    "action_type": "ignore"},
    "email-005": {"category": "system",        "priority": "high",   "action_type": "escalate"},
    "email-006": {"category": "healthcare",    "priority": "high",   "action_type": "reply"},
    "email-007": {"category": "promotional",   "priority": "low",    "action_type": "ignore"},
    "email-008": {"category": "personal",      "priority": "medium", "action_type": "reply"},
    "email-009": {"category": "educational",   "priority": "medium", "action_type": "reply"},
    "email-010": {"category": "transactional", "priority": "medium", "action_type": "ignore"},
    "email-011": {"category": "government",    "priority": "high",   "action_type": "escalate"},
    "email-012": {"category": "travel",        "priority": "medium", "action_type": "reply"},
    "email-013": {"category": "service",       "priority": "low",    "action_type": "ignore"},
    "email-014": {"category": "community",     "priority": "low",    "action_type": "reply"},
    "email-015": {"category": "spam",          "priority": "low",    "action_type": "ignore"},
    "email-016": {"category": "financial",     "priority": "high",   "action_type": "escalate"},
    "email-017": {"category": "support",       "priority": "medium", "action_type": "reply"},
    "email-018": {"category": "sales",         "priority": "low",    "action_type": "ignore"},
    "email-019": {"category": "professional",  "priority": "high",   "action_type": "reply"},
    "email-020": {"category": "spam",          "priority": "low",    "action_type": "ignore"},
}


# ── Deterministic email dataset ─────────────────────────────────────────────

EMAILS: list[dict[str, str]] = [
    {
        "email_id": "email-001",
        "sender": "noreply@paypal.com",
        "subject": "Your payment of $49.99 was received",
        "body": "Hi User, your payment of $49.99 to Acme Corp has been successfully processed. Transaction ID: TXN-9812374. Your current balance is $1,204.56. If you did not authorize this transaction, please contact us immediately.",
    },
    {
        "email_id": "email-002",
        "sender": "hr@techcorp.com",
        "subject": "Performance Review Scheduled - Q1 2026",
        "body": "Dear Team, your quarterly performance review has been scheduled for next Monday at 10 AM. Please prepare your self-assessment and project milestone updates. Attendance is mandatory.",
    },
    {
        "email_id": "email-003",
        "sender": "winner.lottery2026@lucky.xyz",
        "subject": "CONGRATULATIONS!!! You Won $5,000,000!!!",
        "body": "Dear Beneficiary, you have been selected as the winner of the International Lottery. Send a processing fee of $500 via wire transfer to claim your prize.",
    },
    {
        "email_id": "email-004",
        "sender": "notifications@linkedin.com",
        "subject": "You have 5 new connection requests",
        "body": "Hi User, you have 5 new connection requests waiting. John Doe, Senior Engineer at Google, wants to connect. Jane Smith endorsed you for Python.",
    },
    {
        "email_id": "email-005",
        "sender": "security@google.com",
        "subject": "New sign-in from Windows device",
        "body": "A new sign-in was detected on your Google Account. Device: Windows PC. Location: New York, USA. If you don't recognize this sign-in, change your password immediately.",
    },
    {
        "email_id": "email-006",
        "sender": "appointments@mayoclinic.org",
        "subject": "Appointment Confirmation - Dr. Johnson",
        "body": "Your appointment with Dr. Sarah Johnson is confirmed for April 14, 2026 at 2:30 PM. Fasting required for blood test. Please bring your insurance card.",
    },
    {
        "email_id": "email-007",
        "sender": "deals@bestbuy.com",
        "subject": "Flash Sale! 50% OFF Electronics",
        "body": "Don't miss our biggest sale! 50% off all laptops and accessories. Use promo code SPRING50. Free shipping on orders over $35. Limited time offer. Unsubscribe.",
    },
    {
        "email_id": "email-008",
        "sender": "john.doe@gmail.com",
        "subject": "Catching up - long time no see!",
        "body": "Hey! Hope you're doing well. It's been ages since we caught up. Let's meet for coffee this weekend. Miss you! Let me know when you're free.",
    },
    {
        "email_id": "email-009",
        "sender": "professor.smith@university.edu",
        "subject": "Assignment 3 Due Date Extended",
        "body": "Dear Students, I am extending the deadline for Assignment 3 to April 15. Submit your research paper via the course portal. Include proper APA citations.",
    },
    {
        "email_id": "email-010",
        "sender": "noreply@amazon.com",
        "subject": "Your order has shipped - Tracking #1Z999AA10",
        "body": "Your order #302-1234567-8901234 has shipped. Estimated delivery: April 12, 2026. Track with 1Z999AA10. Items: Wireless Mouse, USB-C Hub.",
    },
    {
        "email_id": "email-011",
        "sender": "noreply@irs.gov",
        "subject": "Your 2025 Tax Return Status Update",
        "body": "Your federal tax return for 2025 has been received and is being processed. Expected refund: $2,847.00. Estimated direct deposit: April 20, 2026.",
    },
    {
        "email_id": "email-012",
        "sender": "noreply@booking.com",
        "subject": "Booking Confirmed - Hotel Marriott, New York",
        "body": "Your hotel reservation is confirmed. Hotel Marriott Times Square. Check-in: April 20, 2026. Check-out: April 23, 2026. Booking ref: BK-7891234.",
    },
    {
        "email_id": "email-013",
        "sender": "billing@spotify.com",
        "subject": "Your Spotify Premium subscription renewal",
        "body": "Your Spotify Premium has been renewed. $9.99 charged to Visa ending 4242. Next billing: May 8, 2026. Manage at spotify.com/account.",
    },
    {
        "email_id": "email-014",
        "sender": "events@meetup.com",
        "subject": "New Meetup: AI & Machine Learning Workshop",
        "body": "You're invited to a community AI/ML workshop. Date: April 18, 2026. Location: TechHub Downtown. RSVP to secure your spot. Light refreshments provided.",
    },
    {
        "email_id": "email-015",
        "sender": "prince.nigerian@royalty.xyz",
        "subject": "URGENT - Inheritance Claim $10M",
        "body": "Dearest Friend, I am Prince Abubakar. My late father left $10M in a secret account. I need your help to transfer the funds. You will receive 30% for your assistance. Send your bank details immediately.",
    },
    {
        "email_id": "email-016",
        "sender": "alerts@chase.com",
        "subject": "Unusual Activity on Your Account",
        "body": "We detected unusual activity on your Chase account ending in 4521. A charge of $2,340.00 was attempted at an electronics store. If you did not make this purchase, call us immediately at 1-800-935-9935.",
    },
    {
        "email_id": "email-017",
        "sender": "support@zendesk.com",
        "subject": "Ticket #45892 - Your request has been updated",
        "body": "Hi, your support ticket #45892 regarding billing discrepancy has been updated. Our team has processed your refund of $24.99. The amount will appear in 3-5 business days.",
    },
    {
        "email_id": "email-018",
        "sender": "sales@hubspot.com",
        "subject": "Exclusive Enterprise Plan - 40% Off This Quarter",
        "body": "Hi there, we noticed your team has been growing! Upgrade to our Enterprise plan and get 40% off for the first year. Schedule a demo with our sales team today.",
    },
    {
        "email_id": "email-019",
        "sender": "manager@techcorp.com",
        "subject": "Q2 Planning Meeting - Your Input Needed",
        "body": "Hi, we are scheduling the Q2 planning meeting for next Wednesday at 2 PM. Please prepare your department roadmap and resource allocation proposals. This is critical for budget approval.",
    },
    {
        "email_id": "email-020",
        "sender": "free.iphone@giveaway.tk",
        "subject": "You've been selected! Free iPhone 16 Pro!!!",
        "body": "Congratulations! You've been randomly selected to receive a FREE iPhone 16 Pro! Click the link below to claim your prize. Only 3 left! Act now before time runs out!!!",
    },
]

# Ground truth reply snippets for HARD task grading
GROUND_TRUTH_REPLIES: dict[str, str] = {
    "email-002": "Thank you for the notification. I will prepare my self-assessment and attend the review on Monday at 10 AM.",
    "email-006": "Thank you for confirming my appointment with Dr. Johnson on April 14 at 2:30 PM. I will fast as required and bring my insurance card.",
    "email-008": "Hey! Great to hear from you. I'd love to catch up over coffee this weekend. Let me know what time works for you!",
    "email-009": "Thank you, Professor Smith. I appreciate the extended deadline. I will submit my research paper by April 15 with proper APA citations.",
    "email-012": "Thank you for confirming my reservation at Hotel Marriott for April 20-23. I look forward to my stay.",
    "email-014": "Thanks for the invitation! I'm interested in the AI & ML workshop on April 18. I'll RSVP and plan to attend.",
    "email-017": "Thank you for processing my refund of $24.99 for ticket #45892. I will check my statement in 3-5 business days.",
    "email-019": "Thank you. I will prepare the department roadmap and resource allocation proposals for the Q2 planning meeting on Wednesday at 2 PM.",
}


# Spam email IDs for easy task
SPAM_IDS: set[str] = {"email-003", "email-015", "email-020"}

MAX_STEPS: int = 25  # Maximum steps per episode


class EmailEnv:
    """
    OpenEnv-compatible reinforcement learning environment for email triage.

    The agent receives emails one at a time and must classify, prioritize,
    and decide on an action. The environment provides reward feedback at
    every step based on how well the agent's decisions match ground truth.

    Supports three task difficulties via task_id:
      'easy'    -- binary spam detection
      'medium'  -- category + priority classification
      'hard'    -- full triage including action and optional reply
    """

    def __init__(self) -> None:
        self._emails: list[dict[str, str]] = []
        self._ground_truth: dict[str, dict[str, str]] = {}
        self._current_idx: int = 0
        self._total_reward: float = 0.0
        self._step_count: int = 0
        self._session_id: str = ""
        self._task_id: str = "hard"
        self._processed_ids: set[str] = set()
        self._done: bool = False
        self._history: list[dict] = []

    # ── Core API ─────────────────────────────────────────────────────────────

    def reset(
        self,
        task_id: str = "hard",
        emails: Optional[list[dict[str, str]]] = None,
        ground_truth: Optional[dict[str, dict[str, str]]] = None,
    ) -> dict:
        """
        Reset the environment to the beginning of a new episode.

        Args:
            task_id: One of 'easy', 'medium', 'hard'.
            emails: Optional custom email list. Uses built-in dataset if None.
            ground_truth: Optional custom ground truth. Uses built-in if None.

        Returns:
            Serialised EnvironmentObservation dict.
        """
        self._task_id = task_id
        self._emails = emails if emails is not None else list(EMAILS)
        self._ground_truth = ground_truth if ground_truth is not None else dict(GROUND_TRUTH)
        self._current_idx = 0
        self._total_reward = 0.0
        self._step_count = 0
        self._session_id = str(uuid.uuid4())
        self._processed_ids = set()
        self._done = False
        self._history = []
        return self.state()

    def step(self, action: dict | str) -> tuple[dict, float, bool, dict]:
        """
        Apply an action to the current email and advance the environment.

        Args:
            action: Either a dict matching EmailAction schema, or a JSON string.

        Returns:
            Tuple of (observation_dict, reward_float, done_bool, info_dict).
        """
        # Parse action
        if isinstance(action, str):
            import json
            try:
                action = json.loads(action)
            except (json.JSONDecodeError, TypeError):
                action = {"category": action, "priority": "low", "action_type": "ignore"}

        if not isinstance(action, dict):
            action = {"category": "spam", "priority": "low", "action_type": "ignore"}

        # Episode already done
        if self._done or self._current_idx >= len(self._emails):
            self._done = True
            return self.state(), 0.0, True, {"message": "Episode finished. Call reset()."}

        current_email = self._emails[self._current_idx]
        email_id = current_email["email_id"]

        # Penalty for re-processing the same email
        if email_id in self._processed_ids:
            penalty_reward = -0.5
            self._total_reward += penalty_reward
            self._step_count += 1
            self._current_idx += 1
            done = self._current_idx >= len(self._emails) or self._step_count >= MAX_STEPS
            self._done = done
            return self.state(), penalty_reward, done, {
                "message": f"Duplicate action on {email_id}. Penalty applied.",
                "penalty": True,
            }

        # Compute reward
        reward_obj = self._compute_reward(action, current_email)
        reward_float = reward_obj.total
        self._total_reward += reward_float

        # Record history
        self._processed_ids.add(email_id)
        self._history.append({
            "email_id": email_id,
            "action": action,
            "reward": reward_float,
            "step": self._step_count,
        })

        self._step_count += 1
        self._current_idx += 1

        done = self._current_idx >= len(self._emails) or self._step_count >= MAX_STEPS
        self._done = done

        return self.state(), reward_float, done, {
            "reward_breakdown": reward_obj.model_dump(),
            "email_id": email_id,
            "step": self._step_count,
        }

    def state(self) -> dict:
        """
        Return the current environment observation as a dict.

        Returns:
            Serialised EnvironmentObservation dict.
        """
        current_email = None
        if not self._done and self._current_idx < len(self._emails):
            e = self._emails[self._current_idx]
            current_email = EmailObservation(
                email_id=e["email_id"],
                subject=e["subject"],
                body=e["body"],
                sender=e["sender"],
                current_state=EmailState.PENDING,
            ).model_dump()

        obs = EnvironmentObservation(
            current_email=current_email,
            step_number=self._step_count,
            total_emails=len(self._emails),
            processed_count=len(self._processed_ids),
            remaining_count=max(0, len(self._emails) - self._current_idx),
            episode_done=self._done,
            total_reward=round(self._total_reward, 4),
            task_id=self._task_id,
        )
        return obs.model_dump()

    def get_history(self) -> list[dict]:
        """Return the full action history for the current episode."""
        return list(self._history)

    # ── Reward Logic ─────────────────────────────────────────────────────────

    def _compute_reward(self, action: dict, email: dict) -> StepReward:
        """Compute per-step reward based on task difficulty and ground truth."""
        email_id = email["email_id"]
        gt = self._ground_truth.get(email_id, {})
        if not gt:
            return StepReward(total=0.0, details="No ground truth for this email.")

        gt_category = gt.get("category", "").lower().strip()
        gt_priority = gt.get("priority", "").lower().strip()
        gt_action = gt.get("action_type", "").lower().strip()

        pred_category = str(action.get("category", "")).lower().strip()
        pred_priority = str(action.get("priority", "")).lower().strip()
        pred_action = str(action.get("action_type", "")).lower().strip()
        pred_reply = str(action.get("reply_text", "") or "")

        cat_score = 0.0
        pri_score = 0.0
        act_score = 0.0
        reply_bonus = 0.0
        penalty = 0.0
        details_parts: list[str] = []

        task = self._task_id

        # ── EASY: spam vs non-spam ────────────────────────────────────
        if task == "easy":
            is_spam_gt = gt_category == "spam"
            is_spam_pred = pred_category == "spam"
            if is_spam_gt == is_spam_pred:
                cat_score = 1.0
                details_parts.append("Correct spam classification.")
            else:
                cat_score = 0.0
                penalty = -0.2
                details_parts.append("Wrong spam classification.")

        # ── MEDIUM: category + priority ───────────────────────────────
        elif task == "medium":
            # Category scoring (0.6 weight)
            if pred_category == gt_category:
                cat_score = 0.6
                details_parts.append(f"Category correct: {gt_category}")
            elif _is_related_category(pred_category, gt_category):
                cat_score = 0.3
                details_parts.append(f"Category partially correct: {pred_category} ~ {gt_category}")
            else:
                cat_score = 0.0
                details_parts.append(f"Category wrong: {pred_category} != {gt_category}")

            # Priority scoring (0.4 weight)
            if pred_priority == gt_priority:
                pri_score = 0.4
                details_parts.append(f"Priority correct: {gt_priority}")
            elif _priority_distance(pred_priority, gt_priority) == 1:
                pri_score = 0.2
                details_parts.append(f"Priority close: {pred_priority} ~ {gt_priority}")
            else:
                pri_score = 0.0
                details_parts.append(f"Priority wrong: {pred_priority} != {gt_priority}")

        # ── HARD: full triage ─────────────────────────────────────────
        else:  # task == "hard"
            # Category (0.4)
            if pred_category == gt_category:
                cat_score = 0.4
                details_parts.append(f"Category correct: {gt_category}")
            elif _is_related_category(pred_category, gt_category):
                cat_score = 0.2
                details_parts.append(f"Category partial: {pred_category} ~ {gt_category}")
            else:
                details_parts.append(f"Category wrong: {pred_category} != {gt_category}")

            # Priority (0.3)
            if pred_priority == gt_priority:
                pri_score = 0.3
                details_parts.append(f"Priority correct: {gt_priority}")
            elif _priority_distance(pred_priority, gt_priority) == 1:
                pri_score = 0.15
                details_parts.append(f"Priority close: {pred_priority} ~ {gt_priority}")
            else:
                details_parts.append(f"Priority wrong: {pred_priority} != {gt_priority}")

            # Action (0.3)
            if pred_action == gt_action:
                act_score = 0.3
                details_parts.append(f"Action correct: {gt_action}")
            elif _is_related_action(pred_action, gt_action):
                act_score = 0.15
                details_parts.append(f"Action partial: {pred_action} ~ {gt_action}")
            else:
                details_parts.append(f"Action wrong: {pred_action} != {gt_action}")

            # Reply bonus (up to 0.1 extra for hard task)
            if gt_action == "reply" and pred_action == "reply" and pred_reply:
                gt_reply = GROUND_TRUTH_REPLIES.get(email_id, "")
                if gt_reply:
                    reply_bonus = _score_reply(pred_reply, gt_reply) * 0.1
                    if reply_bonus > 0:
                        details_parts.append(f"Reply bonus: +{reply_bonus:.3f}")

        # Penalty: ignoring high-priority email
        if gt_priority == "high" and pred_action == "ignore":
            penalty = -0.15
            details_parts.append("Penalty: ignoring high-priority email.")

        total = round(cat_score + pri_score + act_score + reply_bonus + penalty, 4)
        total = max(-1.0, min(1.5, total))  # Clamp

        return StepReward(
            total=total,
            category_score=round(cat_score, 4),
            priority_score=round(pri_score, 4),
            action_score=round(act_score, 4),
            reply_bonus=round(reply_bonus, 4),
            penalty=round(penalty, 4),
            details=" | ".join(details_parts),
        )


# ── Helper Functions ─────────────────────────────────────────────────────────

RELATED_CATEGORIES: dict[str, set[str]] = {
    "financial":     {"financial", "transactional"},
    "transactional": {"transactional", "financial"},
    "professional":  {"professional", "educational"},
    "educational":   {"educational", "professional"},
    "service":       {"service", "system", "transactional"},
    "system":        {"system", "service"},
    "social":        {"social", "community", "personal"},
    "community":     {"community", "social"},
    "personal":      {"personal", "social"},
    "promotional":   {"promotional", "sales", "service"},
    "sales":         {"sales", "promotional"},
    "support":       {"support", "service"},
    "spam":          {"spam"},
    "travel":        {"travel", "transactional"},
    "healthcare":    {"healthcare"},
    "government":    {"government"},
}

PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def _is_related_category(pred: str, gt: str) -> bool:
    """Check if predicted category is in the same family as ground truth."""
    family = RELATED_CATEGORIES.get(gt, {gt})
    return pred in family


def _priority_distance(pred: str, gt: str) -> int:
    """Return the absolute distance between two priority levels."""
    return abs(PRIORITY_ORDER.get(pred, -1) - PRIORITY_ORDER.get(gt, -1))


def _is_related_action(pred: str, gt: str) -> bool:
    """Check if two actions are 'close enough' for partial credit."""
    related = {
        ("reply", "escalate"),
        ("escalate", "reply"),
    }
    return (pred, gt) in related


def _score_reply(predicted: str, ground_truth: str) -> float:
    """Score reply text quality based on keyword overlap with ground truth."""
    if not predicted or not ground_truth:
        return 0.0
    pred_words = set(predicted.lower().split())
    gt_words = set(ground_truth.lower().split())
    if not gt_words:
        return 0.0
    overlap = len(pred_words & gt_words) / len(gt_words)
    return min(1.0, overlap)
