"""
grader.py  -- Unified deterministic grading module for all three tasks.

Task graders:
  EasyGrader    -- Spam vs non-spam binary classification
  MediumGrader  -- Category + priority classification
  HardGrader    -- Full triage (category + priority + action + reply)

All graders:
  - Are fully deterministic (no randomness)
  - Return a score strictly in [0.0, 1.0]
  - Support partial credit
"""

from __future__ import annotations

from typing import Any

from models import TaskResult


# ── Category Families (for partial credit) ───────────────────────────────────

RELATED_CATEGORIES: dict[str, set[str]] = {
    "financial":     {"financial", "transactional"},
    "transactional": {"transactional", "financial"},
    "professional":  {"professional", "educational"},
    "educational":   {"educational", "professional"},
    "service":       {"service", "system", "transactional"},
    "system":        {"system", "service"},
    "social":        {"social", "community", "personal"},
    "community":     {"community", "social"},
    "personal":      {"personal", "social"},
    "promotional":   {"promotional", "sales", "service"},
    "sales":         {"sales", "promotional"},
    "support":       {"support", "service"},
    "spam":          {"spam"},
    "travel":        {"travel", "transactional"},
    "healthcare":    {"healthcare"},
    "government":    {"government"},
}

PRIORITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def _is_related(pred: str, gt: str) -> bool:
    family = RELATED_CATEGORIES.get(gt, {gt})
    return pred in family


def _priority_dist(pred: str, gt: str) -> int:
    return abs(PRIORITY_ORDER.get(pred, -1) - PRIORITY_ORDER.get(gt, -1))


# ── Easy Grader ──────────────────────────────────────────────────────────────

class EasyGrader:
    """
    Grade binary spam classification.

    Scoring:
      1.0  -- Correct spam/non-spam prediction
      0.0  -- Incorrect prediction
    """

    def grade(self, predicted: dict[str, Any], expected: dict[str, Any]) -> TaskResult:
        """
        Args:
            predicted: dict with at least 'category'.
            expected:  dict with 'category' ground truth.

        Returns:
            TaskResult with score 0.0 or 1.0.
        """
        pred_cat = str(predicted.get("category", "")).lower().strip()
        gt_cat = str(expected.get("category", "")).lower().strip()

        gt_is_spam = gt_cat == "spam"
        pred_is_spam = pred_cat == "spam"

        correct = gt_is_spam == pred_is_spam
        score = 1.0 if correct else 0.0

        return TaskResult(
            score=score,
            max_score=1.0,
            breakdown={"spam_classification": score},
            feedback=f"{'Correct' if correct else 'Wrong'}: expected={'spam' if gt_is_spam else 'not-spam'}, got={'spam' if pred_is_spam else 'not-spam'}",
        )


# ── Medium Grader ────────────────────────────────────────────────────────────

class MediumGrader:
    """
    Grade category + priority classification.

    Scoring breakdown:
      Category correct  -> 0.6 (partial: related  -> 0.3)
      Priority correct  -> 0.4 (partial: off-by-1  -> 0.2)
    """

    def grade(self, predicted: dict[str, Any], expected: dict[str, Any]) -> TaskResult:
        pred_cat = str(predicted.get("category", "")).lower().strip()
        gt_cat = str(expected.get("category", "")).lower().strip()
        pred_pri = str(predicted.get("priority", "")).lower().strip()
        gt_pri = str(expected.get("priority", "")).lower().strip()

        breakdown: dict[str, float] = {}

        # Category (0.6)
        if pred_cat == gt_cat:
            cat_score = 0.6
        elif _is_related(pred_cat, gt_cat):
            cat_score = 0.3
        else:
            cat_score = 0.0
        breakdown["category"] = cat_score

        # Priority (0.4)
        if pred_pri == gt_pri:
            pri_score = 0.4
        elif _priority_dist(pred_pri, gt_pri) == 1:
            pri_score = 0.2
        else:
            pri_score = 0.0
        breakdown["priority"] = pri_score

        total = round(cat_score + pri_score, 4)
        total = min(1.0, max(0.0, total))

        return TaskResult(
            score=total,
            max_score=1.0,
            breakdown=breakdown,
            feedback=f"cat={pred_cat}({'OK' if cat_score>=0.6 else '~' if cat_score>0 else 'X'}) "
                      f"pri={pred_pri}({'OK' if pri_score>=0.4 else '~' if pri_score>0 else 'X'})",
        )


# ── Hard Grader ──────────────────────────────────────────────────────────────

class HardGrader:
    """
    Grade full email triage.

    Scoring breakdown:
      Category correct        -> +0.4 (partial: related  -> +0.2)
      Priority correct        -> +0.3 (partial: off-by-1  -> +0.15)
      Action type correct     -> +0.3 (partial: related  -> +0.15)

    Reply bonus (when action_type == 'reply'):
      Good reply text  -> up to +0.1 extra (capped at 1.0 total)
    """

    def grade(self, predicted: dict[str, Any], expected: dict[str, Any]) -> TaskResult:
        pred_cat = str(predicted.get("category", "")).lower().strip()
        gt_cat = str(expected.get("category", "")).lower().strip()
        pred_pri = str(predicted.get("priority", "")).lower().strip()
        gt_pri = str(expected.get("priority", "")).lower().strip()
        pred_act = str(predicted.get("action_type", "")).lower().strip()
        gt_act = str(expected.get("action_type", "")).lower().strip()
        pred_reply = str(predicted.get("reply_text", "") or "")
        gt_reply = str(expected.get("reply_text", "") or "")

        breakdown: dict[str, float] = {}

        # Category (0.4)
        if pred_cat == gt_cat:
            cat_s = 0.4
        elif _is_related(pred_cat, gt_cat):
            cat_s = 0.2
        else:
            cat_s = 0.0
        breakdown["category"] = cat_s

        # Priority (0.3)
        if pred_pri == gt_pri:
            pri_s = 0.3
        elif _priority_dist(pred_pri, gt_pri) == 1:
            pri_s = 0.15
        else:
            pri_s = 0.0
        breakdown["priority"] = pri_s

        # Action (0.3)
        if pred_act == gt_act:
            act_s = 0.3
        elif (pred_act, gt_act) in {("reply", "escalate"), ("escalate", "reply")}:
            act_s = 0.15
        else:
            act_s = 0.0
        breakdown["action_type"] = act_s

        # Reply bonus
        reply_s = 0.0
        if gt_act == "reply" and pred_act == "reply" and pred_reply and gt_reply:
            reply_s = _reply_score(pred_reply, gt_reply) * 0.1
        breakdown["reply_bonus"] = round(reply_s, 4)

        total = round(cat_s + pri_s + act_s + reply_s, 4)
        total = min(1.0, max(0.0, total))

        return TaskResult(
            score=total,
            max_score=1.0,
            breakdown=breakdown,
            feedback=f"cat={pred_cat} pri={pred_pri} act={pred_act}"
                      f" -> score={total:.3f}",
        )


def _reply_score(predicted: str, ground_truth: str) -> float:
    """Word overlap score between predicted and ground truth reply."""
    if not predicted or not ground_truth:
        return 0.0
    pred_words = set(predicted.lower().split())
    gt_words = set(ground_truth.lower().split())
    if not gt_words:
        return 0.0
    overlap = len(pred_words & gt_words) / len(gt_words)
    return min(1.0, overlap)
