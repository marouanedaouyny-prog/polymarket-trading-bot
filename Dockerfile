# =============================================================================
# Polymarket Trading Bot — Production Dockerfile
# Multi-stage: smaller final image, faster builds
# =============================================================================

# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps
RUN pip install --no-cache-dir build wheel setuptools

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---- Runtime stage ----
FROM python:3.11-slim

RUN useradd -m -u 1000 user

WORKDIR /app

# Copy pre-built wheels from builder
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links /wheels -r /wheels/requirements.txt \
    && rm -rf /wheels

# Copy application code
COPY --chown=user:user . .

# Hardened security
USER user
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1

CMD ["python", "entrypoint.py"]