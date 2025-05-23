# MCA Application Processing System - Kubernetes Infrastructure

## Overview

This directory contains the Kubernetes configuration for the Merchant Cash Advance (MCA) Application Processing System. The system is deployed as a set of microservices running in Kubernetes, with each service containerized according to the specifications in the technical documentation.

The Kubernetes infrastructure is designed to support the following key requirements:

- Automated email-based application processing with 93% reduction in manual processing
- Processing applications in under 5 minutes from receipt to completion
- 99% data extraction accuracy through AI and machine learning
- 99.9% system uptime across all environments

## Architecture

The MCA Application Processing System uses a microservices architecture deployed on Kubernetes with the following components:

### Microservices

| Service | Technology | Purpose | Resource Requirements |
|---------|------------|---------|----------------------|
| Email Service | Node.js/Nodemailer | Monitors submissions inbox using IMAP protocol | CPU: 0.5-1 cores, Memory: 512Mi-1Gi |
| Document Service | Python/scikit-learn | Classifies incoming documents with AI | CPU: 1-2 cores, Memory: 1-2Gi |
| OCR Service | Python/TensorFlow | Extracts data from documents (typed and handwritten) | CPU: 2-4 cores, GPU: 1, Memory: 2-4Gi |
| Data Service | Java/Spring Boot | Manages application data and business logic | CPU: 1-2 cores, Memory: 1-2Gi |
| Notification Service | Node.js | Handles alerts and webhooks | CPU: 0.5-1 cores, Memory: 512Mi-1Gi |
| API Gateway | Kong | Provides unified API access with security controls | CPU: 1-2 cores, Memory: 1-2Gi |

### Infrastructure Components

| Component | Purpose | Configuration |
|-----------|---------|---------------|
| PostgreSQL 14 | Primary database | Production: Primary + 2 read replicas<br>Staging: Primary + 1 read replica<br>Development: Single instance |
| RabbitMQ | Message queue system | Cluster with mirrored queues and message persistence |
| Redis 7.0 | Caching layer | Cluster with appropriate TTL settings |
| S3-compatible storage | Document repository | Buckets: 'mca-documents-production', 'mca-documents-staging' |

## Directory Structure

```
infrastructure/kubernetes/
├── charts/                  # Helm charts for application services
│   ├── common/              # Common templates used across all charts
│   │   ├── templates/       # Shared Kubernetes manifest templates
│   │   │   ├── deployment.yaml
│   │   │   ├── hpa.yaml
│   │   │   ├── ingress.yaml
│   │   │   ├── pvc.yaml
│   │   │   ├── service.yaml
│   │   │   └── serviceaccount.yaml
│   │   ├── Chart.yaml       # Chart metadata
│   │   └── values.yaml      # Default values for templates
│   ├── api-gateway/         # API Gateway service chart
│   ├── data-service/        # Data Service chart
│   ├── document-service/    # Document Service chart
│   ├── email-service/       # Email Service chart
│   ├── notification-service/# Notification Service chart
│   ├── ocr-service/         # OCR Service chart
│   ├── postgresql/          # PostgreSQL database chart
│   └── rabbitmq/            # RabbitMQ message queue chart
├── config/                  # Environment-specific configuration
│   ├── values-development.yaml  # Development environment values
│   ├── values-staging.yaml      # Staging environment values
│   └── values-production.yaml   # Production environment values
├── namespaces/              # Namespace definitions
│   ├── production-namespace.yaml  # Production namespace
│   ├── rbac.yaml                  # RBAC configuration
│   └── resource-quotas.yaml       # Resource quotas
├── infrastructure/          # Cluster-wide infrastructure
├── kustomization.yaml       # Root kustomization file
└── README.md                # This file
```

## Deployment Process

The MCA Application Processing System supports three deployment environments:

### Development Environment

The development environment is designed for local development and testing with minimal resource requirements:

```bash
# Deploy to development environment
kubectl apply -k overlays/development
```

Development environment characteristics:
- Single replica for each service
- Minimal resource allocations
- Debug mode and verbose logging enabled
- Local endpoints and connection strings
- No database read replicas

### Staging Environment

The staging environment is used for pre-production validation:

```bash
# Deploy to staging environment
kubectl apply -k overlays/staging
```

Staging environment characteristics:
- Moderate replica counts (2-3) for services
- PostgreSQL with 1 read replica
- 'mca-documents-staging' S3 bucket
- Staging-specific feature flags and monitoring

### Production Environment

The production environment is the live system with full redundancy:

```bash
# Deploy to production environment
kubectl apply -k overlays/production
```

Production environment characteristics:
- Higher replica counts (3-5) for high availability
- PostgreSQL with 2 read replicas
- 'mca-documents-production' S3 bucket
- Full monitoring and alerting
- GPU resources for OCR service

## Configuration Guidelines

### Resource Requirements

Each microservice has specific resource requirements that should be configured appropriately for each environment:

- **Email Service**: Monitors email inbox, requires moderate CPU and memory
- **Document Service**: Classifies documents, requires higher CPU and memory
- **OCR Service**: Performs OCR processing, requires GPU acceleration in production
- **Data Service**: Manages application data, requires moderate CPU and memory
- **Notification Service**: Handles webhooks, requires moderate CPU and memory
- **API Gateway**: Routes API requests, requires moderate CPU and memory

### Security Configuration

The Kubernetes deployment implements the following security measures:

- **RBAC**: Role-Based Access Control with two specific roles:
  - Operations Staff: Read all, write application data
  - System Admin: Full access to all endpoints and webhook configuration
- **Network Policies**: Isolation between services and namespaces
- **Secrets Management**: Secure storage of credentials and sensitive information
- **Container Security**: Non-root users, read-only filesystem, security contexts

### Monitoring and Observability

The Kubernetes deployment includes comprehensive monitoring and logging:

- **Metrics**: Application processing time, OCR accuracy, queue depth, API response time
- **Logging**: Structured logging with specified log levels (ERROR, WARN, INFO, DEBUG)
- **Alerting**: Alerts for critical system conditions

## Troubleshooting

### Common Issues

#### Pod Startup Failures

```bash
# Check pod status
kubectl get pods -n <namespace>

# View pod logs
kubectl logs <pod-name> -n <namespace>

# Describe pod for events
kubectl describe pod <pod-name> -n <namespace>
```

#### Resource Constraints

If pods are being evicted or failing to schedule due to resource constraints:

```bash
# Check node resource usage
kubectl top nodes

# Check pod resource usage
kubectl top pods -n <namespace>

# Check resource quotas
kubectl describe resourcequota -n <namespace>
```

#### Database Connectivity Issues

```bash
# Check PostgreSQL service
kubectl get svc postgresql -n <namespace>

# Check PostgreSQL pods
kubectl get pods -l app=postgresql -n <namespace>

# Check PostgreSQL logs
kubectl logs -l app=postgresql -n <namespace>
```

#### Message Queue Issues

```bash
# Check RabbitMQ service
kubectl get svc rabbitmq -n <namespace>

# Check RabbitMQ pods
kubectl get pods -l app=rabbitmq -n <namespace>

# Check RabbitMQ logs
kubectl logs -l app=rabbitmq -n <namespace>
```

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [PostgreSQL Kubernetes Operator](https://github.com/zalando/postgres-operator)
- [RabbitMQ Kubernetes Operator](https://www.rabbitmq.com/kubernetes/operator/operator-overview.html)
- [Redis Kubernetes Operator](https://github.com/spotahome/redis-operator)
- [Kong API Gateway](https://docs.konghq.com/gateway/latest/)

## Related Infrastructure Components

- **Terraform Configuration**: `/infrastructure/terraform/` - Infrastructure as Code for cloud resources
- **CI/CD Pipeline**: `/infrastructure/ci/` - Continuous Integration and Deployment pipeline
- **Monitoring**: Datadog configuration for metrics and alerts