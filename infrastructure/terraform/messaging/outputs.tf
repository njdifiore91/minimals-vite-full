# =============================================================================
# MCA Application Processing System - Messaging Outputs
# =============================================================================
# This file defines all outputs from the RabbitMQ messaging module, including
# connection endpoints, management console URLs, and resource identifiers.
# =============================================================================

output "endpoint" {
  description = "The AMQP connection endpoint for the RabbitMQ broker"
  value       = "amqps://${aws_mq_broker.rabbitmq.instances[0].endpoints[0]}"
  sensitive   = true
}

output "endpoints" {
  description = "All AMQP connection endpoints for the RabbitMQ broker"
  value       = [for instance in aws_mq_broker.rabbitmq.instances : "amqps://${instance.endpoints[0]}"]
  sensitive   = true
}

output "management_console_url" {
  description = "The URL of the RabbitMQ management console"
  value       = "https://${aws_mq_broker.rabbitmq.instances[0].console_url}"
  sensitive   = true
}

output "broker_id" {
  description = "The ID of the RabbitMQ broker"
  value       = aws_mq_broker.rabbitmq.id
}

output "broker_arn" {
  description = "The ARN of the RabbitMQ broker"
  value       = aws_mq_broker.rabbitmq.arn
}

output "connection_string_template" {
  description = "Template for constructing a connection string with credentials"
  value       = "amqps://{username}:{password}@${aws_mq_broker.rabbitmq.instances[0].endpoints[0]}"
  sensitive   = true
}

output "exchanges" {
  description = "List of RabbitMQ exchanges created"
  value       = [for exchange in rabbitmq_exchange.exchanges : exchange.name]
}

output "queues" {
  description = "List of RabbitMQ queues created"
  value       = [for queue in rabbitmq_queue.queues : queue.name]
}

output "cloudwatch_alarms" {
  description = "List of CloudWatch alarms for RabbitMQ monitoring"
  value       = [
    aws_cloudwatch_metric_alarm.rabbitmq_cpu.arn,
    aws_cloudwatch_metric_alarm.rabbitmq_memory.arn
  ]
}