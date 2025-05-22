# -----------------------------------------------------------------------------
# RabbitMQ Terraform Outputs for MCA Application Processing System
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Connection Information
# -----------------------------------------------------------------------------

output "rabbitmq_endpoints" {
  description = "The broker's wire-level protocol endpoints for all cluster nodes"
  value       = aws_mq_broker.rabbitmq_cluster.instances.*.endpoints
}

output "rabbitmq_amqp_endpoint" {
  description = "The AMQP TLS endpoint for the RabbitMQ broker (primary node)"
  value       = "amqps://${aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0}"
}

output "rabbitmq_connection_string" {
  description = "The connection string for RabbitMQ clients (without credentials)"
  value       = "amqps://${aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0}?heartbeat=30&connection_timeout=5000"
  sensitive   = false
}

output "rabbitmq_connection_string_with_credentials" {
  description = "The connection string for RabbitMQ clients (with credentials)"
  value       = "amqps://${var.rabbitmq_admin_username}:${var.rabbitmq_admin_password}@${aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0}?heartbeat=30&connection_timeout=5000"
  sensitive   = true
}

output "rabbitmq_host" {
  description = "The hostname of the primary RabbitMQ node"
  value       = split(":", aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0)[0]
}

output "rabbitmq_port" {
  description = "The AMQP TLS port for the RabbitMQ broker"
  value       = 5671
}

# -----------------------------------------------------------------------------
# Cluster Node Details
# -----------------------------------------------------------------------------

output "rabbitmq_cluster_nodes" {
  description = "List of all RabbitMQ cluster nodes"
  value       = aws_mq_broker.rabbitmq_cluster.instances
}

output "rabbitmq_primary_node" {
  description = "Details of the primary RabbitMQ node"
  value       = aws_mq_broker.rabbitmq_cluster.instances.0
}

output "rabbitmq_console_url" {
  description = "The URL of the RabbitMQ web console"
  value       = "https://${aws_mq_broker.rabbitmq_cluster.instances.0.console_url}"
}

output "rabbitmq_deployment_mode" {
  description = "The deployment mode of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.deployment_mode
}

# -----------------------------------------------------------------------------
# Exchange and Queue Information
# -----------------------------------------------------------------------------

output "rabbitmq_exchange_name" {
  description = "The name of the main document exchange"
  value       = rabbitmq_exchange.mca_documents.name
}

output "rabbitmq_exchange_type" {
  description = "The type of the main document exchange"
  value       = "fanout"
}

output "rabbitmq_queues" {
  description = "Map of queue names and their configurations"
  value = {
    document_processing = {
      name = rabbitmq_queue.document_processing.name
      durable = true
      lazy_mode = true
      message_ttl = 604800000 # 7 days in milliseconds
    },
    data_extraction = {
      name = rabbitmq_queue.data_extraction.name
      durable = true
      lazy_mode = true
      message_ttl = 604800000 # 7 days in milliseconds
    },
    notification = {
      name = rabbitmq_queue.notification.name
      durable = true
      lazy_mode = true
      message_ttl = 604800000 # 7 days in milliseconds
    }
  }
}

output "rabbitmq_vhost" {
  description = "The virtual host used for RabbitMQ resources"
  value       = "/"
}

# -----------------------------------------------------------------------------
# Security Group and Network Information
# -----------------------------------------------------------------------------

output "rabbitmq_security_group_id" {
  description = "The ID of the security group for the RabbitMQ cluster"
  value       = aws_security_group.rabbitmq_sg.id
}

output "rabbitmq_subnet_ids" {
  description = "The subnet IDs where the RabbitMQ cluster is deployed"
  value       = var.private_subnet_ids
}

output "rabbitmq_vpc_id" {
  description = "The VPC ID where the RabbitMQ cluster is deployed"
  value       = var.vpc_id
}

# -----------------------------------------------------------------------------
# Resource IDs
# -----------------------------------------------------------------------------

output "rabbitmq_id" {
  description = "The ID of the RabbitMQ broker"
  value       = aws_mq_broker.rabbitmq_cluster.id
}

output "rabbitmq_arn" {
  description = "The ARN of the RabbitMQ broker"
  value       = aws_mq_broker.rabbitmq_cluster.arn
}

output "rabbitmq_policy_id" {
  description = "The ID of the RabbitMQ HA policy"
  value       = rabbitmq_policy.ha_policy.id
}

# -----------------------------------------------------------------------------
# Monitoring Information
# -----------------------------------------------------------------------------

output "rabbitmq_cloudwatch_alarms" {
  description = "Map of CloudWatch alarms for RabbitMQ monitoring"
  value = {
    cpu_utilization = {
      name = aws_cloudwatch_metric_alarm.rabbitmq_cpu_utilization.alarm_name
      arn  = aws_cloudwatch_metric_alarm.rabbitmq_cpu_utilization.arn
    },
    memory_usage = {
      name = aws_cloudwatch_metric_alarm.rabbitmq_memory_usage.alarm_name
      arn  = aws_cloudwatch_metric_alarm.rabbitmq_memory_usage.arn
    },
    queue_depth = {
      name = aws_cloudwatch_metric_alarm.rabbitmq_queue_depth.alarm_name
      arn  = aws_cloudwatch_metric_alarm.rabbitmq_queue_depth.arn
    }
  }
}

output "rabbitmq_logs_enabled" {
  description = "Whether general and audit logs are enabled for the RabbitMQ broker"
  value = {
    general = aws_mq_broker.rabbitmq_cluster.logs[0].general
    audit   = aws_mq_broker.rabbitmq_cluster.logs[0].audit
  }
}

output "rabbitmq_maintenance_window" {
  description = "The maintenance window configuration for the RabbitMQ broker"
  value = {
    day_of_week = aws_mq_broker.rabbitmq_cluster.maintenance_window_start_time[0].day_of_week
    time_of_day = aws_mq_broker.rabbitmq_cluster.maintenance_window_start_time[0].time_of_day
    time_zone   = aws_mq_broker.rabbitmq_cluster.maintenance_window_start_time[0].time_zone
  }
}

# -----------------------------------------------------------------------------
# Service Integration Information
# -----------------------------------------------------------------------------

output "rabbitmq_service_integration" {
  description = "Integration information for microservices"
  value = {
    amqp_endpoint = "amqps://${aws_mq_broker.rabbitmq_cluster.instances.0.endpoints.0}"
    exchange_name = rabbitmq_exchange.mca_documents.name
    queues = {
      document_processing = rabbitmq_queue.document_processing.name
      data_extraction = rabbitmq_queue.data_extraction.name
      notification = rabbitmq_queue.notification.name
    }
    vhost = "/"
    port = 5671
    tls_required = true
  }
}