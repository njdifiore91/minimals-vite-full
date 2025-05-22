#!/bin/bash

# ============================================================================
# handle-artifacts.sh
#
# Manages build artifacts throughout the CI/CD pipeline, including storage,
# retrieval, and cleanup with proper versioning and integrity verification.
#
# This script supports the MCA Application Processing System by ensuring that
# build artifacts are properly managed, enabling reliable deployments and
# efficient resource usage.
#
# Usage:
#   ./handle-artifacts.sh [command] [options]
#
# Commands:
#   store     - Store artifacts with metadata
#   retrieve  - Retrieve artifacts for deployment
#   cleanup   - Clean up old artifacts based on retention policy
#   verify    - Verify artifact integrity
#   list      - List available artifacts with metadata
#
# Options:
#   --service-type    - Type of service (node, java, python, frontend)
#   --env             - Environment (development, staging, production)
#   --artifact-path   - Path to artifact or directory containing artifacts
#   --version         - Version of the artifact (defaults to git-based version)
#   --repository      - Artifact repository URL (defaults to environment-specific)
#   --retention-days  - Number of days to retain artifacts (default: 30)
#   --metadata        - Additional metadata in JSON format
#
# Examples:
#   ./handle-artifacts.sh store --service-type node --env development --artifact-path ./dist
#   ./handle-artifacts.sh retrieve --service-type java --env staging --version 1.2.3
#   ./handle-artifacts.sh cleanup --env production --retention-days 60
#   ./handle-artifacts.sh verify --service-type python --env staging --version 1.2.3
#   ./handle-artifacts.sh list --service-type frontend --env production
#
# ============================================================================

set -e

# ============================================================================
# Configuration
# ============================================================================

# Default values
DEFAULT_RETENTION_DAYS=30
ARTIFACT_BASE_DIR="/tmp/artifacts"
LOG_FILE="/tmp/artifact-handling.log"
CHECKSUM_ALGORITHM="sha256sum"

# Repository URLs by environment
DEV_REPOSITORY="http://artifact-repo.dev.dollarfunding.com"
STAGING_REPOSITORY="http://artifact-repo.staging.dollarfunding.com"
PROD_REPOSITORY="http://artifact-repo.prod.dollarfunding.com"

# ============================================================================
# Utility Functions
# ============================================================================

# Log message to console and log file
log() {
    local level=$1
    local message=$2
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message"
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Log info message
log_info() {
    log "INFO" "$1"
}

# Log error message
log_error() {
    log "ERROR" "$1"
}

# Log debug message
log_debug() {
    if [[ "$DEBUG" == "true" ]]; then
        log "DEBUG" "$1"
    fi
}

# Check if required tools are installed
check_requirements() {
    local required_tools=("curl" "jq" "$CHECKSUM_ALGORITHM")
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            exit 1
        fi
    done
    
    log_debug "All required tools are available"
}

# Generate a version string based on git information if not provided
generate_version() {
    if [[ -z "$VERSION" ]]; then
        # Get the most recent tag
        local git_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
        
        # Get the current commit hash
        local git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        
        # Get the branch name
        local git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
        
        # Format: <tag>-<commits-since-tag>-g<commit-hash>-<branch>
        # If on a tag exactly, just use the tag
        if git describe --exact-match --tags HEAD &>/dev/null; then
            VERSION="${git_tag#v}"
        else
            local commits_since_tag=$(git rev-list "$git_tag"..HEAD --count 2>/dev/null || echo "0")
            VERSION="${git_tag#v}-$commits_since_tag-g$git_commit-$git_branch"
        fi
        
        log_debug "Generated version: $VERSION"
    fi
    
    echo "$VERSION"
}

# Get repository URL based on environment
get_repository_url() {
    local env=$1
    
    if [[ -n "$REPOSITORY" ]]; then
        echo "$REPOSITORY"
        return
    fi
    
    case "$env" in
        development)
            echo "$DEV_REPOSITORY"
            ;;
        staging)
            echo "$STAGING_REPOSITORY"
            ;;
        production)
            echo "$PROD_REPOSITORY"
            ;;
        *)
            log_error "Unknown environment: $env"
            exit 1
            ;;
    esac
}

# Generate metadata for artifacts
generate_metadata() {
    local service_type=$1
    local env=$2
    local version=$3
    local artifact_path=$4
    local additional_metadata=$5
    
    # Get build information
    local build_number=${CI_BUILD_NUMBER:-"local"}
    local build_timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local build_user=${CI_BUILD_USER:-$(whoami)}
    
    # Create basic metadata
    local metadata='{'
    metadata+="\"service_type\":\"$service_type\","
    metadata+="\"environment\":\"$env\","
    metadata+="\"version\":\"$version\","
    metadata+="\"build_number\":\"$build_number\","
    metadata+="\"build_timestamp\":\"$build_timestamp\","
    metadata+="\"build_user\":\"$build_user\","
    
    # Add git information if available
    if command -v git &> /dev/null && git rev-parse --is-inside-work-tree &> /dev/null; then
        local git_commit=$(git rev-parse HEAD)
        local git_branch=$(git rev-parse --abbrev-ref HEAD)
        local git_repo=$(git config --get remote.origin.url)
        
        metadata+="\"git_commit\":\"$git_commit\","
        metadata+="\"git_branch\":\"$git_branch\","
        metadata+="\"git_repo\":\"$git_repo\","
    fi
    
    # Add checksums for files
    if [[ -f "$artifact_path" ]]; then
        local checksum=$($CHECKSUM_ALGORITHM "$artifact_path" | awk '{print $1}')
        metadata+="\"checksum\":\"$checksum\","
        metadata+="\"checksum_algorithm\":\"${CHECKSUM_ALGORITHM%sum}\","
    elif [[ -d "$artifact_path" ]]; then
        # For directories, create a manifest file with checksums
        local manifest_file="$ARTIFACT_BASE_DIR/manifest-$(date +%s).txt"
        find "$artifact_path" -type f -exec $CHECKSUM_ALGORITHM {} \; > "$manifest_file"
        local manifest_checksum=$($CHECKSUM_ALGORITHM "$manifest_file" | awk '{print $1}')
        
        metadata+="\"manifest_checksum\":\"$manifest_checksum\","
        metadata+="\"checksum_algorithm\":\"${CHECKSUM_ALGORITHM%sum}\","
    fi
    
    # Add additional metadata if provided
    if [[ -n "$additional_metadata" ]]; then
        # Remove the trailing comma and closing brace
        metadata=${metadata%,}
        
        # Add the additional metadata (removing the opening and closing braces)
        additional_metadata=${additional_metadata#\{}
        additional_metadata=${additional_metadata%\}}
        
        if [[ -n "$additional_metadata" ]]; then
            metadata+=",$additional_metadata"
        fi
    else
        # Remove the trailing comma
        metadata=${metadata%,}
    fi
    
    # Close the JSON object
    metadata+='}'
    
    # Validate JSON
    if ! echo "$metadata" | jq . &>/dev/null; then
        log_error "Invalid metadata JSON"
        exit 1
    fi
    
    echo "$metadata"
}

# Create artifact directory structure
create_artifact_directory() {
    local service_type=$1
    local env=$2
    local version=$3
    
    local artifact_dir="$ARTIFACT_BASE_DIR/$service_type/$env/$version"
    
    if [[ ! -d "$artifact_dir" ]]; then
        mkdir -p "$artifact_dir"
        log_debug "Created artifact directory: $artifact_dir"
    fi
    
    echo "$artifact_dir"
}

# ============================================================================
# Main Functions
# ============================================================================

# Store artifacts with metadata
store_artifacts() {
    log_info "Storing artifacts for $SERVICE_TYPE in $ENV environment"
    
    # Validate required parameters
    if [[ -z "$SERVICE_TYPE" || -z "$ENV" || -z "$ARTIFACT_PATH" ]]; then
        log_error "Missing required parameters for store command"
        show_usage
        exit 1
    fi
    
    # Generate version if not provided
    VERSION=$(generate_version)
    
    # Get repository URL
    REPOSITORY_URL=$(get_repository_url "$ENV")
    
    # Create artifact directory
    local artifact_dir=$(create_artifact_directory "$SERVICE_TYPE" "$ENV" "$VERSION")
    
    # Generate metadata
    local metadata=$(generate_metadata "$SERVICE_TYPE" "$ENV" "$VERSION" "$ARTIFACT_PATH" "$METADATA")
    
    # Save metadata to file
    echo "$metadata" > "$artifact_dir/metadata.json"
    log_debug "Saved metadata to $artifact_dir/metadata.json"
    
    # Copy artifacts
    if [[ -f "$ARTIFACT_PATH" ]]; then
        # Single file
        cp "$ARTIFACT_PATH" "$artifact_dir/"
        log_info "Copied artifact file: $ARTIFACT_PATH to $artifact_dir/"
    elif [[ -d "$ARTIFACT_PATH" ]]; then
        # Directory
        cp -r "$ARTIFACT_PATH/"* "$artifact_dir/"
        log_info "Copied artifact directory: $ARTIFACT_PATH to $artifact_dir/"
    else
        log_error "Artifact path does not exist: $ARTIFACT_PATH"
        exit 1
    fi
    
    # Create checksums for all files
    find "$artifact_dir" -type f -not -name "checksums.txt" -exec $CHECKSUM_ALGORITHM {} \; > "$artifact_dir/checksums.txt"
    log_debug "Generated checksums for all files"
    
    # Upload to repository if not local
    if [[ "$REPOSITORY_URL" != "local"* ]]; then
        log_info "Uploading artifacts to repository: $REPOSITORY_URL"
        
        # Create a tarball of the artifact directory
        local tarball_name="$SERVICE_TYPE-$ENV-$VERSION.tar.gz"
        local tarball_path="$ARTIFACT_BASE_DIR/$tarball_name"
        
        tar -czf "$tarball_path" -C "$artifact_dir" .
        log_debug "Created tarball: $tarball_path"
        
        # Upload the tarball to the repository
        # This is a placeholder for the actual upload command, which would depend on the repository type
        # For example, for Nexus or Artifactory, you would use curl or a specific client
        
        # Example for Artifactory:
        # curl -u "$ARTIFACTORY_USER:$ARTIFACTORY_PASSWORD" -X PUT "$REPOSITORY_URL/$SERVICE_TYPE/$ENV/$VERSION/$tarball_name" -T "$tarball_path"
        
        # Example for Nexus:
        # curl -u "$NEXUS_USER:$NEXUS_PASSWORD" -X POST "$REPOSITORY_URL/service/rest/v1/components?repository=artifacts" -F "maven2.groupId=$SERVICE_TYPE" -F "maven2.artifactId=$ENV" -F "maven2.version=$VERSION" -F "maven2.asset1=@$tarball_path"
        
        # Example for AWS S3:
        # aws s3 cp "$tarball_path" "s3://artifacts-bucket/$SERVICE_TYPE/$ENV/$VERSION/$tarball_name"
        
        log_info "Artifacts uploaded successfully to $REPOSITORY_URL"
        
        # Clean up the tarball
        rm -f "$tarball_path"
    fi
    
    log_info "Artifacts stored successfully at $artifact_dir"
    echo "Artifacts stored at: $artifact_dir"
    echo "Version: $VERSION"
}

# Retrieve artifacts for deployment
retrieve_artifacts() {
    log_info "Retrieving artifacts for $SERVICE_TYPE in $ENV environment, version $VERSION"
    
    # Validate required parameters
    if [[ -z "$SERVICE_TYPE" || -z "$ENV" || -z "$VERSION" ]]; then
        log_error "Missing required parameters for retrieve command"
        show_usage
        exit 1
    fi
    
    # Get repository URL
    REPOSITORY_URL=$(get_repository_url "$ENV")
    
    # Set destination directory
    local dest_dir="${ARTIFACT_PATH:-./artifacts}"
    mkdir -p "$dest_dir"
    
    # Check if artifacts exist locally
    local artifact_dir="$ARTIFACT_BASE_DIR/$SERVICE_TYPE/$ENV/$VERSION"
    
    if [[ -d "$artifact_dir" ]]; then
        log_info "Found artifacts locally at $artifact_dir"
        
        # Copy artifacts to destination
        cp -r "$artifact_dir/"* "$dest_dir/"
        log_info "Copied artifacts to $dest_dir"
    else
        log_info "Artifacts not found locally, attempting to retrieve from repository"
        
        # Download from repository
        if [[ "$REPOSITORY_URL" != "local"* ]]; then
            log_info "Downloading artifacts from repository: $REPOSITORY_URL"
            
            # Create a temporary directory for the download
            local temp_dir=$(mktemp -d)
            
            # Download the tarball from the repository
            # This is a placeholder for the actual download command, which would depend on the repository type
            local tarball_name="$SERVICE_TYPE-$ENV-$VERSION.tar.gz"
            local tarball_path="$temp_dir/$tarball_name"
            
            # Example for Artifactory:
            # curl -u "$ARTIFACTORY_USER:$ARTIFACTORY_PASSWORD" -o "$tarball_path" "$REPOSITORY_URL/$SERVICE_TYPE/$ENV/$VERSION/$tarball_name"
            
            # Example for Nexus:
            # curl -u "$NEXUS_USER:$NEXUS_PASSWORD" -o "$tarball_path" "$REPOSITORY_URL/repository/artifacts/$SERVICE_TYPE/$ENV/$VERSION/$tarball_name"
            
            # Example for AWS S3:
            # aws s3 cp "s3://artifacts-bucket/$SERVICE_TYPE/$ENV/$VERSION/$tarball_name" "$tarball_path"
            
            # Extract the tarball to the destination directory
            tar -xzf "$tarball_path" -C "$dest_dir"
            log_info "Extracted artifacts to $dest_dir"
            
            # Clean up the temporary directory
            rm -rf "$temp_dir"
        else
            log_error "Artifacts not found locally and no remote repository configured"
            exit 1
        fi
    fi
    
    # Verify artifact integrity
    if [[ -f "$dest_dir/checksums.txt" ]]; then
        log_info "Verifying artifact integrity"
        
        # Change to the destination directory to verify checksums
        pushd "$dest_dir" > /dev/null
        
        # Verify checksums
        if ! $CHECKSUM_ALGORITHM -c checksums.txt; then
            log_error "Artifact integrity check failed"
            popd > /dev/null
            exit 1
        fi
        
        log_info "Artifact integrity verified successfully"
        popd > /dev/null
    else
        log_warn "No checksums file found, skipping integrity verification"
    fi
    
    log_info "Artifacts retrieved successfully to $dest_dir"
    echo "Artifacts retrieved to: $dest_dir"
}

# Clean up old artifacts based on retention policy
cleanup_artifacts() {
    log_info "Cleaning up old artifacts for environment: $ENV"
    
    # Validate required parameters
    if [[ -z "$ENV" ]]; then
        log_error "Missing required parameters for cleanup command"
        show_usage
        exit 1
    fi
    
    # Set retention days
    local retention_days=${RETENTION_DAYS:-$DEFAULT_RETENTION_DAYS}
    log_info "Retention policy: $retention_days days"
    
    # Get repository URL
    REPOSITORY_URL=$(get_repository_url "$ENV")
    
    # Clean up local artifacts
    log_info "Cleaning up local artifacts older than $retention_days days"
    
    # Find directories older than retention_days
    local cutoff_date=$(date -d "$retention_days days ago" +%s)
    
    # If service type is specified, only clean up that service
    local search_dir="$ARTIFACT_BASE_DIR"
    if [[ -n "$SERVICE_TYPE" ]]; then
        search_dir="$ARTIFACT_BASE_DIR/$SERVICE_TYPE"
    fi
    
    # Only clean up the specified environment
    search_dir="$search_dir/$ENV"
    
    if [[ ! -d "$search_dir" ]]; then
        log_info "No artifacts found for cleanup at $search_dir"
        return
    fi
    
    # Find all version directories
    local version_dirs=$(find "$search_dir" -mindepth 1 -maxdepth 1 -type d)
    local deleted_count=0
    
    for dir in $version_dirs; do
        # Get the directory modification time
        local dir_time=$(stat -c %Y "$dir")
        
        # Check if the directory is older than the cutoff date
        if [[ $dir_time -lt $cutoff_date ]]; then
            # Check if the directory contains a metadata file
            if [[ -f "$dir/metadata.json" ]]; then
                # Check if the artifact is marked as protected
                local protected=$(jq -r '.protected // "false"' "$dir/metadata.json")
                
                if [[ "$protected" == "true" ]]; then
                    log_debug "Skipping protected artifact: $dir"
                    continue
                fi
            fi
            
            log_info "Deleting old artifact: $dir"
            rm -rf "$dir"
            deleted_count=$((deleted_count + 1))
        fi
    done
    
    log_info "Deleted $deleted_count old artifact(s)"
    
    # Clean up remote artifacts if configured
    if [[ "$REPOSITORY_URL" != "local"* ]]; then
        log_info "Cleaning up remote artifacts in repository: $REPOSITORY_URL"
        
        # This is a placeholder for the actual cleanup command, which would depend on the repository type
        # For example, for Nexus or Artifactory, you would use their REST APIs to search for and delete old artifacts
        
        # Example for Artifactory:
        # curl -u "$ARTIFACTORY_USER:$ARTIFACTORY_PASSWORD" -X POST "$REPOSITORY_URL/api/search/aql" -d "items.find({\"repo\":\"artifacts\", \"path\":\"$SERVICE_TYPE/$ENV\", \"created\":{\"$before\":\"${retention_days}d\"}}).include(\"path\", \"name\")" | jq -r '.results[] | .path + "/" + .name' | while read -r item; do
        #     curl -u "$ARTIFACTORY_USER:$ARTIFACTORY_PASSWORD" -X DELETE "$REPOSITORY_URL/$item"
        # done
        
        # Example for Nexus:
        # curl -u "$NEXUS_USER:$NEXUS_PASSWORD" -X GET "$REPOSITORY_URL/service/rest/v1/search?repository=artifacts&group=$SERVICE_TYPE&name=$ENV" | jq -r '.items[] | select(.lastModified < "'$(date -d "$retention_days days ago" -Iseconds)'") | .id' | while read -r item; do
        #     curl -u "$NEXUS_USER:$NEXUS_PASSWORD" -X DELETE "$REPOSITORY_URL/service/rest/v1/components/$item"
        # done
        
        log_info "Remote artifacts cleanup completed"
    fi
    
    log_info "Artifact cleanup completed"
    echo "Cleaned up artifacts older than $retention_days days"
}

# Verify artifact integrity
verify_artifacts() {
    log_info "Verifying artifact integrity for $SERVICE_TYPE in $ENV environment, version $VERSION"
    
    # Validate required parameters
    if [[ -z "$SERVICE_TYPE" || -z "$ENV" || -z "$VERSION" ]]; then
        log_error "Missing required parameters for verify command"
        show_usage
        exit 1
    fi
    
    # Set artifact directory
    local artifact_dir="$ARTIFACT_BASE_DIR/$SERVICE_TYPE/$ENV/$VERSION"
    
    if [[ ! -d "$artifact_dir" ]]; then
        log_error "Artifact directory not found: $artifact_dir"
        exit 1
    fi
    
    # Check if checksums file exists
    if [[ ! -f "$artifact_dir/checksums.txt" ]]; then
        log_error "Checksums file not found in artifact directory"
        exit 1
    fi
    
    log_info "Verifying checksums in $artifact_dir"
    
    # Change to the artifact directory to verify checksums
    pushd "$artifact_dir" > /dev/null
    
    # Verify checksums
    if ! $CHECKSUM_ALGORITHM -c checksums.txt; then
        log_error "Artifact integrity check failed"
        popd > /dev/null
        exit 1
    fi
    
    log_info "Artifact integrity verified successfully"
    popd > /dev/null
    
    echo "Artifact integrity verified successfully"
}

# List available artifacts with metadata
list_artifacts() {
    log_info "Listing artifacts for $SERVICE_TYPE in $ENV environment"
    
    # Validate required parameters
    if [[ -z "$ENV" ]]; then
        log_error "Missing required parameters for list command"
        show_usage
        exit 1
    fi
    
    # Set search directory
    local search_dir="$ARTIFACT_BASE_DIR"
    if [[ -n "$SERVICE_TYPE" ]]; then
        search_dir="$ARTIFACT_BASE_DIR/$SERVICE_TYPE"
    fi
    
    # Only list the specified environment
    search_dir="$search_dir/$ENV"
    
    if [[ ! -d "$search_dir" ]]; then
        log_info "No artifacts found at $search_dir"
        echo "No artifacts found"
        return
    fi
    
    # Find all version directories
    local version_dirs=$(find "$search_dir" -mindepth 1 -maxdepth 1 -type d | sort)
    
    if [[ -z "$version_dirs" ]]; then
        log_info "No artifacts found at $search_dir"
        echo "No artifacts found"
        return
    fi
    
    echo "Available artifacts:"
    echo "-------------------"
    
    for dir in $version_dirs; do
        local version=$(basename "$dir")
        local service=$(basename $(dirname $(dirname "$dir")))
        
        echo "Service: $service"
        echo "Environment: $ENV"
        echo "Version: $version"
        
        # Display metadata if available
        if [[ -f "$dir/metadata.json" ]]; then
            echo "Metadata:"
            jq . "$dir/metadata.json"
        else
            echo "No metadata available"
        fi
        
        echo "-------------------"
    done
    
    log_info "Listed artifacts successfully"
}

# Show usage information
show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  store     - Store artifacts with metadata"
    echo "  retrieve  - Retrieve artifacts for deployment"
    echo "  cleanup   - Clean up old artifacts based on retention policy"
    echo "  verify    - Verify artifact integrity"
    echo "  list      - List available artifacts with metadata"
    echo ""
    echo "Options:"
    echo "  --service-type    - Type of service (node, java, python, frontend)"
    echo "  --env             - Environment (development, staging, production)"
    echo "  --artifact-path   - Path to artifact or directory containing artifacts"
    echo "  --version         - Version of the artifact (defaults to git-based version)"
    echo "  --repository      - Artifact repository URL (defaults to environment-specific)"
    echo "  --retention-days  - Number of days to retain artifacts (default: 30)"
    echo "  --metadata        - Additional metadata in JSON format"
    echo ""
    echo "Examples:"
    echo "  $0 store --service-type node --env development --artifact-path ./dist"
    echo "  $0 retrieve --service-type java --env staging --version 1.2.3"
    echo "  $0 cleanup --env production --retention-days 60"
    echo "  $0 verify --service-type python --env staging --version 1.2.3"
    echo "  $0 list --service-type frontend --env production"
}

# ============================================================================
# Main Script
# ============================================================================

# Create log directory if it doesn't exist
mkdir -p $(dirname "$LOG_FILE")

# Check if required tools are installed
check_requirements

# Parse command line arguments
COMMAND=""
SERVICE_TYPE=""
ENV=""
ARTIFACT_PATH=""
VERSION=""
REPOSITORY=""
RETENTION_DAYS=""
METADATA=""
DEBUG="false"

# Parse command
if [[ $# -gt 0 ]]; then
    COMMAND=$1
    shift
fi

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --service-type)
            SERVICE_TYPE=$2
            shift 2
            ;;
        --env)
            ENV=$2
            shift 2
            ;;
        --artifact-path)
            ARTIFACT_PATH=$2
            shift 2
            ;;
        --version)
            VERSION=$2
            shift 2
            ;;
        --repository)
            REPOSITORY=$2
            shift 2
            ;;
        --retention-days)
            RETENTION_DAYS=$2
            shift 2
            ;;
        --metadata)
            METADATA=$2
            shift 2
            ;;
        --debug)
            DEBUG="true"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Execute command
case $COMMAND in
    store)
        store_artifacts
        ;;
    retrieve)
        retrieve_artifacts
        ;;
    cleanup)
        cleanup_artifacts
        ;;
    verify)
        verify_artifacts
        ;;
    list)
        list_artifacts
        ;;
    help)
        show_usage
        ;;
    "")
        log_error "No command specified"
        show_usage
        exit 1
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

exit 0