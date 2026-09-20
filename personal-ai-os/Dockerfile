# Milestone 45: Dockerization.
# Multi-stage build: a builder stage installs Python deps (including
# sentence-transformers/faiss-cpu, which pull in heavier native wheels),
# then a slim runtime stage copies only the installed packages and app code
# — keeps the final image smaller than installing everything in one stage.

FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed to build some packages' native extensions (faiss-cpu,
# sentence-transformers' torch dependency) — kept in the builder stage only.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from the builder stage rather than reinstalling.
COPY --from=builder /install /usr/local

COPY app/ ./app/
COPY specs/ ./specs/
COPY evals/ ./evals/

# Data directory for SQLite (Milestone 50 replaces this with a real DB in
# production; this keeps local/single-instance runs working the same way
# they do outside Docker).
RUN mkdir -p /app/data

# Non-root user — a basic production security practice (Milestone 58 expands
# on hardening); the app should never need root inside the container.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check hits the voice API's root page (Milestone 51's observability
# work adds a dedicated /health endpoint; until then this is a reasonable
# proxy for "is the process alive and serving HTTP").
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["uvicorn", "app.api.voice_api:app", "--host", "0.0.0.0", "--port", "8000"]
