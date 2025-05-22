# RBAC (Role-Based Access Control) configuration for the MCA Application Processing System
# This file defines service accounts, roles, role bindings, cluster roles, and cluster role bindings
# to implement the principle of least privilege for all microservices and supporting systems.

# ---------------------------------------------------------------------------------------------------------------------
# VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

variable "service_account_annotations" {
  description = "Map of annotations to add to all service accounts"
  type        = map(string)
  default     = {}
}

variable "enable_pod_security_policies" {
  description = "Whether to enable Pod Security Policies"
  type        = bool
  default     = true
}

variable "enable_ci_cd_rbac" {
  description = "Whether to create RBAC resources for CI/CD systems"
  type        = bool
  default     = true
}

variable "ci_cd_namespace" {
  description = "Namespace for CI/CD resources"
  type        = string
  default     = "ci-cd"
}

variable "monitoring_namespace" {
  description = "Namespace for monitoring resources"
  type        = string
  default     = "monitoring"
}

variable "logging_namespace" {
  description = "Namespace for logging resources"
  type        = string
  default     = "logging"
}

# ---------------------------------------------------------------------------------------------------------------------
# SERVICE ACCOUNTS
# ---------------------------------------------------------------------------------------------------------------------

# Email Service Service Account
resource "kubernetes_service_account" "email_service" {
  metadata {
    name      = "email-service"
    namespace = "email-service"
    annotations = merge(
      var.service_account_annotations,
      {
        "description" = "Service account for the Email Service"
      }
    )
    labels = {
      "app.kubernetes.io/name"       = "email-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  automount_service_account_token = true
}

# Document Service Service Account
resource "kubernetes_service_account" "document_service" {
  metadata {
    name      = "document-service"
    namespace = "document-service"
    annotations = merge(
      var.service_account_annotations,
      {
        "description" = "Service account for the Document Service"
      }
    )
    labels = {
      "app.kubernetes.io/name"       = "document-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  automount_service_account_token = true
}

# OCR Service Service Account
resource "kubernetes_service_account" "ocr_service" {
  metadata {
    name      = "ocr-service"
    namespace = "ocr-service"
    annotations = merge(
      var.service_account_annotations,
      {
        "description" = "Service account for the OCR Service"
      }
    )
    labels = {
      "app.kubernetes.io/name"       = "ocr-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  automount_service_account_token = true
}

# Data Service Service Account
resource "kubernetes_service_account" "data_service" {
  metadata {
    name      = "data-service"
    namespace = "data-service"
    annotations = merge(
      var.service_account_annotations,
      {
        "description" = "Service account for the Data Service"
      }
    )
    labels = {
      "app.kubernetes.io/name"       = "data-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  automount_service_account_token = true
}

# Notification Service Service Account
resource "kubernetes_service_account" "notification_service" {
  metadata {
    name      = "notification-service"
    namespace = "notification-service"
    annotations = merge(
      var.service_account_annotations,
      {
        "description" = "Service account for the Notification Service"
      }
    )
    labels = {
      "app.kubernetes.io/name"       = "notification-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  automount_service_account_token = true
}

# API Gateway Service Account
resource "kubernetes_service_account" "api_gateway" {
  metadata {
    name      = "api-gateway"
    namespace = "api-gateway"
    annotations = merge(
      var.service_account_annotations,
      {
        "description" = "Service account for the API Gateway (Kong)"
      }
    )
    labels = {
      "app.kubernetes.io/name"       = "api-gateway"
      "app.kubernetes.io/component"  = "gateway"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  automount_service_account_token = true
}

# ---------------------------------------------------------------------------------------------------------------------
# ROLES AND ROLE BINDINGS FOR MICROSERVICES
# ---------------------------------------------------------------------------------------------------------------------

# Email Service Role
resource "kubernetes_role" "email_service" {
  metadata {
    name      = "email-service-role"
    namespace = "email-service"
    labels = {
      "app.kubernetes.io/name"       = "email-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  # Allow reading ConfigMaps for configuration
  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading Secrets for credentials
  rule {
    api_groups = [""]
    resources  = ["secrets"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow managing pods for self-healing
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow creating events for logging
  rule {
    api_groups = [""]
    resources  = ["events"]
    verbs      = ["create", "patch", "update"]
  }
}

# Email Service Role Binding
resource "kubernetes_role_binding" "email_service" {
  metadata {
    name      = "email-service-rolebinding"
    namespace = "email-service"
    labels = {
      "app.kubernetes.io/name"       = "email-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.email_service.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.email_service.metadata[0].name
    namespace = "email-service"
  }
}

# Document Service Role
resource "kubernetes_role" "document_service" {
  metadata {
    name      = "document-service-role"
    namespace = "document-service"
    labels = {
      "app.kubernetes.io/name"       = "document-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  # Allow reading ConfigMaps for configuration
  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading Secrets for credentials
  rule {
    api_groups = [""]
    resources  = ["secrets"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow managing pods for self-healing
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow creating events for logging
  rule {
    api_groups = [""]
    resources  = ["events"]
    verbs      = ["create", "patch", "update"]
  }
}

# Document Service Role Binding
resource "kubernetes_role_binding" "document_service" {
  metadata {
    name      = "document-service-rolebinding"
    namespace = "document-service"
    labels = {
      "app.kubernetes.io/name"       = "document-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.document_service.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.document_service.metadata[0].name
    namespace = "document-service"
  }
}

# OCR Service Role
resource "kubernetes_role" "ocr_service" {
  metadata {
    name      = "ocr-service-role"
    namespace = "ocr-service"
    labels = {
      "app.kubernetes.io/name"       = "ocr-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  # Allow reading ConfigMaps for configuration
  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading Secrets for credentials
  rule {
    api_groups = [""]
    resources  = ["secrets"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow managing pods for self-healing
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow creating events for logging
  rule {
    api_groups = [""]
    resources  = ["events"]
    verbs      = ["create", "patch", "update"]
  }

  # Allow managing GPU resources
  rule {
    api_groups = [""]
    resources  = ["pods/status"]
    verbs      = ["get", "update", "patch"]
  }
}

# OCR Service Role Binding
resource "kubernetes_role_binding" "ocr_service" {
  metadata {
    name      = "ocr-service-rolebinding"
    namespace = "ocr-service"
    labels = {
      "app.kubernetes.io/name"       = "ocr-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.ocr_service.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.ocr_service.metadata[0].name
    namespace = "ocr-service"
  }
}

# Data Service Role
resource "kubernetes_role" "data_service" {
  metadata {
    name      = "data-service-role"
    namespace = "data-service"
    labels = {
      "app.kubernetes.io/name"       = "data-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  # Allow reading ConfigMaps for configuration
  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading Secrets for credentials
  rule {
    api_groups = [""]
    resources  = ["secrets"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow managing pods for self-healing
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow creating events for logging
  rule {
    api_groups = [""]
    resources  = ["events"]
    verbs      = ["create", "patch", "update"]
  }
}

# Data Service Role Binding
resource "kubernetes_role_binding" "data_service" {
  metadata {
    name      = "data-service-rolebinding"
    namespace = "data-service"
    labels = {
      "app.kubernetes.io/name"       = "data-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.data_service.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.data_service.metadata[0].name
    namespace = "data-service"
  }
}

# Notification Service Role
resource "kubernetes_role" "notification_service" {
  metadata {
    name      = "notification-service-role"
    namespace = "notification-service"
    labels = {
      "app.kubernetes.io/name"       = "notification-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  # Allow reading ConfigMaps for configuration
  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading Secrets for credentials
  rule {
    api_groups = [""]
    resources  = ["secrets"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow managing pods for self-healing
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow creating events for logging
  rule {
    api_groups = [""]
    resources  = ["events"]
    verbs      = ["create", "patch", "update"]
  }
}

# Notification Service Role Binding
resource "kubernetes_role_binding" "notification_service" {
  metadata {
    name      = "notification-service-rolebinding"
    namespace = "notification-service"
    labels = {
      "app.kubernetes.io/name"       = "notification-service"
      "app.kubernetes.io/component"  = "microservice"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.notification_service.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.notification_service.metadata[0].name
    namespace = "notification-service"
  }
}

# API Gateway Role
resource "kubernetes_role" "api_gateway" {
  metadata {
    name      = "api-gateway-role"
    namespace = "api-gateway"
    labels = {
      "app.kubernetes.io/name"       = "api-gateway"
      "app.kubernetes.io/component"  = "gateway"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  # Allow reading ConfigMaps for configuration
  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading Secrets for credentials and certificates
  rule {
    api_groups = [""]
    resources  = ["secrets"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow managing pods for self-healing
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow creating events for logging
  rule {
    api_groups = [""]
    resources  = ["events"]
    verbs      = ["create", "patch", "update"]
  }

  # Allow managing services for dynamic routing
  rule {
    api_groups = [""]
    resources  = ["services"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow managing endpoints for service discovery
  rule {
    api_groups = [""]
    resources  = ["endpoints"]
    verbs      = ["get", "list", "watch"]
  }
}

# API Gateway Role Binding
resource "kubernetes_role_binding" "api_gateway" {
  metadata {
    name      = "api-gateway-rolebinding"
    namespace = "api-gateway"
    labels = {
      "app.kubernetes.io/name"       = "api-gateway"
      "app.kubernetes.io/component"  = "gateway"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.api_gateway.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.api_gateway.metadata[0].name
    namespace = "api-gateway"
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# CLUSTER ROLES AND CLUSTER ROLE BINDINGS
# ---------------------------------------------------------------------------------------------------------------------

# API Gateway Cluster Role for cross-namespace service discovery
resource "kubernetes_cluster_role" "api_gateway_discovery" {
  metadata {
    name = "api-gateway-discovery"
    labels = {
      "app.kubernetes.io/name"       = "api-gateway"
      "app.kubernetes.io/component"  = "gateway"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  # Allow reading services across all namespaces
  rule {
    api_groups = [""]
    resources  = ["services"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading endpoints across all namespaces
  rule {
    api_groups = [""]
    resources  = ["endpoints"]
    verbs      = ["get", "list", "watch"]
  }
}

# API Gateway Cluster Role Binding
resource "kubernetes_cluster_role_binding" "api_gateway_discovery" {
  metadata {
    name = "api-gateway-discovery-binding"
    labels = {
      "app.kubernetes.io/name"       = "api-gateway"
      "app.kubernetes.io/component"  = "gateway"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.api_gateway_discovery.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.api_gateway.metadata[0].name
    namespace = "api-gateway"
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# CI/CD RBAC CONFIGURATION
# ---------------------------------------------------------------------------------------------------------------------

# CI/CD Service Account
resource "kubernetes_service_account" "ci_cd" {
  count = var.enable_ci_cd_rbac ? 1 : 0
  
  metadata {
    name      = "ci-cd-deployer"
    namespace = var.ci_cd_namespace
    annotations = merge(
      var.service_account_annotations,
      {
        "description" = "Service account for CI/CD deployment pipelines"
      }
    )
    labels = {
      "app.kubernetes.io/name"       = "ci-cd"
      "app.kubernetes.io/component"  = "deployment"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  automount_service_account_token = true
}

# CI/CD Cluster Role
resource "kubernetes_cluster_role" "ci_cd" {
  count = var.enable_ci_cd_rbac ? 1 : 0
  
  metadata {
    name = "ci-cd-deployer-role"
    labels = {
      "app.kubernetes.io/name"       = "ci-cd"
      "app.kubernetes.io/component"  = "deployment"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  # Allow managing deployments
  rule {
    api_groups = ["apps"]
    resources  = ["deployments"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Allow managing services
  rule {
    api_groups = [""]
    resources  = ["services"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Allow managing configmaps
  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Allow managing secrets
  rule {
    api_groups = [""]
    resources  = ["secrets"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Allow managing pods
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Allow managing ingresses
  rule {
    api_groups = ["networking.k8s.io"]
    resources  = ["ingresses"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Allow managing statefulsets
  rule {
    api_groups = ["apps"]
    resources  = ["statefulsets"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Allow managing daemonsets
  rule {
    api_groups = ["apps"]
    resources  = ["daemonsets"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Allow managing jobs and cronjobs
  rule {
    api_groups = ["batch"]
    resources  = ["jobs", "cronjobs"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Allow managing horizontal pod autoscalers
  rule {
    api_groups = ["autoscaling"]
    resources  = ["horizontalpodautoscalers"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }
}

# CI/CD Cluster Role Binding
resource "kubernetes_cluster_role_binding" "ci_cd" {
  count = var.enable_ci_cd_rbac ? 1 : 0
  
  metadata {
    name = "ci-cd-deployer-binding"
    labels = {
      "app.kubernetes.io/name"       = "ci-cd"
      "app.kubernetes.io/component"  = "deployment"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.ci_cd[0].metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.ci_cd[0].metadata[0].name
    namespace = var.ci_cd_namespace
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# MONITORING AND LOGGING RBAC CONFIGURATION
# ---------------------------------------------------------------------------------------------------------------------

# Monitoring Service Account
resource "kubernetes_service_account" "monitoring" {
  metadata {
    name      = "monitoring"
    namespace = var.monitoring_namespace
    annotations = merge(
      var.service_account_annotations,
      {
        "description" = "Service account for monitoring systems (Prometheus, Grafana, etc.)"
      }
    )
    labels = {
      "app.kubernetes.io/name"       = "monitoring"
      "app.kubernetes.io/component"  = "observability"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  automount_service_account_token = true
}

# Monitoring Cluster Role
resource "kubernetes_cluster_role" "monitoring" {
  metadata {
    name = "monitoring-role"
    labels = {
      "app.kubernetes.io/name"       = "monitoring"
      "app.kubernetes.io/component"  = "observability"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  # Allow reading pods for metrics collection
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading services for service discovery
  rule {
    api_groups = [""]
    resources  = ["services"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading endpoints for service discovery
  rule {
    api_groups = [""]
    resources  = ["endpoints"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading nodes for cluster metrics
  rule {
    api_groups = [""]
    resources  = ["nodes"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading namespaces for discovery
  rule {
    api_groups = [""]
    resources  = ["namespaces"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading pod metrics
  rule {
    api_groups = ["metrics.k8s.io"]
    resources  = ["pods", "nodes"]
    verbs      = ["get", "list", "watch"]
  }
}

# Monitoring Cluster Role Binding
resource "kubernetes_cluster_role_binding" "monitoring" {
  metadata {
    name = "monitoring-binding"
    labels = {
      "app.kubernetes.io/name"       = "monitoring"
      "app.kubernetes.io/component"  = "observability"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.monitoring.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.monitoring.metadata[0].name
    namespace = var.monitoring_namespace
  }
}

# Logging Service Account
resource "kubernetes_service_account" "logging" {
  metadata {
    name      = "logging"
    namespace = var.logging_namespace
    annotations = merge(
      var.service_account_annotations,
      {
        "description" = "Service account for logging systems (Fluentd, Elasticsearch, etc.)"
      }
    )
    labels = {
      "app.kubernetes.io/name"       = "logging"
      "app.kubernetes.io/component"  = "observability"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  automount_service_account_token = true
}

# Logging Cluster Role
resource "kubernetes_cluster_role" "logging" {
  metadata {
    name = "logging-role"
    labels = {
      "app.kubernetes.io/name"       = "logging"
      "app.kubernetes.io/component"  = "observability"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }

  # Allow reading pods for log collection
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading pod logs
  rule {
    api_groups = [""]
    resources  = ["pods/log"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading namespaces for discovery
  rule {
    api_groups = [""]
    resources  = ["namespaces"]
    verbs      = ["get", "list", "watch"]
  }

  # Allow reading nodes for node-level logging
  rule {
    api_groups = [""]
    resources  = ["nodes"]
    verbs      = ["get", "list", "watch"]
  }
}

# Logging Cluster Role Binding
resource "kubernetes_cluster_role_binding" "logging" {
  metadata {
    name = "logging-binding"
    labels = {
      "app.kubernetes.io/name"       = "logging"
      "app.kubernetes.io/component"  = "observability"
      "app.kubernetes.io/part-of"    = "mca-application-system"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.logging.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.logging.metadata[0].name
    namespace = var.logging_namespace
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------------------------------------------------

output "service_account_names" {
  description = "Names of the service accounts created"
  value = {
    email_service       = kubernetes_service_account.email_service.metadata[0].name
    document_service    = kubernetes_service_account.document_service.metadata[0].name
    ocr_service         = kubernetes_service_account.ocr_service.metadata[0].name
    data_service        = kubernetes_service_account.data_service.metadata[0].name
    notification_service = kubernetes_service_account.notification_service.metadata[0].name
    api_gateway         = kubernetes_service_account.api_gateway.metadata[0].name
    monitoring          = kubernetes_service_account.monitoring.metadata[0].name
    logging             = kubernetes_service_account.logging.metadata[0].name
    ci_cd               = var.enable_ci_cd_rbac ? kubernetes_service_account.ci_cd[0].metadata[0].name : null
  }
}

output "role_names" {
  description = "Names of the roles created"
  value = {
    email_service       = kubernetes_role.email_service.metadata[0].name
    document_service    = kubernetes_role.document_service.metadata[0].name
    ocr_service         = kubernetes_role.ocr_service.metadata[0].name
    data_service        = kubernetes_role.data_service.metadata[0].name
    notification_service = kubernetes_role.notification_service.metadata[0].name
    api_gateway         = kubernetes_role.api_gateway.metadata[0].name
  }
}

output "cluster_role_names" {
  description = "Names of the cluster roles created"
  value = {
    api_gateway_discovery = kubernetes_cluster_role.api_gateway_discovery.metadata[0].name
    monitoring           = kubernetes_cluster_role.monitoring.metadata[0].name
    logging              = kubernetes_cluster_role.logging.metadata[0].name
    ci_cd               = var.enable_ci_cd_rbac ? kubernetes_cluster_role.ci_cd[0].metadata[0].name : null
  }
}