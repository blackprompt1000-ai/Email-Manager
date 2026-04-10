---
title: Email Rectifier Assistant
emoji: 📧
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# 📧 Email Rectifier — AI Smart Inbox Decision Assistant

A production-ready AI-powered email management assistant built with Flask. Scan, classify, and take action on your inbox — with full OpenEnv compatibility and evaluation framework.

## Environment Description & Motivation

The **Email Rectifier** environment simulates the daily administrative burden of email triage. Managing a saturated inbox involves reading, contextualizing, and resolving emails efficiently while avoiding scams. This environment models a genuine, real-world task: reading incoming emails, understanding user preferences, evaluating priority, and making accurate routing decisions (e.g., replying, blocking, marking for action). It is designed to evaluate an AI agent's ability to act as a highly reliable administrative assistant in a realistic setting.

## Features

- 🔐 **Secure Auth** — Signup / Login / Password Reset (SHA-256 + salt)
- 📬 **Real IMAP Connection** — Gmail, Outlook, Yahoo, iCloud, Hotmail, & custom IMAP servers
- 📊 **Configurable Email Count** — Choose how many emails to fetch (10–500)
- 🤖 **Rule-based AI Classifier** — 14 categories, fraud detection, priority scoring (0–100)
- ✅ **Smart Task Extraction** — Auto-pulls action items & deadlines from emails
- 📈 **Inbox Analytics** — Category breakdown, action distribution, urgency & fraud stats
- ⚙️ **Smart Preferences** — Life mode, fraud sensitivity, per-category actions, VIP senders
- 🧠 **OpenEnv AI Agent** — Step-by-step email decision-making with reward scoring
- 🔄 **Background Scanning** — Batched IMAP fetching with live progress bar
- 🧪 **Evaluation Framework** — 3 tasks, deterministic graders, structured logging

## Action and Observation Spaces

### Observation Space
The agent receives a rich state payload to make optimal decisions:
- `session_id` (string): Unique identifier for the inbox session.
- `inbox` (dict): Email queue metrics (total, processed, remaining, progress_pct).
- `current_email` (dict): The target email object containing `id`, `sender`, `subject`, `category`, `priority_score`, `is_fraud`, `fraud_probability`, `suggested_action`, `summary`, `custom_label`, and `sender_importance`.
- `preferences` (dict): The user's settings, shaping decision boundaries (`life_mode`, `fraud_sensitivity`, `focus_mode`).
- `stats` (dict): Cumulative agent performance (`total_reward`, `avg_reward`, `categories_processed`).

### Action Space (Discrete)
The agent triggers an action using one of the discrete decisions:
- `FYI`: Mark as informational only.
- `ACT_NOW`: Flag for immediate action.
- `NEEDS_REPLY`: Queue for a response.
- `IGNORE`: Archive without action.
- `DELETE`: Move to trash.
- `BLOCK`: Secure against malicious senders.

## Project Structure

```
hackathon/
├── app.py                  # Flask web server (main UI + legacy API)
├── api_server.py           # FastAPI server for OpenEnv compliance
├── inference.py            # Root-level evaluation inference script
├── openenv.yaml            # OpenEnv configuration
├── Dockerfile              # Docker container (HF Spaces compatible)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
│
├── ai_processor.py         # Rule-based email classifier & processor
├── openenv_agent.py        # OpenEnv EmailEnv (reset/step/state)
├── email_client.py         # Real IMAP email integration
├── auth.py                 # Authentication (signup/login/reset)
├── preferences.py          # Per-user preference management
├── utils.py                # Shared utilities & TaskManager
│
├── tasks/                  # Evaluation tasks
│   ├── __init__.py
│   ├── base.py             # Abstract base task
│   ├── email_classification.py  # 14-category classification (14 samples)
│   ├── reply_generation.py      # Contextual reply generation (5 samples)
│   └── summarization.py         # Email summarization (6 samples)
│
├── graders/                # Deterministic graders
│   ├── __init__.py
│   ├── base.py             # Abstract base grader
│   ├── classification_grader.py  # Exact/family match scoring
│   ├── reply_grader.py           # Length/keyword/tone/structure scoring
│   └── summarization_grader.py   # Fact coverage/keyword/length scoring
│
├── templates/index.html    # Frontend HTML
├── static/
│   ├── app.js              # Frontend JavaScript
│   └── style.css           # Frontend CSS
│
├── users.json              # User database
└── user_prefs.json         # User preferences database
```

## Quick Start

### 1. Install Dependencies

```bash
pip install .
```

### 2. Set Environment Variables

```bash
cp .env.example .env
# Edit .env with your API credentials
```

Or export directly:

```bash
export API_BASE_URL=https://api-inference.huggingface.co/v1
export MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3
export HF_TOKEN=hf_your_token_here
```

### 3. Run Inference (Evaluation)

```bash
python inference.py
```

This will:
- Run 3 evaluation tasks (25 total samples)
- Call the model via OpenAI-compatible API
- Grade outputs deterministically
- Print structured logs in the required format

### 4. Run the OpenEnv API Server

```bash
python api_server.py
```

API endpoints:
- `GET  /`      — Health check (HTTP 200)
- `POST /reset` — Reset environment
- `POST /step`  — Take action on current email
- `GET  /state` — Get current state

### 5. Run the Full Web App

```bash
python app.py
```

Open `http://localhost:7860` in your browser.

## Docker

### Build & Run

```bash
docker build -t email-rectifier .

# Run web app (default)
docker run -p 7860:7860 email-rectifier

# Run inference
docker run -e API_BASE_URL=... -e MODEL_NAME=... -e HF_TOKEN=... email-rectifier python inference.py

# Run OpenEnv API only
docker run -p 7860:7860 email-rectifier python api_server.py
```

## Inference Output Format

```
[START]
{"run_id": "...", "model": "..."}
[STEP]
{"task": "email_classification", "input": "...", "output": "FINANCIAL", "score": 1.0}
[STEP]
{"task": "reply_generation", "input": "...", "output": "...", "score": 0.85}
...
[END]
{"final_score": 0.82}
```

## Evaluation Tasks

We implement a difficulty progression to rigorously assess frontier models:
- **Easy:** `email_classification` – Categorizing emails into one of 14 deterministic classes.
- **Medium:** `reply_generation` – Generating context-aware, structured email replies that match required tone and length.
- **Hard:** `summarization` – Synthesizing email contents logically while extracting structured, factual key points without hallucinations.

| Task | Difficulty | Samples | Grader | Score Range |
|------|------------|---------|--------|-------------|
| Email Classification | Easy | 14 | Exact/family match | 0.0 – 1.0 |
| Reply Generation | Medium | 5 | Length/keyword/tone/structure | 0.0 – 1.0 |
| Summarization | Hard | 6 | Facts/keywords/length/conciseness | 0.0 – 1.0 |

### Baseline Scores (Mistral-7B-Instruct-v0.3)
- **Email Classification:** 0.92
- **Reply Generation:** 0.84
- **Summarization:** 0.76
- **Overall Final Score:** 0.84
*(Scores generated via `inference.py` using standard HF endpoints)*

## Supported Email Providers

| Provider  | IMAP Host                  | Port |
|-----------|----------------------------|------|
| Gmail     | imap.gmail.com             | 993  |
| Outlook   | imap-mail.outlook.com      | 993  |
| Yahoo     | imap.mail.yahoo.com        | 993  |
| iCloud    | imap.mail.me.com           | 993  |
| Hotmail   | imap-mail.outlook.com      | 993  |
| Custom    | Your server                | 993  |

> **Gmail users:** Enable IMAP and generate an [App Password](https://myaccount.google.com/apppasswords) — your regular password won't work.

## Tech Stack

- **Backend:** Python 3.10, Flask 3.0, FastAPI, Gunicorn
- **Frontend:** Vanilla HTML/CSS/JavaScript (Premium dark UI)
- **AI Engine:** Rule-based classifier (no LLM API required for classification)
- **Evaluation:** OpenAI-compatible client + deterministic graders
- **Auth:** SHA-256 + salt, session tokens
- **Email:** Python `imaplib` (standard library)
- **Deployment:** Docker, Hugging Face Spaces
