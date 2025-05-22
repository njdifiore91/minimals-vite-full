# MCA Application Processing System - Kubernetes Configuration

## Overview

This directory contains the Kubernetes configuration for the Merchant Cash Advance (MCA) Application Processing System. The system is deployed as a set of microservices running in Kubernetes, with each service containerized according to the standards defined in the technical specification.

The Kubernetes configuration follows a GitOps approach, with all resources defined as code and managed through a combination of Helm charts and Kubernetes manifests. This ensures consistent deployment across environments and enables infrastructure validation as part of the CI/CD process.

## Architecture

The MCA Application Processing System consists of the following microservices:

1. **Email Service** (Node.js/Nodemailer): Monitors submissions inbox using IMAP protocol
2. **Document Service** (Python/scikit-learn): Classifies incoming documents with AI
3. **OCR Service** (Python/TensorFlow): Extracts data from documents (typed and handwritten)
4. **Data Service** (Java/Spring Boot): Manages application data and business logic
5. **Notification Service** (Node.js): Handles alerts and webhooks
6. **API Gateway** (Kong): Provides unified API access with security controls

These services are supported by the following infrastructure components:

- **PostgreSQL 14**: Primary database with read replicas
- **RabbitMQ**: Message queue system for service communication
- **Redis 7.0**: Caching layer
- **S3-compatible storage**: Document repository with encryption

### Component Relationships

```
Client (Frontend) --> API Gateway --> Data Service --> PostgreSQL/Redis
                                  --> Notification Service --> External Webhooks

Email Service --> RabbitMQ --> Document Service --> RabbitMQ --> OCR Service --> S3 Storage
                           --> Data Service
```

## Folder Structure

The Kubernetes configuration is organized as follows:

```
/infrastructure/kubernetes/
├── charts/                    # Helm charts for application services
│   ├── common/                # Common templates and helpers
│   ├── api-gateway/           # API Gateway service chart
│   ├── data-service/          # Data Service chart
│   ├── document-service/      # Document Service chart
│   ├── email-service/         # Email Service chart
│   ├── notification-service/  # Notification Service chart
│   ├── ocr-service/           # OCR Service chart
│   ├── postgresql/            # PostgreSQL database chart
│   ├── rabbitmq/              # RabbitMQ message queue chart
│   └── redis/                 # Redis cache chart
├── config/                    # Environment-specific configuration
│   ├── common-values.yaml     # Common values for all environments
│   ├── values-development.yaml # Development environment values
│   ├── values-staging.yaml    # Staging environment values
│   └── values-production.yaml # Production environment values
├── infrastructure/            # Cluster-wide infrastructure resources
├── namespaces/                # Namespace definitions and RBAC
│   ├── development-namespace.yaml # Development namespace
│   ├── staging-namespace.yaml    # Staging namespace
│   ├── production-namespace.yaml # Production namespace
│   ├── network-policies.yaml     # Network policies
│   ├── rbac.yaml                 # RBAC configuration
│   └── resource-quotas.yaml      # Resource quotas
└── kustomization.yaml        # Root kustomization file
```

## Deployment Environments

The system supports three deployment environments:

1. **Development**: Local development setup with minimal resources
2. **Staging**: Pre-production validation environment
3. **Production**: Live system with full redundancy

Each environment is isolated in its own Kubernetes namespace with appropriate resource quotas and network policies.

### Environment-Specific Configurations

Environment-specific configurations are managed through value files in the `/config` directory:

- `common-values.yaml`: Base configuration shared across all environments
- `values-development.yaml`: Development-specific overrides
- `values-staging.yaml`: Staging-specific overrides
- `values-production.yaml`: Production-specific overrides

## Resource Requirements

### Email Service

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit | Replicas |
|-------------|------------|-----------|----------------|--------------|----------|
| Development | 100m       | 200m      | 128Mi          | 256Mi        | 1        |
| Staging     | 200m       | 400m      | 256Mi          | 512Mi        | 2        |
| Production  | 400m       | 800m      | 512Mi          | 1Gi          | 3        |

### Document Service

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit | Replicas |
|-------------|------------|-----------|----------------|--------------|----------|
| Development | 200m       | 500m      | 512Mi          | 1Gi          | 1        |
| Staging     | 500m       | 1000m     | 1Gi            | 2Gi          | 2        |
| Production  | 1000m      | 2000m     | 2Gi            | 4Gi          | 3        |

### OCR Service

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit | GPU      | Replicas |
|-------------|------------|-----------|----------------|--------------|----------|----------|
| Development | 500m       | 1000m     | 1Gi            | 2Gi          | Optional | 1        |
| Staging     | 1000m      | 2000m     | 2Gi            | 4Gi          | 1        | 2        |
| Production  | 2000m      | 4000m     | 4Gi            | 8Gi          | 1        | 3        |

### Data Service

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit | Replicas |
|-------------|------------|-----------|----------------|--------------|----------|
| Development | 200m       | 500m      | 512Mi          | 1Gi          | 1        |
| Staging     | 500m       | 1000m     | 1Gi            | 2Gi          | 2-3      |
| Production  | 1000m      | 2000m     | 2Gi            | 4Gi          | 3-5      |

### Notification Service

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit | Replicas |
|-------------|------------|-----------|----------------|--------------|----------|
| Development | 100m       | 200m      | 128Mi          | 256Mi        | 1        |
| Staging     | 200m       | 400m      | 256Mi          | 512Mi        | 2        |
| Production  | 400m       | 800m      | 512Mi          | 1Gi          | 3        |

### API Gateway

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit | Replicas |
|-------------|------------|-----------|----------------|--------------|----------|
| Development | 200m       | 400m      | 256Mi          | 512Mi        | 1        |
| Staging     | 400m       | 800m      | 512Mi          | 1Gi          | 2        |
| Production  | 800m       | 1600m     | 1Gi            | 2Gi          | 3        |

### Infrastructure Components

#### PostgreSQL

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit | Storage | Read Replicas |
|-------------|------------|-----------|----------------|--------------|---------|---------------|
| Development | 500m       | 1000m     | 1Gi            | 2Gi          | 10Gi    | 0             |
| Staging     | 1000m      | 2000m     | 2Gi            | 4Gi          | 50Gi    | 1             |
| Production  | 2000m      | 4000m     | 4Gi            | 8Gi          | 100Gi   | 2             |

#### RabbitMQ

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit | Storage | Replicas |
|-------------|------------|-----------|----------------|--------------|---------|----------|
| Development | 200m       | 500m      | 512Mi          | 1Gi          | 5Gi     | 1        |
| Staging     | 500m       | 1000m     | 1Gi            | 2Gi          | 10Gi    | 3        |
| Production  | 1000m      | 2000m     | 2Gi            | 4Gi          | 20Gi    | 3        |

#### Redis

| Environment | CPU Request | CPU Limit | Memory Request | Memory Limit | Replicas |
|-------------|------------|-----------|----------------|--------------|----------|
| Development | 100m       | 200m      | 256Mi          | 512Mi        | 1        |
| Staging     | 200m       | 400m      | 512Mi          | 1Gi          | 3        |
| Production  | 400m       | 800m      | 1Gi            | 2Gi          | 3        |

## Deployment Process

### Prerequisites

- Kubernetes cluster (AKS, EKS, GKE, or on-premises)
- kubectl configured to access the cluster
- Helm 3.x installed
- Access to container registry with service images

### Deployment Steps

1. **Create Namespaces**

   ```bash
   kubectl apply -f namespaces/development-namespace.yaml  # For development
   kubectl apply -f namespaces/staging-namespace.yaml      # For staging
   kubectl apply -f namespaces/production-namespace.yaml   # For production
   ```

2. **Apply RBAC Configuration**

   ```bash
   kubectl apply -f namespaces/rbac.yaml
   ```

3. **Apply Resource Quotas**

   ```bash
   kubectl apply -f namespaces/resource-quotas.yaml
   ```

4. **Apply Network Policies**

   ```bash
   kubectl apply -f namespaces/network-policies.yaml
   ```

5. **Deploy Infrastructure Components**

   ```bash
   # For development environment
   helm install postgresql charts/postgresql -f config/common-values.yaml -f config/values-development.yaml -n mca-development
   helm install rabbitmq charts/rabbitmq -f config/common-values.yaml -f config/values-development.yaml -n mca-development
   helm install redis charts/redis -f config/common-values.yaml -f config/values-development.yaml -n mca-development
   ```

6. **Deploy Application Services**

   ```bash
   # For development environment
   helm install email-service charts/email-service -f config/common-values.yaml -f config/values-development.yaml -n mca-development
   helm install document-service charts/document-service -f config/common-values.yaml -f config/values-development.yaml -n mca-development
   helm install ocr-service charts/ocr-service -f config/common-values.yaml -f config/values-development.yaml -n mca-development
   helm install data-service charts/data-service -f config/common-values.yaml -f config/values-development.yaml -n mca-development
   helm install notification-service charts/notification-service -f config/common-values.yaml -f config/values-development.yaml -n mca-development
   helm install api-gateway charts/api-gateway -f config/common-values.yaml -f config/values-development.yaml -n mca-development
   ```

7. **Verify Deployment**

   ```bash
   kubectl get pods -n mca-development
   ```

### Automated Deployment

The deployment process is automated through CI/CD pipelines defined in `/infrastructure/ci/`. The pipelines use Helm and Kustomize to deploy the application to the appropriate environment based on Git branch or tag:

- **Feature branches**: Deploy to ephemeral feature environments
- **Development branch**: Deploy to development environment
- **Main branch**: Deploy to staging environment
- **Tags (v*.*.*)**: Deploy to production environment

## Configuration Guidelines

### Adding a New Service

1. Create a new Helm chart in the `/charts` directory
2. Add service-specific values to the common and environment-specific value files
3. Update network policies to allow communication with the new service
4. Add the service to the deployment pipeline

### Scaling Services

Services can be scaled horizontally by adjusting the replica count in the environment-specific value files:

```yaml
# Example: Scaling the data-service in production
data-service:
  replicaCount: 5  # Increase from 3 to 5
```

Vertical scaling can be achieved by adjusting the resource requests and limits:

```yaml
# Example: Increasing resources for the ocr-service in production
ocr-service:
  resources:
    requests:
      cpu: 3000m    # Increase from 2000m
      memory: 6Gi   # Increase from 4Gi
    limits:
      cpu: 6000m    # Increase from 4000m
      memory: 12Gi  # Increase from 8Gi
```

### Environment Variables

Environment variables for services are defined in the value files and injected into the containers through Kubernetes ConfigMaps and Secrets:

```yaml
# Example: Setting environment variables for the email-service
email-service:
  env:
    # ConfigMap values
    IMAP_HOST: "imap.dollarfunding.com"
    IMAP_PORT: "993"
    POLLING_INTERVAL: "60"
    # Secret values (referenced from Kubernetes Secrets)
    IMAP_USER:
      secretKeyRef:
        name: email-service-credentials
        key: username
    IMAP_PASSWORD:
      secretKeyRef:
        name: email-service-credentials
        key: password
```

## Troubleshooting

### Common Issues

#### Pods Stuck in Pending State

**Possible causes:**
- Insufficient cluster resources
- PersistentVolumeClaim not bound
- Node selector constraints not met

**Resolution:**
```bash
# Check pod status and events
kubectl describe pod <pod-name> -n <namespace>

# Check available resources
kubectl get nodes
kubectl describe node <node-name>

# Check PVC status
kubectl get pvc -n <namespace>
```

#### Service Communication Issues

**Possible causes:**
- Network policies blocking traffic
- Service endpoints not registered
- DNS resolution problems

**Resolution:**
```bash
# Check network policies
kubectl get networkpolicies -n <namespace>

# Check service endpoints
kubectl get endpoints <service-name> -n <namespace>

# Test DNS resolution from a pod
kubectl exec -it <pod-name> -n <namespace> -- nslookup <service-name>
```

#### Container Crashes or Restarts

**Possible causes:**
- Application errors
- Resource limits exceeded
- Liveness/readiness probe failures

**Resolution:**
```bash
# Check pod logs
kubectl logs <pod-name> -n <namespace>

# Check previous container logs if restarted
kubectl logs <pod-name> -n <namespace> --previous

# Check resource usage
kubectl top pod <pod-name> -n <namespace>
```

### Accessing Service Logs

```bash
# Tail logs for a specific service
kubectl logs -f deployment/<service-name> -n <namespace>

# Get logs for all pods in a deployment
kubectl logs -f -l app=<service-name> -n <namespace>
```

### Debugging Services

```bash
# Execute commands in a running container
kubectl exec -it <pod-name> -n <namespace> -- /bin/sh

# Port-forward to access a service locally
kubectl port-forward service/<service-name> <local-port>:<service-port> -n <namespace>
```

## References

### Related Infrastructure Components

- **PostgreSQL**: Primary database with read replicas
  - Production: Primary + 2 read replicas
  - Staging: Primary + 1 read replica
  - Development: Primary only

- **RabbitMQ**: Message queue system with the following exchanges and queues:
  - Exchange: 'mca.documents' (fanout)
  - Queue: 'document-processing'
  - Queue: 'data-extraction'
  - Queue: 'notification'

- **Redis**: Caching layer with the following TTL settings:
  - Application data: 15 minutes
  - User sessions: 24 hours

- **S3-Compatible Storage**: Document repository with the following buckets:
  - 'mca-documents-production'
  - 'mca-documents-staging'
  - AES-256 encryption for document storage

### Documentation Links

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Kustomize Documentation](https://kubectl.docs.kubernetes.io/guides/introduction/kustomize/)

### Internal References

- [Infrastructure as Code Repository](/infrastructure/terraform/)
- [CI/CD Pipeline Configuration](/infrastructure/ci/)
- [Monitoring and Observability Setup](/infrastructure/monitoring/)