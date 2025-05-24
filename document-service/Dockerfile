# Build stage
FROM python:3.9-slim as build

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install build dependencies and create wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production stage
FROM python:3.9-slim

# Create non-root user for security
RUN groupadd -r docservice && 
    useradd -r -g docservice -d /home/docservice -m docservice && 
    mkdir -p /app /app/data /app/logs && 
    chown -R docservice:docservice /app /app/data /app/logs

WORKDIR /app

# Copy wheels and requirements from build stage
COPY --from=build /app/wheels /wheels
COPY --from=build /app/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir /wheels/* && 
    rm -rf /wheels && 
    rm -rf /root/.cache/pip/* && 
    apt-get update && 
    apt-get install -y --no-install-recommends curl && 
    apt-get clean && 
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY src/ /app/src/

# Set ownership of application files
RUN chown -R docservice:docservice /app

# Switch to non-root user
USER docservice

# Expose the application port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1 
    PYTHONDONTWRITEBYTECODE=1 
    PYTHONPATH=/app

# Health check for Kubernetes probes
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 
    CMD curl -f http://localhost:5000/health/liveness || exit 1

# Run the application with gunicorn
CMD ["python", "-m", "gunicorn", "src.main:app", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]