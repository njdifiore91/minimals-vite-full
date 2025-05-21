# =========================================================================
# Build stage - Creates wheels for all dependencies
# =========================================================================
FROM python:3.9-slim as build

# Set working directory
WORKDIR /app

# Install build dependencies
# - build-essential and gcc are needed for compiling some Python packages
# - git is needed for packages that might be installed from git repositories
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Build wheels for dependencies
# This creates reusable binary packages that don't require compilation in the final image
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# =========================================================================
# Production stage - Minimal image with only required dependencies
# =========================================================================
FROM python:3.9-slim

# Set metadata labels
LABEL maintainer="Dollar Funding Engineering Team" \
      description="Document Service for MCA Application Processing System" \
      version="1.0.0"

# Set working directory
WORKDIR /app

# Create non-root user for security
# Running as non-root is a security best practice for containers
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser

# Install runtime dependencies
# - libgomp1 is required for scikit-learn
# - tesseract-ocr is needed for OCR capabilities
# - libmagic1 is needed for file type detection
# - curl is needed for health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgomp1 \
    tesseract-ocr \
    libmagic1 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and requirements from build stage
COPY --from=build /app/wheels /wheels
COPY --from=build /app/requirements.txt .

# Install dependencies from wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copy application code
COPY src/ /app/src/

# Set proper permissions
RUN chown -R appuser:appuser /app

# Security hardening
# Make app directory read-only except for specific directories that need write access
RUN mkdir -p /app/data /app/logs && \
    chmod -R 755 /app && \
    chmod -R 777 /app/data /app/logs && \
    chown -R appuser:appuser /app/data /app/logs

# Switch to non-root user
USER appuser

# Expose port for the service
EXPOSE 5000

# Set Python path
ENV PYTHONPATH=/app

# Set default environment variables
# These can be overridden at runtime
ENV APP_ENV=production \
    LOG_LEVEL=INFO \
    WORKERS=4 \
    RABBITMQ_HOST=rabbitmq \
    RABBITMQ_PORT=5672 \
    RABBITMQ_EXCHANGE=mca.documents \
    RABBITMQ_QUEUE=document-processing \
    S3_ENDPOINT=s3 \
    S3_BUCKET=mca-documents-production \
    MODEL_VERSION=latest

# Set health check for container orchestration
# This checks the liveness endpoint which verifies the application is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:5000/health/liveness || exit 1

# Run the application with gunicorn
# - bind to all interfaces on port 5000
# - number of workers based on environment variable (default 4)
# - use uvicorn worker class for ASGI support (FastAPI)
# - timeout set to 120 seconds for longer document processing tasks
CMD ["gunicorn", "--bind", "0.0.0.0:5000", \
     "--workers", "${WORKERS}", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "src.main:app"]