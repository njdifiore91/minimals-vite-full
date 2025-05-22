# Outputs for the monitoring module
# These outputs provide access to monitoring dashboards, API endpoints, and resource identifiers
# for both Datadog and Prometheus/Grafana monitoring solutions

# Common outputs regardless of monitoring type
output "monitoring_type" {
  description = "The type of monitoring solution deployed (datadog or prometheus)"
  value       = var.monitoring_type
}

output "monitoring_namespace" {
  description = "Kubernetes namespace where monitoring resources are deployed"
  value       = var.monitoring_namespace
}

output "environment" {
  description = "Deployment environment (development, staging, production)"
  value       = var.environment
}

# Datadog-specific outputs
output "datadog_dashboard_url" {
  description = "URL to the main Datadog dashboard for the MCA application"
  value       = var.monitoring_type == "datadog" ? "https://app.${var.datadog_site}/dashboard/mca-application-overview" : null
}

output "datadog_api_url" {
  description = "Datadog API URL for programmatic access"
  value       = var.monitoring_type == "datadog" ? "https://api.${var.datadog_site}" : null
}

output "datadog_app_key_secret_name" {
  description = "Name of the Kubernetes secret containing Datadog API and application keys"
  value       = var.monitoring_type == "datadog" ? "datadog-api-key" : null
  sensitive   = true
}

output "datadog_monitors" {
  description = "Map of Datadog monitor IDs by monitor name"
  value       = var.monitoring_type == "datadog" ? {
    application_processing_time = try(datadog_monitor.application_processing_time[0].id, null)
    ocr_accuracy                = try(datadog_monitor.ocr_accuracy[0].id, null)
    queue_depth                 = try(datadog_monitor.queue_depth[0].id, null)
    api_response_time           = try(datadog_monitor.api_response_time[0].id, null)
  } : null
}

output "datadog_slos" {
  description = "Map of Datadog SLO IDs by SLO name"
  value       = var.monitoring_type == "datadog" ? {
    application_processing_time = try(datadog_service_level_objective.application_processing_time_slo[0].id, null)
    ocr_accuracy                = try(datadog_service_level_objective.ocr_accuracy_slo[0].id, null)
    api_availability            = try(datadog_service_level_objective.api_availability_slo[0].id, null)
  } : null
}

output "datadog_dashboard_id" {
  description = "ID of the main Datadog dashboard for the MCA application"
  value       = var.monitoring_type == "datadog" ? try(datadog_dashboard.mca_application[0].id, null) : null
}

output "datadog_agent_helm_release" {
  description = "Name of the Helm release for the Datadog agent"
  value       = var.monitoring_type == "datadog" ? try(helm_release.datadog[0].name, null) : null
}

# Prometheus/Grafana-specific outputs
output "grafana_url" {
  description = "URL to the Grafana dashboard for the MCA application"
  value       = var.monitoring_type == "prometheus" && var.grafana_ingress_enabled ? "https://${var.grafana_hostname}" : null
}

output "prometheus_operator_helm_release" {
  description = "Name of the Helm release for the Prometheus Operator"
  value       = var.monitoring_type == "prometheus" ? try(helm_release.prometheus_operator[0].name, null) : null
}

output "prometheus_server_endpoint" {
  description = "Internal Kubernetes endpoint for the Prometheus server"
  value       = var.monitoring_type == "prometheus" ? "prometheus-operator-kube-p-prometheus.${var.monitoring_namespace}.svc.cluster.local:9090" : null
}

output "alertmanager_endpoint" {
  description = "Internal Kubernetes endpoint for the Alertmanager"
  value       = var.monitoring_type == "prometheus" ? "prometheus-operator-kube-p-alertmanager.${var.monitoring_namespace}.svc.cluster.local:9093" : null
}

output "grafana_admin_password_secret" {
  description = "Name of the Kubernetes secret containing the Grafana admin password"
  value       = var.monitoring_type == "prometheus" ? "prometheus-operator-grafana" : null
  sensitive   = true
}

output "service_monitors" {
  description = "Map of ServiceMonitor names by service"
  value       = var.monitoring_type == "prometheus" ? {
    email_service        = try(kubernetes_service_monitor.email_service[0].metadata[0].name, null)
    document_service     = try(kubernetes_service_monitor.document_service[0].metadata[0].name, null)
    ocr_service          = try(kubernetes_service_monitor.ocr_service[0].metadata[0].name, null)
    data_service         = try(kubernetes_service_monitor.data_service[0].metadata[0].name, null)
    notification_service = try(kubernetes_service_monitor.notification_service[0].metadata[0].name, null)
    api_gateway          = try(kubernetes_service_monitor.api_gateway[0].metadata[0].name, null)
    postgres_exporter    = "postgres-exporter"
    rabbitmq_exporter    = "rabbitmq-exporter"
    redis_exporter       = "redis-exporter"
    s3_exporter          = try(kubernetes_service_monitor.s3_exporter[0].metadata[0].name, null)
  } : null
}

output "exporters" {
  description = "Map of exporter Helm release names"
  value       = var.monitoring_type == "prometheus" ? {
    postgres = try(helm_release.postgres_exporter[0].name, null)
    rabbitmq = try(helm_release.rabbitmq_exporter[0].name, null)
    redis    = try(helm_release.redis_exporter[0].name, null)
    s3       = "s3-exporter"
  } : null
}

# Common outputs for integration with other infrastructure components
output "metrics_endpoint" {
  description = "Endpoint for scraping metrics, varies by monitoring solution"
  value       = var.monitoring_type == "datadog" ? "https://api.${var.datadog_site}/api/v1/metrics" : "http://prometheus-operator-kube-p-prometheus.${var.monitoring_namespace}.svc.cluster.local:9090/api/v1/query"
}

output "logs_endpoint" {
  description = "Endpoint for sending logs, varies by monitoring solution"
  value       = var.monitoring_type == "datadog" ? "https://http-intake.logs.${var.datadog_site}/api/v2/logs" : null
}

output "traces_endpoint" {
  description = "Endpoint for sending traces, varies by monitoring solution"
  value       = var.monitoring_type == "datadog" ? "https://trace.agent.${var.datadog_site}:4317" : null
}

output "monitoring_tags" {
  description = "Tags to apply to resources for proper monitoring integration"
  value       = var.monitoring_type == "datadog" ? [
    "env:${var.environment}",
    "cluster:${var.cluster_name}",
    "managed-by:terraform"
  ] : {
    app         = "mca-monitoring"
    environment = var.environment
    managed_by  = "terraform"
  }
}

output "monitoring_documentation" {
  description = "URL to the monitoring documentation"
  value       = var.monitoring_type == "datadog" ? "https://docs.datadoghq.com" : "https://prometheus.io/docs/introduction/overview/"
}

output "monitoring_status" {
  description = "Status of the monitoring deployment"
  value       = var.monitoring_type == "datadog" ? (
    try(helm_release.datadog[0].status, "not_deployed")
  ) : (
    try(helm_release.prometheus_operator[0].status, "not_deployed")
  )
}