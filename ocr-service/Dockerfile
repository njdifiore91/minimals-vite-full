# Build stage
# Use Python 3.9 as specified in section 3.1.1 of the technical specification
FROM python:3.9-slim as build

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Create wheels for dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production stage
# Use NVIDIA CUDA image for GPU acceleration as required in section 3.2.3
FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TF_FORCE_GPU_ALLOW_GROWTH=true \
    TF_GPU_ALLOCATOR=cuda_malloc_async \
    PYTHONPATH=/app \
    # Environment variables for service configuration
    OCR_SERVICE_VERSION=1.0.0 \
    # Set log level as specified in section 0.2.5
    LOG_LEVEL=INFO

# Set working directory
WORKDIR /app

# Install Python and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.9 \
    python3.9-distutils \
    python3-pip \
    python3-setuptools \
    curl \
    # Required for health checks
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Make sure we use the right python version
RUN ln -sf /usr/bin/python3.9 /usr/bin/python3 && \
    ln -sf /usr/bin/python3 /usr/bin/python

# Copy wheels and requirements from build stage
COPY --from=build /app/wheels /wheels
COPY --from=build /app/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /wheels/* && \
    # Install TensorFlow 2.15.0 with CUDA support as specified in section 3.2.2
    pip install --no-cache-dir tensorflow==2.15.0 tensorflow[and-cuda] && \
    # Install additional dependencies for RabbitMQ and S3 as specified in section 3.2.2
    pip install --no-cache-dir amqplib==0.10.3 && \
    pip install --no-cache-dir boto3

# Create non-root user for security as specified in section 8.5.4
RUN groupadd -r ocr && useradd -r -g ocr -s /bin/false ocr && \
    mkdir -p /app/data /app/logs /app/models && \
    chown -R ocr:ocr /app

# Copy application code
COPY . .

# Set permissions
RUN chown -R ocr:ocr /app

# Switch to non-root user
USER ocr

# Expose port for API access
EXPOSE 5000

# Health check for Kubernetes probes as specified in section 3.2.3
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Command to run the application
CMD ["python", "-m", "src.main"]