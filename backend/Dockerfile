FROM python:3.12-slim

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

# Background-removal models (apps/media_tools) - baked into the image at
# build time so runtime never depends on an outside service. /opt is
# outside the ./backend:/app bind mount used in docker-compose.yml (dev
# and prod both mount the source tree there), so this survives container
# recreation regardless of that mount.
#
# This only pre-fetches the ONNX model weight files - it deliberately
# doesn't also run remove() to "warm up" pymatting/numba. Their alpha-
# matting kernels use @njit(<explicit signature>) with no cache=True, so
# numba recompiles them from scratch (~100s of real CPU time) on every
# fresh process unconditionally; there's no cache for a build-time warmup
# to bake in. See apps/media_tools/bg_removal.py for how that's actually
# handled (lazy import, kept out of Django's ordinary startup path).
ENV U2NET_HOME=/opt/rembg-models
RUN python -c "from rembg import new_session; [new_session(m) for m in ('u2net', 'isnet-general-use', 'u2netp')]"

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
