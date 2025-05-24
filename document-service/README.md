# Document Service

## Overview

The Document Service is a critical microservice component of the Merchant Cash Advance (MCA) Application Processing System. It is responsible for classifying incoming documents using AI-based algorithms, extracting document metadata, and routing documents to appropriate OCR processors for data extraction.

## Key Features

- AI-powered document classification using scikit-learn (SVM and Random Forest classifiers)
- High-accuracy document type detection (99% accuracy target)
- Confidence scoring for classification decisions
- Seamless integration with RabbitMQ message queue
- Secure document storage with S3-compatible storage
- Kubernetes-ready with health check endpoints
- Comprehensive logging and monitoring

## Architecture

The Document Service is implemented as a Python microservice that consumes document messages from RabbitMQ, processes them using machine learning models, and publishes classification results back to RabbitMQ for further processing by the OCR Service.

### Workflow

1. Email Service extracts documents from incoming emails and publishes them to RabbitMQ
2. Document Service consumes messages from the `document-processing` queue
3. Document Service downloads document content from S3-compatible storage
4. Document Service classifies documents using trained ML models
5. Document Service adds classification metadata and confidence scores
6. Document Service routes documents to appropriate OCR processors via RabbitMQ
7. OCR Service extracts data based on document classification

### Component Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Email Service │     │ Document Service │     │   OCR Service   │
│    (Node.js)    │────▶│    (Python)     │────▶│    (Python)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        RabbitMQ Message Queue                    │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     S3-Compatible Document Storage              │
└─────────────────────────────────────────────────────────────────┘
```

## Technical Requirements

### System Requirements

- Python 3.9+
- scikit-learn 1.4.1
- At least 16GB RAM for processing larger document batches
- CUDA-compatible GPU recommended for improved performance

### Dependencies

- scikit-learn 1.4.1: Machine learning library for document classification
- amqplib 0.10.3: RabbitMQ client for message queue integration
- @aws-sdk/client-s3 3.509.0: S3 client for document storage
- FastAPI: API framework for health checks and diagnostics
- Pydantic: Data validation and settings management
- Uvicorn: ASGI server for running the API

## Configuration

The Document Service is configured using environment variables. Below are the key configuration options:

### Application Configuration

| Environment Variable | Description | Default |
|----------------------|-------------|--------|
| `APP_ENV` | Application environment (development, staging, production) | `development` |
| `LOG_LEVEL` | Logging level (ERROR, WARN, INFO, DEBUG) | `INFO` |
| `SERVICE_PORT` | Port for the health check API | `8080` |

### RabbitMQ Configuration

| Environment Variable | Description | Default |
|----------------------|-------------|--------|
| `RABBITMQ_HOST` | RabbitMQ host | `localhost` |
| `RABBITMQ_PORT` | RabbitMQ port | `5672` |
| `RABBITMQ_USERNAME` | RabbitMQ username | `guest` |
| `RABBITMQ_PASSWORD` | RabbitMQ password | `guest` |
| `RABBITMQ_VHOST` | RabbitMQ virtual host | `/` |
| `RABBITMQ_EXCHANGE` | RabbitMQ exchange name | `mca.documents` |
| `RABBITMQ_QUEUE` | RabbitMQ queue name | `document-processing` |
| `RABBITMQ_ROUTING_KEY` | RabbitMQ routing key | `document.classify` |
| `RABBITMQ_USE_TLS` | Enable TLS for RabbitMQ connection | `true` |
| `RABBITMQ_CERT_PATH` | Path to client certificate for RabbitMQ | |
| `RABBITMQ_KEY_PATH` | Path to client key for RabbitMQ | |
| `RABBITMQ_CA_PATH` | Path to CA certificate for RabbitMQ | |

### S3 Storage Configuration

| Environment Variable | Description | Default |
|----------------------|-------------|--------|
| `S3_ENDPOINT` | S3-compatible storage endpoint | |
| `S3_REGION` | S3 region | `us-east-1` |
| `S3_ACCESS_KEY` | S3 access key | |
| `S3_SECRET_KEY` | S3 secret key | |
| `S3_BUCKET_NAME` | S3 bucket name | `mca-documents-development` |
| `S3_USE_SSL` | Enable SSL for S3 connection | `true` |
| `S3_ENCRYPTION` | Enable AES-256 encryption for documents | `true` |

### Model Configuration

| Environment Variable | Description | Default |
|----------------------|-------------|--------|
| `MODEL_PATH` | Path to trained classification models | `/app/models` |
| `CONFIDENCE_THRESHOLD` | Minimum confidence score for automatic routing | `0.85` |
| `FEATURE_COUNT` | Number of features to use for classification | `1500` |

## API Endpoints

The Document Service exposes the following API endpoints for health checks and diagnostics:

### Health Checks

- `GET /health/liveness`: Kubernetes liveness probe endpoint
- `GET /health/readiness`: Kubernetes readiness probe endpoint (checks RabbitMQ and S3 connections)

### Status and Metrics

- `GET /status`: Overall service status
- `GET /status/metrics`: Prometheus-compatible metrics endpoint

### Diagnostics

- `GET /diagnostics/logs`: Retrieve recent logs (requires authentication)
- `GET /diagnostics/config`: Check current configuration (requires authentication)
- `GET /diagnostics/test`: Run diagnostic tests (requires authentication)

## Local Development

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git

### Setup

1. Clone the repository:

```bash
git clone https://github.com/dollarfunding/mca-document-service.git
cd mca-document-service
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. Set up local environment variables:

```bash
cp .env.example .env
# Edit .env file with your local configuration
```

4. Start local dependencies using Docker Compose:

```bash
docker-compose up -d rabbitmq s3mock
```

5. Run the service:

```bash
python src/main.py
```

### Testing

The Document Service includes comprehensive unit and integration tests. To run the tests:

```bash
pytest
```

To run tests with coverage report:

```bash
pytest --cov=src tests/
```

To run specific test categories:

```bash
pytest tests/test_models/  # Run model tests only
pytest tests/test_services/  # Run service tests only
pytest tests/test_api/  # Run API tests only
```

## Deployment

### Docker

The Document Service can be deployed as a Docker container. A Dockerfile is provided in the repository.

To build the Docker image:

```bash
docker build -t mca-document-service:latest .
```

To run the Docker container:

```bash
docker run -p 8080:8080 --env-file .env mca-document-service:latest
```

### Kubernetes

The Document Service is designed to be deployed in a Kubernetes cluster. Helm charts are provided in the `/infrastructure/kubernetes/charts/document-service` directory.

To deploy using Helm:

```bash
helm upgrade --install document-service ./infrastructure/kubernetes/charts/document-service \
  --namespace mca --create-namespace \
  --set image.repository=mca-document-service \
  --set image.tag=latest \
  --values ./infrastructure/kubernetes/charts/document-service/values-production.yaml
```

#### Resource Requirements

The Document Service requires at least 16GB RAM for processing larger document batches. The recommended Kubernetes resource configuration is:

```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "1"
  limits:
    memory: "16Gi"
    cpu: "2"
```

## Troubleshooting

### Common Issues

#### RabbitMQ Connection Issues

- Verify RabbitMQ credentials and connection settings
- Check that TLS certificates are properly configured
- Ensure the RabbitMQ exchange and queue exist

#### S3 Storage Issues

- Verify S3 credentials and endpoint
- Check bucket permissions
- Ensure the service has proper IAM roles for S3 access

#### Classification Performance Issues

- Check model training data quality
- Verify model paths and versions
- Increase memory allocation for large document batches

### Logs

The Document Service logs to stdout/stderr in JSON format. Log levels can be configured using the `LOG_LEVEL` environment variable.

Example log output:

```json
{"timestamp": "2025-05-22T10:15:30.123Z", "level": "INFO", "message": "Document classified", "document_id": "doc-123", "document_type": "invoice", "confidence": 0.95}
```

## License

Copyright © 2025 Dollar Funding, Inc. All rights reserved.