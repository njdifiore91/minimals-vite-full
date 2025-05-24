#!/bin/bash
# Make script executable with: chmod +x deploy-service.sh

# deploy-service.sh
# 
# This script deploys microservices to Kubernetes using Helm with environment-specific
# configurations and validation. It standardizes the deployment process across all services
# and environments, ensuring consistent application of configuration values and deployment strategies.
#
# Usage: ./deploy-service.sh --service <service-name> --environment <environment> [options]
#
# Required arguments:
#   --service        Name of the service to deploy (e.g., email-service, document-service)
#   --environment    Target environment (development, staging, production)
#
# Optional arguments:
#   --namespace      Kubernetes namespace (defaults to <environment>)
#   --version        Service version to deploy (defaults to latest)
#   --timeout        Deployment timeout in seconds (defaults to 300)
#   --wait           Wait for deployment to complete (true/false, defaults to true)
#   --debug          Enable debug output (true/false, defaults to false)
#   --dry-run        Perform a dry run without actual deployment (true/false, defaults to false)
#   --force          Force deployment even if validation fails (true/false, defaults to false)
#   --values         Additional values file to include (can be specified multiple times)
#   --set            Additional values to set (can be specified multiple times)

# Exit on error
set -e

# Default values
NAMESPACE=""
VERSION="latest"
TIMEOUT=300
WAIT=true
DEBUG=false
DRY_RUN=false
FORCE=false
ADDITIONAL_VALUES=()
ADDITIONAL_SETS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --service)
      SERVICE="$2"
      shift
      shift
      ;;
    --environment)
      ENVIRONMENT="$2"
      shift
      shift
      ;;
    --namespace)
      NAMESPACE="$2"
      shift
      shift
      ;;
    --version)
      VERSION="$2"
      shift
      shift
      ;;
    --timeout)
      TIMEOUT="$2"
      shift
      shift
      ;;
    --wait)
      WAIT="$2"
      shift
      shift
      ;;
    --debug)
      DEBUG="$2"
      shift
      shift
      ;;
    --dry-run)
      DRY_RUN="$2"
      shift
      shift
      ;;
    --force)
      FORCE="$2"
      shift
      shift
      ;;
    --values)
      ADDITIONAL_VALUES+=("$2")
      shift
      shift
      ;;
    --set)
      ADDITIONAL_SETS+=("$2")
      shift
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate required arguments
if [ -z "$SERVICE" ]; then
  echo "Error: --service is required"
  exit 1
fi

if [ -z "$ENVIRONMENT" ]; then
  echo "Error: --environment is required"
  exit 1
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
  echo "Error: environment must be one of: development, staging, production"
  exit 1
fi

# Set namespace if not provided
if [ -z "$NAMESPACE" ]; then
  NAMESPACE="$ENVIRONMENT"
fi

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Enable debug output if requested
if [ "$DEBUG" = "true" ]; then
  set -x
fi

# Function to log messages
log() {
  local level=$1
  local message=$2
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[$timestamp] [$level] $message"
}

# Function to log info messages
log_info() {
  log "INFO" "$1"
}

# Function to log error messages
log_error() {
  log "ERROR" "$1"
}

# Function to log debug messages
log_debug() {
  if [ "$DEBUG" = "true" ]; then
    log "DEBUG" "$1"
  fi
}

log_info "Starting deployment of $SERVICE to $ENVIRONMENT environment"

# Determine service type and chart path
DETERMINE_SERVICE_TYPE() {
  if [[ "$SERVICE" == "email-service" || "$SERVICE" == "notification-service" ]]; then
    SERVICE_TYPE="nodejs"
  elif [[ "$SERVICE" == "document-service" || "$SERVICE" == "ocr-service" ]]; then
    SERVICE_TYPE="python"
  elif [[ "$SERVICE" == "data-service" ]]; then
    SERVICE_TYPE="java"
  elif [[ "$SERVICE" == "api-gateway" ]]; then
    SERVICE_TYPE="kong"
  else
    log_error "Unknown service type for $SERVICE"
    exit 1
  fi
  
  log_debug "Service type determined as: $SERVICE_TYPE"
}

# Set chart path based on service
SET_CHART_PATH() {
  CHART_PATH="$ROOT_DIR/infrastructure/kubernetes/charts/$SERVICE"
  
  # Check if chart exists
  if [ ! -d "$CHART_PATH" ]; then
    log_error "Chart not found at $CHART_PATH"
    exit 1
  fi
  
  log_debug "Chart path set to: $CHART_PATH"
}

# Collect values files
COLLECT_VALUES_FILES() {
  VALUES_FILES=()
  
  # Common values file
  COMMON_VALUES="$CHART_PATH/values.yaml"
  if [ -f "$COMMON_VALUES" ]; then
    VALUES_FILES+=("--values" "$COMMON_VALUES")
    log_debug "Added common values file: $COMMON_VALUES"
  fi
  
  # Environment-specific values file
  ENV_VALUES="$CHART_PATH/values-$ENVIRONMENT.yaml"
  if [ -f "$ENV_VALUES" ]; then
    VALUES_FILES+=("--values" "$ENV_VALUES")
    log_debug "Added environment values file: $ENV_VALUES"
  fi
  
  # Service type specific values
  TYPE_VALUES="$ROOT_DIR/infrastructure/kubernetes/charts/common/values-$SERVICE_TYPE.yaml"
  if [ -f "$TYPE_VALUES" ]; then
    VALUES_FILES+=("--values" "$TYPE_VALUES")
    log_debug "Added service type values file: $TYPE_VALUES"
  fi
  
  # Add additional values files
  for value_file in "${ADDITIONAL_VALUES[@]}"; do
    if [ -f "$value_file" ]; then
      VALUES_FILES+=("--values" "$value_file")
      log_debug "Added additional values file: $value_file"
    else
      log_error "Additional values file not found: $value_file"
      exit 1
    fi
  done
}

# Prepare set values
PREPARE_SET_VALUES() {
  SET_VALUES=()
  
  # Add version
  SET_VALUES+=("--set" "image.tag=$VERSION")
  
  # Add deployment annotations for tracking
  DEPLOY_TIMESTAMP=$(date +"%Y-%m-%d-%H-%M-%S")
  SET_VALUES+=("--set" "deploymentAnnotations.timestamp=$DEPLOY_TIMESTAMP")
  SET_VALUES+=("--set" "deploymentAnnotations.deployer=$USER")
  SET_VALUES+=("--set" "deploymentAnnotations.environment=$ENVIRONMENT")
  SET_VALUES+=("--set" "deploymentAnnotations.version=$VERSION")
  
  # Add additional set values
  for set_value in "${ADDITIONAL_SETS[@]}"; do
    SET_VALUES+=("--set" "$set_value")
    log_debug "Added set value: $set_value"
  done
}

# Check if release exists
CHECK_RELEASE_EXISTS() {
  if helm status "$SERVICE" -n "$NAMESPACE" &> /dev/null; then
    RELEASE_EXISTS=true
    log_debug "Release $SERVICE exists in namespace $NAMESPACE"
  else
    RELEASE_EXISTS=false
    log_debug "Release $SERVICE does not exist in namespace $NAMESPACE"
  fi
}

# Configure deployment strategy based on service type
CONFIGURE_DEPLOYMENT_STRATEGY() {
  case $SERVICE_TYPE in
    nodejs)
      # Node.js services use rolling update with 25% max unavailable
      SET_VALUES+=("--set" "deploymentStrategy.type=RollingUpdate")
      SET_VALUES+=("--set" "deploymentStrategy.rollingUpdate.maxUnavailable=25%")
      SET_VALUES+=("--set" "deploymentStrategy.rollingUpdate.maxSurge=25%")
      ;;
    python)
      # Python services use rolling update with 50% max unavailable due to higher resource needs
      SET_VALUES+=("--set" "deploymentStrategy.type=RollingUpdate")
      SET_VALUES+=("--set" "deploymentStrategy.rollingUpdate.maxUnavailable=50%")
      SET_VALUES+=("--set" "deploymentStrategy.rollingUpdate.maxSurge=50%")
      ;;
    java)
      # Java services use rolling update with 25% max unavailable and longer startup probe
      SET_VALUES+=("--set" "deploymentStrategy.type=RollingUpdate")
      SET_VALUES+=("--set" "deploymentStrategy.rollingUpdate.maxUnavailable=25%")
      SET_VALUES+=("--set" "deploymentStrategy.rollingUpdate.maxSurge=25%")
      SET_VALUES+=("--set" "startupProbe.initialDelaySeconds=30")
      ;;
    kong)
      # API Gateway uses blue-green deployment for zero downtime
      SET_VALUES+=("--set" "deploymentStrategy.type=Recreate")
      ;;
    *)
      log_error "Unknown service type: $SERVICE_TYPE"
      exit 1
      ;;
  esac
  
  log_debug "Configured deployment strategy for service type: $SERVICE_TYPE"
}

# Configure environment-specific settings
CONFIGURE_ENVIRONMENT_SETTINGS() {
  case $ENVIRONMENT in
    development)
      # Development environment has minimal resources
      SET_VALUES+=("--set" "resources.requests.cpu=100m")
      SET_VALUES+=("--set" "resources.requests.memory=256Mi")
      SET_VALUES+=("--set" "resources.limits.cpu=500m")
      SET_VALUES+=("--set" "resources.limits.memory=512Mi")
      SET_VALUES+=("--set" "replicaCount=1")
      ;;
    staging)
      # Staging environment has moderate resources
      SET_VALUES+=("--set" "resources.requests.cpu=250m")
      SET_VALUES+=("--set" "resources.requests.memory=512Mi")
      SET_VALUES+=("--set" "resources.limits.cpu=1000m")
      SET_VALUES+=("--set" "resources.limits.memory=1Gi")
      SET_VALUES+=("--set" "replicaCount=2")
      ;;
    production)
      # Production environment has higher resources and more replicas
      SET_VALUES+=("--set" "resources.requests.cpu=500m")
      SET_VALUES+=("--set" "resources.requests.memory=1Gi")
      SET_VALUES+=("--set" "resources.limits.cpu=2000m")
      SET_VALUES+=("--set" "resources.limits.memory=2Gi")
      SET_VALUES+=("--set" "replicaCount=3")
      ;;
    *)
      log_error "Unknown environment: $ENVIRONMENT"
      exit 1
      ;;
  esac
  
  # Special case for Python services in production (need more memory for ML models)
  if [[ "$SERVICE_TYPE" == "python" && "$ENVIRONMENT" == "production" ]]; then
    SET_VALUES+=("--set" "resources.requests.memory=2Gi")
    SET_VALUES+=("--set" "resources.limits.memory=4Gi")
  fi
  
  log_debug "Configured environment-specific settings for: $ENVIRONMENT"
}

# Configure service-specific post-deployment hooks
CONFIGURE_POST_DEPLOYMENT_HOOKS() {
  case $SERVICE in
    document-service)
      # Document service needs to download ML models after deployment
      SET_VALUES+=("--set" "postDeployment.enabled=true")
      SET_VALUES+=("--set" "postDeployment.command=python,/app/scripts/download_models.py")
      ;;
    ocr-service)
      # OCR service needs to download ML models after deployment
      SET_VALUES+=("--set" "postDeployment.enabled=true")
      SET_VALUES+=("--set" "postDeployment.command=python,/app/scripts/download_models.py")
      ;;
    data-service)
      # Data service needs to run database migrations
      SET_VALUES+=("--set" "postDeployment.enabled=true")
      SET_VALUES+=("--set" "postDeployment.command=java,-jar,/app/app.jar,--migrate")
      ;;
    *)
      # No post-deployment hooks for other services
      SET_VALUES+=("--set" "postDeployment.enabled=false")
      ;;
  esac
  
  log_debug "Configured post-deployment hooks for service: $SERVICE"
}

# Validate deployment configuration
VALIDATE_DEPLOYMENT() {
  log_info "Validating deployment configuration"
  
  # Validate chart
  if ! helm lint "$CHART_PATH" "${VALUES_FILES[@]}" "${SET_VALUES[@]}" &> /dev/null; then
    log_error "Helm chart validation failed"
    if [ "$FORCE" != "true" ]; then
      exit 1
    else
      log_info "Proceeding with deployment despite validation errors (--force=true)"
    fi
  fi
  
  # Validate namespace exists
  if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    log_info "Namespace $NAMESPACE does not exist, creating it"
    kubectl create namespace "$NAMESPACE"
  fi
  
  log_info "Deployment validation successful"
}

# Deploy the service
DEPLOY_SERVICE() {
  log_info "Deploying $SERVICE to $NAMESPACE namespace in $ENVIRONMENT environment"
  
  # Build helm command
  HELM_CMD=(helm)
  
  if [ "$RELEASE_EXISTS" = "true" ]; then
    HELM_CMD+=(upgrade)
    log_info "Performing upgrade of existing release"
  else
    HELM_CMD+=(install)
    log_info "Performing new installation"
  fi
  
  HELM_CMD+=("$SERVICE" "$CHART_PATH")
  HELM_CMD+=(--namespace "$NAMESPACE")
  
  # Add values files
  for value in "${VALUES_FILES[@]}"; do
    HELM_CMD+=("$value")
  done
  
  # Add set values
  for value in "${SET_VALUES[@]}"; do
    HELM_CMD+=("$value")
  done
  
  # Add timeout
  HELM_CMD+=(--timeout "${TIMEOUT}s")
  
  # Add wait flag if specified
  if [ "$WAIT" = "true" ]; then
    HELM_CMD+=(--wait)
  fi
  
  # Add dry-run flag if specified
  if [ "$DRY_RUN" = "true" ]; then
    HELM_CMD+=(--dry-run)
  fi
  
  # Execute helm command
  log_debug "Executing: ${HELM_CMD[*]}"
  "${HELM_CMD[@]}"
  
  DEPLOY_STATUS=$?
  
  if [ $DEPLOY_STATUS -eq 0 ]; then
    log_info "Deployment of $SERVICE to $ENVIRONMENT environment completed successfully"
  else
    log_error "Deployment of $SERVICE to $ENVIRONMENT environment failed with status $DEPLOY_STATUS"
    exit $DEPLOY_STATUS
  fi
}

# Verify deployment
VERIFY_DEPLOYMENT() {
  if [ "$DRY_RUN" = "true" ]; then
    log_info "Skipping deployment verification in dry-run mode"
    return 0
  fi
  
  log_info "Verifying deployment of $SERVICE"
  
  # Wait for pods to be ready
  kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=$SERVICE -n $NAMESPACE --timeout=${TIMEOUT}s
  
  # Check deployment status
  DEPLOYMENT_STATUS=$(kubectl get deployment -l app.kubernetes.io/name=$SERVICE -n $NAMESPACE -o jsonpath='{.items[0].status.conditions[?(@.type=="Available")].status}')
  
  if [ "$DEPLOYMENT_STATUS" = "True" ]; then
    log_info "Deployment of $SERVICE is available and ready"
  else
    log_error "Deployment of $SERVICE is not available. Status: $DEPLOYMENT_STATUS"
    exit 1
  fi
}

# Run post-deployment tasks
RUN_POST_DEPLOYMENT_TASKS() {
  if [ "$DRY_RUN" = "true" ]; then
    log_info "Skipping post-deployment tasks in dry-run mode"
    return 0
  fi
  
  # Check if post-deployment is enabled
  POST_DEPLOYMENT_ENABLED=$(helm get values $SERVICE -n $NAMESPACE -o jsonpath='{.postDeployment.enabled}')
  
  if [ "$POST_DEPLOYMENT_ENABLED" = "true" ]; then
    log_info "Running post-deployment tasks for $SERVICE"
    
    # Get post-deployment command
    POST_DEPLOYMENT_COMMAND=$(helm get values $SERVICE -n $NAMESPACE -o jsonpath='{.postDeployment.command}')
    
    # Get pod name
    POD_NAME=$(kubectl get pod -l app.kubernetes.io/name=$SERVICE -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
    
    # Convert command string to array
    IFS=',' read -ra CMD_ARRAY <<< "$POST_DEPLOYMENT_COMMAND"
    
    # Execute command in pod
    log_debug "Executing post-deployment command in pod $POD_NAME: ${CMD_ARRAY[*]}"
    kubectl exec -n $NAMESPACE $POD_NAME -- "${CMD_ARRAY[@]}"
    
    POST_DEPLOYMENT_STATUS=$?
    
    if [ $POST_DEPLOYMENT_STATUS -eq 0 ]; then
      log_info "Post-deployment tasks completed successfully"
    else
      log_error "Post-deployment tasks failed with status $POST_DEPLOYMENT_STATUS"
      exit $POST_DEPLOYMENT_STATUS
    fi
  else
    log_debug "No post-deployment tasks configured for $SERVICE"
  fi
}

# Main execution flow
DETERMINE_SERVICE_TYPE
SET_CHART_PATH
COLLECT_VALUES_FILES
PREPARE_SET_VALUES
CHECK_RELEASE_EXISTS
CONFIGURE_DEPLOYMENT_STRATEGY
CONFIGURE_ENVIRONMENT_SETTINGS
CONFIGURE_POST_DEPLOYMENT_HOOKS
VALIDATE_DEPLOYMENT
DEPLOY_SERVICE
VERIFY_DEPLOYMENT
RUN_POST_DEPLOYMENT_TASKS

log_info "Deployment process completed successfully"
exit 0