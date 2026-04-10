"""
utils.py — Shared utility functions and task management system.
"""

import re
import uuid
from datetime import datetime
from typing import Optional


def sanitize_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text)


def truncate(text: str, max_length: int = 200) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."


def format_timestamp(dt_str: str) -> str:
    """Format a datetime string for display."""
    if not dt_str:
        return "Unknown"
    return dt_str[:30]


# ══════════════════════════════════════════════════
# TASK MANAGEMENT SYSTEM
# ══════════════════════════════════════════════════

class TaskManager:
    """
    In-memory task manager that stores extracted tasks from emails.
    Each task has: id, email_id, task, deadline, status.
    """

    def __init__(self):
        self._tasks: list[dict] = []

    def add_task(self, email_id: str, task_text: str,
                 deadline: Optional[str] = None) -> dict:
        """Create and store a new task."""
        task = {
            "id": str(uuid.uuid4()),
            "email_id": email_id,
            "task": task_text,
            "deadline": deadline,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        # Avoid duplicates (same email + same task text)
        for existing in self._tasks:
            if existing["email_id"] == email_id and existing["task"] == task_text:
                return existing
        self._tasks.append(task)
        return task

    def complete_task(self, task_id: str) -> Optional[dict]:
        """Mark a task as completed."""
        for task in self._tasks:
            if task["id"] == task_id:
                task["status"] = "completed"
                task["completed_at"] = datetime.now().isoformat()
                return task
        return None

    def get_pending_tasks(self) -> list[dict]:
        """Return all pending tasks, sorted by deadline (soonest first)."""
        pending = [t for t in self._tasks if t["status"] == "pending"]
        # Sort: tasks with deadlines first, then by deadline date
        def sort_key(t):
            if t.get("deadline"):
                return (0, t["deadline"])
            return (1, "")
        return sorted(pending, key=sort_key)

    def get_all_tasks(self) -> list[dict]:
        """Return all tasks."""
        return list(self._tasks)

    def get_tasks_for_email(self, email_id: str) -> list[dict]:
        """Return tasks extracted from a specific email."""
        return [t for t in self._tasks if t["email_id"] == email_id]

    def extract_and_store_tasks(self, email_id: str, ai_result: dict) -> list[dict]:
        """
        Extract tasks and deadlines from AI processing result
        and store them in the task manager.
        """
        stored = []

        # Store extracted tasks
        for task_text in ai_result.get("extracted_tasks", []):
            task = self.add_task(email_id, task_text)
            stored.append(task)

        # Store deadline-based tasks
        for dl in ai_result.get("deadlines", []):
            task = self.add_task(
                email_id,
                dl.get("task", "Deadline task"),
                deadline=dl.get("deadline"),
            )
            stored.append(task)

        return stored

    @property
    def pending_count(self) -> int:
        return sum(1 for t in self._tasks if t["status"] == "pending")

    @property
    def completed_count(self) -> int:
        return sum(1 for t in self._tasks if t["status"] == "completed")
