"""
tasks — Evaluation task modules for the Email Rectifier Assistant.

Each task defines:
  - A set of test samples (deterministic)
  - A prompt builder for the LLM
  - Integration with the corresponding grader
"""

from tasks.email_classification import EmailClassificationTask
from tasks.reply_generation import ReplyGenerationTask
from tasks.summarization import SummarizationTask

ALL_TASKS = [
    EmailClassificationTask,
    ReplyGenerationTask,
    SummarizationTask,
]

__all__ = [
    "EmailClassificationTask",
    "ReplyGenerationTask",
    "SummarizationTask",
    "ALL_TASKS",
]
