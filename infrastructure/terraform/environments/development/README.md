# MCA Application Processing System - Development Environment

This directory contains the Terraform configuration for the development environment of the Merchant Cash Advance (MCA) Application Processing System. It provisions the necessary infrastructure components with settings optimized for local development and testing.

## Infrastructure Components

- **PostgreSQL 14**: Single instance database (no read replicas)
- **RabbitMQ**: Single-node message broker
- **Redis 7.0**: Single-node cache with separate instances for application data and user sessions
- **S3-compatible Storage**: Document repository with encryption

## Key Differences from Production/Staging

- **Simplified Architecture**: Single instances instead of clusters
- **Reduced Resources**: Smaller instance sizes and storage allocations
- **No High Availability**: Single AZ deployment without auto-failover
- **Simplified Monitoring**: Basic monitoring with less frequent metrics collection
- **Shorter Retention Periods**: Reduced backup and data retention periods

## Usage

### Prerequisites

- Terraform 1.0.0 or newer
- AWS CLI configured with appropriate credentials
- Access to the AWS account where development resources will be deployed

### Deployment

1. Initialize Terraform:
   ```
   terraform init
   ```

2. Review the execution plan:
   ```
   terraform plan
   ```

3. Apply the configuration:
   ```
   terraform apply
   ```

### Cleanup

To destroy all resources created by this configuration:

```
terraform destroy
```

## Configuration

The development environment is configured through the following files:

- **main.tf**: Main infrastructure configuration
- **variables.tf**: Variable definitions
- **terraform.tfvars**: Variable values specific to development
- **outputs.tf**: Output values exported from the configuration
- **backend.tf**: Terraform state configuration

## Security Considerations

Even though this is a development environment, security best practices are still followed:

- Encryption is enabled for data at rest and in transit
- No public access to resources
- Secure authentication for all services

## Notes

- The development environment is designed for local development and testing only
- It is not intended for processing real customer data
- Resource sizes are minimized to reduce costs
- For local development without AWS, consider using Docker Compose with the configuration in `/infrastructure/docker-compose`