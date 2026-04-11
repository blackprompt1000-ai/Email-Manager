"""
inference.py  -- End-to-end evaluation inference script.

Runs all 3 tasks (easy, medium, hard) against an OpenAI-compatible model,
grades outputs with deterministic graders, and prints strict structured logs.

Environment Variables:
    API_BASE_URL   -- Base URL for the OpenAI-compatible API
    MODEL_NAME     -- Model identifier to use
    HF_TOKEN       -- Hugging Face token (used as API key fallback)
    OPENAI_API_KEY  -- OpenAI API key (alternative to HF_TOKEN)

Usage:
    python inference.py

Output Format:
    [START]
    {"run_id": "...", "model": "..."}
    [STEP]
    {"task": "...", "input": "...", "output": "...", "score": 0.0}
    ...
    [END]
    {"final_score": 0.0, "task_scores": {"easy": 0.0, "medium": 0.0, "hard": 0.0}}
"""

import json
import os
import sys
import uuid
import time
from typing import Any

# ── Environment Variables ────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api-inference.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.3")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


def get_client():
    """Create an OpenAI-compatible client."""
    try:
        from openai import OpenAI
    except ImportError:
        print("[ERROR] openai package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    api_key = OPENAI_API_KEY or HF_TOKEN or "no-key"
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=api_key,
    )
    return client


def call_model(client: Any, prompt: str, max_retries: int = 3) -> str:
    """
    Call the LLM via the OpenAI-compatible API.
    Returns the model's text response.
    """
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful AI email assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=512,
                temperature=0.0,  # Deterministic output
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue
            return f'{{"error": "{str(e)[:100]}"}}'


def parse_json_response(raw: str) -> dict:
    """Parse a JSON response from the model, handling common issues."""
    raw = raw.strip()
    # Try to find JSON in the response
    if raw.startswith("```"):
        # Remove code blocks
        lines = raw.split("\n")
        json_lines = [l for l in lines if not l.startswith("```")]
        raw = "\n".join(json_lines).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        import re
        match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {}


# ── Task-Specific Prompts ────────────────────────────────────────────────────

def build_easy_prompt(email: dict) -> str:
    """Build prompt for easy task: spam vs non-spam."""
    return (
        f"Classify the following email as either 'spam' or 'not-spam'.\n\n"
        f"Sender: {email['sender']}\n"
        f"Subject: {email['subject']}\n"
        f"Body: {email['body']}\n\n"
        f"Respond with ONLY a JSON object: {{\"category\": \"spam\"}} or {{\"category\": \"not-spam\"}}\n"
        f"Do not include any other text."
    )


def build_medium_prompt(email: dict) -> str:
    """Build prompt for medium task: category + priority."""
    categories = "spam, support, sales, personal, financial, professional, educational, travel, healthcare, government, transactional, promotional, social, system, community, service"
    return (
        f"Classify the following email into a category and priority level.\n\n"
        f"Sender: {email['sender']}\n"
        f"Subject: {email['subject']}\n"
        f"Body: {email['body']}\n\n"
        f"Categories: {categories}\n"
        f"Priority levels: low, medium, high\n\n"
        f"Respond with ONLY a JSON object: {{\"category\": \"<category>\", \"priority\": \"<priority>\"}}\n"
        f"Do not include any other text."
    )


def build_hard_prompt(email: dict) -> str:
    """Build prompt for hard task: full triage."""
    categories = "spam, support, sales, personal, financial, professional, educational, travel, healthcare, government, transactional, promotional, social, system, community, service"
    return (
        f"Perform full email triage on the following email.\n\n"
        f"Sender: {email['sender']}\n"
        f"Subject: {email['subject']}\n"
        f"Body: {email['body']}\n\n"
        f"Categories: {categories}\n"
        f"Priority levels: low, medium, high\n"
        f"Action types: ignore, reply, escalate\n\n"
        f"Instructions:\n"
        f"1. Classify the email into a category\n"
        f"2. Assign a priority level\n"
        f"3. Choose an action type\n"
        f"4. If action is 'reply', write a brief reply\n\n"
        f"Respond with ONLY a JSON object:\n"
        f"{{\"category\": \"<category>\", \"priority\": \"<priority>\", "
        f"\"action_type\": \"<action>\", \"reply_text\": \"<reply or null>\"}}\n"
        f"Do not include any other text."
    )


# ── Main Inference ───────────────────────────────────────────────────────────

def run_inference() -> float:
    """Run all tasks, grade outputs, and print structured logs."""
    from email_rectifier import EMAILS, GROUND_TRUTH, GROUND_TRUTH_REPLIES
    from grader import EasyGrader, MediumGrader, HardGrader

    run_id = str(uuid.uuid4())
    client = get_client()

    # Task configurations
    tasks = [
        {
            "task_id": "easy",
            "name": "spam_detection",
            "prompt_fn": build_easy_prompt,
            "grader": EasyGrader(),
        },
        {
            "task_id": "medium",
            "name": "category_priority",
            "prompt_fn": build_medium_prompt,
            "grader": MediumGrader(),
        },
        {
            "task_id": "hard",
            "name": "full_triage",
            "prompt_fn": build_hard_prompt,
            "grader": HardGrader(),
        },
    ]

    # ── [START] ──────────────────────────────────────────────────────────────
    print("[START]")
    print(json.dumps({"run_id": run_id, "model": MODEL_NAME}))

    all_scores: list[float] = []
    task_scores: dict[str, list[float]] = {}

    # ── Process each task ────────────────────────────────────────────────────
    for task_config in tasks:
        task_id = task_config["task_id"]
        task_name = task_config["name"]
        prompt_fn = task_config["prompt_fn"]
        grader = task_config["grader"]
        task_scores[task_id] = []

        for email in EMAILS:
            email_id = email["email_id"]
            gt = GROUND_TRUTH.get(email_id, {})
            if not gt:
                continue

            # Build the expected dict for grading
            expected = dict(gt)
            # Add reply_text for hard task grading
            if task_id == "hard" and email_id in GROUND_TRUTH_REPLIES:
                expected["reply_text"] = GROUND_TRUTH_REPLIES[email_id]

            # Build prompt and call model
            prompt = prompt_fn(email)
            raw_output = call_model(client, prompt)
            parsed = parse_json_response(raw_output)

            # For easy task, normalize non-spam categories
            if task_id == "easy":
                cat = parsed.get("category", "").lower().strip()
                if cat not in ("spam", "not-spam"):
                    # If model returned a specific category, treat non-spam as not-spam
                    parsed["category"] = "spam" if "spam" in cat else "not-spam"
                # Normalize expected for easy grading
                expected_easy = {"category": expected.get("category", "")}
                result = grader.grade(parsed, expected_easy)
            elif task_id == "medium":
                result = grader.grade(parsed, expected)
            else:
                result = grader.grade(parsed, expected)

            score = round(min(1.0, max(0.0, float(result.score))), 4)
            all_scores.append(score)
            task_scores[task_id].append(score)

            # Build log strings
            input_str = json.dumps({
                "email_id": email_id,
                "sender": email["sender"],
                "subject": email["subject"],
            }, ensure_ascii=False)
            output_str = json.dumps(parsed, ensure_ascii=False)

            # ── [STEP] ──────────────────────────────────────────────────
            print("[STEP]")
            print(json.dumps({
                "task": task_name,
                "input": input_str,
                "output": output_str,
                "score": score,
            }, ensure_ascii=False))

    # ── [END] ────────────────────────────────────────────────────────────────
    final_score = round(sum(all_scores) / len(all_scores), 4) if all_scores else 0.0

    per_task = {}
    for tid, scores in task_scores.items():
        per_task[tid] = round(sum(scores) / len(scores), 4) if scores else 0.0

    print("[END]")
    print(json.dumps({
        "final_score": final_score,
        "task_scores": per_task,
        "total_steps": len(all_scores),
    }))

    return final_score


if __name__ == "__main__":
    score = run_inference()
    sys.exit(0)
