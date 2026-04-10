"""
inference.py — End-to-end evaluation inference script.

Runs all evaluation tasks against an OpenAI-compatible model,
grades the outputs with deterministic graders, and prints
strict structured logs.

Environment Variables:
    API_BASE_URL  — Base URL for the OpenAI-compatible API
    MODEL_NAME    — Model identifier to use
    HF_TOKEN      — Hugging Face token (used as API key fallback)

Usage:
    python inference.py

Output Format:
    [START]
    {"run_id": "...", "model": "..."}
    [STEP]
    {"task": "...", "input": "...", "output": "...", "score": 0.0}
    ...
    [END]
    {"final_score": 0.0}
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


def get_client():
    """Create an OpenAI-compatible client."""
    try:
        from openai import OpenAI
    except ImportError:
        print("[ERROR] openai package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    api_key = HF_TOKEN or "no-key"
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=api_key,
    )
    return client


def call_model(client, prompt: str, max_retries: int = 3) -> str:
    """
    Call the LLM via the OpenAI-compatible API.
    Returns the model's text response.
    """
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful AI email assistant."},
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
            # On final retry failure, return error marker
            return f"[ERROR: {str(e)[:100]}]"


def run_inference():
    """Run all tasks, grade outputs, and print structured logs."""
    # ── Import tasks and graders ─────────────────────────────────────────────
    from tasks.email_classification import EmailClassificationTask
    from tasks.reply_generation import ReplyGenerationTask
    from tasks.summarization import SummarizationTask
    from graders.classification_grader import ClassificationGrader
    from graders.reply_grader import ReplyGrader
    from graders.summarization_grader import SummarizationGrader

    # ── Setup ────────────────────────────────────────────────────────────────
    run_id = str(uuid.uuid4())
    client = get_client()

    tasks_and_graders = [
        (EmailClassificationTask(), ClassificationGrader()),
        (ReplyGenerationTask(), ReplyGrader()),
        (SummarizationTask(), SummarizationGrader()),
    ]

    # ── [START] ──────────────────────────────────────────────────────────────
    print("[START]")
    print(json.dumps({"run_id": run_id, "model": MODEL_NAME}))

    all_scores: list[float] = []

    # ── Process each task ────────────────────────────────────────────────────
    for task, grader in tasks_and_graders:
        samples = task.get_samples()

        for sample in samples:
            # Build prompt
            prompt = task.build_prompt(sample)

            # Call model
            raw_output = call_model(client, prompt)

            # Parse response
            parsed_output = task.parse_response(raw_output)

            # Grade
            score = grader.grade(parsed_output, sample["expected"])

            # Ensure score is in [0.0, 1.0]
            score = round(min(1.0, max(0.0, float(score))), 4)
            all_scores.append(score)

            # Build input string for log
            input_data = sample["input"]
            if isinstance(input_data, dict):
                input_str = json.dumps(input_data, ensure_ascii=False)
            else:
                input_str = str(input_data)

            # Build output string for log
            if isinstance(parsed_output, dict):
                output_str = json.dumps(parsed_output, ensure_ascii=False)
            else:
                output_str = str(parsed_output)

            # ── [STEP] ──────────────────────────────────────────────────────
            print("[STEP]")
            print(json.dumps({
                "task": task.task_name,
                "input": input_str,
                "output": output_str,
                "score": score,
            }, ensure_ascii=False))

    # ── [END] ────────────────────────────────────────────────────────────────
    final_score = round(sum(all_scores) / len(all_scores), 4) if all_scores else 0.0

    print("[END]")
    print(json.dumps({"final_score": final_score}))

    return final_score


if __name__ == "__main__":
    score = run_inference()
    sys.exit(0)
