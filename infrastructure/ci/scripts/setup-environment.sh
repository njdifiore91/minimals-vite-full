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

# Default values
DEFAULT_CLOUD_PROVIDER="aws"
DEFAULT_ENVIRONMENT="development"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
LOG_FILE="${SCRIPT_DIR}/setup-environment.log"

# Function to display usage information
usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -e, --environment     Target environment (development, staging, production)"
  echo "  -c, --cloud-provider  Cloud provider (aws, azure, gcp)"
  echo "  -k, --k8s-context     Kubernetes context name (optional)"
  echo "  -n, --namespace       Kubernetes namespace (optional)"
  echo "  -h, --help            Display this help message"
  echo "  -v, --verbose         Enable verbose output"
  exit 1
}

# Function for logging
log() {
  local level=$1
  local message=$2
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  
  echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
  
  if [[ "${level}" == "ERROR" ]]; then
    echo "[${timestamp}] [${level}] ${message}" >&2
  fi
}

# Function to validate environment
validate_environment() {
  local env=$1
  case "${env}" in
    development|staging|production)
      log "INFO" "Environment validated: ${env}"
      return 0
      ;;
    *)
      log "ERROR" "Invalid environment: ${env}. Must be one of: development, staging, production"
      return 1
      ;;
  esac
}

# Function to validate cloud provider
validate_cloud_provider() {
  local provider=$1
  case "${provider}" in
    aws|azure|gcp)
      log "INFO" "Cloud provider validated: ${provider}"
      return 0
      ;;
    *)
      log "ERROR" "Invalid cloud provider: ${provider}. Must be one of: aws, azure, gcp"
      return 1
      ;;
  esac
}

# Function to configure AWS credentials
configure_aws_credentials() {
  log "INFO" "Configuring AWS credentials"
  
  # Check if AWS credentials are already configured
  if [[ -z "${AWS_ACCESS_KEY_ID}" || -z "${AWS_SECRET_ACCESS_KEY}" ]]; then
    log "ERROR" "AWS credentials not found in environment variables"
    
    # Check if running in CI environment with secrets
    if [[ -n "${CI}" && -n "${AWS_ACCESS_KEY_ID_SECRET}" && -n "${AWS_SECRET_ACCESS_KEY_SECRET}" ]]; then
      log "INFO" "Using CI secrets for AWS credentials"
      export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID_SECRET}"
      export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY_SECRET}"
    else
      # Try to use AWS CLI profile
      if [[ -f "${HOME}/.aws/credentials" ]]; then
        log "INFO" "Using AWS CLI profile for credentials"
        export AWS_PROFILE="mca-${ENVIRONMENT}"
      else
        log "ERROR" "No AWS credentials found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
        return 1
      fi
    fi
  fi
  
  # Set AWS region based on environment
  case "${ENVIRONMENT}" in
    development)
      export AWS_REGION="us-west-2"
      ;;
    staging)
      export AWS_REGION="us-east-2"
      ;;
    production)
      export AWS_REGION="us-east-1"
      ;;
  esac
  
  log "INFO" "AWS region set to ${AWS_REGION}"
  return 0
}

# Function to configure Azure credentials
configure_azure_credentials() {
  log "INFO" "Configuring Azure credentials"
  
  # Check if Azure credentials are already configured
  if [[ -z "${AZURE_CLIENT_ID}" || -z "${AZURE_CLIENT_SECRET}" || -z "${AZURE_TENANT_ID}" ]]; then
    log "ERROR" "Azure credentials not found in environment variables"
    
    # Check if running in CI environment with secrets
    if [[ -n "${CI}" && -n "${AZURE_CLIENT_ID_SECRET}" && -n "${AZURE_CLIENT_SECRET_SECRET}" && -n "${AZURE_TENANT_ID_SECRET}" ]]; then
      log "INFO" "Using CI secrets for Azure credentials"
      export AZURE_CLIENT_ID="${AZURE_CLIENT_ID_SECRET}"
      export AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET_SECRET}"
      export AZURE_TENANT_ID="${AZURE_TENANT_ID_SECRET}"
    else
      log "ERROR" "No Azure credentials found. Please set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID environment variables"
      return 1
    fi
  fi
  
  # Set Azure subscription based on environment
  case "${ENVIRONMENT}" in
    development)
      export AZURE_SUBSCRIPTION_ID="dev-subscription-id"
      ;;
    staging)
      export AZURE_SUBSCRIPTION_ID="staging-subscription-id"
      ;;
    production)
      export AZURE_SUBSCRIPTION_ID="prod-subscription-id"
      ;;
  esac
  
  log "INFO" "Azure subscription set to ${AZURE_SUBSCRIPTION_ID}"
  return 0
}

# Function to configure GCP credentials
configure_gcp_credentials() {
  log "INFO" "Configuring GCP credentials"
  
  # Check if GCP credentials are already configured
  if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
    log "ERROR" "GCP credentials not found in environment variables"
    
    # Check if running in CI environment with secrets
    if [[ -n "${CI}" && -n "${GCP_SERVICE_ACCOUNT_KEY}" ]]; then
      log "INFO" "Using CI secrets for GCP credentials"
      export GOOGLE_APPLICATION_CREDENTIALS="${ROOT_DIR}/gcp-credentials.json"
      echo "${GCP_SERVICE_ACCOUNT_KEY}" > "${GOOGLE_APPLICATION_CREDENTIALS}"
      chmod 600 "${GOOGLE_APPLICATION_CREDENTIALS}"
    else
      # Try to use GCP CLI configuration
      if [[ -f "${HOME}/.config/gcloud/application_default_credentials.json" ]]; then
        log "INFO" "Using GCP CLI default credentials"
        export GOOGLE_APPLICATION_CREDENTIALS="${HOME}/.config/gcloud/application_default_credentials.json"
      else
        log "ERROR" "No GCP credentials found. Please set GOOGLE_APPLICATION_CREDENTIALS environment variable"
        return 1
      fi
    fi
  fi
  
  # Set GCP project based on environment
  case "${ENVIRONMENT}" in
    development)
      export GCP_PROJECT_ID="mca-development"
      ;;
    staging)
      export GCP_PROJECT_ID="mca-staging"
      ;;
    production)
      export GCP_PROJECT_ID="mca-production"
      ;;
  esac
  
  log "INFO" "GCP project set to ${GCP_PROJECT_ID}"
  return 0
}

# Function to configure Kubernetes context
configure_kubernetes_context() {
  log "INFO" "Configuring Kubernetes context"
  
  # Set default Kubernetes context based on environment and cloud provider if not provided
  if [[ -z "${K8S_CONTEXT}" ]]; then
    case "${CLOUD_PROVIDER}" in
      aws)
        export K8S_CONTEXT="arn:aws:eks:${AWS_REGION}:*:cluster/mca-${ENVIRONMENT}"
        ;;
      azure)
        export K8S_CONTEXT="mca-${ENVIRONMENT}"
        ;;
      gcp)
        export K8S_CONTEXT="gke_${GCP_PROJECT_ID}_${GCP_REGION}_mca-${ENVIRONMENT}"
        ;;
    esac
  fi
  
  # Set default namespace based on environment if not provided
  if [[ -z "${NAMESPACE}" ]]; then
    export NAMESPACE="mca-${ENVIRONMENT}"
  fi
  
  # Check if kubectl is installed
  if ! command -v kubectl &> /dev/null; then
    log "ERROR" "kubectl not found. Please install kubectl"
    return 1
  fi
  
  # Configure kubectl context
  if ! kubectl config use-context "${K8S_CONTEXT}" &> /dev/null; then
    log "WARNING" "Failed to set Kubernetes context to ${K8S_CONTEXT}. Context may not exist yet."
  else
    log "INFO" "Kubernetes context set to ${K8S_CONTEXT}"
  fi
  
  # Ensure namespace exists
  if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
    log "INFO" "Creating namespace ${NAMESPACE}"
    kubectl create namespace "${NAMESPACE}" || {
      log "WARNING" "Failed to create namespace ${NAMESPACE}. It may already exist or you may not have permission."
    }
  fi
  
  log "INFO" "Kubernetes namespace set to ${NAMESPACE}"
  return 0
}

# Function to configure environment-specific variables
configure_environment_variables() {
  log "INFO" "Configuring environment-specific variables"
  
  # Set common variables
  export MCA_ENV="${ENVIRONMENT}"
  export MCA_CLOUD_PROVIDER="${CLOUD_PROVIDER}"
  export MCA_K8S_NAMESPACE="${NAMESPACE}"
  
  # Set environment-specific variables
  case "${ENVIRONMENT}" in
    development)
      # Database configuration
      export MCA_DB_HOST="postgres.${NAMESPACE}.svc.cluster.local"
      export MCA_DB_PORT="5432"
      export MCA_DB_NAME="mca_dev"
      export MCA_DB_USER="mca_dev_user"
      
      # RabbitMQ configuration
      export MCA_RABBITMQ_HOST="rabbitmq.${NAMESPACE}.svc.cluster.local"
      export MCA_RABBITMQ_PORT="5672"
      export MCA_RABBITMQ_VHOST="/"
      export MCA_RABBITMQ_USER="mca_dev_user"
      
      # Redis configuration
      export MCA_REDIS_HOST="redis.${NAMESPACE}.svc.cluster.local"
      export MCA_REDIS_PORT="6379"
      
      # S3 configuration
      export MCA_S3_BUCKET="mca-documents-development"
      
      # Logging configuration
      export MCA_LOG_LEVEL="DEBUG"
      
      # Feature flags
      export MCA_FEATURE_OCR_HANDWRITING="true"
      export MCA_FEATURE_AUTO_APPROVAL="false"
      
      # Resource limits
      export MCA_RESOURCE_CPU_REQUEST="100m"
      export MCA_RESOURCE_CPU_LIMIT="500m"
      export MCA_RESOURCE_MEMORY_REQUEST="256Mi"
      export MCA_RESOURCE_MEMORY_LIMIT="1Gi"
      ;;
      
    staging)
      # Database configuration
      export MCA_DB_HOST="postgres.${NAMESPACE}.svc.cluster.local"
      export MCA_DB_PORT="5432"
      export MCA_DB_NAME="mca_staging"
      export MCA_DB_USER="mca_staging_user"
      
      # RabbitMQ configuration
      export MCA_RABBITMQ_HOST="rabbitmq.${NAMESPACE}.svc.cluster.local"
      export MCA_RABBITMQ_PORT="5672"
      export MCA_RABBITMQ_VHOST="/"
      export MCA_RABBITMQ_USER="mca_staging_user"
      
      # Redis configuration
      export MCA_REDIS_HOST="redis.${NAMESPACE}.svc.cluster.local"
      export MCA_REDIS_PORT="6379"
      
      # S3 configuration
      export MCA_S3_BUCKET="mca-documents-staging"
      
      # Logging configuration
      export MCA_LOG_LEVEL="INFO"
      
      # Feature flags
      export MCA_FEATURE_OCR_HANDWRITING="true"
      export MCA_FEATURE_AUTO_APPROVAL="true"
      
      # Resource limits
      export MCA_RESOURCE_CPU_REQUEST="500m"
      export MCA_RESOURCE_CPU_LIMIT="1000m"
      export MCA_RESOURCE_MEMORY_REQUEST="512Mi"
      export MCA_RESOURCE_MEMORY_LIMIT="2Gi"
      ;;
      
    production)
      # Database configuration
      export MCA_DB_HOST="postgres.${NAMESPACE}.svc.cluster.local"
      export MCA_DB_PORT="5432"
      export MCA_DB_NAME="mca_production"
      export MCA_DB_USER="mca_production_user"
      
      # RabbitMQ configuration
      export MCA_RABBITMQ_HOST="rabbitmq.${NAMESPACE}.svc.cluster.local"
      export MCA_RABBITMQ_PORT="5672"
      export MCA_RABBITMQ_VHOST="/"
      export MCA_RABBITMQ_USER="mca_production_user"
      
      # Redis configuration
      export MCA_REDIS_HOST="redis.${NAMESPACE}.svc.cluster.local"
      export MCA_REDIS_PORT="6379"
      
      # S3 configuration
      export MCA_S3_BUCKET="mca-documents-production"
      
      # Logging configuration
      export MCA_LOG_LEVEL="WARN"
      
      # Feature flags
      export MCA_FEATURE_OCR_HANDWRITING="true"
      export MCA_FEATURE_AUTO_APPROVAL="true"
      
      # Resource limits
      export MCA_RESOURCE_CPU_REQUEST="1000m"
      export MCA_RESOURCE_CPU_LIMIT="2000m"
      export MCA_RESOURCE_MEMORY_REQUEST="1Gi"
      export MCA_RESOURCE_MEMORY_LIMIT="4Gi"
      ;;
  esac
  
  # Set service-specific endpoints
  export MCA_EMAIL_SERVICE_ENDPOINT="http://email-service.${NAMESPACE}.svc.cluster.local:3000"
  export MCA_DOCUMENT_SERVICE_ENDPOINT="http://document-service.${NAMESPACE}.svc.cluster.local:5000"
  export MCA_OCR_SERVICE_ENDPOINT="http://ocr-service.${NAMESPACE}.svc.cluster.local:5000"
  export MCA_DATA_SERVICE_ENDPOINT="http://data-service.${NAMESPACE}.svc.cluster.local:8080"
  export MCA_NOTIFICATION_SERVICE_ENDPOINT="http://notification-service.${NAMESPACE}.svc.cluster.local:3000"
  
  # Set API Gateway endpoint
  case "${ENVIRONMENT}" in
    development)
      export MCA_API_GATEWAY_ENDPOINT="https://api-dev.dollarfunding.com"
      ;;
    staging)
      export MCA_API_GATEWAY_ENDPOINT="https://api-staging.dollarfunding.com"
      ;;
    production)
      export MCA_API_GATEWAY_ENDPOINT="https://api.dollarfunding.com"
      ;;
  esac
  
  log "INFO" "Environment variables configured for ${ENVIRONMENT}"
  return 0
}

# Function to validate required environment variables
validate_environment_variables() {
  log "INFO" "Validating environment variables"
  
  local missing_vars=false
  
  # Common required variables
  local required_vars=(
    "MCA_ENV"
    "MCA_CLOUD_PROVIDER"
    "MCA_K8S_NAMESPACE"
    "MCA_DB_HOST"
    "MCA_DB_PORT"
    "MCA_DB_NAME"
    "MCA_DB_USER"
    "MCA_RABBITMQ_HOST"
    "MCA_RABBITMQ_PORT"
    "MCA_RABBITMQ_USER"
    "MCA_REDIS_HOST"
    "MCA_REDIS_PORT"
    "MCA_S3_BUCKET"
    "MCA_LOG_LEVEL"
  )
  
  # Check each required variable
  for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
      log "ERROR" "Required environment variable ${var} is not set"
      missing_vars=true
    fi
  done
  
  # Cloud provider specific variables
  case "${CLOUD_PROVIDER}" in
    aws)
      if [[ -z "${AWS_REGION}" || -z "${AWS_ACCESS_KEY_ID}" || -z "${AWS_SECRET_ACCESS_KEY}" ]]; then
        log "ERROR" "Required AWS environment variables are not set"
        missing_vars=true
      fi
      ;;
    azure)
      if [[ -z "${AZURE_SUBSCRIPTION_ID}" || -z "${AZURE_CLIENT_ID}" || -z "${AZURE_CLIENT_SECRET}" || -z "${AZURE_TENANT_ID}" ]]; then
        log "ERROR" "Required Azure environment variables are not set"
        missing_vars=true
      fi
      ;;
    gcp)
      if [[ -z "${GCP_PROJECT_ID}" || -z "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
        log "ERROR" "Required GCP environment variables are not set"
        missing_vars=true
      fi
      ;;
  esac
  
  if [[ "${missing_vars}" == "true" ]]; then
    log "ERROR" "Environment validation failed. Some required variables are missing."
    return 1
  fi
  
  log "INFO" "Environment validation successful"
  return 0
}

# Function to export environment variables to a file for sourcing
export_environment_variables() {
  local output_file="${ROOT_DIR}/.env.${ENVIRONMENT}"
  
  log "INFO" "Exporting environment variables to ${output_file}"
  
  # Create or truncate the output file
  echo "# MCA Application Processing System - Environment Variables" > "${output_file}"
  echo "# Generated on $(date)" >> "${output_file}"
  echo "# Environment: ${ENVIRONMENT}" >> "${output_file}"
  echo "# Cloud Provider: ${CLOUD_PROVIDER}" >> "${output_file}"
  echo "" >> "${output_file}"
  
  # Export all MCA_ prefixed variables
  env | grep "^MCA_" | sort >> "${output_file}"
  
  # Export cloud provider specific variables
  case "${CLOUD_PROVIDER}" in
    aws)
      echo "" >> "${output_file}"
      echo "# AWS Configuration" >> "${output_file}"
      echo "AWS_REGION=${AWS_REGION}" >> "${output_file}"
      echo "AWS_PROFILE=${AWS_PROFILE:-}" >> "${output_file}"
      ;;
    azure)
      echo "" >> "${output_file}"
      echo "# Azure Configuration" >> "${output_file}"
      echo "AZURE_SUBSCRIPTION_ID=${AZURE_SUBSCRIPTION_ID}" >> "${output_file}"
      ;;
    gcp)
      echo "" >> "${output_file}"
      echo "# GCP Configuration" >> "${output_file}"
      echo "GCP_PROJECT_ID=${GCP_PROJECT_ID}" >> "${output_file}"
      ;;
  esac
  
  # Export Kubernetes configuration
  echo "" >> "${output_file}"
  echo "# Kubernetes Configuration" >> "${output_file}"
  echo "K8S_CONTEXT=${K8S_CONTEXT}" >> "${output_file}"
  echo "NAMESPACE=${NAMESPACE}" >> "${output_file}"
  
  log "INFO" "Environment variables exported to ${output_file}"
  
  # Make the file readable only by the owner
  chmod 600 "${output_file}"
  
  echo "Environment variables exported to ${output_file}"
  echo "To use these variables, run: source ${output_file}"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -c|--cloud-provider)
      CLOUD_PROVIDER="$2"
      shift 2
      ;;
    -k|--k8s-context)
      K8S_CONTEXT="$2"
      shift 2
      ;;
    -n|--namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    -v|--verbose)
      VERBOSE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Set default values if not provided
ENVIRONMENT=${ENVIRONMENT:-${DEFAULT_ENVIRONMENT}}
CLOUD_PROVIDER=${CLOUD_PROVIDER:-${DEFAULT_CLOUD_PROVIDER}}

# Create log directory if it doesn't exist
mkdir -p "$(dirname "${LOG_FILE}")"

# Initialize log file
echo "# MCA Application Processing System - Environment Setup Log" > "${LOG_FILE}"
echo "# Started on $(date)" >> "${LOG_FILE}"
echo "# Environment: ${ENVIRONMENT}" >> "${LOG_FILE}"
echo "# Cloud Provider: ${CLOUD_PROVIDER}" >> "${LOG_FILE}"
echo "" >> "${LOG_FILE}"

# Main execution
log "INFO" "Starting environment setup for ${ENVIRONMENT} on ${CLOUD_PROVIDER}"

# Validate environment and cloud provider
validate_environment "${ENVIRONMENT}" || exit 1
validate_cloud_provider "${CLOUD_PROVIDER}" || exit 1

# Configure cloud provider credentials
case "${CLOUD_PROVIDER}" in
  aws)
    configure_aws_credentials || exit 1
    ;;
  azure)
    configure_azure_credentials || exit 1
    ;;
  gcp)
    configure_gcp_credentials || exit 1
    ;;
esac

# Configure Kubernetes context
configure_kubernetes_context || exit 1

# Configure environment-specific variables
configure_environment_variables || exit 1

# Validate environment variables
validate_environment_variables || exit 1

# Export environment variables to a file
export_environment_variables

log "INFO" "Environment setup completed successfully"

# Print summary
echo ""
echo "Environment setup completed successfully"
echo "Environment: ${ENVIRONMENT}"
echo "Cloud Provider: ${CLOUD_PROVIDER}"
echo "Kubernetes Context: ${K8S_CONTEXT}"
echo "Kubernetes Namespace: ${NAMESPACE}"
echo ""
echo "Environment variables have been exported to ${ROOT_DIR}/.env.${ENVIRONMENT}"
echo "To use these variables, run: source ${ROOT_DIR}/.env.${ENVIRONMENT}"

exit 0