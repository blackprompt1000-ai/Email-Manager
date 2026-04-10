"""
graders/classification_grader.py — Deterministic grader for email classification.

Scoring:
  1.0 — Exact category match
  0.5 — Predicted category is in the same "family" as expected
  0.0 — Wrong category
"""

from graders.base import BaseGrader

# Categories that are considered "related" for partial credit
CATEGORY_FAMILIES = {
    "FINANCIAL":     {"FINANCIAL", "TRANSACTIONAL"},
    "TRANSACTIONAL": {"TRANSACTIONAL", "FINANCIAL"},
    "PROFESSIONAL":  {"PROFESSIONAL", "EDUCATIONAL"},
    "EDUCATIONAL":   {"EDUCATIONAL", "PROFESSIONAL"},
    "SERVICE":       {"SERVICE", "SYSTEM", "TRANSACTIONAL"},
    "SYSTEM":        {"SYSTEM", "SERVICE"},
    "SOCIAL":        {"SOCIAL", "COMMUNITY", "PERSONAL"},
    "COMMUNITY":     {"COMMUNITY", "SOCIAL"},
    "PERSONAL":      {"PERSONAL", "SOCIAL"},
    "PROMOTIONAL":   {"PROMOTIONAL", "SERVICE"},
    "SPAM":          {"SPAM"},
    "TRAVEL":        {"TRAVEL", "TRANSACTIONAL"},
    "HEALTHCARE":    {"HEALTHCARE"},
    "GOVERNMENT":    {"GOVERNMENT"},
}


class ClassificationGrader(BaseGrader):
    """Deterministic grader for email classification task."""

    def grade(self, predicted: str, expected: str) -> float:
        """
        Grade classification output.

        Args:
            predicted: The predicted category string (e.g., "FINANCIAL").
            expected:  The ground-truth category string.

        Returns:
            1.0 for exact match, 0.5 for related category, 0.0 otherwise.
        """
        if not predicted or not expected:
            return 0.0

        predicted = predicted.strip().upper()
        expected = expected.strip().upper()

        # Exact match
        if predicted == expected:
            return 1.0

        # Partial credit for related categories
        family = CATEGORY_FAMILIES.get(expected, {expected})
        if predicted in family:
            return 0.5

        return 0.0
