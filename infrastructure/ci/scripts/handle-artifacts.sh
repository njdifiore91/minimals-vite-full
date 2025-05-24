#!/bin/bash

# handle-artifacts.sh
#
# This script manages build artifacts throughout the CI/CD pipeline, including storage,
# retrieval, and cleanup with proper versioning. It stores artifacts with appropriate
# metadata, retrieves them for deployments, and cleans up old artifacts to prevent storage bloat.
#
# Part of the MCA Application Processing System infrastructure.
#
# Usage: ./handle-artifacts.sh --action <store|retrieve|cleanup|verify|index> --service <service-name> [options]

set -eo pipefail

# Default values
ACTION=""
SERVICE=""
ENVIRONMENT="development"
ARTIFACT_TYPE=""
ARTIFACT_PATH=""
VERSION=""
TAG=""
RETENTION_DAYS=30
VERBOSE=false
FORCE=false
REPOSITORY_TYPE="s3"
REPOSITORY_URL=""
REPOSITORY_USER=""
REPOSITORY_TOKEN=""
METADATA_FILE=""
CHECKSUM_ALGORITHM="sha256"
TIMEOUT=300
RETRIES=3
RETRY_DELAY=10

# MCA Application Processing System specific settings
MCA_CONFIG_DIR="${REPO_ROOT}/infrastructure/ci/config"
MCA_ARTIFACTS_DIR="${REPO_ROOT}/artifacts"

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
    --action)
      ACTION="$2"
      shift 2
      ;;
    --service)
      SERVICE="$2"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --artifact-type)
      ARTIFACT_TYPE="$2"
      shift 2
      ;;
    --artifact-path)
      ARTIFACT_PATH="$2"
      shift 2
      ;;
    --version)
      VERSION="$2"
      shift 2
      ;;
    --tag)
      TAG="$2"
      shift 2
      ;;
    --retention-days)
      RETENTION_DAYS="$2"
      shift 2
      ;;
    --repository-type)
      REPOSITORY_TYPE="$2"
      shift 2
      ;;
    --repository-url)
      REPOSITORY_URL="$2"
      shift 2
      ;;
    --repository-user)
      REPOSITORY_USER="$2"
      shift 2
      ;;
    --repository-token)
      REPOSITORY_TOKEN="$2"
      shift 2
      ;;
    --metadata-file)
      METADATA_FILE="$2"
      shift 2
      ;;
    --checksum-algorithm)
      CHECKSUM_ALGORITHM="$2"
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
    --force)
      FORCE=true
      shift
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --help)
      echo "Usage: ./handle-artifacts.sh --action <store|retrieve|cleanup|verify> --service <service-name> [options]"
      echo ""
      echo "Actions:"
      echo "  store     Store artifacts in the repository"
      echo "  retrieve  Retrieve artifacts from the repository"
      echo "  cleanup   Clean up old artifacts based on retention policy"
      echo "  verify    Verify artifact integrity"
      echo "  index     Index artifact metadata for searching"
      echo ""
      echo "Required arguments:"
      echo "  --action          Action to perform (required)"
      echo "  --service         Service name (required)"
      echo ""
      echo "Options:"
      echo "  --environment      Target environment (development, staging, production) (default: development)"
      echo "  --artifact-type    Type of artifact (ui, container, helm, terraform, etc.)"
      echo "  --artifact-path    Path to the artifact file or directory"
      echo "  --version          Artifact version (default: derived from git)"
      echo "  --tag              Additional tag for the artifact"
      echo "  --retention-days   Number of days to retain artifacts (default: 30)"
      echo "  --repository-type  Repository type (s3, nexus, artifactory) (default: s3)"
      echo "  --repository-url   Repository URL"
      echo "  --repository-user  Repository username"
      echo "  --repository-token Repository token/password"
      echo "  --metadata-file    Path to additional metadata JSON file"
      echo "  --checksum-algorithm  Algorithm for checksums (md5, sha1, sha256, sha512) (default: sha256)"
      echo "  --timeout          Timeout in seconds for operations (default: 300)"
      echo "  --retries          Number of retries for operations (default: 3)"
      echo "  --retry-delay      Delay between retries in seconds (default: 10)"
      echo "  --force            Force operation even if validation fails"
      echo "  --verbose          Enable verbose logging"
      echo "  --help             Display this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run './handle-artifacts.sh --help' for usage information"
      exit 1
      ;;
  esac
done

# Validate required arguments
if [ -z "$ACTION" ] || [ -z "$SERVICE" ]; then
  echo -e "${RED}Error: Missing required arguments${NC}"
  echo "Run './handle-artifacts.sh --help' for usage information"
  exit 1
fi

# Validate action
if [[ "$ACTION" != "store" && "$ACTION" != "retrieve" && "$ACTION" != "cleanup" && "$ACTION" != "verify" && "$ACTION" != "index" ]]; then
  echo -e "${RED}Error: Invalid action. Must be one of: store, retrieve, cleanup, verify, index${NC}"
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
  local log_dir="${REPO_ROOT}/logs/artifacts"
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

# Function to check required tools
check_required_tools() {
  log_verbose "Checking required tools"
  
  # Check for common tools
  for tool in jq curl tar gzip; do
    if ! command -v $tool &> /dev/null; then
      log "ERROR" "$tool is not installed or not in PATH"
      return 1
    fi
  done
  
  # Check for repository-specific tools
  case "$REPOSITORY_TYPE" in
    "s3")
      if ! command -v aws &> /dev/null; then
        log "ERROR" "aws CLI is not installed or not in PATH"
        return 1
      fi
      ;;
    "nexus")
      # Nexus uses curl which we already checked
      ;;
    "artifactory")
      # Artifactory uses curl which we already checked
      ;;
    *)
      log "ERROR" "Unsupported repository type: $REPOSITORY_TYPE"
      return 1
      ;;
  esac
  
  return 0
}

# Function to determine artifact version if not provided
determine_version() {
  if [ -n "$VERSION" ]; then
    log_verbose "Using provided version: $VERSION"
    return 0
  fi
  
  log_verbose "Determining version from Git"
  
  # Check if we're in a Git repository
  if [ -d "${REPO_ROOT}/.git" ]; then
    # Get the Git commit SHA
    local git_commit=$(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null)
    
    if [ -n "$git_commit" ]; then
      # Check if there's a tag pointing to this commit
      local git_tag=$(git -C "${REPO_ROOT}" tag --points-at HEAD 2>/dev/null | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
      
      if [ -n "$git_tag" ]; then
        # Use the tag as the version (without the 'v' prefix)
        VERSION="${git_tag#v}"
        log_verbose "Using Git tag as version: $VERSION"
      else
        # Use the commit SHA as the version
        VERSION="0.0.0-${git_commit}"
        log_verbose "Using Git commit as version: $VERSION"
      fi
    else
      log "WARN" "Failed to get Git commit SHA"
      VERSION="0.0.0-unknown"
    fi
  else
    log "WARN" "Not a Git repository, using timestamp as version"
    VERSION="0.0.0-$(date +"%Y%m%d%H%M%S")"
  fi
  
  log "INFO" "Determined version: $VERSION"
  return 0
}

# Function to determine artifact type if not provided
determine_artifact_type() {
  if [ -n "$ARTIFACT_TYPE" ]; then
    log_verbose "Using provided artifact type: $ARTIFACT_TYPE"
    return 0
  fi
  
  log_verbose "Determining artifact type based on service and path"
  
  # Determine artifact type based on service name and path
  case "$SERVICE" in
    "frontend")
      ARTIFACT_TYPE="ui"
      ;;
    "email-service" | "notification-service")
      ARTIFACT_TYPE="node"
      ;;
    "document-service" | "ocr-service")
      ARTIFACT_TYPE="python"
      ;;
    "data-service")
      ARTIFACT_TYPE="java"
      ;;
    "api-gateway")
      ARTIFACT_TYPE="kong"
      ;;
    *)
      # Try to determine from the artifact path
      if [[ "$ARTIFACT_PATH" == *".jar" ]]; then
        ARTIFACT_TYPE="java"
      elif [[ "$ARTIFACT_PATH" == *".zip" && -d "${REPO_ROOT}/frontend/dist" ]]; then
        ARTIFACT_TYPE="ui"
      elif [[ "$ARTIFACT_PATH" == *".tar.gz" && -f "${REPO_ROOT}/Dockerfile" ]]; then
        ARTIFACT_TYPE="container"
      elif [[ -d "${REPO_ROOT}/infrastructure/terraform" && "$ARTIFACT_PATH" == *".tfplan" ]]; then
        ARTIFACT_TYPE="terraform"
      elif [[ -d "${REPO_ROOT}/infrastructure/kubernetes" && "$ARTIFACT_PATH" == *".yaml" ]]; then
        ARTIFACT_TYPE="kubernetes"
      else
        log "WARN" "Could not determine artifact type, using 'generic'"
        ARTIFACT_TYPE="generic"
      fi
      ;;
  esac
  
  log "INFO" "Determined artifact type: $ARTIFACT_TYPE"
  return 0
}

# Function to generate artifact metadata
generate_metadata() {
  log "INFO" "Generating artifact metadata"
  
  local artifact_file=$(basename "$ARTIFACT_PATH")
  local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local hostname=$(hostname)
  local username=$(whoami)
  local git_commit=""
  local git_branch=""
  local build_number="${BUILD_NUMBER:-unknown}"
  local build_url="${BUILD_URL:-unknown}"
  local job_name="${JOB_NAME:-unknown}"
  
  # Get Git information if available
  if [ -d "${REPO_ROOT}/.git" ]; then
    git_commit=$(git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || echo "unknown")
    git_branch=$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
  fi
  
  # Calculate checksums
  local checksum=""
  case "$CHECKSUM_ALGORITHM" in
    "md5")
      checksum=$(md5sum "$ARTIFACT_PATH" | awk '{print $1}')
      ;;
    "sha1")
      checksum=$(sha1sum "$ARTIFACT_PATH" | awk '{print $1}')
      ;;
    "sha256")
      checksum=$(sha256sum "$ARTIFACT_PATH" | awk '{print $1}')
      ;;
    "sha512")
      checksum=$(sha512sum "$ARTIFACT_PATH" | awk '{print $1}')
      ;;
    *)
      log "WARN" "Unsupported checksum algorithm: $CHECKSUM_ALGORITHM, using sha256"
      checksum=$(sha256sum "$ARTIFACT_PATH" | awk '{print $1}')
      ;;
  esac
  
  # Get file size
  local file_size=$(stat -c%s "$ARTIFACT_PATH")
  
  # Create metadata JSON
  local metadata_json="{
    \"service\": \"$SERVICE\",
    \"environment\": \"$ENVIRONMENT\",
    \"artifact_type\": \"$ARTIFACT_TYPE\",
    \"artifact_name\": \"$artifact_file\",
    \"version\": \"$VERSION\",
    \"tag\": \"$TAG\",
    \"timestamp\": \"$timestamp\",
    \"build_number\": \"$build_number\",
    \"build_url\": \"$build_url\",
    \"job_name\": \"$job_name\",
    \"git_commit\": \"$git_commit\",
    \"git_branch\": \"$git_branch\",
    \"checksum_algorithm\": \"$CHECKSUM_ALGORITHM\",
    \"checksum\": \"$checksum\",
    \"file_size\": $file_size,
    \"created_by\": \"$username\",
    \"hostname\": \"$hostname\"
  }"
  
  # Merge with additional metadata if provided
  if [ -n "$METADATA_FILE" ] && [ -f "$METADATA_FILE" ]; then
    log_verbose "Merging with additional metadata from $METADATA_FILE"
    metadata_json=$(jq -s '.[0] * .[1]' <(echo "$metadata_json") "$METADATA_FILE")
  fi
  
  # Create metadata file
  local metadata_dir="${MCA_ARTIFACTS_DIR}/metadata/${SERVICE}/${ENVIRONMENT}"
  mkdir -p "$metadata_dir"
  local metadata_path="${metadata_dir}/${SERVICE}-${VERSION}.json"
  echo "$metadata_json" > "$metadata_path"
  
  log "SUCCESS" "Metadata generated and saved to $metadata_path"
  echo "$metadata_path"
  return 0
}

# Function to determine repository URL if not provided
determine_repository_url() {
  if [ -n "$REPOSITORY_URL" ]; then
    log_verbose "Using provided repository URL: $REPOSITORY_URL"
    return 0
  fi
  
  log_verbose "Determining repository URL based on repository type and environment"
  
  # Check environment variables first
  case "$REPOSITORY_TYPE" in
    "s3")
      if [ -n "$S3_ARTIFACT_BUCKET" ]; then
        REPOSITORY_URL="$S3_ARTIFACT_BUCKET"
      fi
      ;;
    "nexus")
      if [ -n "$NEXUS_URL" ]; then
        REPOSITORY_URL="$NEXUS_URL"
      fi
      ;;
    "artifactory")
      if [ -n "$ARTIFACTORY_URL" ]; then
        REPOSITORY_URL="$ARTIFACTORY_URL"
      fi
      ;;
  esac
  
  # If still not set, check config files
  if [ -z "$REPOSITORY_URL" ]; then
    local config_file="${MCA_CONFIG_DIR}/artifacts-${ENVIRONMENT}.conf"
    if [ -f "$config_file" ]; then
      case "$REPOSITORY_TYPE" in
        "s3")
          REPOSITORY_URL=$(grep -oP 'S3_ARTIFACT_BUCKET=\K.*' "$config_file" || echo "")
          ;;
        "nexus")
          REPOSITORY_URL=$(grep -oP 'NEXUS_URL=\K.*' "$config_file" || echo "")
          ;;
        "artifactory")
          REPOSITORY_URL=$(grep -oP 'ARTIFACTORY_URL=\K.*' "$config_file" || echo "")
          ;;
      esac
    fi
  fi
  
  # If still not set, use default based on environment
  if [ -z "$REPOSITORY_URL" ]; then
    case "$REPOSITORY_TYPE" in
      "s3")
        REPOSITORY_URL="mca-artifacts-${ENVIRONMENT}"
        ;;
      "nexus")
        REPOSITORY_URL="https://nexus.example.com/repository/mca-${ENVIRONMENT}"
        ;;
      "artifactory")
        REPOSITORY_URL="https://artifactory.example.com/artifactory/mca-${ENVIRONMENT}"
        ;;
    esac
    log "WARN" "Repository URL not provided, using default: $REPOSITORY_URL"
  fi
  
  log "INFO" "Using repository URL: $REPOSITORY_URL"
  return 0
}

# Function to determine repository credentials if not provided
determine_repository_credentials() {
  # If credentials are already provided, use them
  if [ -n "$REPOSITORY_USER" ] && [ -n "$REPOSITORY_TOKEN" ]; then
    log_verbose "Using provided repository credentials"
    return 0
  fi
  
  log_verbose "Determining repository credentials based on repository type and environment"
  
  # For S3, we rely on AWS CLI configuration or instance profile
  if [ "$REPOSITORY_TYPE" = "s3" ]; then
    log_verbose "Using AWS CLI configuration for S3 authentication"
    return 0
  fi
  
  # Check environment variables first
  case "$REPOSITORY_TYPE" in
    "nexus")
      if [ -n "$NEXUS_USER" ] && [ -n "$NEXUS_TOKEN" ]; then
        REPOSITORY_USER="$NEXUS_USER"
        REPOSITORY_TOKEN="$NEXUS_TOKEN"
      fi
      ;;
    "artifactory")
      if [ -n "$ARTIFACTORY_USER" ] && [ -n "$ARTIFACTORY_TOKEN" ]; then
        REPOSITORY_USER="$ARTIFACTORY_USER"
        REPOSITORY_TOKEN="$ARTIFACTORY_TOKEN"
      fi
      ;;
  esac
  
  # If still not set, check config files
  if [ -z "$REPOSITORY_USER" ] || [ -z "$REPOSITORY_TOKEN" ]; then
    local config_file="${MCA_CONFIG_DIR}/artifacts-${ENVIRONMENT}.conf"
    if [ -f "$config_file" ]; then
      case "$REPOSITORY_TYPE" in
        "nexus")
          REPOSITORY_USER=$(grep -oP 'NEXUS_USER=\K.*' "$config_file" || echo "")
          REPOSITORY_TOKEN=$(grep -oP 'NEXUS_TOKEN=\K.*' "$config_file" || echo "")
          ;;
        "artifactory")
          REPOSITORY_USER=$(grep -oP 'ARTIFACTORY_USER=\K.*' "$config_file" || echo "")
          REPOSITORY_TOKEN=$(grep -oP 'ARTIFACTORY_TOKEN=\K.*' "$config_file" || echo "")
          ;;
      esac
    fi
  fi
  
  # Validate credentials for non-S3 repositories
  if [ "$REPOSITORY_TYPE" != "s3" ] && ([ -z "$REPOSITORY_USER" ] || [ -z "$REPOSITORY_TOKEN" ]); then
    log "ERROR" "Repository credentials not found for $REPOSITORY_TYPE"
    return 1
  fi
  
  log_verbose "Repository credentials determined successfully"
  return 0
}

# Function to store artifact in repository
store_artifact() {
  log "INFO" "Storing artifact: $ARTIFACT_PATH"
  
  # Validate artifact path
  if [ ! -f "$ARTIFACT_PATH" ]; then
    log "ERROR" "Artifact file not found: $ARTIFACT_PATH"
    return 1
  fi
  
  # Generate metadata
  local metadata_path=$(generate_metadata)
  if [ $? -ne 0 ]; then
    log "ERROR" "Failed to generate metadata"
    return 1
  fi
  
  # Determine repository URL and credentials
  determine_repository_url
  determine_repository_credentials
  
  # Prepare artifact for storage
  local artifact_file=$(basename "$ARTIFACT_PATH")
  local artifact_key="${SERVICE}/${VERSION}/${artifact_file}"
  local metadata_file=$(basename "$metadata_path")
  local metadata_key="metadata/${SERVICE}/${VERSION}/${metadata_file}"
  
  # Store artifact based on repository type
  case "$REPOSITORY_TYPE" in
    "s3")
      log "INFO" "Uploading artifact to S3: $REPOSITORY_URL/$artifact_key"
      
      # Upload artifact
      local s3_cmd="aws s3 cp \"$ARTIFACT_PATH\" s3://\"$REPOSITORY_URL/$artifact_key\" --metadata-directive REPLACE"
      if [ "$VERBOSE" = true ]; then
        s3_cmd="$s3_cmd --debug"
      fi
      
      if ! retry "$s3_cmd" "Upload artifact to S3"; then
        log "ERROR" "Failed to upload artifact to S3"
        return 1
      fi
      
      # Upload metadata
      log "INFO" "Uploading metadata to S3: $REPOSITORY_URL/$metadata_key"
      s3_cmd="aws s3 cp \"$metadata_path\" s3://\"$REPOSITORY_URL/$metadata_key\" --content-type application/json --metadata-directive REPLACE"
      if [ "$VERBOSE" = true ]; then
        s3_cmd="$s3_cmd --debug"
      fi
      
      if ! retry "$s3_cmd" "Upload metadata to S3"; then
        log "ERROR" "Failed to upload metadata to S3"
        return 1
      fi
      
      # Add tags if specified
      if [ -n "$TAG" ]; then
        log "INFO" "Adding tag to S3 object: $TAG"
        local tag_cmd="aws s3api put-object-tagging --bucket \"$REPOSITORY_URL\" --key \"$artifact_key\" --tagging 'TagSet=[{Key=\"tag\",Value=\"$TAG\"}]'"
        
        if ! retry "$tag_cmd" "Add tag to S3 object"; then
          log "WARN" "Failed to add tag to S3 object, but artifact was uploaded successfully"
        fi
      fi
      ;;
      
    "nexus")
      log "INFO" "Uploading artifact to Nexus: $REPOSITORY_URL/$artifact_key"
      
      # Upload artifact
      local nexus_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X PUT \"$REPOSITORY_URL/$artifact_key\" --upload-file \"$ARTIFACT_PATH\" -H \"Content-Type: application/octet-stream\""
      if [ "$VERBOSE" = true ]; then
        nexus_cmd="$nexus_cmd -v"
      else
        nexus_cmd="$nexus_cmd -s"
      fi
      
      if ! retry "$nexus_cmd" "Upload artifact to Nexus"; then
        log "ERROR" "Failed to upload artifact to Nexus"
        return 1
      fi
      
      # Upload metadata
      log "INFO" "Uploading metadata to Nexus: $REPOSITORY_URL/$metadata_key"
      nexus_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X PUT \"$REPOSITORY_URL/$metadata_key\" --upload-file \"$metadata_path\" -H \"Content-Type: application/json\""
      if [ "$VERBOSE" = true ]; then
        nexus_cmd="$nexus_cmd -v"
      else
        nexus_cmd="$nexus_cmd -s"
      fi
      
      if ! retry "$nexus_cmd" "Upload metadata to Nexus"; then
        log "ERROR" "Failed to upload metadata to Nexus"
        return 1
      fi
      ;;
      
    "artifactory")
      log "INFO" "Uploading artifact to Artifactory: $REPOSITORY_URL/$artifact_key"
      
      # Upload artifact with properties
      local props="service=$SERVICE;environment=$ENVIRONMENT;version=$VERSION"
      if [ -n "$TAG" ]; then
        props="$props;tag=$TAG"
      fi
      
      local artifactory_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X PUT \"$REPOSITORY_URL/$artifact_key;$props\" --upload-file \"$ARTIFACT_PATH\" -H \"Content-Type: application/octet-stream\""
      if [ "$VERBOSE" = true ]; then
        artifactory_cmd="$artifactory_cmd -v"
      else
        artifactory_cmd="$artifactory_cmd -s"
      fi
      
      if ! retry "$artifactory_cmd" "Upload artifact to Artifactory"; then
        log "ERROR" "Failed to upload artifact to Artifactory"
        return 1
      fi
      
      # Upload metadata
      log "INFO" "Uploading metadata to Artifactory: $REPOSITORY_URL/$metadata_key"
      artifactory_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X PUT \"$REPOSITORY_URL/$metadata_key;$props\" --upload-file \"$metadata_path\" -H \"Content-Type: application/json\""
      if [ "$VERBOSE" = true ]; then
        artifactory_cmd="$artifactory_cmd -v"
      else
        artifactory_cmd="$artifactory_cmd -s"
      fi
      
      if ! retry "$artifactory_cmd" "Upload metadata to Artifactory"; then
        log "ERROR" "Failed to upload metadata to Artifactory"
        return 1
      fi
      ;;
  esac
  
  log "SUCCESS" "Artifact stored successfully: $SERVICE/$VERSION/$artifact_file"
  return 0
}

# Function to retrieve artifact from repository
retrieve_artifact() {
  log "INFO" "Retrieving artifact for $SERVICE version $VERSION"
  
  # Determine repository URL and credentials
  determine_repository_url
  determine_repository_credentials
  
  # Determine output path if not provided
  if [ -z "$ARTIFACT_PATH" ]; then
    ARTIFACT_PATH="${MCA_ARTIFACTS_DIR}/${SERVICE}/${VERSION}"
    mkdir -p "$ARTIFACT_PATH"
    log_verbose "Output path not provided, using: $ARTIFACT_PATH"
  fi
  
  # Prepare artifact key
  local artifact_key=""
  local metadata_key=""
  
  # If artifact file name is not known, try to get it from metadata
  if [[ "$ARTIFACT_PATH" == */ ]]; then
    log_verbose "Artifact path is a directory, will try to get artifact name from metadata"
    
    # Get metadata first
    metadata_key="metadata/${SERVICE}/${VERSION}/${SERVICE}-${VERSION}.json"
    local metadata_file="${ARTIFACT_PATH}/${SERVICE}-${VERSION}.json"
    
    case "$REPOSITORY_TYPE" in
      "s3")
        log_verbose "Downloading metadata from S3: $REPOSITORY_URL/$metadata_key"
        local s3_cmd="aws s3 cp s3://\"$REPOSITORY_URL/$metadata_key\" \"$metadata_file\""
        if [ "$VERBOSE" = true ]; then
          s3_cmd="$s3_cmd --debug"
        fi
        
        if ! retry "$s3_cmd" "Download metadata from S3"; then
          log "ERROR" "Failed to download metadata from S3"
          return 1
        fi
        ;;
        
      "nexus")
        log_verbose "Downloading metadata from Nexus: $REPOSITORY_URL/$metadata_key"
        local nexus_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X GET \"$REPOSITORY_URL/$metadata_key\" -o \"$metadata_file\""
        if [ "$VERBOSE" = true ]; then
          nexus_cmd="$nexus_cmd -v"
        else
          nexus_cmd="$nexus_cmd -s"
        fi
        
        if ! retry "$nexus_cmd" "Download metadata from Nexus"; then
          log "ERROR" "Failed to download metadata from Nexus"
          return 1
        fi
        ;;
        
      "artifactory")
        log_verbose "Downloading metadata from Artifactory: $REPOSITORY_URL/$metadata_key"
        local artifactory_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X GET \"$REPOSITORY_URL/$metadata_key\" -o \"$metadata_file\""
        if [ "$VERBOSE" = true ]; then
          artifactory_cmd="$artifactory_cmd -v"
        else
          artifactory_cmd="$artifactory_cmd -s"
        fi
        
        if ! retry "$artifactory_cmd" "Download metadata from Artifactory"; then
          log "ERROR" "Failed to download metadata from Artifactory"
          return 1
        fi
        ;;
    esac
    
    # Extract artifact name from metadata
    if [ -f "$metadata_file" ]; then
      local artifact_name=$(jq -r '.artifact_name' "$metadata_file")
      if [ -n "$artifact_name" ] && [ "$artifact_name" != "null" ]; then
        artifact_key="${SERVICE}/${VERSION}/${artifact_name}"
        ARTIFACT_PATH="${ARTIFACT_PATH}/${artifact_name}"
        log_verbose "Extracted artifact name from metadata: $artifact_name"
      else
        log "ERROR" "Failed to extract artifact name from metadata"
        return 1
      fi
    else
      log "ERROR" "Metadata file not found: $metadata_file"
      return 1
    fi
  else
    # Artifact file name is provided in the path
    local artifact_name=$(basename "$ARTIFACT_PATH")
    artifact_key="${SERVICE}/${VERSION}/${artifact_name}"
    metadata_key="metadata/${SERVICE}/${VERSION}/${SERVICE}-${VERSION}.json"
    log_verbose "Using provided artifact name: $artifact_name"
  fi
  
  # Create directory if it doesn't exist
  mkdir -p "$(dirname "$ARTIFACT_PATH")"
  
  # Download artifact based on repository type
  case "$REPOSITORY_TYPE" in
    "s3")
      log "INFO" "Downloading artifact from S3: $REPOSITORY_URL/$artifact_key"
      local s3_cmd="aws s3 cp s3://\"$REPOSITORY_URL/$artifact_key\" \"$ARTIFACT_PATH\""
      if [ "$VERBOSE" = true ]; then
        s3_cmd="$s3_cmd --debug"
      fi
      
      if ! retry "$s3_cmd" "Download artifact from S3"; then
        log "ERROR" "Failed to download artifact from S3"
        return 1
      fi
      ;;
      
    "nexus")
      log "INFO" "Downloading artifact from Nexus: $REPOSITORY_URL/$artifact_key"
      local nexus_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X GET \"$REPOSITORY_URL/$artifact_key\" -o \"$ARTIFACT_PATH\""
      if [ "$VERBOSE" = true ]; then
        nexus_cmd="$nexus_cmd -v"
      else
        nexus_cmd="$nexus_cmd -s"
      fi
      
      if ! retry "$nexus_cmd" "Download artifact from Nexus"; then
        log "ERROR" "Failed to download artifact from Nexus"
        return 1
      fi
      ;;
      
    "artifactory")
      log "INFO" "Downloading artifact from Artifactory: $REPOSITORY_URL/$artifact_key"
      local artifactory_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X GET \"$REPOSITORY_URL/$artifact_key\" -o \"$ARTIFACT_PATH\""
      if [ "$VERBOSE" = true ]; then
        artifactory_cmd="$artifactory_cmd -v"
      else
        artifactory_cmd="$artifactory_cmd -s"
      fi
      
      if ! retry "$artifactory_cmd" "Download artifact from Artifactory"; then
        log "ERROR" "Failed to download artifact from Artifactory"
        return 1
      fi
      ;;
  esac
  
  log "SUCCESS" "Artifact retrieved successfully: $ARTIFACT_PATH"
  return 0
}

# Function to verify artifact integrity
verify_artifact() {
  log "INFO" "Verifying artifact integrity: $ARTIFACT_PATH"
  
  # Validate artifact path
  if [ ! -f "$ARTIFACT_PATH" ]; then
    log "ERROR" "Artifact file not found: $ARTIFACT_PATH"
    return 1
  fi
  
  # If version is not provided, try to extract it from the path
  if [ -z "$VERSION" ]; then
    local path_parts=(${ARTIFACT_PATH//\// })
    for ((i=0; i<${#path_parts[@]}; i++)); do
      if [[ "${path_parts[i]}" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]]; then
        VERSION="${path_parts[i]}"
        log_verbose "Extracted version from path: $VERSION"
        break
      fi
    done
    
    if [ -z "$VERSION" ]; then
      log "ERROR" "Could not determine version, please provide it with --version"
      return 1
    fi
  fi
  
  # Determine repository URL and credentials
  determine_repository_url
  determine_repository_credentials
  
  # Get metadata
  local metadata_key="metadata/${SERVICE}/${VERSION}/${SERVICE}-${VERSION}.json"
  local metadata_file="${MCA_ARTIFACTS_DIR}/metadata/${SERVICE}/${ENVIRONMENT}/${SERVICE}-${VERSION}.json"
  mkdir -p "$(dirname "$metadata_file")"
  
  # Download metadata if not already available locally
  if [ ! -f "$metadata_file" ]; then
    log_verbose "Metadata not found locally, downloading from repository"
    
    case "$REPOSITORY_TYPE" in
      "s3")
        log_verbose "Downloading metadata from S3: $REPOSITORY_URL/$metadata_key"
        local s3_cmd="aws s3 cp s3://\"$REPOSITORY_URL/$metadata_key\" \"$metadata_file\""
        if [ "$VERBOSE" = true ]; then
          s3_cmd="$s3_cmd --debug"
        fi
        
        if ! retry "$s3_cmd" "Download metadata from S3"; then
          log "ERROR" "Failed to download metadata from S3"
          return 1
        fi
        ;;
        
      "nexus")
        log_verbose "Downloading metadata from Nexus: $REPOSITORY_URL/$metadata_key"
        local nexus_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X GET \"$REPOSITORY_URL/$metadata_key\" -o \"$metadata_file\""
        if [ "$VERBOSE" = true ]; then
          nexus_cmd="$nexus_cmd -v"
        else
          nexus_cmd="$nexus_cmd -s"
        fi
        
        if ! retry "$nexus_cmd" "Download metadata from Nexus"; then
          log "ERROR" "Failed to download metadata from Nexus"
          return 1
        fi
        ;;
        
      "artifactory")
        log_verbose "Downloading metadata from Artifactory: $REPOSITORY_URL/$metadata_key"
        local artifactory_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X GET \"$REPOSITORY_URL/$metadata_key\" -o \"$metadata_file\""
        if [ "$VERBOSE" = true ]; then
          artifactory_cmd="$artifactory_cmd -v"
        else
          artifactory_cmd="$artifactory_cmd -s"
        fi
        
        if ! retry "$artifactory_cmd" "Download metadata from Artifactory"; then
          log "ERROR" "Failed to download metadata from Artifactory"
          return 1
        fi
        ;;
    esac
  fi
  
  # Verify metadata exists
  if [ ! -f "$metadata_file" ]; then
    log "ERROR" "Metadata file not found: $metadata_file"
    return 1
  fi
  
  # Extract checksum algorithm and expected checksum from metadata
  local expected_checksum=$(jq -r '.checksum' "$metadata_file")
  local checksum_algorithm=$(jq -r '.checksum_algorithm' "$metadata_file")
  
  if [ -z "$expected_checksum" ] || [ "$expected_checksum" = "null" ]; then
    log "ERROR" "Checksum not found in metadata"
    return 1
  fi
  
  if [ -z "$checksum_algorithm" ] || [ "$checksum_algorithm" = "null" ]; then
    log "WARN" "Checksum algorithm not found in metadata, using sha256"
    checksum_algorithm="sha256"
  fi
  
  # Calculate actual checksum
  local actual_checksum=""
  case "$checksum_algorithm" in
    "md5")
      actual_checksum=$(md5sum "$ARTIFACT_PATH" | awk '{print $1}')
      ;;
    "sha1")
      actual_checksum=$(sha1sum "$ARTIFACT_PATH" | awk '{print $1}')
      ;;
    "sha256")
      actual_checksum=$(sha256sum "$ARTIFACT_PATH" | awk '{print $1}')
      ;;
    "sha512")
      actual_checksum=$(sha512sum "$ARTIFACT_PATH" | awk '{print $1}')
      ;;
    *)
      log "WARN" "Unsupported checksum algorithm: $checksum_algorithm, using sha256"
      actual_checksum=$(sha256sum "$ARTIFACT_PATH" | awk '{print $1}')
      ;;
  esac
  
  # Compare checksums
  if [ "$actual_checksum" = "$expected_checksum" ]; then
    log "SUCCESS" "Artifact integrity verified: checksums match"
    return 0
  else
    log "ERROR" "Artifact integrity verification failed: checksums do not match"
    log "ERROR" "Expected: $expected_checksum"
    log "ERROR" "Actual: $actual_checksum"
    return 1
  fi
}

# Function to clean up old artifacts
cleanup_artifacts() {
  log "INFO" "Cleaning up old artifacts for $SERVICE in $ENVIRONMENT environment"
  
  # Determine repository URL and credentials
  determine_repository_url
  determine_repository_credentials
  
  # Calculate cutoff date
  local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +"%Y-%m-%d")
  log_verbose "Retention policy: $RETENTION_DAYS days (cutoff date: $cutoff_date)"
  
  # List artifacts based on repository type
  case "$REPOSITORY_TYPE" in
    "s3")
      log "INFO" "Listing artifacts in S3: $REPOSITORY_URL/$SERVICE/"
      
      # List all artifacts for the service
      local s3_cmd="aws s3 ls s3://\"$REPOSITORY_URL/$SERVICE/\" --recursive"
      local artifacts=$(eval "$s3_cmd")
      
      if [ -z "$artifacts" ]; then
        log "INFO" "No artifacts found for $SERVICE"
        return 0
      fi
      
      # Process each artifact
      local deleted_count=0
      while read -r line; do
        # Extract date and key from the listing
        local date_str=$(echo "$line" | awk '{print $1}')
        local artifact_key=$(echo "$line" | awk '{$1=""; $2=""; $3=""; $4=""; print $0}' | sed 's/^[ \t]*//')
        
        # Skip metadata files for now (we'll delete them after the main artifacts)
        if [[ "$artifact_key" == metadata/* ]]; then
          continue
        fi
        
        # Check if the artifact is older than the cutoff date
        if [[ "$date_str" < "$cutoff_date" ]]; then
          # Check if this is a release version that should be kept
          if [[ "$artifact_key" =~ /[0-9]+\.[0-9]+\.[0-9]+/ ]] && ! [[ "$artifact_key" =~ -SNAPSHOT/ ]]; then
            # This is a release version, check if it has a keep tag
            local tags_cmd="aws s3api get-object-tagging --bucket \"$REPOSITORY_URL\" --key \"$artifact_key\""
            local tags_output=$(eval "$tags_cmd" 2>/dev/null)
            
            if echo "$tags_output" | grep -q '"Key": "keep"'; then
              log_verbose "Keeping release artifact with 'keep' tag: $artifact_key"
              continue
            fi
          fi
          
          # Delete the artifact
          log "INFO" "Deleting old artifact: $artifact_key (from $date_str)"
          local delete_cmd="aws s3 rm s3://\"$REPOSITORY_URL/$artifact_key\""
          
          if retry "$delete_cmd" "Delete artifact from S3"; then
            ((deleted_count++))
            
            # Also delete the corresponding metadata
            local version=$(echo "$artifact_key" | grep -oP "$SERVICE/\K[^/]+")
            local metadata_key="metadata/$SERVICE/$version/${SERVICE}-${version}.json"
            local metadata_delete_cmd="aws s3 rm s3://\"$REPOSITORY_URL/$metadata_key\""
            
            retry "$metadata_delete_cmd" "Delete metadata from S3"
          fi
        fi
      done <<< "$artifacts"
      
      log "SUCCESS" "Cleanup completed: deleted $deleted_count artifacts"
      ;;
      
    "nexus")
      log "INFO" "Cleaning up artifacts in Nexus is handled by Nexus repository policies"
      log "INFO" "Please configure cleanup policies in the Nexus repository manager"
      ;;
      
    "artifactory")
      log "INFO" "Cleaning up artifacts in Artifactory is handled by Artifactory retention policies"
      log "INFO" "Please configure retention policies in the Artifactory repository manager"
      ;;
  esac
  
  return 0
}

# Function to index artifact metadata for searching
index_artifacts() {
  log "INFO" "Indexing artifact metadata for $SERVICE in $ENVIRONMENT environment"
  
  # Determine repository URL and credentials
  determine_repository_url
  determine_repository_credentials
  
  # Create index directory
  local index_dir="${MCA_ARTIFACTS_DIR}/index/${SERVICE}/${ENVIRONMENT}"
  mkdir -p "$index_dir"
  
  # Create or update index file
  local index_file="${index_dir}/artifacts.json"
  
  # Initialize index file if it doesn't exist
  if [ ! -f "$index_file" ]; then
    echo "[]" > "$index_file"
  fi
  
  # List metadata files based on repository type
  case "$REPOSITORY_TYPE" in
    "s3")
      log "INFO" "Listing metadata in S3: $REPOSITORY_URL/metadata/$SERVICE/"
      
      # List all metadata files for the service
      local s3_cmd="aws s3 ls s3://\"$REPOSITORY_URL/metadata/$SERVICE/\" --recursive"
      local metadata_files=$(eval "$s3_cmd")
      
      if [ -z "$metadata_files" ]; then
        log "INFO" "No metadata found for $SERVICE"
        return 0
      fi
      
      # Process each metadata file
      local temp_dir=$(mktemp -d)
      local indexed_count=0
      
      while read -r line; do
        # Extract key from the listing
        local metadata_key=$(echo "$line" | awk '{$1=""; $2=""; $3=""; $4=""; print $0}' | sed 's/^[ \t]*//')
        
        # Download metadata file
        local temp_file="${temp_dir}/$(basename "$metadata_key")"
        local download_cmd="aws s3 cp s3://\"$REPOSITORY_URL/$metadata_key\" \"$temp_file\""
        
        if retry "$download_cmd" "Download metadata from S3"; then
          # Add to index
          local metadata_content=$(cat "$temp_file")
          local current_index=$(cat "$index_file")
          
          # Extract version from metadata
          local version=$(jq -r '.version' "$temp_file")
          
          # Check if this version is already in the index
          if ! echo "$current_index" | jq -e ".[] | select(.version == \"$version\")" > /dev/null; then
            # Add to index
            echo "$current_index" | jq '. += ['$metadata_content']' > "$index_file"
            ((indexed_count++))
          fi
        fi
      done <<< "$metadata_files"
      
      # Clean up temp directory
      rm -rf "$temp_dir"
      
      log "SUCCESS" "Indexing completed: indexed $indexed_count artifacts"
      ;;
      
    "nexus")
      log "INFO" "Indexing Nexus artifacts"
      
      # Get list of artifacts using Nexus REST API
      local nexus_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X GET \"$REPOSITORY_URL/service/rest/v1/components?repository=mca-${ENVIRONMENT}&group=$SERVICE\""
      local nexus_response=$(eval "$nexus_cmd")
      
      if [ -z "$nexus_response" ]; then
        log "INFO" "No artifacts found in Nexus for $SERVICE"
        return 0
      fi
      
      # Process each artifact
      local items=$(echo "$nexus_response" | jq -r '.items')
      local indexed_count=0
      
      if [ "$items" != "null" ] && [ "$items" != "[]" ]; then
        local item_count=$(echo "$items" | jq '. | length')
        
        for ((i=0; i<item_count; i++)); do
          local item=$(echo "$items" | jq -r ".[$i]")
          local version=$(echo "$item" | jq -r '.version')
          
          # Get metadata asset
          local assets=$(echo "$item" | jq -r '.assets')
          local metadata_url=""
          
          for ((j=0; j<$(echo "$assets" | jq '. | length'); j++)); do
            local asset=$(echo "$assets" | jq -r ".[$j]")
            local path=$(echo "$asset" | jq -r '.path')
            
            if [[ "$path" == *".json" ]]; then
              metadata_url=$(echo "$asset" | jq -r '.downloadUrl')
              break
            fi
          done
          
          if [ -n "$metadata_url" ]; then
            # Download metadata
            local temp_file=$(mktemp)
            local download_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X GET \"$metadata_url\" -o \"$temp_file\""
            
            if retry "$download_cmd" "Download metadata from Nexus"; then
              # Add to index
              local metadata_content=$(cat "$temp_file")
              local current_index=$(cat "$index_file")
              
              # Check if this version is already in the index
              if ! echo "$current_index" | jq -e ".[] | select(.version == \"$version\")" > /dev/null; then
                # Add to index
                echo "$current_index" | jq '. += ['$metadata_content']' > "$index_file"
                ((indexed_count++))
              fi
              
              rm -f "$temp_file"
            fi
          fi
        done
      fi
      
      log "SUCCESS" "Indexing completed: indexed $indexed_count artifacts"
      ;;
      
    "artifactory")
      log "INFO" "Indexing Artifactory artifacts"
      
      # Get list of artifacts using Artifactory AQL
      local aql_query='{"repo":"mca-'"$ENVIRONMENT"'","path":"'"$SERVICE"'","type":"file","name":{"$match":"*.json"},"path":{"$match":"*/metadata/*"}}'      
      local artifactory_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X POST -H \"Content-Type: text/plain\" -d \"$aql_query\" \"$REPOSITORY_URL/api/search/aql\""
      local artifactory_response=$(eval "$artifactory_cmd")
      
      if [ -z "$artifactory_response" ]; then
        log "INFO" "No artifacts found in Artifactory for $SERVICE"
        return 0
      fi
      
      # Process each artifact
      local items=$(echo "$artifactory_response" | jq -r '.results')
      local indexed_count=0
      
      if [ "$items" != "null" ] && [ "$items" != "[]" ]; then
        local item_count=$(echo "$items" | jq '. | length')
        
        for ((i=0; i<item_count; i++)); do
          local item=$(echo "$items" | jq -r ".[$i]")
          local repo=$(echo "$item" | jq -r '.repo')
          local path=$(echo "$item" | jq -r '.path')
          local name=$(echo "$item" | jq -r '.name')
          
          # Download metadata
          local metadata_url="$REPOSITORY_URL/$repo/$path/$name"
          local temp_file=$(mktemp)
          local download_cmd="curl -s -u \"$REPOSITORY_USER:$REPOSITORY_TOKEN\" -X GET \"$metadata_url\" -o \"$temp_file\""
          
          if retry "$download_cmd" "Download metadata from Artifactory"; then
            # Add to index
            local metadata_content=$(cat "$temp_file")
            local current_index=$(cat "$index_file")
            local version=$(echo "$metadata_content" | jq -r '.version')
            
            # Check if this version is already in the index
            if ! echo "$current_index" | jq -e ".[] | select(.version == \"$version\")" > /dev/null; then
              # Add to index
              echo "$current_index" | jq '. += ['$metadata_content']' > "$index_file"
              ((indexed_count++))
            fi
            
            rm -f "$temp_file"
          fi
        done
      fi
      
      log "SUCCESS" "Indexing completed: indexed $indexed_count artifacts"
      ;;
  esac
  
  return 0
}

# Main function
main() {
  log "INFO" "Starting artifact handling for $SERVICE ($ACTION)"
  
  # Check required tools
  if ! check_required_tools; then
    log "ERROR" "Required tools are not available, cannot proceed"
    exit 1
  fi
  
  # Determine version if not provided
  determine_version
  
  # Determine artifact type if not provided
  determine_artifact_type
  
  # Perform the requested action
  case "$ACTION" in
    "store")
      if [ -z "$ARTIFACT_PATH" ]; then
        log "ERROR" "Artifact path is required for store action"
        exit 1
      fi
      
      if ! store_artifact; then
        log "ERROR" "Failed to store artifact"
        exit 1
      fi
      ;;
      
    "retrieve")
      if ! retrieve_artifact; then
        log "ERROR" "Failed to retrieve artifact"
        exit 1
      fi
      ;;
      
    "verify")
      if [ -z "$ARTIFACT_PATH" ]; then
        log "ERROR" "Artifact path is required for verify action"
        exit 1
      fi
      
      if ! verify_artifact; then
        log "ERROR" "Artifact verification failed"
        exit 1
      fi
      ;;
      
    "cleanup")
      if ! cleanup_artifacts; then
        log "ERROR" "Failed to clean up artifacts"
        exit 1
      fi
      ;;
      
    "index")
      if ! index_artifacts; then
        log "ERROR" "Failed to index artifacts"
        exit 1
      fi
      ;;
  esac
  
  log "SUCCESS" "Artifact handling completed successfully for $SERVICE ($ACTION)"
  exit 0
}

# Run the main function
main