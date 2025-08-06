# Multi-stage build for MCP ADHD Server production deployment
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Add labels for metadata
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="mcp-adhd-server" \
      org.label-schema.description="Meta-Cognitive Protocol server for ADHD executive function support" \
      org.label-schema.version=$VERSION \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/adrianwedd/mcp-adhd-server" \
      org.label-schema.schema-version="1.0"

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy dependency files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install hatch and build the package
RUN pip install --no-cache-dir hatch
RUN hatch build

# Production stage
FROM python:3.11-slim as production

# Set build arguments for runtime
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Add metadata labels
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="mcp-adhd-server" \
      org.label-schema.description="Meta-Cognitive Protocol server for ADHD executive function support" \
      org.label-schema.version=$VERSION \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/adrianwedd/mcp-adhd-server" \
      org.label-schema.schema-version="1.0"

# Create non-root user for security
RUN groupadd -r mcpuser && useradd -r -g mcpuser -s /bin/false mcpuser

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    redis-tools \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy built package from builder stage
COPY --from=builder /build/dist/*.whl /tmp/

# Install the package and dependencies
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/static && \
    chown -R mcpuser:mcpuser /app

# Copy static files and templates
COPY static/ ./static/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Set ownership
RUN chown -R mcpuser:mcpuser /app

# Create health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/health || exit 1' > /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Switch to non-root user
USER mcpuser

# Set environment variables with production defaults
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    LOG_LEVEL=INFO \
    ENVIRONMENT=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD /healthcheck.sh

# Default command
CMD ["sh", "-c", "alembic upgrade head && uvicorn mcp_server.main:app --host $HOST --port $PORT --log-level $LOG_LEVEL"]

# Development stage (for testing and development)
FROM production as development

# Switch back to root to install dev dependencies
USER root

# Install development tools
RUN pip install --no-cache-dir \
    pytest>=7.4.0 \
    pytest-asyncio>=0.21.0 \
    pytest-mock>=3.12.0 \
    pytest-cov>=4.1.0 \
    black>=23.0.0 \
    ruff>=0.1.0 \
    mypy>=1.6.0 \
    ipython \
    jupyter

# Set development environment
ENV ENVIRONMENT=development \
    LOG_LEVEL=DEBUG

# Switch back to mcpuser
USER mcpuser

# Override command for development (with auto-reload)
CMD ["sh", "-c", "alembic upgrade head && uvicorn mcp_server.main:app --host $HOST --port $PORT --log-level $LOG_LEVEL --reload"]