# Multi-stage Dockerfile for Habit Reward Bot
# Stage 1: Builder - Install dependencies
FROM python:3.13-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Stage 2: Runtime - Minimal production image
FROM python:3.13-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash botuser

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=botuser:botuser . .

# Copy and set permissions for entrypoint script
COPY --chown=botuser:botuser deployment/scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create directories for static files and persistence
RUN mkdir -p /app/staticfiles /app/data && \
    chown -R botuser:botuser /app/staticfiles /app/data

# Switch to non-root user
USER botuser

# Expose port for Django/Uvicorn
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/admin/login/?next=/admin/')" || exit 1

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command - start Uvicorn ASGI server
CMD ["uvicorn", "src.habit_reward_project.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
