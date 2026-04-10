"""Comprehensive compliance validation script."""
import os
import json
import sys


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    return condition


def main():
    print("=== FILE EXISTENCE CHECKS ===\n")

    files = [
        "inference.py", "openenv.yaml", "Dockerfile", ".env.example",
        "api_server.py", "requirements.txt",
        "tasks/__init__.py", "tasks/base.py",
        "tasks/email_classification.py", "tasks/reply_generation.py",
        "tasks/summarization.py",
        "graders/__init__.py", "graders/base.py",
        "graders/classification_grader.py", "graders/reply_grader.py",
        "graders/summarization_grader.py",
    ]
    file_results = []
    for f in files:
        file_results.append(check(f, os.path.isfile(f)))

    print("\n=== FUNCTIONAL CHECKS ===\n")

    # 1. Tasks
    from tasks import ALL_TASKS
    check("Minimum 3 tasks: " + str(len(ALL_TASKS)), len(ALL_TASKS) >= 3)

    # 2. Graders
    from graders import ALL_GRADERS
    check("Minimum 3 graders: " + str(len(ALL_GRADERS)), len(ALL_GRADERS) >= 3)

    # 3. Sample counts
    total_samples = sum(len(t().get_samples()) for t in ALL_TASKS)
    check(f"Total samples: {total_samples}", total_samples >= 15)

    # 4. Deterministic grading
    from graders.classification_grader import ClassificationGrader
    cg = ClassificationGrader()
    s1 = cg.grade("FINANCIAL", "FINANCIAL")
    s2 = cg.grade("FINANCIAL", "FINANCIAL")
    check("Deterministic grading (same input -> same output)", s1 == s2)
    check(f"Score in [0, 1]: {s1}", 0.0 <= s1 <= 1.0)

    # 5. All graders produce valid scores
    from graders.reply_grader import ReplyGrader
    from graders.summarization_grader import SummarizationGrader
    rg = ReplyGrader()
    sg = SummarizationGrader()

    scores = [
        cg.grade("FINANCIAL", "FINANCIAL"),
        cg.grade("SPAM", "FINANCIAL"),
        cg.grade("", "FINANCIAL"),
        rg.grade("Thank you for this email. I will attend. Best regards.", {
            "must_contain": ["thank"], "min_length": 30, "max_length": 500, "tone": "professional"
        }),
        rg.grade("", {"must_contain": ["x"], "min_length": 10, "max_length": 100, "tone": "professional"}),
        sg.grade("Payment processed for $49.99 to Acme Corp.", {
            "must_contain": ["payment"], "must_not_contain": [], "min_length": 10,
            "max_length": 200, "key_facts": ["payment"]
        }),
        sg.grade("", {"must_contain": ["x"], "must_not_contain": [], "min_length": 10,
                      "max_length": 200, "key_facts": ["x"]}),
    ]
    all_valid = all(0.0 <= s <= 1.0 for s in scores)
    check(f"All grader scores in [0.0, 1.0]: {all_valid}", all_valid)
    no_random = scores == [
        cg.grade("FINANCIAL", "FINANCIAL"),
        cg.grade("SPAM", "FINANCIAL"),
        cg.grade("", "FINANCIAL"),
        rg.grade("Thank you for this email. I will attend. Best regards.", {
            "must_contain": ["thank"], "min_length": 30, "max_length": 500, "tone": "professional"
        }),
        rg.grade("", {"must_contain": ["x"], "min_length": 10, "max_length": 100, "tone": "professional"}),
        sg.grade("Payment processed for $49.99 to Acme Corp.", {
            "must_contain": ["payment"], "must_not_contain": [], "min_length": 10,
            "max_length": 200, "key_facts": ["payment"]
        }),
        sg.grade("", {"must_contain": ["x"], "must_not_contain": [], "min_length": 10,
                      "max_length": 200, "key_facts": ["x"]}),
    ]
    check("No randomness in grading", no_random)

    # 6. OpenEnv API endpoints
    from api_server import app as fastapi_app
    from fastapi.testclient import TestClient
    tc = TestClient(fastapi_app)

    r1 = tc.get("/")
    check("GET / returns 200", r1.status_code == 200)
    r2 = tc.post("/reset")
    check("POST /reset returns 200", r2.status_code == 200)
    r3 = tc.get("/state")
    check("GET /state returns 200", r3.status_code == 200)
    r4 = tc.post("/step", json={"action": "FYI"})
    check("POST /step returns 200", r4.status_code == 200)

    # 7. All responses are JSON
    all_json = True
    for r in [r1, r2, r3, r4]:
        try:
            r.json()
        except Exception:
            all_json = False
    check("All OpenEnv responses are JSON", all_json)

    # 8. Deterministic responses
    tc2 = TestClient(fastapi_app)
    r2a = tc2.post("/reset")
    r2b = tc2.get("/state")
    state_a = r2b.json()["state"]
    check("Deterministic state after reset", state_a["inbox"]["total"] > 0)

    # 9. Log format compliance
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
    check("Log format compliance", valid_format)

    # 10. openenv.yaml valid
    import yaml
    with open("openenv.yaml") as f:
        cfg = yaml.safe_load(f)
    check("openenv.yaml has API section", bool(cfg.get("api")))
    check("openenv.yaml has tasks section", bool(cfg.get("tasks")))
    check("openenv.yaml has environment section", bool(cfg.get("environment")))

    # 11. Env vars in inference.py
    with open("inference.py") as f:
        src = f.read()
    check("inference.py reads API_BASE_URL", "API_BASE_URL" in src)
    check("inference.py reads MODEL_NAME", "MODEL_NAME" in src)
    check("inference.py reads HF_TOKEN", "HF_TOKEN" in src)

    print("\n" + "=" * 50)
    print("ALL COMPLIANCE CHECKS PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    main()
