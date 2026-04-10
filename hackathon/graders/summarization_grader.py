"""
graders/summarization_grader.py — Deterministic grader for email summarization.

Scoring breakdown:
  - Key fact coverage:       0.40
  - Must-contain keywords:   0.25
  - Length compliance:        0.15
  - Must-not-contain check:  0.10
  - Conciseness bonus:       0.10
"""

from graders.base import BaseGrader


class SummarizationGrader(BaseGrader):
    """Deterministic grader for email summarization task."""

    def grade(self, predicted: str, expected: dict) -> float:
        """
        Grade a generated summary.

        Args:
            predicted: The generated summary text.
            expected:  Dict with keys: must_contain, must_not_contain,
                       min_length, max_length, key_facts.

        Returns:
            Float score in [0.0, 1.0].
        """
        if not predicted or not expected:
            return 0.0

        predicted_lower = predicted.lower().strip()
        score = 0.0

        # 1. Key fact coverage (0.40)
        key_facts = expected.get("key_facts", [])
        if key_facts:
            fact_hits = sum(
                1 for fact in key_facts
                if fact.lower() in predicted_lower
            )
            fact_ratio = fact_hits / len(key_facts)
            score += 0.40 * fact_ratio
        else:
            score += 0.40

        # 2. Must-contain keywords (0.25)
        must_contain = expected.get("must_contain", [])
        if must_contain:
            kw_hits = sum(
                1 for kw in must_contain
                if kw.lower() in predicted_lower
            )
            kw_ratio = kw_hits / len(must_contain)
            score += 0.25 * kw_ratio
        else:
            score += 0.25

        # 3. Length compliance (0.15)
        min_len = expected.get("min_length", 20)
        max_len = expected.get("max_length", 200)
        pred_len = len(predicted)

        if min_len <= pred_len <= max_len:
            score += 0.15
        elif pred_len < min_len:
            score += 0.15 * max(0.0, pred_len / min_len) if min_len > 0 else 0.0
        else:
            # Over max but still somewhat reasonable
            over_ratio = max_len / pred_len if pred_len > 0 else 0
            score += 0.15 * max(0.0, over_ratio)

        # 4. Must-not-contain check (0.10)
        must_not = expected.get("must_not_contain", [])
        if must_not:
            violations = sum(
                1 for bad in must_not
                if bad.lower() in predicted_lower
            )
            if violations == 0:
                score += 0.10
            else:
                # Penalize per violation
                penalty = min(1.0, violations / len(must_not))
                score += 0.10 * (1.0 - penalty)
        else:
            score += 0.10

        # 5. Conciseness bonus (0.10)
        # Reward summaries that are short but information-dense
        word_count = len(predicted.split())
        if 10 <= word_count <= 60:
            score += 0.10
        elif 5 <= word_count < 10:
            score += 0.05
        elif 60 < word_count <= 100:
            score += 0.05
        # Very short (<5 words) or very long (>100 words): no bonus

        return round(min(1.0, max(0.0, score)), 4)
