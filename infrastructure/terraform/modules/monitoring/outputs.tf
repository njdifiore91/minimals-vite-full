# Outputs for the monitoring module
# These outputs provide access to monitoring endpoints and resources

# Prometheus outputs
output "prometheus_server_endpoint" {
  description = "Prometheus server endpoint URL"
  value       = var.monitoring_type == "prometheus" ? "http://prometheus-operator-kube-prometheus-prometheus.${var.monitoring_namespace}.svc.cluster.local:9090" : null
}

output "prometheus_alertmanager_endpoint" {
  description = "Prometheus AlertManager endpoint URL"
  value       = var.monitoring_type == "prometheus" ? "http://prometheus-operator-kube-prometheus-alertmanager.${var.monitoring_namespace}.svc.cluster.local:9093" : null
}

output "grafana_endpoint" {
  description = "Grafana endpoint URL"
  value       = var.monitoring_type == "prometheus" ? "http://prometheus-operator-grafana.${var.monitoring_namespace}.svc.cluster.local:80" : null
}

output "grafana_external_url" {
  description = "Grafana external URL (if Ingress is enabled)"
  value       = var.monitoring_type == "prometheus" && var.grafana_ingress_enabled ? "https://${var.grafana_hostname}" : null
}

output "prometheus_operator_crds" {
  description = "List of CRDs created by Prometheus Operator"
  value       = var.monitoring_type == "prometheus" ? [
    "alertmanagerconfigs.monitoring.coreos.com",
    "alertmanagers.monitoring.coreos.com",
    "podmonitors.monitoring.coreos.com",
    "probes.monitoring.coreos.com",
    "prometheuses.monitoring.coreos.com",
    "prometheusrules.monitoring.coreos.com",
    "servicemonitors.monitoring.coreos.com",
    "thanosrulers.monitoring.coreos.com"
  ] : null
}

output "monitoring_namespace" {
  description = "Kubernetes namespace where monitoring resources are deployed"
  value       = var.monitoring_namespace
}

output "monitoring_type" {
  description = "Type of monitoring solution deployed"
  value       = var.monitoring_type
}

# Common outputs for both monitoring types
output "monitoring_enabled" {
  description = "Whether monitoring is enabled"
  value       = true
}

output "monitoring_labels" {
  description = "Common labels used for monitoring resources"
  value       = {
    app         = "mca-monitoring"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# Datadog outputs
output "datadog_dashboard_url" {
  description = "URL to the main Datadog dashboard"
  value       = var.monitoring_type == "datadog" ? "https://app.${var.datadog_site}/dashboard/mca-application-overview" : null
}

output "datadog_monitors" {
  description = "List of Datadog monitor IDs created"
  value       = var.monitoring_type == "datadog" ? {
    application_processing_time = try(datadog_monitor.application_processing_time[0].id, null)
    ocr_accuracy                = try(datadog_monitor.ocr_accuracy[0].id, null)
    queue_depth                 = try(datadog_monitor.queue_depth[0].id, null)
    api_response_time           = try(datadog_monitor.api_response_time[0].id, null)
  } : null
}

output "datadog_slos" {
  description = "List of Datadog SLO IDs created"
  value       = var.monitoring_type == "datadog" ? {
    application_processing_time = try(datadog_service_level_objective.application_processing_time_slo[0].id, null)
    ocr_accuracy                = try(datadog_service_level_objective.ocr_accuracy_slo[0].id, null)
    api_availability            = try(datadog_service_level_objective.api_availability_slo[0].id, null)
  } : null
}

output "datadog_agent_namespace" {
  description = "Kubernetes namespace where Datadog agent is deployed"
  value       = var.monitoring_type == "datadog" ? kubernetes_namespace.datadog[0].metadata[0].name : null
}