# infrastructure/terraform/modules/monitoring/outputs.tf

# Common outputs regardless of monitoring solution
output "monitoring_type" {
  description = "The type of monitoring solution deployed"
  value       = var.monitoring_type
}

output "monitoring_enabled" {
  description = "Whether monitoring is enabled"
  value       = true
}

# Datadog-specific outputs
output "datadog_dashboard_url" {
  description = "URL to the Datadog dashboard"
  value       = local.use_datadog ? "https://app.datadoghq.com/dashboard/lists" : null
}

output "datadog_monitor_urls" {
  description = "URLs to the Datadog monitors"
  value = local.use_datadog ? {
    app_processing_time = "https://app.datadoghq.com/monitors#${module.datadog[0].app_processing_time_monitor_id}"
    ocr_accuracy        = "https://app.datadoghq.com/monitors#${module.datadog[0].ocr_accuracy_monitor_id}"
    queue_depth         = "https://app.datadoghq.com/monitors#${module.datadog[0].queue_depth_monitor_id}"
    api_response_time   = "https://app.datadoghq.com/monitors#${module.datadog[0].api_response_time_monitor_id}"
  } : null
}

# Prometheus/Grafana-specific outputs
output "prometheus_url" {
  description = "URL to the Prometheus UI"
  value       = local.use_prometheus ? module.prometheus[0].prometheus_url : null
}

output "grafana_url" {
  description = "URL to the Grafana dashboard"
  value       = local.use_prometheus ? module.prometheus[0].grafana_url : null
}

output "alertmanager_url" {
  description = "URL to the Alertmanager UI"
  value       = local.use_prometheus ? module.prometheus[0].alertmanager_url : null
}

# Monitoring endpoints for application integration
output "metrics_endpoint" {
  description = "Endpoint for sending metrics"
  value = local.use_datadog ? {
    url     = "https://api.datadoghq.com/api/v1/series"
    headers = {
      "Content-Type"       = "application/json"
      "DD-API-KEY"         = var.datadog_api_key
    }
  } : {
    url     = "${module.prometheus[0].prometheus_url}/api/v1/write"
    headers = {
      "Content-Type" = "application/json"
    }
  }
  sensitive = true
}

output "logs_endpoint" {
  description = "Endpoint for sending logs"
  value = local.use_datadog ? {
    url     = "https://http-intake.logs.datadoghq.com/v1/input"
    headers = {
      "Content-Type"       = "application/json"
      "DD-API-KEY"         = var.datadog_api_key
    }
  } : {
    url     = "${module.prometheus[0].loki_url}/loki/api/v1/push"
    headers = {
      "Content-Type" = "application/json"
    }
  }
  sensitive = true
}

output "traces_endpoint" {
  description = "Endpoint for sending traces"
  value = local.use_datadog ? {
    url     = "https://trace.agent.datadoghq.com"
    headers = {
      "Content-Type"       = "application/json"
      "DD-API-KEY"         = var.datadog_api_key
    }
  } : {
    url     = "${module.prometheus[0].tempo_url}/api/traces"
    headers = {
      "Content-Type" = "application/json"
    }
  }
  sensitive = true
}

# Monitoring configuration for application services
output "monitoring_config" {
  description = "Monitoring configuration for application services"
  value = {
    type                      = var.monitoring_type
    metric_collection_interval = local.metric_collection_interval
    environment               = var.environment
    alert_thresholds          = local.alert_thresholds
    custom_metrics            = var.custom_metrics
  }
}