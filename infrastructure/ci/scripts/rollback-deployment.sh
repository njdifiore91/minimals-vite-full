#!/bin/bash

# rollback-deployment.sh
#
# This script performs rollbacks in case of deployment failures by reverting to previous
# known-good versions. It identifies the previous version, executes rollback commands,
# and verifies rollback success to ensure service availability is restored quickly.
#
# Part of the MCA Application Processing System infrastructure.
#
# Usage: ./rollback-deployment.sh --service <service-name> --namespace <namespace> --environment <env> [options]

set -eo pipefail

# Default values
TIMEOUT=300
RETRIES=3
RETRY_DELAY=10
VERBOSE=false
FORCE=false
NOTIFY=true
INCIDENT_SYSTEM="pagerduty"
ROLLBACK_VERSION=""
PROGRESSIVE=false
SKIP_VALIDATION=false

# MCA Application Processing System specific settings
MCA_CONFIG_DIR="${REPO_ROOT}/infrastructure/ci/config"
MCA_LOGS_DIR="${REPO_ROOT}/logs"

# Color codes for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Script directory for relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

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
    --version)
      ROLLBACK_VERSION="$2"
      shift 2
      ;;
    --progressive)
      PROGRESSIVE=true
      shift
      ;;
    --skip-validation)
      SKIP_VALIDATION=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --no-notify)
      NOTIFY=false
      shift
      ;;
    --incident-system)
      INCIDENT_SYSTEM="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --help)
      echo "Usage: ./rollback-deployment.sh --service <service-name> --namespace <namespace> --environment <env> [options]"
      echo ""
      echo "Options:"
      echo "  --service          Service name to rollback (required)"
      echo "  --namespace        Kubernetes namespace (required)"
      echo "  --environment      Environment (development, staging, production) (required)"
      echo "  --timeout          Timeout in seconds for rollback operations (default: 300)"
      echo "  --retries          Number of retries for rollback operations (default: 3)"
      echo "  --retry-delay      Delay between retries in seconds (default: 10)"
      echo "  --version          Specific version to rollback to (default: previous successful release)"
      echo "  --progressive      Use progressive rollback for complex services"
      echo "  --skip-validation  Skip validation after rollback"
      echo "  --force            Force rollback even if validation fails"
      echo "  --no-notify        Disable notifications"
      echo "  --incident-system  Incident management system to use (default: pagerduty)"
      echo "  --verbose          Enable verbose logging"
      echo "  --help             Display this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run './rollback-deployment.sh --help' for usage information"
      exit 1
      ;;
  esac
done

# Validate required arguments
if [ -z "$SERVICE" ] || [ -z "$NAMESPACE" ] || [ -z "$ENVIRONMENT" ]; then
  echo -e "${RED}Error: Missing required arguments${NC}"
  echo "Run './rollback-deployment.sh --help' for usage information"
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
  
  # Log to file
  local log_dir="${REPO_ROOT}/logs/rollbacks"
  mkdir -p "$log_dir"
  local log_file="${log_dir}/${SERVICE}-${ENVIRONMENT}-$(date +"%Y%m%d").log"
  echo "$timestamp - [$level] - $message" >> "$log_file"
}

# Verbose logging function
log_verbose() {
  if [ "$VERBOSE" = true ]; then
    log "INFO" "$1"
  fi
}

# Function to check if helm is available
check_helm() {
  if ! command -v helm &> /dev/null; then
    log "ERROR" "helm is not installed or not in PATH"
    return 1
  fi
  
  # Check if we can access the cluster
  if ! helm list -n "$NAMESPACE" &> /dev/null; then
    log "ERROR" "Cannot connect to Kubernetes cluster or access namespace $NAMESPACE"
    return 1
  fi
  
  return 0
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

# Function to identify the previous known-good version
identify_previous_version() {
  log "INFO" "Identifying previous known-good version for $SERVICE in namespace $NAMESPACE"
  
  # Check if a specific version was requested
  if [ -n "$ROLLBACK_VERSION" ]; then
    log "INFO" "Using specified rollback version: $ROLLBACK_VERSION"
    PREVIOUS_VERSION=$ROLLBACK_VERSION
    return 0
  fi
  
  # Get the current version
  CURRENT_VERSION=$(helm ls -n "$NAMESPACE" -o json | jq -r ".[] | select(.name==\"$SERVICE\") | .revision")
  
  if [ -z "$CURRENT_VERSION" ] || [ "$CURRENT_VERSION" == "null" ]; then
    log "ERROR" "Could not determine current version for $SERVICE"
    return 1
  fi
  
  log_verbose "Current version is $CURRENT_VERSION"
  
  # Get the release history
  RELEASE_HISTORY=$(helm history "$SERVICE" -n "$NAMESPACE" -o json)
  
  if [ -z "$RELEASE_HISTORY" ] || [ "$RELEASE_HISTORY" == "null" ]; then
    log "ERROR" "Could not retrieve release history for $SERVICE"
    return 1
  fi
  
  # Find the previous successful release
  PREVIOUS_VERSION=$(echo "$RELEASE_HISTORY" | jq -r "[.[] | select(.revision < $CURRENT_VERSION and .status == \"deployed\")] | sort_by(.revision) | reverse | .[0].revision")
  
  if [ -z "$PREVIOUS_VERSION" ] || [ "$PREVIOUS_VERSION" == "null" ]; then
    log "ERROR" "Could not find a previous successful release for $SERVICE"
    return 1
  fi
  
  log "INFO" "Previous known-good version identified: $PREVIOUS_VERSION"
  return 0
}

# Function to get dependent services
get_dependent_services() {
  log_verbose "Identifying dependent services for $SERVICE"
  
  # Define service dependencies based on the MCA Application Processing System architecture
  case "$SERVICE" in
    "api-gateway")
      # API Gateway depends on all backend services
      DEPENDENT_SERVICES=("data-service" "notification-service" "document-service" "ocr-service" "email-service")
      ;;
    "data-service")
      # Data service depends on PostgreSQL and RabbitMQ
      DEPENDENT_SERVICES=("postgresql" "rabbitmq")
      ;;
    "notification-service")
      # Notification service depends on RabbitMQ
      DEPENDENT_SERVICES=("rabbitmq")
      ;;
    "document-service")
      # Document service depends on RabbitMQ and S3 storage
      DEPENDENT_SERVICES=("rabbitmq")
      ;;
    "ocr-service")
      # OCR service depends on RabbitMQ and S3 storage
      DEPENDENT_SERVICES=("rabbitmq")
      ;;
    "email-service")
      # Email service depends on RabbitMQ
      DEPENDENT_SERVICES=("rabbitmq")
      ;;
    "frontend")
      # Frontend depends on API Gateway
      DEPENDENT_SERVICES=("api-gateway")
      ;;
    *)
      # No dependencies for other services
      DEPENDENT_SERVICES=()
      ;;
  esac
  
  log_verbose "Dependent services for $SERVICE: ${DEPENDENT_SERVICES[*]}"
  return 0
}

# Function to perform the rollback
perform_rollback() {
  log "INFO" "Rolling back $SERVICE in namespace $NAMESPACE to version $PREVIOUS_VERSION"
  
  # Prepare rollback command
  local rollback_cmd="helm rollback $SERVICE $PREVIOUS_VERSION -n $NAMESPACE --timeout ${TIMEOUT}s"
  
  if [ "$FORCE" = true ]; then
    rollback_cmd="$rollback_cmd --force"
  fi
  
  if [ "$VERBOSE" = true ]; then
    rollback_cmd="$rollback_cmd --debug"
  fi
  
  # Execute rollback command
  if ! retry "$rollback_cmd" "Rollback $SERVICE to version $PREVIOUS_VERSION"; then
    log "ERROR" "Failed to rollback $SERVICE to version $PREVIOUS_VERSION"
    return 1
  fi
  
  log "SUCCESS" "Successfully rolled back $SERVICE to version $PREVIOUS_VERSION"
  return 0
}

# Function to perform progressive rollback
perform_progressive_rollback() {
  log "INFO" "Performing progressive rollback for $SERVICE and its dependencies"
  
  # Get dependent services
  get_dependent_services
  
  # If no dependencies or progressive flag is not set, just rollback the service
  if [ ${#DEPENDENT_SERVICES[@]} -eq 0 ] || [ "$PROGRESSIVE" != "true" ]; then
    perform_rollback
    return $?
  fi
  
  # Rollback dependent services first
  for dep_service in "${DEPENDENT_SERVICES[@]}"; do
    log "INFO" "Checking if dependent service $dep_service needs rollback"
    
    # Check if the dependent service exists and has a release history
    if helm status "$dep_service" -n "$NAMESPACE" &> /dev/null; then
      # Store original service name
      local original_service=$SERVICE
      
      # Temporarily set SERVICE to the dependent service
      SERVICE=$dep_service
      
      # Identify previous version for the dependent service
      if identify_previous_version; then
        # Perform rollback for the dependent service
        perform_rollback
        local dep_rollback_status=$?
        
        if [ $dep_rollback_status -ne 0 ]; then
          log "ERROR" "Failed to rollback dependent service $dep_service"
          # Restore original service name
          SERVICE=$original_service
          return 1
        fi
      else
        log "WARN" "Could not identify previous version for dependent service $dep_service, skipping"
      fi
      
      # Restore original service name
      SERVICE=$original_service
    else
      log "WARN" "Dependent service $dep_service not found in namespace $NAMESPACE, skipping"
    fi
  done
  
  # Now rollback the main service
  perform_rollback
  return $?
}

# Function to validate rollback success
validate_rollback() {
  log "INFO" "Validating rollback success for $SERVICE in namespace $NAMESPACE"
  
  if [ "$SKIP_VALIDATION" = true ]; then
    log "WARN" "Skipping validation as requested"
    return 0
  fi
  
  # Wait for pods to be ready
  log "INFO" "Waiting for pods to be ready"
  local wait_cmd="kubectl -n $NAMESPACE wait --for=condition=ready pods -l app=$SERVICE --timeout=${TIMEOUT}s"
  
  if ! retry "$wait_cmd" "Wait for pods to be ready"; then
    log "ERROR" "Pods for $SERVICE did not become ready after rollback"
    if [ "$FORCE" != "true" ]; then
      return 1
    else
      log "WARN" "Continuing despite validation failure due to --force flag"
    fi
  fi
  
  # Use the validate-deployment.sh script for comprehensive validation
  log "INFO" "Running comprehensive validation checks"
  
  local validate_script="${SCRIPT_DIR}/validate-deployment.sh"
  if [ -f "$validate_script" ]; then
    local validate_cmd="$validate_script --service $SERVICE --namespace $NAMESPACE --environment $ENVIRONMENT --timeout $TIMEOUT"
    
    if [ "$VERBOSE" = true ]; then
      validate_cmd="$validate_cmd --verbose"
    fi
    
    # For MCA Application Processing System, we need service-specific validation options
    case "$SERVICE" in
      "email-service")
        # Skip integration tests for email service during rollback
        validate_cmd="$validate_cmd --skip-integration"
        ;;
      "document-service")
        # Skip functional tests for document service during rollback
        validate_cmd="$validate_cmd --skip-functional"
        ;;
      "ocr-service")
        # OCR service needs more time for ML models to load
        validate_cmd="$validate_cmd --timeout 600"
        ;;
      "data-service")
        # Data service needs database connection validation
        validate_cmd="$validate_cmd"
        ;;
      "notification-service")
        # Notification service needs RabbitMQ connection validation
        validate_cmd="$validate_cmd"
        ;;
      "api-gateway")
        # API Gateway needs route validation
        validate_cmd="$validate_cmd"
        ;;
      *)
        # Default validation
        validate_cmd="$validate_cmd"
        ;;
    esac
    
    if ! retry "$validate_cmd" "Validate rollback success"; then
      log "ERROR" "Validation failed after rollback"
      if [ "$FORCE" != "true" ]; then
        return 1
      else
        log "WARN" "Continuing despite validation failure due to --force flag"
      fi
    fi
  else
    log "WARN" "Validation script not found at $validate_script, skipping comprehensive validation"
    
    # Fallback to basic validation
    log "INFO" "Performing basic validation"
    
    # Check if pods are running
    local pod_status=$(kubectl get pods -n "$NAMESPACE" -l "app=$SERVICE" -o jsonpath='{.items[*].status.phase}')
    if ! echo "$pod_status" | grep -q "Running"; then
      log "ERROR" "Pods for $SERVICE are not running after rollback"
      if [ "$FORCE" != "true" ]; then
        return 1
      else
        log "WARN" "Continuing despite validation failure due to --force flag"
      fi
    fi
    
    # Check if service is available
    if ! kubectl get service "$SERVICE" -n "$NAMESPACE" &> /dev/null; then
      log "ERROR" "Service $SERVICE is not available after rollback"
      if [ "$FORCE" != "true" ]; then
        return 1
      else
        log "WARN" "Continuing despite validation failure due to --force flag"
      fi
    fi
    
    # For MCA Application Processing System, check service-specific health endpoints
    case "$SERVICE" in
      "data-service")
        # Check Spring Boot actuator health endpoint
        local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=$SERVICE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [ -n "$pod_name" ]; then
          log_verbose "Checking data-service health endpoint"
          kubectl -n "$NAMESPACE" port-forward "$pod_name" 8080:8080 &> /dev/null &
          local port_forward_pid=$!
          sleep 2
          local health_status=$(curl -s http://localhost:8080/actuator/health)
          kill $port_forward_pid 2> /dev/null || true
          wait $port_forward_pid 2> /dev/null || true
          
          if ! echo "$health_status" | grep -q '"status":"UP"'; then
            log "ERROR" "Data service health check failed"
            if [ "$FORCE" != "true" ]; then
              return 1
            else
              log "WARN" "Continuing despite health check failure due to --force flag"
            fi
          fi
        fi
        ;;
      "api-gateway")
        # Check Kong status
        local pod_name=$(kubectl -n "$NAMESPACE" get pods -l "app=$SERVICE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [ -n "$pod_name" ]; then
          log_verbose "Checking API Gateway (Kong) status"
          if ! kubectl -n "$NAMESPACE" exec "$pod_name" -- kong health | grep -q "Kong is healthy"; then
            log "ERROR" "API Gateway (Kong) health check failed"
            if [ "$FORCE" != "true" ]; then
              return 1
            else
              log "WARN" "Continuing despite health check failure due to --force flag"
            fi
          fi
        fi
        ;;
    esac
  fi
  
  log "SUCCESS" "Rollback validation successful for $SERVICE"
  return 0
}

# Function to send notification
send_notification() {
  local status=$1
  local message=$2
  
  if [ "$NOTIFY" != "true" ]; then
    log_verbose "Notifications disabled, skipping"
    return 0
  fi
  
  log "INFO" "Sending rollback notification to $INCIDENT_SYSTEM"
  
  # Prepare notification data
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local hostname=$(hostname)
  local user=$(whoami)
  
  # Get Git information if available
  local git_commit=""
  if [ -d "${REPO_ROOT}/.git" ]; then
    git_commit=$(git -C "${REPO_ROOT}" rev-parse HEAD)
  fi
  
  # Create notification payload
  local payload="{\
    \"service\": \"$SERVICE\",\
    \"namespace\": \"$NAMESPACE\",\
    \"environment\": \"$ENVIRONMENT\",\
    \"status\": \"$status\",\
    \"message\": \"$message\",\
    \"timestamp\": \"$timestamp\",\
    \"hostname\": \"$hostname\",\
    \"user\": \"$user\",\
    \"git_commit\": \"$git_commit\",\
    \"previous_version\": \"$PREVIOUS_VERSION\"\
  }"
  
  # Send notification based on incident system
  case "$INCIDENT_SYSTEM" in
    "pagerduty")
      # PagerDuty integration
      # Get PagerDuty key from environment or config file
      local pagerduty_key=""
      if [ -n "$PAGERDUTY_KEY" ]; then
        pagerduty_key="$PAGERDUTY_KEY"
      elif [ -f "${REPO_ROOT}/infrastructure/ci/config/pagerduty.conf" ]; then
        pagerduty_key=$(grep -oP 'PAGERDUTY_KEY=\K.*' "${REPO_ROOT}/infrastructure/ci/config/pagerduty.conf")
      fi
      
      if [ -n "$pagerduty_key" ]; then
        log_verbose "Sending notification to PagerDuty"
        
        # Create PagerDuty-specific payload
        local pd_payload="{\
          \"routing_key\": \"$pagerduty_key\",\
          \"event_action\": \"trigger\",\
          \"payload\": {\
            \"summary\": \"$message\",\
            \"source\": \"$hostname\",\
            \"severity\": \"$status\",\
            \"component\": \"$SERVICE\",\
            \"group\": \"$ENVIRONMENT\",\
            \"class\": \"rollback\",\
            \"custom_details\": $payload\
          }\
        }"
        
        # Send to PagerDuty
        if [ "$VERBOSE" = true ]; then
          curl -s -X POST -H "Content-Type: application/json" \
            -d "$pd_payload" \
            "https://events.pagerduty.com/v2/enqueue"
        else
          curl -s -X POST -H "Content-Type: application/json" \
            -d "$pd_payload" \
            "https://events.pagerduty.com/v2/enqueue" > /dev/null
        fi
      else
        log "WARN" "PagerDuty key not found, notification not sent"
      fi
      ;;
      
    "slack")
      # Slack integration
      # Get Slack webhook from environment or config file
      local slack_webhook=""
      if [ -n "$SLACK_WEBHOOK" ]; then
        slack_webhook="$SLACK_WEBHOOK"
      elif [ -f "${REPO_ROOT}/infrastructure/ci/config/slack.conf" ]; then
        slack_webhook=$(grep -oP 'SLACK_WEBHOOK=\K.*' "${REPO_ROOT}/infrastructure/ci/config/slack.conf")
      fi
      
      if [ -n "$slack_webhook" ]; then
        log_verbose "Sending notification to Slack"
        
        # Create Slack-specific payload
        local slack_payload="{\
          \"text\": \"*$status*: $message\",\
          \"attachments\": [\
            {\
              \"color\": \"${status,,}\" == \"success\" ? \"good\" : \"danger\",\
              \"fields\": [\
                { \"title\": \"Service\", \"value\": \"$SERVICE\", \"short\": true },\
                { \"title\": \"Environment\", \"value\": \"$ENVIRONMENT\", \"short\": true },\
                { \"title\": \"Namespace\", \"value\": \"$NAMESPACE\", \"short\": true },\
                { \"title\": \"Previous Version\", \"value\": \"$PREVIOUS_VERSION\", \"short\": true },\
                { \"title\": \"Triggered By\", \"value\": \"$user@$hostname\", \"short\": true },\
                { \"title\": \"Timestamp\", \"value\": \"$timestamp\", \"short\": true }\
              ]\
            }\
          ]\
        }"
        
        # Send to Slack
        if [ "$VERBOSE" = true ]; then
          curl -s -X POST -H "Content-Type: application/json" \
            -d "$slack_payload" \
            "$slack_webhook"
        else
          curl -s -X POST -H "Content-Type: application/json" \
            -d "$slack_payload" \
            "$slack_webhook" > /dev/null
        fi
      else
        log "WARN" "Slack webhook not found, notification not sent"
      fi
      ;;
      
    "jira")
      # Jira integration
      # Get Jira credentials from environment or config file
      local jira_url=""
      local jira_user=""
      local jira_token=""
      
      if [ -n "$JIRA_URL" ] && [ -n "$JIRA_USER" ] && [ -n "$JIRA_TOKEN" ]; then
        jira_url="$JIRA_URL"
        jira_user="$JIRA_USER"
        jira_token="$JIRA_TOKEN"
      elif [ -f "${REPO_ROOT}/infrastructure/ci/config/jira.conf" ]; then
        jira_url=$(grep -oP 'JIRA_URL=\K.*' "${REPO_ROOT}/infrastructure/ci/config/jira.conf")
        jira_user=$(grep -oP 'JIRA_USER=\K.*' "${REPO_ROOT}/infrastructure/ci/config/jira.conf")
        jira_token=$(grep -oP 'JIRA_TOKEN=\K.*' "${REPO_ROOT}/infrastructure/ci/config/jira.conf")
      fi
      
      if [ -n "$jira_url" ] && [ -n "$jira_user" ] && [ -n "$jira_token" ]; then
        log_verbose "Creating Jira issue for rollback event"
        
        # Create Jira-specific payload
        local jira_payload="{\
          \"fields\": {\
            \"project\": { \"key\": \"MCA\" },\
            \"summary\": \"[$ENVIRONMENT] Rollback of $SERVICE to version $PREVIOUS_VERSION\",\
            \"description\": \"$message\\n\\nDetails:\\n$payload\",\
            \"issuetype\": { \"name\": \"Incident\" },\
            \"priority\": { \"name\": \"${status,,}\" == \"success\" ? \"Medium\" : \"High\" },\
            \"labels\": [\"rollback\", \"$ENVIRONMENT\", \"$SERVICE\"],\
            \"customfield_10001\": \"$PREVIOUS_VERSION\"\
          }\
        }"
        
        # Send to Jira
        if [ "$VERBOSE" = true ]; then
          curl -s -X POST -H "Content-Type: application/json" \
            -H "Authorization: Basic $(echo -n "$jira_user:$jira_token" | base64)" \
            -d "$jira_payload" \
            "$jira_url/rest/api/2/issue"
        else
          curl -s -X POST -H "Content-Type: application/json" \
            -H "Authorization: Basic $(echo -n "$jira_user:$jira_token" | base64)" \
            -d "$jira_payload" \
            "$jira_url/rest/api/2/issue" > /dev/null
        fi
      else
        log "WARN" "Jira credentials not found, notification not sent"
      fi
      ;;
      
    *)
      log "WARN" "Unknown incident system: $INCIDENT_SYSTEM"
      ;;
  esac
  
  log "INFO" "Notification sent to $INCIDENT_SYSTEM"
  return 0
}

# Function to create incident ticket
create_incident_ticket() {
  local status=$1
  local message=$2
  
  if [ "$NOTIFY" != "true" ]; then
    log_verbose "Incident tracking disabled, skipping"
    return 0
  fi
  
  log "INFO" "Creating incident ticket in $INCIDENT_SYSTEM"
  
  # Prepare incident data
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local incident_id="ROLLBACK-${SERVICE}-${ENVIRONMENT}-$(date +"%Y%m%d%H%M%S")"
  
  # Create incident payload
  local payload="{\
    \"incident_id\": \"$incident_id\",\
    \"service\": \"$SERVICE\",\
    \"namespace\": \"$NAMESPACE\",\
    \"environment\": \"$ENVIRONMENT\",\
    \"status\": \"$status\",\
    \"message\": \"$message\",\
    \"timestamp\": \"$timestamp\",\
    \"previous_version\": \"$PREVIOUS_VERSION\"\
  }"
  
  # Write incident information to local file for tracking
  local incidents_dir="${REPO_ROOT}/logs/incidents"
  mkdir -p "$incidents_dir"
  local incident_file="${incidents_dir}/${incident_id}.json"
  echo "$payload" > "$incident_file"
  
  # For MCA Application Processing System, we use the same incident system as notifications
  # So we'll just call the send_notification function
  send_notification "$status" "$message"
  
  log "INFO" "Incident ticket created: $incident_id"
  return 0
}

# Function to capture and save rollback metrics
save_rollback_metrics() {
  local status=$1
  local start_time=$2
  local end_time=$3
  
  # Calculate duration in seconds
  local duration=$((end_time - start_time))
  
  # Create metrics directory if it doesn't exist
  local metrics_dir="${REPO_ROOT}/logs/metrics"
  mkdir -p "$metrics_dir"
  
  # Create metrics file
  local metrics_file="${metrics_dir}/rollback-metrics.csv"
  
  # Create header if file doesn't exist
  if [ ! -f "$metrics_file" ]; then
    echo "timestamp,service,namespace,environment,status,duration,previous_version" > "$metrics_file"
  fi
  
  # Append metrics
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "$timestamp,$SERVICE,$NAMESPACE,$ENVIRONMENT,$status,$duration,$PREVIOUS_VERSION" >> "$metrics_file"
  
  log_verbose "Rollback metrics saved to $metrics_file"
}

# Main function
main() {
  # Record start time
  local start_time=$(date +%s)
  
  log "INFO" "Starting rollback process for $SERVICE in namespace $NAMESPACE ($ENVIRONMENT environment)"
  
  # Check if helm and kubectl are available
  if ! check_helm || ! check_kubectl; then
    log "ERROR" "Required tools are not available, cannot proceed with rollback"
    local end_time=$(date +%s)
    save_rollback_metrics "FAILED" "$start_time" "$end_time"
    exit 1
  fi
  
  # Create incident ticket for the rollback operation
  create_incident_ticket "STARTED" "Rollback operation started for $SERVICE in $ENVIRONMENT environment"
  
  # Identify the previous known-good version
  if ! identify_previous_version; then
    log "ERROR" "Failed to identify previous known-good version, cannot proceed with rollback"
    send_notification "FAILED" "Failed to identify previous known-good version for $SERVICE in $ENVIRONMENT environment"
    local end_time=$(date +%s)
    save_rollback_metrics "FAILED" "$start_time" "$end_time"
    exit 1
  fi
  
  # For MCA Application Processing System, use progressive rollback for production environment
  if [ "$ENVIRONMENT" = "production" ]; then
    log "INFO" "Using progressive rollback for production environment"
    PROGRESSIVE=true
  fi
  
  # Perform the rollback (progressive if specified)
  if [ "$PROGRESSIVE" = true ]; then
    if ! perform_progressive_rollback; then
      log "ERROR" "Progressive rollback failed for $SERVICE"
      send_notification "FAILED" "Progressive rollback failed for $SERVICE in $ENVIRONMENT environment"
      local end_time=$(date +%s)
      save_rollback_metrics "FAILED" "$start_time" "$end_time"
      exit 1
    fi
  else
    if ! perform_rollback; then
      log "ERROR" "Rollback failed for $SERVICE"
      send_notification "FAILED" "Rollback failed for $SERVICE in $ENVIRONMENT environment"
      local end_time=$(date +%s)
      save_rollback_metrics "FAILED" "$start_time" "$end_time"
      exit 1
    fi
  fi
  
  # Validate rollback success
  if ! validate_rollback; then
    log "ERROR" "Rollback validation failed for $SERVICE"
    send_notification "FAILED" "Rollback validation failed for $SERVICE in $ENVIRONMENT environment"
    local end_time=$(date +%s)
    save_rollback_metrics "FAILED" "$start_time" "$end_time"
    exit 1
  fi
  
  # Record end time and save metrics
  local end_time=$(date +%s)
  save_rollback_metrics "SUCCESS" "$start_time" "$end_time"
  
  # Send success notification
  send_notification "SUCCESS" "Successfully rolled back $SERVICE to version $PREVIOUS_VERSION in $ENVIRONMENT environment"
  
  log "SUCCESS" "Rollback process completed successfully for $SERVICE in namespace $NAMESPACE ($ENVIRONMENT environment)"
  log "INFO" "Rollback duration: $((end_time - start_time)) seconds"
  exit 0
}

# Run the main function
main