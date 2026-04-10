"""
auth.py — Persistent authentication system with login, signup, and password reset.

Uses SHA-256 hashing with salt. Stores users in a local JSON file.
"""

import hashlib
import json
import os
import re
import secrets
import uuid
from typing import Optional


USER_DB_PATH = os.path.join(os.path.dirname(__file__), "users.json")


class AuthManager:
    """Handles user authentication: signup, login, password reset."""

    def __init__(self):
        self._sessions: dict[str, str] = {}  # token -> username
        self._load_users()

    def _load_users(self):
        """Load users from JSON file."""
        if os.path.exists(USER_DB_PATH):
            with open(USER_DB_PATH, "r") as f:
                self._users = json.load(f)
        else:
            self._users = {}

    def _save_users(self):
        """Persist users to JSON file."""
        with open(USER_DB_PATH, "w") as f:
            json.dump(self._users, f, indent=2)

    # ── Password Validation ───────────────────────────

    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """
        Validate password against rules:
        - At least 8 characters
        - At least 1 alphabet
        - At least 1 digit
        - At least 1 special character
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r"[A-Za-z]", password):
            return False, "Password must contain at least one alphabet character."
        if not re.search(r"[0-9]", password):
            return False, "Password must contain at least one digit."
        if not re.search(r"[^A-Za-z0-9]", password):
            return False, "Password must contain at least one special character."
        return True, ""

    @staticmethod
    def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
        """Hash password with salt. Returns (hash, salt)."""
        if salt is None:
            salt = secrets.token_hex(16)
        hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return hashed, salt

    # ── Signup ────────────────────────────────────────

    def signup(self, username: str, password: str, confirm_password: str) -> dict:
        """Register a new user."""
        if not username or not username.strip():
            return {"success": False, "message": "Username cannot be empty."}

        username = username.strip().lower()

        if username in self._users:
            return {"success": False, "message": "Username already exists."}

        if password != confirm_password:
            return {"success": False, "message": "Passwords do not match."}

        valid, err = self.validate_password(password)
        if not valid:
            return {"success": False, "message": err}

        hashed, salt = self._hash_password(password)
        self._users[username] = {"hash": hashed, "salt": salt}
        self._save_users()

        token = str(uuid.uuid4())
        self._sessions[token] = username
        return {"success": True, "message": "Signup successful!", "token": token}

    # ── Login ─────────────────────────────────────────

    def login(self, username: str, password: str) -> dict:
        """Authenticate an existing user."""
        username = username.strip().lower()

        if username not in self._users:
            return {"success": False, "message": "User not found."}

        stored = self._users[username]
        hashed, _ = self._hash_password(password, stored["salt"])

        if stored["hash"] != hashed:
            return {"success": False, "message": "Invalid password."}

        token = str(uuid.uuid4())
        self._sessions[token] = username
        return {"success": True, "message": "Login successful!", "token": token}

    # ── Reset Password ────────────────────────────────

    def reset_password(
        self, username: str, new_password: str, confirm_new_password: str
    ) -> dict:
        """Reset password for an existing user."""
        username = username.strip().lower()

        if username not in self._users:
            return {"success": False, "message": "User not found. Cannot reset password."}

        if new_password != confirm_new_password:
            return {"success": False, "message": "New passwords do not match."}

        valid, err = self.validate_password(new_password)
        if not valid:
            return {"success": False, "message": err}

        hashed, salt = self._hash_password(new_password)
        self._users[username] = {"hash": hashed, "salt": salt}
        self._save_users()

        # Invalidate existing sessions
        tokens_to_remove = [t for t, u in self._sessions.items() if u == username]
        for t in tokens_to_remove:
            del self._sessions[t]

        return {"success": True, "message": "Password reset successful! Please login."}

    # ── Session Helpers ───────────────────────────────

    def verify_session(self, token: str) -> Optional[str]:
        """Return username for a valid session token, else None."""
        return self._sessions.get(token)

    def logout(self, token: str) -> bool:
        """Invalidate a session token."""
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False
