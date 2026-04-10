"""
tasks/reply_generation.py — Email reply generation evaluation task.

Tests the model's ability to generate appropriate email replies
given the email context, category, and suggested action.
"""

import re
from tasks.base import BaseTask


SAMPLES = [
    {
        "input": {
            "sender": "hr@techcorp.com",
            "subject": "Performance Review Scheduled - Q1 2026",
            "body": "Dear Team, your quarterly performance review has been scheduled for next Monday at 10 AM. Please prepare your self-assessment and project milestone updates. Meeting will be held in Conference Room B. Attendance is mandatory.",
            "category": "PROFESSIONAL",
            "action": "ACT_NOW",
        },
        "expected": {
            "must_contain": ["thank", "review", "monday"],
            "min_length": 50,
            "max_length": 500,
            "tone": "professional",
        },
    },
    {
        "input": {
            "sender": "professor.smith@university.edu",
            "subject": "Assignment 3 Due Date Extended",
            "body": "Dear Students, I am extending the deadline for Assignment 3 to April 15. Please submit your completed research paper via the course portal. Remember to include proper citations in APA format. Office hours are available Thursday 2-4 PM.",
            "category": "EDUCATIONAL",
            "action": "NEEDS_REPLY",
        },
        "expected": {
            "must_contain": ["thank", "assignment", "deadline"],
            "min_length": 40,
            "max_length": 400,
            "tone": "respectful",
        },
    },
    {
        "input": {
            "sender": "john.doe@gmail.com",
            "subject": "Catching up - long time no see!",
            "body": "Hey! Hope you're doing well. It's been ages since we last caught up. I was thinking of you the other day. Let's meet for coffee this weekend. Miss you and would love to hear how things are going with the new job. Let me know when you're free!",
            "category": "PERSONAL",
            "action": "NEEDS_REPLY",
        },
        "expected": {
            "must_contain": ["coffee", "weekend"],
            "min_length": 30,
            "max_length": 400,
            "tone": "friendly",
        },
    },
    {
        "input": {
            "sender": "appointments@mayoclinic.org",
            "subject": "Appointment Confirmation - Dr. Johnson",
            "body": "Your appointment with Dr. Sarah Johnson (Internal Medicine) is confirmed for April 14, 2026 at 2:30 PM. Please arrive 15 minutes early. Bring your insurance card and a list of current medications. Fasting required for blood test.",
            "category": "HEALTHCARE",
            "action": "ACT_NOW",
        },
        "expected": {
            "must_contain": ["appointment", "confirm"],
            "min_length": 30,
            "max_length": 400,
            "tone": "professional",
        },
    },
    {
        "input": {
            "sender": "events@meetup.com",
            "subject": "New Meetup: AI & Machine Learning Workshop",
            "body": "You're invited to a community workshop on AI and Machine Learning. Date: April 18, 2026. Location: TechHub Downtown. RSVP now to secure your spot. Network with fellow developers and data scientists. Light refreshments provided.",
            "category": "COMMUNITY",
            "action": "FYI",
        },
        "expected": {
            "must_contain": ["workshop", "attend"],
            "min_length": 30,
            "max_length": 400,
            "tone": "casual",
        },
    },
]


class ReplyGenerationTask(BaseTask):
    """Evaluate LLM's ability to generate contextual email replies."""

    @property
    def task_name(self) -> str:
        return "reply_generation"

    @property
    def task_description(self) -> str:
        return "Generate appropriate email replies based on email content, category, and action."

    def get_samples(self) -> list[dict]:
        return SAMPLES

    def build_prompt(self, sample: dict) -> str:
        inp = sample["input"]
        return (
            f"You are an AI email assistant. Generate a brief, appropriate reply "
            f"to the following email.\n\n"
            f"From: {inp['sender']}\n"
            f"Subject: {inp['subject']}\n"
            f"Body: {inp['body']}\n"
            f"Category: {inp['category']}\n"
            f"Suggested Action: {inp['action']}\n\n"
            f"Write a concise reply (50-300 words) that:\n"
            f"1. Acknowledges the key points of the email\n"
            f"2. Uses an appropriate tone for the category\n"
            f"3. Includes relevant action items if applicable\n\n"
            f"Respond with ONLY the reply text. No subject line, no metadata."
        )

    def parse_response(self, raw_response: str) -> str:
        """Return the reply text as-is after basic cleanup."""
        text = raw_response.strip()
        # Remove common LLM prefixes
        for prefix in ["Subject:", "Re:", "Reply:", "Dear", "---"]:
            if text.lower().startswith(prefix.lower()):
                # Keep "Dear" — it's part of the reply
                if prefix.lower() == "dear":
                    break
                text = text[len(prefix):].strip()
        return text
