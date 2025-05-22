#!/bin/bash

# =============================================================================
# MCA Application Processing System - Environment Cleanup Script
# =============================================================================
# This script cleans up resources after tests or when environments are no longer needed
# to prevent resource leaks. It identifies resources to clean up, executes cleanup
# commands, and verifies successful cleanup to ensure efficient resource usage.
#
# Usage: ./cleanup-environment.sh [options]
#
# Options:
#   -e, --environment     Environment name (dev, staging, feature-*, etc.)
#   -n, --namespace       Kubernetes namespace to clean up
#   -g, --grace-period    Grace period in seconds before cleanup (default: 300)
#   -r, --retain-logs     Retain logs after cleanup (default: true)
#   -f, --force           Force cleanup without confirmation
#   -h, --help            Display this help message
# =============================================================================

set -e

# Default values
ENVIRONMENT=""
NAMESPACE=""
GRACE_PERIOD=300
RETAIN_LOGS=true
FORCE=false
LOG_DIR="/var/log/cleanup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/cleanup_${TIMESTAMP}.log"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Function to log messages
log() {
  local level=$1
  local message=$2
  echo "[$(date +"%Y-%m-%d %H:%M:%S")] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

# Function to display help message
show_help() {
  cat << EOF
Usage: ./cleanup-environment.sh [options]

Options:
  -e, --environment     Environment name (dev, staging, feature-*, etc.)
  -n, --namespace       Kubernetes namespace to clean up
  -g, --grace-period    Grace period in seconds before cleanup (default: 300)
  -r, --retain-logs     Retain logs after cleanup (default: true)
  -f, --force           Force cleanup without confirmation
  -h, --help            Display this help message
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -n|--namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    -g|--grace-period)
      GRACE_PERIOD="$2"
      shift 2
      ;;
    -r|--retain-logs)
      RETAIN_LOGS="$2"
      shift 2
      ;;
    -f|--force)
      FORCE=true
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

# Validate required parameters
if [[ -z "${ENVIRONMENT}" && -z "${NAMESPACE}" ]]; then
  log "ERROR" "Either environment (-e) or namespace (-n) must be specified"
  show_help
  exit 1
fi

# If namespace is not specified but environment is, derive namespace from environment
if [[ -z "${NAMESPACE}" && -n "${ENVIRONMENT}" ]]; then
  NAMESPACE="mca-${ENVIRONMENT}"
  log "INFO" "Derived namespace: ${NAMESPACE}"
fi

# Function to check if kubectl is available
check_kubectl() {
  if ! command -v kubectl &> /dev/null; then
    log "ERROR" "kubectl is not installed or not in PATH"
    exit 1
  fi
}

# Function to check if the namespace exists
check_namespace() {
  if ! kubectl get namespace "${NAMESPACE}" &> /dev/null; then
    log "ERROR" "Namespace ${NAMESPACE} does not exist"
    exit 1
  fi
}

# Function to check if AWS CLI is available
check_aws_cli() {
  if ! command -v aws &> /dev/null; then
    log "WARN" "AWS CLI is not installed or not in PATH. AWS resource cleanup will be skipped."
    return 1
  fi
  return 0
}

# Function to check if Terraform is available
check_terraform() {
  if ! command -v terraform &> /dev/null; then
    log "WARN" "Terraform is not installed or not in PATH. Terraform-managed resource cleanup will be skipped."
    return 1
  fi
  return 0
}

# Function to confirm cleanup
confirm_cleanup() {
  if [[ "${FORCE}" == true ]]; then
    return 0
  fi

  log "WARN" "You are about to clean up resources for namespace: ${NAMESPACE}"
  log "WARN" "This action cannot be undone."
  read -p "Are you sure you want to continue? (y/n): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "INFO" "Cleanup aborted by user"
    exit 0
  fi
}

# Function to wait for grace period
wait_grace_period() {
  if [[ ${GRACE_PERIOD} -gt 0 ]]; then
    log "INFO" "Waiting for grace period of ${GRACE_PERIOD} seconds before cleanup..."
    sleep "${GRACE_PERIOD}"
  fi
}

# Function to identify Kubernetes resources to clean up
identify_k8s_resources() {
  log "INFO" "Identifying Kubernetes resources in namespace: ${NAMESPACE}"
  
  # Get all resource types in the namespace
  RESOURCE_TYPES=$(kubectl api-resources --verbs=list --namespaced -o name | grep -v "events.events.k8s.io" | grep -v "events" | sort | uniq)
  
  # For each resource type, get all resources
  for resource_type in ${RESOURCE_TYPES}; do
    log "INFO" "Checking resources of type: ${resource_type}"
    RESOURCES=$(kubectl get "${resource_type}" -n "${NAMESPACE}" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -n "${RESOURCES}" ]]; then
      for resource in ${RESOURCES}; do
        log "INFO" "Found ${resource_type}/${resource}"
      done
    fi
  done
}

# Function to clean up Kubernetes resources
cleanup_k8s_resources() {
  log "INFO" "Cleaning up Kubernetes resources in namespace: ${NAMESPACE}"
  
  # Save resources for verification
  kubectl get all -n "${NAMESPACE}" -o wide > "${LOG_DIR}/pre_cleanup_resources_${TIMESTAMP}.log" 2>/dev/null || true
  
  # Delete all resources in the namespace
  log "INFO" "Deleting all resources in namespace: ${NAMESPACE}"
  kubectl delete all --all -n "${NAMESPACE}" --timeout=5m || log "WARN" "Some resources could not be deleted"
  
  # Delete PVCs
  log "INFO" "Deleting persistent volume claims"
  kubectl delete pvc --all -n "${NAMESPACE}" --timeout=5m 2>/dev/null || log "WARN" "No PVCs found or some PVCs could not be deleted"
  
  # Delete ConfigMaps
  log "INFO" "Deleting ConfigMaps"
  kubectl delete configmap --all -n "${NAMESPACE}" --timeout=2m 2>/dev/null || log "WARN" "No ConfigMaps found or some ConfigMaps could not be deleted"
  
  # Delete Secrets
  log "INFO" "Deleting Secrets"
  kubectl delete secret --all -n "${NAMESPACE}" --timeout=2m 2>/dev/null || log "WARN" "No Secrets found or some Secrets could not be deleted"
  
  # Delete ServiceAccounts
  log "INFO" "Deleting ServiceAccounts"
  kubectl delete serviceaccount --all -n "${NAMESPACE}" --timeout=2m 2>/dev/null || log "WARN" "No ServiceAccounts found or some ServiceAccounts could not be deleted"
  
  # Delete the namespace itself if it's a feature environment
  if [[ "${NAMESPACE}" == mca-feature-* ]]; then
    log "INFO" "Deleting namespace: ${NAMESPACE}"
    kubectl delete namespace "${NAMESPACE}" --timeout=5m || log "ERROR" "Failed to delete namespace: ${NAMESPACE}"
  else
    log "INFO" "Skipping namespace deletion for non-feature environment: ${NAMESPACE}"
  fi
}

# Function to clean up cloud resources (AWS example)
cleanup_cloud_resources() {
  if check_aws_cli; then
    log "INFO" "Cleaning up AWS resources for environment: ${ENVIRONMENT}"
    
    # Get load balancers associated with the environment
    log "INFO" "Identifying load balancers"
    LBS=$(aws elb describe-load-balancers --query "LoadBalancerDescriptions[?contains(LoadBalancerName, '${ENVIRONMENT}')].LoadBalancerName" --output text 2>/dev/null || echo "")
    
    if [[ -n "${LBS}" ]]; then
      for lb in ${LBS}; do
        log "INFO" "Deleting load balancer: ${lb}"
        aws elb delete-load-balancer --load-balancer-name "${lb}" || log "WARN" "Failed to delete load balancer: ${lb}"
      done
    else
      log "INFO" "No load balancers found for environment: ${ENVIRONMENT}"
    fi
    
    # Get EBS volumes associated with the environment
    log "INFO" "Identifying EBS volumes"
    VOLUMES=$(aws ec2 describe-volumes --filters "Name=tag:Environment,Values=${ENVIRONMENT}" --query "Volumes[*].VolumeId" --output text 2>/dev/null || echo "")
    
    if [[ -n "${VOLUMES}" ]]; then
      for volume in ${VOLUMES}; do
        log "INFO" "Deleting EBS volume: ${volume}"
        aws ec2 delete-volume --volume-id "${volume}" || log "WARN" "Failed to delete EBS volume: ${volume}"
      done
    else
      log "INFO" "No EBS volumes found for environment: ${ENVIRONMENT}"
    fi
    
    # Clean up S3 buckets (only for feature environments)
    if [[ "${ENVIRONMENT}" == feature-* ]]; then
      log "INFO" "Identifying S3 buckets"
      BUCKETS=$(aws s3api list-buckets --query "Buckets[?contains(Name, 'mca-documents-${ENVIRONMENT}')].Name" --output text 2>/dev/null || echo "")
      
      if [[ -n "${BUCKETS}" ]]; then
        for bucket in ${BUCKETS}; do
          log "INFO" "Emptying and deleting S3 bucket: ${bucket}"
          aws s3 rm "s3://${bucket}" --recursive || log "WARN" "Failed to empty S3 bucket: ${bucket}"
          aws s3api delete-bucket --bucket "${bucket}" || log "WARN" "Failed to delete S3 bucket: ${bucket}"
        done
      else
        log "INFO" "No S3 buckets found for environment: ${ENVIRONMENT}"
      fi
    fi
  fi
}

# Function to clean up database test data
cleanup_database() {
  log "INFO" "Cleaning up database test data for environment: ${ENVIRONMENT}"
  
  # Get database connection details from Kubernetes secrets
  if kubectl get secret db-credentials -n "${NAMESPACE}" &> /dev/null; then
    DB_HOST=$(kubectl get secret db-credentials -n "${NAMESPACE}" -o jsonpath='{.data.host}' | base64 --decode)
    DB_PORT=$(kubectl get secret db-credentials -n "${NAMESPACE}" -o jsonpath='{.data.port}' | base64 --decode)
    DB_USER=$(kubectl get secret db-credentials -n "${NAMESPACE}" -o jsonpath='{.data.username}' | base64 --decode)
    DB_PASS=$(kubectl get secret db-credentials -n "${NAMESPACE}" -o jsonpath='{.data.password}' | base64 --decode)
    DB_NAME="mca_${ENVIRONMENT//-/_}"
    
    log "INFO" "Connecting to database: ${DB_NAME} on ${DB_HOST}"
    
    # Check if psql is available
    if command -v psql &> /dev/null; then
      # Export password for psql
      export PGPASSWORD="${DB_PASS}"
      
      # For feature environments, drop the database
      if [[ "${ENVIRONMENT}" == feature-* ]]; then
        log "INFO" "Dropping database: ${DB_NAME}"
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};" || log "WARN" "Failed to drop database: ${DB_NAME}"
      else
        # For persistent environments, truncate tables instead of dropping the database
        log "INFO" "Truncating tables in database: ${DB_NAME}"
        
        # Get list of tables
        TABLES=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        
        # Disable triggers temporarily
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "SET session_replication_role = 'replica';" || log "WARN" "Failed to disable triggers"
        
        # Truncate each table
        for table in ${TABLES}; do
          log "INFO" "Truncating table: ${table}"
          psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "TRUNCATE TABLE ${table} CASCADE;" || log "WARN" "Failed to truncate table: ${table}"
        done
        
        # Re-enable triggers
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "SET session_replication_role = 'origin';" || log "WARN" "Failed to re-enable triggers"
      fi
      
      # Unset password
      unset PGPASSWORD
    else
      log "WARN" "psql is not installed or not in PATH. Database cleanup will be skipped."
    fi
  else
    log "WARN" "Database credentials not found. Database cleanup will be skipped."
  fi
}

# Function to clean up RabbitMQ queues
cleanup_rabbitmq() {
  log "INFO" "Cleaning up RabbitMQ queues for environment: ${ENVIRONMENT}"
  
  # Get RabbitMQ connection details from Kubernetes secrets
  if kubectl get secret rabbitmq-credentials -n "${NAMESPACE}" &> /dev/null; then
    RABBITMQ_HOST=$(kubectl get secret rabbitmq-credentials -n "${NAMESPACE}" -o jsonpath='{.data.host}' | base64 --decode)
    RABBITMQ_PORT=$(kubectl get secret rabbitmq-credentials -n "${NAMESPACE}" -o jsonpath='{.data.port}' | base64 --decode)
    RABBITMQ_USER=$(kubectl get secret rabbitmq-credentials -n "${NAMESPACE}" -o jsonpath='{.data.username}' | base64 --decode)
    RABBITMQ_PASS=$(kubectl get secret rabbitmq-credentials -n "${NAMESPACE}" -o jsonpath='{.data.password}' | base64 --decode)
    
    log "INFO" "Connecting to RabbitMQ: ${RABBITMQ_HOST}"
    
    # Check if rabbitmqadmin is available
    if command -v rabbitmqadmin &> /dev/null; then
      # Get list of queues for the environment
      QUEUES=$(rabbitmqadmin --host="${RABBITMQ_HOST}" --port="${RABBITMQ_PORT}" --username="${RABBITMQ_USER}" --password="${RABBITMQ_PASS}" list queues name | grep "${ENVIRONMENT}" | awk '{print $2}')
      
      # Delete each queue
      for queue in ${QUEUES}; do
        log "INFO" "Deleting RabbitMQ queue: ${queue}"
        rabbitmqadmin --host="${RABBITMQ_HOST}" --port="${RABBITMQ_PORT}" --username="${RABBITMQ_USER}" --password="${RABBITMQ_PASS}" delete queue name="${queue}" || log "WARN" "Failed to delete RabbitMQ queue: ${queue}"
      done
    else
      log "WARN" "rabbitmqadmin is not installed or not in PATH. RabbitMQ cleanup will be skipped."
    fi
  else
    log "WARN" "RabbitMQ credentials not found. RabbitMQ cleanup will be skipped."
  fi
}

# Function to clean up Redis data
cleanup_redis() {
  log "INFO" "Cleaning up Redis data for environment: ${ENVIRONMENT}"
  
  # Get Redis connection details from Kubernetes secrets
  if kubectl get secret redis-credentials -n "${NAMESPACE}" &> /dev/null; then
    REDIS_HOST=$(kubectl get secret redis-credentials -n "${NAMESPACE}" -o jsonpath='{.data.host}' | base64 --decode)
    REDIS_PORT=$(kubectl get secret redis-credentials -n "${NAMESPACE}" -o jsonpath='{.data.port}' | base64 --decode)
    REDIS_PASS=$(kubectl get secret redis-credentials -n "${NAMESPACE}" -o jsonpath='{.data.password}' | base64 --decode)
    
    log "INFO" "Connecting to Redis: ${REDIS_HOST}"
    
    # Check if redis-cli is available
    if command -v redis-cli &> /dev/null; then
      # Flush all keys with the environment prefix
      log "INFO" "Flushing Redis keys with prefix: ${ENVIRONMENT}"
      redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" -a "${REDIS_PASS}" --scan --pattern "${ENVIRONMENT}:*" | xargs -r redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" -a "${REDIS_PASS}" del || log "WARN" "Failed to flush Redis keys"
    else
      log "WARN" "redis-cli is not installed or not in PATH. Redis cleanup will be skipped."
    fi
  else
    log "WARN" "Redis credentials not found. Redis cleanup will be skipped."
  fi
}

# Function to verify successful cleanup
verify_cleanup() {
  log "INFO" "Verifying successful cleanup"
  
  # Check if namespace still exists (for feature environments)
  if [[ "${NAMESPACE}" == mca-feature-* ]]; then
    if kubectl get namespace "${NAMESPACE}" &> /dev/null; then
      log "ERROR" "Namespace ${NAMESPACE} still exists after cleanup"
      return 1
    else
      log "INFO" "Namespace ${NAMESPACE} successfully deleted"
    fi
  else
    # For persistent environments, check if resources are cleaned up
    REMAINING_RESOURCES=$(kubectl get all -n "${NAMESPACE}" -o name 2>/dev/null | grep -v "service/kubernetes" || echo "")
    
    if [[ -n "${REMAINING_RESOURCES}" ]]; then
      log "WARN" "Some resources still exist in namespace ${NAMESPACE} after cleanup:"
      echo "${REMAINING_RESOURCES}" | tee -a "${LOG_FILE}"
      return 1
    else
      log "INFO" "All resources in namespace ${NAMESPACE} successfully cleaned up"
    fi
  fi
  
  # Additional verification for cloud resources could be added here
  
  return 0
}

# Function to archive logs if retention is enabled
archive_logs() {
  if [[ "${RETAIN_LOGS}" == true ]]; then
    log "INFO" "Archiving logs for future reference"
    
    # Create archive directory
    ARCHIVE_DIR="${LOG_DIR}/archives"
    mkdir -p "${ARCHIVE_DIR}"
    
    # Archive logs
    ARCHIVE_FILE="${ARCHIVE_DIR}/cleanup_${ENVIRONMENT}_${TIMESTAMP}.tar.gz"
    tar -czf "${ARCHIVE_FILE}" -C "${LOG_DIR}" "cleanup_${TIMESTAMP}.log" "pre_cleanup_resources_${TIMESTAMP}.log" 2>/dev/null || true
    
    log "INFO" "Logs archived to: ${ARCHIVE_FILE}"
  else
    log "INFO" "Log retention disabled, skipping archiving"
  fi
}

# Main execution
main() {
  log "INFO" "Starting cleanup process for environment: ${ENVIRONMENT}, namespace: ${NAMESPACE}"
  
  # Check prerequisites
  check_kubectl
  
  # Check if namespace exists
  check_namespace
  
  # Confirm cleanup
  confirm_cleanup
  
  # Wait for grace period
  wait_grace_period
  
  # Identify resources to clean up
  identify_k8s_resources
  
  # Clean up Kubernetes resources
  cleanup_k8s_resources
  
  # Clean up cloud resources
  cleanup_cloud_resources
  
  # Clean up database test data
  cleanup_database
  
  # Clean up RabbitMQ queues
  cleanup_rabbitmq
  
  # Clean up Redis data
  cleanup_redis
  
  # Verify successful cleanup
  if verify_cleanup; then
    log "INFO" "Cleanup completed successfully"
  else
    log "WARN" "Cleanup completed with warnings or errors"
  fi
  
  # Archive logs
  archive_logs
  
  log "INFO" "Cleanup process finished"
}

# Execute main function
main