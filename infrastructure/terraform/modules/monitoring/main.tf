# infrastructure/terraform/modules/monitoring/main.tf

# This module conditionally provisions either Datadog or Prometheus/Grafana based on the monitoring_type variable
# It serves as the orchestrator for the entire monitoring infrastructure

locals {
  # Common tags to be assigned to all resources
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Module      = "monitoring"
  }

  # Determine if we're using Datadog or Prometheus/Grafana
  use_datadog = var.monitoring_type == "datadog"
  use_prometheus = var.monitoring_type == "prometheus"

  # Validate monitoring type
  validate_monitoring_type = (
    var.monitoring_type == "datadog" || var.monitoring_type == "prometheus" ? true : 
    tobool("Invalid monitoring_type. Must be either 'datadog' or 'prometheus'")
  )

  # Define metric collection intervals based on environment
  metric_collection_interval = var.environment == "production" ? 10 : 30

  # Define retention periods based on environment
  metrics_retention_days = {
    "development" = 30
    "staging"     = 90
    "production"  = 455  # ~15 months
  }

  # Define alert thresholds
  alert_thresholds = {
    # Application processing time thresholds (in seconds)
    app_processing_time_warning  = 240  # 4 minutes
    app_processing_time_critical = 300  # 5 minutes
    
    # OCR accuracy thresholds (in percentage)
    ocr_accuracy_warning  = 95.0
    ocr_accuracy_critical = 90.0
    
    # Queue depth thresholds (in number of messages)
    queue_depth_warning  = var.environment == "production" ? 1000 : 500
    queue_depth_critical = var.environment == "production" ? 5000 : 1000
    
    # API response time thresholds (in milliseconds)
    api_response_time_warning  = 500
    api_response_time_critical = 1000
  }
}

# Conditionally create Datadog resources if monitoring_type is "datadog"
module "datadog" {
  count  = local.use_datadog ? 1 : 0
  source = "./datadog"

  project_name    = var.project_name
  environment     = var.environment
  datadog_api_key = var.datadog_api_key
  datadog_app_key = var.datadog_app_key
  
  kubernetes_integration_enabled = var.kubernetes_integration_enabled
  kubernetes_cluster_name       = var.kubernetes_cluster_name
  
  metric_collection_interval = local.metric_collection_interval
  metrics_retention_days     = local.metrics_retention_days[var.environment]
  alert_thresholds           = local.alert_thresholds
  
  notification_channels = var.notification_channels
  tags                  = merge(local.common_tags, var.additional_tags)
}

# Conditionally create Prometheus/Grafana resources if monitoring_type is "prometheus"
module "prometheus" {
  count  = local.use_prometheus ? 1 : 0
  source = "./prometheus"

  project_name    = var.project_name
  environment     = var.environment
  
  kubernetes_integration_enabled = var.kubernetes_integration_enabled
  kubernetes_cluster_name       = var.kubernetes_cluster_name
  kubernetes_namespace          = var.kubernetes_namespace
  
  storage_class_name        = var.storage_class_name
  prometheus_retention_days = local.metrics_retention_days[var.environment]
  prometheus_storage_size   = var.prometheus_storage_size
  grafana_storage_size      = var.grafana_storage_size
  
  alert_thresholds     = local.alert_thresholds
  notification_channels = var.notification_channels
  tags                  = merge(local.common_tags, var.additional_tags)
}

# Create monitoring dashboards for application metrics
resource "null_resource" "monitoring_dashboards" {
  depends_on = [
    module.datadog,
    module.prometheus
  ]

  # This is a placeholder for dashboard creation logic
  # In a real implementation, this would use provider-specific resources
  # to create dashboards programmatically

  triggers = {
    monitoring_type = var.monitoring_type
    environment     = var.environment
    # Add other triggers that would cause dashboards to be recreated
  }
}

# Create monitoring for application processing time metrics
resource "null_resource" "app_processing_time_monitoring" {
  depends_on = [
    module.datadog,
    module.prometheus
  ]

  # This is a placeholder for application processing time monitoring
  # In a real implementation, this would use provider-specific resources

  triggers = {
    monitoring_type = var.monitoring_type
    environment     = var.environment
    # Add other triggers that would cause monitoring to be recreated
  }
}

# Create monitoring for OCR accuracy metrics
resource "null_resource" "ocr_accuracy_monitoring" {
  depends_on = [
    module.datadog,
    module.prometheus
  ]

  # This is a placeholder for OCR accuracy monitoring
  # In a real implementation, this would use provider-specific resources

  triggers = {
    monitoring_type = var.monitoring_type
    environment     = var.environment
    # Add other triggers that would cause monitoring to be recreated
  }
}

# Create monitoring for queue depth
resource "null_resource" "queue_depth_monitoring" {
  depends_on = [
    module.datadog,
    module.prometheus
  ]

  # This is a placeholder for queue depth monitoring
  # In a real implementation, this would use provider-specific resources

  triggers = {
    monitoring_type = var.monitoring_type
    environment     = var.environment
    # Add other triggers that would cause monitoring to be recreated
  }
}

# Create monitoring for API response time
resource "null_resource" "api_response_time_monitoring" {
  depends_on = [
    module.datadog,
    module.prometheus
  ]

  # This is a placeholder for API response time monitoring
  # In a real implementation, this would use provider-specific resources

  triggers = {
    monitoring_type = var.monitoring_type
    environment     = var.environment
    # Add other triggers that would cause monitoring to be recreated
  }
}