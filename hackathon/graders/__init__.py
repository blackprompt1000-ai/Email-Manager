"""
graders — Deterministic grading modules for email evaluation tasks.

Each grader:
  - Is fully deterministic (no randomness)
  - Returns a score strictly in [0.0, 1.0]
  - Works on parsed model output + expected ground truth
"""

from graders.classification_grader import ClassificationGrader
from graders.reply_grader import ReplyGrader
from graders.summarization_grader import SummarizationGrader

ALL_GRADERS = {
    "email_classification": ClassificationGrader,
    "reply_generation": ReplyGrader,
    "summarization": SummarizationGrader,
}

__all__ = [
    "ClassificationGrader",
    "ReplyGrader",
    "SummarizationGrader",
    "ALL_GRADERS",
]
