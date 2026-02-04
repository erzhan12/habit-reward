# Multi-stage Dockerfile for Habit Reward Bot (Simplified)
# Stage 1: Builder - Install dependencies
FROM python:3.13-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Stage 2: Runtime - Minimal production image
FROM python:3.13-slim

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash botuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=botuser:botuser src/ ./src/
COPY --chown=botuser:botuser manage.py asgi.py ./

# Copy entrypoint script
COPY --chown=botuser:botuser deployment/scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create directories with proper permissions
RUN mkdir -p /app/staticfiles /app/data && \
    chown -R botuser:botuser /app/staticfiles /app/data

# Switch to non-root user
USER botuser

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/admin/login/')" || exit 1

# Entrypoint handles migrations and superuser creation
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command: Start Uvicorn server (combined Django + FastAPI)
CMD ["uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
