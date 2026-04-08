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

A production-ready AI-powered email management assistant built with Flask. Scan, classify, and take action on your inbox — all without requiring an LLM API.

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

## How to Use

1. Register or log in with your credentials
2. Connect your email account (use an **App Password** for Gmail)
3. Choose how many emails to fetch (10–500)
4. Click **Connect & Continue** to scan your inbox
5. Configure AI preferences based on detected categories
6. Review AI-generated summaries, priority scores, and suggested actions

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

- **Backend:** Python 3.10, Flask 3.0, Gunicorn
- **Frontend:** Vanilla HTML/CSS/JavaScript (Premium dark UI)
- **AI Engine:** Rule-based classifier (no LLM API required)
- **Auth:** SHA-256 + salt, session tokens
- **Email:** Python `imaplib` (standard library)
- **Deployment:** Docker, Hugging Face Spaces
