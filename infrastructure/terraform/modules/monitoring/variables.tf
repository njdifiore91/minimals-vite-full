# infrastructure/terraform/modules/monitoring/variables.tf

# Core variables
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "mca-application-processing"
}

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "monitoring_type" {
  description = "Type of monitoring solution to deploy (datadog or prometheus)"
  type        = string
  default     = "datadog"
  validation {
    condition     = contains(["datadog", "prometheus"], var.monitoring_type)
    error_message = "Monitoring type must be either 'datadog' or 'prometheus'."
  }
}

variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Datadog-specific variables
variable "datadog_api_key" {
  description = "Datadog API key for authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "datadog_app_key" {
  description = "Datadog application key for API access"
  type        = string
  default     = ""
  sensitive   = true
}

# Prometheus-specific variables
variable "prometheus_storage_size" {
  description = "Storage size for Prometheus in Gi"
  type        = string
  default     = "50Gi"
}

variable "grafana_storage_size" {
  description = "Storage size for Grafana in Gi"
  type        = string
  default     = "10Gi"
}

variable "storage_class_name" {
  description = "Kubernetes storage class name for Prometheus and Grafana PVCs"
  type        = string
  default     = "standard"
}

# Kubernetes integration variables
variable "kubernetes_integration_enabled" {
  description = "Whether to enable Kubernetes integration"
  type        = bool
  default     = true
}

variable "kubernetes_cluster_name" {
  description = "Name of the Kubernetes cluster to monitor"
  type        = string
  default     = ""
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace to deploy Prometheus and Grafana"
  type        = string
  default     = "monitoring"
}

# Notification variables
variable "notification_channels" {
  description = "Map of notification channels for alerts"
  type = map(object({
    type  = string
    value = string
  }))
  default = {
    email = {
      type  = "email"
      value = "alerts@dollarfunding.com"
    }
    slack = {
      type  = "slack"
      value = "#alerts-monitoring"
    }
    pagerduty = {
      type  = "pagerduty"
      value = "monitoring-service-key"
    }
  }
}

# Metric collection variables
variable "custom_metrics" {
  description = "List of custom metrics to collect"
  type = list(object({
    name        = string
    description = string
    query       = string
    interval    = number
  }))
  default = [
    {
      name        = "app_processing_time"
      description = "Application processing time in seconds"
      query       = "avg:app.processing.time{*} by {service}"
      interval    = 60
    },
    {
      name        = "ocr_accuracy"
      description = "OCR extraction accuracy percentage"
      query       = "avg:ocr.accuracy{*} by {document_type}"
      interval    = 60
    },
    {
      name        = "queue_depth"
      description = "Message queue depth"
      query       = "avg:rabbitmq.queue.messages{*} by {queue_name}"
      interval    = 30
    },
    {
      name        = "api_response_time"
      description = "API response time in milliseconds"
      query       = "avg:api.response.time{*} by {endpoint}"
      interval    = 30
    }
  ]
}