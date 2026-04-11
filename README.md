---
title: AI Smart Inbox Decision Assistant
emoji: 📧
colorFrom: blue
colorTo: green
sdk: docker
app_file: app.py
pinned: false
---

# Email Rectifier — OpenEnv RL Environment

> **An OpenEnv-compatible reinforcement learning environment for AI-driven email classification, prioritization, and decision-making.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-purple.svg)](https://docs.pydantic.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![HF Spaces](https://img.shields.io/badge/🤗-Spaces%20Ready-yellow.svg)](https://huggingface.co/spaces)

---

## 📋 Project Overview

Email Rectifier is a **reinforcement learning environment** where an AI agent learns to triage emails. The agent receives emails one at a time and must:

1. **Classify** the email into a category (spam, financial, professional, etc.)
2. **Prioritize** each email (low, medium, high)
3. **Decide** on an action (ignore, reply, escalate)
4. **Optionally generate** a reply when needed

The environment provides **per-step reward feedback** based on how well the agent's decisions match ground truth, enabling iterative learning and optimization.

---

## 🌍 Real-World Motivation

The average professional receives **120+ emails per day**. Manually triaging each email consumes significant time and cognitive energy. This environment simulates the email triage problem, training AI agents to:

- **Filter spam** (30% of all email traffic)
- **Prioritize urgent messages** (financial alerts, security warnings)
- **Route appropriately** (reply to personal, escalate security issues)
- **Reduce information overload** through intelligent automation

The RL approach ensures the agent improves over time through reward-based feedback, adapting to different types of inboxes and user preferences.

---

## 🎯 Task Descriptions

### 🟢 Task 1: Easy — Spam Detection
| Attribute | Value |
|-----------|-------|
| **Objective** | Binary classification: spam vs non-spam |
| **Input** | Email sender, subject, body |
| **Output** | `{"category": "spam"}` or `{"category": "<other>"}` |
| **Scoring** | 1.0 = correct, 0.0 = incorrect |
| **Emails** | 20 deterministic samples (3 spam, 17 legitimate) |

### 🟡 Task 2: Medium — Category + Priority
| Attribute | Value |
|-----------|-------|
| **Objective** | Classify email category and assign priority |
| **Input** | Email sender, subject, body |
| **Output** | `{"category": "<cat>", "priority": "<low\|medium\|high>"}` |
| **Scoring** | Category correct → +0.6, Priority correct → +0.4 |
| **Partial Credit** | Related category → +0.3, Off-by-one priority → +0.2 |

### 🔴 Task 3: Hard — Full Email Triage
| Attribute | Value |
|-----------|-------|
| **Objective** | Full triage: classify, prioritize, decide action, generate reply |
| **Input** | Email sender, subject, body |
| **Output** | `{"category": "...", "priority": "...", "action_type": "...", "reply_text": "..."}` |
| **Scoring** | Category → +0.4, Priority → +0.3, Action → +0.3, Reply bonus → +0.1 |
| **Partial Credit** | Related category/action → half credit, off-by-one priority → half credit |

---

## 📐 Observation Space

The agent observes a structured `EnvironmentObservation` at each step:

```json
{
  "current_email": {
    "email_id": "email-001",
    "subject": "Your payment of $49.99 was received",
    "body": "Hi User, your payment of $49.99 to Acme Corp...",
    "sender": "noreply@paypal.com",
    "current_state": "pending"
  },
  "step_number": 0,
  "total_emails": 20,
  "processed_count": 0,
  "remaining_count": 20,
  "episode_done": false,
  "total_reward": 0.0,
  "task_id": "hard"
}
```

---

## 🎮 Action Space

The agent submits a structured `EmailAction`:

```json
{
  "category": "financial",
  "priority": "high",
  "action_type": "escalate",
  "reply_text": null
}
```

### Valid Values

| Field | Options |
|-------|---------|
| `category` | spam, support, sales, personal, financial, professional, educational, travel, healthcare, government, transactional, promotional, social, system, community, service |
| `priority` | low, medium, high |
| `action_type` | ignore, reply, escalate |
| `reply_text` | Free-text string (optional, used in hard task) |

---

## 💰 Reward Design

Rewards are given **at every step** (not just at episode end):

### Easy Task Rewards
| Condition | Reward |
|-----------|--------|
| Correct spam/non-spam | +1.0 |
| Incorrect | 0.0 |

### Medium Task Rewards
| Component | Correct | Partial | Wrong |
|-----------|---------|---------|-------|
| Category (0.6) | +0.6 | +0.3 (related) | 0.0 |
| Priority (0.4) | +0.4 | +0.2 (off-by-1) | 0.0 |

### Hard Task Rewards
| Component | Correct | Partial | Wrong |
|-----------|---------|---------|-------|
| Category (0.4) | +0.4 | +0.2 (related) | 0.0 |
| Priority (0.3) | +0.3 | +0.15 (off-by-1) | 0.0 |
| Action (0.3) | +0.3 | +0.15 (related) | 0.0 |
| Reply bonus | up to +0.1 | — | — |
| **Penalty** | — | — | -0.15 (ignoring high-priority) |

### Episode Logic
- **Start**: `reset()` loads 20 deterministic emails
- **Termination**: All emails processed OR max 25 steps reached
- **Duplicate penalty**: -0.5 for re-processing same email

---

## 🏗️ Project Structure

```
email-rectifier-openenv/
├── models.py                    # Pydantic schemas (Observation, Action, Reward)
├── grader.py                    # Unified graders (Easy, Medium, Hard)
├── environment.py               # → email_rectifier/environment.py
├── api_server.py                # FastAPI server (OpenEnv API)
├── inference.py                 # Evaluation inference script
├── validate.py                  # Compliance validation tests
├── openenv.yaml                 # OpenEnv configuration
├── Dockerfile                   # Container configuration
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── README.md                    # This file
│
├── email_rectifier/             # Core environment package
│   ├── __init__.py
│   └── environment.py           # EmailEnv class + dataset
│
├── graders/                     # Legacy graders (backward compat)
│   ├── __init__.py
│   ├── base.py
│   ├── classification_grader.py
│   ├── reply_grader.py
│   └── summarization_grader.py
│
├── tasks/                       # Legacy task definitions
│   ├── __init__.py
│   ├── base.py
│   ├── email_classification.py
│   ├── reply_generation.py
│   └── summarization.py
│
└── server/                      # Server entry wrapper
    ├── __init__.py
    └── app.py
```

---

## 🚀 Setup Instructions

### Prerequisites
- Python 3.10+
- pip

### Local Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/email-rectifier-openenv.git
cd email-rectifier-openenv

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Run validation
python validate.py

# Start the API server
python api_server.py
```

### Quick Test

```bash
# Reset environment (easy task)
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy"}'

# Take a step
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"category": "spam", "priority": "low", "action_type": "ignore"}}'

# Get state
curl http://localhost:7860/state
```

---

## 🐳 Docker Instructions

### Build

```bash
docker build -t email-rectifier-openenv .
```

### Run API Server

```bash
docker run -p 7860:7860 \
  -e HF_TOKEN=your_token_here \
  email-rectifier-openenv
```

### Run Inference

```bash
docker run \
  -e API_BASE_URL=https://api-inference.huggingface.co/v1 \
  -e MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3 \
  -e HF_TOKEN=your_token_here \
  email-rectifier-openenv \
  python inference.py
```

---

## 🤗 Hugging Face Deployment

### Deploy to HF Spaces

1. Create a new Space on [huggingface.co/new-space](https://huggingface.co/new-space)
2. Select **Docker** as the SDK
3. Push the repository:

```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/email-rectifier
git push hf main
```

4. Set secrets in Space settings:
   - `HF_TOKEN` — Your Hugging Face API token
   - `API_BASE_URL` — (optional) Custom API endpoint
   - `MODEL_NAME` — (optional) Model to use

### Verify Deployment

```bash
# Health check
curl https://YOUR_USERNAME-email-rectifier.hf.space/

# Reset environment
curl -X POST https://YOUR_USERNAME-email-rectifier.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "hard"}'

# Step
curl -X POST https://YOUR_USERNAME-email-rectifier.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"category": "financial", "priority": "high", "action_type": "escalate"}}'
```

---

## 📊 Baseline Results

| Task | Strategy | Average Score |
|------|----------|:------------:|
| **Easy** | Always predict "not-spam" | 0.850 |
| **Easy** | Rule-based (keyword matching) | 0.950 |
| **Medium** | Random category + priority | 0.100 |
| **Medium** | Rule-based classification | 0.650 |
| **Hard** | Random all fields | 0.080 |
| **Hard** | Rule-based triage | 0.580 |
| **Hard** | LLM (Mistral-7B) | 0.720 |

---

## 🔧 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/reset` | POST | Reset environment (accepts `task_id`) |
| `/step` | POST | Submit action for current email |
| `/state` | GET | Get current observation |
| `/tasks` | GET | List available tasks |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

Built for the OpenEnv Hackathon. Uses FastAPI, Pydantic v2, and the OpenAI-compatible API specification.
