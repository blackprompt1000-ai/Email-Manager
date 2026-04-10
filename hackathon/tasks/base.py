"""
tasks/base.py — Abstract base class for all evaluation tasks.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTask(ABC):
    """Base class for evaluation tasks."""

    @property
    @abstractmethod
    def task_name(self) -> str:
        """Unique name of this task."""
        ...

    @property
    @abstractmethod
    def task_description(self) -> str:
        """Human-readable description."""
        ...

    @abstractmethod
    def get_samples(self) -> list[dict]:
        """
        Return a list of deterministic test samples.
        Each sample must have at minimum:
          - "input": the raw input data (str or dict)
          - "expected": the ground-truth expected output
        """
        ...

    @abstractmethod
    def build_prompt(self, sample: dict) -> str:
        """
        Build the LLM prompt for a single sample.
        Returns a plain string to be sent as the user message.
        """
        ...

    @abstractmethod
    def parse_response(self, raw_response: str) -> Any:
        """
        Parse the raw LLM response string into a structured result
        suitable for grading.
        """
        ...
