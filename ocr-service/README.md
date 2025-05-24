# OCR Service

## Overview

The OCR Service is a Python-based microservice that extracts structured data from documents using TensorFlow machine learning models. It's a critical component of the Merchant Cash Advance (MCA) Application Processing System, responsible for extracting data from application documents with high accuracy.

This service processes documents received via RabbitMQ from the Document Service, extracts text and structured data using specialized OCR models, and publishes the results back to RabbitMQ for consumption by the Data Service. It supports both typed and handwritten text extraction with confidence scoring for each extracted field.

## Key Features

- **High-Accuracy Text Extraction**: Achieves 99% data extraction accuracy through specialized TensorFlow models
- **Document Type Support**: Processes typed, handwritten, and mixed-format documents
- **GPU-Accelerated Processing**: Utilizes CUDA-compatible GPUs for fast processing
- **Confidence Scoring**: Provides confidence scores for all extracted fields
- **Structured Data Extraction**: Extracts key-value pairs and tabular data with semantic understanding
- **Asynchronous Processing**: Integrates with RabbitMQ for scalable document processing
- **Secure Document Handling**: Works with S3-compatible storage using AES-256 encryption

## Architecture

The OCR Service is built as a Python microservice with the following components:

- **Core OCR Engine**: TensorFlow-based models for text extraction
- **Message Queue Client**: RabbitMQ integration for asynchronous processing
- **Storage Client**: S3-compatible storage integration for document access
- **API Layer**: FastAPI endpoints for health checks, monitoring, and diagnostics
- **Configuration System**: Environment-based configuration for different deployment scenarios

## Requirements

### Hardware Requirements

- **GPU**: CUDA-compatible GPU with at least 8GB VRAM
- **Memory**: Minimum 16GB RAM recommended
- **Storage**: 10GB for application and models

### Software Requirements

- **Python**: Version 3.9 or higher
- **TensorFlow**: Version 2.15.0
- **CUDA**: Compatible with TensorFlow 2.15.0 (typically CUDA 11.8)
- **cuDNN**: Compatible with TensorFlow 2.15.0 and CUDA version
- **Docker**: For containerized deployment

## Installation and Setup

### Local Development Setup

1. Clone the repository

```bash
git clone https://github.com/your-organization/ocr-service.git
cd ocr-service
```

2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Set up environment variables (see Configuration section)

5. Run the service

```bash
python src/main.py
```

### Docker Deployment

1. Build the Docker image

```bash
docker build -t ocr-service:latest .
```

2. Run the container

```bash
docker run -d --gpus all \
  --name ocr-service \
  -p 8080:8080 \
  -e RABBITMQ_HOST=rabbitmq \
  -e S3_ENDPOINT=s3-storage \
  -e ENVIRONMENT=production \
  ocr-service:latest
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Deployment environment (development, staging, production) | `development` | Yes |
| `LOG_LEVEL` | Logging level (ERROR, WARN, INFO, DEBUG) | `INFO` | No |
| `SERVICE_PORT` | Port for the API server | `8080` | No |
| `RABBITMQ_HOST` | RabbitMQ host | `localhost` | Yes |
| `RABBITMQ_PORT` | RabbitMQ port | `5672` | No |
| `RABBITMQ_USER` | RabbitMQ username | - | Yes |
| `RABBITMQ_PASSWORD` | RabbitMQ password | - | Yes |
| `RABBITMQ_VHOST` | RabbitMQ virtual host | `/` | No |
| `RABBITMQ_TLS_ENABLED` | Enable TLS for RabbitMQ | `true` | No |
| `RABBITMQ_CERT_PATH` | Path to client certificate for RabbitMQ | - | If TLS enabled |
| `S3_ENDPOINT` | S3-compatible storage endpoint | - | Yes |
| `S3_REGION` | S3 region | `us-east-1` | No |
| `S3_ACCESS_KEY` | S3 access key | - | Yes |
| `S3_SECRET_KEY` | S3 secret key | - | Yes |
| `S3_BUCKET` | S3 bucket name | Based on environment | Yes |
| `S3_ENCRYPTION_ENABLED` | Enable AES-256 encryption for S3 | `true` | No |
| `TF_GPU_MEMORY_LIMIT` | GPU memory limit in MB | `8192` | No |
| `TF_CONFIDENCE_THRESHOLD` | Minimum confidence threshold for extraction | `0.75` | No |

### Configuration Files

The service uses several configuration files located in the `src/config` directory:

- `app_config.py`: Core application configuration
- `rabbitmq_config.py`: RabbitMQ connection and queue settings
- `s3_config.py`: S3 storage configuration
- `tensorflow_config.py`: TensorFlow model and GPU settings
- `logging_config.py`: Logging configuration

## Usage

### API Endpoints

The service exposes the following API endpoints:

#### Health and Monitoring

- `GET /health/liveness`: Kubernetes liveness probe
- `GET /health/readiness`: Kubernetes readiness probe
- `GET /status`: Service status information
- `GET /status/metrics`: Prometheus-compatible metrics

#### Diagnostics

- `GET /diagnostics/logs`: Recent logs (requires authentication)
- `GET /diagnostics/config`: Current configuration (requires authentication)
- `GET /diagnostics/test`: Run diagnostic tests (requires authentication)
- `GET /diagnostics/models`: Check loaded models (requires authentication)
- `POST /diagnostics/models/reload`: Reload models (requires authentication)

#### OCR Operations

- `GET /ocr/{document_id}`: Get OCR results for a document
- `POST /ocr/{document_id}/process`: Manually trigger OCR processing
- `POST /ocr/batch`: Process multiple documents

### Message Queue Integration

The service integrates with RabbitMQ for asynchronous document processing:

#### Consuming Messages

The service consumes messages from the `data-extraction` queue, which should contain:

```json
{
  "document_id": "doc-123456",
  "document_type": "application_form",
  "storage_path": "applications/doc-123456.pdf",
  "correlation_id": "corr-789012",
  "metadata": {
    "merchant_id": "merch-345678",
    "application_id": "app-901234",
    "document_classification": "tax_return"
  }
}
```

#### Publishing Results

The service publishes extraction results to the `data.processing` queue:

```json
{
  "document_id": "doc-123456",
  "extraction_id": "ext-567890",
  "correlation_id": "corr-789012",
  "status": "completed",
  "processing_time_ms": 1250,
  "extracted_data": {
    "fields": [
      {
        "name": "business_name",
        "value": "Acme Corporation",
        "confidence": 0.98,
        "location": {
          "page": 1,
          "x": 120,
          "y": 240,
          "width": 300,
          "height": 30
        }
      },
      // Additional fields...
    ],
    "tables": [
      // Table data...
    ]
  },
  "metadata": {
    "document_type": "application_form",
    "model_version": "1.2.3",
    "confidence_score": 0.95
  }
}
```

## Development

### Project Structure

```
ocr-service/
├── src/
│   ├── api/              # API endpoints
│   ├── config/           # Configuration
│   ├── models/           # OCR models
│   ├── services/         # Core services
│   ├── types/            # Type definitions
│   ├── utils/            # Utility functions
│   ├── app.py            # Application setup
│   └── main.py           # Entry point
├── tests/                # Test suite
│   ├── test_data/        # Test documents
│   ├── test_api/         # API tests
│   ├── test_models/      # Model tests
│   └── test_services/    # Service tests
├── Dockerfile            # Docker configuration
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Testing

The service includes a comprehensive test suite using pytest:

```bash
# Run all tests
pytest

# Run unit tests only
pytest -m unit

# Run integration tests
pytest -m integration

# Run with coverage report
pytest --cov=src
```

## Troubleshooting

### Common Issues

#### GPU Not Detected

**Symptoms**: Service logs show "No GPU devices found" or falls back to CPU processing.

**Solutions**:
- Verify CUDA and cuDNN installation
- Check GPU drivers are properly installed
- Ensure Docker is configured with GPU support
- Verify the GPU has at least 8GB VRAM

#### RabbitMQ Connection Failures

**Symptoms**: Service logs show "Failed to connect to RabbitMQ" or "Connection refused".

**Solutions**:
- Verify RabbitMQ is running and accessible
- Check credentials and virtual host settings
- Ensure TLS certificates are properly configured if using TLS
- Check network connectivity and firewall settings

#### Low OCR Accuracy

**Symptoms**: Extracted data has many errors or low confidence scores.

**Solutions**:
- Check document quality and resolution
- Verify the correct model is being used for the document type
- Adjust confidence thresholds in configuration
- Consider retraining models with similar document samples

#### Memory Issues

**Symptoms**: Service crashes with "Out of memory" errors.

**Solutions**:
- Adjust `TF_GPU_MEMORY_LIMIT` to a lower value
- Increase system or container memory allocation
- Process fewer documents concurrently
- Check for memory leaks in custom code

## Contributing

Contributions to the OCR Service are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code passes all tests and includes appropriate documentation.