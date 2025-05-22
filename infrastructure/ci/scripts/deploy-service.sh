#!/bin/bash

# deploy-service.sh
# 
# This script deploys MCA Application Processing System microservices to Kubernetes
# using Helm with environment-specific configurations and validation.
#
# It selects the appropriate Helm chart, applies environment-specific values,
# and handles the distinction between upgrades and installations.
#
# Usage: ./deploy-service.sh --service <service-name> --env <environment> [options]

set -eo pipefail

# Default values
DRY_RUN="false"
WAIT="true"
TIMEOUT="300s"
DEBUG="false"
FORCE="false"
NAMESPACE=""
VALUES_FILES=()
SET_VALUES=()
CHART_VERSION=""

# Script directory for relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Color codes for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [[ "${DEBUG}" == "true" ]]; then
        echo -e "${YELLOW}[DEBUG]${NC} $1"
    fi
}

# Display usage information
usage() {
    cat << EOF
Usage: $(basename "$0") --service <service-name> --env <environment> [options]

Deploys a service to Kubernetes using Helm with environment-specific configurations.

Required arguments:
  --service, -s       Service name to deploy (e.g., email-service, document-service)
  --env, -e           Target environment (development, staging, production)

Optional arguments:
  --namespace, -n     Kubernetes namespace (defaults to <environment>-mca)
  --values, -f        Additional values file(s) to use (can be specified multiple times)
  --set               Set values on the command line (can be specified multiple times)
  --version, -v       Chart version to deploy
  --timeout, -t       Timeout for deployment (default: 300s)
  --dry-run           Perform a dry-run deployment
  --no-wait           Don't wait for deployment to complete
  --debug             Enable debug output
  --force             Force deployment even if validation fails
  --help, -h          Display this help message

Examples:
  $(basename "$0") --service email-service --env development
  $(basename "$0") --service data-service --env production --timeout 600s
  $(basename "$0") --service ocr-service --env staging --set resources.limits.gpu=1
  $(basename "$0") --service document-service --env development --dry-run

Supported services:
  - email-service
  - document-service
  - ocr-service
  - data-service
  - notification-service
  - api-gateway
  - frontend
  - postgresql
  - rabbitmq
  - redis
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --service|-s)
                SERVICE_NAME="$2"
                shift 2
                ;;
            --env|-e)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --namespace|-n)
                NAMESPACE="$2"
                shift 2
                ;;
            --values|-f)
                VALUES_FILES+=("$2")
                shift 2
                ;;
            --set)
                SET_VALUES+=("$2")
                shift 2
                ;;
            --version|-v)
                CHART_VERSION="$2"
                shift 2
                ;;
            --timeout|-t)
                TIMEOUT="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --no-wait)
                WAIT="false"
                shift
                ;;
            --debug)
                DEBUG="true"
                shift
                ;;
            --force)
                FORCE="true"
                shift
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "${SERVICE_NAME}" ]]; then
        log_error "Service name is required"
        usage
        exit 1
    fi

    if [[ -z "${ENVIRONMENT}" ]]; then
        log_error "Environment is required"
        usage
        exit 1
    fi

    # Validate environment
    if [[ "${ENVIRONMENT}" != "development" && "${ENVIRONMENT}" != "staging" && "${ENVIRONMENT}" != "production" ]]; then
        log_error "Invalid environment: ${ENVIRONMENT}. Must be one of: development, staging, production"
        exit 1
    fi

    # Set default namespace if not provided
    if [[ -z "${NAMESPACE}" ]]; then
        NAMESPACE="${ENVIRONMENT}-mca"
    fi
}

# Validate service name and determine service type
validate_service() {
    # List of supported services
    local supported_services=("email-service" "document-service" "ocr-service" "data-service" "notification-service" "api-gateway" "frontend" "postgresql" "rabbitmq" "redis")
    
    # Check if service is supported
    local service_supported=false
    for supported_service in "${supported_services[@]}"; do
        if [[ "${SERVICE_NAME}" == "${supported_service}" ]]; then
            service_supported=true
            break
        fi
    done

    if [[ "${service_supported}" == "false" ]]; then
        log_error "Unsupported service: ${SERVICE_NAME}"
        log_error "Supported services: ${supported_services[*]}"
        exit 1
    fi

    # Determine service type for specific configurations
    case "${SERVICE_NAME}" in
        email-service|notification-service)
            SERVICE_TYPE="nodejs"
            ;;
        document-service|ocr-service)
            SERVICE_TYPE="python"
            ;;
        data-service)
            SERVICE_TYPE="java"
            ;;
        api-gateway)
            SERVICE_TYPE="kong"
            ;;
        frontend)
            SERVICE_TYPE="static"
            ;;
        postgresql|rabbitmq|redis)
            SERVICE_TYPE="infrastructure"
            ;;
        *)
            SERVICE_TYPE="unknown"
            ;;
    esac

    log_debug "Service type: ${SERVICE_TYPE}"
}

# Check if Kubernetes namespace exists, create if it doesn't
ensure_namespace() {
    if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
        log_info "Namespace ${NAMESPACE} does not exist, creating..."
        kubectl create namespace "${NAMESPACE}"
        log_success "Namespace ${NAMESPACE} created"
    else
        log_debug "Namespace ${NAMESPACE} already exists"
    fi
}

# Check if Helm release already exists
check_release_exists() {
    if helm status "${SERVICE_NAME}" -n "${NAMESPACE}" &> /dev/null; then
        RELEASE_EXISTS=true
        log_debug "Helm release ${SERVICE_NAME} already exists in namespace ${NAMESPACE}"
    else
        RELEASE_EXISTS=false
        log_debug "Helm release ${SERVICE_NAME} does not exist in namespace ${NAMESPACE}"
    fi
}

# Get chart path based on service name
get_chart_path() {
    # Infrastructure services use their own charts
    if [[ "${SERVICE_TYPE}" == "infrastructure" ]]; then
        CHART_PATH="${REPO_ROOT}/infrastructure/kubernetes/charts/${SERVICE_NAME}"
    else
        # Application services use their own charts
        CHART_PATH="${REPO_ROOT}/infrastructure/kubernetes/charts/${SERVICE_NAME}"
    fi

    # Check if chart exists
    if [[ ! -d "${CHART_PATH}" ]]; then
        log_error "Chart not found at ${CHART_PATH}"
        exit 1
    fi

    log_debug "Using chart at ${CHART_PATH}"
}

# Get values files for the deployment
get_values_files() {
    # Common values file
    local common_values="${REPO_ROOT}/infrastructure/kubernetes/config/common.yaml"
    if [[ -f "${common_values}" ]]; then
        VALUES_ARGS+=("--values" "${common_values}")
        log_debug "Added common values file: ${common_values}"
    fi

    # Environment-specific common values
    local env_common_values="${REPO_ROOT}/infrastructure/kubernetes/config/${ENVIRONMENT}/common.yaml"
    if [[ -f "${env_common_values}" ]]; then
        VALUES_ARGS+=("--values" "${env_common_values}")
        log_debug "Added environment-specific common values file: ${env_common_values}"
    fi

    # Service-specific values
    local service_values="${REPO_ROOT}/infrastructure/kubernetes/config/${SERVICE_NAME}.yaml"
    if [[ -f "${service_values}" ]]; then
        VALUES_ARGS+=("--values" "${service_values}")
        log_debug "Added service-specific values file: ${service_values}"
    fi

    # Environment-specific service values
    local env_service_values="${REPO_ROOT}/infrastructure/kubernetes/config/${ENVIRONMENT}/${SERVICE_NAME}.yaml"
    if [[ -f "${env_service_values}" ]]; then
        VALUES_ARGS+=("--values" "${env_service_values}")
        log_debug "Added environment-specific service values file: ${env_service_values}"
    fi

    # Add any additional values files specified on the command line
    for values_file in "${VALUES_FILES[@]}"; do
        if [[ -f "${values_file}" ]]; then
            VALUES_ARGS+=("--values" "${values_file}")
            log_debug "Added additional values file: ${values_file}"
        else
            log_warning "Values file not found: ${values_file}"
        fi
    done
}

# Set deployment strategy based on service type
set_deployment_strategy() {
    # Default strategy is RollingUpdate
    local strategy="--set deployment.strategy.type=RollingUpdate"
    
    # For stateful services, use Recreate to avoid conflicts
    if [[ "${SERVICE_TYPE}" == "infrastructure" ]]; then
        strategy="--set deployment.strategy.type=Recreate"
    fi
    
    # For frontend, use BlueGreen if in production
    if [[ "${SERVICE_TYPE}" == "static" && "${ENVIRONMENT}" == "production" ]]; then
        strategy="--set deployment.strategy.type=BlueGreen"
    fi
    
    # Add strategy to set values
    SET_VALUES+=("${strategy#--set }")
    log_debug "Set deployment strategy: ${strategy}"
}

# Add deployment annotations for tracking and auditing
add_deployment_annotations() {
    # Get current timestamp
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Get Git commit information
    local git_commit=""
    if [[ -d "${REPO_ROOT}/.git" ]]; then
        git_commit=$(git -C "${REPO_ROOT}" rev-parse HEAD)
    fi
    
    # Add annotations
    SET_VALUES+=("deployment.annotations.kubernetes\.io/change-cause=Deployed by $(whoami) at ${timestamp} from commit ${git_commit}")
    SET_VALUES+=("deployment.annotations.app\.kubernetes\.io/deployed-by=$(whoami)")
    SET_VALUES+=("deployment.annotations.app\.kubernetes\.io/deployed-at=${timestamp}")
    if [[ -n "${git_commit}" ]]; then
        SET_VALUES+=("deployment.annotations.app\.kubernetes\.io/git-commit=${git_commit}")
    fi
    
    log_debug "Added deployment annotations for tracking and auditing"
}

# Prepare Helm command arguments
prepare_helm_args() {
    # Initialize arrays
    HELM_ARGS=()
    VALUES_ARGS=()
    
    # Get values files
    get_values_files
    
    # Set deployment strategy
    set_deployment_strategy
    
    # Add deployment annotations
    add_deployment_annotations
    
    # Add set values
    for set_value in "${SET_VALUES[@]}"; do
        HELM_ARGS+=("--set" "${set_value}")
    done
    
    # Add values files
    HELM_ARGS+=("${VALUES_ARGS[@]}")
    
    # Add namespace
    HELM_ARGS+=("--namespace" "${NAMESPACE}")
    
    # Add timeout
    HELM_ARGS+=("--timeout" "${TIMEOUT}")
    
    # Add wait flag if specified
    if [[ "${WAIT}" == "true" ]]; then
        HELM_ARGS+=("--wait")
    fi
    
    # Add dry-run flag if specified
    if [[ "${DRY_RUN}" == "true" ]]; then
        HELM_ARGS+=("--dry-run")
    fi
    
    # Add debug flag if specified
    if [[ "${DEBUG}" == "true" ]]; then
        HELM_ARGS+=("--debug")
    fi
    
    # Add chart version if specified
    if [[ -n "${CHART_VERSION}" ]]; then
        HELM_ARGS+=("--version" "${CHART_VERSION}")
    fi
    
    # Add service type
    HELM_ARGS+=("--set" "serviceType=${SERVICE_TYPE}")
    
    # Add environment
    HELM_ARGS+=("--set" "env.ENVIRONMENT=${ENVIRONMENT}")
    
    log_debug "Helm arguments: ${HELM_ARGS[*]}"
}

# Deploy the service using Helm
deploy_service() {
    # Ensure namespace exists
    ensure_namespace
    
    # Check if release already exists
    check_release_exists
    
    # Get chart path
    get_chart_path
    
    # Prepare Helm arguments
    prepare_helm_args
    
    # Deploy the service
    if [[ "${RELEASE_EXISTS}" == "true" ]]; then
        log_info "Upgrading existing Helm release ${SERVICE_NAME} in namespace ${NAMESPACE}..."
        helm upgrade "${SERVICE_NAME}" "${CHART_PATH}" "${HELM_ARGS[@]}"
    else
        log_info "Installing new Helm release ${SERVICE_NAME} in namespace ${NAMESPACE}..."
        helm install "${SERVICE_NAME}" "${CHART_PATH}" "${HELM_ARGS[@]}"
    fi
    
    # Check deployment status
    if [[ "${WAIT}" == "true" && "${DRY_RUN}" == "false" ]]; then
        check_deployment_status
    fi
}

# Check deployment status
check_deployment_status() {
    log_info "Checking deployment status..."
    
    # Get deployment name
    local deployment_name="${SERVICE_NAME}"
    
    # Wait for deployment to be ready
    if kubectl rollout status deployment "${deployment_name}" -n "${NAMESPACE}" --timeout="${TIMEOUT}"; then
        log_success "Deployment ${deployment_name} is ready"
        
        # Run post-deployment hooks if any
        run_post_deployment_hooks
    else
        log_error "Deployment ${deployment_name} failed to become ready within timeout"
        
        # Show pod status for debugging
        log_info "Pod status:"
        kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/name=${SERVICE_NAME}" -o wide
        
        # Show recent events
        log_info "Recent events:"
        kubectl get events -n "${NAMESPACE}" --sort-by=.metadata.creationTimestamp | tail -n 20
        
        # Show logs from failed pods
        log_info "Logs from failed pods:"
        for pod in $(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/name=${SERVICE_NAME}" -o jsonpath='{.items[?(@.status.phase!="Running")].metadata.name}'); do
            log_info "Logs from pod ${pod}:"
            kubectl logs "${pod}" -n "${NAMESPACE}" --tail=50 || true
        done
        
        exit 1
    fi
}

# Run post-deployment hooks
run_post_deployment_hooks() {
    log_info "Running post-deployment hooks..."
    
    # Service-specific initialization
    case "${SERVICE_NAME}" in
        # Database migrations for data-service
        data-service)
            log_info "Running database migrations..."
            # Get the pod name
            local pod_name=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/name=${SERVICE_NAME}" -o jsonpath='{.items[0].metadata.name}')
            # Run migrations
            kubectl exec "${pod_name}" -n "${NAMESPACE}" -- java -jar app.jar --spring.profiles.active=${ENVIRONMENT} --migrate
            log_success "Database migrations completed"
            ;;
        
        # Initialize RabbitMQ exchanges and queues
        rabbitmq)
            log_info "Initializing RabbitMQ exchanges and queues..."
            # Get the pod name
            local pod_name=$(kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/name=${SERVICE_NAME}" -o jsonpath='{.items[0].metadata.name}')
            # Apply RabbitMQ definitions
            kubectl cp "${REPO_ROOT}/infrastructure/kubernetes/config/${ENVIRONMENT}/rabbitmq-definitions.json" "${NAMESPACE}/${pod_name}:/tmp/definitions.json"
            kubectl exec "${pod_name}" -n "${NAMESPACE}" -- rabbitmqctl import_definitions /tmp/definitions.json
            log_success "RabbitMQ initialization completed"
            ;;
        
        # No post-deployment hooks for other services
        *)
            log_debug "No post-deployment hooks for ${SERVICE_NAME}"
            ;;
    esac
}

# Main function
main() {
    log_info "Starting deployment of ${SERVICE_NAME} to ${ENVIRONMENT} environment"
    
    # Parse command line arguments
    parse_args "$@"
    
    # Validate service
    validate_service
    
    # Deploy the service
    deploy_service
    
    log_success "Deployment of ${SERVICE_NAME} to ${ENVIRONMENT} environment completed successfully"
}

# Run main function with all arguments
main "$@"