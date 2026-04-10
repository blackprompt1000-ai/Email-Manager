"""
graders/reply_grader.py — Deterministic grader for email reply generation.

Scoring breakdown (each component weighted equally, summed to 1.0):
  - Length compliance:           0.20
  - Keyword coverage:           0.40
  - Tone appropriateness:       0.20
  - Structure quality:          0.20
"""

from graders.base import BaseGrader


# Keywords associated with different tones
TONE_KEYWORDS = {
    "professional": [
        "thank", "regards", "sincerely", "please", "appreciate",
        "confirmed", "acknowledge", "look forward", "noted",
    ],
    "friendly": [
        "hey", "hi", "great", "awesome", "sounds good", "love",
        "excited", "sure", "definitely", "cheers", "thanks",
    ],
    "respectful": [
        "thank", "professor", "sir", "ma'am", "appreciate",
        "grateful", "sincerely", "respectfully", "please",
    ],
    "casual": [
        "thanks", "sounds", "cool", "great", "sure", "interested",
        "looking forward", "awesome", "cheers",
    ],
}


class ReplyGrader(BaseGrader):
    """Deterministic grader for email reply generation task."""

    def grade(self, predicted: str, expected: dict) -> float:
        """
        Grade a generated reply.

        Args:
            predicted: The generated reply text.
            expected:  Dict with keys: must_contain, min_length, max_length, tone.

        Returns:
            Float score in [0.0, 1.0].
        """
        if not predicted or not expected:
            return 0.0

        predicted_lower = predicted.lower()
        score = 0.0

        # 1. Length compliance (0.20)
        min_len = expected.get("min_length", 30)
        max_len = expected.get("max_length", 500)
        pred_len = len(predicted)

        if min_len <= pred_len <= max_len:
            score += 0.20
        elif pred_len < min_len:
            # Partial: ratio of actual to minimum
            score += 0.20 * max(0.0, pred_len / min_len)
        else:
            # Over max: penalize proportionally
            over_ratio = max_len / pred_len if pred_len > 0 else 0
            score += 0.20 * max(0.0, over_ratio)

        # 2. Keyword coverage (0.40)
        must_contain = expected.get("must_contain", [])
        if must_contain:
            hits = sum(1 for kw in must_contain if kw.lower() in predicted_lower)
            keyword_ratio = hits / len(must_contain)
            score += 0.40 * keyword_ratio
        else:
            score += 0.40  # No keywords required = full credit

        # 3. Tone appropriateness (0.20)
        tone = expected.get("tone", "professional")
        tone_words = TONE_KEYWORDS.get(tone, TONE_KEYWORDS["professional"])
        tone_hits = sum(1 for tw in tone_words if tw.lower() in predicted_lower)
        # At least 2 tone words = full credit, 1 = half, 0 = zero
        if tone_hits >= 2:
            score += 0.20
        elif tone_hits == 1:
            score += 0.10
        # else: 0

        # 4. Structure quality (0.20)
        structure_score = 0.0

        # Has greeting (Hi/Hello/Dear/Hey)
        greetings = ["hi", "hello", "dear", "hey", "good morning", "good afternoon"]
        if any(predicted_lower.startswith(g) or f"\n{g}" in predicted_lower for g in greetings):
            structure_score += 0.05

        # Has a closing (regards/thanks/best/sincerely/cheers)
        closings = ["regards", "thanks", "thank you", "best", "sincerely", "cheers", "warm"]
        if any(c in predicted_lower for c in closings):
            structure_score += 0.05

        # Has multiple sentences (more than one period/exclamation/question mark)
        sentence_ends = sum(1 for c in predicted if c in ".!?")
        if sentence_ends >= 2:
            structure_score += 0.05

        # Not just one word or very terse
        word_count = len(predicted.split())
        if word_count >= 10:
            structure_score += 0.05

        score += structure_score

        return round(min(1.0, max(0.0, score)), 4)
