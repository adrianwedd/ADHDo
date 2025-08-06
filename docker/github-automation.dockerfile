# GitHub Issue Automation System - Production Dockerfile
# 
# Multi-stage build for optimized production deployment with
# comprehensive monitoring, health checks, and security hardening.

# === BUILD STAGE ===
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG BUILD_DATE
ARG VCS_REF

# Build metadata
LABEL org.opencontainers.image.title="ADHDo GitHub Automation System"
LABEL org.opencontainers.image.description="Enterprise GitHub issue automation with AI-powered feature detection"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.revision=${VCS_REF}
LABEL org.opencontainers.image.vendor="CODEFORGE Systems Architecture"
LABEL org.opencontainers.image.authors="building-the-future@codeforge.dev"

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt pyproject.toml ./
COPY src/github_automation/requirements-automation.txt ./requirements-automation.txt

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-automation.txt

# Install additional production dependencies
RUN pip install --no-cache-dir \
    gunicorn==21.2.0 \
    uvloop==0.17.0 \
    httptools==0.6.0 \
    prometheus-client==0.17.1 \
    sentry-sdk[fastapi]==1.32.0

# === PRODUCTION STAGE ===
FROM python:3.11-slim as production

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    procps \
    htop \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser static/ ./static/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser pyproject.toml ./

# Create necessary directories with correct permissions
RUN mkdir -p /app/logs /app/data /app/tmp /app/cache \
    && chown -R appuser:appuser /app

# Create health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/api/github/health || exit 1' > /usr/local/bin/healthcheck.sh \
    && chmod +x /usr/local/bin/healthcheck.sh

# Environment variables for production
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ENVIRONMENT=production
ENV LOG_LEVEL=INFO
ENV WORKERS=4
ENV MAX_WORKERS=8
ENV WORKER_CLASS=uvicorn.workers.UvicornWorker
ENV BIND_HOST=0.0.0.0
ENV BIND_PORT=8000
ENV TIMEOUT=120
ENV KEEPALIVE=2
ENV MAX_REQUESTS=1000
ENV MAX_REQUESTS_JITTER=100

# Security settings
ENV SECURE_SSL_REDIRECT=true
ENV SESSION_COOKIE_SECURE=true
ENV CSRF_COOKIE_SECURE=true

# GitHub automation specific settings
ENV GITHUB_AUTOMATION_ENABLED=true
ENV GITHUB_WEBHOOK_ENABLED=true
ENV AUTOMATION_MAX_CONCURRENT_ACTIONS=10
ENV AUTOMATION_RATE_LIMIT_BUFFER=0.8

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Production startup script
COPY --chown=appuser:appuser docker/entrypoint-github-automation.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Default command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["production"]

# === DEVELOPMENT STAGE ===
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest==7.4.2 \
    pytest-asyncio==0.21.1 \
    pytest-cov==4.1.0 \
    black==23.7.0 \
    ruff==0.0.292 \
    mypy==1.5.1 \
    pre-commit==3.4.0 \
    jupyter==1.0.0 \
    ipdb==0.13.13

# Development environment variables
ENV ENVIRONMENT=development
ENV DEBUG=true
ENV LOG_LEVEL=DEBUG
ENV RELOAD=true
ENV WORKERS=1

# Create development directories
RUN mkdir -p /app/tests /app/notebooks /app/dev-data \
    && chown -R appuser:appuser /app

# Switch back to app user
USER appuser

# Development command
CMD ["development"]

# === TESTING STAGE ===
FROM development as testing

# Copy test files
COPY --chown=appuser:appuser tests/ ./tests/
COPY --chown=appuser:appuser pytest.ini ./

# Testing environment
ENV ENVIRONMENT=testing
ENV DATABASE_URL=postgresql+asyncpg://test:test@test-db:5432/test_adhd
ENV REDIS_URL=redis://test-redis:6379/0

# Test command
CMD ["pytest", "tests/", "-v", "--cov=src/github_automation", "--cov-report=html:/app/coverage"]

# === CI/CD STAGE ===
FROM testing as ci

# Install CI/CD specific tools
USER root
RUN pip install --no-cache-dir \
    coverage[toml]==7.3.0 \
    safety==2.3.4 \
    bandit==1.7.5 \
    semgrep==1.45.0

# CI/CD scripts
COPY --chown=appuser:appuser scripts/ci/ ./scripts/ci/
RUN chmod +x ./scripts/ci/*.sh

USER appuser

# CI command
CMD ["./scripts/ci/run-all-checks.sh"]