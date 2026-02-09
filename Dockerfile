# x402-tron-facilitator Docker image
# Python 3.12 slim for smaller image
FROM python:3.12-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Build deps: gcc for wheels, git for pip install from git URLs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
# Use example config (mount your facilitator.config.yaml at runtime to override)
COPY facilitator.config.example.yaml ./facilitator.config.yaml

# Create logs directory (config may write here)
RUN mkdir -p logs && chmod 755 logs

# Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

# Default: run facilitator. Override CMD for custom entry.
CMD ["python", "src/main.py"]
