# Stage 1: Build stage
FROM nvidia/cuda:12.3.0-cudnn8-devel-ubuntu22.04 AS build

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Install Python 3.9 and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.9 \
    python3.9-dev \
    python3.9-venv \
    python3-pip \
    python3-wheel \
    build-essential \
    pkg-config \
    wget \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python3.9 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Copy requirements file
WORKDIR /app
COPY requirements.txt .

# Install dependencies
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Install TensorFlow with GPU support
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels tensorflow==2.15.0

# Stage 2: Production stage
FROM nvidia/cuda:12.3.0-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install Python 3.9 and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.9 \
    python3.9-venv \
    python3-pip \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python3.9 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip

# Create app directory
WORKDIR /app

# Copy wheels from build stage
COPY --from=build /app/wheels /wheels
COPY --from=build /app/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir /wheels/*

# Copy application code
COPY . .

# Create a non-root user
RUN groupadd -r ocr && \
    useradd -r -g ocr -d /app -s /bin/bash ocr && \
    chown -R ocr:ocr /app

# Switch to non-root user
USER ocr

# Expose port
EXPOSE 5000

# Set health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Command to run the application
CMD ["python", "-m", "gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2"]