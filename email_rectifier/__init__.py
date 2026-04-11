"""Packaged OpenEnv entry points for Email Rectifier."""

from .environment import (
    EMAILS,
    GROUND_TRUTH,
    GROUND_TRUTH_REPLIES,
    RELATED_CATEGORIES,
    SPAM_IDS,
    EmailEnv,
)

__all__ = [
    "EMAILS",
    "GROUND_TRUTH",
    "GROUND_TRUTH_REPLIES",
    "RELATED_CATEGORIES",
    "SPAM_IDS",
    "EmailEnv",
]
