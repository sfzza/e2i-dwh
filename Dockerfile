# Main Dockerfile for Railway deployment
# This will build the Django backend as the primary service

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies including Node.js
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        curl \
        git \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        python3-dev \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY e2i/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . /app/

# Make start script executable
RUN chmod +x start.sh

# Create necessary directories
RUN mkdir -p /app/exports
RUN mkdir -p /app/logs
RUN mkdir -p /app/e2i/backend/logs
RUN mkdir -p /app/e2i/backend/static
RUN mkdir -p /app/e2i/backend/staticfiles

# Create __init__.py files for proper Python package structure
RUN touch /app/e2i/__init__.py && \
    touch /app/e2i/backend/__init__.py && \
    touch /app/e2i/backend/e2i_api/__init__.py

# Set proper permissions
RUN chmod -R 755 /app

# Expose port (Railway will set PORT environment variable)
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health/ || exit 1

# Start the application
CMD ["bash", "start.sh"]
