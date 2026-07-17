# syntax=docker/dockerfile:1
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_BASE_URL=http://0.0.0.0:7860 \
    LOCAL_STORAGE_PATH=/tmp/ai-docx-editor

WORKDIR /code

# Install system dependencies if required by lxml/OpenXML processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with UID 1000 (Hugging Face Spaces requirement)
RUN useradd -m -u 1000 user && \
    mkdir -p /tmp/ai-docx-editor && \
    chown -R user:user /code /tmp/ai-docx-editor

# Copy requirements and install dependencies
COPY --chown=user:user requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and configuration
COPY --chown=user:user app /code/app
COPY --chown=user:user api /code/api
COPY --chown=user:user config /code/config
COPY --chown=user:user schemas /code/schemas

# Switch to non-root user
USER user

# Expose port 7860 (Hugging Face Spaces default port)
EXPOSE 7860

# Health check against /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
