"""
graders/base.py — Abstract base class for all graders.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseGrader(ABC):
    """Base class for deterministic graders."""

    @abstractmethod
    def grade(self, predicted: Any, expected: Any) -> float:
        """
        Grade the predicted output against the expected ground truth.

        Args:
            predicted: The parsed model output.
            expected:  The ground-truth expected value from the sample.

        Returns:
            A float score strictly in [0.0, 1.0].
        """
        ...
