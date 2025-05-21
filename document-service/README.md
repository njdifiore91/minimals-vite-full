# Document Service

## Overview

The Document Service is a critical microservice in the Merchant Cash Advance (MCA) Application Processing System. It is responsible for classifying incoming documents using AI-based algorithms, extracting document metadata, and routing documents to appropriate OCR processors based on their classification.

### Key Features

- **AI-Based Document Classification**: Uses scikit-learn models (SVM, Random Forest) to classify documents with 99% accuracy
- **RabbitMQ Integration**: Consumes document messages from RabbitMQ and publishes classification results
- **S3 Storage**: Securely stores documents with AES-256 encryption
- **Intelligent Routing**: Routes documents to specialized OCR processors based on document type
- **Health Monitoring**: Provides comprehensive health check endpoints for Kubernetes
- **Confidence Scoring**: Includes confidence metrics for classification decisions

## Architecture

The Document Service is implemented as a Python microservice using scikit-learn for machine learning capabilities. It follows a modular architecture with clear separation of concerns:

```
document-service/
├── src/
│   ├── api/                 # FastAPI endpoints
│   ├── config/              # Configuration modules
│   ├── models/              # Classification models
│   ├── services/            # Core services
│   ├── types/               # Type definitions
│   ├── utils/               # Utility functions
│   ├── app.py               # Application setup
│   └── main.py              # Entry point
├── tests/                   # Test suite
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

### Document Classification Workflow

1. **Message Consumption**: Service consumes document messages from the `document-processing` queue in RabbitMQ
2. **Document Retrieval**: Documents are retrieved from S3-compatible storage
3. **Preprocessing**: Documents are preprocessed to normalize format, size, and orientation
4. **Feature Extraction**: Features are extracted from documents for classification
5. **Classification**: Documents are classified using ensemble methods (SVM, Random Forest)
6. **Confidence Scoring**: Classification results include confidence scores
7. **Document Routing**: Documents are routed to appropriate OCR processors based on classification
8. **Result Publishing**: Classification results are published to the OCR Service via RabbitMQ

## Requirements

### System Requirements

- Python 3.9+
- 16GB RAM minimum (for processing larger document batches)
- Access to RabbitMQ cluster
- Access to S3-compatible storage
- GPU acceleration (optional, for improved performance)

### Dependencies

- scikit-learn 1.4.1: Machine learning library for document classification
- FastAPI: API framework for health checks and diagnostics
- pika: RabbitMQ client for message queue integration
- boto3: AWS SDK for S3 storage integration
- pydantic: Data validation and settings management
- uvicorn: ASGI server for FastAPI
- python-dotenv: Environment variable management
- loguru: Structured logging

## Configuration

The Document Service is configured using environment variables. These can be provided directly or through a `.env` file in development environments.

### Core Configuration

```env
# Application settings
APP_NAME=document-service
APP_VERSION=1.0.0
LOG_LEVEL=INFO  # ERROR, WARN, INFO, DEBUG
PORT=8000

# Environment
ENVIRONMENT=production  # development, staging, production
```

### RabbitMQ Configuration

```env
# RabbitMQ connection
RABBITMQ_HOST=rabbitmq.example.com
RABBITMQ_PORT=5671
RABBITMQ_VHOST=/mca
RABBITMQ_USERNAME=document-service
RABBITMQ_PASSWORD=your-secure-password
RABBITMQ_USE_TLS=true
RABBITMQ_CLIENT_CERT=/path/to/client.cert
RABBITMQ_CLIENT_KEY=/path/to/client.key

# RabbitMQ exchanges and queues
RABBITMQ_EXCHANGE=mca.documents
RABBITMQ_QUEUE=document-processing
RABBITMQ_ROUTING_KEY=document.new
RABBITMQ_OUTPUT_ROUTING_KEY=document.classified
```

### S3 Storage Configuration

```env
# S3 connection
S3_ENDPOINT=s3.example.com
S3_REGION=us-east-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_USE_SSL=true

# S3 buckets
S3_BUCKET_PRODUCTION=mca-documents-production
S3_BUCKET_STAGING=mca-documents-staging
```

### Model Configuration

```env
# Classification models
MODEL_PATH=/app/models
MODEL_VERSION=1.0.0
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.75
```

## API Endpoints

The Document Service exposes several API endpoints for health monitoring, diagnostics, and document operations.

### Health Endpoints

- `GET /health/liveness`: Kubernetes liveness probe
- `GET /health/readiness`: Kubernetes readiness probe (checks RabbitMQ and S3 connections)

### Status Endpoints

- `GET /status`: Overall service status
- `GET /status/metrics`: Prometheus-compatible metrics

### Diagnostic Endpoints

- `GET /diagnostics/logs`: Recent logs (requires authentication)
- `GET /diagnostics/config`: Current configuration (requires authentication)
- `GET /diagnostics/test`: Run diagnostic tests (requires authentication)

### Document Endpoints

- `GET /documents/{document_id}`: Get document classification status
- `POST /documents/{document_id}/classify`: Manually trigger classification
- `POST /documents/batch`: Batch classification operations

## Deployment

### Local Development

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file with required configuration
6. Run the service: `python -m src.main`

### Docker Deployment

```bash
# Build the Docker image
docker build -t document-service:latest .

# Run the container
docker run -p 8000:8000 --env-file .env document-service:latest
```

### Kubernetes Deployment

The Document Service is designed to be deployed in Kubernetes using the provided Helm chart.

```bash
# Deploy using Helm
helm upgrade --install document-service ./infrastructure/kubernetes/charts/document-service \
  --namespace mca \
  --values ./infrastructure/kubernetes/charts/document-service/values-production.yaml
```

## Resource Requirements

The Document Service requires the following resources for optimal performance:

### Development Environment

- CPU: 2 cores
- Memory: 8GB
- Storage: 10GB

### Production Environment

- CPU: 4 cores
- Memory: 16GB (minimum)
- Storage: 20GB
- GPU: Optional, for improved performance

## Monitoring

The Document Service exposes Prometheus-compatible metrics at the `/status/metrics` endpoint. These metrics include:

- Document processing throughput
- Classification accuracy
- Queue depth
- Processing time
- Error rates
- Resource usage (CPU, memory)

These metrics can be collected by Prometheus and visualized in Datadog or Grafana dashboards.

## Troubleshooting

### Common Issues

1. **RabbitMQ Connection Failures**
   - Check RabbitMQ credentials and connection parameters
   - Verify TLS certificates are valid and accessible
   - Ensure the RabbitMQ server is running and accessible

2. **S3 Storage Access Issues**
   - Verify S3 credentials and bucket permissions
   - Check network connectivity to the S3 endpoint
   - Ensure the correct bucket is configured for the environment

3. **Classification Performance Issues**
   - Check if the service has sufficient memory (16GB minimum recommended)
   - Verify model files are correctly loaded
   - Monitor classification confidence scores for potential model drift

### Logs

The Document Service uses structured logging with the following levels:

- `ERROR`: Processing failures
- `WARN`: Potential issues
- `INFO`: Normal operations
- `DEBUG`: Troubleshooting (development only)

Logs can be accessed via the `/diagnostics/logs` endpoint (requires authentication) or through the container logs.

## License

Copyright © 2025 Dollar Funding, Inc. All rights reserved.