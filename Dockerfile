FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev \
    || pip install --no-cache-dir \
        fastapi \
        uvicorn[standard] \
        sqlalchemy \
        psycopg2-binary \
        alembic \
        prometheus-client \
        pydantic \
        python-multipart

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Create non-root user
RUN adduser --disabled-password --gecos '' --uid 1000 capsim \
    && chown -R capsim:capsim /app
USER capsim

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Expose ports
EXPOSE 8000 9090

# Default command - use simplified version for now
CMD ["python", "-m", "uvicorn", "capsim.api.main_simple:app", "--host", "0.0.0.0", "--port", "8000"] 