# Email Service

## Overview

The Email Service is a critical component of the Merchant Cash Advance (MCA) Application Processing System, serving as the primary entry point for document processing. It continuously monitors configured email inboxes, extracts mortgage application documents, and ingests them into the MCA processing pipeline, ensuring reliable and secure document capture from external sources.

### Key Responsibilities

- Monitor the submissions@dollarfunding.com inbox via IMAP protocol
- Extract email metadata and attachments
- Validate and scan attachments for security threats
- Store documents in S3-compatible storage with encryption
- Publish document messages to RabbitMQ for further processing
- Maintain stateful tracking of processed emails to prevent duplicates

## Architecture

The Email Service is built as a Node.js microservice using TypeScript for type safety. It follows a modular architecture with clear separation of concerns:

### Core Components

- **Email Monitor**: Connects to IMAP servers and polls for new emails
- **Attachment Processor**: Extracts and validates email attachments
- **Virus Scanner**: Scans attachments for security threats
- **Storage Service**: Stores attachments in S3-compatible storage
- **Message Queue Service**: Publishes messages to RabbitMQ

### Workflow

The Email Monitoring & Ingestion workflow operates as a continuous process:

1. Service initializes and establishes connections to configured IMAP servers
2. Service enters a polling loop, checking for new emails at configured intervals (typically 1-5 minutes)
3. When a new email is detected, attachments are extracted and validated
4. Attachments are scanned for viruses; infected files are quarantined
5. Valid attachments are stored in S3-compatible storage with encryption
6. Document metadata and storage location are published to RabbitMQ
7. Email is marked as processed to prevent reprocessing
8. Service continues monitoring for new emails

```
Email Inbox → Email Service → Virus Scan → S3 Storage → RabbitMQ → Document Service
```

### Integration with Other Services

The Email Service integrates with several other components in the MCA system:

- **Document Service**: Receives document messages from RabbitMQ for classification
- **S3-compatible Storage**: Stores email attachments with encryption
- **RabbitMQ**: Facilitates asynchronous communication between services

## Configuration

The Email Service is configured using environment variables, making it suitable for containerized deployment.

### Environment Variables

#### IMAP Configuration

```
IMAP_SERVER=mail.dollarfunding.com
IMAP_PORT=993
IMAP_USER=submissions@dollarfunding.com
IMAP_PASSWORD=your-secure-password
IMAP_TLS_ENABLED=true
IMAP_POLL_INTERVAL=300000  # 5 minutes in milliseconds
IMAP_MAILBOX=INBOX
```

#### RabbitMQ Configuration

```
RABBITMQ_HOST=rabbitmq.dollarfunding.com
RABBITMQ_PORT=5671
RABBITMQ_USER=email-service
RABBITMQ_PASSWORD=your-secure-password
RABBITMQ_VHOST=mca
RABBITMQ_EXCHANGE=mca.documents
RABBITMQ_ROUTING_KEY=document.new
RABBITMQ_TLS_ENABLED=true
RABBITMQ_CERT_PATH=/path/to/client/certificate
RABBITMQ_KEY_PATH=/path/to/client/key
RABBITMQ_CA_PATH=/path/to/ca/certificate
```

#### S3 Storage Configuration

```
S3_ENDPOINT=s3.dollarfunding.com
S3_REGION=us-east-1
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET=mca-documents-production
S3_ENCRYPTION_ENABLED=true
S3_TLS_ENABLED=true
```

#### Application Configuration

```
NODE_ENV=production
LOG_LEVEL=info
SERVICE_PORT=3000
HEALTH_CHECK_PATH=/health
MAX_ATTACHMENT_SIZE=25000000  # 25MB in bytes
ALLOWED_FILE_TYPES=application/pdf,image/tiff,image/png,image/jpeg
```

### Security Considerations

The Email Service implements several security measures to protect sensitive data:

1. **TLS Encryption**: All IMAP connections enforce TLS 1.2+ with certificate validation
2. **Virus Scanning**: All attachments are scanned for viruses before processing
3. **Document Encryption**: AES-256 encryption is used for document storage
4. **Secure Credentials**: Sensitive credentials are managed securely and rotated regularly
5. **TLS for RabbitMQ**: All RabbitMQ connections use TLS with client certificate authentication

## Deployment

### Prerequisites

- Node.js v18.x LTS
- Access to IMAP email server
- RabbitMQ cluster
- S3-compatible storage (AWS S3 or MinIO)
- Docker (for containerized deployment)
- Kubernetes (for orchestrated deployment)

### Docker Deployment

A Dockerfile is provided for containerized deployment:

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY dist/ ./dist/

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

Build and run the Docker image:

```bash
# Build the image
docker build -t email-service:latest .

# Run the container
docker run -d \
  --name email-service \
  -p 3000:3000 \
  --env-file .env \
  email-service:latest
```

### Kubernetes Deployment

A sample Kubernetes deployment manifest is provided in the `infrastructure/kubernetes/charts/email-service/templates/` directory. The service can be deployed using Helm:

```bash
helm upgrade --install email-service ./infrastructure/kubernetes/charts/email-service \
  --namespace mca \
  --values ./infrastructure/kubernetes/charts/email-service/values-production.yaml
```

### Health Checks

The Email Service exposes a health check endpoint at `/health` that returns the service status. This endpoint can be used for Kubernetes liveness and readiness probes:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Development

### Local Setup

1. Clone the repository
2. Install dependencies: `npm install`
3. Create a `.env.local` file with required environment variables
4. Start the service in development mode: `npm run dev`

### Building

```bash
# Build the service
npm run build

# Run the built service
node dist/index.js
```

### Testing

```bash
# Run unit tests
npm test

# Run integration tests
npm run test:integration

# Run all tests with coverage
npm run test:coverage
```

## Troubleshooting

### Common Issues

#### IMAP Connection Failures

- Verify IMAP server address and port
- Check credentials and permissions
- Ensure TLS settings are correct
- Check network connectivity and firewall rules

#### RabbitMQ Connection Issues

- Verify RabbitMQ server address and port
- Check credentials and vhost permissions
- Ensure TLS certificates are valid and accessible
- Verify exchange and queue configurations

#### Document Processing Failures

- Check attachment size limits
- Verify allowed file types
- Ensure S3 storage is accessible
- Check virus scanner configuration

### Logging

The Email Service uses structured logging with the following levels:

- **ERROR**: Processing failures and critical issues
- **WARN**: Potential issues that don't prevent processing
- **INFO**: Normal operations and status updates
- **DEBUG**: Detailed information for troubleshooting (development only)

Logs are output to stdout/stderr in JSON format for easy integration with log aggregation systems like ELK Stack or Datadog.

### Monitoring

The Email Service exposes metrics for monitoring:

- Email processing rate and latency
- Attachment extraction success/failure rates
- Queue publishing success/failure rates
- Storage operation success/failure rates
- Virus detection rates

These metrics can be collected using Prometheus and visualized with Grafana.

## License

Copyright © 2025 Dollar Funding, Inc. All rights reserved.