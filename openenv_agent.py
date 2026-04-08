"""
openenv_agent.py — OpenEnv-compatible Email Decision Environment.

Interface:
    env.reset(emails, preferences)  → Initialize environment
    env.step(action)                → Process current email; returns (state, reward, done, info)
    env.state()                     → Current environment state dict

Reward function credits:
    +2  category classified
    +3  action matches ideal for category
    +2  action aligned with user priority preferences
    +5  correct fraud handling (DELETE/BLOCK on fraud)
    -3  wrong action on confirmed fraud
    +1  per extracted task (max 3)
    +1  summary quality
    -2  IGNORE on high-priority non-fraud email
    ×M  life-mode category multiplier
"""

import uuid
from datetime import datetime

# Ground-truth ideal action per category
CATEGORY_IDEAL_ACTIONS = {
    "SPAM":          "DELETE",
    "FINANCIAL":     "ACT_NOW",
    "PROFESSIONAL":  "ACT_NOW",
    "EDUCATIONAL":   "NEEDS_REPLY",
    "TRAVEL":        "FYI",
    "HEALTHCARE":    "ACT_NOW",
    "GOVERNMENT":    "ACT_NOW",
    "TRANSACTIONAL": "FYI",
    "PROMOTIONAL":   "IGNORE",
    "SOCIAL":        "FYI",
    "SYSTEM":        "FYI",
    "COMMUNITY":     "FYI",
    "SERVICE":       "FYI",
    "PERSONAL":      "NEEDS_REPLY",
}

# Life mode → category priority multipliers
LIFE_MODE_MULTIPLIERS = {
    "Student":    {"EDUCATIONAL": 1.4, "PROFESSIONAL": 0.8, "FINANCIAL": 1.1},
    "Work":       {"PROFESSIONAL": 1.4, "FINANCIAL": 1.2, "EDUCATIONAL": 0.9},
    "Business":   {"PROFESSIONAL": 1.5, "FINANCIAL": 1.5, "GOVERNMENT": 1.3},
    "Job Seeker": {"PROFESSIONAL": 1.6, "EDUCATIONAL": 1.2, "FINANCIAL": 1.0},
}


class EmailEnv:
    """OpenEnv-compatible environment for AI-driven email decision-making."""

    def __init__(self):
        self._emails: list = []
        self._preferences: dict = {}
        self._current_idx: int = 0
        self._history: list = []
        self._total_reward: float = 0.0
        self._session_id: str = ""

    # ── Core OpenEnv Interface ──────────────────────────────────────────────

    def reset(self, emails: list = None, preferences: dict = None) -> dict:
        """Initialize the environment with inbox emails and user preferences."""
        self._emails = emails or []
        self._preferences = preferences or {}
        self._current_idx = 0
        self._history = []
        self._total_reward = 0.0
        self._session_id = str(uuid.uuid4())
        return self.state()

    def step(self, action: str) -> tuple:
        """
        Apply action to the current email and advance.
        Returns: (state, reward, done, info)
        """
        if self._current_idx >= len(self._emails):
            return self.state(), 0.0, True, {"message": "All emails processed."}

        current = self._emails[self._current_idx]
        reward = self._compute_reward(action, current)
        self._total_reward += reward

        self._history.append({
            "email_id": current.get("id", ""),
            "subject":  current.get("subject", "")[:60],
            "category": current.get("ai", {}).get("category", "UNKNOWN"),
            "action_taken": action,
            "reward": reward,
            "timestamp": datetime.now().isoformat(),
        })

        self._current_idx += 1
        done = self._current_idx >= len(self._emails)

        return self.state(), reward, done, {
            "processed": current.get("subject", "")[:60],
            "reward": reward,
            "total_reward": round(self._total_reward, 2),
            "done": done,
        }

    def state(self) -> dict:
        """Return the full current environment state."""
        current_email = None
        if self._current_idx < len(self._emails):
            em = self._emails[self._current_idx]
            ai = em.get("ai", {})
            current_email = {
                "id":               em.get("id", ""),
                "sender":           em.get("sender", ""),
                "subject":          em.get("subject", ""),
                "category":         ai.get("category", "UNKNOWN"),
                "priority_score":   ai.get("priority_score", 0),
                "is_fraud":         ai.get("is_fraud", False),
                "fraud_probability":ai.get("fraud_probability", 0.0),
                "suggested_action": ai.get("suggested_action", "FYI"),
                "summary":          ai.get("summary", ""),
                "custom_label":     ai.get("custom_label", ""),
                "sender_importance":ai.get("sender_importance", False),
            }

        categories: dict = {}
        for h in self._history:
            cat = h.get("category", "UNKNOWN")
            categories[cat] = categories.get(cat, 0) + 1

        total = len(self._emails)
        return {
            "session_id": self._session_id,
            "inbox": {
                "total":        total,
                "processed":    self._current_idx,
                "remaining":    max(0, total - self._current_idx),
                "progress_pct": round((self._current_idx / total * 100) if total else 0, 1),
            },
            "current_email": current_email,
            "preferences": {
                "life_mode":        self._preferences.get("life_mode", "Work"),
                "fraud_sensitivity":self._preferences.get("fraud_sensitivity", "MEDIUM"),
                "focus_mode":       self._preferences.get("focus_mode", False),
            },
            "stats": {
                "total_reward":          round(self._total_reward, 2),
                "avg_reward":            round(self._total_reward / self._current_idx, 2) if self._current_idx else 0,
                "categories_processed":  categories,
            },
        }

    # ── Analytics ──────────────────────────────────────────────────────────

    def get_history(self) -> list:
        return list(self._history)

    def get_session_analytics(self) -> dict:
        if not self._history:
            return {"message": "No emails processed yet."}

        action_dist: dict = {}
        category_dist: dict = {}
        reward_by_action: dict = {}

        for h in self._history:
            a, c, r = h["action_taken"], h["category"], h["reward"]
            action_dist[a]   = action_dist.get(a, 0) + 1
            category_dist[c] = category_dist.get(c, 0) + 1
            reward_by_action.setdefault(a, []).append(r)

        return {
            "total_processed":      len(self._history),
            "total_reward":         round(self._total_reward, 2),
            "avg_reward":           round(self._total_reward / len(self._history), 2),
            "action_distribution":  action_dist,
            "category_distribution":category_dist,
            "avg_reward_by_action": {
                a: round(sum(rs) / len(rs), 2) for a, rs in reward_by_action.items()
            },
        }

    # ── Reward Function ─────────────────────────────────────────────────────

    def _compute_reward(self, action: str, email_data: dict) -> float:
        reward = 0.0
        ai          = email_data.get("ai", {})
        category    = ai.get("category", "")
        is_fraud    = ai.get("is_fraud", False)
        fraud_prob  = ai.get("fraud_probability", 0.0)
        priority    = ai.get("priority_score", 0)
        tasks       = ai.get("extracted_tasks", [])
        summary     = ai.get("summary", "")
        prefs       = self._preferences

        # 1. Category classified
        if category:
            reward += 2.0

        # 2. Fraud handling
        if is_fraud or fraud_prob >= 0.7:
            reward += 5.0 if action in ("DELETE", "BLOCK") else -3.0
        elif fraud_prob >= 0.4:
            if action in ("DELETE", "BLOCK", "IGNORE"):
                reward += 2.0
        else:
            ideal = CATEGORY_IDEAL_ACTIONS.get(category, "FYI")
            if action == ideal:
                reward += 3.0
            elif action in ("ACT_NOW", "NEEDS_REPLY") and ideal in ("ACT_NOW", "NEEDS_REPLY"):
                reward += 1.5

        # 3. Priority alignment with user preferences
        priority_prefs = prefs.get("priority_preferences", {})
        if priority_prefs.get(category.lower(), False) and action in ("ACT_NOW", "NEEDS_REPLY") and priority >= 60:
            reward += 2.0

        # 4. Action preference alignment
        action_prefs = prefs.get("action_preferences", {})
        if action_prefs.get(category.lower(), "") == action:
            reward += 1.0

        # 5. Important sender bonus
        sender = email_data.get("sender", "")
        important = prefs.get("important_senders", [])
        if any(s.lower() in sender.lower() for s in important if s):
            if action in ("ACT_NOW", "NEEDS_REPLY"):
                reward += 1.5

        # 6. Task extraction
        reward += min(len(tasks), 3) * 1.0

        # 7. Summary quality
        if summary and len(summary) > 20:
            reward += 1.0

        # 8. Penalty: ignoring high-priority non-fraud
        if priority >= 75 and action == "IGNORE" and not is_fraud:
            reward -= 2.0

        # 9. Life-mode category multiplier
        mults = LIFE_MODE_MULTIPLIERS.get(prefs.get("life_mode", "Work"), {})
        if category in mults and action in ("ACT_NOW", "NEEDS_REPLY", "FYI"):
            reward *= mults[category]

        return round(reward, 2)
