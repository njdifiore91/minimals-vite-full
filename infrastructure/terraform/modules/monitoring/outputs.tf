# Outputs for the Prometheus and Grafana monitoring stack

output "prometheus_server_endpoint" {
  description = "The endpoint URL of the Prometheus server"
  value       = "http://prometheus-server.${var.namespace}.svc.cluster.local"
}

output "grafana_endpoint" {
  description = "The endpoint URL of the Grafana dashboard"
  value       = "http://prometheus-grafana.${var.namespace}.svc.cluster.local"
}

output "alertmanager_endpoint" {
  description = "The endpoint URL of the Alertmanager"
  value       = "http://prometheus-alertmanager.${var.namespace}.svc.cluster.local"
}

output "prometheus_namespace" {
  description = "The namespace where Prometheus is deployed"
  value       = local.namespace
}

output "grafana_admin_password" {
  description = "The admin password for Grafana"
  value       = var.grafana_admin_password
  sensitive   = true
}

output "prometheus_service_account" {
  description = "The service account used by Prometheus"
  value       = "prometheus-${var.prometheus_release_name}"
}

output "monitoring_enabled" {
  description = "Whether monitoring is enabled"
  value       = true
}

output "exporters_deployed" {
  description = "List of exporters that have been deployed"
  value       = [
    var.postgres_exporter_enabled ? "postgres-exporter" : null,
    var.rabbitmq_exporter_enabled ? "rabbitmq-exporter" : null,
    var.redis_exporter_enabled ? "redis-exporter" : null,
    var.cloudwatch_exporter_enabled ? "cloudwatch-exporter" : null
  ]
}

output "service_monitors_deployed" {
  description = "List of service monitors that have been deployed"
  value       = [
    var.email_service_monitor_enabled ? "email-service-monitor" : null,
    var.document_service_monitor_enabled ? "document-service-monitor" : null,
    var.ocr_service_monitor_enabled ? "ocr-service-monitor" : null,
    var.data_service_monitor_enabled ? "data-service-monitor" : null,
    var.notification_service_monitor_enabled ? "notification-service-monitor" : null,
    var.api_gateway_service_monitor_enabled ? "api-gateway-monitor" : null
  ]
}

output "grafana_ingress_hosts" {
  description = "The hosts configured for Grafana ingress"
  value       = var.grafana_ingress_enabled ? var.grafana_ingress_hosts : []
}

output "prometheus_retention_period" {
  description = "The data retention period for Prometheus"
  value       = var.prometheus_retention_period
}

output "prometheus_storage_size" {
  description = "The storage size allocated for Prometheus"
  value       = var.prometheus_storage_enabled ? var.prometheus_storage_size : "ephemeral"
}

output "grafana_storage_size" {
  description = "The storage size allocated for Grafana"
  value       = var.grafana_storage_enabled ? var.grafana_storage_size : "ephemeral"
}

output "prometheus_version" {
  description = "The version of Prometheus deployed"
  value       = var.prometheus_version
}

output "grafana_version" {
  description = "The version of Grafana deployed"
  value       = var.grafana_version
}

output "alertmanager_version" {
  description = "The version of Alertmanager deployed"
  value       = var.alertmanager_version
}