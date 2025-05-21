# OCR Service

## Overview

The OCR Service is a specialized microservice within the Merchant Cash Advance (MCA) Application Processing System that extracts structured data from documents using advanced machine learning models. It processes documents from various sources, including loan applications, tax returns, bank statements, and identity documents, extracting key information with high accuracy to enable automated application processing.

### Key Features

- High-accuracy text extraction from both typed and handwritten documents
- Specialized models for different document types and formats
- GPU-accelerated processing for optimal performance
- Confidence scoring for all extracted fields
- Structured JSON output with standardized schemas
- Integration with RabbitMQ for asynchronous processing
- S3-compatible storage for document access and result storage

## Architecture

The OCR Service is built as a Python microservice using TensorFlow for text recognition. It integrates with the following components:

- **RabbitMQ**: Consumes document processing requests and publishes extraction results
- **S3-compatible Storage**: Accesses documents and stores extraction results
- **TensorFlow**: Powers the OCR models with GPU acceleration
- **FastAPI**: Provides health check and diagnostic endpoints

### Processing Pipeline

1. Consumes document messages from the `data-extraction` queue
2. Downloads documents from S3-compatible storage
3. Selects appropriate OCR model based on document type
4. Extracts text and structured data using TensorFlow models
5. Calculates confidence scores for all extracted fields
6. Formats results in standardized JSON structure
7. Publishes results to the Data Service via RabbitMQ
8. Stores extraction results in S3-compatible storage

## Requirements

### System Requirements

- Python 3.9+
- TensorFlow 2.15.0
- CUDA-compatible GPU with at least 8GB VRAM
- CUDA Toolkit 11.8+ and cuDNN 8.6+
- Docker and Docker Compose (for containerized deployment)
- 16GB+ RAM for processing larger document batches

### Dependencies

- TensorFlow 2.15.0: OCR model framework
- FastAPI: API framework for health checks and diagnostics
- Pydantic: Data validation and settings management
- Pillow: Image processing
- PyTorch (optional): Additional model support
- boto3: S3 client for document storage
- pika: RabbitMQ client
- uvicorn: ASGI server
- python-multipart: File upload support
- python-dotenv: Environment variable management

## Setup

### Local Development

1. Clone the repository

```bash
git clone https://github.com/your-org/mca-application-processing.git
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

4. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the service

```bash
python src/main.py
```

### Docker Deployment

1. Build the Docker image

```bash
docker build -t ocr-service .
```

2. Run the container

```bash
docker run -d --gpus all -p 8000:8000 --env-file .env --name ocr-service ocr-service
```

### Kubernetes Deployment

The service can be deployed to Kubernetes using the provided Helm chart:

```bash
cd infrastructure/kubernetes/charts/ocr-service
helm install ocr-service . -f values-dev.yaml
```

## Configuration

The OCR Service is configured using environment variables. Create a `.env` file based on the `.env.example` template.

### Core Settings

| Variable | Description | Default |
|----------|-------------|--------|
| `OCR_SERVICE_NAME` | Service name for logging and metrics | `ocr-service` |
| `OCR_SERVICE_VERSION` | Service version | `1.0.0` |
| `OCR_SERVICE_PORT` | HTTP port for health checks | `8000` |
| `OCR_LOG_LEVEL` | Logging level (ERROR, WARN, INFO, DEBUG) | `INFO` |
| `OCR_ENVIRONMENT` | Deployment environment (development, staging, production) | `development` |

### RabbitMQ Configuration

| Variable | Description | Default |
|----------|-------------|--------|
| `RABBITMQ_HOST` | RabbitMQ host | `localhost` |
| `RABBITMQ_PORT` | RabbitMQ port | `5672` |
| `RABBITMQ_USERNAME` | RabbitMQ username | `guest` |
| `RABBITMQ_PASSWORD` | RabbitMQ password | `guest` |
| `RABBITMQ_VHOST` | RabbitMQ virtual host | `/` |
| `RABBITMQ_EXCHANGE` | RabbitMQ exchange name | `mca.documents` |
| `RABBITMQ_QUEUE` | RabbitMQ queue name | `data-extraction` |
| `RABBITMQ_USE_TLS` | Enable TLS for RabbitMQ connection | `false` |
| `RABBITMQ_CERT_PATH` | Path to client certificate for TLS | `` |
| `RABBITMQ_KEY_PATH` | Path to client key for TLS | `` |
| `RABBITMQ_CA_PATH` | Path to CA certificate for TLS | `` |

### S3 Storage Configuration

| Variable | Description | Default |
|----------|-------------|--------|
| `S3_ENDPOINT` | S3-compatible storage endpoint | `http://localhost:9000` |
| `S3_ACCESS_KEY` | S3 access key | `minioadmin` |
| `S3_SECRET_KEY` | S3 secret key | `minioadmin` |
| `S3_REGION` | S3 region | `us-east-1` |
| `S3_BUCKET` | S3 bucket name | `mca-documents-development` |
| `S3_USE_SSL` | Enable SSL for S3 connection | `true` |
| `S3_VERIFY_SSL` | Verify SSL certificates | `true` |

### TensorFlow Configuration

| Variable | Description | Default |
|----------|-------------|--------|
| `TF_ENABLE_GPU` | Enable GPU acceleration | `true` |
| `TF_GPU_MEMORY_LIMIT` | GPU memory limit in MB | `4096` |
| `TF_MODELS_PATH` | Path to TensorFlow models | `models/` |
| `TF_CONFIDENCE_THRESHOLD` | Minimum confidence threshold for automation | `0.85` |
| `TF_INTER_OP_PARALLELISM` | TensorFlow inter-op parallelism threads | `4` |
| `TF_INTRA_OP_PARALLELISM` | TensorFlow intra-op parallelism threads | `4` |

## API Endpoints

The OCR Service exposes the following HTTP endpoints for health checks, monitoring, and diagnostics:

### Health Checks

- `GET /health/liveness`: Kubernetes liveness probe
- `GET /health/readiness`: Kubernetes readiness probe (checks RabbitMQ, S3, and GPU)

### Status and Metrics

- `GET /status`: Overall service status
- `GET /status/metrics`: Prometheus-compatible metrics

### Diagnostics

- `GET /diagnostics/logs`: Recent logs (requires authentication)
- `GET /diagnostics/config`: Current configuration (requires authentication)
- `GET /diagnostics/test`: Run diagnostic tests (requires authentication)
- `GET /diagnostics/models`: Check loaded OCR models (requires authentication)
- `POST /diagnostics/models/reload`: Reload OCR models (requires authentication)

### OCR Operations

- `GET /ocr/{document_id}`: Get OCR results for a document
- `POST /ocr/{document_id}/process`: Manually trigger OCR processing
- `POST /ocr/batch`: Batch processing operations

## Message Formats

### Input Message (from Document Service)

```json
{
  "document_id": "doc-123456",
  "correlation_id": "corr-789012",
  "application_id": "app-345678",
  "document_type": "BANK_STATEMENT",
  "document_path": "applications/app-345678/bank_statement.pdf",
  "classification": {
    "type": "BANK_STATEMENT",
    "confidence": 0.98,
    "metadata": {
      "bank_name": "First National Bank",
      "statement_date": "2023-01-15"
    }
  },
  "timestamp": "2023-01-20T14:30:45.123Z"
}
```

### Output Message (to Data Service)

```json
{
  "document_id": "doc-123456",
  "correlation_id": "corr-789012",
  "application_id": "app-345678",
  "document_type": "BANK_STATEMENT",
  "document_path": "applications/app-345678/bank_statement.pdf",
  "extraction_result": {
    "status": "SUCCESS",
    "extracted_data": {
      "account_number": {
        "value": "123456789",
        "confidence": 0.97,
        "location": {
          "page": 1,
          "x": 450,
          "y": 120,
          "width": 100,
          "height": 20
        }
      },
      "account_holder": {
        "value": "ACME Corporation",
        "confidence": 0.95,
        "location": {
          "page": 1,
          "x": 150,
          "y": 120,
          "width": 200,
          "height": 20
        }
      },
      "statement_date": {
        "value": "2023-01-15",
        "confidence": 0.99,
        "location": {
          "page": 1,
          "x": 500,
          "y": 80,
          "width": 80,
          "height": 20
        }
      },
      "ending_balance": {
        "value": "45678.90",
        "confidence": 0.96,
        "location": {
          "page": 1,
          "x": 500,
          "y": 400,
          "width": 100,
          "height": 20
        }
      },
      "transactions": {
        "value": [
          {
            "date": "2023-01-05",
            "description": "Deposit",
            "amount": "12000.00",
            "type": "credit"
          },
          {
            "date": "2023-01-10",
            "description": "Withdrawal",
            "amount": "5000.00",
            "type": "debit"
          }
        ],
        "confidence": 0.92,
        "location": {
          "page": 1,
          "x": 50,
          "y": 200,
          "width": 500,
          "height": 150
        }
      }
    },
    "processing_time_ms": 1250,
    "model_version": "bank_statement_v2.1",
    "overall_confidence": 0.95
  },
  "timestamp": "2023-01-20T14:30:48.456Z"
}
```

## GPU Configuration

The OCR Service requires a CUDA-compatible GPU with at least 8GB VRAM for optimal performance. The service automatically detects available GPUs and configures TensorFlow accordingly.

### GPU Requirements

- NVIDIA GPU with CUDA support (Tesla T4, V100, A100, or equivalent)
- CUDA Toolkit 11.8 or higher
- cuDNN 8.6 or higher
- Minimum 8GB VRAM (16GB+ recommended for production)

### Docker GPU Configuration

To enable GPU support in Docker, install the NVIDIA Container Toolkit and run the container with GPU access:

```bash
# Install NVIDIA Container Toolkit
curl -s -L https://nvidia.github.io/nvidia-container-runtime/gpgkey | \
  sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-container-runtime/$distribution/nvidia-container-runtime.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-runtime.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Run container with GPU access
docker run -d --gpus all -p 8000:8000 --env-file .env --name ocr-service ocr-service
```

### Kubernetes GPU Configuration

To enable GPU support in Kubernetes, install the NVIDIA Device Plugin and configure the deployment to request GPU resources:

```yaml
# values.yaml for Helm chart
resources:
  limits:
    nvidia.com/gpu: 1
  requests:
    nvidia.com/gpu: 1
```

## Troubleshooting

### Common Issues

#### GPU Not Detected

**Symptoms**: Service logs show "No GPU devices found" or "Running on CPU only"

**Solutions**:
- Verify CUDA installation: `nvidia-smi`
- Check TensorFlow GPU support: `python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"`
- Ensure NVIDIA drivers are installed and up-to-date
- Check Docker GPU configuration if running in container

#### RabbitMQ Connection Issues

**Symptoms**: Service logs show "Failed to connect to RabbitMQ" or "Connection refused"

**Solutions**:
- Verify RabbitMQ is running: `rabbitmqctl status`
- Check connection parameters in .env file
- Ensure network connectivity between service and RabbitMQ
- Verify TLS certificates if using TLS

#### S3 Storage Access Issues

**Symptoms**: Service logs show "Access denied" or "Failed to download document"

**Solutions**:
- Verify S3 credentials in .env file
- Check bucket permissions
- Ensure network connectivity to S3 endpoint
- Verify SSL configuration if using HTTPS

#### Low OCR Accuracy

**Symptoms**: Extracted data has many errors or low confidence scores

**Solutions**:
- Check document quality and resolution
- Verify appropriate model is being selected for document type
- Adjust preprocessing parameters for image enhancement
- Consider retraining models with similar document samples

### Logging

The OCR Service uses structured logging with configurable levels. Logs are output to stdout/stderr in JSON format for easy integration with log aggregation systems.

To change the log level, set the `OCR_LOG_LEVEL` environment variable to one of:
- `ERROR`: Only log errors and critical issues
- `WARN`: Log warnings and errors
- `INFO`: Log normal operations (default)
- `DEBUG`: Log detailed information for troubleshooting

### Monitoring

The service exposes Prometheus-compatible metrics at the `/status/metrics` endpoint. Key metrics include:

- `ocr_documents_processed_total`: Total number of documents processed
- `ocr_processing_time_seconds`: Document processing time histogram
- `ocr_extraction_confidence`: Confidence score histogram
- `ocr_queue_depth`: Current RabbitMQ queue depth
- `ocr_gpu_utilization`: GPU utilization percentage
- `ocr_memory_usage`: Memory usage metrics

## Examples

### Processing a Document Manually

To manually trigger OCR processing for a document:

```bash
curl -X POST "http://localhost:8000/ocr/doc-123456/process" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"document_path": "applications/app-345678/bank_statement.pdf", "document_type": "BANK_STATEMENT"}'  
```

### Retrieving OCR Results

To retrieve OCR results for a processed document:

```bash
curl -X GET "http://localhost:8000/ocr/doc-123456" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Checking Service Health

To check if the service is healthy and ready to process documents:

```bash
curl -X GET "http://localhost:8000/health/readiness"
```

## License

This project is licensed under the [License Name] - see the LICENSE file for details.

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.