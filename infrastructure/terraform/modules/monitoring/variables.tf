# Variables for the monitoring module
# This file defines all input variables for configuring monitoring infrastructure
# across different environments (development, staging, production)

# General monitoring configuration
variable "monitoring_type" {
  description = "Type of monitoring solution to deploy (datadog or prometheus)"
  type        = string
  default     = "datadog"
  validation {
    condition     = contains(["datadog", "prometheus"], var.monitoring_type)
    error_message = "The monitoring_type must be either 'datadog' or 'prometheus'."
  }
}

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "The environment must be one of: development, staging, production."
  }
}

variable "resource_tags" {
  description = "Tags to apply to all monitoring resources for cost tracking and organization"
  type        = map(string)
  default     = {}
}

# Datadog specific configuration
variable "datadog_api_key" {
  description = "Datadog API key for authentication"
  type        = string
  sensitive   = true
  default     = ""
}

variable "datadog_app_key" {
  description = "Datadog application key for API access"
  type        = string
  sensitive   = true
  default     = ""
}

variable "datadog_site" {
  description = "Datadog site (e.g., 'us', 'eu')"
  type        = string
  default     = "us"
}

variable "datadog_enable_apm" {
  description = "Enable Application Performance Monitoring in Datadog"
  type        = bool
  default     = true
}

variable "datadog_enable_logs" {
  description = "Enable log collection in Datadog"
  type        = bool
  default     = true
}

variable "datadog_enable_process_monitoring" {
  description = "Enable process monitoring in Datadog"
  type        = bool
  default     = true
}

# Prometheus and Grafana specific configuration
variable "prometheus_retention_days" {
  description = "Number of days to retain Prometheus metrics"
  type        = number
  default     = 15
}

variable "prometheus_storage_size" {
  description = "Storage size for Prometheus in GB"
  type        = number
  default     = 50
}

variable "grafana_admin_password" {
  description = "Admin password for Grafana"
  type        = string
  sensitive   = true
  default     = ""
}

variable "grafana_version" {
  description = "Grafana version to deploy"
  type        = string
  default     = "9.5.1"
}

variable "grafana_plugins" {
  description = "List of Grafana plugins to install"
  type        = list(string)
  default     = ["grafana-piechart-panel", "grafana-clock-panel"]
}

# Monitoring thresholds and retention configuration
variable "metrics_retention_policy" {
  description = "Retention policy for different metric types in days"
  type = object({
    infrastructure = number
    container     = number
    application   = number
    database      = number
    frontend      = number
  })
  default = {
    infrastructure = 30
    container     = 14
    application   = 90
    database      = 30
    frontend      = 90
  }
}

variable "alert_thresholds" {
  description = "Thresholds for different alert types"
  type = object({
    cpu_utilization_percent    = number
    memory_utilization_percent = number
    disk_utilization_percent   = number
    error_rate_percent         = number
    api_latency_ms             = number
    queue_depth_messages       = number
  })
  default = {
    cpu_utilization_percent    = 80
    memory_utilization_percent = 85
    disk_utilization_percent   = 85
    error_rate_percent         = 5
    api_latency_ms             = 500
    queue_depth_messages       = 1000
  }
}

# Alert notification configuration
variable "alert_notification_channels" {
  description = "Configuration for alert notification channels"
  type = object({
    email_recipients  = list(string)
    slack_webhook_url = string
    pagerduty_key     = string
    use_pagerduty     = bool
    use_slack         = bool
    use_email         = bool
  })
  default = {
    email_recipients  = []
    slack_webhook_url = ""
    pagerduty_key     = ""
    use_pagerduty     = false
    use_slack         = true
    use_email         = true
  }
  sensitive = true
}

# Environment-specific monitoring configuration
variable "environment_config" {
  description = "Environment-specific monitoring configuration"
  type = object({
    agent_count             = number
    enable_detailed_metrics = bool
    sampling_rate_percent   = number
    log_level               = string
  })
  default = {
    agent_count             = 1
    enable_detailed_metrics = true
    sampling_rate_percent   = 100
    log_level               = "INFO"
  }
}

# Cost monitoring configuration
variable "cost_monitoring_enabled" {
  description = "Enable cost monitoring and optimization features"
  type        = bool
  default     = true
}

variable "budget_alert_thresholds" {
  description = "Budget alert thresholds as percentages of allocated budget"
  type        = list(number)
  default     = [70, 85, 95]
  validation {
    condition     = length([for threshold in var.budget_alert_thresholds : threshold if threshold >= 0 && threshold <= 100]) == length(var.budget_alert_thresholds)
    error_message = "Budget alert thresholds must be between 0 and 100."
  }
}

# Web vitals monitoring configuration for frontend
variable "web_vitals_monitoring" {
  description = "Configuration for Web Vitals monitoring"
  type = object({
    enabled                = bool
    lcp_threshold_ms       = number # Largest Contentful Paint threshold
    fid_threshold_ms       = number # First Input Delay threshold
    cls_threshold          = number # Cumulative Layout Shift threshold
    ttfb_threshold_ms      = number # Time to First Byte threshold
    sampling_rate_percent  = number # Percentage of sessions to sample
  })
  default = {
    enabled                = true
    lcp_threshold_ms       = 2500
    fid_threshold_ms       = 100
    cls_threshold          = 0.1
    ttfb_threshold_ms      = 600
    sampling_rate_percent  = 10
  }
}

# Service-specific monitoring configuration
variable "service_monitors" {
  description = "Configuration for service-specific monitoring"
  type = map(object({
    enabled                = bool
    scrape_interval_seconds = number
    port                   = number
    path                   = string
    custom_labels          = map(string)
  }))
  default = {
    "email-service" = {
      enabled                = true
      scrape_interval_seconds = 30
      port                   = 8080
      path                   = "/metrics"
      custom_labels          = {}
    },
    "document-service" = {
      enabled                = true
      scrape_interval_seconds = 30
      port                   = 8080
      path                   = "/metrics"
      custom_labels          = {}
    },
    "ocr-service" = {
      enabled                = true
      scrape_interval_seconds = 30
      port                   = 8080
      path                   = "/metrics"
      custom_labels          = {}
    },
    "data-service" = {
      enabled                = true
      scrape_interval_seconds = 30
      port                   = 8080
      path                   = "/actuator/prometheus"
      custom_labels          = {}
    },
    "notification-service" = {
      enabled                = true
      scrape_interval_seconds = 30
      port                   = 8080
      path                   = "/metrics"
      custom_labels          = {}
    }
  }
}

# Database monitoring configuration
variable "database_monitoring" {
  description = "Configuration for database monitoring"
  type = object({
    enabled                  = bool
    connection_pool_metrics  = bool
    query_performance_metrics = bool
    replication_lag_threshold_seconds = number
    max_connections_percent  = number
  })
  default = {
    enabled                  = true
    connection_pool_metrics  = true
    query_performance_metrics = true
    replication_lag_threshold_seconds = 30
    max_connections_percent  = 80
  }
}

# Message queue monitoring configuration
variable "queue_monitoring" {
  description = "Configuration for message queue monitoring"
  type = object({
    enabled                = bool
    queue_depth_threshold  = number
    consumer_lag_threshold = number
    dead_letter_threshold  = number
  })
  default = {
    enabled                = true
    queue_depth_threshold  = 1000
    consumer_lag_threshold = 100
    dead_letter_threshold  = 10
  }
}

# Cache monitoring configuration
variable "cache_monitoring" {
  description = "Configuration for Redis cache monitoring"
  type = object({
    enabled                = bool
    memory_usage_percent  = number
    hit_rate_threshold    = number
    eviction_threshold    = number
  })
  default = {
    enabled                = true
    memory_usage_percent  = 80
    hit_rate_threshold    = 50
    eviction_threshold    = 100
  }
}

# Storage monitoring configuration
variable "storage_monitoring" {
  description = "Configuration for S3 storage monitoring"
  type = object({
    enabled                = bool
    error_rate_threshold  = number
    latency_threshold_ms  = number
    bucket_size_alert_gb  = number
  })
  default = {
    enabled                = true
    error_rate_threshold  = 5
    latency_threshold_ms  = 200
    bucket_size_alert_gb  = 1000
  }
}