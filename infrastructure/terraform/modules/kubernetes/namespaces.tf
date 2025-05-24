/**
 * Kubernetes Namespaces Terraform Module
 *
 * This module creates dedicated namespaces for each microservice in the MCA Application Processing System,
 * configures resource quotas, and sets up namespace-level policies for service isolation and resource management.
 */

# Variables for namespace configuration
variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
}

variable "namespace_labels" {
  description = "Common labels to apply to all namespaces"
  type        = map(string)
  default     = {}
}

variable "enable_network_policies" {
  description = "Whether to enable network policies for namespace isolation"
  type        = bool
  default     = true
}

# Resource quotas configuration
variable "default_resource_quotas" {
  description = "Default resource quotas for standard namespaces"
  type = object({
    cpu_request      = string
    cpu_limit        = string
    memory_request   = string
    memory_limit     = string
    storage_request  = string
    pods             = number
    services         = number
    configmaps       = number
    secrets          = number
    persistent_volume_claims = number
  })
  default = {
    cpu_request      = "4"
    cpu_limit        = "8"
    memory_request   = "8Gi"
    memory_limit     = "16Gi"
    storage_request  = "20Gi"
    pods             = 20
    services         = 10
    configmaps       = 20
    secrets          = 30
    persistent_volume_claims = 10
  }
}

# Special resource quotas for OCR service (GPU-enabled)
variable "ocr_resource_quotas" {
  description = "Resource quotas for OCR service namespace (GPU-enabled)"
  type = object({
    cpu_request      = string
    cpu_limit        = string
    memory_request   = string
    memory_limit     = string
    storage_request  = string
    gpu_limit        = string
    pods             = number
    services         = number
    configmaps       = number
    secrets          = number
    persistent_volume_claims = number
  })
  default = {
    cpu_request      = "8"
    cpu_limit        = "16"
    memory_request   = "16Gi"
    memory_limit     = "32Gi"
    storage_request  = "50Gi"
    gpu_limit        = "2"
    pods             = 15
    services         = 5
    configmaps       = 20
    secrets          = 30
    persistent_volume_claims = 10
  }
}

# Local variables for namespace configuration
locals {
  base_labels = merge(
    var.namespace_labels,
    {
      "app.kubernetes.io/part-of" = "mca-system"
      "environment"               = var.environment
      "managed-by"                = "terraform"
    }
  )
  
  # Service-specific labels
  email_service_labels = merge(local.base_labels, {
    "app.kubernetes.io/name" = "email-service"
    "service-type"           = "nodejs"
  })
  
  document_service_labels = merge(local.base_labels, {
    "app.kubernetes.io/name" = "document-service"
    "service-type"           = "python"
  })
  
  ocr_service_labels = merge(local.base_labels, {
    "app.kubernetes.io/name" = "ocr-service"
    "service-type"           = "python"
    "gpu-enabled"            = "true"
  })
  
  data_service_labels = merge(local.base_labels, {
    "app.kubernetes.io/name" = "data-service"
    "service-type"           = "java"
  })
  
  notification_service_labels = merge(local.base_labels, {
    "app.kubernetes.io/name" = "notification-service"
    "service-type"           = "nodejs"
  })
}

# Email Service Namespace
resource "kubernetes_namespace" "email_service" {
  metadata {
    name = "email-service-${var.environment}"
    labels = local.email_service_labels
  }
}

# Document Service Namespace
resource "kubernetes_namespace" "document_service" {
  metadata {
    name = "document-service-${var.environment}"
    labels = local.document_service_labels
  }
}

# OCR Service Namespace (GPU-enabled)
resource "kubernetes_namespace" "ocr_service" {
  metadata {
    name = "ocr-service-${var.environment}"
    labels = local.ocr_service_labels
  }
}

# Data Service Namespace
resource "kubernetes_namespace" "data_service" {
  metadata {
    name = "data-service-${var.environment}"
    labels = local.data_service_labels
  }
}

# Notification Service Namespace
resource "kubernetes_namespace" "notification_service" {
  metadata {
    name = "notification-service-${var.environment}"
    labels = local.notification_service_labels
  }
}

# Resource Quotas for standard services
resource "kubernetes_resource_quota" "email_service" {
  metadata {
    name      = "resource-quota"
    namespace = kubernetes_namespace.email_service.metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = var.default_resource_quotas.cpu_request
      "limits.cpu"      = var.default_resource_quotas.cpu_limit
      "requests.memory" = var.default_resource_quotas.memory_request
      "limits.memory"   = var.default_resource_quotas.memory_limit
      "requests.storage" = var.default_resource_quotas.storage_request
      "pods"            = var.default_resource_quotas.pods
      "services"        = var.default_resource_quotas.services
      "configmaps"      = var.default_resource_quotas.configmaps
      "secrets"         = var.default_resource_quotas.secrets
      "persistentvolumeclaims" = var.default_resource_quotas.persistent_volume_claims
    }
  }
}

resource "kubernetes_resource_quota" "document_service" {
  metadata {
    name      = "resource-quota"
    namespace = kubernetes_namespace.document_service.metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = var.default_resource_quotas.cpu_request
      "limits.cpu"      = var.default_resource_quotas.cpu_limit
      "requests.memory" = var.default_resource_quotas.memory_request
      "limits.memory"   = var.default_resource_quotas.memory_limit
      "requests.storage" = var.default_resource_quotas.storage_request
      "pods"            = var.default_resource_quotas.pods
      "services"        = var.default_resource_quotas.services
      "configmaps"      = var.default_resource_quotas.configmaps
      "secrets"         = var.default_resource_quotas.secrets
      "persistentvolumeclaims" = var.default_resource_quotas.persistent_volume_claims
    }
  }
}

resource "kubernetes_resource_quota" "data_service" {
  metadata {
    name      = "resource-quota"
    namespace = kubernetes_namespace.data_service.metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = var.default_resource_quotas.cpu_request
      "limits.cpu"      = var.default_resource_quotas.cpu_limit
      "requests.memory" = var.default_resource_quotas.memory_request
      "limits.memory"   = var.default_resource_quotas.memory_limit
      "requests.storage" = var.default_resource_quotas.storage_request
      "pods"            = var.default_resource_quotas.pods
      "services"        = var.default_resource_quotas.services
      "configmaps"      = var.default_resource_quotas.configmaps
      "secrets"         = var.default_resource_quotas.secrets
      "persistentvolumeclaims" = var.default_resource_quotas.persistent_volume_claims
    }
  }
}

resource "kubernetes_resource_quota" "notification_service" {
  metadata {
    name      = "resource-quota"
    namespace = kubernetes_namespace.notification_service.metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = var.default_resource_quotas.cpu_request
      "limits.cpu"      = var.default_resource_quotas.cpu_limit
      "requests.memory" = var.default_resource_quotas.memory_request
      "limits.memory"   = var.default_resource_quotas.memory_limit
      "requests.storage" = var.default_resource_quotas.storage_request
      "pods"            = var.default_resource_quotas.pods
      "services"        = var.default_resource_quotas.services
      "configmaps"      = var.default_resource_quotas.configmaps
      "secrets"         = var.default_resource_quotas.secrets
      "persistentvolumeclaims" = var.default_resource_quotas.persistent_volume_claims
    }
  }
}

# Special resource quota for OCR service with GPU resources
resource "kubernetes_resource_quota" "ocr_service" {
  metadata {
    name      = "resource-quota"
    namespace = kubernetes_namespace.ocr_service.metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = var.ocr_resource_quotas.cpu_request
      "limits.cpu"      = var.ocr_resource_quotas.cpu_limit
      "requests.memory" = var.ocr_resource_quotas.memory_request
      "limits.memory"   = var.ocr_resource_quotas.memory_limit
      "requests.storage" = var.ocr_resource_quotas.storage_request
      "limits.nvidia.com/gpu" = var.ocr_resource_quotas.gpu_limit
      "pods"            = var.ocr_resource_quotas.pods
      "services"        = var.ocr_resource_quotas.services
      "configmaps"      = var.ocr_resource_quotas.configmaps
      "secrets"         = var.ocr_resource_quotas.secrets
      "persistentvolumeclaims" = var.ocr_resource_quotas.persistent_volume_claims
    }
  }
}

# Default limit ranges for pods within each namespace
resource "kubernetes_limit_range" "email_service" {
  metadata {
    name      = "default-limits"
    namespace = kubernetes_namespace.email_service.metadata[0].name
  }

  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "500m"
        memory = "512Mi"
      }
      default_request = {
        cpu    = "250m"
        memory = "256Mi"
      }
    }
  }
}

resource "kubernetes_limit_range" "document_service" {
  metadata {
    name      = "default-limits"
    namespace = kubernetes_namespace.document_service.metadata[0].name
  }

  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "1000m"
        memory = "1Gi"
      }
      default_request = {
        cpu    = "500m"
        memory = "512Mi"
      }
    }
  }
}

resource "kubernetes_limit_range" "ocr_service" {
  metadata {
    name      = "default-limits"
    namespace = kubernetes_namespace.ocr_service.metadata[0].name
  }

  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "2000m"
        memory = "4Gi"
      }
      default_request = {
        cpu    = "1000m"
        memory = "2Gi"
      }
    }
  }
}

resource "kubernetes_limit_range" "data_service" {
  metadata {
    name      = "default-limits"
    namespace = kubernetes_namespace.data_service.metadata[0].name
  }

  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "1000m"
        memory = "2Gi"
      }
      default_request = {
        cpu    = "500m"
        memory = "1Gi"
      }
    }
  }
}

resource "kubernetes_limit_range" "notification_service" {
  metadata {
    name      = "default-limits"
    namespace = kubernetes_namespace.notification_service.metadata[0].name
  }

  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "500m"
        memory = "512Mi"
      }
      default_request = {
        cpu    = "250m"
        memory = "256Mi"
      }
    }
  }
}

# Network policies for namespace isolation
resource "kubernetes_network_policy" "email_service_default_deny" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "default-deny"
    namespace = kubernetes_namespace.email_service.metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

resource "kubernetes_network_policy" "email_service_allow_same_namespace" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-same-namespace"
    namespace = kubernetes_namespace.email_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = kubernetes_namespace.email_service.metadata[0].name
          }
        }
      }
    }

    policy_types = ["Ingress"]
  }
}

resource "kubernetes_network_policy" "email_service_allow_api_gateway" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-api-gateway"
    namespace = kubernetes_namespace.email_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "api-gateway"
          }
        }
      }
    }

    policy_types = ["Ingress"]
  }
}

# Allow email service to access RabbitMQ for message publishing
resource "kubernetes_network_policy" "email_service_allow_rabbitmq_egress" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-rabbitmq-egress"
    namespace = kubernetes_namespace.email_service.metadata[0].name
  }

  spec {
    pod_selector {}

    egress {
      to {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "rabbitmq"
          }
        }
      }
    }

    policy_types = ["Egress"]
  }
}

# Similar network policies for other services
resource "kubernetes_network_policy" "document_service_default_deny" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "default-deny"
    namespace = kubernetes_namespace.document_service.metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

resource "kubernetes_network_policy" "document_service_allow_same_namespace" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-same-namespace"
    namespace = kubernetes_namespace.document_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = kubernetes_namespace.document_service.metadata[0].name
          }
        }
      }
    }

    policy_types = ["Ingress"]
  }
}

# Allow document service to access RabbitMQ for message consumption and publishing
resource "kubernetes_network_policy" "document_service_allow_rabbitmq" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-rabbitmq"
    namespace = kubernetes_namespace.document_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "rabbitmq"
          }
        }
      }
    }

    egress {
      to {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "rabbitmq"
          }
        }
      }
    }

    policy_types = ["Ingress", "Egress"]
  }
}

# Allow document service to access S3 storage
resource "kubernetes_network_policy" "document_service_allow_s3_egress" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-s3-egress"
    namespace = kubernetes_namespace.document_service.metadata[0].name
  }

  spec {
    pod_selector {}

    egress {
      to {
        ip_block {
          cidr = "0.0.0.0/0" # This would be refined in production to specific S3 endpoints
          except = [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16"
          ]
        }
      }

      ports {
        port     = 443
        protocol = "TCP"
      }
    }

    policy_types = ["Egress"]
  }
}

# OCR Service Network Policies
resource "kubernetes_network_policy" "ocr_service_default_deny" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "default-deny"
    namespace = kubernetes_namespace.ocr_service.metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

resource "kubernetes_network_policy" "ocr_service_allow_same_namespace" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-same-namespace"
    namespace = kubernetes_namespace.ocr_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = kubernetes_namespace.ocr_service.metadata[0].name
          }
        }
      }
    }

    policy_types = ["Ingress"]
  }
}

# Allow OCR service to access RabbitMQ for message consumption and publishing
resource "kubernetes_network_policy" "ocr_service_allow_rabbitmq" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-rabbitmq"
    namespace = kubernetes_namespace.ocr_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "rabbitmq"
          }
        }
      }
    }

    egress {
      to {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "rabbitmq"
          }
        }
      }
    }

    policy_types = ["Ingress", "Egress"]
  }
}

# Allow OCR service to access S3 storage
resource "kubernetes_network_policy" "ocr_service_allow_s3_egress" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-s3-egress"
    namespace = kubernetes_namespace.ocr_service.metadata[0].name
  }

  spec {
    pod_selector {}

    egress {
      to {
        ip_block {
          cidr = "0.0.0.0/0" # This would be refined in production to specific S3 endpoints
          except = [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16"
          ]
        }
      }

      ports {
        port     = 443
        protocol = "TCP"
      }
    }

    policy_types = ["Egress"]
  }
}

# Data Service Network Policies
resource "kubernetes_network_policy" "data_service_default_deny" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "default-deny"
    namespace = kubernetes_namespace.data_service.metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

resource "kubernetes_network_policy" "data_service_allow_same_namespace" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-same-namespace"
    namespace = kubernetes_namespace.data_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = kubernetes_namespace.data_service.metadata[0].name
          }
        }
      }
    }

    policy_types = ["Ingress"]
  }
}

# Allow data service to access RabbitMQ for message consumption
resource "kubernetes_network_policy" "data_service_allow_rabbitmq" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-rabbitmq"
    namespace = kubernetes_namespace.data_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "rabbitmq"
          }
        }
      }
    }

    egress {
      to {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "rabbitmq"
          }
        }
      }
    }

    policy_types = ["Ingress", "Egress"]
  }
}

# Allow data service to access PostgreSQL database
resource "kubernetes_network_policy" "data_service_allow_postgres_egress" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-postgres-egress"
    namespace = kubernetes_namespace.data_service.metadata[0].name
  }

  spec {
    pod_selector {}

    egress {
      to {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "postgresql"
          }
        }
      }

      ports {
        port     = 5432
        protocol = "TCP"
      }
    }

    policy_types = ["Egress"]
  }
}

# Allow data service to access Redis cache
resource "kubernetes_network_policy" "data_service_allow_redis_egress" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-redis-egress"
    namespace = kubernetes_namespace.data_service.metadata[0].name
  }

  spec {
    pod_selector {}

    egress {
      to {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "redis"
          }
        }
      }

      ports {
        port     = 6379
        protocol = "TCP"
      }
    }

    policy_types = ["Egress"]
  }
}

# Allow API Gateway to access data service
resource "kubernetes_network_policy" "data_service_allow_api_gateway" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-api-gateway"
    namespace = kubernetes_namespace.data_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "api-gateway"
          }
        }
      }
    }

    policy_types = ["Ingress"]
  }
}

# Notification Service Network Policies
resource "kubernetes_network_policy" "notification_service_default_deny" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "default-deny"
    namespace = kubernetes_namespace.notification_service.metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

resource "kubernetes_network_policy" "notification_service_allow_same_namespace" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-same-namespace"
    namespace = kubernetes_namespace.notification_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = kubernetes_namespace.notification_service.metadata[0].name
          }
        }
      }
    }

    policy_types = ["Ingress"]
  }
}

# Allow notification service to access RabbitMQ for message consumption
resource "kubernetes_network_policy" "notification_service_allow_rabbitmq" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-rabbitmq"
    namespace = kubernetes_namespace.notification_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "rabbitmq"
          }
        }
      }
    }

    egress {
      to {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "rabbitmq"
          }
        }
      }
    }

    policy_types = ["Ingress", "Egress"]
  }
}

# Allow API Gateway to access notification service
resource "kubernetes_network_policy" "notification_service_allow_api_gateway" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-api-gateway"
    namespace = kubernetes_namespace.notification_service.metadata[0].name
  }

  spec {
    pod_selector {}

    ingress {
      from {
        namespace_selector {
          match_labels = {
            "app.kubernetes.io/name" = "api-gateway"
          }
        }
      }
    }

    policy_types = ["Ingress"]
  }
}

# Allow notification service to send webhooks to external services
resource "kubernetes_network_policy" "notification_service_allow_webhooks_egress" {
  count = var.enable_network_policies ? 1 : 0

  metadata {
    name      = "allow-webhooks-egress"
    namespace = kubernetes_namespace.notification_service.metadata[0].name
  }

  spec {
    pod_selector {}

    egress {
      to {
        ip_block {
          cidr = "0.0.0.0/0" # This would be refined in production to specific webhook endpoints
          except = [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16"
          ]
        }
      }

      ports {
        port     = 443
        protocol = "TCP"
      }
    }

    policy_types = ["Egress"]
  }
}

# Output the namespace names for use in other modules
output "email_service_namespace" {
  description = "The name of the email service namespace"
  value       = kubernetes_namespace.email_service.metadata[0].name
}

output "document_service_namespace" {
  description = "The name of the document service namespace"
  value       = kubernetes_namespace.document_service.metadata[0].name
}

output "ocr_service_namespace" {
  description = "The name of the OCR service namespace"
  value       = kubernetes_namespace.ocr_service.metadata[0].name
}

output "data_service_namespace" {
  description = "The name of the data service namespace"
  value       = kubernetes_namespace.data_service.metadata[0].name
}

output "notification_service_namespace" {
  description = "The name of the notification service namespace"
  value       = kubernetes_namespace.notification_service.metadata[0].name
}