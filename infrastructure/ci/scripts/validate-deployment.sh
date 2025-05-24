#!/bin/bash

# validate-deployment.sh
#
# This script validates that a Kubernetes deployment was successful by performing
# a series of progressive checks with increasing complexity:
# 1. Basic pod status and readiness checks
# 2. Service-specific health endpoint verification
# 3. API endpoint validation with authentication
# 4. Functional smoke tests for critical paths
# 5. Integration tests for service interactions
#
# The script is designed to work with the MCA Application Processing System microservices
# and supports different service types (Node.js, Java, Python) with appropriate health checks.
#
# For the MCA Application Processing System, this script validates:
# - Email Service (Node.js/Nodemailer)
# - Document Service (Python/scikit-learn)
# - OCR Service (Python/TensorFlow)
# - Data Service (Java/Spring Boot)
# - Notification Service (Node.js)
# - API Gateway (Kong)
#
# Usage: ./validate-deployment.sh [options]
#
# Options:
#   -n, --namespace <namespace>       Kubernetes namespace (default: current namespace)
#   -s, --service <service-name>      Service name to validate
#   -t, --timeout <seconds>           Timeout for validation in seconds (default: 300)
#   -r, --retries <count>             Number of retries for transient issues (default: 5)
#   -l, --level <1-5>                 Validation level (default: 3)
#                                     1: Basic pod status
#                                     2: Health endpoints
#                                     3: API verification
#                                     4: Functional tests
#                                     5: Integration tests
#   -w, --wait <seconds>              Initial wait before validation (default: 10)
#   -v, --verbose                     Enable verbose output
#   -h, --help                        Show this help message

set -eo pipefail

# Default values
NAMESPACE=""
SERVICE=""
TIMEOUT=300
RETRIES=5
VALIDATION_LEVEL=3
INITIAL_WAIT=10
VERBOSE=false
JWT_TOKEN=""
API_GATEWAY_URL=""

# Color codes for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -n|--namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    -s|--service)
      SERVICE="$2"
      shift 2
      ;;
    -t|--timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    -r|--retries)
      RETRIES="$2"
      shift 2
      ;;
    -l|--level)
      VALIDATION_LEVEL="$2"
      shift 2
      ;;
    -w|--wait)
      INITIAL_WAIT="$2"
      shift 2
      ;;
    -v|--verbose)
      VERBOSE=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  -n, --namespace <namespace>       Kubernetes namespace (default: current namespace)"
      echo "  -s, --service <service-name>      Service name to validate"
      echo "  -t, --timeout <seconds>           Timeout for validation in seconds (default: 300)"
      echo "  -r, --retries <count>             Number of retries for transient issues (default: 5)"
      echo "  -l, --level <1-5>                 Validation level (default: 3)"
      echo "                                    1: Basic pod status"
      echo "                                    2: Health endpoints"
      echo "                                    3: API verification"
      echo "                                    4: Functional tests"
      echo "                                    5: Integration tests"
      echo "  -w, --wait <seconds>              Initial wait before validation (default: 10)"
      echo "  -v, --verbose                     Enable verbose output"
      echo "  -h, --help                        Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Determine namespace if not provided
if [[ -z "$NAMESPACE" ]]; then
  NAMESPACE=$(kubectl config view --minify --output 'jsonpath={..namespace}')
  if [[ -z "$NAMESPACE" ]]; then
    NAMESPACE="default"
  fi
fi

# Validate required parameters
if [[ -z "$SERVICE" ]]; then
  echo -e "${RED}Error: Service name is required. Use -s or --service to specify.${NC}"
  exit 1
fi

# Log function with timestamp and service name
log() {
  local level=$1
  local message=$2
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  
  case $level in
    "INFO")
      echo -e "${BLUE}[$timestamp] [INFO] [$SERVICE] $message${NC}"
      ;;
    "SUCCESS")
      echo -e "${GREEN}[$timestamp] [SUCCESS] [$SERVICE] $message${NC}"
      ;;
    "WARN")
      echo -e "${YELLOW}[$timestamp] [WARN] [$SERVICE] $message${NC}"
      ;;
    "ERROR")
      echo -e "${RED}[$timestamp] [ERROR] [$SERVICE] $message${NC}"
      ;;
    *)
      if [[ "$VERBOSE" == "true" ]]; then
        echo -e "[$timestamp] [DEBUG] [$SERVICE] $message"
      fi
      ;;
  esac
}

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check for required tools
for cmd in kubectl curl jq; do
  if ! command_exists "$cmd"; then
    log "ERROR" "Required command '$cmd' not found. Please install it and try again."
    exit 1
  fi
done

# Wait for initial delay before starting validation
if [[ $INITIAL_WAIT -gt 0 ]]; then
  log "INFO" "Waiting for $INITIAL_WAIT seconds before starting validation..."
  sleep $INITIAL_WAIT
fi

# Determine service type (nodejs, java, python) based on labels or annotations
determine_service_type() {
  local service_type
  
  # Try to get service type from pod labels
  service_type=$(kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/name=$SERVICE" -o jsonpath='{.items[0].metadata.labels.serviceType}' 2>/dev/null)
  
  # If not found in labels, try to infer from the service name
  if [[ -z "$service_type" ]]; then
    if [[ "$SERVICE" == *-service ]]; then
      case "$SERVICE" in
        email-service|notification-service)
          service_type="nodejs"
          ;;
        data-service)
          service_type="java"
          ;;
        document-service|ocr-service)
          service_type="python"
          ;;
        *)
          service_type="unknown"
          ;;
      esac
    else
      service_type="unknown"
    fi
  fi
  
  echo "$service_type"
}

# Get health check endpoint based on service type
get_health_endpoint() {
  local service_type=$1
  local endpoint
  
  case "$service_type" in
    "nodejs")
      endpoint="/health"
      ;;
    "java")
      endpoint="/actuator/health"
      ;;
    "python")
      endpoint="/health/live"
      ;;
    *)
      endpoint="/health"
      ;;
  esac
  
  echo "$endpoint"
}

# Get readiness check endpoint based on service type
get_readiness_endpoint() {
  local service_type=$1
  local endpoint
  
  case "$service_type" in
    "nodejs")
      endpoint="/health"
      ;;
    "java")
      endpoint="/actuator/health/readiness"
      ;;
    "python")
      endpoint="/health/ready"
      ;;
    *)
      endpoint="/health"
      ;;
  esac
  
  echo "$endpoint"
}

# Function to retry a command with exponential backoff
retry_with_backoff() {
  local max_attempts=$1
  local timeout=$2
  local attempt=1
  local exit_code=0
  local wait_time=5
  local command=${@:3}
  
  while [[ $attempt -le $max_attempts ]]; do
    log "DEBUG" "Attempt $attempt/$max_attempts: $command"
    
    # Execute the command with a timeout
    timeout $timeout bash -c "$command"
    exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
      return 0
    fi
    
    log "WARN" "Attempt $attempt failed with exit code $exit_code. Retrying in $wait_time seconds..."
    sleep $wait_time
    
    # Exponential backoff with a cap
    wait_time=$(( wait_time * 2 ))
    if [[ $wait_time -gt 60 ]]; then
      wait_time=60
    fi
    
    attempt=$(( attempt + 1 ))
  done
  
  log "ERROR" "All $max_attempts attempts failed!"
  return $exit_code
}

# Function to get a JWT token for authenticated API calls
get_jwt_token() {
  # This is a placeholder. In a real environment, you would implement
  # proper authentication to get a valid JWT token.
  # For example, calling an auth endpoint with service credentials.
  
  # For now, we'll check if there's a token in the environment
  if [[ -n "$MCA_AUTH_TOKEN" ]]; then
    echo "$MCA_AUTH_TOKEN"
    return 0
  fi
  
  # If running in CI, try to get token from a predefined secret
  if [[ -n "$CI" && -f "/var/run/secrets/kubernetes.io/serviceaccount/token" ]]; then
    # Use the service account token for authentication
    cat "/var/run/secrets/kubernetes.io/serviceaccount/token"
    return 0
  fi
  
  # If we can't get a token, return an empty string
  echo ""
  return 1
}

# Function to get API Gateway URL
get_api_gateway_url() {
  # Try to get the API Gateway service URL
  local gateway_service="api-gateway"
  local gateway_url
  
  # First try to get the ingress URL if available
  gateway_url=$(kubectl get ingress -n "$NAMESPACE" "$gateway_service" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
  
  if [[ -z "$gateway_url" ]]; then
    # Try to get the hostname if IP is not available
    gateway_url=$(kubectl get ingress -n "$NAMESPACE" "$gateway_service" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
  fi
  
  if [[ -z "$gateway_url" ]]; then
    # If ingress is not available, try to get the service ClusterIP
    gateway_url=$(kubectl get service -n "$NAMESPACE" "$gateway_service" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)
    
    if [[ -n "$gateway_url" ]]; then
      local port=$(kubectl get service -n "$NAMESPACE" "$gateway_service" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)
      if [[ -n "$port" ]]; then
        gateway_url="$gateway_url:$port"
      fi
    fi
  fi
  
  # If we still don't have a URL, use a default for development
  if [[ -z "$gateway_url" ]]; then
    log "WARN" "Could not determine API Gateway URL. Using default for development."
    gateway_url="api-gateway:8000"
  fi
  
  # Ensure the URL has a protocol
  if [[ "$gateway_url" != http* ]]; then
    gateway_url="http://$gateway_url"
  fi
  
  echo "$gateway_url"
}

# Validation Level 1: Check pod status and readiness
validate_pod_status() {
  log "INFO" "Starting pod status validation (Level 1)..."
  
  # Check if pods exist for the service
  local pod_count=$(kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/name=$SERVICE" --no-headers 2>/dev/null | wc -l)
  
  if [[ $pod_count -eq 0 ]]; then
    log "ERROR" "No pods found for service '$SERVICE' in namespace '$NAMESPACE'"
    return 1
  fi
  
  log "INFO" "Found $pod_count pods for service '$SERVICE'"
  
  # Check if all pods are running and ready
  local command=""
  command+="kubectl get pods -n \"$NAMESPACE\" -l \"app.kubernetes.io/name=$SERVICE\" -o json | "
  command+="jq -e '.items | map(select(.status.phase == \"Running\")) | length == (.items | length) and length > 0'"
  
  if ! retry_with_backoff $RETRIES $TIMEOUT "$command"; then
    log "ERROR" "Not all pods are in Running state for service '$SERVICE'"
    kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/name=$SERVICE" -o wide
    return 1
  fi
  
  # Check if all containers in pods are ready
  command=""
  command+="kubectl get pods -n \"$NAMESPACE\" -l \"app.kubernetes.io/name=$SERVICE\" -o json | "
  command+="jq -e '.items | map(.status.containerStatuses[] | select(.ready == true)) | length == (.items | map(.status.containerStatuses | length) | add)'"
  
  if ! retry_with_backoff $RETRIES $TIMEOUT "$command"; then
    log "ERROR" "Not all containers are ready for service '$SERVICE'"
    kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/name=$SERVICE" -o wide
    return 1
  fi
  
  log "SUCCESS" "All pods for service '$SERVICE' are running and ready"
  return 0
}

# Validation Level 2: Check health endpoints
validate_health_endpoints() {
  log "INFO" "Starting health endpoint validation (Level 2)..."
  
  # Determine service type
  local service_type=$(determine_service_type)
  log "INFO" "Detected service type: $service_type"
  
  # Get health and readiness endpoints
  local health_endpoint=$(get_health_endpoint "$service_type")
  local readiness_endpoint=$(get_readiness_endpoint "$service_type")
  
  # Get service URL
  local service_url
  service_url=$(kubectl get service -n "$NAMESPACE" "$SERVICE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)
  
  if [[ -z "$service_url" ]]; then
    log "ERROR" "Could not determine service URL for '$SERVICE'"
    return 1
  fi
  
  # Get service port
  local service_port
  service_port=$(kubectl get service -n "$NAMESPACE" "$SERVICE" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)
  
  if [[ -z "$service_port" ]]; then
    log "WARN" "Could not determine service port for '$SERVICE', using default port 8080"
    service_port=8080
  fi
  
  # Check health endpoint
  log "INFO" "Checking health endpoint: http://$service_url:$service_port$health_endpoint"
  
  local command="curl -s -o /dev/null -w '%{http_code}' http://$service_url:$service_port$health_endpoint | grep -q '200'"
  
  if ! retry_with_backoff $RETRIES $TIMEOUT "$command"; then
    log "ERROR" "Health check failed for service '$SERVICE' at endpoint '$health_endpoint'"
    return 1
  fi
  
  log "SUCCESS" "Health check passed for service '$SERVICE'"
  
  # Check readiness endpoint if different from health endpoint
  if [[ "$readiness_endpoint" != "$health_endpoint" ]]; then
    log "INFO" "Checking readiness endpoint: http://$service_url:$service_port$readiness_endpoint"
    
    command="curl -s -o /dev/null -w '%{http_code}' http://$service_url:$service_port$readiness_endpoint | grep -q '200'"
    
    if ! retry_with_backoff $RETRIES $TIMEOUT "$command"; then
      log "ERROR" "Readiness check failed for service '$SERVICE' at endpoint '$readiness_endpoint'"
      return 1
    fi
    
    log "SUCCESS" "Readiness check passed for service '$SERVICE'"
  fi
  
  return 0
}

# Validation Level 3: Verify API endpoints through API Gateway
validate_api_endpoints() {
  log "INFO" "Starting API endpoint validation (Level 3)..."
  
  # Get API Gateway URL
  if [[ -z "$API_GATEWAY_URL" ]]; then
    API_GATEWAY_URL=$(get_api_gateway_url)
  fi
  
  log "INFO" "Using API Gateway URL: $API_GATEWAY_URL"
  
  # Get JWT token for authenticated requests if needed
  if [[ -z "$JWT_TOKEN" ]]; then
    JWT_TOKEN=$(get_jwt_token)
    if [[ -z "$JWT_TOKEN" ]]; then
      log "WARN" "Could not obtain JWT token. Some API validations may fail if authentication is required."
    else
      log "INFO" "Successfully obtained JWT token for API validation"
    fi
  fi
  
  # Define service-specific API endpoints to check
  local endpoints=()
  
  case "$SERVICE" in
    "email-service")
      endpoints=("/api/v1/email/status")
      ;;
    "document-service")
      endpoints=("/api/v1/documents/types")
      ;;
    "ocr-service")
      endpoints=("/api/v1/ocr/status")
      ;;
    "data-service")
      endpoints=("/api/v1/applications")
      ;;
    "notification-service")
      endpoints=("/api/v1/webhooks")
      ;;
    "api-gateway")
      endpoints=("/api/v1/status")
      ;;
    *)
      log "WARN" "No predefined API endpoints for service '$SERVICE'. Skipping API validation."
      return 0
      ;;
  esac
  
  # Check each endpoint
  for endpoint in "${endpoints[@]}"; do
    log "INFO" "Validating API endpoint: $API_GATEWAY_URL$endpoint"
    
    local curl_command="curl -s -o /dev/null -w '%{http_code}'"
    
    # Add authentication header if token is available
    if [[ -n "$JWT_TOKEN" ]]; then
      curl_command+="  -H 'Authorization: Bearer $JWT_TOKEN'"
    fi
    
    curl_command+=" $API_GATEWAY_URL$endpoint | grep -q '2[0-9][0-9]'"
    
    if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
      log "ERROR" "API validation failed for endpoint '$endpoint'"
      return 1
    fi
    
    log "SUCCESS" "API validation passed for endpoint '$endpoint'"
  done
  
  return 0
}

# Validation Level 4: Run functional smoke tests
validate_functional_tests() {
  log "INFO" "Starting functional smoke tests (Level 4)..."
  
  # Define service-specific functional tests
  case "$SERVICE" in
    "email-service")
      # Test email monitoring status
      log "INFO" "Testing email monitoring functionality"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      local curl_command="curl -s"
      if [[ -n "$JWT_TOKEN" ]]; then
        curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
      fi
      
      curl_command+=" $API_GATEWAY_URL/api/v1/email/status | jq -e '.status == \"active\"'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "Email service functional test failed: monitoring not active"
        return 1
      fi
      
      log "SUCCESS" "Email service functional test passed"
      ;;
      
    "document-service")
      # Test document classification capability
      log "INFO" "Testing document classification functionality"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      local curl_command="curl -s"
      if [[ -n "$JWT_TOKEN" ]]; then
        curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
      fi
      
      curl_command+=" $API_GATEWAY_URL/api/v1/documents/types | jq -e 'length > 0'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "Document service functional test failed: could not retrieve document types"
        return 1
      fi
      
      log "SUCCESS" "Document service functional test passed"
      ;;
      
    "ocr-service")
      # Test OCR service status
      log "INFO" "Testing OCR service functionality"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      local curl_command="curl -s"
      if [[ -n "$JWT_TOKEN" ]]; then
        curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
      fi
      
      curl_command+=" $API_GATEWAY_URL/api/v1/ocr/status | jq -e '.status == \"ready\"'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "OCR service functional test failed: service not ready"
        return 1
      fi
      
      log "SUCCESS" "OCR service functional test passed"
      ;;
      
    "data-service")
      # Test data service API
      log "INFO" "Testing data service functionality"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      local curl_command="curl -s"
      if [[ -n "$JWT_TOKEN" ]]; then
        curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
      fi
      
      # Check if we can retrieve applications (even if empty)
      curl_command+=" $API_GATEWAY_URL/api/v1/applications?limit=1 | jq -e 'has(\"data\")'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "Data service functional test failed: could not retrieve applications"
        return 1
      fi
      
      log "SUCCESS" "Data service functional test passed"
      ;;
      
    "notification-service")
      # Test notification service webhook configuration
      log "INFO" "Testing notification service functionality"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      local curl_command="curl -s"
      if [[ -n "$JWT_TOKEN" ]]; then
        curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
      fi
      
      curl_command+=" $API_GATEWAY_URL/api/v1/webhooks | jq -e 'has(\"webhooks\")'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "Notification service functional test failed: could not retrieve webhooks"
        return 1
      fi
      
      log "SUCCESS" "Notification service functional test passed"
      ;;
      
    "api-gateway")
      # Test API Gateway routes
      log "INFO" "Testing API Gateway functionality"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      local curl_command="curl -s $API_GATEWAY_URL/api/v1/status | jq -e '.status == \"ok\"'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "API Gateway functional test failed: status check failed"
        return 1
      fi
      
      log "SUCCESS" "API Gateway functional test passed"
      ;;
      
    *)
      log "WARN" "No functional tests defined for service '$SERVICE'. Skipping functional validation."
      return 0
      ;;
  esac
  
  return 0
}

# Validation Level 5: Run integration tests
validate_integration_tests() {
  log "INFO" "Starting integration tests (Level 5)..."
  
  # Define service-specific integration tests that verify interactions with other services
  case "$SERVICE" in
    "email-service")
      # Test email to document service integration
      log "INFO" "Testing email to document service integration"
      
      # This would typically involve a more complex test that simulates an email being processed
      # For now, we'll just check if the service can communicate with RabbitMQ
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      local curl_command="curl -s"
      if [[ -n "$JWT_TOKEN" ]]; then
        curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
      fi
      
      curl_command+=" $API_GATEWAY_URL/api/v1/email/queue-status | jq -e '.connected == true'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "Email service integration test failed: not connected to message queue"
        return 1
      fi
      
      log "SUCCESS" "Email service integration test passed"
      ;;
      
    "document-service")
      # Test document to OCR service integration
      log "INFO" "Testing document to OCR service integration"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      local curl_command="curl -s"
      if [[ -n "$JWT_TOKEN" ]]; then
        curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
      fi
      
      curl_command+=" $API_GATEWAY_URL/api/v1/documents/ocr-status | jq -e '.connected == true'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "Document service integration test failed: OCR service connection issue"
        return 1
      fi
      
      log "SUCCESS" "Document service integration test passed"
      ;;
      
    "ocr-service")
      # Test OCR to data service integration
      log "INFO" "Testing OCR to data service integration"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      local curl_command="curl -s"
      if [[ -n "$JWT_TOKEN" ]]; then
        curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
      fi
      
      curl_command+=" $API_GATEWAY_URL/api/v1/ocr/data-service-status | jq -e '.connected == true'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "OCR service integration test failed: data service connection issue"
        return 1
      fi
      
      log "SUCCESS" "OCR service integration test passed"
      ;;
      
    "data-service")
      # Test data service to notification service integration
      log "INFO" "Testing data service to notification service integration"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      local curl_command="curl -s"
      if [[ -n "$JWT_TOKEN" ]]; then
        curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
      fi
      
      curl_command+=" $API_GATEWAY_URL/api/v1/applications/notification-status | jq -e '.connected == true'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "Data service integration test failed: notification service connection issue"
        return 1
      fi
      
      log "SUCCESS" "Data service integration test passed"
      ;;
      
    "notification-service")
      # Test notification service webhook delivery
      log "INFO" "Testing notification service webhook delivery"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      local curl_command="curl -s"
      if [[ -n "$JWT_TOKEN" ]]; then
        curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
      fi
      
      # Test webhook ping functionality
      curl_command+=" -X POST $API_GATEWAY_URL/api/v1/webhooks/test-ping | jq -e '.success == true'"
      
      if ! retry_with_backoff $RETRIES $TIMEOUT "$curl_command"; then
        log "ERROR" "Notification service integration test failed: webhook ping failed"
        return 1
      fi
      
      log "SUCCESS" "Notification service integration test passed"
      ;;
      
    "api-gateway")
      # Test API Gateway service routing
      log "INFO" "Testing API Gateway service routing"
      
      if [[ -z "$API_GATEWAY_URL" ]]; then
        API_GATEWAY_URL=$(get_api_gateway_url)
      fi
      
      if [[ -z "$JWT_TOKEN" ]]; then
        JWT_TOKEN=$(get_jwt_token)
      fi
      
      # Test routing to multiple services
      local services_to_check=("email" "documents" "applications" "webhooks")
      local all_passed=true
      
      for svc in "${services_to_check[@]}"; do
        log "INFO" "Checking routing to $svc service"
        
        local curl_command="curl -s -o /dev/null -w '%{http_code}'"
        if [[ -n "$JWT_TOKEN" ]]; then
          curl_command+=" -H 'Authorization: Bearer $JWT_TOKEN'"
        fi
        
        curl_command+=" $API_GATEWAY_URL/api/v1/$svc | grep -q '2[0-9][0-9]'"
        
        if ! retry_with_backoff 2 $TIMEOUT "$curl_command"; then
          log "WARN" "API Gateway routing test to $svc service failed"
          all_passed=false
        else
          log "SUCCESS" "API Gateway routing to $svc service works"
        fi
      done
      
      if [[ "$all_passed" != "true" ]]; then
        log "ERROR" "API Gateway integration test failed: some service routes are not working"
        return 1
      fi
      
      log "SUCCESS" "API Gateway integration test passed"
      ;;
      
    *)
      log "WARN" "No integration tests defined for service '$SERVICE'. Skipping integration validation."
      return 0
      ;;
  esac
  
  return 0
}

# Main validation function that runs checks based on the validation level
run_validation() {
  log "INFO" "Starting deployment validation for service '$SERVICE' in namespace '$NAMESPACE'"
  log "INFO" "Validation level: $VALIDATION_LEVEL, Timeout: ${TIMEOUT}s, Retries: $RETRIES"
  
  # Level 1: Basic pod status
  if ! validate_pod_status; then
    log "ERROR" "Pod status validation failed. Deployment is not successful."
    return 1
  fi
  
  # If validation level is 1, we're done
  if [[ $VALIDATION_LEVEL -eq 1 ]]; then
    log "SUCCESS" "Validation level 1 passed for service '$SERVICE'"
    return 0
  fi
  
  # Level 2: Health endpoints
  if ! validate_health_endpoints; then
    log "ERROR" "Health endpoint validation failed. Deployment is not successful."
    return 1
  fi
  
  # If validation level is 2, we're done
  if [[ $VALIDATION_LEVEL -eq 2 ]]; then
    log "SUCCESS" "Validation level 2 passed for service '$SERVICE'"
    return 0
  fi
  
  # Level 3: API endpoints
  if ! validate_api_endpoints; then
    log "ERROR" "API endpoint validation failed. Deployment is not successful."
    return 1
  fi
  
  # If validation level is 3, we're done
  if [[ $VALIDATION_LEVEL -eq 3 ]]; then
    log "SUCCESS" "Validation level 3 passed for service '$SERVICE'"
    return 0
  fi
  
  # Level 4: Functional tests
  if ! validate_functional_tests; then
    log "ERROR" "Functional test validation failed. Deployment is not successful."
    return 1
  fi
  
  # If validation level is 4, we're done
  if [[ $VALIDATION_LEVEL -eq 4 ]]; then
    log "SUCCESS" "Validation level 4 passed for service '$SERVICE'"
    return 0
  fi
  
  # Level 5: Integration tests
  if ! validate_integration_tests; then
    log "ERROR" "Integration test validation failed. Deployment is not successful."
    return 1
  fi
  
  # All validation levels passed
  log "SUCCESS" "All validation levels passed for service '$SERVICE'"
  return 0
}

# Run the validation
if run_validation; then
  log "SUCCESS" "Deployment validation successful for service '$SERVICE'"
  exit 0
else
  log "ERROR" "Deployment validation failed for service '$SERVICE'"
  exit 1
fi