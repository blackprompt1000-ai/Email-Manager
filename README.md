🚀 AI Smart Inbox Decision Assistant (OpenEnv)

An OpenEnv-compatible simulation environment where AI agents learn to intelligently manage emails — not just classify them.

Instead of basic filtering, this system focuses on:

👉 What should the user do next?

🧠 Problem

Modern email systems:

- overload users with too many emails
- lack meaningful prioritization
- fail to clearly indicate what needs action
- still allow spam & phishing to slip through

💡 Solution
AI-powered decision assistant for email workflows

The agent:
- prioritizes emails
- detects fraud/phishing
- summarizes content
- extracts tasks & deadlines
- recommends actions (reply, ignore, delete, block)

🎯 Key Features
🔥 Action-Based Inbox

Instead of folders:
🔴 Act Now
🟡 Needs Reply
🟢 FYI
⚫ Ignore

⚡ Smart Priority Scoring
Each email gets a score (0–100) based on:
- sender importance
- urgency
- user preferences

🕵️ Fraud & Phishing Detection
Detects:
- suspicious senders
- scam patterns
- fake urgency

🧾 Email Summarization
1–2 line summaries

key points extraction
⏱️ Task & Deadline Extraction
Example:
“Submit report by Friday” → automatically detected

🧬 Personalized User Profiles
Supports:
- students
- professionals
- freelancers
- job seekers

Features
- 🔐 Secure Auth — Signup / Login / Password Reset
- 📬 Real IMAP Connection — Gmail, Outlook, Yahoo, iCloud, Hotmail, & custom IMAP servers
- 📊 Configurable Email Count — Choose how many emails to fetch (10–500)
- 🤖 Rule-based AI Classifier — 14 categories, fraud detection, priority scoring (0–100)
- ✅ Smart Task Extraction — Auto-pulls action items & deadlines from emails
- 📈 Inbox Analytics — Category breakdown, action distribution, urgency & fraud stats
- ⚙️ Smart Preferences — Life mode, fraud sensitivity, per-category actions, VIP senders
- 🧠 OpenEnv AI Agent — Step-by-step email decision-making with reward scoring
- 🔄 Background Scanning — Batched IMAP fetching with live progress bar

🟢 Task 1 – Classification
Classify email into category

🟡 Task 2 – Priority & Fraud Detection
assign priority
detect malicious emails

🔴 Task 3 – Full Workflow
classify
prioritize
detect fraud
decide action
summarize
extract tasks

How to Use
1. Register or log in with your credentials
2. Connect your email account (use an **App Password** for Gmail)
3. Choose how many emails to fetch (10–500)
4. Click **Connect & Continue** to scan your inbox
5. Configure AI preferences based on detected categories
6. Review AI-generated summaries, priority scores, and suggested actions

Supported Email Providers
| Provider  | IMAP Host                  | Port |
|-----------|----------------------------|------|
| Gmail     | imap.gmail.com             | 993  |
| Outlook   | imap-mail.outlook.com      | 993  |
| Yahoo     | imap.mail.yahoo.com        | 993  |
| iCloud    | imap.mail.me.com           | 993  |
| Hotmail   | imap-mail.outlook.com      | 993  |
| Custom    | Your server                | 993  |

> **Gmail users:** Enable IMAP and generate an [App Password](https://myaccount.google.com/apppasswords) — your regular password won't work.

Tech Stack
- Backend: Python 3.10, Flask 3.0, Gunicorn
- Frontend: Vanilla HTML/CSS/JavaScript (Premium dark UI)
- AI Engine: Rule-based classifier (no LLM API required)
- Auth: SHA-256 + salt, session tokens
- Email: Python `imaplib` (standard library)
- Deployment: Docker, Hugging Face Spaces
