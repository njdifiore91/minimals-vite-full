# Email Service

## Overview

The Email Service is a Node.js microservice responsible for monitoring email inboxes for incoming Merchant Cash Advance (MCA) applications, extracting documents, and initiating the document processing pipeline. It serves as the primary entry point for document ingestion in the MCA Application Processing System.

### Key Features

- Secure IMAP connection to monitor submission inboxes
- Automatic email filtering and attachment extraction
- Virus scanning for all attachments
- Document validation and metadata extraction
- Secure storage of documents in S3-compatible storage
- Message publishing to RabbitMQ for downstream processing
- Comprehensive logging and error handling
- Retry mechanisms for resilient operation

## Architecture

The Email Service is built using Node.js v18.x LTS with TypeScript for type safety. It uses the following key libraries:

- **nodemailer** (v6.9.8): For email processing with TLS enforcement
- **imap-simple** (v6.0.0): For IMAP access with TLS required
- **amqplib** (v0.10.3): For RabbitMQ messaging with TLS enforcement
- **@aws-sdk/client-s3**: For S3-compatible storage integration

### Email Monitoring Workflow

The service implements the following workflow:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  IMAP Server    │────▶│  Email Service  │────▶│  RabbitMQ       │
│  (Submissions)  │     │                 │     │  (mca.documents) │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                          │
                               │                          │
                               ▼                          ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │                 │     │                 │
                        │  S3 Storage     │     │  Document       │
                        │  (Documents)    │     │  Service        │
                        │                 │     │                 │
                        └─────────────────┘     └─────────────────┘
```

1. **Email Monitoring**: The service connects to the configured IMAP server and polls for new emails at regular intervals.
2. **Email Filtering**: Emails are filtered based on configurable rules (sender domains, subject patterns).
3. **Attachment Extraction**: Attachments are extracted from emails and validated for supported document types.
4. **Virus Scanning**: All attachments are scanned for viruses before processing.
5. **Document Storage**: Valid attachments are stored in S3-compatible storage with AES-256 encryption.
6. **Message Publishing**: Document metadata and storage location are published to RabbitMQ for further processing.
7. **Email Marking**: Processed emails are marked to prevent reprocessing.

## Setup and Configuration

### Prerequisites

- Node.js v18.x LTS or higher
- Access to an IMAP email server
- RabbitMQ server with TLS support
- S3-compatible storage service
- Docker (for containerized deployment)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd email-service

# Install dependencies
npm install

# Build the service
npm run build

# Start the service
npm start
```

### Configuration

The service is configured using environment variables. Create a `.env` file based on the provided `.env.example` template:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the configuration
nano .env
```

## Integration with Other Services

### RabbitMQ Integration

The Email Service publishes messages to the `mca.documents` exchange in RabbitMQ with the routing key `document.new`. The message payload includes:

- Document binary location in S3
- File type and metadata
- Sender information
- Subject line
- Received timestamp
- Email message ID
- Attachment metadata

Example message format:

```json
{
  "documentId": "doc-123456",
  "storageLocation": "s3://mca-documents-production/2025/05/21/doc-123456.pdf",
  "fileType": "application/pdf",
  "fileName": "business_application.pdf",
  "fileSize": 1024567,
  "metadata": {
    "sender": "applicant@example.com",
    "recipient": "submissions@dollarfunding.com",
    "subject": "Business Funding Application",
    "receivedAt": "2025-05-21T14:30:45.123Z",
    "messageId": "<message-id-123456@mail.example.com>"
  }
}
```

### S3 Storage Integration

The Email Service stores documents in S3-compatible storage with the following configuration:

- Bucket: `mca-documents-production` or `mca-documents-staging` (environment-dependent)
- Path format: `YYYY/MM/DD/document-id.extension`
- Encryption: AES-256 for data at rest
- TLS: Required for data in transit

## Security Considerations

### IMAP Security

- TLS 1.2+ is enforced for all IMAP connections
- Certificate validation is mandatory
- STARTTLS connections are rejected to prevent downgrade attacks
- Credentials are stored securely in environment variables

### RabbitMQ Security

- TLS 1.3 is enforced for all RabbitMQ connections
- Client certificate authentication is used
- Service-specific users and virtual hosts maintain connection isolation
- Credentials are stored in secure environment-specific vaults

### Document Security

- All attachments are scanned for viruses before processing
- Malicious files are quarantined and administrators are notified
- Document metadata is stripped to remove potentially sensitive information
- AES-256 encryption is used for document storage

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `NODE_ENV` | Environment (development, staging, production) | `development` | Yes |
| `LOG_LEVEL` | Logging level (error, warn, info, debug) | `info` | No |
| `IMAP_HOST` | IMAP server hostname | - | Yes |
| `IMAP_PORT` | IMAP server port | `993` | No |
| `IMAP_USER` | IMAP username | - | Yes |
| `IMAP_PASSWORD` | IMAP password | - | Yes |
| `IMAP_TLS` | Enforce TLS for IMAP | `true` | No |
| `IMAP_REJECT_UNAUTHORIZED` | Reject unauthorized certificates | `true` | No |
| `IMAP_MAILBOX` | Mailbox to monitor | `INBOX` | No |
| `IMAP_POLL_INTERVAL` | Polling interval in milliseconds | `60000` | No |
| `RABBITMQ_HOST` | RabbitMQ hostname | - | Yes |
| `RABBITMQ_PORT` | RabbitMQ port | `5671` | No |
| `RABBITMQ_USER` | RabbitMQ username | - | Yes |
| `RABBITMQ_PASSWORD` | RabbitMQ password | - | Yes |
| `RABBITMQ_VHOST` | RabbitMQ virtual host | `/` | No |
| `RABBITMQ_EXCHANGE` | RabbitMQ exchange name | `mca.documents` | No |
| `RABBITMQ_ROUTING_KEY` | RabbitMQ routing key | `document.new` | No |
| `RABBITMQ_TLS` | Enforce TLS for RabbitMQ | `true` | No |
| `RABBITMQ_CERT_PATH` | Path to client certificate | - | No |
| `RABBITMQ_KEY_PATH` | Path to client key | - | No |
| `RABBITMQ_CA_PATH` | Path to CA certificate | - | No |
| `S3_ENDPOINT` | S3 endpoint URL | - | Yes |
| `S3_REGION` | S3 region | `us-east-1` | No |
| `S3_ACCESS_KEY` | S3 access key | - | Yes |
| `S3_SECRET_KEY` | S3 secret key | - | Yes |
| `S3_BUCKET` | S3 bucket name | - | Yes |
| `S3_USE_SSL` | Use SSL for S3 connections | `true` | No |
| `VIRUS_SCAN_ENABLED` | Enable virus scanning | `true` | No |
| `VIRUS_SCAN_HOST` | Virus scanner hostname | `localhost` | No |
| `VIRUS_SCAN_PORT` | Virus scanner port | `3310` | No |
| `MAX_ATTACHMENT_SIZE` | Maximum attachment size in bytes | `10485760` | No |
| `ALLOWED_FILE_TYPES` | Comma-separated list of allowed file types | `pdf,tiff,png,jpeg,jpg` | No |

## Deployment

### Docker Deployment

The service includes a Dockerfile for containerized deployment:

```bash
# Build the Docker image
docker build -t email-service .

# Run the container
docker run -d --name email-service \
  --env-file .env \
  -p 3000:3000 \
  email-service
```

### Kubernetes Deployment

The service can be deployed to Kubernetes using the provided Helm chart:

```bash
# Deploy using Helm
helm upgrade --install email-service \
  ./infrastructure/kubernetes/charts/email-service \
  --namespace mca-system \
  --values ./infrastructure/kubernetes/charts/email-service/values-production.yaml
```

## Monitoring and Logging

The Email Service implements comprehensive logging with the following log levels:

- **ERROR**: Processing failures and critical issues
- **WARN**: Potential issues that don't prevent operation
- **INFO**: Normal operations and status updates
- **DEBUG**: Detailed information for troubleshooting (development only)

Logs include timestamp, service name, and context information for effective troubleshooting.

## Troubleshooting

### Common Issues

#### IMAP Connection Failures

- Verify IMAP server hostname and port
- Check credentials and permissions
- Ensure TLS settings are correct
- Verify network connectivity and firewall rules

#### RabbitMQ Connection Issues

- Verify RabbitMQ server hostname and port
- Check credentials and permissions
- Ensure TLS settings and certificates are correct
- Verify exchange and queue existence

#### S3 Storage Problems

- Verify S3 endpoint and credentials
- Check bucket existence and permissions
- Ensure TLS settings are correct
- Verify network connectivity

#### Document Processing Errors

- Check allowed file types configuration
- Verify virus scanner configuration
- Check attachment size limits
- Review logs for specific error messages

### Diagnostic Commands

```bash
# Check service status
docker ps | grep email-service

# View logs
docker logs email-service

# Check IMAP connectivity
nc -zv $IMAP_HOST $IMAP_PORT

# Check RabbitMQ connectivity
nc -zv $RABBITMQ_HOST $RABBITMQ_PORT

# Check S3 connectivity
aws s3 ls s3://$S3_BUCKET --endpoint-url $S3_ENDPOINT
```

## License

[Proprietary] - Dollar Funding, Inc.