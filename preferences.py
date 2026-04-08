"""
preferences.py — Per-user preference storage for Email Rectifier Assistant.

Persists preferences to user_prefs.json so they survive server restarts.
"""

import json
import os
from typing import Optional

PREFS_FILE = os.path.join(os.path.dirname(__file__), "user_prefs.json")


class PreferencesManager:
    """Stores and retrieves per-user email preferences, backed by disk."""

    def __init__(self):
        self._prefs: dict = {}
        self._load()

    def _load(self):
        if os.path.exists(PREFS_FILE):
            try:
                with open(PREFS_FILE, "r") as f:
                    self._prefs = json.load(f)
            except Exception:
                self._prefs = {}

    def _save(self):
        try:
            with open(PREFS_FILE, "w") as f:
                json.dump(self._prefs, f, indent=2)
        except Exception:
            pass

    def save(self, username: str, prefs: dict) -> None:
        self._prefs[username] = prefs
        self._save()

    def load(self, username: str) -> Optional[dict]:
        return self._prefs.get(username)

    @staticmethod
    def get_defaults() -> dict:
        return {
            "priority_preferences":  {},           # category_lower -> bool
            "action_preferences":    {},           # category_lower -> action string
            "important_senders":     [],           # list of email addresses
            "email_distribution":    [],           # selected categories
            "notification_preference": "only_important",
            "ai_behavior": {
                "allow_scanning":      True,
                "allow_learning":      True,
                "allow_auto_actions":  False,
            },
            "fraud_sensitivity":   "MEDIUM",       # LOW | MEDIUM | HIGH
            "summary_preference":  "MEDIUM",       # SHORT | MEDIUM | DETAILED
            "task_extraction":     True,
            "custom_labels":       {},             # category_lower -> display name
            "focus_mode":          False,
            "life_mode":           "Work",         # Student | Work | Business | Job Seeker
        }
