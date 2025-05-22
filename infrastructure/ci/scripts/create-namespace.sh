#!/bin/bash
# Make script executable with: chmod +x create-namespace.sh

# create-namespace.sh
# 
# This script creates and configures Kubernetes namespaces for dynamic environments
# with proper resource quotas, network policies, and RBAC configuration.
#
# It supports:
# - Dynamic namespace generation based on Git branch or PR information
# - Environment-specific resource quotas (feature, development, staging, production)
# - Network policy configuration for service isolation
# - RBAC setup with appropriate roles and service accounts
# - Validation to prevent namespace collisions
# - Cleanup hooks for ephemeral environments
#
# Usage: ./create-namespace.sh [options]
#
# Options:
#   --env-type <type>       Environment type: feature, development, staging, production
#   --branch <branch>       Git branch name (for feature environments)
#   --pr <number>           PR number (for feature environments)
#   --prefix <prefix>       Namespace prefix (default: mca)
#   --cleanup <days>        Days until cleanup for ephemeral environments (default: 7)
#   --dry-run               Show what would be done without making changes
#   --help                  Show this help message

set -eo pipefail

# Default values
ENV_TYPE=""
BRANCH_NAME=""
PR_NUMBER=""
NAMESPACE_PREFIX="mca"
CLEANUP_DAYS=7
DRY_RUN=false

# Colors for output
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --env-type <type>       Environment type: feature, development, staging, production"
    echo "  --branch <branch>       Git branch name (for feature environments)"
    echo "  --pr <number>           PR number (for feature environments)"
    echo "  --prefix <prefix>       Namespace prefix (default: mca)"
    echo "  --cleanup <days>        Days until cleanup for ephemeral environments (default: 7)"
    echo "  --dry-run               Show what would be done without making changes"
    echo "  --help                  Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --env-type feature --branch feature/add-email-service --prefix mca --cleanup 5"
    echo "  $0 --env-type development --prefix mca"
    echo "  $0 --env-type staging --prefix mca"
    echo "  $0 --env-type production --prefix mca"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --env-type)
            ENV_TYPE="$2"
            shift
            shift
            ;;
        --branch)
            BRANCH_NAME="$2"
            shift
            shift
            ;;
        --pr)
            PR_NUMBER="$2"
            shift
            shift
            ;;
        --prefix)
            NAMESPACE_PREFIX="$2"
            shift
            shift
            ;;
        --cleanup)
            CLEANUP_DAYS="$2"
            shift
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$ENV_TYPE" ]]; then
    log_error "Environment type is required. Use --env-type option."
    show_help
    exit 1
fi

# Validate environment type
if [[ "$ENV_TYPE" != "feature" && "$ENV_TYPE" != "development" && "$ENV_TYPE" != "staging" && "$ENV_TYPE" != "production" ]]; then
    log_error "Invalid environment type: $ENV_TYPE. Must be one of: feature, development, staging, production."
    show_help
    exit 1
fi

# For feature environments, either branch or PR is required
if [[ "$ENV_TYPE" == "feature" && -z "$BRANCH_NAME" && -z "$PR_NUMBER" ]]; then
    log_error "For feature environments, either branch name or PR number is required."
    show_help
    exit 1
fi

# Generate namespace name
generate_namespace_name() {
    local env_type=$1
    local branch_name=$2
    local pr_number=$3
    local prefix=$4
    
    if [[ "$env_type" == "feature" ]]; then
        if [[ -n "$pr_number" ]]; then
            # Use PR number if provided
            echo "${prefix}-pr-${pr_number}"
        else
            # Use branch name, sanitized for Kubernetes
            # Replace invalid characters with dashes and convert to lowercase
            local sanitized_branch=$(echo "$branch_name" | sed 's/[^a-zA-Z0-9]/-/g' | tr '[:upper:]' '[:lower:]')
            # Trim to 63 characters (Kubernetes limit) minus prefix length minus 1 for dash
            local max_length=$((63 - ${#prefix} - 1))
            sanitized_branch=${sanitized_branch:0:$max_length}
            echo "${prefix}-${sanitized_branch}"
        fi
    else
        # For standard environments, use the environment type
        echo "${prefix}-${env_type}"
    fi
}

# Check if namespace already exists
namespace_exists() {
    local namespace=$1
    kubectl get namespace "$namespace" &> /dev/null
    return $?
}

# Create namespace with labels and annotations
create_namespace() {
    local namespace=$1
    local env_type=$2
    local branch_name=$3
    local pr_number=$4
    local cleanup_days=$5
    
    local cmd="kubectl create namespace $namespace"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would execute: $cmd"
    else
        log_info "Creating namespace: $namespace"
        eval "$cmd"
        
        # Add labels
        kubectl label namespace "$namespace" "environment=$env_type" --overwrite
        kubectl label namespace "$namespace" "app.kubernetes.io/part-of=mca-application-system" --overwrite
        kubectl label namespace "$namespace" "app.kubernetes.io/managed-by=ci-cd" --overwrite
        
        # Add annotations
        kubectl annotate namespace "$namespace" "created-by=create-namespace-script" --overwrite
        kubectl annotate namespace "$namespace" "creation-timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")" --overwrite
        
        # For feature environments, add cleanup annotation
        if [[ "$env_type" == "feature" ]]; then
            local cleanup_date=$(date -u -d "+$cleanup_days days" +"%Y-%m-%dT%H:%M:%SZ")
            kubectl annotate namespace "$namespace" "cleanup-after=$cleanup_date" --overwrite
            
            # Add source information
            if [[ -n "$branch_name" ]]; then
                kubectl annotate namespace "$namespace" "source-branch=$branch_name" --overwrite
            fi
            if [[ -n "$pr_number" ]]; then
                kubectl annotate namespace "$namespace" "source-pr=$pr_number" --overwrite
            fi
        fi
        
        log_success "Namespace created successfully: $namespace"
    fi
}

# Apply resource quotas based on environment type
apply_resource_quotas() {
    local namespace=$1
    local env_type=$2
    
    log_info "Applying resource quotas for $env_type environment"
    
    local quota_file="/tmp/${namespace}-quota.yaml"
    
    # Create resource quota YAML based on environment type
    cat > "$quota_file" << EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ${namespace}-quota
  namespace: ${namespace}
spec:
  hard:
    # Compute Resources
EOF
    
    # Add environment-specific resource limits
    case "$env_type" in
        feature)
            cat >> "$quota_file" << EOF
    requests.cpu: "4"
    limits.cpu: "8"
    requests.memory: 8Gi
    limits.memory: 16Gi
    
    # GPU Resources (for OCR Service)
    requests.nvidia.com/gpu: "1"
    limits.nvidia.com/gpu: "1"
    
    # Storage Resources
    requests.storage: 50Gi
    persistentvolumeclaims: "10"
    
    # Object Count Limits
    pods: "30"
    services: "15"
    configmaps: "20"
    secrets: "20"
    
    # Load Balancer Limits
    services.loadbalancers: "1"
EOF
            ;;
        development)
            cat >> "$quota_file" << EOF
    requests.cpu: "8"
    limits.cpu: "16"
    requests.memory: 16Gi
    limits.memory: 32Gi
    
    # GPU Resources (for OCR Service)
    requests.nvidia.com/gpu: "1"
    limits.nvidia.com/gpu: "2"
    
    # Storage Resources
    requests.storage: 100Gi
    persistentvolumeclaims: "20"
    
    # Object Count Limits
    pods: "50"
    services: "20"
    configmaps: "30"
    secrets: "30"
    
    # Load Balancer Limits
    services.loadbalancers: "1"
EOF
            ;;
        staging)
            cat >> "$quota_file" << EOF
    requests.cpu: "16"
    limits.cpu: "32"
    requests.memory: 32Gi
    limits.memory: 64Gi
    
    # GPU Resources (for OCR Service)
    requests.nvidia.com/gpu: "2"
    limits.nvidia.com/gpu: "4"
    
    # Storage Resources
    requests.storage: 200Gi
    persistentvolumeclaims: "30"
    
    # Object Count Limits
    pods: "75"
    services: "30"
    configmaps: "40"
    secrets: "40"
    
    # Load Balancer Limits
    services.loadbalancers: "2"
EOF
            ;;
        production)
            cat >> "$quota_file" << EOF
    requests.cpu: "32"
    limits.cpu: "64"
    requests.memory: 64Gi
    limits.memory: 128Gi
    
    # GPU Resources (for OCR Service)
    requests.nvidia.com/gpu: "4"
    limits.nvidia.com/gpu: "8"
    
    # Storage Resources
    requests.storage: 500Gi
    persistentvolumeclaims: "50"
    
    # Object Count Limits
    pods: "100"
    services: "40"
    configmaps: "50"
    secrets: "50"
    
    # Load Balancer Limits
    services.loadbalancers: "3"
EOF
            
            # Add additional production-specific quotas
            cat >> "$quota_file" << EOF
---
# Priority Class Quota for Production
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ${namespace}-priority-quota
  namespace: ${namespace}
spec:
  hard:
    pods: "50"
  scopeSelector:
    matchExpressions:
    - operator: In
      scopeName: PriorityClass
      values: 
      - high-priority
      - critical-priority
---
# Storage Class Quota for Production
apiVersion: v1
kind: ResourceQuota
metadata:
  name: ${namespace}-storage-quota
  namespace: ${namespace}
spec:
  hard:
    ssd.storageclass.storage.k8s.io/requests.storage: 200Gi
    standard.storageclass.storage.k8s.io/requests.storage: 300Gi
EOF
            ;;
    esac
    
    # Apply the resource quota
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would apply resource quotas from: $quota_file"
        cat "$quota_file"
    else
        kubectl apply -f "$quota_file"
        log_success "Resource quotas applied successfully"
    fi
    
    # Clean up temporary file
    rm -f "$quota_file"
}

# Apply default network policies
apply_network_policies() {
    local namespace=$1
    
    log_info "Applying network policies for namespace: $namespace"
    
    local policy_file="/tmp/${namespace}-network-policy.yaml"
    
    # Create default deny-all policy
    cat > "$policy_file" << EOF
# Default Deny All Network Policy
# This policy ensures that any traffic not explicitly allowed by other policies is denied
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: ${namespace}
  labels:
    app.kubernetes.io/component: security
    app.kubernetes.io/part-of: mca-application-system
spec:
  podSelector: {}  # Selects all pods in the namespace
  policyTypes:
  - Ingress
  - Egress
  # No ingress or egress rules means all traffic is denied by default
---
# DNS Access Policy
# This policy allows all pods to access DNS services
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-access
  namespace: ${namespace}
  labels:
    app.kubernetes.io/component: security
    app.kubernetes.io/part-of: mca-application-system
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
EOF
    
    # Apply the network policies
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would apply network policies from: $policy_file"
        cat "$policy_file"
    else
        kubectl apply -f "$policy_file"
        log_success "Network policies applied successfully"
    fi
    
    # Clean up temporary file
    rm -f "$policy_file"
}

# Create service accounts and RBAC configuration
setup_rbac() {
    local namespace=$1
    local env_type=$2
    
    log_info "Setting up RBAC for namespace: $namespace"
    
    local rbac_file="/tmp/${namespace}-rbac.yaml"
    
    # Create service accounts for all microservices
    cat > "$rbac_file" << EOF
# Service Accounts for MCA Application Processing System
apiVersion: v1
kind: ServiceAccount
metadata:
  name: email-service
  namespace: ${namespace}
  labels:
    app: email-service
    environment: ${env_type}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: document-service
  namespace: ${namespace}
  labels:
    app: document-service
    environment: ${env_type}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ocr-service
  namespace: ${namespace}
  labels:
    app: ocr-service
    environment: ${env_type}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: data-service
  namespace: ${namespace}
  labels:
    app: data-service
    environment: ${env_type}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: notification-service
  namespace: ${namespace}
  labels:
    app: notification-service
    environment: ${env_type}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api-gateway
  namespace: ${namespace}
  labels:
    app: api-gateway
    environment: ${env_type}
---
# Default Role for all services
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: service-role
  namespace: ${namespace}
  labels:
    environment: ${env_type}
rules:
- apiGroups: [""] 
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
---
# Role Binding for all service accounts
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: service-role-binding
  namespace: ${namespace}
  labels:
    environment: ${env_type}
subjects:
- kind: ServiceAccount
  name: email-service
  namespace: ${namespace}
- kind: ServiceAccount
  name: document-service
  namespace: ${namespace}
- kind: ServiceAccount
  name: ocr-service
  namespace: ${namespace}
- kind: ServiceAccount
  name: data-service
  namespace: ${namespace}
- kind: ServiceAccount
  name: notification-service
  namespace: ${namespace}
- kind: ServiceAccount
  name: api-gateway
  namespace: ${namespace}
roleRef:
  kind: Role
  name: service-role
  apiGroup: rbac.authorization.k8s.io
EOF
    
    # Add environment-specific roles if needed
    if [[ "$env_type" == "production" || "$env_type" == "staging" ]]; then
        cat >> "$rbac_file" << EOF
---
# Operations Staff Role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: operations-staff
  namespace: ${namespace}
  labels:
    role: operations-staff
    environment: ${env_type}
rules:
- apiGroups: [""] # "" indicates the core API group
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""] 
  resources: ["pods/log"]
  verbs: ["get", "list"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""] 
  resources: ["secrets"]
  resourceNames: ["application-data-*"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
# System Admin Role
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: system-admin
  namespace: ${namespace}
  labels:
    role: system-admin
    environment: ${env_type}
rules:
- apiGroups: [""] # "" indicates the core API group
  resources: ["pods", "services", "configmaps", "secrets", "namespaces", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""] 
  resources: ["pods/log", "pods/exec"]
  verbs: ["get", "list", "create"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets", "replicasets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses", "networkpolicies"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["rbac.authorization.k8s.io"]
  resources: ["roles", "rolebindings"]
  verbs: ["get", "list", "watch"]
---
# Operations Staff RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: operations-staff-binding
  namespace: ${namespace}
  labels:
    role: operations-staff
    environment: ${env_type}
subjects:
- kind: Group
  name: operations-staff
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: operations-staff
  apiGroup: rbac.authorization.k8s.io
---
# System Admin RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: system-admin-binding
  namespace: ${namespace}
  labels:
    role: system-admin
    environment: ${env_type}
subjects:
- kind: Group
  name: system-admin
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: system-admin
  apiGroup: rbac.authorization.k8s.io
EOF
    fi
    
    # Apply the RBAC configuration
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would apply RBAC configuration from: $rbac_file"
        cat "$rbac_file"
    else
        kubectl apply -f "$rbac_file"
        log_success "RBAC configuration applied successfully"
    fi
    
    # Clean up temporary file
    rm -f "$rbac_file"
}

# Setup cleanup hooks for ephemeral environments
setup_cleanup_hooks() {
    local namespace=$1
    local cleanup_days=$2
    
    log_info "Setting up cleanup hooks for ephemeral environment: $namespace"
    
    # For feature environments, create a cleanup job
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would create cleanup job for namespace: $namespace after $cleanup_days days"
    else
        # Create a Kubernetes CronJob to check for namespaces that need cleanup
        # This is typically done at the cluster level, not per namespace
        # Here we're just setting the annotation that the cleanup job will look for
        local cleanup_date=$(date -u -d "+$cleanup_days days" +"%Y-%m-%dT%H:%M:%SZ")
        kubectl annotate namespace "$namespace" "cleanup-after=$cleanup_date" --overwrite
        log_success "Cleanup hook set for namespace: $namespace (cleanup after: $cleanup_date)"
    fi
}

# Main execution

# Generate the namespace name
NAMESPACE=$(generate_namespace_name "$ENV_TYPE" "$BRANCH_NAME" "$PR_NUMBER" "$NAMESPACE_PREFIX")
log_info "Generated namespace name: $NAMESPACE"

# Check if namespace already exists
if namespace_exists "$NAMESPACE"; then
    log_warning "Namespace already exists: $NAMESPACE"
    
    # For feature environments, we can update the cleanup date
    if [[ "$ENV_TYPE" == "feature" && "$DRY_RUN" != "true" ]]; then
        local cleanup_date=$(date -u -d "+$CLEANUP_DAYS days" +"%Y-%m-%dT%H:%M:%SZ")
        kubectl annotate namespace "$NAMESPACE" "cleanup-after=$cleanup_date" --overwrite
        log_info "Updated cleanup date for namespace: $NAMESPACE (cleanup after: $cleanup_date)"
    fi
else
    # Create the namespace
    create_namespace "$NAMESPACE" "$ENV_TYPE" "$BRANCH_NAME" "$PR_NUMBER" "$CLEANUP_DAYS"
    
    # Apply resource quotas
    apply_resource_quotas "$NAMESPACE" "$ENV_TYPE"
    
    # Apply network policies
    apply_network_policies "$NAMESPACE"
    
    # Setup RBAC
    setup_rbac "$NAMESPACE" "$ENV_TYPE"
    
    # For feature environments, setup cleanup hooks
    if [[ "$ENV_TYPE" == "feature" ]]; then
        setup_cleanup_hooks "$NAMESPACE" "$CLEANUP_DAYS"
    fi
fi

# Output the namespace name for use in subsequent steps
echo "NAMESPACE=$NAMESPACE"

log_success "Namespace setup completed successfully: $NAMESPACE"
exit 0