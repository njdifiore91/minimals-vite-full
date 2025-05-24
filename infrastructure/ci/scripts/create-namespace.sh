#!/bin/bash

# =============================================================================
# create-namespace.sh
# =============================================================================
#
# Creates and configures Kubernetes namespaces for dynamic environments with
# proper resource quotas and network policies. It generates namespace names
# based on branch or PR information, applies appropriate resource limits, and
# configures network policies for service isolation.
#
# This script enables the dynamic environment creation feature described in the
# CI/CD pipeline architecture, allowing isolated testing environments for
# feature branches.
#
# Usage:
#   ./create-namespace.sh --env-type <type> --branch-name <branch> [--pr-number <number>] [--cleanup <true|false>]
#
# Arguments:
#   --env-type     Environment type (feature, development, staging, production)
#   --branch-name  Git branch name (required for feature environments)
#   --pr-number    Pull request number (optional, for feature environments)
#   --cleanup      Whether to add cleanup hooks (default: true for feature environments)
#   --help         Display this help message
#
# Examples:
#   ./create-namespace.sh --env-type feature --branch-name feature/add-ocr --pr-number 123
#   ./create-namespace.sh --env-type development
#   ./create-namespace.sh --env-type staging
#   ./create-namespace.sh --env-type production
#
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================

# Base namespace prefix
NAMESPACE_PREFIX="mca"

# Maximum namespace name length (Kubernetes limit is 63 characters)
MAX_NAMESPACE_LENGTH=63

# Default cleanup setting
DEFAULT_CLEANUP="true"

# Resource quota templates location
RESOURCE_QUOTA_TEMPLATES="/infrastructure/kubernetes/namespaces/resource-quotas.yaml"

# Network policy templates location
NETWORK_POLICY_TEMPLATES="/infrastructure/kubernetes/namespaces/network-policies"

# RBAC templates location
RBAC_TEMPLATES="/infrastructure/kubernetes/namespaces/rbac.yaml"

# =============================================================================
# Logging functions
# =============================================================================

log_info() {
  echo -e "\033[0;32m[INFO]\033[0m $1"
}

log_warn() {
  echo -e "\033[0;33m[WARN]\033[0m $1"
}

log_error() {
  echo -e "\033[0;31m[ERROR]\033[0m $1"
}

log_debug() {
  if [[ "${DEBUG:-false}" == "true" ]]; then
    echo -e "\033[0;34m[DEBUG]\033[0m $1"
  fi
}

# =============================================================================
# Helper functions
# =============================================================================

show_help() {
  grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^#//' | sed 's/^ //' | sed '/^$/q'
  exit 0
}

check_command() {
  if ! command -v "$1" &> /dev/null; then
    log_error "Required command '$1' not found. Please install it and try again."
    exit 1
  fi
}

check_dependencies() {
  log_debug "Checking dependencies..."
  check_command "kubectl"
  check_command "yq"
  check_command "jq"
}

validate_input() {
  # Validate environment type
  if [[ -z "${ENV_TYPE}" ]]; then
    log_error "Environment type (--env-type) is required"
    show_help
    exit 1
  fi

  if [[ "${ENV_TYPE}" != "feature" && "${ENV_TYPE}" != "development" && "${ENV_TYPE}" != "staging" && "${ENV_TYPE}" != "production" ]]; then
    log_error "Invalid environment type: ${ENV_TYPE}. Must be one of: feature, development, staging, production"
    exit 1
  fi

  # Validate branch name for feature environments
  if [[ "${ENV_TYPE}" == "feature" && -z "${BRANCH_NAME}" ]]; then
    log_error "Branch name (--branch-name) is required for feature environments"
    exit 1
  fi

  # Set default cleanup value for feature environments
  if [[ "${ENV_TYPE}" == "feature" && -z "${CLEANUP}" ]]; then
    CLEANUP="${DEFAULT_CLEANUP}"
    log_debug "Setting default cleanup value: ${CLEANUP}"
  fi
}

# =============================================================================
# Namespace generation and validation
# =============================================================================

generate_namespace_name() {
  local env_type="$1"
  local branch_name="$2"
  local pr_number="$3"
  local namespace_name=""

  case "${env_type}" in
    feature)
      # For feature branches, use branch name and PR number if available
      # Convert branch name to valid Kubernetes name: lowercase, alphanumeric, dashes
      local sanitized_branch=$(echo "${branch_name}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')
      
      if [[ -n "${pr_number}" ]]; then
        namespace_name="${NAMESPACE_PREFIX}-feature-pr${pr_number}"
      else
        namespace_name="${NAMESPACE_PREFIX}-feature-${sanitized_branch}"
      fi
      ;;
    development)
      namespace_name="${NAMESPACE_PREFIX}-development"
      ;;
    staging)
      namespace_name="${NAMESPACE_PREFIX}-staging"
      ;;
    production)
      namespace_name="${NAMESPACE_PREFIX}-production"
      ;;
    *)
      log_error "Invalid environment type: ${env_type}"
      exit 1
      ;;
  esac

  # Ensure namespace name is not too long
  if [[ ${#namespace_name} -gt ${MAX_NAMESPACE_LENGTH} ]]; then
    # Truncate namespace name if too long
    namespace_name="${namespace_name:0:$((MAX_NAMESPACE_LENGTH - 8))}-$(echo "${namespace_name}" | md5sum | cut -c1-7)"
    log_warn "Namespace name was too long and has been truncated to: ${namespace_name}"
  fi

  echo "${namespace_name}"
}

check_namespace_exists() {
  local namespace="$1"
  if kubectl get namespace "${namespace}" &> /dev/null; then
    return 0  # Namespace exists
  else
    return 1  # Namespace does not exist
  fi
}

# =============================================================================
# Namespace creation and configuration
# =============================================================================

create_namespace() {
  local namespace="$1"
  local env_type="$2"
  local branch_name="$3"
  local pr_number="$4"

  log_info "Creating namespace: ${namespace}"

  # Create namespace with appropriate labels and annotations
  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: ${namespace}
  labels:
    name: ${namespace}
    environment: ${env_type}
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
    tier: ${env_type}
    version: "1.0"
    network-policy: restricted
    monitoring: enabled
    logging: enabled
    tracing: ${env_type == "production" || env_type == "staging" ? "enabled" : "disabled"}
  annotations:
    description: "${env_type} environment for MCA Application Processing System"
    documentation: "https://dollarfunding.com/docs/mca-application-processing"
    scheduler.alpha.kubernetes.io/node-selector: "env=${env_type},workload=mca"
    compliance.dollarfunding.com/data-classification: "${env_type == "production" ? "sensitive" : "internal"}"
    backup.dollarfunding.com/schedule: "${env_type == "production" ? "daily" : env_type == "staging" ? "weekly" : "none"}"
    backup.dollarfunding.com/retention: "${env_type == "production" ? "7-years" : env_type == "staging" ? "30-days" : "none"}"
    monitoring.dollarfunding.com/priority: "${env_type == "production" ? "p1" : env_type == "staging" ? "p2" : "p3"}"
    monitoring.dollarfunding.com/sla: "${env_type == "production" ? "99.9%" : env_type == "staging" ? "99.5%" : "best-effort"}"
    cost.dollarfunding.com/business-unit: "lending"
    cost.dollarfunding.com/project: "mca-application-processing"
    cost.dollarfunding.com/owner: "lending-operations"
    ci.dollarfunding.com/created-by: "create-namespace.sh"
    ci.dollarfunding.com/created-at: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    ${env_type == "feature" ? "ci.dollarfunding.com/branch: \"${branch_name}\"" : ""}
    ${pr_number ? "ci.dollarfunding.com/pr-number: \"${pr_number}\"" : ""}
    ${env_type == "feature" && CLEANUP == "true" ? "ci.dollarfunding.com/auto-cleanup: \"true\"" : ""}
spec:
  finalizers:
  - kubernetes
EOF

  log_info "Namespace ${namespace} created successfully"
}

# =============================================================================
# Resource quota application
# =============================================================================

apply_resource_quotas() {
  local namespace="$1"
  local env_type="$2"

  log_info "Applying resource quotas for namespace: ${namespace}"

  # Determine which resource quota to apply based on environment type
  local quota_name
  case "${env_type}" in
    feature)
      # For feature branches, use a more restricted quota
      quota_name="mca-development-quota"  # Reuse development quota but with tighter limits
      ;;
    development)
      quota_name="mca-development-quota"
      ;;
    staging)
      quota_name="mca-staging-quota"
      ;;
    production)
      quota_name="mca-production-quota"
      ;;
    *)
      log_error "Invalid environment type for resource quota: ${env_type}"
      exit 1
      ;;
  esac

  # Extract and apply the appropriate resource quota
  if [[ -f "${RESOURCE_QUOTA_TEMPLATES}" ]]; then
    # Extract the specific quota from the template file
    yq eval "select(.metadata.name == \"${quota_name}\")" "${RESOURCE_QUOTA_TEMPLATES}" > "/tmp/${quota_name}.yaml"
    
    # Update the namespace in the extracted quota
    yq eval ".metadata.namespace = \"${namespace}\"" -i "/tmp/${quota_name}.yaml"
    
    # Apply the quota
    kubectl apply -f "/tmp/${quota_name}.yaml"
    
    # Clean up temporary file
    rm -f "/tmp/${quota_name}.yaml"
    
    log_info "Applied resource quota ${quota_name} to namespace ${namespace}"
  else
    log_warn "Resource quota template file not found: ${RESOURCE_QUOTA_TEMPLATES}"
    log_warn "Skipping resource quota application"
  fi

  # For feature environments, apply tighter limits
  if [[ "${env_type}" == "feature" ]]; then
    # Create a feature-specific resource quota with tighter limits
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: feature-environment-quota
  namespace: ${namespace}
  labels:
    environment: feature
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Feature environment resource quota with tighter limits"
spec:
  hard:
    # Compute Resources - more restricted for feature environments
    requests.cpu: "4"
    limits.cpu: "8"
    requests.memory: "8Gi"
    limits.memory: "16Gi"
    # GPU Resources - limited to 1 for OCR Service
    requests.nvidia.com/gpu: "1"
    limits.nvidia.com/gpu: "1"
    # Storage Resources
    requests.storage: "50Gi"
    persistentvolumeclaims: "10"
    # Object Count Limits
    pods: "30"
    services: "15"
    services.loadbalancers: "2"
    configmaps: "30"
    secrets: "30"
    deployments.apps: "15"
    statefulsets.apps: "5"
    jobs.batch: "20"
    cronjobs.batch: "5"
EOF
    log_info "Applied feature-specific resource quota to namespace ${namespace}"
  fi
}

# =============================================================================
# Network policy configuration
# =============================================================================

apply_network_policies() {
  local namespace="$1"
  local env_type="$2"

  log_info "Applying network policies for namespace: ${namespace}"

  # Default deny all ingress and egress traffic
  cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Default deny all ingress and egress traffic"
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
EOF

  # Allow DNS resolution
  cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-resolution
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Allow DNS resolution"
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
EOF

  # Allow intra-namespace communication
  cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-intra-namespace
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Allow communication between pods in the same namespace"
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector: {}
EOF

  # Allow ingress from API Gateway
  cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-gateway-ingress
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Allow ingress from API Gateway"
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/part-of: mca-application-processing
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: api-gateway
      podSelector:
        matchLabels:
          app.kubernetes.io/component: api-gateway
EOF

  # Allow egress to RabbitMQ
  cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-rabbitmq-egress
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Allow egress to RabbitMQ"
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/part-of: mca-application-processing
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: rabbitmq
      podSelector:
        matchLabels:
          app.kubernetes.io/component: rabbitmq
    ports:
    - protocol: TCP
      port: 5672
EOF

  # Allow egress to PostgreSQL
  cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-postgresql-egress
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Allow egress to PostgreSQL"
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/part-of: mca-application-processing
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: postgresql
      podSelector:
        matchLabels:
          app.kubernetes.io/component: postgresql
    ports:
    - protocol: TCP
      port: 5432
EOF

  # Allow egress to Redis
  cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-redis-egress
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Allow egress to Redis"
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/part-of: mca-application-processing
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: redis
      podSelector:
        matchLabels:
          app.kubernetes.io/component: redis
    ports:
    - protocol: TCP
      port: 6379
EOF

  # Allow egress to S3 storage (via proxy or direct)
  cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-s3-egress
  namespace: ${namespace}
  labels:
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Allow egress to S3 storage"
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/part-of: mca-application-processing
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
    ports:
    - protocol: TCP
      port: 443
  - to:
    - namespaceSelector:
        matchLabels:
          name: s3-proxy
      podSelector:
        matchLabels:
          app.kubernetes.io/component: s3-proxy
EOF

  log_info "Applied network policies to namespace ${namespace}"
}

# =============================================================================
# RBAC configuration
# =============================================================================

apply_rbac() {
  local namespace="$1"
  local env_type="$2"

  log_info "Applying RBAC configuration for namespace: ${namespace}"

  # Create service accounts for each microservice
  for service in "email-service" "document-service" "ocr-service" "data-service" "notification-service" "api-gateway"; do
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${service}
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/component: ${service}
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Service account for ${service}"
EOF
  done

  # Create roles for each service type
  # Email Service Role
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: email-service-role
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
rules:
# Access to its own configuration
- apiGroups: [""] # Core API group
  resources: ["configmaps"]
  resourceNames: ["email-service-config"]
  verbs: ["get", "list", "watch"]
# Access to RabbitMQ credentials
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["rabbitmq-credentials"]
  verbs: ["get"]
# Access to email credentials
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["email-credentials"]
  verbs: ["get"]
EOF

  # Document Service Role
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: document-service-role
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
rules:
# Access to its own configuration
- apiGroups: [""] # Core API group
  resources: ["configmaps"]
  resourceNames: ["document-service-config"]
  verbs: ["get", "list", "watch"]
# Access to RabbitMQ credentials
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["rabbitmq-credentials"]
  verbs: ["get"]
# Access to S3 storage credentials
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["s3-credentials"]
  verbs: ["get"]
# Access to ML model configuration
- apiGroups: [""] # Core API group
  resources: ["configmaps"]
  resourceNames: ["document-classification-models"]
  verbs: ["get", "list", "watch"]
EOF

  # OCR Service Role
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ocr-service-role
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
rules:
# Access to its own configuration
- apiGroups: [""] # Core API group
  resources: ["configmaps"]
  resourceNames: ["ocr-service-config"]
  verbs: ["get", "list", "watch"]
# Access to RabbitMQ credentials
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["rabbitmq-credentials"]
  verbs: ["get"]
# Access to S3 storage credentials
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["s3-credentials"]
  verbs: ["get"]
# Access to TensorFlow model configuration
- apiGroups: [""] # Core API group
  resources: ["configmaps"]
  resourceNames: ["ocr-models"]
  verbs: ["get", "list", "watch"]
EOF

  # Data Service Role
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: data-service-role
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
rules:
# Access to its own configuration
- apiGroups: [""] # Core API group
  resources: ["configmaps"]
  resourceNames: ["data-service-config"]
  verbs: ["get", "list", "watch"]
# Access to RabbitMQ credentials
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["rabbitmq-credentials"]
  verbs: ["get"]
# Access to database credentials
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["postgresql-credentials"]
  verbs: ["get"]
# Access to Redis credentials
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["redis-credentials"]
  verbs: ["get"]
# Access to encryption keys for PII
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["field-encryption-keys"]
  verbs: ["get"]
EOF

  # Notification Service Role
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: notification-service-role
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
rules:
# Access to its own configuration
- apiGroups: [""] # Core API group
  resources: ["configmaps"]
  resourceNames: ["notification-service-config"]
  verbs: ["get", "list", "watch"]
# Access to RabbitMQ credentials
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["rabbitmq-credentials"]
  verbs: ["get"]
# Access to webhook configuration
- apiGroups: [""] # Core API group
  resources: ["configmaps"]
  resourceNames: ["webhook-configurations"]
  verbs: ["get", "list", "watch"]
# Access to webhook signing keys
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["webhook-signing-keys"]
  verbs: ["get"]
EOF

  # API Gateway Role
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: api-gateway-role
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
rules:
# Access to its own configuration
- apiGroups: [""] # Core API group
  resources: ["configmaps"]
  resourceNames: ["api-gateway-config"]
  verbs: ["get", "list", "watch"]
# Access to TLS certificates
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["api-gateway-tls"]
  verbs: ["get"]
# Access to JWT public keys for validation
- apiGroups: [""] # Core API group
  resources: ["secrets"]
  resourceNames: ["jwt-public-keys"]
  verbs: ["get"]
# Access to service discovery
- apiGroups: [""] # Core API group
  resources: ["services", "endpoints"]
  verbs: ["get", "list", "watch"]
EOF

  # Create role bindings for each service
  for service in "email-service" "document-service" "ocr-service" "data-service" "notification-service" "api-gateway"; do
    cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ${service}-binding
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
subjects:
- kind: ServiceAccount
  name: ${service}
  namespace: ${namespace}
roleRef:
  kind: Role
  name: ${service}-role
  apiGroup: rbac.authorization.k8s.io
EOF
  done

  # Create roles for user types as specified in section 0.1.3
  # Operations Staff Role - Read all, write application data
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: operations-staff-role
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Role for Operations Staff with permissions to read all and write application data"
rules:
# Read access to all resources
- apiGroups: [""] # Core API group
  resources: ["pods", "services", "configmaps", "secrets", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch"]
# Write access to application data resources
- apiGroups: [""] # Core API group
  resources: ["configmaps"]
  resourceNames: ["application-data", "document-metadata"]
  verbs: ["update", "patch"]
# Access to logs
- apiGroups: [""] # Core API group
  resources: ["pods/log"]
  verbs: ["get", "list"]
# Access to application-specific custom resources
- apiGroups: ["mca.dollarfunding.com"]
  resources: ["applications", "documents"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
EOF

  # System Admin Role - Full access to all endpoints and webhook configuration
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: system-admin-role
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
  annotations:
    description: "Role for System Admin with full access to all endpoints and webhook configuration"
rules:
# Full access to all resources in the namespace
- apiGroups: [""] # Core API group
  resources: ["*"]
  verbs: ["*"]
# Full access to all custom resources
- apiGroups: ["mca.dollarfunding.com"]
  resources: ["*"]
  verbs: ["*"]
# Full access to webhook configuration
- apiGroups: ["mca.dollarfunding.com"]
  resources: ["webhooks", "webhookconfigurations"]
  verbs: ["*"]
# Access to Kong API Gateway configuration
- apiGroups: ["configuration.konghq.com"]
  resources: ["kongplugins", "kongconsumers", "kongingresses"]
  verbs: ["*"]
EOF

  # Create role bindings for user roles
  # Operations Staff RoleBinding
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: operations-staff-binding
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
subjects:
# This is where user identities would be bound to the role
# For JWT authentication, this would be managed by an authentication proxy
# that maps JWT claims to Kubernetes RBAC
- kind: Group
  name: operations-staff
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: operations-staff-role
  apiGroup: rbac.authorization.k8s.io
EOF

  # System Admin RoleBinding
  cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: system-admin-binding
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
subjects:
# This is where user identities would be bound to the role
# For JWT authentication, this would be managed by an authentication proxy
# that maps JWT claims to Kubernetes RBAC
- kind: Group
  name: system-admins
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: system-admin-role
  apiGroup: rbac.authorization.k8s.io
EOF

  log_info "Applied RBAC configuration to namespace ${namespace}"
}

# =============================================================================
# Cleanup hooks
# =============================================================================

add_cleanup_hooks() {
  local namespace="$1"
  local env_type="$2"
  local branch_name="$3"
  local pr_number="$4"

  # Only add cleanup hooks for feature environments
  if [[ "${env_type}" != "feature" || "${CLEANUP}" != "true" ]]; then
    log_debug "Skipping cleanup hooks for ${env_type} environment or cleanup disabled"
    return 0
  fi

  log_info "Adding cleanup hooks for namespace: ${namespace}"

  # Create a ConfigMap to store cleanup information
  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: cleanup-info
  namespace: ${namespace}
  labels:
    app.kubernetes.io/part-of: mca-application-processing
    app.kubernetes.io/managed-by: ci-pipeline
    cleanup: "true"
  annotations:
    description: "Cleanup information for feature environment"
    ci.dollarfunding.com/branch: "${branch_name}"
    ci.dollarfunding.com/pr-number: "${pr_number:-none}"
    ci.dollarfunding.com/created-at: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    ci.dollarfunding.com/cleanup-policy: "pr-closed"
data:
  branch: "${branch_name}"
  pr-number: "${pr_number:-none}"
  created-at: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  cleanup-policy: "pr-closed"
  ttl-hours: "168"  # 7 days TTL for feature environments
EOF

  # Create a CronJob to check if the PR is closed and delete the namespace if it is
  # Note: This would typically be handled by a central cleanup service monitoring all namespaces
  # For demonstration purposes, we're showing what such a job might look like
  log_info "Cleanup hooks added for namespace ${namespace}"
  log_info "Note: Actual cleanup will be performed by the CI/CD system when the PR is closed"
}

# =============================================================================
# Main execution
# =============================================================================

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-type)
      ENV_TYPE="$2"
      shift 2
      ;;
    --branch-name)
      BRANCH_NAME="$2"
      shift 2
      ;;
    --pr-number)
      PR_NUMBER="$2"
      shift 2
      ;;
    --cleanup)
      CLEANUP="$2"
      shift 2
      ;;
    --help)
      show_help
      ;;
    --debug)
      DEBUG="true"
      shift
      ;;
    *)
      log_error "Unknown option: $1"
      show_help
      exit 1
      ;;
  esac
done

# Validate input parameters
validate_input

# Check dependencies
check_dependencies

# Generate namespace name
NAMESPACE=$(generate_namespace_name "${ENV_TYPE}" "${BRANCH_NAME}" "${PR_NUMBER}")

# Check if namespace already exists
if check_namespace_exists "${NAMESPACE}"; then
  log_warn "Namespace ${NAMESPACE} already exists"
  
  # For feature environments, we might want to recreate it
  if [[ "${ENV_TYPE}" == "feature" ]]; then
    log_info "Recreating feature environment namespace: ${NAMESPACE}"
    kubectl delete namespace "${NAMESPACE}" --wait=true
    
    # Wait for namespace to be fully deleted
    while check_namespace_exists "${NAMESPACE}"; do
      log_info "Waiting for namespace ${NAMESPACE} to be deleted..."
      sleep 5
    done
  else
    log_info "Using existing namespace: ${NAMESPACE}"
    exit 0
  fi
fi

# Create namespace
create_namespace "${NAMESPACE}" "${ENV_TYPE}" "${BRANCH_NAME}" "${PR_NUMBER}"

# Apply resource quotas
apply_resource_quotas "${NAMESPACE}" "${ENV_TYPE}"

# Apply network policies
apply_network_policies "${NAMESPACE}" "${ENV_TYPE}"

# Apply RBAC configuration
apply_rbac "${NAMESPACE}" "${ENV_TYPE}"

# Add cleanup hooks for feature environments
if [[ "${ENV_TYPE}" == "feature" && "${CLEANUP}" == "true" ]]; then
  add_cleanup_hooks "${NAMESPACE}" "${ENV_TYPE}" "${BRANCH_NAME}" "${PR_NUMBER}"
fi

log_info "Namespace ${NAMESPACE} has been successfully created and configured"

# Output the namespace name for use by other scripts
echo "${NAMESPACE}"

exit 0