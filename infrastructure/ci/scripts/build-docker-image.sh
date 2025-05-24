#!/bin/bash

# build-docker-image.sh
# Script to build, tag, and push Docker images for MCA Application Processing System microservices
# Supports Node.js, Java, and Python service types with appropriate build strategies
# 
# This script standardizes the Docker image building process across all microservices
# and ensures consistent image tagging for deployment tracking

set -e

# Default values
SERVICE_DIR="."
REGISTRY=""
PUSH=false
BUILD_ARGS=""
CACHE=true
ENVIRONMENT="development"
REGISTRY_USERNAME=""
REGISTRY_PASSWORD=""
PLATFORM="linux/amd64"

# Display usage information
usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -d, --directory DIR   Service directory (default: current directory)"
  echo "  -r, --registry URL    Container registry URL"
  echo "  -p, --push            Push image to registry after build"
  echo "  -e, --env ENV         Environment (development, staging, production)"
  echo "  -a, --arg KEY=VALUE   Add build argument (can be used multiple times)"
  echo "  --no-cache            Disable Docker build cache"
  echo "  --username USER       Registry username for authentication"
  echo "  --password PASS       Registry password for authentication"
  echo "  --platform PLATFORM   Build platform (e.g., linux/amd64, linux/arm64)"
  echo "  -h, --help            Display this help message"
  exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--directory)
      SERVICE_DIR="$2"
      shift 2
      ;;
    -r|--registry)
      REGISTRY="$2"
      shift 2
      ;;
    -p|--push)
      PUSH=true
      shift
      ;;
    -e|--env)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -a|--arg)
      BUILD_ARGS="$BUILD_ARGS --build-arg $2"
      shift 2
      ;;
    --no-cache)
      CACHE=false
      shift
      ;;
    --username)
      REGISTRY_USERNAME="$2"
      shift 2
      ;;
    --password)
      REGISTRY_PASSWORD="$2"
      shift 2
      ;;
    --platform)
      PLATFORM="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

# Validate service directory
if [ ! -d "$SERVICE_DIR" ]; then
  echo "Error: Service directory '$SERVICE_DIR' does not exist"
  exit 1
fi

# Change to service directory
cd "$SERVICE_DIR"

# Detect service type based on project files
detect_service_type() {
  if [ -f "package.json" ]; then
    echo "nodejs"
  elif [ -f "pom.xml" ] || [ -f "build.gradle" ]; then
    echo "java"
  elif [ -f "requirements.txt" ] || [ -f "setup.py" ]; then
    echo "python"
  else
    echo "unknown"
  fi
}

# Generate semantic version tag based on Git information
generate_version_tag() {
  local service_name=$1
  
  # Try to get the latest Git tag
  local git_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
  
  # If no Git tag exists, use 0.1.0 as the base version
  if [ -z "$git_tag" ]; then
    git_tag="0.1.0"
  fi
  
  # Remove 'v' prefix if present
  git_tag=${git_tag#v}
  
  # Get commit hash
  local commit_hash=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
  
  # Get commit count since tag for patch version
  local commit_count=$(git rev-list --count HEAD 2>/dev/null || echo "0")
  
  # Parse the semver components
  IFS='.' read -r major minor patch <<< "$git_tag"
  
  # Extract pre-release info if present
  if [[ "$patch" == *"-"* ]]; then
    IFS='-' read -r patch_num pre_release <<< "$patch"
    patch="$patch_num"
  else
    pre_release=""
  fi
  
  # Check if working directory is clean
  if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    # Working directory is dirty, add -dirty suffix
    if [ -n "$pre_release" ]; then
      echo "$major.$minor.$patch-$pre_release.$commit_count.$commit_hash.dirty"
    else
      echo "$major.$minor.$patch-$commit_count.$commit_hash.dirty"
    fi
  else
    # Working directory is clean
    if [ -n "$pre_release" ]; then
      echo "$major.$minor.$patch-$pre_release.$commit_count.$commit_hash"
    else
      echo "$major.$minor.$patch-$commit_count.$commit_hash"
    fi
  fi
}

# Get service name from directory name
SERVICE_NAME=$(basename "$(pwd)")

# Detect service type
SERVICE_TYPE=$(detect_service_type)
echo "Detected service type: $SERVICE_TYPE"

# Generate version tag
VERSION_TAG=$(generate_version_tag "$SERVICE_NAME")
echo "Generated version tag: $VERSION_TAG"

# Set image name
if [ -n "$REGISTRY" ]; then
  IMAGE_NAME="$REGISTRY/$SERVICE_NAME"
else
  IMAGE_NAME="$SERVICE_NAME"
fi

# Set cache options
if [ "$CACHE" = false ]; then
  CACHE_OPTS="--no-cache"
else
  CACHE_OPTS=""
fi

# Add environment as build arg
BUILD_ARGS="$BUILD_ARGS --build-arg ENVIRONMENT=$ENVIRONMENT"

# Add build timestamp and git commit as labels
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

LABEL_ARGS=""
LABEL_ARGS="$LABEL_ARGS --label org.opencontainers.image.created=$BUILD_TIMESTAMP"
LABEL_ARGS="$LABEL_ARGS --label org.opencontainers.image.revision=$GIT_COMMIT"
LABEL_ARGS="$LABEL_ARGS --label org.opencontainers.image.version=$VERSION_TAG"
LABEL_ARGS="$LABEL_ARGS --label org.dollarfunding.mca.environment=$ENVIRONMENT"
LABEL_ARGS="$LABEL_ARGS --label org.dollarfunding.mca.branch=$GIT_BRANCH"

# Build Docker image based on service type
build_image() {
  echo "Building Docker image for $SERVICE_NAME ($SERVICE_TYPE)..."
  
  # Check if Dockerfile exists
  if [ ! -f "Dockerfile" ]; then
    echo "Error: Dockerfile not found in $SERVICE_DIR"
    exit 1
  fi
  
  # Add service-type specific build arguments
  case "$SERVICE_TYPE" in
    nodejs)
      # Add Node.js specific build args
      BUILD_ARGS="$BUILD_ARGS --build-arg NODE_ENV=$ENVIRONMENT"
      ;;
    java)
      # Add Java specific build args
      BUILD_ARGS="$BUILD_ARGS --build-arg SPRING_PROFILES_ACTIVE=$ENVIRONMENT"
      ;;
    python)
      # Add Python specific build args
      BUILD_ARGS="$BUILD_ARGS --build-arg PYTHON_ENV=$ENVIRONMENT"
      ;;
  esac
  
  # Build the image with BuildKit enabled for better caching
  DOCKER_BUILDKIT=1 docker build \
    $CACHE_OPTS \
    $BUILD_ARGS \
    $LABEL_ARGS \
    --platform="$PLATFORM" \
    -t "$IMAGE_NAME:$VERSION_TAG" \
    -t "$IMAGE_NAME:latest" \
    .
  
  echo "Successfully built image: $IMAGE_NAME:$VERSION_TAG"
}

# Push Docker image to registry
push_image() {
  if [ "$PUSH" = true ]; then
    echo "Pushing Docker image to registry..."
    
    # Check if registry is specified
    if [ -z "$REGISTRY" ]; then
      echo "Error: Registry URL is required for pushing images"
      exit 1
    fi
    
    # Check if authentication is required
    if [ -n "$REGISTRY_USERNAME" ] && [ -n "$REGISTRY_PASSWORD" ]; then
      echo "Authenticating with container registry..."
      echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY" -u "$REGISTRY_USERNAME" --password-stdin
      
      if [ $? -ne 0 ]; then
        echo "Error: Failed to authenticate with registry"
        exit 1
      fi
    fi
    
    # Push the image with version tag
    echo "Pushing $IMAGE_NAME:$VERSION_TAG..."
    docker push "$IMAGE_NAME:$VERSION_TAG"
    
    # Push the latest tag
    echo "Pushing $IMAGE_NAME:latest..."
    docker push "$IMAGE_NAME:latest"
    
    # Push environment-specific tag if not development
    if [ "$ENVIRONMENT" != "development" ]; then
      echo "Pushing $IMAGE_NAME:$ENVIRONMENT..."
      docker tag "$IMAGE_NAME:$VERSION_TAG" "$IMAGE_NAME:$ENVIRONMENT"
      docker push "$IMAGE_NAME:$ENVIRONMENT"
    fi
    
    echo "Successfully pushed image: $IMAGE_NAME:$VERSION_TAG"
  fi
}

# Run security scan with Trivy if available
scan_image() {
  if command -v trivy &> /dev/null; then
    echo "Scanning image for vulnerabilities with Trivy..."
    
    # Create output directory for scan results if it doesn't exist
    SCAN_DIR="./security-scans"
    mkdir -p "$SCAN_DIR"
    
    # Generate JSON and HTML reports
    SCAN_TIMESTAMP=$(date +"%Y%m%d%H%M%S")
    JSON_OUTPUT="$SCAN_DIR/${SERVICE_NAME}_${VERSION_TAG}_${SCAN_TIMESTAMP}.json"
    HTML_OUTPUT="$SCAN_DIR/${SERVICE_NAME}_${VERSION_TAG}_${SCAN_TIMESTAMP}.html"
    
    echo "Generating vulnerability reports..."
    
    # Run scan with JSON output
    trivy image --format json --output "$JSON_OUTPUT" "$IMAGE_NAME:$VERSION_TAG"
    
    # Run scan with HTML output for human-readable report
    trivy image --format template --template "@/contrib/html.tpl" --output "$HTML_OUTPUT" "$IMAGE_NAME:$VERSION_TAG" 2>/dev/null || true
    
    # Run console output scan for immediate feedback
    trivy image --severity HIGH,CRITICAL "$IMAGE_NAME:$VERSION_TAG"
    
    # Check Trivy exit code
    if [ $? -ne 0 ]; then
      echo "Warning: Security vulnerabilities found in image"
      echo "Reports saved to: $JSON_OUTPUT and $HTML_OUTPUT"
      # Don't fail the build, just warn
    else
      echo "No critical vulnerabilities found"
      echo "Reports saved to: $JSON_OUTPUT and $HTML_OUTPUT"
    fi
  else
    echo "Trivy not found, skipping security scan"
  fi
}

# Main execution
echo "=== Building Docker image for $SERVICE_NAME ==="
echo "Service type: $SERVICE_TYPE"
echo "Environment: $ENVIRONMENT"
echo "Version tag: $VERSION_TAG"
echo "Platform: $PLATFORM"
echo "Registry: ${REGISTRY:-'Not specified (local only)'}"

# Build the Docker image
build_image

# Scan the image for vulnerabilities
scan_image

# Push the image if requested
push_image

echo "=== Docker image build completed successfully ==="