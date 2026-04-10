# ── Email Rectifier Assistant — Production Dockerfile ──
# Compatible with Hugging Face Spaces (Docker SDK)
# Supports: Flask UI, FastAPI OpenEnv API, and inference.py

FROM python:3.10-slim

# System-level setup — minimal footprint
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Install Python dependencies first (leverages Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure data files are writable (HF Spaces runs as non-root sometimes)
RUN chmod -R 777 /app

# Hugging Face Spaces requires port 7860
EXPOSE 7860

# Environment variables (can be overridden at runtime)
ENV API_BASE_URL=https://api-inference.huggingface.co/v1
ENV MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3
ENV HF_TOKEN=""

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/')" || exit 1

# Default: run the Flask UI + API server with gunicorn
# Override with: docker run <image> python inference.py     (for evaluation)
# Override with: docker run <image> python api_server.py    (for OpenEnv API only)
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
