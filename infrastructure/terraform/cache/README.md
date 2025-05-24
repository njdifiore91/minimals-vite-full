# Redis Cache Infrastructure

This directory contains Terraform configuration for the Redis 7.0 caching infrastructure used by the MCA Application Processing System. The infrastructure provides distributed caching and session management capabilities with high availability and performance optimizations.

## Features

- **Redis 7.0 Cluster**: Configured with environment-specific settings for development, staging, and production
- **Dual-Purpose Caching**:
  - Application data cache with 15-minute TTL and allkeys-lru eviction policy
  - User session cache with 24-hour TTL and noeviction policy
- **Memory Optimization**: Memory tiering with SSD persistence for cost-effective caching
- **High Availability**: Multi-AZ deployment with automatic failover (15-second failover time)
- **Security**: TLS encryption for transit and AES-256 encryption at rest
- **Monitoring**: CloudWatch alarms for CPU and memory utilization

## Usage

### Prerequisites

- Terraform 1.0 or later
- AWS credentials configured
- Network infrastructure already deployed

### Deployment

```bash
# Initialize Terraform
terraform init -backend-config="bucket=your-state-bucket" -backend-config="region=us-east-1"

# Plan the deployment
terraform plan -var="environment=development" -var="state_bucket=your-state-bucket"

# Apply the configuration
terraform apply -var="environment=development" -var="state_bucket=your-state-bucket"
```

### Environment-Specific Configurations

The Redis infrastructure is configured differently based on the environment:

| Configuration | Development | Staging | Production |
|---------------|-------------|---------|------------|
| Node Type | cache.t3.small | cache.t3.medium | cache.m5.large |
| Memory Size | 1 GB | 2 GB | 4 GB |
| Shard Count | 1 | 2 | 3 |
| Replica Count | 0 | 1 | 1 |
| Multi-AZ | No | Yes | Yes |

## Integration

The Redis cache infrastructure is used by various microservices in the MCA Application Processing System:

- **Data Service**: Uses Redis for caching database query results
- **API Gateway**: Uses Redis for rate limiting and request caching
- **Authentication**: Uses Redis for session management
- **Document Service**: Uses Redis for caching document metadata

## Monitoring

The Redis infrastructure includes CloudWatch alarms for:

- CPU utilization (threshold: 75%)
- Memory utilization (threshold: 80%)

## TTL Settings

- **Application Data**: 15 minutes (900 seconds)
- **User Sessions**: 24 hours (86400 seconds)

## Security

- TLS encryption for all Redis connections
- AES-256 encryption for data at rest
- VPC security groups limiting access to authorized services
- No direct public access to Redis instances

## Maintenance

Maintenance windows are configured to minimize impact on operations:

- **Cache Instance**: Sunday 05:00-06:00 UTC
- **Session Instance**: Sunday 07:00-08:00 UTC