# infrastructure/terraform/modules/monitoring/outputs.tf

# This file exports output values from the monitoring module, including:
# - Dashboard URLs for accessing monitoring dashboards
# - API endpoints for programmatic access to monitoring data
# - Authentication details for programmatic access (marked as sensitive)
# - Resource identifiers for cross-module references

#--------------------------------------------------------------
# General Outputs
#--------------------------------------------------------------

output "monitoring_type" {
  description = "The type of monitoring system deployed (datadog or prometheus)"
  value       = var.monitoring_type
}

output "environment" {
  description = "The environment where monitoring is deployed"
  value       = var.environment
}

#--------------------------------------------------------------
# Dashboard URLs
#--------------------------------------------------------------

output "dashboard_url" {
  description = "URL to access the main monitoring dashboard"
  value       = local.use_datadog ? "https://app.datadoghq.com/dashboard/mca-${var.environment}" : "http://${local.use_prometheus ? module.prometheus[0].grafana_endpoint : ""}"
}

output "application_dashboard_url" {
  description = "URL to access the MCA application processing dashboard"
  value       = local.use_datadog ? "https://app.datadoghq.com/dashboard/${local.use_datadog ? module.datadog[0].dashboard_id : ""}" : "http://${local.use_prometheus ? module.prometheus[0].grafana_endpoint : ""}/d/mca-application-processing"
}

output "infrastructure_dashboard_url" {
  description = "URL to access the infrastructure monitoring dashboard"
  value       = local.use_datadog ? "https://app.datadoghq.com/infrastructure" : "http://${local.use_prometheus ? module.prometheus[0].grafana_endpoint : ""}/d/mca-infrastructure"
}

#--------------------------------------------------------------
# API Endpoints
#--------------------------------------------------------------

output "api_endpoint" {
  description = "API endpoint for programmatic access to monitoring data"
  value       = local.use_datadog ? "https://api.datadoghq.com/api/v1" : "http://${local.use_prometheus ? module.prometheus[0].prometheus_endpoint : ""}/api/v1"
}

output "metrics_endpoint" {
  description = "API endpoint for metrics data"
  value       = local.use_datadog ? "https://api.datadoghq.com/api/v1/metrics" : "http://${local.use_prometheus ? module.prometheus[0].prometheus_endpoint : ""}/api/v1/query"
}

output "alerts_endpoint" {
  description = "API endpoint for alerts data"
  value       = local.use_datadog ? "https://api.datadoghq.com/api/v1/monitor" : "http://${local.use_prometheus ? module.prometheus[0].alertmanager_endpoint : ""}/api/v1/alerts"
}

#--------------------------------------------------------------
# Authentication Details (Sensitive)
#--------------------------------------------------------------

output "api_key" {
  description = "API key for programmatic access to monitoring system"
  value       = local.use_datadog ? var.datadog_api_key : null
  sensitive   = true
}

output "app_key" {
  description = "Application key for programmatic access to monitoring system"
  value       = local.use_datadog ? var.datadog_app_key : null
  sensitive   = true
}

output "grafana_admin_password" {
  description = "Admin password for Grafana (only applicable for prometheus monitoring type)"
  value       = local.use_prometheus ? module.prometheus[0].grafana_admin_password : null
  sensitive   = true
}

#--------------------------------------------------------------
# Resource Identifiers
#--------------------------------------------------------------

output "dashboard_id" {
  description = "ID of the main application dashboard"
  value       = local.use_datadog ? module.datadog[0].dashboard_id : null
}

#--------------------------------------------------------------
# Monitor IDs
#--------------------------------------------------------------

output "app_processing_time_monitor_id" {
  description = "ID of the application processing time monitor"
  value       = local.use_datadog ? module.datadog[0].app_processing_time_monitor_id : null
}

output "ocr_accuracy_monitor_id" {
  description = "ID of the OCR accuracy monitor"
  value       = local.use_datadog ? module.datadog[0].ocr_accuracy_monitor_id : null
}

output "queue_depth_monitor_id" {
  description = "ID of the queue depth monitor"
  value       = local.use_datadog ? module.datadog[0].queue_depth_monitor_id : null
}

output "api_response_time_monitor_id" {
  description = "ID of the API response time monitor"
  value       = local.use_datadog ? module.datadog[0].api_response_time_monitor_id : null
}

#--------------------------------------------------------------
# Prometheus/Grafana Specific Outputs
#--------------------------------------------------------------

output "prometheus_endpoint" {
  description = "Endpoint for Prometheus server (only applicable for prometheus monitoring type)"
  value       = local.use_prometheus ? module.prometheus[0].prometheus_endpoint : null
}

output "alertmanager_endpoint" {
  description = "Endpoint for Alertmanager (only applicable for prometheus monitoring type)"
  value       = local.use_prometheus ? module.prometheus[0].alertmanager_endpoint : null
}

output "grafana_endpoint" {
  description = "Endpoint for Grafana dashboard (only applicable for prometheus monitoring type)"
  value       = local.use_prometheus ? module.prometheus[0].grafana_endpoint : null
}

#--------------------------------------------------------------
# Integration Outputs
#--------------------------------------------------------------

output "monitoring_namespace" {
  description = "Kubernetes namespace where monitoring resources are deployed"
  value       = local.use_prometheus ? module.prometheus[0].monitoring_namespace : null
}

output "service_account_name" {
  description = "Name of the service account used by monitoring system"
  value       = local.use_prometheus ? module.prometheus[0].service_account_name : null
}

output "metrics_collection_interval" {
  description = "Interval in seconds at which metrics are collected"
  value       = local.metric_collection_interval
}

output "metrics_retention_days" {
  description = "Number of days metrics are retained in the monitoring system"
  value       = local.metrics_retention_days[var.environment]
}

#--------------------------------------------------------------
# Alert Thresholds
#--------------------------------------------------------------

output "alert_thresholds" {
  description = "Alert thresholds configured for various metrics"
  value       = local.alert_thresholds
}