#!/bin/bash

# =========================================================================
# scan-image.sh - Container Image Vulnerability Scanner
# =========================================================================
# Description: Scans container images for vulnerabilities using Trivy with
#              environment-specific severity thresholds.
#
# Usage: ./scan-image.sh [OPTIONS] IMAGE_NAME
#
# Options:
#   -e, --environment ENV    Specify environment (dev|staging|prod) [default: dev]
#   -f, --format FORMAT      Output format (table|json|html) [default: table]
#   -o, --output FILE        Output file path [default: trivy-results.{format}]
#   -c, --cache-dir DIR      Cache directory [default: .trivycache]
#   -t, --timeout SECONDS    Timeout in seconds [default: 300]
#   -i, --ignore-unfixed     Ignore unfixed vulnerabilities
#   -n, --notify             Send notifications for vulnerabilities
#   -h, --help               Show this help message
#
# Examples:
#   ./scan-image.sh nginx:latest
#   ./scan-image.sh -e prod -f json -o results.json myapp:1.0.0
#   ./scan-image.sh --environment staging --ignore-unfixed myregistry/myapp:latest
# =========================================================================

set -eo pipefail

# Default values
ENVIRONMENT="dev"
FORMAT="table"
OUTPUT=""
CACHE_DIR=".trivycache"
TIMEOUT=300
IGNORE_UNFIXED=false
NOTIFY=false
DEBUG=false

# Color codes for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Environment-specific severity thresholds
# Format: [ENV]_[SEVERITY]_THRESHOLD
# These thresholds define the maximum number of vulnerabilities allowed
# before failing the pipeline
DEV_CRITICAL_THRESHOLD=1
DEV_HIGH_THRESHOLD=10
DEV_MEDIUM_THRESHOLD=20
DEV_LOW_THRESHOLD=50

STAGING_CRITICAL_THRESHOLD=0
STAGING_HIGH_THRESHOLD=5
STAGING_MEDIUM_THRESHOLD=15
STAGING_LOW_THRESHOLD=30

PROD_CRITICAL_THRESHOLD=0
PROD_HIGH_THRESHOLD=0
PROD_MEDIUM_THRESHOLD=5
PROD_LOW_THRESHOLD=15

# Function to display usage information
show_usage() {
    grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^# \?//'
    exit 0
}

# Function to log messages
log() {
    local level=$1
    local message=$2
    local color=$NC
    
    case $level in
        "INFO") color=$BLUE ;;
        "SUCCESS") color=$GREEN ;;
        "WARNING") color=$YELLOW ;;
        "ERROR") color=$RED ;;
    esac
    
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] ${message}${NC}"
}

# Function to log debug messages
debug_log() {
    if [ "$DEBUG" = true ]; then
        log "DEBUG" "$1"
    fi
}

# Function to check if Trivy is installed
check_trivy() {
    if ! command -v trivy &> /dev/null; then
        log "ERROR" "Trivy is not installed. Please install Trivy first."
        log "INFO" "Visit https://github.com/aquasecurity/trivy#installation for installation instructions."
        exit 1
    fi
    
    log "INFO" "Using Trivy version: $(trivy --version | head -n 1)"
}

# Function to check if jq is installed (needed for JSON parsing)
check_jq() {
    if ! command -v jq &> /dev/null; then
        log "WARNING" "jq is not installed. JSON parsing capabilities will be limited."
    fi
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -f|--format)
                FORMAT="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT="$2"
                shift 2
                ;;
            -c|--cache-dir)
                CACHE_DIR="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -i|--ignore-unfixed)
                IGNORE_UNFIXED=true
                shift
                ;;
            -n|--notify)
                NOTIFY=true
                shift
                ;;
            -d|--debug)
                DEBUG=true
                shift
                ;;
            -h|--help)
                show_usage
                ;;
            -*)
                log "ERROR" "Unknown option: $1"
                show_usage
                ;;
            *)
                IMAGE_NAME="$1"
                shift
                ;;
        esac
    done
    
    # Validate required arguments
    if [ -z "$IMAGE_NAME" ]; then
        log "ERROR" "Image name is required"
        show_usage
    fi
    
    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
        log "ERROR" "Invalid environment: $ENVIRONMENT. Must be one of: dev, staging, prod"
        exit 1
    fi
    
    # Validate format
    if [[ ! "$FORMAT" =~ ^(table|json|html)$ ]]; then
        log "ERROR" "Invalid format: $FORMAT. Must be one of: table, json, html"
        exit 1
    fi
    
    # Set default output file if not specified
    if [ -z "$OUTPUT" ]; then
        OUTPUT="trivy-results.${FORMAT}"
    fi
}

# Function to set thresholds based on environment
set_thresholds() {
    case $ENVIRONMENT in
        "dev")
            CRITICAL_THRESHOLD=$DEV_CRITICAL_THRESHOLD
            HIGH_THRESHOLD=$DEV_HIGH_THRESHOLD
            MEDIUM_THRESHOLD=$DEV_MEDIUM_THRESHOLD
            LOW_THRESHOLD=$DEV_LOW_THRESHOLD
            ;;
        "staging")
            CRITICAL_THRESHOLD=$STAGING_CRITICAL_THRESHOLD
            HIGH_THRESHOLD=$STAGING_HIGH_THRESHOLD
            MEDIUM_THRESHOLD=$STAGING_MEDIUM_THRESHOLD
            LOW_THRESHOLD=$STAGING_LOW_THRESHOLD
            ;;
        "prod")
            CRITICAL_THRESHOLD=$PROD_CRITICAL_THRESHOLD
            HIGH_THRESHOLD=$PROD_HIGH_THRESHOLD
            MEDIUM_THRESHOLD=$PROD_MEDIUM_THRESHOLD
            LOW_THRESHOLD=$PROD_LOW_THRESHOLD
            ;;
    esac
    
    log "INFO" "Environment: $ENVIRONMENT"
    log "INFO" "Thresholds - CRITICAL: $CRITICAL_THRESHOLD, HIGH: $HIGH_THRESHOLD, MEDIUM: $MEDIUM_THRESHOLD, LOW: $LOW_THRESHOLD"
}

# Function to run Trivy scan
run_scan() {
    local trivy_args=("image")
    
    # Add common arguments
    trivy_args+=("--cache-dir" "$CACHE_DIR")
    trivy_args+=("--timeout" "${TIMEOUT}s")
    
    # Add format-specific arguments
    case $FORMAT in
        "table")
            trivy_args+=("--format" "table")
            ;;
        "json")
            trivy_args+=("--format" "json")
            ;;
        "html")
            trivy_args+=("--format" "template")
            trivy_args+=("--template" "@/contrib/html.tpl")
            ;;
    esac
    
    # Add output file if specified
    if [ -n "$OUTPUT" ]; then
        trivy_args+=("--output" "$OUTPUT")
    fi
    
    # Add ignore-unfixed flag if specified
    if [ "$IGNORE_UNFIXED" = true ]; then
        trivy_args+=("--ignore-unfixed")
    fi
    
    # Add severity levels to scan
    trivy_args+=("--severity" "CRITICAL,HIGH,MEDIUM,LOW")
    
    # Add image name
    trivy_args+=("$IMAGE_NAME")
    
    # Create a temporary file for JSON output (for parsing)
    TEMP_JSON=$(mktemp)
    
    # Always generate JSON output for parsing, regardless of requested format
    log "INFO" "Running Trivy scan on image: $IMAGE_NAME"
    debug_log "Trivy command: trivy ${trivy_args[@]}"
    
    # Run the scan with the specified format for user output
    if ! trivy "${trivy_args[@]}"; then
        log "ERROR" "Trivy scan failed"
        exit 1
    fi
    
    # Run again with JSON output for parsing if the original format wasn't JSON
    if [ "$FORMAT" != "json" ]; then
        if ! trivy image --cache-dir "$CACHE_DIR" --timeout "${TIMEOUT}s" --format json --ignore-unfixed="$IGNORE_UNFIXED" --severity "CRITICAL,HIGH,MEDIUM,LOW" "$IMAGE_NAME" > "$TEMP_JSON"; then
            log "ERROR" "Failed to generate JSON output for parsing"
            rm -f "$TEMP_JSON"
            exit 1
        fi
    else
        # If JSON was requested, use the output file
        cp "$OUTPUT" "$TEMP_JSON"
    fi
    
    log "SUCCESS" "Scan completed successfully"
    log "INFO" "Results saved to: $OUTPUT"
    
    # Parse results and check against thresholds
    parse_results "$TEMP_JSON"
    
    # Clean up temporary file
    rm -f "$TEMP_JSON"
}

# Function to parse scan results and check against thresholds
parse_results() {
    local json_file=$1
    local critical_count=0
    local high_count=0
    local medium_count=0
    local low_count=0
    
    # Check if jq is available for better JSON parsing
    if command -v jq &> /dev/null; then
        # Use jq to parse the JSON and count vulnerabilities by severity
        if [ -s "$json_file" ]; then
            critical_count=$(jq '[.Results[].Vulnerabilities[] | select(.Severity == "CRITICAL")] | length' "$json_file" 2>/dev/null || echo 0)
            high_count=$(jq '[.Results[].Vulnerabilities[] | select(.Severity == "HIGH")] | length' "$json_file" 2>/dev/null || echo 0)
            medium_count=$(jq '[.Results[].Vulnerabilities[] | select(.Severity == "MEDIUM")] | length' "$json_file" 2>/dev/null || echo 0)
            low_count=$(jq '[.Results[].Vulnerabilities[] | select(.Severity == "LOW")] | length' "$json_file" 2>/dev/null || echo 0)
        else
            log "WARNING" "Empty JSON result file"
        fi
    else
        # Fallback to grep and wc if jq is not available
        log "WARNING" "Using fallback method for parsing results (less accurate)"
        if [ -s "$json_file" ]; then
            critical_count=$(grep -c '"Severity":"CRITICAL"' "$json_file" || echo 0)
            high_count=$(grep -c '"Severity":"HIGH"' "$json_file" || echo 0)
            medium_count=$(grep -c '"Severity":"MEDIUM"' "$json_file" || echo 0)
            low_count=$(grep -c '"Severity":"LOW"' "$json_file" || echo 0)
        else
            log "WARNING" "Empty JSON result file"
        fi
    fi
    
    # Log vulnerability counts
    log "INFO" "Vulnerability counts - CRITICAL: $critical_count, HIGH: $high_count, MEDIUM: $medium_count, LOW: $low_count"
    
    # Check against thresholds
    local failed=false
    local failure_reasons=""
    
    if [ "$critical_count" -gt "$CRITICAL_THRESHOLD" ]; then
        failed=true
        failure_reasons+="CRITICAL vulnerabilities ($critical_count) exceed threshold ($CRITICAL_THRESHOLD)\n"
    fi
    
    if [ "$high_count" -gt "$HIGH_THRESHOLD" ]; then
        failed=true
        failure_reasons+="HIGH vulnerabilities ($high_count) exceed threshold ($HIGH_THRESHOLD)\n"
    fi
    
    if [ "$medium_count" -gt "$MEDIUM_THRESHOLD" ]; then
        failed=true
        failure_reasons+="MEDIUM vulnerabilities ($medium_count) exceed threshold ($MEDIUM_THRESHOLD)\n"
    fi
    
    if [ "$low_count" -gt "$LOW_THRESHOLD" ]; then
        failed=true
        failure_reasons+="LOW vulnerabilities ($low_count) exceed threshold ($LOW_THRESHOLD)\n"
    fi
    
    # Send notification if requested
    if [ "$NOTIFY" = true ]; then
        send_notification "$critical_count" "$high_count" "$medium_count" "$low_count" "$failed"
    fi
    
    # Exit with appropriate status
    if [ "$failed" = true ]; then
        log "ERROR" "Vulnerability scan failed due to threshold violations:"
        echo -e "$failure_reasons"
        exit 1
    else
        log "SUCCESS" "All vulnerability counts are within acceptable thresholds"
    fi
}

# Function to send notifications
send_notification() {
    local critical_count=$1
    local high_count=$2
    local medium_count=$3
    local low_count=$4
    local failed=$5
    local status="PASSED"
    
    if [ "$failed" = true ]; then
        status="FAILED"
    fi
    
    log "INFO" "Sending vulnerability scan notification (Status: $status)"
    
    # This is a placeholder for notification integration
    # In a real implementation, you would integrate with your notification system
    # Examples: Slack, Email, MS Teams, etc.
    
    # Example for webhook-based notification:
    # curl -X POST -H "Content-Type: application/json" \
    #     -d "{\"image\":\"$IMAGE_NAME\",\"environment\":\"$ENVIRONMENT\",\"status\":\"$status\",\"vulnerabilities\":{\"critical\":$critical_count,\"high\":$high_count,\"medium\":$medium_count,\"low\":$low_count}}" \
    #     "https://your-webhook-url"
    
    debug_log "Notification would be sent with: Image=$IMAGE_NAME, Environment=$ENVIRONMENT, Status=$status, Vulnerabilities={critical:$critical_count,high:$high_count,medium:$medium_count,low:$low_count}"
}

# Main function
main() {
    # Check dependencies
    check_trivy
    check_jq
    
    # Parse command line arguments
    parse_args "$@"
    
    # Set thresholds based on environment
    set_thresholds
    
    # Create cache directory if it doesn't exist
    mkdir -p "$CACHE_DIR"
    
    # Run the scan
    run_scan
}

# Execute main function with all arguments
main "$@"