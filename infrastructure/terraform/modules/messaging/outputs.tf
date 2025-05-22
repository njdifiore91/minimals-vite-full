# RabbitMQ Messaging Module Outputs
#
# This file exports essential RabbitMQ information as module outputs, including
# connection endpoints, port numbers, virtual hosts, and resource identifiers.
# These outputs are consumed by other Terraform modules and application configuration.

# Basic cluster information
output "cluster_id" {
  description = "The ID of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.id
}

output "cluster_arn" {
  description = "The ARN of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.arn
}

output "cluster_name" {
  description = "The name of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.broker_name
}

# Connection endpoints
output "amqp_endpoints" {
  description = "AMQP TLS endpoints for the RabbitMQ cluster"
  value       = [for instance in aws_mq_broker.rabbitmq_cluster.instances : instance.endpoints[0]]
}

output "primary_amqp_endpoint" {
  description = "Primary AMQP TLS endpoint for the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0]
}

# Management UI endpoints
output "management_endpoints" {
  description = "Management UI TLS endpoints for the RabbitMQ cluster"
  value       = [for instance in aws_mq_broker.rabbitmq_cluster.instances : instance.endpoints[1]]
}

output "primary_management_endpoint" {
  description = "Primary Management UI TLS endpoint for the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[1]
}

# Connection details
output "rabbitmq_vhost" {
  description = "RabbitMQ virtual host"
  value       = var.rabbitmq_vhost
}

output "rabbitmq_port" {
  description = "RabbitMQ AMQP TLS port"
  value       = 5671
}

output "rabbitmq_management_port" {
  description = "RabbitMQ Management UI TLS port"
  value       = 15671
}

# DNS information (if created)
output "dns_record" {
  description = "DNS record for the RabbitMQ cluster (if created)"
  value       = var.create_dns_record ? "rabbitmq.${var.dns_domain}" : null
}

# Connection string templates for different service types
output "connection_string_template" {
  description = "Generic connection string template for RabbitMQ (replace USERNAME and PASSWORD with actual credentials)"
  value       = "amqps://USERNAME:PASSWORD@${aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0]}:5671/${urlencode(var.rabbitmq_vhost)}"
  sensitive   = true
}

output "nodejs_amqplib_connection_config" {
  description = "Connection configuration object for Node.js amqplib 0.10.3"
  value       = jsonencode({
    protocol: "amqps",
    hostname: split(":", split("/", aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0])[2])[0],
    port: 5671,
    vhost: var.rabbitmq_vhost,
    username: "USERNAME", # Replace with actual username
    password: "PASSWORD", # Replace with actual password
    connectionOptions: {
      heartbeat: 60,
      timeout: 30000
    }
  })
  sensitive   = true
}

output "python_pika_connection_params" {
  description = "Connection parameters for Python Pika library"
  value       = jsonencode({
    host: split(":", split("/", aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0])[2])[0],
    port: 5671,
    virtual_host: var.rabbitmq_vhost,
    credentials: {
      username: "USERNAME", # Replace with actual username
      password: "PASSWORD"  # Replace with actual password
    },
    ssl: true,
    heartbeat: 60
  })
  sensitive   = true
}

output "java_spring_amqp_connection_properties" {
  description = "Connection properties for Java Spring AMQP"
  value       = jsonencode({
    "spring.rabbitmq.host": split(":", split("/", aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0])[2])[0],
    "spring.rabbitmq.port": 5671,
    "spring.rabbitmq.username": "USERNAME", # Replace with actual username
    "spring.rabbitmq.password": "PASSWORD", # Replace with actual password
    "spring.rabbitmq.virtual-host": var.rabbitmq_vhost,
    "spring.rabbitmq.ssl.enabled": true,
    "spring.rabbitmq.connection-timeout": 30000,
    "spring.rabbitmq.requested-heartbeat": 60
  })
  sensitive   = true
}

# Exchange and queue information
output "document_exchange" {
  description = "Name of the document exchange"
  value       = "mca.documents"
}

output "critical_queues" {
  description = "List of critical queue names"
  value       = var.critical_queues
}

# Monitoring and logging information
output "cloudwatch_log_group" {
  description = "CloudWatch log group for RabbitMQ logs"
  value       = aws_cloudwatch_log_group.rabbitmq_logs.name
}

output "cloudwatch_dashboard" {
  description = "CloudWatch dashboard for RabbitMQ monitoring"
  value       = aws_cloudwatch_dashboard.rabbitmq.dashboard_name
}

output "health_alarm_arn" {
  description = "ARN of the CloudWatch alarm for RabbitMQ cluster health"
  value       = aws_cloudwatch_metric_alarm.rabbitmq_health.arn
}

output "queue_depth_alarm_arns" {
  description = "ARNs of the CloudWatch alarms for queue depths"
  value       = [for alarm in aws_cloudwatch_metric_alarm.queue_depth : alarm.arn]
}

# Security information
output "security_group_id" {
  description = "ID of the security group for the RabbitMQ cluster"
  value       = var.security_group_id
}

output "kms_key_id" {
  description = "ID of the KMS key used for RabbitMQ encryption"
  value       = aws_kms_key.rabbitmq.key_id
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for RabbitMQ encryption"
  value       = aws_kms_key.rabbitmq.arn
}

# Recovery information
output "recovery_lambda_arn" {
  description = "ARN of the Lambda function for RabbitMQ recovery"
  value       = aws_lambda_function.rabbitmq_recovery.arn
}

# Environment information
output "environment" {
  description = "Environment name for the RabbitMQ cluster"
  value       = var.environment
}