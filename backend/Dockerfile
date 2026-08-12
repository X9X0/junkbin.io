FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    build-essential \
    libpq-dev \
    libmagic1 \
    curl \
    gettext \
    tesseract-ocr \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Baked in at build time so Sentry can tag events with the release that
# produced them (see config/settings/production.py) - placed after the
# pip install layer so it doesn't bust that cache on every commit.
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA

# Copy project
COPY . /app/

# Create media and static directories
RUN mkdir -p /app/media /app/static && \
    chmod -R 755 /app/media /app/static

# Expose port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "config.wsgi:application"]
