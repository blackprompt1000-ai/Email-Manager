# ── Email Rectifier — AI Smart Inbox Decision Assistant ──
# Production Dockerfile for Hugging Face Spaces (Docker SDK)
# Serves the Flask web UI + OpenEnv API endpoints

FROM python:3.10-slim

# ── System Dependencies ─────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# ── Working Directory ───────────────────────────────────
WORKDIR /app

# ── Install Python Dependencies (layer caching) ────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy ALL Application Code ──────────────────────────
# Core Flask app + modules
COPY app.py .
COPY auth.py .
COPY email_client.py .
COPY ai_processor.py .
COPY utils.py .
COPY preferences.py .
COPY openenv_agent.py .

# OpenEnv API + models
COPY api_server.py .
COPY models.py .
COPY grader.py .
COPY inference.py .
COPY validate.py .
COPY openenv.yaml .

# Packages / subdirectories
COPY email_rectifier/ ./email_rectifier/
COPY graders/ ./graders/
COPY tasks/ ./tasks/
COPY server/ ./server/

# Frontend (templates + static assets)
COPY templates/ ./templates/
COPY static/ ./static/

# Data files (writable defaults)
COPY users.json .
COPY user_prefs.json .

# ── Permissions (HF Spaces may run as non-root) ────────
RUN chmod -R 777 /app

# ── Port ────────────────────────────────────────────────
EXPOSE 7860

# ── Environment Variables ───────────────────────────────
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV API_BASE_URL=https://api-inference.huggingface.co/v1
ENV MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3
ENV HF_TOKEN=""
ENV OPENAI_API_KEY=""

# ── Health Check ────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/')" || exit 1

# ── Start the Flask Application ─────────────────────────
# Using gunicorn for production stability
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
