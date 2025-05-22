# MCA Application Processing System - Terraform Infrastructure

This directory contains Terraform configurations for provisioning the infrastructure required by the MCA Application Processing System. The infrastructure is designed to support a microservices architecture with high availability, scalability, and security.

## Infrastructure Components

- **PostgreSQL 14**: Primary database with read replicas for scalability and high availability
- **RabbitMQ**: Message queue system for service communication
- **Redis 7.0**: Caching layer for improved performance
- **S3-compatible Storage**: Document repository with encryption
- **Kubernetes Cluster**: Container orchestration platform for microservices
- **Monitoring**: Comprehensive monitoring and logging solution

## Directory Structure

```
terraform/
├── main.tf                 # Main Terraform configuration
├── variables.tf            # Variable definitions
├── terraform.tfvars.example # Example variable values
├── README.md               # This file
├── modules/                # Reusable Terraform modules
│   ├── database/           # PostgreSQL database module
│   ├── messaging/          # RabbitMQ messaging module
│   ├── cache/              # Redis cache module
│   ├── storage/            # S3 storage module
│   ├── network/            # VPC and networking module
│   ├── kubernetes/         # Kubernetes cluster module
│   ├── monitoring/         # Monitoring and logging module
│   └── security/           # Security and IAM module
├── environments/           # Environment-specific configurations
│   ├── development/        # Development environment
│   ├── staging/            # Staging environment
│   └── production/         # Production environment
├── global/                 # Global resources
└── state/                  # State management configuration
```

## Usage

### Prerequisites

- Terraform v1.0.0 or newer
- AWS CLI configured with appropriate credentials
- kubectl for Kubernetes interaction

### Setup

1. Copy the example variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

2. Edit `terraform.tfvars` with your specific values.

3. Initialize Terraform:

```bash
terraform init -backend-config=environments/<environment>/backend.tfvars
```

4. Plan the deployment:

```bash
terraform plan -var-file=environments/<environment>/terraform.tfvars
```

5. Apply the configuration:

```bash
terraform apply -var-file=environments/<environment>/terraform.tfvars
```

### Environment Promotion

The infrastructure supports a promotion flow from development to staging to production. Each environment has its own configuration in the `environments/` directory.

## Module Documentation

### Database Module

Provisions a PostgreSQL 14 database with the following features:
- Primary database with multiple read replicas
- Multi-AZ deployment for high availability
- Automated backups with configurable retention period
- Encryption at rest and in transit

### Messaging Module

Sets up a RabbitMQ cluster for asynchronous messaging between services:
- Cluster mode with configurable node count
- Message persistence for reliability
- TLS encryption for secure communication

### Cache Module

Deploys a Redis 7.0 cluster for caching and session management:
- Cluster mode with replicas for high availability
- Configurable node type and count
- Encryption and authentication

### Storage Module

Creates S3-compatible storage for document repository:
- AES-256 encryption for all objects
- Versioning for document history
- Lifecycle rules for cost optimization

### Network Module

Establishes the VPC and networking components:
- Multi-AZ deployment for high availability
- Public and private subnets
- NAT gateways for outbound connectivity
- Security groups for access control

### Kubernetes Module

Provisions an EKS cluster for container orchestration:
- Managed node groups with auto-scaling
- GPU-enabled nodes for OCR processing
- RBAC for access control

### Monitoring Module

Sets up monitoring and logging infrastructure:
- CloudWatch for logs and metrics
- Prometheus and Grafana for visualization
- Alerting for critical events

### Security Module

Implements security controls and IAM policies:
- IAM roles and policies for service accounts
- KMS for encryption key management
- Security groups for network access control

## Cost Optimization

The infrastructure is designed with cost optimization in mind:
- Auto-scaling to match resource usage with demand
- Lifecycle policies for S3 storage to transition infrequently accessed data
- Right-sized instances based on workload requirements
- Resource tagging for cost allocation and tracking

## Security Considerations

- All sensitive data is encrypted at rest and in transit
- IAM roles follow the principle of least privilege
- Network access is restricted through security groups
- Kubernetes RBAC controls access to cluster resources

## Maintenance and Updates

- Regular updates to Kubernetes version
- Security patches for all components
- Backup and restore procedures for data protection
- Disaster recovery planning

## Troubleshooting

Common issues and their solutions:

1. **Terraform state lock**: If a previous Terraform operation was interrupted, you may need to release the state lock:

```bash
terraform force-unlock <LOCK_ID>
```

2. **AWS credential issues**: Ensure your AWS credentials are properly configured:

```bash
aws configure
```

3. **Kubernetes connectivity**: After cluster creation, configure kubectl:

```bash
aws eks update-kubeconfig --name mca-<environment> --region <region>
```