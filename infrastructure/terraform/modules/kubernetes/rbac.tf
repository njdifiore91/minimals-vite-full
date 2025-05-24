# Role-Based Access Control (RBAC) for Kubernetes
# This file defines service accounts, roles, and role bindings for the MCA Application Processing System
# It implements the principle of least privilege, ensuring services have only the permissions they need

# ---------------------------------------------------------------------------------------------------------------------
# Service Accounts for each microservice
# ---------------------------------------------------------------------------------------------------------------------

# Email Service Service Account
resource "kubernetes_service_account" "email_service" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "email-service"
    namespace = each.key
    labels = {
      app         = "email-service"
      environment = each.key
    }
    annotations = var.cloud_provider == "aws" ? {
      "eks.amazonaws.com/role-arn" = "arn:aws:iam::${var.aws_account_id}:role/${each.key}-email-service"
    } : var.cloud_provider == "azure" ? {
      "azure.workload.identity/client-id" = "${each.key}-email-service"
    } : var.cloud_provider == "gcp" ? {
      "iam.gke.io/gcp-service-account" = "${each.key}-email-service@${var.gcp_project_id}.iam.gserviceaccount.com"
    } : {}
  }

  automount_service_account_token = true
}

# Document Service Service Account
resource "kubernetes_service_account" "document_service" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "document-service"
    namespace = each.key
    labels = {
      app         = "document-service"
      environment = each.key
    }
    annotations = var.cloud_provider == "aws" ? {
      "eks.amazonaws.com/role-arn" = "arn:aws:iam::${var.aws_account_id}:role/${each.key}-document-service"
    } : var.cloud_provider == "azure" ? {
      "azure.workload.identity/client-id" = "${each.key}-document-service"
    } : var.cloud_provider == "gcp" ? {
      "iam.gke.io/gcp-service-account" = "${each.key}-document-service@${var.gcp_project_id}.iam.gserviceaccount.com"
    } : {}
  }

  automount_service_account_token = true
}

# OCR Service Service Account
resource "kubernetes_service_account" "ocr_service" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "ocr-service"
    namespace = each.key
    labels = {
      app         = "ocr-service"
      environment = each.key
    }
    annotations = var.cloud_provider == "aws" ? {
      "eks.amazonaws.com/role-arn" = "arn:aws:iam::${var.aws_account_id}:role/${each.key}-ocr-service"
    } : var.cloud_provider == "azure" ? {
      "azure.workload.identity/client-id" = "${each.key}-ocr-service"
    } : var.cloud_provider == "gcp" ? {
      "iam.gke.io/gcp-service-account" = "${each.key}-ocr-service@${var.gcp_project_id}.iam.gserviceaccount.com"
    } : {}
  }

  automount_service_account_token = true
}

# Data Service Service Account
resource "kubernetes_service_account" "data_service" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "data-service"
    namespace = each.key
    labels = {
      app         = "data-service"
      environment = each.key
    }
    annotations = var.cloud_provider == "aws" ? {
      "eks.amazonaws.com/role-arn" = "arn:aws:iam::${var.aws_account_id}:role/${each.key}-data-service"
    } : var.cloud_provider == "azure" ? {
      "azure.workload.identity/client-id" = "${each.key}-data-service"
    } : var.cloud_provider == "gcp" ? {
      "iam.gke.io/gcp-service-account" = "${each.key}-data-service@${var.gcp_project_id}.iam.gserviceaccount.com"
    } : {}
  }

  automount_service_account_token = true
}

# Notification Service Service Account
resource "kubernetes_service_account" "notification_service" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "notification-service"
    namespace = each.key
    labels = {
      app         = "notification-service"
      environment = each.key
    }
    annotations = var.cloud_provider == "aws" ? {
      "eks.amazonaws.com/role-arn" = "arn:aws:iam::${var.aws_account_id}:role/${each.key}-notification-service"
    } : var.cloud_provider == "azure" ? {
      "azure.workload.identity/client-id" = "${each.key}-notification-service"
    } : var.cloud_provider == "gcp" ? {
      "iam.gke.io/gcp-service-account" = "${each.key}-notification-service@${var.gcp_project_id}.iam.gserviceaccount.com"
    } : {}
  }

  automount_service_account_token = true
}

# API Gateway Service Account
resource "kubernetes_service_account" "api_gateway" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "api-gateway"
    namespace = each.key
    labels = {
      app         = "api-gateway"
      environment = each.key
    }
    annotations = var.cloud_provider == "aws" ? {
      "eks.amazonaws.com/role-arn" = "arn:aws:iam::${var.aws_account_id}:role/${each.key}-api-gateway"
    } : var.cloud_provider == "azure" ? {
      "azure.workload.identity/client-id" = "${each.key}-api-gateway"
    } : var.cloud_provider == "gcp" ? {
      "iam.gke.io/gcp-service-account" = "${each.key}-api-gateway@${var.gcp_project_id}.iam.gserviceaccount.com"
    } : {}
  }

  automount_service_account_token = true
}

# CI/CD Service Account for deployments
resource "kubernetes_service_account" "cicd" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "cicd-deployer"
    namespace = each.key
    labels = {
      app         = "cicd"
      environment = each.key
    }
    annotations = var.cloud_provider == "aws" ? {
      "eks.amazonaws.com/role-arn" = "arn:aws:iam::${var.aws_account_id}:role/${each.key}-cicd-deployer"
    } : var.cloud_provider == "azure" ? {
      "azure.workload.identity/client-id" = "${each.key}-cicd-deployer"
    } : var.cloud_provider == "gcp" ? {
      "iam.gke.io/gcp-service-account" = "${each.key}-cicd-deployer@${var.gcp_project_id}.iam.gserviceaccount.com"
    } : {}
  }

  automount_service_account_token = true
}

# ---------------------------------------------------------------------------------------------------------------------
# Roles for user access
# ---------------------------------------------------------------------------------------------------------------------

# Operations Staff Role
resource "kubernetes_role" "operations_staff" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "operations-staff"
    namespace = each.key
    labels = {
      role        = "operations-staff"
      environment = each.key
    }
  }

  # Read access to most resources
  rule {
    api_groups = [""]
    resources  = ["pods", "services", "configmaps"]
    verbs      = ["get", "list", "watch"]
  }

  # Access to pod logs
  rule {
    api_groups = [""]
    resources  = ["pods/log"]
    verbs      = ["get", "list"]
  }

  # Read access to deployments and statefulsets
  rule {
    api_groups = ["apps"]
    resources  = ["deployments", "statefulsets"]
    verbs      = ["get", "list", "watch"]
  }

  # Read access to jobs and cronjobs
  rule {
    api_groups = ["batch"]
    resources  = ["jobs", "cronjobs"]
    verbs      = ["get", "list", "watch"]
  }

  # Full access to application data secrets
  rule {
    api_groups     = [""]
    resources      = ["secrets"]
    resource_names = ["application-data-*"]
    verbs          = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }
}

# System Admin Role
resource "kubernetes_role" "system_admin" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "system-admin"
    namespace = each.key
    labels = {
      role        = "system-admin"
      environment = each.key
    }
  }

  # Full access to most resources
  rule {
    api_groups = [""]
    resources  = ["pods", "services", "configmaps", "secrets", "namespaces", "persistentvolumeclaims"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Access to pod logs and exec
  rule {
    api_groups = [""]
    resources  = ["pods/log", "pods/exec"]
    verbs      = ["get", "list", "create"]
  }

  # Full access to deployments, statefulsets, daemonsets, replicasets
  rule {
    api_groups = ["apps"]
    resources  = ["deployments", "statefulsets", "daemonsets", "replicasets"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Full access to jobs and cronjobs
  rule {
    api_groups = ["batch"]
    resources  = ["jobs", "cronjobs"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Full access to ingresses and network policies
  rule {
    api_groups = ["networking.k8s.io"]
    resources  = ["ingresses", "networkpolicies"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Read access to roles and role bindings
  rule {
    api_groups = ["rbac.authorization.k8s.io"]
    resources  = ["roles", "rolebindings"]
    verbs      = ["get", "list", "watch"]
  }
}

# CI/CD Deployer Role
resource "kubernetes_role" "cicd_deployer" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "cicd-deployer"
    namespace = each.key
    labels = {
      role        = "cicd-deployer"
      environment = each.key
    }
  }

  # Access to resources needed for deployments
  rule {
    api_groups = [""]
    resources  = ["pods", "services", "configmaps", "secrets"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Access to deployments, statefulsets, daemonsets, replicasets
  rule {
    api_groups = ["apps"]
    resources  = ["deployments", "statefulsets", "daemonsets", "replicasets"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Access to jobs and cronjobs
  rule {
    api_groups = ["batch"]
    resources  = ["jobs", "cronjobs"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }

  # Access to ingresses
  rule {
    api_groups = ["networking.k8s.io"]
    resources  = ["ingresses"]
    verbs      = ["get", "list", "watch", "create", "update", "patch", "delete"]
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Service-specific roles with least privilege principle
# ---------------------------------------------------------------------------------------------------------------------

# Email Service Role
resource "kubernetes_role" "email_service_role" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "email-service-role"
    namespace = each.key
    labels = {
      app         = "email-service"
      environment = each.key
    }
  }

  # Access to specific configmaps
  rule {
    api_groups     = [""]
    resources      = ["configmaps"]
    resource_names = ["email-service-config", "email-credentials"]
    verbs          = ["get", "list", "watch"]
  }

  # Access to specific secrets
  rule {
    api_groups     = [""]
    resources      = ["secrets"]
    resource_names = ["email-service-secrets", "rabbitmq-credentials"]
    verbs          = ["get", "list", "watch"]
  }
}

# Document Service Role
resource "kubernetes_role" "document_service_role" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "document-service-role"
    namespace = each.key
    labels = {
      app         = "document-service"
      environment = each.key
    }
  }

  # Access to specific configmaps
  rule {
    api_groups     = [""]
    resources      = ["configmaps"]
    resource_names = ["document-service-config", "document-classification-config"]
    verbs          = ["get", "list", "watch"]
  }

  # Access to specific secrets
  rule {
    api_groups     = [""]
    resources      = ["secrets"]
    resource_names = ["document-service-secrets", "rabbitmq-credentials", "s3-credentials"]
    verbs          = ["get", "list", "watch"]
  }
}

# OCR Service Role
resource "kubernetes_role" "ocr_service_role" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "ocr-service-role"
    namespace = each.key
    labels = {
      app         = "ocr-service"
      environment = each.key
    }
  }

  # Access to specific configmaps
  rule {
    api_groups     = [""]
    resources      = ["configmaps"]
    resource_names = ["ocr-service-config", "ocr-models-config"]
    verbs          = ["get", "list", "watch"]
  }

  # Access to specific secrets
  rule {
    api_groups     = [""]
    resources      = ["secrets"]
    resource_names = ["ocr-service-secrets", "rabbitmq-credentials", "s3-credentials"]
    verbs          = ["get", "list", "watch"]
  }
}

# Data Service Role
resource "kubernetes_role" "data_service_role" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "data-service-role"
    namespace = each.key
    labels = {
      app         = "data-service"
      environment = each.key
    }
  }

  # Access to specific configmaps
  rule {
    api_groups     = [""]
    resources      = ["configmaps"]
    resource_names = ["data-service-config", "database-config"]
    verbs          = ["get", "list", "watch"]
  }

  # Access to specific secrets
  rule {
    api_groups     = [""]
    resources      = ["secrets"]
    resource_names = ["data-service-secrets", "rabbitmq-credentials", "database-credentials", "redis-credentials"]
    verbs          = ["get", "list", "watch"]
  }
}

# Notification Service Role
resource "kubernetes_role" "notification_service_role" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "notification-service-role"
    namespace = each.key
    labels = {
      app         = "notification-service"
      environment = each.key
    }
  }

  # Access to specific configmaps
  rule {
    api_groups     = [""]
    resources      = ["configmaps"]
    resource_names = ["notification-service-config", "webhook-config"]
    verbs          = ["get", "list", "watch"]
  }

  # Access to specific secrets
  rule {
    api_groups     = [""]
    resources      = ["secrets"]
    resource_names = ["notification-service-secrets", "rabbitmq-credentials", "webhook-credentials"]
    verbs          = ["get", "list", "watch"]
  }
}

# API Gateway Role
resource "kubernetes_role" "api_gateway_role" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "api-gateway-role"
    namespace = each.key
    labels = {
      app         = "api-gateway"
      environment = each.key
    }
  }

  # Access to specific configmaps
  rule {
    api_groups     = [""]
    resources      = ["configmaps"]
    resource_names = ["api-gateway-config", "jwt-config", "cors-config"]
    verbs          = ["get", "list", "watch"]
  }

  # Access to specific secrets
  rule {
    api_groups     = [""]
    resources      = ["secrets"]
    resource_names = ["api-gateway-secrets", "jwt-keys"]
    verbs          = ["get", "list", "watch"]
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# Role Bindings for service accounts
# ---------------------------------------------------------------------------------------------------------------------

# Email Service Role Bindings
resource "kubernetes_role_binding" "email_service_binding" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "email-service-binding"
    namespace = each.key
    labels = {
      app         = "email-service"
      environment = each.key
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = "email-service-role"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "email-service"
    namespace = each.key
  }

  depends_on = [
    kubernetes_service_account.email_service,
    kubernetes_role.email_service_role
  ]
}

# Document Service Role Bindings
resource "kubernetes_role_binding" "document_service_binding" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "document-service-binding"
    namespace = each.key
    labels = {
      app         = "document-service"
      environment = each.key
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = "document-service-role"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "document-service"
    namespace = each.key
  }

  depends_on = [
    kubernetes_service_account.document_service,
    kubernetes_role.document_service_role
  ]
}

# OCR Service Role Bindings
resource "kubernetes_role_binding" "ocr_service_binding" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "ocr-service-binding"
    namespace = each.key
    labels = {
      app         = "ocr-service"
      environment = each.key
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = "ocr-service-role"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "ocr-service"
    namespace = each.key
  }

  depends_on = [
    kubernetes_service_account.ocr_service,
    kubernetes_role.ocr_service_role
  ]
}

# Data Service Role Bindings
resource "kubernetes_role_binding" "data_service_binding" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "data-service-binding"
    namespace = each.key
    labels = {
      app         = "data-service"
      environment = each.key
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = "data-service-role"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "data-service"
    namespace = each.key
  }

  depends_on = [
    kubernetes_service_account.data_service,
    kubernetes_role.data_service_role
  ]
}

# Notification Service Role Bindings
resource "kubernetes_role_binding" "notification_service_binding" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "notification-service-binding"
    namespace = each.key
    labels = {
      app         = "notification-service"
      environment = each.key
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = "notification-service-role"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "notification-service"
    namespace = each.key
  }

  depends_on = [
    kubernetes_service_account.notification_service,
    kubernetes_role.notification_service_role
  ]
}

# API Gateway Role Bindings
resource "kubernetes_role_binding" "api_gateway_binding" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "api-gateway-binding"
    namespace = each.key
    labels = {
      app         = "api-gateway"
      environment = each.key
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = "api-gateway-role"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "api-gateway"
    namespace = each.key
  }

  depends_on = [
    kubernetes_service_account.api_gateway,
    kubernetes_role.api_gateway_role
  ]
}

# CI/CD Deployer Role Bindings
resource "kubernetes_role_binding" "cicd_deployer_binding" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "cicd-deployer-binding"
    namespace = each.key
    labels = {
      role        = "cicd-deployer"
      environment = each.key
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = "cicd-deployer"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "cicd-deployer"
    namespace = each.key
  }

  depends_on = [
    kubernetes_service_account.cicd,
    kubernetes_role.cicd_deployer
  ]
}

# ---------------------------------------------------------------------------------------------------------------------
# User Role Bindings
# ---------------------------------------------------------------------------------------------------------------------

# Operations Staff Role Bindings
resource "kubernetes_role_binding" "operations_staff_binding" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "operations-staff-binding"
    namespace = each.key
    labels = {
      role        = "operations-staff"
      environment = each.key
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = "operations-staff"
  }

  subject {
    kind     = "Group"
    name     = "operations-staff"
    api_group = "rbac.authorization.k8s.io"
  }

  depends_on = [
    kubernetes_role.operations_staff
  ]
}

# System Admin Role Bindings
resource "kubernetes_role_binding" "system_admin_binding" {
  for_each = toset(["development", "staging", "production"])

  metadata {
    name      = "system-admin-binding"
    namespace = each.key
    labels = {
      role        = "system-admin"
      environment = each.key
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = "system-admin"
  }

  subject {
    kind     = "Group"
    name     = "system-admin"
    api_group = "rbac.authorization.k8s.io"
  }

  depends_on = [
    kubernetes_role.system_admin
  ]
}

# ---------------------------------------------------------------------------------------------------------------------
# Cluster-wide roles for monitoring and logging
# ---------------------------------------------------------------------------------------------------------------------

# Monitoring Role
resource "kubernetes_cluster_role" "monitoring" {
  metadata {
    name = "monitoring-role"
    labels = {
      role = "monitoring"
    }
  }

  # Access to metrics and health endpoints
  rule {
    api_groups = [""]
    resources  = ["pods", "nodes", "services", "endpoints"]
    verbs      = ["get", "list", "watch"]
  }

  # Access to custom metrics
  rule {
    api_groups = ["metrics.k8s.io"]
    resources  = ["pods", "nodes"]
    verbs      = ["get", "list", "watch"]
  }

  # Access to Prometheus resources if using Prometheus Operator
  rule {
    api_groups = ["monitoring.coreos.com"]
    resources  = ["servicemonitors", "podmonitors", "prometheusrules"]
    verbs      = ["get", "list", "watch"]
  }
}

# Logging Role
resource "kubernetes_cluster_role" "logging" {
  metadata {
    name = "logging-role"
    labels = {
      role = "logging"
    }
  }

  # Access to pod logs
  rule {
    api_groups = [""]
    resources  = ["pods", "pods/log"]
    verbs      = ["get", "list", "watch"]
  }

  # Access to namespaces for discovery
  rule {
    api_groups = [""]
    resources  = ["namespaces"]
    verbs      = ["get", "list", "watch"]
  }
}

# Monitoring Service Account
resource "kubernetes_service_account" "monitoring" {
  metadata {
    name      = "monitoring-account"
    namespace = "monitoring"
    labels = {
      app = "monitoring"
    }
  }

  automount_service_account_token = true
}

# Logging Service Account
resource "kubernetes_service_account" "logging" {
  metadata {
    name      = "logging-account"
    namespace = "logging"
    labels = {
      app = "logging"
    }
  }

  automount_service_account_token = true
}

# Monitoring Cluster Role Binding
resource "kubernetes_cluster_role_binding" "monitoring_binding" {
  metadata {
    name = "monitoring-binding"
    labels = {
      role = "monitoring"
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = "monitoring-role"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "monitoring-account"
    namespace = "monitoring"
  }

  depends_on = [
    kubernetes_service_account.monitoring,
    kubernetes_cluster_role.monitoring
  ]
}

# Logging Cluster Role Binding
resource "kubernetes_cluster_role_binding" "logging_binding" {
  metadata {
    name = "logging-binding"
    labels = {
      role = "logging"
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = "logging-role"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "logging-account"
    namespace = "logging"
  }

  depends_on = [
    kubernetes_service_account.logging,
    kubernetes_cluster_role.logging
  ]
}

# ---------------------------------------------------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------------------------------------------------

variable "cloud_provider" {
  description = "Cloud provider where the Kubernetes cluster is running (aws, azure, gcp)"
  type        = string
  default     = "aws"
}

variable "aws_account_id" {
  description = "AWS account ID for IAM role ARN construction"
  type        = string
  default     = ""
}

variable "gcp_project_id" {
  description = "GCP project ID for service account email construction"
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------------------------------------------------

output "service_account_names" {
  description = "Names of the service accounts created"
  value = {
    email_service       = { for k, v in kubernetes_service_account.email_service : k => v.metadata[0].name }
    document_service    = { for k, v in kubernetes_service_account.document_service : k => v.metadata[0].name }
    ocr_service         = { for k, v in kubernetes_service_account.ocr_service : k => v.metadata[0].name }
    data_service        = { for k, v in kubernetes_service_account.data_service : k => v.metadata[0].name }
    notification_service = { for k, v in kubernetes_service_account.notification_service : k => v.metadata[0].name }
    api_gateway         = { for k, v in kubernetes_service_account.api_gateway : k => v.metadata[0].name }
    cicd                = { for k, v in kubernetes_service_account.cicd : k => v.metadata[0].name }
  }
}

output "role_names" {
  description = "Names of the roles created"
  value = {
    operations_staff    = { for k, v in kubernetes_role.operations_staff : k => v.metadata[0].name }
    system_admin        = { for k, v in kubernetes_role.system_admin : k => v.metadata[0].name }
    cicd_deployer       = { for k, v in kubernetes_role.cicd_deployer : k => v.metadata[0].name }
    monitoring          = kubernetes_cluster_role.monitoring.metadata[0].name
    logging             = kubernetes_cluster_role.logging.metadata[0].name
  }
}