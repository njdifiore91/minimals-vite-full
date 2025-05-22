#!/bin/bash

# ======================================================================
# MCA Application Processing System - Environment Setup Script
# ======================================================================
# This script configures environment variables and settings for CI/CD
# pipelines based on the target environment (development, staging, production).
# It sets up cloud provider credentials, configures Kubernetes context,
# and establishes environment-specific variables needed by other scripts
# and pipeline steps.
# ======================================================================

set -e

# ======================================================================
# Environment Detection and Validation
# ======================================================================

ENVIRONMENT=${1:-development}

# Validate environment parameter
if [[ "$ENVIRONMENT" != "development" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo "Error: Invalid environment specified: $ENVIRONMENT"
    echo "Usage: $0 [development|staging|production]"
    exit 1
fi

echo "Setting up environment for: $ENVIRONMENT"

# ======================================================================
# Cloud Provider Configuration
# ======================================================================

# Detect cloud provider from environment variable or use default
CLOUD_PROVIDER=${CLOUD_PROVIDER:-aws}

if [[ "$CLOUD_PROVIDER" != "aws" && "$CLOUD_PROVIDER" != "azure" && "$CLOUD_PROVIDER" != "gcp" ]]; then
    echo "Error: Unsupported cloud provider: $CLOUD_PROVIDER"
    echo "Supported providers: aws, azure, gcp"
    exit 1
fi

echo "Configuring for cloud provider: $CLOUD_PROVIDER"

# Configure cloud provider credentials based on environment
case $CLOUD_PROVIDER in
    aws)
        # AWS credentials configuration
        if [[ -z "$AWS_ACCESS_KEY_ID" || -z "$AWS_SECRET_ACCESS_KEY" ]]; then
            echo "Error: AWS credentials not found in environment variables"
            exit 1
        fi
        
        # Set AWS region based on environment
        case $ENVIRONMENT in
            development)
                export AWS_REGION=${AWS_REGION:-us-west-2}
                ;;
            staging)
                export AWS_REGION=${AWS_REGION:-us-west-2}
                ;;
            production)
                export AWS_REGION=${AWS_REGION:-us-east-1}
                # Use multi-region for production
                export AWS_SECONDARY_REGION=${AWS_SECONDARY_REGION:-us-west-2}
                ;;
        esac
        
        echo "AWS region set to: $AWS_REGION"
        ;;
        
    azure)
        # Azure credentials configuration
        if [[ -z "$AZURE_CLIENT_ID" || -z "$AZURE_CLIENT_SECRET" || -z "$AZURE_TENANT_ID" ]]; then
            echo "Error: Azure credentials not found in environment variables"
            exit 1
        fi
        
        # Set Azure region based on environment
        case $ENVIRONMENT in
            development)
                export AZURE_REGION=${AZURE_REGION:-westus2}
                ;;
            staging)
                export AZURE_REGION=${AZURE_REGION:-westus2}
                ;;
            production)
                export AZURE_REGION=${AZURE_REGION:-eastus}
                # Use multi-region for production
                export AZURE_SECONDARY_REGION=${AZURE_SECONDARY_REGION:-westus2}
                ;;
        esac
        
        echo "Azure region set to: $AZURE_REGION"
        ;;
        
    gcp)
        # GCP credentials configuration
        if [[ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
            echo "Error: GCP credentials not found in environment variables"
            exit 1
        fi
        
        # Set GCP region based on environment
        case $ENVIRONMENT in
            development)
                export GCP_REGION=${GCP_REGION:-us-west1}
                ;;
            staging)
                export GCP_REGION=${GCP_REGION:-us-west1}
                ;;
            production)
                export GCP_REGION=${GCP_REGION:-us-east1}
                # Use multi-region for production
                export GCP_SECONDARY_REGION=${GCP_SECONDARY_REGION:-us-west1}
                ;;
        esac
        
        echo "GCP region set to: $GCP_REGION"
        ;;
        
esac

# ======================================================================
# Kubernetes Context Configuration
# ======================================================================

# Set Kubernetes context based on environment and cloud provider
case $CLOUD_PROVIDER in
    aws)
        # Configure EKS context
        case $ENVIRONMENT in
            development)
                export K8S_CLUSTER_NAME=${K8S_CLUSTER_NAME:-mca-dev-cluster}
                export K8S_NAMESPACE=${K8S_NAMESPACE:-mca-dev}
                ;;
            staging)
                export K8S_CLUSTER_NAME=${K8S_CLUSTER_NAME:-mca-staging-cluster}
                export K8S_NAMESPACE=${K8S_NAMESPACE:-mca-staging}
                ;;
            production)
                export K8S_CLUSTER_NAME=${K8S_CLUSTER_NAME:-mca-prod-cluster}
                export K8S_NAMESPACE=${K8S_NAMESPACE:-mca-prod}
                ;;
        esac
        
        # Update kubeconfig for EKS
        echo "Updating kubeconfig for EKS cluster: $K8S_CLUSTER_NAME"
        aws eks update-kubeconfig --name $K8S_CLUSTER_NAME --region $AWS_REGION
        ;;
        
    azure)
        # Configure AKS context
        case $ENVIRONMENT in
            development)
                export K8S_CLUSTER_NAME=${K8S_CLUSTER_NAME:-mca-dev-cluster}
                export K8S_RESOURCE_GROUP=${K8S_RESOURCE_GROUP:-mca-dev-rg}
                export K8S_NAMESPACE=${K8S_NAMESPACE:-mca-dev}
                ;;
            staging)
                export K8S_CLUSTER_NAME=${K8S_CLUSTER_NAME:-mca-staging-cluster}
                export K8S_RESOURCE_GROUP=${K8S_RESOURCE_GROUP:-mca-staging-rg}
                export K8S_NAMESPACE=${K8S_NAMESPACE:-mca-staging}
                ;;
            production)
                export K8S_CLUSTER_NAME=${K8S_CLUSTER_NAME:-mca-prod-cluster}
                export K8S_RESOURCE_GROUP=${K8S_RESOURCE_GROUP:-mca-prod-rg}
                export K8S_NAMESPACE=${K8S_NAMESPACE:-mca-prod}
                ;;
        esac
        
        # Update kubeconfig for AKS
        echo "Updating kubeconfig for AKS cluster: $K8S_CLUSTER_NAME"
        az aks get-credentials --resource-group $K8S_RESOURCE_GROUP --name $K8S_CLUSTER_NAME
        ;;
        
    gcp)
        # Configure GKE context
        case $ENVIRONMENT in
            development)
                export K8S_CLUSTER_NAME=${K8S_CLUSTER_NAME:-mca-dev-cluster}
                export K8S_ZONE=${K8S_ZONE:-$GCP_REGION-a}
                export K8S_NAMESPACE=${K8S_NAMESPACE:-mca-dev}
                ;;
            staging)
                export K8S_CLUSTER_NAME=${K8S_CLUSTER_NAME:-mca-staging-cluster}
                export K8S_ZONE=${K8S_ZONE:-$GCP_REGION-a}
                export K8S_NAMESPACE=${K8S_NAMESPACE:-mca-staging}
                ;;
            production)
                export K8S_CLUSTER_NAME=${K8S_CLUSTER_NAME:-mca-prod-cluster}
                export K8S_ZONE=${K8S_ZONE:-$GCP_REGION-a}
                export K8S_NAMESPACE=${K8S_NAMESPACE:-mca-prod}
                ;;
        esac
        
        # Update kubeconfig for GKE
        echo "Updating kubeconfig for GKE cluster: $K8S_CLUSTER_NAME"
        gcloud container clusters get-credentials $K8S_CLUSTER_NAME --zone $K8S_ZONE
        ;;
        
esac

# Ensure namespace exists
echo "Ensuring namespace exists: $K8S_NAMESPACE"
kubectl create namespace $K8S_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Set current namespace
kubectl config set-context --current --namespace=$K8S_NAMESPACE

# ======================================================================
# Environment-Specific Variables
# ======================================================================

# Set environment-specific variables for services
case $ENVIRONMENT in
    development)
        # Development environment settings
        export REPLICA_COUNT_DEFAULT=1
        export REPLICA_COUNT_API_GATEWAY=1
        export REPLICA_COUNT_DATA_SERVICE=1
        export REPLICA_COUNT_EMAIL_SERVICE=1
        export REPLICA_COUNT_DOCUMENT_SERVICE=1
        export REPLICA_COUNT_OCR_SERVICE=1
        export REPLICA_COUNT_NOTIFICATION_SERVICE=1
        
        # Resource limits for development
        export CPU_REQUEST="100m"
        export CPU_LIMIT="500m"
        export MEMORY_REQUEST="256Mi"
        export MEMORY_LIMIT="512Mi"
        export OCR_GPU_ENABLED="false"
        
        # Logging level for development
        export LOG_LEVEL="DEBUG"
        
        # Feature flags for development
        export FEATURE_EMAIL_PROCESSING="true"
        export FEATURE_DOCUMENT_CLASSIFICATION="true"
        export FEATURE_OCR_PROCESSING="true"
        export FEATURE_WEBHOOK_DELIVERY="true"
        
        # S3 bucket for development
        export S3_BUCKET="mca-documents-development"
        ;;
        
    staging)
        # Staging environment settings
        export REPLICA_COUNT_DEFAULT=2
        export REPLICA_COUNT_API_GATEWAY=2
        export REPLICA_COUNT_DATA_SERVICE=2
        export REPLICA_COUNT_EMAIL_SERVICE=2
        export REPLICA_COUNT_DOCUMENT_SERVICE=2
        export REPLICA_COUNT_OCR_SERVICE=2
        export REPLICA_COUNT_NOTIFICATION_SERVICE=2
        
        # Resource limits for staging
        export CPU_REQUEST="250m"
        export CPU_LIMIT="1000m"
        export MEMORY_REQUEST="512Mi"
        export MEMORY_LIMIT="1Gi"
        export OCR_GPU_ENABLED="true"
        
        # Logging level for staging
        export LOG_LEVEL="INFO"
        
        # Feature flags for staging
        export FEATURE_EMAIL_PROCESSING="true"
        export FEATURE_DOCUMENT_CLASSIFICATION="true"
        export FEATURE_OCR_PROCESSING="true"
        export FEATURE_WEBHOOK_DELIVERY="true"
        
        # S3 bucket for staging
        export S3_BUCKET="mca-documents-staging"
        ;;
        
    production)
        # Production environment settings
        export REPLICA_COUNT_DEFAULT=3
        export REPLICA_COUNT_API_GATEWAY=3
        export REPLICA_COUNT_DATA_SERVICE=5
        export REPLICA_COUNT_EMAIL_SERVICE=3
        export REPLICA_COUNT_DOCUMENT_SERVICE=3
        export REPLICA_COUNT_OCR_SERVICE=5
        export REPLICA_COUNT_NOTIFICATION_SERVICE=3
        
        # Resource limits for production
        export CPU_REQUEST="500m"
        export CPU_LIMIT="2000m"
        export MEMORY_REQUEST="1Gi"
        export MEMORY_LIMIT="2Gi"
        export OCR_GPU_ENABLED="true"
        
        # Logging level for production
        export LOG_LEVEL="INFO"
        
        # Feature flags for production
        export FEATURE_EMAIL_PROCESSING="true"
        export FEATURE_DOCUMENT_CLASSIFICATION="true"
        export FEATURE_OCR_PROCESSING="true"
        export FEATURE_WEBHOOK_DELIVERY="true"
        
        # S3 bucket for production
        export S3_BUCKET="mca-documents-production"
        ;;
        
esac

# ======================================================================
# Database Configuration
# ======================================================================

# Set database configuration based on environment
case $ENVIRONMENT in
    development)
        # Development database settings
        export DB_HOST="postgres-postgresql.mca-dev"
        export DB_PORT="5432"
        export DB_NAME="mca_dev"
        export DB_USER="mca_user"
        export DB_SSL_MODE="disable"
        export DB_CONNECTION_POOL_MIN="5"
        export DB_CONNECTION_POOL_MAX="20"
        export DB_READ_REPLICA_COUNT="0"
        ;;
        
    staging)
        # Staging database settings
        export DB_HOST="postgres-postgresql.mca-staging"
        export DB_PORT="5432"
        export DB_NAME="mca_staging"
        export DB_USER="mca_user"
        export DB_SSL_MODE="require"
        export DB_CONNECTION_POOL_MIN="10"
        export DB_CONNECTION_POOL_MAX="30"
        export DB_READ_REPLICA_COUNT="1"
        export DB_READ_REPLICA_HOST="postgres-postgresql-read.mca-staging"
        ;;
        
    production)
        # Production database settings
        export DB_HOST="postgres-postgresql.mca-prod"
        export DB_PORT="5432"
        export DB_NAME="mca_prod"
        export DB_USER="mca_user"
        export DB_SSL_MODE="verify-full"
        export DB_CONNECTION_POOL_MIN="10"
        export DB_CONNECTION_POOL_MAX="50"
        export DB_READ_REPLICA_COUNT="2"
        export DB_READ_REPLICA_HOST="postgres-postgresql-read.mca-prod"
        ;;
        
esac

# ======================================================================
# Redis Cache Configuration
# ======================================================================

# Set Redis configuration based on environment
case $ENVIRONMENT in
    development)
        # Development Redis settings
        export REDIS_HOST="redis-master.mca-dev"
        export REDIS_PORT="6379"
        export REDIS_DATA_TTL="900"  # 15 minutes in seconds
        export REDIS_SESSION_TTL="86400"  # 24 hours in seconds
        ;;
        
    staging)
        # Staging Redis settings
        export REDIS_HOST="redis-master.mca-staging"
        export REDIS_PORT="6379"
        export REDIS_DATA_TTL="900"  # 15 minutes in seconds
        export REDIS_SESSION_TTL="86400"  # 24 hours in seconds
        ;;
        
    production)
        # Production Redis settings
        export REDIS_HOST="redis-master.mca-prod"
        export REDIS_PORT="6379"
        export REDIS_DATA_TTL="900"  # 15 minutes in seconds
        export REDIS_SESSION_TTL="86400"  # 24 hours in seconds
        ;;
        
esac

# ======================================================================
# RabbitMQ Configuration
# ======================================================================

# Set RabbitMQ configuration based on environment
case $ENVIRONMENT in
    development)
        # Development RabbitMQ settings
        export RABBITMQ_HOST="rabbitmq.mca-dev"
        export RABBITMQ_PORT="5672"
        export RABBITMQ_VHOST="/"
        export RABBITMQ_EXCHANGE="mca.documents"
        export RABBITMQ_QUEUE_DOCUMENT_PROCESSING="document-processing"
        export RABBITMQ_QUEUE_DATA_EXTRACTION="data-extraction"
        export RABBITMQ_QUEUE_NOTIFICATION="notification"
        ;;
        
    staging)
        # Staging RabbitMQ settings
        export RABBITMQ_HOST="rabbitmq.mca-staging"
        export RABBITMQ_PORT="5672"
        export RABBITMQ_VHOST="/"
        export RABBITMQ_EXCHANGE="mca.documents"
        export RABBITMQ_QUEUE_DOCUMENT_PROCESSING="document-processing"
        export RABBITMQ_QUEUE_DATA_EXTRACTION="data-extraction"
        export RABBITMQ_QUEUE_NOTIFICATION="notification"
        ;;
        
    production)
        # Production RabbitMQ settings
        export RABBITMQ_HOST="rabbitmq.mca-prod"
        export RABBITMQ_PORT="5672"
        export RABBITMQ_VHOST="/"
        export RABBITMQ_EXCHANGE="mca.documents"
        export RABBITMQ_QUEUE_DOCUMENT_PROCESSING="document-processing"
        export RABBITMQ_QUEUE_DATA_EXTRACTION="data-extraction"
        export RABBITMQ_QUEUE_NOTIFICATION="notification"
        ;;
        
esac

# ======================================================================
# Email Service Configuration
# ======================================================================

# Set Email Service configuration based on environment
case $ENVIRONMENT in
    development)
        # Development Email settings
        export EMAIL_IMAP_HOST="imap.example.com"
        export EMAIL_IMAP_PORT="993"
        export EMAIL_IMAP_SECURE="true"
        export EMAIL_INBOX="INBOX"
        export EMAIL_POLL_INTERVAL="60"  # seconds
        export EMAIL_ADDRESS="submissions-dev@dollarfunding.com"
        ;;
        
    staging)
        # Staging Email settings
        export EMAIL_IMAP_HOST="imap.example.com"
        export EMAIL_IMAP_PORT="993"
        export EMAIL_IMAP_SECURE="true"
        export EMAIL_INBOX="INBOX"
        export EMAIL_POLL_INTERVAL="30"  # seconds
        export EMAIL_ADDRESS="submissions-staging@dollarfunding.com"
        ;;
        
    production)
        # Production Email settings
        export EMAIL_IMAP_HOST="imap.example.com"
        export EMAIL_IMAP_PORT="993"
        export EMAIL_IMAP_SECURE="true"
        export EMAIL_INBOX="INBOX"
        export EMAIL_POLL_INTERVAL="30"  # seconds
        export EMAIL_ADDRESS="submissions@dollarfunding.com"
        ;;
        
esac

# ======================================================================
# JWT Authentication Configuration
# ======================================================================

# Set JWT configuration based on environment
case $ENVIRONMENT in
    development)
        # Development JWT settings
        export JWT_ALGORITHM="RS256"
        export JWT_EXPIRY="3600"  # 60 minutes in seconds
        export JWT_REFRESH_EXPIRY="604800"  # 7 days in seconds
        export JWT_PRIVATE_KEY_PATH="/etc/jwt/private.key"
        export JWT_PUBLIC_KEY_PATH="/etc/jwt/public.key"
        ;;
        
    staging)
        # Staging JWT settings
        export JWT_ALGORITHM="RS256"
        export JWT_EXPIRY="3600"  # 60 minutes in seconds
        export JWT_REFRESH_EXPIRY="604800"  # 7 days in seconds
        export JWT_PRIVATE_KEY_PATH="/etc/jwt/private.key"
        export JWT_PUBLIC_KEY_PATH="/etc/jwt/public.key"
        ;;
        
    production)
        # Production JWT settings
        export JWT_ALGORITHM="RS256"
        export JWT_EXPIRY="3600"  # 60 minutes in seconds
        export JWT_REFRESH_EXPIRY="604800"  # 7 days in seconds
        export JWT_PRIVATE_KEY_PATH="/etc/jwt/private.key"
        export JWT_PUBLIC_KEY_PATH="/etc/jwt/public.key"
        ;;
        
esac

# ======================================================================
# Validation Checks
# ======================================================================

# Validate that required environment variables are set
REQUIRED_VARS=(
    "K8S_NAMESPACE"
    "DB_HOST"
    "DB_PORT"
    "DB_NAME"
    "DB_USER"
    "REDIS_HOST"
    "REDIS_PORT"
    "RABBITMQ_HOST"
    "RABBITMQ_PORT"
    "S3_BUCKET"
    "JWT_ALGORITHM"
    "JWT_EXPIRY"
    "JWT_REFRESH_EXPIRY"
)

MISSING_VARS=0
for VAR in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!VAR}" ]]; then
        echo "Error: Required environment variable $VAR is not set"
        MISSING_VARS=$((MISSING_VARS+1))
    fi
done

if [[ $MISSING_VARS -gt 0 ]]; then
    echo "Error: $MISSING_VARS required environment variables are missing"
    exit 1
fi

# ======================================================================
# Output Environment Summary
# ======================================================================

echo "======================================================================"
echo "Environment Configuration Summary"
echo "======================================================================"
echo "Environment: $ENVIRONMENT"
echo "Cloud Provider: $CLOUD_PROVIDER"
echo "Kubernetes Namespace: $K8S_NAMESPACE"
echo "Database Host: $DB_HOST"
echo "Redis Host: $REDIS_HOST"
echo "RabbitMQ Host: $RABBITMQ_HOST"
echo "S3 Bucket: $S3_BUCKET"
echo "Log Level: $LOG_LEVEL"
echo "Default Replica Count: $REPLICA_COUNT_DEFAULT"
echo "OCR GPU Enabled: $OCR_GPU_ENABLED"
echo "======================================================================"

echo "Environment setup completed successfully for: $ENVIRONMENT"
exit 0