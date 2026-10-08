# ==============================================================================
# Multi-Stage Hardened Dockerfile for SecureFlow (Smart City Traffic Operations)
# Non-root user, read-only root filesystem compatible, no build tools in runtime
# ==============================================================================

# Stage 1: Build Dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final Minimal Runtime Image
FROM python:3.12-slim AS runner

# Security: Create non-privileged user and group
RUN groupadd -g 10001 secureflow && \
    useradd -u 10001 -g secureflow -s /bin/false -M secureflow

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/secureflow/.local
ENV PATH=/home/secureflow/.local/bin:$PATH
ENV PYTHONPATH=/app/src:/app

# Copy application source code and static assets
COPY src/ /app/src/
COPY static/ /app/static/
COPY scripts/ /app/scripts/
COPY pyproject.toml /app/

# Create runtime directories for temp/data with ownership
RUN mkdir -p /app/data /tmp/secureflow && \
    chown -R secureflow:secureflow /app /tmp/secureflow

USER secureflow

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

CMD ["python", "-m", "uvicorn", "secureflow.main:app", "--host", "0.0.0.0", "--port", "8000"]
