# Outputs for PostgreSQL Database Monitoring Configuration

output "monitoring_role_arn" {
  description = "ARN of the RDS enhanced monitoring IAM role"
  value       = aws_iam_role.rds_enhanced_monitoring.arn
}

output "monitoring_role_name" {
  description = "Name of the RDS enhanced monitoring IAM role"
  value       = aws_iam_role.rds_enhanced_monitoring.name
}

output "cloudwatch_log_groups" {
  description = "Map of CloudWatch Log Groups created for RDS logs"
  value = {
    postgresql = try(aws_cloudwatch_log_group.postgresql_logs.name, "")
    audit      = try(aws_cloudwatch_log_group.postgresql_audit_logs.name, "")
  }
}

output "cloudwatch_alarms" {
  description = "Map of CloudWatch Alarms created for RDS monitoring"
  value = {
    cpu_critical         = try(aws_cloudwatch_metric_alarm.database_cpu_critical[0].arn, "")
    cpu_warning          = try(aws_cloudwatch_metric_alarm.database_cpu_warning[0].arn, "")
    memory_critical      = try(aws_cloudwatch_metric_alarm.database_memory_critical[0].arn, "")
    connections_critical = try(aws_cloudwatch_metric_alarm.database_connections_critical[0].arn, "")
    disk_queue_critical  = try(aws_cloudwatch_metric_alarm.database_disk_queue_critical[0].arn, "")
    replica_lag_critical = try(aws_cloudwatch_metric_alarm.database_replica_lag_critical[0].arn, "")
  }
}

output "cloudwatch_dashboard_name" {
  description = "Name of the CloudWatch Dashboard created for RDS monitoring"
  value       = try(aws_cloudwatch_dashboard.database_dashboard[0].dashboard_name, "")
}

output "datadog_monitors" {
  description = "Map of Datadog Monitors created for RDS monitoring"
  value = {
    high_cpu          = try(datadog_monitor.postgres_high_cpu[0].id, "")
    connection_count  = try(datadog_monitor.postgres_connection_count[0].id, "")
    replica_lag       = try(datadog_monitor.postgres_replica_lag[0].id, "")
  }
}

output "datadog_dashboard_id" {
  description = "ID of the Datadog Dashboard created for RDS monitoring"
  value       = try(datadog_dashboard.postgres_dashboard[0].id, "")
}

output "monitoring_configuration" {
  description = "Monitoring configuration for RDS instances"
  value = {
    performance_insights_retention_period = local.performance_insights_retention_period
    monitoring_interval                   = local.monitoring_interval
    monitoring_role_arn                   = local.monitoring_role_arn
    enable_enhanced_monitoring            = local.enable_enhanced_monitoring
    enable_performance_insights           = local.enable_performance_insights
  }
}