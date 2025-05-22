# Network Policies for MCA Application
# This file defines Kubernetes NetworkPolicy resources to control pod-to-pod communication
# and implement network security for the Merchant Cash Advance (MCA) Application Processing System.

# Variables for the module
variable "namespace" {
  description = "Kubernetes namespace where network policies will be applied"
  type        = string
  default     = "mca-system"
}

variable "api_gateway_selector" {
  description = "Label selector for API Gateway pods"
  type        = map(string)
  default     = { app = "api-gateway" }
}

variable "email_service_selector" {
  description = "Label selector for Email Service pods"
  type        = map(string)
  default     = { app = "email-service" }
}

variable "document_service_selector" {
  description = "Label selector for Document Service pods"
  type        = map(string)
  default     = { app = "document-service" }
}

variable "ocr_service_selector" {
  description = "Label selector for OCR Service pods"
  type        = map(string)
  default     = { app = "ocr-service" }
}

variable "data_service_selector" {
  description = "Label selector for Data Service pods"
  type        = map(string)
  default     = { app = "data-service" }
}

variable "notification_service_selector" {
  description = "Label selector for Notification Service pods"
  type        = map(string)
  default     = { app = "notification-service" }
}

variable "rabbitmq_selector" {
  description = "Label selector for RabbitMQ pods"
  type        = map(string)
  default     = { app = "rabbitmq" }
}

variable "redis_selector" {
  description = "Label selector for Redis pods"
  type        = map(string)
  default     = { app = "redis" }
}

variable "postgres_selector" {
  description = "Label selector for PostgreSQL pods"
  type        = map(string)
  default     = { app = "postgresql" }
}

variable "s3_storage_cidr" {
  description = "CIDR block for S3-compatible storage"
  type        = list(string)
  default     = []
}

variable "external_email_cidr" {
  description = "CIDR block for external email servers"
  type        = list(string)
  default     = []
}

variable "external_webhook_cidr" {
  description = "CIDR block for external webhook endpoints"
  type        = list(string)
  default     = []
}

# Default deny all ingress and egress traffic for the namespace
# This establishes a secure baseline where all traffic is denied by default
# Following the security best practice of denying all traffic and then explicitly allowing only necessary traffic
resource "kubernetes_manifest" "default_deny_all" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "default-deny-all"
      namespace = var.namespace
    }
    spec = {
      podSelector = {}
      policyTypes = ["Ingress", "Egress"]
    }
  }
}

# Allow DNS resolution for all pods
# This is essential for service discovery and external connectivity
resource "kubernetes_manifest" "allow_dns" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "allow-dns"
      namespace = var.namespace
    }
    spec = {
      podSelector = {}
      policyTypes = ["Egress"]
      egress = [{
        to = [{
          namespaceSelector = {
            matchLabels = {
              "kubernetes.io/metadata.name" = "kube-system"
            }
          }
          podSelector = {
            matchLabels = {
              "k8s-app" = "kube-dns"
            }
          }
        }]
        ports = [{
          protocol = "UDP"
          port     = 53
        }, {
          protocol = "TCP"
          port     = 53
        }]
      }]
    }
  }
}

# API Gateway Network Policy
# Allows ingress from external clients and egress to backend services
resource "kubernetes_manifest" "api_gateway_policy" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "api-gateway-policy"
      namespace = var.namespace
    }
    spec = {
      podSelector = {
        matchLabels = var.api_gateway_selector
      }
      policyTypes = ["Ingress", "Egress"]
      ingress = [{
        # Allow ingress from anywhere (typically handled by Ingress Controller)
        from = []
      }]
      egress = [{
        # Allow egress to Data Service
        to = [{
          podSelector = {
            matchLabels = var.data_service_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 8080 # Assuming Data Service runs on port 8080
        }]
      }, {
        # Allow egress to Notification Service
        to = [{
          podSelector = {
            matchLabels = var.notification_service_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 3000 # Assuming Notification Service runs on port 3000
        }]
      }]
    }
  }
}

# Email Service Network Policy
# Allows egress to external email servers and RabbitMQ
resource "kubernetes_manifest" "email_service_policy" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "email-service-policy"
      namespace = var.namespace
    }
    spec = {
      podSelector = {
        matchLabels = var.email_service_selector
      }
      policyTypes = ["Ingress", "Egress"]
      ingress = [] # No direct ingress needed
      egress = [{
        # Allow egress to RabbitMQ
        to = [{
          podSelector = {
            matchLabels = var.rabbitmq_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5672 # RabbitMQ AMQP port
        }]
      }, {
        # Allow egress to external email servers (IMAP/SMTP)
        to = length(var.external_email_cidr) > 0 ? [{
          ipBlock = {
            cidr = var.external_email_cidr[0]
          }
        }] : []
        ports = [{
          protocol = "TCP"
          port     = 143 # IMAP
        }, {
          protocol = "TCP"
          port     = 993 # IMAPS
        }, {
          protocol = "TCP"
          port     = 25 # SMTP
        }, {
          protocol = "TCP"
          port     = 587 # SMTP Submission
        }, {
          protocol = "TCP"
          port     = 465 # SMTPS
        }]
      }]
    }
  }
}

# Document Service Network Policy
# Allows ingress from RabbitMQ and egress to RabbitMQ and S3 storage
resource "kubernetes_manifest" "document_service_policy" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "document-service-policy"
      namespace = var.namespace
    }
    spec = {
      podSelector = {
        matchLabels = var.document_service_selector
      }
      policyTypes = ["Ingress", "Egress"]
      ingress = [{
        # Allow ingress from RabbitMQ
        from = [{
          podSelector = {
            matchLabels = var.rabbitmq_selector
          }
        }]
      }]
      egress = [{
        # Allow egress to RabbitMQ
        to = [{
          podSelector = {
            matchLabels = var.rabbitmq_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5672 # RabbitMQ AMQP port
        }]
      }, {
        # Allow egress to S3 storage
        to = length(var.s3_storage_cidr) > 0 ? [{
          ipBlock = {
            cidr = var.s3_storage_cidr[0]
          }
        }] : []
        ports = [{
          protocol = "TCP"
          port     = 443 # HTTPS
        }]
      }]
    }
  }
}

# OCR Service Network Policy
# Allows ingress from RabbitMQ and egress to RabbitMQ and S3 storage
resource "kubernetes_manifest" "ocr_service_policy" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "ocr-service-policy"
      namespace = var.namespace
    }
    spec = {
      podSelector = {
        matchLabels = var.ocr_service_selector
      }
      policyTypes = ["Ingress", "Egress"]
      ingress = [{
        # Allow ingress from RabbitMQ
        from = [{
          podSelector = {
            matchLabels = var.rabbitmq_selector
          }
        }]
      }]
      egress = [{
        # Allow egress to RabbitMQ
        to = [{
          podSelector = {
            matchLabels = var.rabbitmq_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5672 # RabbitMQ AMQP port
        }]
      }, {
        # Allow egress to S3 storage
        to = length(var.s3_storage_cidr) > 0 ? [{
          ipBlock = {
            cidr = var.s3_storage_cidr[0]
          }
        }] : []
        ports = [{
          protocol = "TCP"
          port     = 443 # HTTPS
        }]
      }]
    }
  }
}

# Data Service Network Policy
# Allows ingress from API Gateway and RabbitMQ, egress to PostgreSQL, Redis, and RabbitMQ
resource "kubernetes_manifest" "data_service_policy" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "data-service-policy"
      namespace = var.namespace
    }
    spec = {
      podSelector = {
        matchLabels = var.data_service_selector
      }
      policyTypes = ["Ingress", "Egress"]
      ingress = [{
        # Allow ingress from API Gateway
        from = [{
          podSelector = {
            matchLabels = var.api_gateway_selector
          }
        }]
      }, {
        # Allow ingress from RabbitMQ
        from = [{
          podSelector = {
            matchLabels = var.rabbitmq_selector
          }
        }]
      }]
      egress = [{
        # Allow egress to PostgreSQL
        to = [{
          podSelector = {
            matchLabels = var.postgres_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5432 # PostgreSQL port
        }]
      }, {
        # Allow egress to Redis
        to = [{
          podSelector = {
            matchLabels = var.redis_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 6379 # Redis port
        }]
      }, {
        # Allow egress to RabbitMQ
        to = [{
          podSelector = {
            matchLabels = var.rabbitmq_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5672 # RabbitMQ AMQP port
        }]
      }]
    }
  }
}

# Notification Service Network Policy
# Allows ingress from API Gateway and RabbitMQ, egress to external webhook endpoints and RabbitMQ
resource "kubernetes_manifest" "notification_service_policy" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "notification-service-policy"
      namespace = var.namespace
    }
    spec = {
      podSelector = {
        matchLabels = var.notification_service_selector
      }
      policyTypes = ["Ingress", "Egress"]
      ingress = [{
        # Allow ingress from API Gateway
        from = [{
          podSelector = {
            matchLabels = var.api_gateway_selector
          }
        }]
      }, {
        # Allow ingress from RabbitMQ
        from = [{
          podSelector = {
            matchLabels = var.rabbitmq_selector
          }
        }]
      }]
      egress = [{
        # Allow egress to RabbitMQ
        to = [{
          podSelector = {
            matchLabels = var.rabbitmq_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5672 # RabbitMQ AMQP port
        }]
      }, {
        # Allow egress to external webhook endpoints
        to = length(var.external_webhook_cidr) > 0 ? [{
          ipBlock = {
            cidr = var.external_webhook_cidr[0]
          }
        }] : []
        ports = [{
          protocol = "TCP"
          port     = 443 # HTTPS
        }, {
          protocol = "TCP"
          port     = 80 # HTTP
        }]
      }]
    }
  }
}

# RabbitMQ Network Policy
# Allows ingress from services that need to connect to RabbitMQ
resource "kubernetes_manifest" "rabbitmq_policy" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "rabbitmq-policy"
      namespace = var.namespace
    }
    spec = {
      podSelector = {
        matchLabels = var.rabbitmq_selector
      }
      policyTypes = ["Ingress"]
      ingress = [{
        # Allow ingress from Email Service
        from = [{
          podSelector = {
            matchLabels = var.email_service_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5672 # RabbitMQ AMQP port
        }]
      }, {
        # Allow ingress from Document Service
        from = [{
          podSelector = {
            matchLabels = var.document_service_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5672 # RabbitMQ AMQP port
        }]
      }, {
        # Allow ingress from OCR Service
        from = [{
          podSelector = {
            matchLabels = var.ocr_service_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5672 # RabbitMQ AMQP port
        }]
      }, {
        # Allow ingress from Data Service
        from = [{
          podSelector = {
            matchLabels = var.data_service_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5672 # RabbitMQ AMQP port
        }]
      }, {
        # Allow ingress from Notification Service
        from = [{
          podSelector = {
            matchLabels = var.notification_service_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5672 # RabbitMQ AMQP port
        }]
      }]
    }
  }
}

# PostgreSQL Network Policy
# Allows ingress from Data Service
resource "kubernetes_manifest" "postgres_policy" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "postgres-policy"
      namespace = var.namespace
    }
    spec = {
      podSelector = {
        matchLabels = var.postgres_selector
      }
      policyTypes = ["Ingress"]
      ingress = [{
        # Allow ingress from Data Service
        from = [{
          podSelector = {
            matchLabels = var.data_service_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 5432 # PostgreSQL port
        }]
      }]
    }
  }
}

# Redis Network Policy
# Allows ingress from Data Service
resource "kubernetes_manifest" "redis_policy" {
  manifest = {
    apiVersion = "networking.k8s.io/v1"
    kind       = "NetworkPolicy"
    metadata = {
      name      = "redis-policy"
      namespace = var.namespace
    }
    spec = {
      podSelector = {
        matchLabels = var.redis_selector
      }
      policyTypes = ["Ingress"]
      ingress = [{
        # Allow ingress from Data Service
        from = [{
          podSelector = {
            matchLabels = var.data_service_selector
          }
        }]
        ports = [{
          protocol = "TCP"
          port     = 6379 # Redis port
        }]
      }]
    }
  }
}

# Output the network policy names for reference
output "network_policy_names" {
  description = "Names of the created network policies"
  value = [
    kubernetes_manifest.default_deny_all.manifest.metadata.name,
    kubernetes_manifest.allow_dns.manifest.metadata.name,
    kubernetes_manifest.api_gateway_policy.manifest.metadata.name,
    kubernetes_manifest.email_service_policy.manifest.metadata.name,
    kubernetes_manifest.document_service_policy.manifest.metadata.name,
    kubernetes_manifest.ocr_service_policy.manifest.metadata.name,
    kubernetes_manifest.data_service_policy.manifest.metadata.name,
    kubernetes_manifest.notification_service_policy.manifest.metadata.name,
    kubernetes_manifest.rabbitmq_policy.manifest.metadata.name,
    kubernetes_manifest.postgres_policy.manifest.metadata.name,
    kubernetes_manifest.redis_policy.manifest.metadata.name
  ]
}

# Documentation for the module
# This section provides information about the network policies implemented in this module
# and how they contribute to the overall security of the MCA application
output "network_policy_documentation" {
  description = "Documentation for the network policies implemented in this module"
  value       = <<-EOT
    # MCA Application Network Policies

    This module implements network policies for the Merchant Cash Advance (MCA) Application Processing System
    following security best practices and the principle of least privilege.

    ## Security Approach

    1. **Default Deny**: All traffic is denied by default, and only explicitly allowed traffic is permitted.
    2. **Service Isolation**: Each microservice has its own network policy that defines allowed ingress and egress.
    3. **Defense in Depth**: Multiple layers of network security are implemented.
    4. **Least Privilege**: Services can only communicate with other services as required by the application architecture.

    ## Policy Overview

    - **Default Deny All**: Blocks all traffic by default
    - **Allow DNS**: Permits DNS resolution for all pods
    - **API Gateway**: Controls external access to backend services
    - **Email Service**: Restricts communication to RabbitMQ and external email servers
    - **Document Service**: Limits access to RabbitMQ and S3 storage
    - **OCR Service**: Restricts communication to RabbitMQ and S3 storage
    - **Data Service**: Controls access to databases, caching, and message queues
    - **Notification Service**: Manages webhook delivery and message queue access
    - **Infrastructure Components**: Specific policies for RabbitMQ, PostgreSQL, and Redis

    ## Usage Notes

    - Ensure your CNI plugin supports NetworkPolicy (e.g., Calico, Cilium)
    - Monitor policy effectiveness with logging and observability tools
    - Review and update policies as application architecture evolves
  EOT
}