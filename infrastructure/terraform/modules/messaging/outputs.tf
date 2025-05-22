# Outputs for RabbitMQ Messaging Module
#
# This file exports essential RabbitMQ information as module outputs,
# including connection endpoints, port numbers, virtual hosts, and resource identifiers.
# These outputs are consumed by other Terraform modules and application configuration.

# RabbitMQ cluster endpoints
output "rabbitmq_endpoints" {
  description = "The endpoints of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.instances.*.endpoints
}

# AMQP connection string for applications
output "amqp_connection_string" {
  description = "AMQP connection string for applications (without credentials)"
  value       = "amqp://${aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0}:5671/${var.rabbitmq_vhost}"
  sensitive   = false
}

# AMQPS (TLS) connection string for applications
output "amqps_connection_string" {
  description = "AMQPS (TLS) connection string for applications (without credentials)"
  value       = "amqps://${aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0}:5671/${var.rabbitmq_vhost}"
  sensitive   = false
}

# Management UI endpoint
output "management_endpoint" {
  description = "Management UI endpoint for RabbitMQ"
  value       = "https://${aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0}:15671"
  sensitive   = false
}

# RabbitMQ cluster ID
output "rabbitmq_cluster_id" {
  description = "The ID of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.id
}

# RabbitMQ cluster ARN
output "rabbitmq_cluster_arn" {
  description = "The ARN of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.arn
}

# RabbitMQ configuration ID
output "rabbitmq_config_id" {
  description = "The ID of the RabbitMQ configuration"
  value       = aws_mq_configuration.rabbitmq_config.id
}

# RabbitMQ configuration revision
output "rabbitmq_config_revision" {
  description = "The revision of the RabbitMQ configuration"
  value       = aws_mq_configuration.rabbitmq_config.latest_revision
}

# RabbitMQ virtual host
output "rabbitmq_vhost" {
  description = "The RabbitMQ virtual host"
  value       = var.rabbitmq_vhost
}

# RabbitMQ admin username
output "rabbitmq_admin_username" {
  description = "The RabbitMQ admin username"
  value       = var.rabbitmq_admin_username
  sensitive   = false
}

# Connection information for microservices
output "connection_info" {
  description = "Connection information for microservices (JSON format)"
  value = jsonencode({
    host      = aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0
    port      = 5671
    vhost     = var.rabbitmq_vhost
    use_tls   = true
    endpoints = aws_mq_broker.rabbitmq_cluster.instances.*.endpoints
  })
  sensitive = false
}

# CloudWatch alarm ARNs
output "cloudwatch_alarm_arns" {
  description = "ARNs of CloudWatch alarms for RabbitMQ"
  value = concat(
    [aws_cloudwatch_metric_alarm.rabbitmq_health.arn],
    aws_cloudwatch_metric_alarm.queue_depth.*.arn
  )
}

# DNS record (if created)
output "dns_record" {
  description = "DNS record for RabbitMQ cluster (if created)"
  value       = var.create_dns_record ? "rabbitmq.${var.dns_domain}" : null
}