# Variables for the Prometheus and Grafana monitoring stack

# General configuration
variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
}

variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace for monitoring resources"
  type        = string
  default     = "monitoring"
}

variable "create_namespace" {
  description = "Whether to create the monitoring namespace"
  type        = bool
  default     = true
}

variable "namespace_labels" {
  description = "Labels to apply to the monitoring namespace"
  type        = map(string)
  default     = {}
}

variable "app_namespace" {
  description = "Kubernetes namespace where application services are deployed"
  type        = string
  default     = "default"
}

# Prometheus configuration
variable "prometheus_release_name" {
  description = "Name of the Prometheus Helm release"
  type        = string
  default     = "prometheus"
}

variable "prometheus_chart_version" {
  description = "Version of the kube-prometheus-stack Helm chart"
  type        = string
  default     = "45.7.1"
}

variable "prometheus_operator_version" {
  description = "Version of the Prometheus Operator"
  type        = string
  default     = "v0.63.0"
}

variable "prometheus_version" {
  description = "Version of Prometheus"
  type        = string
  default     = "v2.42.0"
}

variable "alertmanager_version" {
  description = "Version of Alertmanager"
  type        = string
  default     = "v0.25.0"
}

variable "prometheus_storage_enabled" {
  description = "Whether to enable persistent storage for Prometheus"
  type        = bool
  default     = true
}

variable "prometheus_storage_class" {
  description = "Storage class for Prometheus persistent volume"
  type        = string
  default     = "standard"
}

variable "prometheus_storage_size" {
  description = "Size of Prometheus persistent volume"
  type        = string
  default     = "50Gi"
}

variable "prometheus_retention_period" {
  description = "Data retention period for Prometheus"
  type        = string
  default     = "15d"
}

variable "prometheus_operator_resources" {
  description = "Resource requests and limits for Prometheus Operator"
  type        = map(map(string))
  default     = {
    requests = {
      cpu    = "100m"
      memory = "128Mi"
    }
    limits = {
      cpu    = "200m"
      memory = "256Mi"
    }
  }
}

variable "prometheus_resources" {
  description = "Resource requests and limits for Prometheus"
  type        = map(map(string))
  default     = {
    requests = {
      cpu    = "500m"
      memory = "2Gi"
    }
    limits = {
      cpu    = "1000m"
      memory = "4Gi"
    }
  }
}

variable "alertmanager_resources" {
  description = "Resource requests and limits for Alertmanager"
  type        = map(map(string))
  default     = {
    requests = {
      cpu    = "100m"
      memory = "128Mi"
    }
    limits = {
      cpu    = "200m"
      memory = "256Mi"
    }
  }
}

variable "additional_scrape_configs" {
  description = "Additional scrape configurations for Prometheus"
  type        = list(any)
  default     = []
}

# Grafana configuration
variable "grafana_version" {
  description = "Version of Grafana"
  type        = string
  default     = "9.3.6"
}

variable "grafana_admin_password" {
  description = "Admin password for Grafana"
  type        = string
  sensitive   = true
  default     = "prom-operator"
}

variable "grafana_storage_enabled" {
  description = "Whether to enable persistent storage for Grafana"
  type        = bool
  default     = true
}

variable "grafana_storage_class" {
  description = "Storage class for Grafana persistent volume"
  type        = string
  default     = "standard"
}

variable "grafana_storage_size" {
  description = "Size of Grafana persistent volume"
  type        = string
  default     = "10Gi"
}

variable "grafana_resources" {
  description = "Resource requests and limits for Grafana"
  type        = map(map(string))
  default     = {
    requests = {
      cpu    = "100m"
      memory = "128Mi"
    }
    limits = {
      cpu    = "200m"
      memory = "256Mi"
    }
  }
}

variable "grafana_service_type" {
  description = "Kubernetes service type for Grafana"
  type        = string
  default     = "ClusterIP"
}

variable "grafana_ingress_enabled" {
  description = "Whether to enable ingress for Grafana"
  type        = bool
  default     = false
}

variable "grafana_ingress_annotations" {
  description = "Annotations for Grafana ingress"
  type        = map(string)
  default     = {}
}

variable "grafana_ingress_hosts" {
  description = "Hosts for Grafana ingress"
  type        = list(string)
  default     = []
}

variable "grafana_ingress_tls" {
  description = "TLS configuration for Grafana ingress"
  type        = list(map(any))
  default     = []
}

variable "grafana_root_url" {
  description = "Root URL for Grafana"
  type        = string
  default     = ""
}

variable "grafana_disable_login_form" {
  description = "Whether to disable the login form in Grafana"
  type        = bool
  default     = false
}

variable "grafana_anonymous_enabled" {
  description = "Whether to enable anonymous access to Grafana"
  type        = bool
  default     = false
}

# PostgreSQL exporter configuration
variable "postgres_exporter_enabled" {
  description = "Whether to enable PostgreSQL exporter"
  type        = bool
  default     = true
}

variable "postgres_exporter_version" {
  description = "Version of the PostgreSQL exporter Helm chart"
  type        = string
  default     = "2.9.0"
}

variable "postgres_host" {
  description = "PostgreSQL host"
  type        = string
  default     = ""
}

variable "postgres_port" {
  description = "PostgreSQL port"
  type        = number
  default     = 5432
}

variable "postgres_user" {
  description = "PostgreSQL user"
  type        = string
  default     = ""
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "postgres_database" {
  description = "PostgreSQL database"
  type        = string
  default     = ""
}

variable "postgres_exporter_resources" {
  description = "Resource requests and limits for PostgreSQL exporter"
  type        = map(map(string))
  default     = {
    requests = {
      cpu    = "50m"
      memory = "64Mi"
    }
    limits = {
      cpu    = "100m"
      memory = "128Mi"
    }
  }
}

# RabbitMQ exporter configuration
variable "rabbitmq_exporter_enabled" {
  description = "Whether to enable RabbitMQ exporter"
  type        = bool
  default     = true
}

variable "rabbitmq_exporter_version" {
  description = "Version of the RabbitMQ exporter Helm chart"
  type        = string
  default     = "1.6.1"
}

variable "rabbitmq_host" {
  description = "RabbitMQ host"
  type        = string
  default     = ""
}

variable "rabbitmq_port" {
  description = "RabbitMQ port"
  type        = number
  default     = 15672
}

variable "rabbitmq_user" {
  description = "RabbitMQ user"
  type        = string
  default     = ""
}

variable "rabbitmq_password" {
  description = "RabbitMQ password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "rabbitmq_exporter_resources" {
  description = "Resource requests and limits for RabbitMQ exporter"
  type        = map(map(string))
  default     = {
    requests = {
      cpu    = "50m"
      memory = "64Mi"
    }
    limits = {
      cpu    = "100m"
      memory = "128Mi"
    }
  }
}

# Redis exporter configuration
variable "redis_exporter_enabled" {
  description = "Whether to enable Redis exporter"
  type        = bool
  default     = true
}

variable "redis_exporter_version" {
  description = "Version of the Redis exporter Helm chart"
  type        = string
  default     = "5.2.0"
}

variable "redis_host" {
  description = "Redis host"
  type        = string
  default     = ""
}

variable "redis_port" {
  description = "Redis port"
  type        = number
  default     = 6379
}

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
  default     = ""
}

variable "redis_exporter_resources" {
  description = "Resource requests and limits for Redis exporter"
  type        = map(map(string))
  default     = {
    requests = {
      cpu    = "50m"
      memory = "64Mi"
    }
    limits = {
      cpu    = "100m"
      memory = "128Mi"
    }
  }
}

# CloudWatch exporter configuration for S3 metrics
variable "cloudwatch_exporter_enabled" {
  description = "Whether to enable CloudWatch exporter for S3 metrics"
  type        = bool
  default     = false
}

variable "cloudwatch_exporter_version" {
  description = "Version of the CloudWatch exporter Helm chart"
  type        = string
  default     = "0.22.0"
}

variable "cloudwatch_exporter_role" {
  description = "IAM role for CloudWatch exporter"
  type        = string
  default     = ""
}

variable "aws_region" {
  description = "AWS region for CloudWatch metrics"
  type        = string
  default     = "us-east-1"
}

variable "cloudwatch_exporter_resources" {
  description = "Resource requests and limits for CloudWatch exporter"
  type        = map(map(string))
  default     = {
    requests = {
      cpu    = "50m"
      memory = "64Mi"
    }
    limits = {
      cpu    = "100m"
      memory = "128Mi"
    }
  }
}

# Service monitor configuration
variable "email_service_monitor_enabled" {
  description = "Whether to enable service monitor for Email Service"
  type        = bool
  default     = true
}

variable "document_service_monitor_enabled" {
  description = "Whether to enable service monitor for Document Service"
  type        = bool
  default     = true
}

variable "ocr_service_monitor_enabled" {
  description = "Whether to enable service monitor for OCR Service"
  type        = bool
  default     = true
}

variable "data_service_monitor_enabled" {
  description = "Whether to enable service monitor for Data Service"
  type        = bool
  default     = true
}

variable "notification_service_monitor_enabled" {
  description = "Whether to enable service monitor for Notification Service"
  type        = bool
  default     = true
}

variable "api_gateway_service_monitor_enabled" {
  description = "Whether to enable service monitor for API Gateway"
  type        = bool
  default     = true
}

# Alert thresholds
variable "sla_processing_time_threshold" {
  description = "Threshold for application processing time SLA in seconds"
  type        = number
  default     = 300  # 5 minutes
}

variable "ocr_accuracy_threshold" {
  description = "Threshold for OCR extraction accuracy in percentage"
  type        = number
  default     = 99  # 99%
}

variable "queue_depth_threshold" {
  description = "Threshold for queue depth"
  type        = number
  default     = 1000
}

variable "api_response_time_threshold" {
  description = "Threshold for API response time in seconds"
  type        = number
  default     = 1  # 1 second
}