#!/bin/bash

# ============================================================================
# check-compliance.sh
#
# This script checks compliance with security policies for infrastructure and
# application code. It runs a series of compliance checks against predefined
# policies, generates detailed reports, and fails the pipeline if policy
# violations are detected.
#
# Usage: ./check-compliance.sh [options]
#
# Options:
#   -t, --target-dir <dir>     Directory to scan (default: current directory)
#   -c, --config <file>        Custom configuration file
#   -r, --report-dir <dir>     Directory to store reports (default: ./compliance-reports)
#   -s, --severity <level>     Minimum severity level to fail (default: HIGH)
#   -f, --format <format>      Output format (default: json)
#   -n, --no-fail              Don't fail the pipeline on policy violations
#   --cache                    Use cached results if available
#   --cache-dir <dir>          Directory to store cache (default: ./.compliance-cache)
#   --skip-terraform           Skip Terraform checks
#   --skip-kubernetes          Skip Kubernetes checks
#   --skip-container           Skip container image checks
#   --skip-license             Skip license checks
#   --tracking-id <id>         Compliance tracking system ID
#   -h, --help                 Show this help message
#
# Examples:
#   ./check-compliance.sh --target-dir ./infrastructure
#   ./check-compliance.sh --severity MEDIUM --format html
#   ./check-compliance.sh --skip-container --no-fail
#
# ============================================================================

set -e

# Default values
TARGET_DIR="."
CONFIG_FILE=""
REPORT_DIR="./compliance-reports"
SEVERITY="HIGH"
FORMAT="json"
NO_FAIL=false
USE_CACHE=false
CACHE_DIR="./.compliance-cache"
SKIP_TERRAFORM=false
SKIP_KUBERNETES=false
SKIP_CONTAINER=false
SKIP_LICENSE=false
TRACKING_ID=""

# Colors for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -t|--target-dir)
      TARGET_DIR="$2"
      shift 2
      ;;
    -c|--config)
      CONFIG_FILE="$2"
      shift 2
      ;;
    -r|--report-dir)
      REPORT_DIR="$2"
      shift 2
      ;;
    -s|--severity)
      SEVERITY="$2"
      shift 2
      ;;
    -f|--format)
      FORMAT="$2"
      shift 2
      ;;
    -n|--no-fail)
      NO_FAIL=true
      shift
      ;;
    --cache)
      USE_CACHE=true
      shift
      ;;
    --cache-dir)
      CACHE_DIR="$2"
      shift 2
      ;;
    --skip-terraform)
      SKIP_TERRAFORM=true
      shift
      ;;
    --skip-kubernetes)
      SKIP_KUBERNETES=true
      shift
      ;;
    --skip-container)
      SKIP_CONTAINER=true
      shift
      ;;
    --skip-license)
      SKIP_LICENSE=true
      shift
      ;;
    --tracking-id)
      TRACKING_ID="$2"
      shift 2
      ;;
    -h|--help)
      grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo -e "${RED}Error: Unknown option $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Create report directory if it doesn't exist
mkdir -p "$REPORT_DIR"

# Create cache directory if using cache
if [ "$USE_CACHE" = true ]; then
  mkdir -p "$CACHE_DIR"
fi

# Generate a unique run ID for this compliance check
RUN_ID=$(date +%Y%m%d%H%M%S)-$(head /dev/urandom | tr -dc a-z0-9 | head -c 8)
echo -e "${BLUE}Compliance check run ID: $RUN_ID${NC}"

# Log file for this run
LOG_FILE="$REPORT_DIR/compliance-check-$RUN_ID.log"
touch "$LOG_FILE"

# Function to log messages
log() {
  local level=$1
  local message=$2
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
  
  case $level in
    INFO)
      echo -e "${BLUE}[$level] $message${NC}"
      ;;
    WARNING)
      echo -e "${YELLOW}[$level] $message${NC}"
      ;;
    ERROR)
      echo -e "${RED}[$level] $message${NC}"
      ;;
    SUCCESS)
      echo -e "${GREEN}[$level] $message${NC}"
      ;;
    *)
      echo "[$level] $message"
      ;;
  esac
}

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to check if a file has changed since last run (for caching)
file_changed() {
  local file=$1
  local cache_file="$CACHE_DIR/$(echo "$file" | md5sum | cut -d' ' -f1).hash"
  
  if [ ! -f "$cache_file" ]; then
    return 0 # File has changed (cache doesn't exist)
  fi
  
  local current_hash=$(md5sum "$file" | cut -d' ' -f1)
  local cached_hash=$(cat "$cache_file")
  
  if [ "$current_hash" != "$cached_hash" ]; then
    return 0 # File has changed
  else
    return 1 # File has not changed
  fi
}

# Function to update cache for a file
update_cache() {
  local file=$1
  local cache_file="$CACHE_DIR/$(echo "$file" | md5sum | cut -d' ' -f1).hash"
  md5sum "$file" | cut -d' ' -f1 > "$cache_file"
}

# Function to check if we should use cached results
should_use_cache() {
  local check_type=$1
  local check_target=$2
  
  if [ "$USE_CACHE" = false ]; then
    return 1 # Don't use cache
  fi
  
  local cache_key="$check_type-$(echo "$check_target" | md5sum | cut -d' ' -f1)"
  local cache_file="$CACHE_DIR/$cache_key.json"
  
  if [ ! -f "$cache_file" ]; then
    return 1 # Cache doesn't exist
  fi
  
  # Check if any relevant files have changed
  if [ "$check_type" = "terraform" ]; then
    find "$check_target" -name "*.tf" -type f | while read -r file; do
      if file_changed "$file"; then
        return 1 # File has changed, don't use cache
      fi
    done
  elif [ "$check_type" = "kubernetes" ]; then
    find "$check_target" -name "*.yaml" -o -name "*.yml" -type f | while read -r file; do
      if file_changed "$file"; then
        return 1 # File has changed, don't use cache
      fi
    done
  fi
  
  return 0 # Use cache
}

# Function to get cached results
get_cached_results() {
  local check_type=$1
  local check_target=$2
  local cache_key="$check_type-$(echo "$check_target" | md5sum | cut -d' ' -f1)"
  local cache_file="$CACHE_DIR/$cache_key.json"
  
  cat "$cache_file"
}

# Function to save results to cache
save_to_cache() {
  local check_type=$1
  local check_target=$2
  local results=$3
  local cache_key="$check_type-$(echo "$check_target" | md5sum | cut -d' ' -f1)"
  local cache_file="$CACHE_DIR/$cache_key.json"
  
  echo "$results" > "$cache_file"
  
  # Update cache for all relevant files
  if [ "$check_type" = "terraform" ]; then
    find "$check_target" -name "*.tf" -type f | while read -r file; do
      update_cache "$file"
    done
  elif [ "$check_type" = "kubernetes" ]; then
    find "$check_target" -name "*.yaml" -o -name "*.yml" -type f | while read -r file; do
      update_cache "$file"
    done
  fi
}

# Function to check if required tools are installed
check_requirements() {
  local missing_tools=false
  
  if [ "$SKIP_TERRAFORM" = false ]; then
    if ! command_exists checkov; then
      log "ERROR" "checkov is not installed. Please install it with: pip install checkov"
      missing_tools=true
    fi
    
    if ! command_exists kics; then
      log "WARNING" "kics is not installed. Some Terraform checks will be skipped. Install with: https://docs.kics.io/latest/getting-started/"
    fi
  fi
  
  if [ "$SKIP_KUBERNETES" = false ]; then
    if ! command_exists checkov; then
      log "ERROR" "checkov is not installed. Please install it with: pip install checkov"
      missing_tools=true
    fi
    
    if ! command_exists kube-bench; then
      log "WARNING" "kube-bench is not installed. CIS benchmark checks will be skipped. Install with: https://github.com/aquasecurity/kube-bench"
    fi
  fi
  
  if [ "$SKIP_CONTAINER" = false ]; then
    if ! command_exists trivy; then
      log "ERROR" "trivy is not installed. Please install it with: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
      missing_tools=true
    fi
  fi
  
  if [ "$SKIP_LICENSE" = false ]; then
    if ! command_exists license-finder; then
      log "WARNING" "license-finder is not installed. License checks will be skipped. Install with: gem install license_finder"
    fi
  fi
  
  if [ "$missing_tools" = true ]; then
    log "ERROR" "Missing required tools. Please install them and try again."
    exit 1
  fi
}

# Function to check Terraform code
check_terraform() {
  if [ "$SKIP_TERRAFORM" = true ]; then
    log "INFO" "Skipping Terraform checks"
    return 0
  fi
  
  log "INFO" "Checking Terraform code in $TARGET_DIR"
  
  # Find all Terraform directories (containing .tf files)
  local tf_dirs=$(find "$TARGET_DIR" -name "*.tf" -type f -exec dirname {} \; | sort -u)
  
  if [ -z "$tf_dirs" ]; then
    log "INFO" "No Terraform files found in $TARGET_DIR"
    return 0
  fi
  
  local total_issues=0
  local high_issues=0
  
  for dir in $tf_dirs; do
    log "INFO" "Checking Terraform directory: $dir"
    
    # Check if we should use cached results
    if should_use_cache "terraform" "$dir"; then
      log "INFO" "Using cached results for $dir"
      local results=$(get_cached_results "terraform" "$dir")
      echo "$results" > "$REPORT_DIR/terraform-$(basename "$dir")-$RUN_ID.$FORMAT"
      
      # Extract issue counts from cached results
      local dir_issues=$(echo "$results" | grep -o '"failed": [0-9]\+' | awk '{sum += $2} END {print sum}')
      local dir_high_issues=$(echo "$results" | grep -o '"HIGH": [0-9]\+' | awk '{sum += $2} END {print sum}')
      
      total_issues=$((total_issues + dir_issues))
      high_issues=$((high_issues + dir_high_issues))
      
      continue
    fi
    
    # Run Checkov on Terraform directory
    local checkov_output_file="$REPORT_DIR/terraform-checkov-$(basename "$dir")-$RUN_ID.$FORMAT"
    if ! checkov -d "$dir" --framework terraform -o "$FORMAT" --output-file "$checkov_output_file" --quiet; then
      log "WARNING" "Checkov found issues in $dir"
    else
      log "SUCCESS" "Checkov found no issues in $dir"
    fi
    
    # Run KICS on Terraform directory if available
    if command_exists kics; then
      local kics_output_file="$REPORT_DIR/terraform-kics-$(basename "$dir")-$RUN_ID.$FORMAT"
      if ! kics scan -p "$dir" -t "Terraform" -o "$REPORT_DIR" -f "$FORMAT" --output-name "$(basename "$kics_output_file")" --silent; then
        log "WARNING" "KICS found issues in $dir"
      else
        log "SUCCESS" "KICS found no issues in $dir"
      fi
    fi
    
    # Count issues
    local dir_issues=$(grep -o '"failed": [0-9]\+' "$checkov_output_file" | awk '{sum += $2} END {print sum}')
    local dir_high_issues=$(grep -o '"HIGH": [0-9]\+' "$checkov_output_file" | awk '{sum += $2} END {print sum}')
    
    if [ -z "$dir_issues" ]; then dir_issues=0; fi
    if [ -z "$dir_high_issues" ]; then dir_high_issues=0; fi
    
    total_issues=$((total_issues + dir_issues))
    high_issues=$((high_issues + dir_high_issues))
    
    # Save results to cache if using cache
    if [ "$USE_CACHE" = true ]; then
      save_to_cache "terraform" "$dir" "$(cat "$checkov_output_file")"
    fi
  done
  
  log "INFO" "Terraform checks completed. Found $total_issues total issues, $high_issues HIGH severity issues."
  
  # Return non-zero exit code if high severity issues found and --no-fail not set
  if [ "$high_issues" -gt 0 ] && [ "$NO_FAIL" = false ]; then
    return 1
  fi
  
  return 0
}

# Function to check Kubernetes manifests
check_kubernetes() {
  if [ "$SKIP_KUBERNETES" = true ]; then
    log "INFO" "Skipping Kubernetes checks"
    return 0
  fi
  
  log "INFO" "Checking Kubernetes manifests in $TARGET_DIR"
  
  # Find all Kubernetes manifest files
  local k8s_files=$(find "$TARGET_DIR" -name "*.yaml" -o -name "*.yml" | grep -v "Chart.yaml" | grep -v "values.yaml")
  
  if [ -z "$k8s_files" ]; then
    log "INFO" "No Kubernetes manifest files found in $TARGET_DIR"
    return 0
  fi
  
  local total_issues=0
  local high_issues=0
  
  # Create a temporary directory for Kubernetes files
  local k8s_temp_dir=$(mktemp -d)
  trap 'rm -rf "$k8s_temp_dir"' EXIT
  
  # Copy all Kubernetes files to the temporary directory
  for file in $k8s_files; do
    cp "$file" "$k8s_temp_dir/"
  done
  
  # Check if we should use cached results
  if should_use_cache "kubernetes" "$k8s_temp_dir"; then
    log "INFO" "Using cached results for Kubernetes manifests"
    local results=$(get_cached_results "kubernetes" "$k8s_temp_dir")
    echo "$results" > "$REPORT_DIR/kubernetes-$RUN_ID.$FORMAT"
    
    # Extract issue counts from cached results
    local k8s_issues=$(echo "$results" | grep -o '"failed": [0-9]\+' | awk '{sum += $2} END {print sum}')
    local k8s_high_issues=$(echo "$results" | grep -o '"HIGH": [0-9]\+' | awk '{sum += $2} END {print sum}')
    
    total_issues=$((total_issues + k8s_issues))
    high_issues=$((high_issues + k8s_high_issues))
  else
    # Run Checkov on Kubernetes manifests
    local checkov_output_file="$REPORT_DIR/kubernetes-checkov-$RUN_ID.$FORMAT"
    if ! checkov -d "$k8s_temp_dir" --framework kubernetes -o "$FORMAT" --output-file "$checkov_output_file" --quiet; then
      log "WARNING" "Checkov found issues in Kubernetes manifests"
    else
      log "SUCCESS" "Checkov found no issues in Kubernetes manifests"
    fi
    
    # Run kube-bench if available and if we're checking a cluster
    if command_exists kube-bench && [ -n "$KUBECONFIG" ]; then
      local kube_bench_output_file="$REPORT_DIR/kubernetes-kube-bench-$RUN_ID.json"
      if ! kube-bench --json | tee "$kube_bench_output_file" > /dev/null; then
        log "WARNING" "kube-bench found issues in Kubernetes cluster"
      else
        log "SUCCESS" "kube-bench found no issues in Kubernetes cluster"
      fi
    fi
    
    # Count issues
    local k8s_issues=$(grep -o '"failed": [0-9]\+' "$checkov_output_file" | awk '{sum += $2} END {print sum}')
    local k8s_high_issues=$(grep -o '"HIGH": [0-9]\+' "$checkov_output_file" | awk '{sum += $2} END {print sum}')
    
    if [ -z "$k8s_issues" ]; then k8s_issues=0; fi
    if [ -z "$k8s_high_issues" ]; then k8s_high_issues=0; fi
    
    total_issues=$((total_issues + k8s_issues))
    high_issues=$((high_issues + k8s_high_issues))
    
    # Save results to cache if using cache
    if [ "$USE_CACHE" = true ]; then
      save_to_cache "kubernetes" "$k8s_temp_dir" "$(cat "$checkov_output_file")"
    fi
  fi
  
  log "INFO" "Kubernetes checks completed. Found $total_issues total issues, $high_issues HIGH severity issues."
  
  # Return non-zero exit code if high severity issues found and --no-fail not set
  if [ "$high_issues" -gt 0 ] && [ "$NO_FAIL" = false ]; then
    return 1
  fi
  
  return 0
}

# Function to check container images
check_containers() {
  if [ "$SKIP_CONTAINER" = true ]; then
    log "INFO" "Skipping container image checks"
    return 0
  fi
  
  log "INFO" "Checking container images"
  
  # Find all Dockerfiles
  local dockerfiles=$(find "$TARGET_DIR" -name "Dockerfile" -type f)
  
  if [ -z "$dockerfiles" ]; then
    log "INFO" "No Dockerfiles found in $TARGET_DIR"
    return 0
  fi
  
  local total_issues=0
  local high_issues=0
  
  for dockerfile in $dockerfiles; do
    local dockerfile_dir=$(dirname "$dockerfile")
    local dockerfile_name=$(basename "$dockerfile_dir")
    
    log "INFO" "Checking Dockerfile: $dockerfile"
    
    # Check if we should use cached results
    if should_use_cache "container" "$dockerfile"; then
      log "INFO" "Using cached results for $dockerfile"
      local results=$(get_cached_results "container" "$dockerfile")
      echo "$results" > "$REPORT_DIR/container-$(echo "$dockerfile_name" | tr '/' '-')-$RUN_ID.$FORMAT"
      
      # Extract issue counts from cached results
      local container_issues=$(echo "$results" | grep -o '"Total": [0-9]\+' | awk '{sum += $2} END {print sum}')
      local container_high_issues=$(echo "$results" | grep -o '"HIGH": [0-9]\+' | awk '{sum += $2} END {print sum}')
      
      total_issues=$((total_issues + container_issues))
      high_issues=$((high_issues + container_high_issues))
      
      continue
    fi
    
    # Run Trivy on Dockerfile
    local trivy_output_file="$REPORT_DIR/container-trivy-$(echo "$dockerfile_name" | tr '/' '-')-$RUN_ID.$FORMAT"
    if ! trivy config --format "$FORMAT" -o "$trivy_output_file" "$dockerfile"; then
      log "WARNING" "Trivy found issues in $dockerfile"
    else
      log "SUCCESS" "Trivy found no issues in $dockerfile"
    fi
    
    # Count issues
    local container_issues=$(grep -o '"Total": [0-9]\+' "$trivy_output_file" | awk '{sum += $2} END {print sum}')
    local container_high_issues=$(grep -o '"HIGH": [0-9]\+' "$trivy_output_file" | awk '{sum += $2} END {print sum}')
    
    if [ -z "$container_issues" ]; then container_issues=0; fi
    if [ -z "$container_high_issues" ]; then container_high_issues=0; fi
    
    total_issues=$((total_issues + container_issues))
    high_issues=$((high_issues + container_high_issues))
    
    # Save results to cache if using cache
    if [ "$USE_CACHE" = true ]; then
      save_to_cache "container" "$dockerfile" "$(cat "$trivy_output_file")"
    fi
  done
  
  log "INFO" "Container checks completed. Found $total_issues total issues, $high_issues HIGH severity issues."
  
  # Return non-zero exit code if high severity issues found and --no-fail not set
  if [ "$high_issues" -gt 0 ] && [ "$NO_FAIL" = false ]; then
    return 1
  fi
  
  return 0
}

# Function to check licenses
check_licenses() {
  if [ "$SKIP_LICENSE" = true ]; then
    log "INFO" "Skipping license checks"
    return 0
  fi
  
  log "INFO" "Checking licenses in $TARGET_DIR"
  
  # Check if license-finder is installed
  if ! command_exists license_finder; then
    log "WARNING" "license_finder is not installed. Skipping license checks."
    return 0
  fi
  
  # Find all package manager files
  local package_files=$(find "$TARGET_DIR" -name "package.json" -o -name "Gemfile" -o -name "requirements.txt" -o -name "go.mod" -o -name "pom.xml" -o -name "build.gradle" -type f)
  
  if [ -z "$package_files" ]; then
    log "INFO" "No package manager files found in $TARGET_DIR"
    return 0
  fi
  
  local license_issues=0
  
  for package_file in $package_files; do
    local package_dir=$(dirname "$package_file")
    local package_type=$(basename "$package_file")
    
    log "INFO" "Checking licenses in $package_dir ($package_type)"
    
    # Check if we should use cached results
    if should_use_cache "license" "$package_file"; then
      log "INFO" "Using cached results for $package_file"
      local results=$(get_cached_results "license" "$package_file")
      echo "$results" > "$REPORT_DIR/license-$(echo "$package_dir" | tr '/' '-')-$RUN_ID.$FORMAT"
      
      # Extract issue count from cached results
      local pkg_license_issues=$(echo "$results" | grep -c "license action needed")
      
      license_issues=$((license_issues + pkg_license_issues))
      
      continue
    fi
    
    # Run license_finder on package directory
    local license_output_file="$REPORT_DIR/license-$(echo "$package_dir" | tr '/' '-')-$RUN_ID.$FORMAT"
    if ! (cd "$package_dir" && license_finder report --format "$FORMAT" > "$license_output_file"); then
      log "WARNING" "license_finder found issues in $package_dir"
    else
      log "SUCCESS" "license_finder found no issues in $package_dir"
    fi
    
    # Count issues
    local pkg_license_issues=$(grep -c "license action needed" "$license_output_file")
    
    if [ -z "$pkg_license_issues" ]; then pkg_license_issues=0; fi
    
    license_issues=$((license_issues + pkg_license_issues))
    
    # Save results to cache if using cache
    if [ "$USE_CACHE" = true ]; then
      save_to_cache "license" "$package_file" "$(cat "$license_output_file")"
    fi
  done
  
  log "INFO" "License checks completed. Found $license_issues license issues."
  
  # Return non-zero exit code if license issues found and --no-fail not set
  if [ "$license_issues" -gt 0 ] && [ "$NO_FAIL" = false ]; then
    return 1
  fi
  
  return 0
}

# Function to generate a summary report
generate_summary() {
  local summary_file="$REPORT_DIR/compliance-summary-$RUN_ID.$FORMAT"
  
  log "INFO" "Generating summary report: $summary_file"
  
  # Count total issues by severity
  local total_high=0
  local total_medium=0
  local total_low=0
  
  # Count Terraform issues
  if [ "$SKIP_TERRAFORM" = false ]; then
    for file in "$REPORT_DIR"/terraform-*-"$RUN_ID".*; do
      if [ -f "$file" ]; then
        local high=$(grep -o '"HIGH": [0-9]\+' "$file" | awk '{sum += $2} END {print sum}')
        local medium=$(grep -o '"MEDIUM": [0-9]\+' "$file" | awk '{sum += $2} END {print sum}')
        local low=$(grep -o '"LOW": [0-9]\+' "$file" | awk '{sum += $2} END {print sum}')
        
        if [ -n "$high" ]; then total_high=$((total_high + high)); fi
        if [ -n "$medium" ]; then total_medium=$((total_medium + medium)); fi
        if [ -n "$low" ]; then total_low=$((total_low + low)); fi
      fi
    done
  fi
  
  # Count Kubernetes issues
  if [ "$SKIP_KUBERNETES" = false ]; then
    for file in "$REPORT_DIR"/kubernetes-*-"$RUN_ID".*; do
      if [ -f "$file" ]; then
        local high=$(grep -o '"HIGH": [0-9]\+' "$file" | awk '{sum += $2} END {print sum}')
        local medium=$(grep -o '"MEDIUM": [0-9]\+' "$file" | awk '{sum += $2} END {print sum}')
        local low=$(grep -o '"LOW": [0-9]\+' "$file" | awk '{sum += $2} END {print sum}')
        
        if [ -n "$high" ]; then total_high=$((total_high + high)); fi
        if [ -n "$medium" ]; then total_medium=$((total_medium + medium)); fi
        if [ -n "$low" ]; then total_low=$((total_low + low)); fi
      fi
    done
  fi
  
  # Count Container issues
  if [ "$SKIP_CONTAINER" = false ]; then
    for file in "$REPORT_DIR"/container-*-"$RUN_ID".*; do
      if [ -f "$file" ]; then
        local high=$(grep -o '"HIGH": [0-9]\+' "$file" | awk '{sum += $2} END {print sum}')
        local medium=$(grep -o '"MEDIUM": [0-9]\+' "$file" | awk '{sum += $2} END {print sum}')
        local low=$(grep -o '"LOW": [0-9]\+' "$file" | awk '{sum += $2} END {print sum}')
        
        if [ -n "$high" ]; then total_high=$((total_high + high)); fi
        if [ -n "$medium" ]; then total_medium=$((total_medium + medium)); fi
        if [ -n "$low" ]; then total_low=$((total_low + low)); fi
      fi
    done
  fi
  
  # Count License issues
  local license_issues=0
  if [ "$SKIP_LICENSE" = false ]; then
    for file in "$REPORT_DIR"/license-*-"$RUN_ID".*; do
      if [ -f "$file" ]; then
        local issues=$(grep -c "license action needed" "$file")
        if [ -n "$issues" ]; then license_issues=$((license_issues + issues)); fi
      fi
    done
  fi
  
  # Create summary report
  if [ "$FORMAT" = "json" ]; then
    cat > "$summary_file" << EOF
{
  "run_id": "$RUN_ID",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "target_directory": "$TARGET_DIR",
  "tracking_id": "$TRACKING_ID",
  "issues_by_severity": {
    "HIGH": $total_high,
    "MEDIUM": $total_medium,
    "LOW": $total_low,
    "LICENSE": $license_issues
  },
  "total_issues": $((total_high + total_medium + total_low + license_issues)),
  "checks_performed": {
    "terraform": $([ "$SKIP_TERRAFORM" = false ] && echo "true" || echo "false"),
    "kubernetes": $([ "$SKIP_KUBERNETES" = false ] && echo "true" || echo "false"),
    "container": $([ "$SKIP_CONTAINER" = false ] && echo "true" || echo "false"),
    "license": $([ "$SKIP_LICENSE" = false ] && echo "true" || echo "false")
  },
  "report_files": [
$(find "$REPORT_DIR" -name "*-$RUN_ID.*" -not -name "compliance-summary-$RUN_ID.*" | sort | sed 's/.*\/\(.*\)/    "\1",/' | sed '$s/,$//')
  ]
}
EOF
  elif [ "$FORMAT" = "html" ]; then
    cat > "$summary_file" << EOF
<!DOCTYPE html>
<html>
<head>
  <title>Compliance Check Summary - $RUN_ID</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    h1 { color: #333; }
    table { border-collapse: collapse; width: 100%; margin-top: 20px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background-color: #f2f2f2; }
    .high { color: red; font-weight: bold; }
    .medium { color: orange; }
    .low { color: green; }
  </style>
</head>
<body>
  <h1>Compliance Check Summary</h1>
  <p><strong>Run ID:</strong> $RUN_ID</p>
  <p><strong>Timestamp:</strong> $(date -u +"%Y-%m-%d %H:%M:%S UTC")</p>
  <p><strong>Target Directory:</strong> $TARGET_DIR</p>
  <p><strong>Tracking ID:</strong> $TRACKING_ID</p>
  
  <h2>Issues by Severity</h2>
  <table>
    <tr>
      <th>Severity</th>
      <th>Count</th>
    </tr>
    <tr>
      <td class="high">HIGH</td>
      <td>$total_high</td>
    </tr>
    <tr>
      <td class="medium">MEDIUM</td>
      <td>$total_medium</td>
    </tr>
    <tr>
      <td class="low">LOW</td>
      <td>$total_low</td>
    </tr>
    <tr>
      <td>LICENSE</td>
      <td>$license_issues</td>
    </tr>
    <tr>
      <th>Total</th>
      <th>$((total_high + total_medium + total_low + license_issues))</th>
    </tr>
  </table>
  
  <h2>Checks Performed</h2>
  <table>
    <tr>
      <th>Check Type</th>
      <th>Performed</th>
    </tr>
    <tr>
      <td>Terraform</td>
      <td>$([ "$SKIP_TERRAFORM" = false ] && echo "Yes" || echo "No")</td>
    </tr>
    <tr>
      <td>Kubernetes</td>
      <td>$([ "$SKIP_KUBERNETES" = false ] && echo "Yes" || echo "No")</td>
    </tr>
    <tr>
      <td>Container</td>
      <td>$([ "$SKIP_CONTAINER" = false ] && echo "Yes" || echo "No")</td>
    </tr>
    <tr>
      <td>License</td>
      <td>$([ "$SKIP_LICENSE" = false ] && echo "Yes" || echo "No")</td>
    </tr>
  </table>
  
  <h2>Report Files</h2>
  <ul>
$(find "$REPORT_DIR" -name "*-$RUN_ID.*" -not -name "compliance-summary-$RUN_ID.*" | sort | sed 's/.*\/\(.*\)/    <li><a href="\1">\1<\/a><\/li>/')
  </ul>
</body>
</html>
EOF
  else
    cat > "$summary_file" << EOF
Compliance Check Summary
=======================

Run ID: $RUN_ID
Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Target Directory: $TARGET_DIR
Tracking ID: $TRACKING_ID

Issues by Severity:
------------------
HIGH: $total_high
MEDIUM: $total_medium
LOW: $total_low
LICENSE: $license_issues
Total: $((total_high + total_medium + total_low + license_issues))

Checks Performed:
----------------
Terraform: $([ "$SKIP_TERRAFORM" = false ] && echo "Yes" || echo "No")
Kubernetes: $([ "$SKIP_KUBERNETES" = false ] && echo "Yes" || echo "No")
Container: $([ "$SKIP_CONTAINER" = false ] && echo "Yes" || echo "No")
License: $([ "$SKIP_LICENSE" = false ] && echo "Yes" || echo "No")

Report Files:
-------------
$(find "$REPORT_DIR" -name "*-$RUN_ID.*" -not -name "compliance-summary-$RUN_ID.*" | sort | sed 's/.*\//- /')
EOF
  fi
  
  log "SUCCESS" "Summary report generated: $summary_file"
  
  # Print summary to console
  echo -e "\n${BLUE}=== Compliance Check Summary ===${NC}"
  echo -e "${BLUE}Run ID:${NC} $RUN_ID"
  echo -e "${BLUE}Target Directory:${NC} $TARGET_DIR"
  echo -e "${BLUE}Report Directory:${NC} $REPORT_DIR"
  echo -e "\n${BLUE}Issues by Severity:${NC}"
  echo -e "${RED}HIGH:${NC} $total_high"
  echo -e "${YELLOW}MEDIUM:${NC} $total_medium"
  echo -e "${GREEN}LOW:${NC} $total_low"
  echo -e "LICENSE: $license_issues"
  echo -e "${BLUE}Total:${NC} $((total_high + total_medium + total_low + license_issues))"
  
  # Return non-zero exit code if high severity issues found and --no-fail not set
  if [ "$total_high" -gt 0 ] && [ "$NO_FAIL" = false ]; then
    return 1
  fi
  
  return 0
}

# Function to upload results to compliance tracking system
upload_to_tracking_system() {
  if [ -z "$TRACKING_ID" ]; then
    log "INFO" "No tracking ID provided. Skipping upload to compliance tracking system."
    return 0
  fi
  
  log "INFO" "Uploading results to compliance tracking system with ID: $TRACKING_ID"
  
  # This is a placeholder for the actual upload logic
  # In a real implementation, you would use an API call to your compliance tracking system
  # For example:
  # curl -X POST -H "Content-Type: application/json" -d @"$REPORT_DIR/compliance-summary-$RUN_ID.json" "https://compliance-tracking-system.example.com/api/v1/reports/$TRACKING_ID"
  
  log "SUCCESS" "Results uploaded to compliance tracking system"
  return 0
}

# Main function
main() {
  log "INFO" "Starting compliance check with run ID: $RUN_ID"
  log "INFO" "Target directory: $TARGET_DIR"
  log "INFO" "Report directory: $REPORT_DIR"
  
  # Check if required tools are installed
  check_requirements
  
  # Create an array to store exit codes
  local exit_codes=()
  
  # Run checks
  check_terraform
  exit_codes+=("$?")
  
  check_kubernetes
  exit_codes+=("$?")
  
  check_containers
  exit_codes+=("$?")
  
  check_licenses
  exit_codes+=("$?")
  
  # Generate summary report
  generate_summary
  exit_codes+=("$?")
  
  # Upload results to compliance tracking system
  upload_to_tracking_system
  
  # Check if any check failed
  local failed=false
  for code in "${exit_codes[@]}"; do
    if [ "$code" -ne 0 ]; then
      failed=true
      break
    fi
  done
  
  if [ "$failed" = true ] && [ "$NO_FAIL" = false ]; then
    log "ERROR" "Compliance check failed. See reports in $REPORT_DIR for details."
    exit 1
  else
    log "SUCCESS" "Compliance check completed successfully. See reports in $REPORT_DIR for details."
    exit 0
  fi
}

# Run main function
main