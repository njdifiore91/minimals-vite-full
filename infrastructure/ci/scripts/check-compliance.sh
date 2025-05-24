#!/bin/bash

# ============================================================================
# check-compliance.sh - Security and Compliance Checking Script
#
# This script performs comprehensive compliance checks for infrastructure and
# application code against predefined security policies. It ensures all deployed
# code and infrastructure meet the organization's security and compliance
# requirements.
#
# Features:
# - Infrastructure code compliance checking (Terraform, Kubernetes)
# - Application code security scanning (secrets, vulnerabilities)
# - License compliance verification
# - Detailed report generation
# - Pipeline failure on policy violations
# - Compliance check caching for performance
# - Integration with compliance tracking systems
#
# Usage: ./check-compliance.sh [options]
#   Options:
#     -t, --target <path>       Target directory or file to scan
#     -c, --config <file>       Custom configuration file
#     -o, --output <dir>        Output directory for reports
#     -f, --format <format>     Report format (json, xml, html, text)
#     -s, --severity <level>    Minimum severity level to report (info, low, medium, high, critical)
#     -n, --no-fail             Don't fail the pipeline on violations
#     -k, --cache               Use cached results if available
#     -h, --help                Show this help message
#
# ============================================================================

set -eo pipefail

# ============================================================================
# Configuration and Constants
# ============================================================================

# Script version
VERSION="1.0.0"

# Default values
DEFAULT_TARGET="."
DEFAULT_CONFIG="/etc/compliance/config.yaml"
DEFAULT_OUTPUT="./compliance-reports"
DEFAULT_FORMAT="json"
DEFAULT_SEVERITY="low"
DEFAULT_FAIL_ON_VIOLATIONS=true
DEFAULT_USE_CACHE=false

# Tool paths - these will be checked and installed if missing
TERRAFORM_CHECKOV="checkov"
KUBERNETES_KICS="kics"
SECRETS_SCANNER="trufflehog"
LICENSE_SCANNER="fossology"
VULN_SCANNER="trivy"

# Colors for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
MAGENTA="\033[0;35m"
CYAN="\033[0;36m"
NC="\033[0m" # No Color

# ============================================================================
# Functions
# ============================================================================

# Display script usage information
show_help() {
    echo -e "${CYAN}Compliance Checking Script v${VERSION}${NC}"
    echo -e "Checks infrastructure and application code for security and compliance issues."
    echo ""
    echo -e "${YELLOW}Usage:${NC} $0 [options]"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo "  -t, --target <path>       Target directory or file to scan (default: ${DEFAULT_TARGET})"
    echo "  -c, --config <file>       Custom configuration file (default: ${DEFAULT_CONFIG})"
    echo "  -o, --output <dir>        Output directory for reports (default: ${DEFAULT_OUTPUT})"
    echo "  -f, --format <format>     Report format: json, xml, html, text (default: ${DEFAULT_FORMAT})"
    echo "  -s, --severity <level>    Minimum severity: info, low, medium, high, critical (default: ${DEFAULT_SEVERITY})"
    echo "  -n, --no-fail             Don't fail the pipeline on violations"
    echo "  -k, --cache               Use cached results if available"
    echo "  -h, --help                Show this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 --target ./infrastructure --format html --severity medium"
    echo "  $0 --target ./src --output ./reports --no-fail"
    echo ""
}

# Log messages with timestamp and level
log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    case $level in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} ${timestamp} - ${message}"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} ${timestamp} - ${message}"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${timestamp} - ${message}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - ${message}"
            ;;
        *)
            echo -e "${timestamp} - ${message}"
            ;;
    esac
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install required tools if they don't exist
install_dependencies() {
    log "INFO" "Checking for required dependencies..."
    
    local missing_tools=false
    
    # Check for Checkov (Terraform/IaC scanner)
    if ! command_exists "${TERRAFORM_CHECKOV}"; then
        log "WARNING" "Checkov not found. Installing..."
        pip install checkov >/dev/null 2>&1 || { log "ERROR" "Failed to install Checkov"; missing_tools=true; }
    fi
    
    # Check for KICS (Kubernetes scanner)
    if ! command_exists "${KUBERNETES_KICS}"; then
        log "WARNING" "KICS not found. Installing..."
        curl -sfL https://raw.githubusercontent.com/Checkmarx/kics/master/install.sh | sh >/dev/null 2>&1 || { log "ERROR" "Failed to install KICS"; missing_tools=true; }
    fi
    
    # Check for TruffleHog (Secrets scanner)
    if ! command_exists "${SECRETS_SCANNER}"; then
        log "WARNING" "TruffleHog not found. Installing..."
        pip install trufflehog >/dev/null 2>&1 || { log "ERROR" "Failed to install TruffleHog"; missing_tools=true; }
    fi
    
    # Check for FOSSology (License scanner)
    if ! command_exists "${LICENSE_SCANNER}"; then
        log "WARNING" "FOSSology CLI not found. Using alternative license scanning method."
        # We'll use a fallback method for license scanning
    fi
    
    # Check for Trivy (Vulnerability scanner)
    if ! command_exists "${VULN_SCANNER}"; then
        log "WARNING" "Trivy not found. Installing..."
        curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin >/dev/null 2>&1 || { log "ERROR" "Failed to install Trivy"; missing_tools=true; }
    fi
    
    if [ "$missing_tools" = true ]; then
        log "ERROR" "Some required tools could not be installed. Check your permissions and network connection."
        exit 1
    fi
    
    log "SUCCESS" "All dependencies are available."
}

# Create output directory if it doesn't exist
create_output_dir() {
    if [ ! -d "$OUTPUT_DIR" ]; then
        mkdir -p "$OUTPUT_DIR" || { log "ERROR" "Failed to create output directory: $OUTPUT_DIR"; exit 1; }
    fi
}

# Generate a unique cache key based on target and config
generate_cache_key() {
    local target_hash=$(find "$TARGET_PATH" -type f -not -path "*/\.*" -print0 | sort -z | xargs -0 sha1sum | sha1sum | cut -d' ' -f1)
    local config_hash=$(sha1sum "$CONFIG_FILE" 2>/dev/null | cut -d' ' -f1 || echo "noconfig")
    echo "${target_hash}_${config_hash}"
}

# Check if cached results are available and valid
check_cache() {
    if [ "$USE_CACHE" = true ]; then
        local cache_key=$(generate_cache_key)
        local cache_file="${OUTPUT_DIR}/.cache/${cache_key}.json"
        
        if [ -f "$cache_file" ]; then
            # Check if cache is still valid (less than 24 hours old)
            local cache_time=$(stat -c %Y "$cache_file" 2>/dev/null || stat -f %m "$cache_file")
            local current_time=$(date +%s)
            local cache_age=$((current_time - cache_time))
            
            if [ $cache_age -lt 86400 ]; then  # 24 hours in seconds
                log "INFO" "Using cached compliance results (${cache_age}s old)"
                cat "$cache_file" > "${OUTPUT_DIR}/compliance-report.json"
                return 0
            else
                log "INFO" "Cache expired (${cache_age}s old). Running new scan."
            fi
        else
            log "INFO" "No cache found. Running new scan."
        fi
    fi
    return 1
}

# Save results to cache
save_to_cache() {
    if [ "$USE_CACHE" = true ]; then
        local cache_key=$(generate_cache_key)
        local cache_dir="${OUTPUT_DIR}/.cache"
        local cache_file="${cache_dir}/${cache_key}.json"
        
        mkdir -p "$cache_dir" || { log "WARNING" "Failed to create cache directory"; return 1; }
        
        cp "${OUTPUT_DIR}/compliance-report.json" "$cache_file" || { log "WARNING" "Failed to save results to cache"; return 1; }
        
        log "INFO" "Saved compliance results to cache"
    fi
}

# Run infrastructure code compliance checks (Terraform, CloudFormation, etc.)
check_infrastructure_compliance() {
    log "INFO" "Checking infrastructure code compliance..."
    
    # Create output directory for infrastructure checks
    local infra_output_dir="${OUTPUT_DIR}/infrastructure"
    mkdir -p "$infra_output_dir"
    
    # Run Checkov for Terraform, CloudFormation, etc.
    log "INFO" "Running Checkov for IaC scanning..."
    $TERRAFORM_CHECKOV --directory "$TARGET_PATH" \
        --output "$REPORT_FORMAT" \
        --output-file "${infra_output_dir}/checkov-report.${REPORT_FORMAT}" \
        --quiet \
        --soft-fail \
        --framework terraform,cloudformation,kubernetes,dockerfile,helm \
        --check "CKV_AWS_*,CKV_AZURE_*,CKV_GCP_*,CKV_K8S_*,CKV_DOCKER_*" \
        --severity-filter "${SEVERITY_LEVEL}" \
        || { log "WARNING" "Checkov found compliance issues"; COMPLIANCE_ISSUES=true; }
    
    # Run KICS for Kubernetes manifests
    log "INFO" "Running KICS for Kubernetes compliance..."
    $KUBERNETES_KICS scan \
        --path "$TARGET_PATH" \
        --output-path "$infra_output_dir" \
        --output-name "kics-report" \
        --report-formats "$REPORT_FORMAT" \
        --type "Kubernetes,Dockerfile,Terraform" \
        --exclude-severities "info,low" \
        --fail-on "high" \
        --no-progress \
        --silent \
        || { log "WARNING" "KICS found compliance issues"; COMPLIANCE_ISSUES=true; }
    
    log "INFO" "Infrastructure compliance checks completed"
}

# Run secrets scanning to detect hardcoded credentials
check_secrets() {
    log "INFO" "Scanning for secrets and credentials..."
    
    # Create output directory for secrets scanning
    local secrets_output_dir="${OUTPUT_DIR}/secrets"
    mkdir -p "$secrets_output_dir"
    
    # Run TruffleHog for secrets scanning
    log "INFO" "Running TruffleHog for secrets detection..."
    $SECRETS_SCANNER filesystem --directory="$TARGET_PATH" \
        --json \
        --output="${secrets_output_dir}/secrets-report.json" \
        || { log "WARNING" "TruffleHog found potential secrets"; COMPLIANCE_ISSUES=true; }
    
    # Convert JSON to requested format if not JSON
    if [ "$REPORT_FORMAT" != "json" ]; then
        log "INFO" "Converting secrets report to ${REPORT_FORMAT} format"
        # This would require a conversion utility, using a placeholder
        touch "${secrets_output_dir}/secrets-report.${REPORT_FORMAT}"
    fi
    
    log "INFO" "Secrets scanning completed"
}

# Run license compliance checks
check_license_compliance() {
    log "INFO" "Checking license compliance..."
    
    # Create output directory for license checks
    local license_output_dir="${OUTPUT_DIR}/licenses"
    mkdir -p "$license_output_dir"
    
    # Check if FOSSology is available
    if command_exists "$LICENSE_SCANNER"; then
        log "INFO" "Running FOSSology for license scanning..."
        # This is a simplified example - actual FOSSology CLI usage would be more complex
        $LICENSE_SCANNER -d "$TARGET_PATH" -o "${license_output_dir}/license-report.json" \
            || { log "WARNING" "FOSSology found license compliance issues"; COMPLIANCE_ISSUES=true; }
    else
        # Fallback to a simpler license scanning approach
        log "INFO" "Using alternative license scanning method..."
        
        # Look for license files and package manifests
        find "$TARGET_PATH" -type f -name "LICENSE*" -o -name "COPYING*" -o -name "package.json" -o -name "pom.xml" -o -name "*.gradle" | \
        while read -r file; do
            log "INFO" "Found license-related file: $file"
            # Extract license information (simplified example)
            if [[ "$file" == *"package.json"* ]]; then
                grep -i "license" "$file" >> "${license_output_dir}/license-findings.txt" || true
            elif [[ "$file" == *"pom.xml"* ]]; then
                grep -i "<license>" -A 3 "$file" >> "${license_output_dir}/license-findings.txt" || true
            else
                head -n 20 "$file" >> "${license_output_dir}/license-findings.txt" || true
            fi
        done
        
        # Create a simple report
        echo "{\"license_files_found\": $(find "$TARGET_PATH" -type f -name "LICENSE*" -o -name "COPYING*" | wc -l)}" \
            > "${license_output_dir}/license-report.json"
    fi
    
    # Convert JSON to requested format if not JSON
    if [ "$REPORT_FORMAT" != "json" ]; then
        log "INFO" "Converting license report to ${REPORT_FORMAT} format"
        # This would require a conversion utility, using a placeholder
        touch "${license_output_dir}/license-report.${REPORT_FORMAT}"
    fi
    
    log "INFO" "License compliance checks completed"
}

# Run vulnerability scanning
check_vulnerabilities() {
    log "INFO" "Scanning for vulnerabilities..."
    
    # Create output directory for vulnerability scanning
    local vuln_output_dir="${OUTPUT_DIR}/vulnerabilities"
    mkdir -p "$vuln_output_dir"
    
    # Run Trivy for vulnerability scanning
    log "INFO" "Running Trivy for vulnerability detection..."
    $VULN_SCANNER fs --security-checks vuln,config,secret \
        --severity "${SEVERITY_LEVEL},CRITICAL,HIGH" \
        --output "${vuln_output_dir}/vuln-report.${REPORT_FORMAT}" \
        --format "$REPORT_FORMAT" \
        "$TARGET_PATH" \
        || { log "WARNING" "Trivy found vulnerabilities"; COMPLIANCE_ISSUES=true; }
    
    log "INFO" "Vulnerability scanning completed"
}

# Combine all reports into a single comprehensive report
generate_combined_report() {
    log "INFO" "Generating combined compliance report..."
    
    # This is a simplified example - a real implementation would parse and combine the reports
    # from each tool into a unified format
    
    cat > "${OUTPUT_DIR}/compliance-report.json" << EOF
{
    "scan_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "target": "$TARGET_PATH",
    "config": "$CONFIG_FILE",
    "compliance_status": "$([ "$COMPLIANCE_ISSUES" = true ] && echo "FAILED" || echo "PASSED")",
    "reports": {
        "infrastructure": "${OUTPUT_DIR}/infrastructure/",
        "secrets": "${OUTPUT_DIR}/secrets/",
        "licenses": "${OUTPUT_DIR}/licenses/",
        "vulnerabilities": "${OUTPUT_DIR}/vulnerabilities/"
    }
}
EOF
    
    # Convert to requested format if not JSON
    if [ "$REPORT_FORMAT" != "json" ]; then
        log "INFO" "Converting combined report to ${REPORT_FORMAT} format"
        # This would require a conversion utility, using a placeholder
        touch "${OUTPUT_DIR}/compliance-report.${REPORT_FORMAT}"
    fi
    
    log "SUCCESS" "Combined compliance report generated: ${OUTPUT_DIR}/compliance-report.${REPORT_FORMAT}"
}

# Send report to compliance tracking system
send_to_compliance_system() {
    log "INFO" "Sending report to compliance tracking system..."
    
    # This is a placeholder for integration with a compliance tracking system
    # In a real implementation, this would use an API to send the report to a system like Jira, ServiceNow, etc.
    
    # Example using curl to send to a hypothetical compliance API
    if [ -n "${COMPLIANCE_API_URL:-}" ] && [ -n "${COMPLIANCE_API_KEY:-}" ]; then
        log "INFO" "Uploading to compliance system at $COMPLIANCE_API_URL"
        
        curl -s -X POST \
            -H "Authorization: Bearer $COMPLIANCE_API_KEY" \
            -H "Content-Type: application/json" \
            -d @"${OUTPUT_DIR}/compliance-report.json" \
            "$COMPLIANCE_API_URL" > /dev/null || log "WARNING" "Failed to send report to compliance system"
            
        log "SUCCESS" "Report sent to compliance tracking system"
    else
        log "INFO" "Compliance tracking system integration not configured. Skipping upload."
    fi
}

# Main function to run all checks
run_compliance_checks() {
    log "INFO" "Starting compliance checks for: $TARGET_PATH"
    
    # Create output directory
    create_output_dir
    
    # Check if we can use cached results
    if check_cache; then
        log "SUCCESS" "Using cached compliance results"
        return 0
    fi
    
    # Run all compliance checks
    check_infrastructure_compliance
    check_secrets
    check_license_compliance
    check_vulnerabilities
    
    # Generate combined report
    generate_combined_report
    
    # Save results to cache for future runs
    save_to_cache
    
    # Send report to compliance tracking system
    send_to_compliance_system
    
    # Determine exit status based on findings and configuration
    if [ "$COMPLIANCE_ISSUES" = true ] && [ "$FAIL_ON_VIOLATIONS" = true ]; then
        log "ERROR" "Compliance checks failed. See report for details: ${OUTPUT_DIR}/compliance-report.${REPORT_FORMAT}"
        return 1
    else
        if [ "$COMPLIANCE_ISSUES" = true ]; then
            log "WARNING" "Compliance issues found but pipeline continues. See report for details: ${OUTPUT_DIR}/compliance-report.${REPORT_FORMAT}"
        else
            log "SUCCESS" "All compliance checks passed!"
        fi
        return 0
    fi
}

# ============================================================================
# Main Script
# ============================================================================

# Initialize variables with default values
TARGET_PATH="$DEFAULT_TARGET"
CONFIG_FILE="$DEFAULT_CONFIG"
OUTPUT_DIR="$DEFAULT_OUTPUT"
REPORT_FORMAT="$DEFAULT_FORMAT"
SEVERITY_LEVEL="$DEFAULT_SEVERITY"
FAIL_ON_VIOLATIONS=$DEFAULT_FAIL_ON_VIOLATIONS
USE_CACHE=$DEFAULT_USE_CACHE
COMPLIANCE_ISSUES=false

# Parse command line arguments
while [ $# -gt 0 ]; do
    case "$1" in
        -t|--target)
            TARGET_PATH="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -f|--format)
            REPORT_FORMAT="$2"
            shift 2
            ;;
        -s|--severity)
            SEVERITY_LEVEL="$2"
            shift 2
            ;;
        -n|--no-fail)
            FAIL_ON_VIOLATIONS=false
            shift
            ;;
        -k|--cache)
            USE_CACHE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate target path
if [ ! -e "$TARGET_PATH" ]; then
    log "ERROR" "Target path does not exist: $TARGET_PATH"
    exit 1
fi

# Validate config file if specified and not using default
if [ "$CONFIG_FILE" != "$DEFAULT_CONFIG" ] && [ ! -f "$CONFIG_FILE" ]; then
    log "ERROR" "Config file does not exist: $CONFIG_FILE"
    exit 1
fi

# Validate report format
case "$REPORT_FORMAT" in
    json|xml|html|text)
        # Valid format
        ;;
    *)
        log "ERROR" "Invalid report format: $REPORT_FORMAT. Must be one of: json, xml, html, text"
        exit 1
        ;;
esac

# Validate severity level
case "$SEVERITY_LEVEL" in
    info|low|medium|high|critical)
        # Valid severity
        ;;
    *)
        log "ERROR" "Invalid severity level: $SEVERITY_LEVEL. Must be one of: info, low, medium, high, critical"
        exit 1
        ;;
esac

# Install dependencies
install_dependencies

# Run compliance checks
run_compliance_checks
exit_code=$?

exit $exit_code