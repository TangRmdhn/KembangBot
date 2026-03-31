FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir ".[dev]"

# Copy application code
COPY . .

# HF Spaces requires port 7860
EXPOSE 7860

# Non-root user (HF Spaces requirement)
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Start server on port 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
