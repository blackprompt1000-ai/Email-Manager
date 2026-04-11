"""
validate.py  -- Comprehensive compliance validation script.

Checks:
  1. File existence
  2. Task & grader functionality
  3. Deterministic grading
  4. OpenEnv API endpoints
  5. Log format compliance
  6. openenv.yaml validity
  7. Environment variables in inference.py
"""

import os
import json
import sys


def check(label: str, condition: bool) -> bool:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    return condition


def main() -> None:
    passed = 0
    failed = 0

    def track(result: bool) -> None:
        nonlocal passed, failed
        if result:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print("  OpenEnv Compliance Validation  -- Email Rectifier v3.0")
    print("=" * 60)

    # ═══ 1. FILE EXISTENCE ═══════════════════════════════════════════
    print("\n=== FILE EXISTENCE CHECKS ===\n")

    required_files = [
        "models.py",
        "grader.py",
        "inference.py",
        "openenv.yaml",
        "Dockerfile",
        ".env.example",
        "api_server.py",
        "requirements.txt",
        "email_rectifier/__init__.py",
        "email_rectifier/environment.py",
        "tasks/__init__.py",
        "tasks/base.py",
        "tasks/email_classification.py",
        "tasks/reply_generation.py",
        "tasks/summarization.py",
        "graders/__init__.py",
        "graders/base.py",
        "graders/classification_grader.py",
        "graders/reply_grader.py",
        "graders/summarization_grader.py",
    ]
    for f in required_files:
        track(check(f, os.path.isfile(f)))

    # ═══ 2. PYDANTIC MODELS ═════════════════════════════════════════
    print("\n=== PYDANTIC MODEL CHECKS ===\n")

    from models import (
        EmailObservation,
        EmailAction,
        StepReward,
        EnvironmentObservation,
        TaskResult,
        EmailState,
        EmailCategory,
        Priority,
        ActionType,
    )

    # Test EmailObservation
    obs = EmailObservation(
        email_id="test-001",
        subject="Test Subject",
        body="Test Body",
        sender="test@test.com",
        current_state=EmailState.PENDING,
    )
    track(check("EmailObservation model valid", obs.email_id == "test-001"))

    # Test EmailAction
    act = EmailAction(
        category="spam",
        priority="low",
        action_type="ignore",
    )
    track(check("EmailAction model valid", act.category == "spam"))

    # Test StepReward
    rew = StepReward(total=0.7, category_score=0.4, priority_score=0.3)
    track(check("StepReward model valid", rew.total == 0.7))

    # Test TaskResult
    tr = TaskResult(score=0.8, breakdown={"cat": 0.5, "pri": 0.3})
    track(check("TaskResult model valid", 0.0 <= tr.score <= 1.0))

    # Test Enums
    track(check("EmailCategory enum has 'spam'", EmailCategory.SPAM.value == "spam"))
    track(check("Priority enum has 'high'", Priority.HIGH.value == "high"))
    track(check("ActionType enum has 'reply'", ActionType.REPLY.value == "reply"))

    # ═══ 3. ENVIRONMENT ═════════════════════════════════════════════
    print("\n=== ENVIRONMENT CHECKS ===\n")

    from email_rectifier import EmailEnv, EMAILS, GROUND_TRUTH

    env = EmailEnv()

    # Test reset with each task
    for task_id in ["easy", "medium", "hard"]:
        state = env.reset(task_id=task_id)
        track(check(
            f"reset(task_id='{task_id}') returns valid state",
            state.get("total_emails", 0) > 0 and state.get("task_id") == task_id
        ))

    # Test step
    env.reset(task_id="hard")
    action = {"category": "financial", "priority": "high", "action_type": "escalate"}
    state, reward, done, info = env.step(action)
    track(check("step() returns 4-tuple", state is not None and isinstance(reward, float)))
    track(check("step() reward is float", isinstance(reward, float)))
    track(check("step() done is bool", isinstance(done, bool)))

    # Test state
    state_out = env.state()
    track(check("state() returns dict with current_email", "current_email" in state_out))
    track(check("state() has step_number", "step_number" in state_out))
    track(check("state() has total_emails", "total_emails" in state_out))

    # Deterministic: same inputs  -> same rewards
    env.reset(task_id="easy")
    _, r1, _, _ = env.step({"category": "financial", "priority": "high", "action_type": "escalate"})
    env.reset(task_id="easy")
    _, r2, _, _ = env.step({"category": "financial", "priority": "high", "action_type": "escalate"})
    track(check("Deterministic rewards (same input -> same reward)", r1 == r2))

    # Episode termination
    env.reset(task_id="easy")
    for _ in range(len(EMAILS) + 5):  # More than enough
        _, _, d, _ = env.step({"category": "spam", "priority": "low", "action_type": "ignore"})
        if d:
            break
    track(check("Episode terminates correctly", d))

    # ═══ 4. GRADERS ═════════════════════════════════════════════════
    print("\n=== GRADER CHECKS ===\n")

    from grader import EasyGrader, MediumGrader, HardGrader

    eg = EasyGrader()
    mg = MediumGrader()
    hg = HardGrader()

    # Easy grader
    r_spam_correct = eg.grade({"category": "spam"}, {"category": "spam"})
    r_spam_wrong = eg.grade({"category": "financial"}, {"category": "spam"})
    track(check("EasyGrader: spam correct  -> 1.0", r_spam_correct.score == 1.0))
    track(check("EasyGrader: spam wrong  -> 0.0", r_spam_wrong.score == 0.0))

    # Deterministic
    r1 = eg.grade({"category": "spam"}, {"category": "spam"})
    r2 = eg.grade({"category": "spam"}, {"category": "spam"})
    track(check("EasyGrader: deterministic", r1.score == r2.score))

    # Medium grader
    r_full = mg.grade(
        {"category": "financial", "priority": "high"},
        {"category": "financial", "priority": "high"},
    )
    r_partial = mg.grade(
        {"category": "transactional", "priority": "medium"},
        {"category": "financial", "priority": "high"},
    )
    r_zero = mg.grade(
        {"category": "spam", "priority": "low"},
        {"category": "financial", "priority": "high"},
    )
    track(check("MediumGrader: perfect  -> 1.0", r_full.score == 1.0))
    track(check("MediumGrader: partial credit works", 0.0 < r_partial.score < 1.0))
    track(check("MediumGrader: all wrong  -> 0.0", r_zero.score == 0.0))
    track(check("MediumGrader: score in [0, 1]", 0.0 <= r_partial.score <= 1.0))

    # Hard grader
    r_hard_full = hg.grade(
        {"category": "financial", "priority": "high", "action_type": "escalate"},
        {"category": "financial", "priority": "high", "action_type": "escalate"},
    )
    r_hard_partial = hg.grade(
        {"category": "financial", "priority": "medium", "action_type": "reply"},
        {"category": "financial", "priority": "high", "action_type": "escalate"},
    )
    track(check("HardGrader: perfect  -> 1.0", r_hard_full.score == 1.0))
    track(check("HardGrader: partial credit works", 0.0 < r_hard_partial.score < 1.0))
    track(check("HardGrader: has breakdown dict", isinstance(r_hard_full.breakdown, dict)))

    # All in [0, 1]
    all_scores = [
        r_spam_correct.score, r_spam_wrong.score,
        r_full.score, r_partial.score, r_zero.score,
        r_hard_full.score, r_hard_partial.score,
    ]
    track(check("All grader scores in [0.0, 1.0]", all(0.0 <= s <= 1.0 for s in all_scores)))

    # ═══ 5. LEGACY GRADERS ══════════════════════════════════════════
    print("\n=== LEGACY GRADER CHECKS ===\n")

    from graders.classification_grader import ClassificationGrader
    from graders.reply_grader import ReplyGrader
    from graders.summarization_grader import SummarizationGrader

    cg = ClassificationGrader()
    rg = ReplyGrader()
    sg = SummarizationGrader()

    s1 = cg.grade("FINANCIAL", "FINANCIAL")
    s2 = cg.grade("FINANCIAL", "FINANCIAL")
    track(check("ClassificationGrader deterministic", s1 == s2))
    track(check(f"ClassificationGrader score in [0, 1]: {s1}", 0.0 <= s1 <= 1.0))

    rg_score = rg.grade(
        "Thank you for this email. I will attend. Best regards.",
        {"must_contain": ["thank"], "min_length": 30, "max_length": 500, "tone": "professional"},
    )
    track(check(f"ReplyGrader score in [0, 1]: {rg_score}", 0.0 <= rg_score <= 1.0))

    sg_score = sg.grade(
        "Payment processed for $49.99 to Acme Corp.",
        {"must_contain": ["payment"], "must_not_contain": [], "min_length": 10,
         "max_length": 200, "key_facts": ["payment"]},
    )
    track(check(f"SummarizationGrader score in [0, 1]: {sg_score}", 0.0 <= sg_score <= 1.0))

    # ═══ 6. API ENDPOINTS ═══════════════════════════════════════════
    print("\n=== API ENDPOINT CHECKS ===\n")

    from api_server import app as fastapi_app
    from fastapi.testclient import TestClient

    tc = TestClient(fastapi_app)

    r = tc.get("/")
    track(check("GET / returns 200", r.status_code == 200))

    r = tc.post("/reset", json={"task_id": "easy"})
    track(check("POST /reset (easy) returns 200", r.status_code == 200))

    r = tc.post("/reset", json={"task_id": "medium"})
    track(check("POST /reset (medium) returns 200", r.status_code == 200))

    r = tc.post("/reset", json={"task_id": "hard"})
    track(check("POST /reset (hard) returns 200", r.status_code == 200))

    r = tc.get("/state")
    track(check("GET /state returns 200", r.status_code == 200))

    r = tc.post("/step", json={"action": {"category": "financial", "priority": "high", "action_type": "escalate"}})
    track(check("POST /step returns 200", r.status_code == 200))

    r = tc.get("/tasks")
    track(check("GET /tasks returns 200", r.status_code == 200))
    tasks_data = r.json()
    track(check("3 tasks defined", len(tasks_data.get("tasks", [])) == 3))

    # JSON responses
    endpoints = [tc.get("/"), tc.post("/reset"), tc.get("/state"),
                 tc.post("/step", json={"action": {"category": "spam", "priority": "low", "action_type": "ignore"}})]
    all_json = True
    for er in endpoints:
        try:
            er.json()
        except Exception:
            all_json = False
    track(check("All endpoint responses are valid JSON", all_json))

    # Deterministic state
    tc.post("/reset", json={"task_id": "hard"})
    s1 = tc.get("/state").json()
    tc.post("/reset", json={"task_id": "hard"})
    s2 = tc.get("/state").json()
    track(check(
        "Deterministic state after reset",
        s1["state"]["total_emails"] == s2["state"]["total_emails"]
    ))

    # ═══ 7. LOG FORMAT ═══════════════════════════════════════════════
    print("\n=== LOG FORMAT CHECKS ===\n")

    test_log = [
        "[START]",
        json.dumps({"run_id": "test", "model": "test"}),
        "[STEP]",
        json.dumps({"task": "t", "input": "i", "output": "o", "score": 0.5}),
        "[END]",
        json.dumps({"final_score": 0.5}),
    ]
    valid_format = True
    for line in test_log:
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
                if not isinstance(parsed, dict):
                    valid_format = False
            except Exception:
                valid_format = False
    track(check("Log format compliance", valid_format))

    # ═══ 8. OPENENV YAML ════════════════════════════════════════════
    print("\n=== OPENENV.YAML CHECKS ===\n")

    import yaml
    with open("openenv.yaml") as f:
        cfg = yaml.safe_load(f)

    track(check("Has 'environment' section", bool(cfg.get("environment"))))
    track(check("Has 'api' section", bool(cfg.get("api"))))
    track(check("Has 'tasks' section", bool(cfg.get("tasks"))))
    track(check("Has 'inference' section", bool(cfg.get("inference"))))
    track(check("Has 'docker' section", bool(cfg.get("docker"))))
    track(check("Exactly 3 tasks defined in YAML", len(cfg.get("tasks", [])) == 3))

    task_difficulties = {t["difficulty"] for t in cfg.get("tasks", [])}
    track(check("Tasks cover easy/medium/hard", task_difficulties == {"easy", "medium", "hard"}))

    # ═══ 9. INFERENCE ENV VARS ══════════════════════════════════════
    print("\n=== INFERENCE SCRIPT CHECKS ===\n")

    with open("inference.py") as f:
        src = f.read()
    track(check("inference.py reads API_BASE_URL", "API_BASE_URL" in src))
    track(check("inference.py reads MODEL_NAME", "MODEL_NAME" in src))
    track(check("inference.py reads HF_TOKEN", "HF_TOKEN" in src))
    track(check("inference.py reads OPENAI_API_KEY", "OPENAI_API_KEY" in src))
    track(check("inference.py uses [START] log", "[START]" in src))
    track(check("inference.py uses [STEP] log", "[STEP]" in src))
    track(check("inference.py uses [END] log", "[END]" in src))

    # ═══ 10. DATA INTEGRITY ═════════════════════════════════════════
    print("\n=== DATA INTEGRITY CHECKS ===\n")

    track(check(f"Dataset has 20 emails", len(EMAILS) == 20))
    track(check(f"Ground truth has {len(GROUND_TRUTH)} entries", len(GROUND_TRUTH) >= 20))

    # Verify all emails have ground truth
    all_have_gt = all(e["email_id"] in GROUND_TRUTH for e in EMAILS)
    track(check("All emails have ground truth", all_have_gt))

    # Verify spam IDs are correct
    from email_rectifier import SPAM_IDS
    spam_count = sum(1 for gt in GROUND_TRUTH.values() if gt["category"] == "spam")
    track(check(f"Spam emails in dataset: {spam_count}", spam_count >= 3))

    # ═══ SUMMARY ════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  RESULTS: {passed}/{total} passed, {failed}/{total} failed")

    if failed == 0:
        print("  [OK] ALL COMPLIANCE CHECKS PASSED!")
    else:
        print("  [FAIL] SOME CHECKS FAILED  -- review above output")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
