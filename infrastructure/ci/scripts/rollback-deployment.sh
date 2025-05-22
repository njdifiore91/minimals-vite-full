#!/bin/bash
# Make script executable: chmod +x rollback-deployment.sh

# =============================================================================
# Rollback Deployment Script for MCA Application Processing System
# =============================================================================
#
# This script performs automated rollbacks in case of deployment failures by
# reverting to previous known-good versions. It identifies the previous version,
# executes rollback commands, and verifies rollback success to ensure service
# availability is restored quickly.
#
# Features:
# - Identifies previous known-good version for rollback
# - Implements Helm rollback commands with appropriate flags
# - Verifies rollback success through service health checks
# - Notifies about rollback events through multiple channels
# - Implements progressive rollback strategy for complex services
# - Provides detailed logging of rollback process for troubleshooting
# - Integrates with incident management systems
#
# Usage: ./rollback-deployment.sh [options]
#
# Options:
#   -s, --service <service-name>     Service to rollback (required)
#   -n, --namespace <namespace>      Kubernetes namespace (required)
#   -r, --revision <revision>        Specific revision to rollback to (optional)
#   -t, --timeout <timeout>          Timeout for rollback operation in seconds (default: 300)
#   -f, --force                      Force rollback even if verification fails
#   -d, --dry-run                    Simulate rollback without making changes
#   -v, --verbose                    Enable verbose output
#   -h, --help                       Display this help message
#
# Examples:
#   ./rollback-deployment.sh --service email-service --namespace mca-production
#   ./rollback-deployment.sh -s data-service -n mca-staging -r 2 -t 600
#   ./rollback-deployment.sh -s ocr-service -n mca-development --dry-run
#
# =============================================================================

set -e

# Default values
SERVICE=""
NAMESPACE=""
REVISION=""
TIMEOUT=300
FORCE=false
DRY_RUN=false
VERBOSE=false
LOG_FILE="/tmp/rollback-$(date +%Y%m%d-%H%M%S).log"
INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"

# Color codes for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# =============================================================================
# Function Definitions
# =============================================================================

# Display usage information
function show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -s, --service <service-name>     Service to rollback (required)"
    echo "  -n, --namespace <namespace>      Kubernetes namespace (required)"
    echo "  -r, --revision <revision>        Specific revision to rollback to (optional)"
    echo "  -t, --timeout <timeout>          Timeout for rollback operation in seconds (default: 300)"
    echo "  -f, --force                      Force rollback even if verification fails"
    echo "  -d, --dry-run                    Simulate rollback without making changes"
    echo "  -v, --verbose                    Enable verbose output"
    echo "  -h, --help                       Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --service email-service --namespace mca-production"
    echo "  $0 -s data-service -n mca-staging -r 2 -t 600"
    echo "  $0 -s ocr-service -n mca-development --dry-run"
    exit 1
}

# Parse command line arguments
function parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--service)
                SERVICE="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--revision)
                REVISION="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_usage
                ;;
            *)
                echo -e "${RED}Error: Unknown option $1${NC}"
                show_usage
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$SERVICE" ]]; then
        echo -e "${RED}Error: Service name is required${NC}"
        show_usage
    fi

    if [[ -z "$NAMESPACE" ]]; then
        echo -e "${RED}Error: Namespace is required${NC}"
        show_usage
    fi
}

# Log message to console and log file
function log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    case $level in
        INFO)
            local color=$GREEN
            ;;
        WARN)
            local color=$YELLOW
            ;;
        ERROR)
            local color=$RED
            ;;
        DEBUG)
            local color=$BLUE
            if [[ "$VERBOSE" != "true" ]]; then
                return
            fi
            ;;
        *)
            local color=$NC
            ;;
    esac
    
    echo -e "${color}[$timestamp] [$level] $message${NC}"
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Identify the previous known-good version
function identify_previous_version() {
    log "INFO" "Identifying previous known-good version for $SERVICE in namespace $NAMESPACE"
    
    # If revision is specified, use it
    if [[ -n "$REVISION" ]]; then
        log "INFO" "Using specified revision: $REVISION"
        return 0
    fi
    
    # Get Helm release history
    log "DEBUG" "Getting Helm release history for $SERVICE"
    local history_output
    if ! history_output=$(helm history "$SERVICE" -n "$NAMESPACE" -o json 2>/dev/null); then
        log "ERROR" "Failed to get Helm release history for $SERVICE"
        return 1
    fi
    
    # Parse history to find the previous successful release
    log "DEBUG" "Parsing Helm release history to find previous successful release"
    local current_revision=$(echo "$history_output" | jq -r 'map(select(.status == "deployed")) | max_by(.revision) | .revision')
    
    if [[ -z "$current_revision" || "$current_revision" == "null" ]]; then
        log "ERROR" "No deployed revision found for $SERVICE"
        return 1
    fi
    
    if [[ "$current_revision" -le 1 ]]; then
        log "ERROR" "Current revision is 1, no previous revision available for rollback"
        return 1
    fi
    
    # Find the previous successful revision
    local previous_revision=$(echo "$history_output" | \
        jq -r "map(select(.status == \"superseded\" and .revision < $current_revision)) | max_by(.revision) | .revision")
    
    if [[ -z "$previous_revision" || "$previous_revision" == "null" ]]; then
        log "ERROR" "No previous successful revision found for $SERVICE"
        return 1
    fi
    
    REVISION="$previous_revision"
    log "INFO" "Identified previous successful revision: $REVISION"
    return 0
}

# Execute the rollback operation
function execute_rollback() {
    log "INFO" "Executing rollback of $SERVICE in namespace $NAMESPACE to revision $REVISION"
    
    local helm_args=("rollback" "$SERVICE" "$REVISION" "-n" "$NAMESPACE" "--timeout" "${TIMEOUT}s" "--wait")
    
    # Add dry-run flag if specified
    if [[ "$DRY_RUN" == "true" ]]; then
        helm_args+=("--dry-run")
        log "WARN" "DRY RUN MODE: No actual changes will be made"
    fi
    
    # Add force flag if specified
    if [[ "$FORCE" == "true" ]]; then
        helm_args+=("--force")
        log "WARN" "FORCE MODE: Rollback will proceed even if there are issues"
    fi
    
    # Execute Helm rollback command
    log "DEBUG" "Executing: helm ${helm_args[*]}"
    if ! helm "${helm_args[@]}" 2>&1 | tee -a "$LOG_FILE"; then
        log "ERROR" "Helm rollback failed for $SERVICE to revision $REVISION"
        return 1
    fi
    
    log "INFO" "Rollback executed successfully for $SERVICE to revision $REVISION"
    return 0
}

# Verify rollback success through service checks
function verify_rollback() {
    log "INFO" "Verifying rollback success for $SERVICE in namespace $NAMESPACE"
    
    # Skip verification in dry-run mode
    if [[ "$DRY_RUN" == "true" ]]; then
        log "WARN" "Skipping verification in dry-run mode"
        return 0
    fi
    
    # Wait for pods to be ready
    log "DEBUG" "Waiting for pods to be ready"
    if ! kubectl rollout status deployment "$SERVICE" -n "$NAMESPACE" --timeout="${TIMEOUT}s" 2>&1 | tee -a "$LOG_FILE"; then
        log "ERROR" "Pods for $SERVICE did not reach ready state after rollback"
        if [[ "$FORCE" != "true" ]]; then
            return 1
        fi
        log "WARN" "Continuing despite pod readiness failure due to --force flag"
    fi
    
    # Check service health endpoint
    log "DEBUG" "Checking service health endpoint"
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/name=$SERVICE" -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
    
    if [[ -z "$pod_name" ]]; then
        log "ERROR" "No pods found for $SERVICE after rollback"
        if [[ "$FORCE" != "true" ]]; then
            return 1
        fi
        log "WARN" "Continuing despite pod availability failure due to --force flag"
        return 0
    fi
    
    # Determine health endpoint based on service type
    local health_endpoint="/health"
    local service_type=$(kubectl get deployment "$SERVICE" -n "$NAMESPACE" -o jsonpath="{.spec.template.metadata.labels.serviceType}" 2>/dev/null)
    
    case $service_type in
        nodejs)
            health_endpoint="/health"
            ;;
        java)
            health_endpoint="/actuator/health"
            ;;
        python)
            health_endpoint="/health/live"
            ;;
        *)
            health_endpoint="/health"
            ;;
    esac
    
    log "DEBUG" "Using health endpoint: $health_endpoint for service type: $service_type"
    
    # Check health endpoint using port-forward
    local port=8080
    log "DEBUG" "Setting up port-forward to pod $pod_name"
    kubectl port-forward "$pod_name" "$port:$port" -n "$NAMESPACE" &
    local port_forward_pid=$!
    
    # Give port-forward time to establish
    sleep 3
    
    # Check health endpoint
    log "DEBUG" "Checking health endpoint: http://localhost:$port$health_endpoint"
    local health_status
    if ! health_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port$health_endpoint"); then
        log "ERROR" "Failed to connect to health endpoint"
        kill $port_forward_pid 2>/dev/null || true
        if [[ "$FORCE" != "true" ]]; then
            return 1
        fi
        log "WARN" "Continuing despite health check failure due to --force flag"
        return 0
    fi
    
    # Clean up port-forward
    kill $port_forward_pid 2>/dev/null || true
    
    # Check if health status is 200 OK
    if [[ "$health_status" == "200" ]]; then
        log "INFO" "Health check passed: $health_status"
    else
        log "ERROR" "Health check failed with status: $health_status"
        if [[ "$FORCE" != "true" ]]; then
            return 1
        fi
        log "WARN" "Continuing despite health check failure due to --force flag"
    fi
    
    return 0
}

# Notify about rollback events
function notify_rollback() {
    local status=$1
    local message=$2
    
    log "INFO" "Sending rollback notification: $status - $message"
    
    # Skip notification in dry-run mode
    if [[ "$DRY_RUN" == "true" ]]; then
        log "WARN" "Skipping notification in dry-run mode"
        return 0
    fi
    
    # Determine environment from namespace
    local environment="development"
    if [[ "$NAMESPACE" == *"staging"* ]]; then
        environment="staging"
    elif [[ "$NAMESPACE" == *"prod"* ]]; then
        environment="production"
    fi
    
    # Prepare notification payload
    local payload='{"incident_id":"'"$INCIDENT_ID"'","service":"'"$SERVICE"'","namespace":"'"$NAMESPACE"'","environment":"'"$environment"'","revision":"'"$REVISION"'","status":"'"$status"'","message":"'"$message"'","timestamp":"'"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'"}'
    
    # Send notification to Datadog
    log "DEBUG" "Sending notification to Datadog"
    if command -v datadog-agent &>/dev/null; then
        if ! datadog-agent event "Rollback $status: $SERVICE" "$message" --tags "service:$SERVICE,environment:$environment,incident:$INCIDENT_ID" 2>&1 | tee -a "$LOG_FILE"; then
            log "WARN" "Failed to send notification to Datadog"
        fi
    else
        log "WARN" "Datadog agent not found, skipping Datadog notification"
    fi
    
    # Send notification to Slack (if webhook URL is configured)
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        log "DEBUG" "Sending notification to Slack"
        local color="good"
        if [[ "$status" != "SUCCESS" ]]; then
            color="danger"
        fi
        
        local slack_payload='{"attachments":[{"color":"'"$color"'","title":"Rollback '"$status"': '"$SERVICE"'","text":"'"$message"'","fields":[{"title":"Service","value":"'"$SERVICE"'","short":true},{"title":"Environment","value":"'"$environment"'","short":true},{"title":"Namespace","value":"'"$NAMESPACE"'","short":true},{"title":"Revision","value":"'"$REVISION"'","short":true},{"title":"Incident ID","value":"'"$INCIDENT_ID"'","short":true}]}]}'
        
        if ! curl -s -X POST -H "Content-Type: application/json" -d "$slack_payload" "$SLACK_WEBHOOK_URL" 2>&1 | tee -a "$LOG_FILE"; then
            log "WARN" "Failed to send notification to Slack"
        fi
    else
        log "WARN" "SLACK_WEBHOOK_URL not configured, skipping Slack notification"
    fi
    
    # Create incident in PagerDuty (if API key is configured)
    if [[ -n "$PAGERDUTY_API_KEY" && "$status" != "SUCCESS" && "$environment" == "production" ]]; then
        log "DEBUG" "Creating incident in PagerDuty"
        local pagerduty_payload='{"incident":{"type":"incident","title":"Rollback '"$status"': '"$SERVICE"' in '"$environment"'","service":{"id":"'"$PAGERDUTY_SERVICE_ID"'"},"body":{"type":"incident_body","details":"'"$message"'"},"incident_key":"'"$INCIDENT_ID"'"}}}'
        
        if ! curl -s -X POST -H "Content-Type: application/json" -H "Authorization: Token token=$PAGERDUTY_API_KEY" -H "Accept: application/vnd.pagerduty+json;version=2" -H "From: rollback@dollarfunding.com" -d "$pagerduty_payload" "https://api.pagerduty.com/incidents" 2>&1 | tee -a "$LOG_FILE"; then
            log "WARN" "Failed to create incident in PagerDuty"
        fi
    else
        log "DEBUG" "Skipping PagerDuty incident creation (not configured or not production or successful rollback)"
    fi
    
    return 0
}

# Implement progressive rollback strategy for complex services
function progressive_rollback() {
    log "INFO" "Implementing progressive rollback strategy for $SERVICE"
    
    # Skip in dry-run mode
    if [[ "$DRY_RUN" == "true" ]]; then
        log "WARN" "Skipping progressive rollback in dry-run mode"
        return 0
    fi
    
    # Check if service has dependencies that need to be rolled back first
    local has_dependencies=false
    
    # Define service dependencies (which services should be rolled back first)
    case $SERVICE in
        data-service)
            # Data service has no dependencies that need to be rolled back first
            has_dependencies=false
            ;;
        ocr-service|document-service)
            # These services depend on data-service
            has_dependencies=true
            local dependencies=("data-service")
            ;;
        notification-service)
            # Notification service depends on data-service
            has_dependencies=true
            local dependencies=("data-service")
            ;;
        email-service)
            # Email service depends on document-service and data-service
            has_dependencies=true
            local dependencies=("data-service" "document-service")
            ;;
        *)
            # Default: no dependencies
            has_dependencies=false
            ;;
    esac
    
    # If service has dependencies, check if they need to be rolled back
    if [[ "$has_dependencies" == "true" ]]; then
        log "INFO" "Service $SERVICE has dependencies that may need to be rolled back first"
        
        for dep in "${dependencies[@]}"; do
            log "DEBUG" "Checking if dependency $dep needs to be rolled back"
            
            # Check if dependency is in a failed state
            local dep_status=$(kubectl get deployment "$dep" -n "$NAMESPACE" -o jsonpath="{.status.conditions[?(@.type=='Available')].status}" 2>/dev/null)
            
            if [[ "$dep_status" != "True" ]]; then
                log "WARN" "Dependency $dep appears to be in a failed state, it should be rolled back first"
                log "WARN" "Please run: $0 -s $dep -n $NAMESPACE"
                
                if [[ "$FORCE" != "true" ]]; then
                    log "ERROR" "Aborting rollback due to dependency issue. Use --force to override."
                    return 1
                fi
                
                log "WARN" "Continuing despite dependency issue due to --force flag"
            else
                log "DEBUG" "Dependency $dep appears to be healthy"
            fi
        done
    fi
    
    return 0
}

# Main function
function main() {
    log "INFO" "Starting rollback process for $SERVICE in namespace $NAMESPACE"
    log "INFO" "Incident ID: $INCIDENT_ID"
    log "INFO" "Log file: $LOG_FILE"
    
    # Check if kubectl is available
    if ! command -v kubectl &>/dev/null; then
        log "ERROR" "kubectl command not found"
        notify_rollback "FAILED" "kubectl command not found"
        exit 1
    fi
    
    # Check if helm is available
    if ! command -v helm &>/dev/null; then
        log "ERROR" "helm command not found"
        notify_rollback "FAILED" "helm command not found"
        exit 1
    fi
    
    # Check if jq is available
    if ! command -v jq &>/dev/null; then
        log "ERROR" "jq command not found"
        notify_rollback "FAILED" "jq command not found"
        exit 1
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
        log "ERROR" "Namespace $NAMESPACE does not exist"
        notify_rollback "FAILED" "Namespace $NAMESPACE does not exist"
        exit 1
    fi
    
    # Check if service exists
    if ! kubectl get deployment "$SERVICE" -n "$NAMESPACE" &>/dev/null; then
        log "ERROR" "Service $SERVICE does not exist in namespace $NAMESPACE"
        notify_rollback "FAILED" "Service $SERVICE does not exist in namespace $NAMESPACE"
        exit 1
    fi
    
    # Implement progressive rollback strategy
    if ! progressive_rollback; then
        log "ERROR" "Progressive rollback strategy failed"
        notify_rollback "FAILED" "Progressive rollback strategy failed"
        exit 1
    fi
    
    # Identify previous known-good version
    if ! identify_previous_version; then
        log "ERROR" "Failed to identify previous known-good version"
        notify_rollback "FAILED" "Failed to identify previous known-good version"
        exit 1
    fi
    
    # Execute rollback
    if ! execute_rollback; then
        log "ERROR" "Rollback execution failed"
        notify_rollback "FAILED" "Rollback execution failed"
        exit 1
    fi
    
    # Verify rollback success
    if ! verify_rollback; then
        log "ERROR" "Rollback verification failed"
        notify_rollback "FAILED" "Rollback verification failed"
        exit 1
    fi
    
    # Notify about successful rollback
    notify_rollback "SUCCESS" "Successfully rolled back $SERVICE in namespace $NAMESPACE to revision $REVISION"
    
    log "INFO" "Rollback process completed successfully"
    log "INFO" "Service: $SERVICE"
    log "INFO" "Namespace: $NAMESPACE"
    log "INFO" "Revision: $REVISION"
    log "INFO" "Log file: $LOG_FILE"
    
    return 0
}

# =============================================================================
# Script Execution
# =============================================================================

# Parse command line arguments
parse_args "$@"

# Execute main function
main