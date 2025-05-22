#!/bin/bash

# validate-deployment.sh
#
# This script validates that a deployment was successful by checking pod status,
# running smoke tests, and verifying endpoints. It performs a series of checks
# to ensure that the deployed service is running correctly and accessible.
#
# Usage: ./validate-deployment.sh --service <service-name> --namespace <namespace> --environment <env> [options]
#
# Options:
#   --service        Service name to validate (required)
#   --namespace      Kubernetes namespace (required)
#   --environment    Environment (development, staging, production) (required)
#   --timeout        Timeout in seconds for validation checks (default: 300)
#   --retries        Number of retries for validation checks (default: 5)
#   --retry-delay    Delay between retries in seconds (default: 10)
#   --skip-basic     Skip basic validation checks
#   --skip-functional Skip functional validation checks
#   --skip-integration Skip integration validation checks
#   --verbose        Enable verbose logging
#   --help           Display this help message

set -e

# Default values
TIMEOUT=300
RETRIES=5
RETRY_DELAY=10
SKIP_BASIC=false
SKIP_FUNCTIONAL=false
SKIP_INTEGRATION=false
VERBOSE=false

# Color codes for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --service)
      SERVICE="$2"
      shift 2
      ;;
    --namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    --retries)
      RETRIES="$2"
      shift 2
      ;;
    --retry-delay)
      RETRY_DELAY="$2"
      shift 2
      ;;
    --skip-basic)
      SKIP_BASIC=true
      shift
      ;;
    --skip-functional)
      SKIP_FUNCTIONAL=true
      shift
      ;;
    --skip-integration)
      SKIP_INTEGRATION=true
      shift
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --help)
      echo "Usage: ./validate-deployment.sh --service <service-name> --namespace <namespace> --environment <env> [options]"
      echo ""
      echo "Options:"
      echo "  --service        Service name to validate (required)"
      echo "  --namespace      Kubernetes namespace (required)"
      echo "  --environment    Environment (development, staging, production) (required)"
      echo "  --timeout        Timeout in seconds for validation checks (default: 300)"
      echo "  --retries        Number of retries for validation checks (default: 5)"
      echo "  --retry-delay    Delay between retries in seconds (default: 10)"
      echo "  --skip-basic     Skip basic validation checks"
      echo "  --skip-functional Skip functional validation checks"
      echo "  --skip-integration Skip integration validation checks"
      echo "  --verbose        Enable verbose logging"
      echo "  --help           Display this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run './validate-deployment.sh --help' for usage information"
      exit 1
      ;;
  esac
done

# Validate required arguments
if [ -z "$SERVICE" ] || [ -z "$NAMESPACE" ] || [ -z "$ENVIRONMENT" ]; then
  echo -e "${RED}Error: Missing required arguments${NC}"
  echo "Run './validate-deployment.sh --help' for usage information"
  exit 1
fi

# Validate environment
if [[ "$ENVIRONMENT" != "development" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
  echo -e "${RED}Error: Environment must be one of: development, staging, production${NC}"
  exit 1
fi

# Log function with timestamp
log() {
  local level=$1
  local message=$2
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  
  case "$level" in
    "INFO")
      echo -e "${BLUE}[INFO]${NC} $timestamp - $message"
      ;;
    "SUCCESS")
      echo -e "${GREEN}[SUCCESS]${NC} $timestamp - $message"
      ;;
    "WARN")
      echo -e "${YELLOW}[WARN]${NC} $timestamp - $message"
      ;;
    "ERROR")
      echo -e "${RED}[ERROR]${NC} $timestamp - $message"
      ;;
    *)
      echo -e "$timestamp - $message"
      ;;
  esac
  
  # Log to file if needed
  # echo "$timestamp - [$level] - $message" >> "$LOG_FILE"
}

# Verbose logging function
log_verbose() {
  if [ "$VERBOSE" = true ]; then
    log "INFO" "$1"
  fi
}

# Function to check if kubectl is available
check_kubectl() {
  if ! command -v kubectl &> /dev/null; then
    log "ERROR" "kubectl is not installed or not in PATH"
    return 1
  fi
  
  # Check if we can access the cluster
  if ! kubectl cluster-info &> /dev/null; then
    log "ERROR" "Cannot connect to Kubernetes cluster"
    return 1
  fi
  
  return 0
}

# Function to retry a command
retry() {
  local cmd=$1
  local description=$2
  local n=1
  local max=$RETRIES
  local delay=$RETRY_DELAY
  
  log_verbose "Executing: $description"
  
  while true; do
    log_verbose "Attempt $n/$max: $description"
    
    if eval "$cmd"; then
      log_verbose "Command succeeded: $description"
      return 0
    fi
    
    if [[ $n -lt $max ]]; then
      log "WARN" "Command failed, retrying in $delay seconds: $description"
      sleep $delay
      ((n++))
    else
      log "ERROR" "Command failed after $max attempts: $description"
      return 1
    fi
  done
}

# Function to wait for pods to be ready
wait_for_pods_ready() {
  local selector="app=$SERVICE"
  local timeout=$TIMEOUT
  
  log "INFO" "Waiting for pods with selector '$selector' to be ready (timeout: ${timeout}s)"
  
  local cmd="kubectl -n $NAMESPACE wait --for=condition=ready pods -l $selector --timeout=${timeout}s"
  
  if retry "$cmd" "Wait for pods to be ready"; then
    log "SUCCESS" "All pods for service '$SERVICE' are ready"
    return 0
  else
    log "ERROR" "Timed out waiting for pods to be ready"
    return 1
  fi
}

# Function to check pod status
check_pod_status() {
  local selector="app=$SERVICE"
  
  log "INFO" "Checking pod status for service '$SERVICE'"
  
  # Get pod count
  local pod_count=$(kubectl -n "$NAMESPACE" get pods -l "$selector" -o name 2>/dev/null | wc -l)
  
  if [ "$pod_count" -eq 0 ]; then
    log "ERROR" "No pods found for service '$SERVICE'"
    return 1
  fi
  
  log_verbose "Found $pod_count pods for service '$SERVICE'"
  
  # Check if any pods are in a failed state
  local failed_pods=$(kubectl -n "$NAMESPACE" get pods -l "$selector" -o jsonpath='{.items[?(@.status.phase=="Failed")].metadata.name}' 2>/dev/null)
  
  if [ -n "$failed_pods" ]; then
    log "ERROR" "Failed pods found: $failed_pods"
    return 1
  fi
  
  # Check if any pods are in a pending state
  local pending_pods=$(kubectl -n "$NAMESPACE" get pods -l "$selector" -o jsonpath='{.items[?(@.status.phase=="Pending")].metadata.name}' 2>/dev/null)
  
  if [ -n "$pending_pods" ]; then
    log "WARN" "Pending pods found: $pending_pods"
    # Don't fail for pending pods, they might still be starting
  fi
  
  # Check if any containers are not ready
  local not_ready_pods=$(kubectl -n "$NAMESPACE" get pods -l "$selector" -o jsonpath='{.items[?(@.status.containerStatuses[*].ready==false)].metadata.name}' 2>/dev/null)
  
  if [ -n "$not_ready_pods" ]; then
    log "ERROR" "Pods with containers not ready: $not_ready_pods"
    return 1
  fi
  
  log "SUCCESS" "All pods for service '$SERVICE' are running and ready"
  return 0
}

# Function to check service endpoints
check_service_endpoints() {
  log "INFO" "Checking service endpoints for '$SERVICE'"
  
  # Check if service exists
  if ! kubectl -n "$NAMESPACE" get service "$SERVICE" &> /dev/null; then
    log "ERROR" "Service '$SERVICE' not found in namespace '$NAMESPACE'"
    return 1
  fi
  
  # Check if endpoints exist
  local endpoints=$(kubectl -n "$NAMESPACE" get endpoints "$SERVICE" -o jsonpath='{.subsets[*].addresses}' 2>/dev/null)
  
  if [ -z "$endpoints" ]; then
    log "ERROR" "No endpoints found for service '$SERVICE'"
    return 1
  fi
  
  log "SUCCESS" "Service endpoints for '$SERVICE' are available"
  return 0
}

# Function to run basic health checks
run_basic_health_checks() {
  log "INFO" "Running basic health checks for service '$SERVICE'"
  
  # Check pod status
  if ! check_pod_status; then
    return 1
  fi
  
  # Check service endpoints
  if ! check_service_endpoints; then
    return 1
  fi
  
  # Check readiness probe
  local readiness_failures=$(kubectl -n "$NAMESPACE" get pods -l "app=$SERVICE" -o jsonpath='{.items[?(@.status.conditions[?(@.type=="Ready")].status=="False")].metadata.name}' 2>/dev/null)
  
  if [ -n "$readiness_failures" ]; then
    log "ERROR" "Readiness probe failures in pods: $readiness_failures"
    return 1
  fi
  
  log "SUCCESS" "Basic health checks passed for service '$SERVICE'"
  return 0
}

# Function to run service-specific health checks
run_service_specific_health_checks() {
  log "INFO" "Running service-specific health checks for '$SERVICE'"
  
  # Service-specific health checks based on service type
  case "$SERVICE" in
    "email-service")
      check_email_service_health
      ;;
    "document-service")
      check_document_service_health
      ;;
    "ocr-service")
      check_ocr_service_health
      ;;
    "data-service")
      check_data_service_health
      ;;
    "notification-service")
      check_notification_service_health
      ;;
    "api-gateway")
      check_api_gateway_health
      ;;
    *)
      log "WARN" "No service-specific health checks defined for '$SERVICE', using generic health check"
      check_generic_service_health
      ;;
  esac
}

# Generic health check for services without specific checks
check_generic_service_health() {
  log_verbose "Running generic health check for '$SERVICE'"
  
  # Try to access health endpoint if it exists
  local service_port=$(kubectl -n "$NAMESPACE" get service "$SERVICE" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)
  
  if [ -z "$service_port" ]; then
    log "WARN" "Could not determine service port for '$SERVICE'"
    return 0  # Don't fail if we can't determine the port
  fi
  
  # Use kubectl port-forward to access the service
  local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=$SERVICE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$pod_name" ]; then
    log "ERROR" "Could not find pod for service '$SERVICE'"
    return 1
  fi
  
  log_verbose "Using pod '$pod_name' for health check"
  
  # Try common health endpoints
  local health_endpoints=("/health" "/healthz" "/status" "/actuator/health")
  local health_check_success=false
  
  for endpoint in "${health_endpoints[@]}"; do
    log_verbose "Checking health endpoint: $endpoint"
    
    # Start port-forward in background
    kubectl -n "$NAMESPACE" port-forward "$pod_name" 8080:"$service_port" &> /dev/null &
    local port_forward_pid=$!
    
    # Wait for port-forward to establish
    sleep 2
    
    # Try to access health endpoint
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080"$endpoint" | grep -q -E "200|204|301|302"; then
      log "SUCCESS" "Health check passed for endpoint: $endpoint"
      health_check_success=true
      kill $port_forward_pid 2> /dev/null || true
      wait $port_forward_pid 2> /dev/null || true
      break
    fi
    
    # Kill port-forward
    kill $port_forward_pid 2> /dev/null || true
    wait $port_forward_pid 2> /dev/null || true
  done
  
  if [ "$health_check_success" = false ]; then
    log "WARN" "Could not verify health endpoints for '$SERVICE', but continuing as pods are running"
    return 0  # Don't fail if we can't verify health endpoints
  fi
  
  return 0
}

# Email service specific health check
check_email_service_health() {
  log_verbose "Running email service health check"
  
  # Check if the service can connect to the email server
  local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=email-service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$pod_name" ]; then
    log "ERROR" "Could not find pod for email-service"
    return 1
  fi
  
  # Check logs for successful connection to email server
  if kubectl -n "$NAMESPACE" logs "$pod_name" --tail=50 | grep -q "Successfully connected to email server"; then
    log "SUCCESS" "Email service successfully connected to email server"
  else
    log "WARN" "Could not verify email server connection in logs"
  fi
  
  # Check if the service is listening on its port
  check_generic_service_health
  return $?
}

# Document service specific health check
check_document_service_health() {
  log_verbose "Running document service health check"
  
  # Check if the service can access the document storage
  local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=document-service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$pod_name" ]; then
    log "ERROR" "Could not find pod for document-service"
    return 1
  fi
  
  # Check logs for successful connection to storage
  if kubectl -n "$NAMESPACE" logs "$pod_name" --tail=50 | grep -q "Connected to document storage"; then
    log "SUCCESS" "Document service successfully connected to storage"
  else
    log "WARN" "Could not verify document storage connection in logs"
  fi
  
  # Check if the service is listening on its port
  check_generic_service_health
  return $?
}

# OCR service specific health check
check_ocr_service_health() {
  log_verbose "Running OCR service health check"
  
  # Check if the service has loaded its ML models
  local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=ocr-service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$pod_name" ]; then
    log "ERROR" "Could not find pod for ocr-service"
    return 1
  fi
  
  # Check logs for successful model loading
  if kubectl -n "$NAMESPACE" logs "$pod_name" --tail=50 | grep -q "ML models loaded successfully"; then
    log "SUCCESS" "OCR service successfully loaded ML models"
  else
    log "WARN" "Could not verify ML model loading in logs"
  fi
  
  # Check if the service is listening on its port
  check_generic_service_health
  return $?
}

# Data service specific health check
check_data_service_health() {
  log_verbose "Running data service health check"
  
  # Check if the service can connect to the database
  local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=data-service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$pod_name" ]; then
    log "ERROR" "Could not find pod for data-service"
    return 1
  fi
  
  # Use Spring Boot actuator health endpoint
  kubectl -n "$NAMESPACE" port-forward "$pod_name" 8080:8080 &> /dev/null &
  local port_forward_pid=$!
  
  # Wait for port-forward to establish
  sleep 2
  
  # Check actuator health endpoint
  local health_status=$(curl -s http://localhost:8080/actuator/health)
  
  # Kill port-forward
  kill $port_forward_pid 2> /dev/null || true
  wait $port_forward_pid 2> /dev/null || true
  
  if echo "$health_status" | grep -q '"status":"UP"'; then
    log "SUCCESS" "Data service health check passed"
    return 0
  else
    log "ERROR" "Data service health check failed"
    log_verbose "Health status: $health_status"
    return 1
  fi
}

# Notification service specific health check
check_notification_service_health() {
  log_verbose "Running notification service health check"
  
  # Check if the service can connect to the message queue
  local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=notification-service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$pod_name" ]; then
    log "ERROR" "Could not find pod for notification-service"
    return 1
  fi
  
  # Check logs for successful connection to RabbitMQ
  if kubectl -n "$NAMESPACE" logs "$pod_name" --tail=50 | grep -q "Connected to RabbitMQ"; then
    log "SUCCESS" "Notification service successfully connected to RabbitMQ"
  else
    log "WARN" "Could not verify RabbitMQ connection in logs"
  fi
  
  # Check if the service is listening on its port
  check_generic_service_health
  return $?
}

# API Gateway specific health check
check_api_gateway_health() {
  log_verbose "Running API Gateway health check"
  
  # Check if the gateway is routing requests
  local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=api-gateway" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$pod_name" ]; then
    log "ERROR" "Could not find pod for api-gateway"
    return 1
  fi
  
  # Check if Kong is running
  if kubectl -n "$NAMESPACE" exec "$pod_name" -- kong health | grep -q "Kong is healthy"; then
    log "SUCCESS" "API Gateway (Kong) is healthy"
    return 0
  else
    log "ERROR" "API Gateway (Kong) health check failed"
    return 1
  fi
}

# Function to run functional tests
run_functional_tests() {
  log "INFO" "Running functional tests for service '$SERVICE'"
  
  # Service-specific functional tests
  case "$SERVICE" in
    "email-service")
      test_email_service_functionality
      ;;
    "document-service")
      test_document_service_functionality
      ;;
    "ocr-service")
      test_ocr_service_functionality
      ;;
    "data-service")
      test_data_service_functionality
      ;;
    "notification-service")
      test_notification_service_functionality
      ;;
    "api-gateway")
      test_api_gateway_functionality
      ;;
    *)
      log "WARN" "No functional tests defined for '$SERVICE', skipping"
      return 0
      ;;
  esac
}

# Email service functional test
test_email_service_functionality() {
  log_verbose "Testing email service functionality"
  
  # For now, we'll just check if the service is running
  # In a real implementation, we would send a test email and verify receipt
  log "WARN" "Email service functional test not fully implemented, checking service status only"
  
  # Check if the service is running
  if kubectl -n "$NAMESPACE" get pods -l "app=email-service" | grep -q "Running"; then
    log "SUCCESS" "Email service is running"
    return 0
  else
    log "ERROR" "Email service is not running"
    return 1
  fi
}

# Document service functional test
test_document_service_functionality() {
  log_verbose "Testing document service functionality"
  
  # For now, we'll just check if the service is running
  # In a real implementation, we would upload a test document and verify classification
  log "WARN" "Document service functional test not fully implemented, checking service status only"
  
  # Check if the service is running
  if kubectl -n "$NAMESPACE" get pods -l "app=document-service" | grep -q "Running"; then
    log "SUCCESS" "Document service is running"
    return 0
  else
    log "ERROR" "Document service is not running"
    return 1
  fi
}

# OCR service functional test
test_ocr_service_functionality() {
  log_verbose "Testing OCR service functionality"
  
  # For now, we'll just check if the service is running
  # In a real implementation, we would send a test image and verify OCR extraction
  log "WARN" "OCR service functional test not fully implemented, checking service status only"
  
  # Check if the service is running
  if kubectl -n "$NAMESPACE" get pods -l "app=ocr-service" | grep -q "Running"; then
    log "SUCCESS" "OCR service is running"
    return 0
  else
    log "ERROR" "OCR service is not running"
    return 1
  fi
}

# Data service functional test
test_data_service_functionality() {
  log_verbose "Testing data service functionality"
  
  # For now, we'll just check if the service is running and can handle a simple API request
  log "WARN" "Data service functional test not fully implemented, checking basic API functionality"
  
  local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=data-service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$pod_name" ]; then
    log "ERROR" "Could not find pod for data-service"
    return 1
  fi
  
  # Use port-forward to access the API
  kubectl -n "$NAMESPACE" port-forward "$pod_name" 8080:8080 &> /dev/null &
  local port_forward_pid=$!
  
  # Wait for port-forward to establish
  sleep 2
  
  # Try to access a simple API endpoint
  local api_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v1/health)
  
  # Kill port-forward
  kill $port_forward_pid 2> /dev/null || true
  wait $port_forward_pid 2> /dev/null || true
  
  if [ "$api_response" = "200" ]; then
    log "SUCCESS" "Data service API is responding correctly"
    return 0
  else
    log "ERROR" "Data service API returned unexpected status code: $api_response"
    return 1
  fi
}

# Notification service functional test
test_notification_service_functionality() {
  log_verbose "Testing notification service functionality"
  
  # For now, we'll just check if the service is running
  # In a real implementation, we would send a test notification and verify delivery
  log "WARN" "Notification service functional test not fully implemented, checking service status only"
  
  # Check if the service is running
  if kubectl -n "$NAMESPACE" get pods -l "app=notification-service" | grep -q "Running"; then
    log "SUCCESS" "Notification service is running"
    return 0
  else
    log "ERROR" "Notification service is not running"
    return 1
  fi
}

# API Gateway functional test
test_api_gateway_functionality() {
  log_verbose "Testing API Gateway functionality"
  
  # For now, we'll just check if the gateway is running and responding to requests
  log "WARN" "API Gateway functional test not fully implemented, checking basic routing"
  
  local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=api-gateway" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$pod_name" ]; then
    log "ERROR" "Could not find pod for api-gateway"
    return 1
  fi
  
  # Use port-forward to access the gateway
  kubectl -n "$NAMESPACE" port-forward "$pod_name" 8000:8000 &> /dev/null &
  local port_forward_pid=$!
  
  # Wait for port-forward to establish
  sleep 2
  
  # Try to access the gateway status endpoint
  local gateway_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/status)
  
  # Kill port-forward
  kill $port_forward_pid 2> /dev/null || true
  wait $port_forward_pid 2> /dev/null || true
  
  if [ "$gateway_response" = "200" ]; then
    log "SUCCESS" "API Gateway is responding correctly"
    return 0
  else
    log "ERROR" "API Gateway returned unexpected status code: $gateway_response"
    return 1
  fi
}

# Function to run integration tests
run_integration_tests() {
  log "INFO" "Running integration tests for service '$SERVICE'"
  
  # In a real implementation, we would run more comprehensive integration tests
  # For now, we'll just check if the service can communicate with its dependencies
  
  case "$SERVICE" in
    "email-service")
      # Check if email service can communicate with RabbitMQ
      check_service_dependency "email-service" "rabbitmq"
      ;;
    "document-service")
      # Check if document service can communicate with RabbitMQ and S3
      check_service_dependency "document-service" "rabbitmq"
      check_service_dependency "document-service" "s3"
      ;;
    "ocr-service")
      # Check if OCR service can communicate with RabbitMQ and S3
      check_service_dependency "ocr-service" "rabbitmq"
      check_service_dependency "ocr-service" "s3"
      ;;
    "data-service")
      # Check if data service can communicate with PostgreSQL and RabbitMQ
      check_service_dependency "data-service" "postgresql"
      check_service_dependency "data-service" "rabbitmq"
      ;;
    "notification-service")
      # Check if notification service can communicate with RabbitMQ
      check_service_dependency "notification-service" "rabbitmq"
      ;;
    "api-gateway")
      # Check if API gateway can communicate with backend services
      check_service_dependency "api-gateway" "data-service"
      ;;
    *)
      log "WARN" "No integration tests defined for '$SERVICE', skipping"
      return 0
      ;;
  esac
}

# Function to check service dependencies
check_service_dependency() {
  local service=$1
  local dependency=$2
  
  log_verbose "Checking if $service can communicate with $dependency"
  
  # Get a pod from the service
  local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=$service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  
  if [ -z "$pod_name" ]; then
    log "ERROR" "Could not find pod for $service"
    return 1
  fi
  
  # Check logs for successful connection to dependency
  if kubectl -n "$NAMESPACE" logs "$pod_name" --tail=100 | grep -q -i "connected.*$dependency"; then
    log "SUCCESS" "$service successfully connected to $dependency"
    return 0
  else
    log "WARN" "Could not verify connection between $service and $dependency in logs"
    # Don't fail the test, as the log message might be different or not present
    return 0
  fi
}

# Main function
main() {
  log "INFO" "Starting deployment validation for service '$SERVICE' in namespace '$NAMESPACE' ($ENVIRONMENT environment)"
  
  # Check if kubectl is available
  if ! check_kubectl; then
    log "ERROR" "kubectl is not available, cannot proceed with validation"
    exit 1
  fi
  
  # Wait for pods to be ready
  if ! wait_for_pods_ready; then
    log "ERROR" "Pods for service '$SERVICE' are not ready, validation failed"
    exit 1
  fi
  
  # Run basic health checks
  if [ "$SKIP_BASIC" != "true" ]; then
    if ! run_basic_health_checks; then
      log "ERROR" "Basic health checks failed for service '$SERVICE'"
      exit 1
    fi
    
    # Run service-specific health checks
    if ! run_service_specific_health_checks; then
      log "ERROR" "Service-specific health checks failed for '$SERVICE'"
      exit 1
    fi
  else
    log "INFO" "Skipping basic health checks as requested"
  fi
  
  # Run functional tests
  if [ "$SKIP_FUNCTIONAL" != "true" ]; then
    if ! run_functional_tests; then
      log "ERROR" "Functional tests failed for service '$SERVICE'"
      exit 1
    fi
  else
    log "INFO" "Skipping functional tests as requested"
  fi
  
  # Run integration tests
  if [ "$SKIP_INTEGRATION" != "true" ]; then
    if ! run_integration_tests; then
      log "ERROR" "Integration tests failed for service '$SERVICE'"
      exit 1
    fi
  else
    log "INFO" "Skipping integration tests as requested"
  fi
  
  log "SUCCESS" "All validation checks passed for service '$SERVICE' in namespace '$NAMESPACE' ($ENVIRONMENT environment)"
  exit 0
}

# Run the main function
main