# =============================================================================
# MCA Application Processing System - Messaging Infrastructure
# =============================================================================
# This file defines the main Terraform configuration for the RabbitMQ messaging
# infrastructure used by the MCA Application Processing System. It sets up a
# highly available RabbitMQ cluster with the required exchanges and queues for
# document processing, data extraction, and notifications.
# =============================================================================

terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
    rabbitmq = {
      source  = "cyrilgdn/rabbitmq"
      version = ">= 1.8.0"
    }
  }
}

# Local variables for RabbitMQ configuration
locals {
  # Environment-specific settings
  env_settings = {
    development = {
      cluster_size = 1
      instance_type = "mq.t3.micro"
      multi_az = false
      auto_minor_version_upgrade = true
    },
    staging = {
      cluster_size = 3
      instance_type = "mq.t3.small"
      multi_az = true
      auto_minor_version_upgrade = true
    },
    production = {
      cluster_size = 3
      instance_type = "mq.m5.large"
      multi_az = true
      auto_minor_version_upgrade = false
    }
  }
  
  # Use environment-specific settings or default to development
  settings = lookup(local.env_settings, var.environment, local.env_settings["development"])
  
  # Common tags for all resources
  common_tags = merge(var.tags, {
    Component = "Messaging"
    Service   = "RabbitMQ"
  })
  
  # RabbitMQ exchange and queue configuration
  exchanges = [
    {
      name = "mca.documents"
      type = "fanout"
      durable = true
      auto_delete = false
    }
  ]
  
  queues = [
    {
      name = "document-processing"
      durable = true
      auto_delete = false
      arguments = {
        "x-queue-type" = "classic"
        "x-ha-policy" = "all"
        "x-queue-mode" = "lazy"
      }
    },
    {
      name = "data-extraction"
      durable = true
      auto_delete = false
      arguments = {
        "x-queue-type" = "classic"
        "x-ha-policy" = "all"
        "x-queue-mode" = "lazy"
      }
    },
    {
      name = "notification"
      durable = true
      auto_delete = false
      arguments = {
        "x-queue-type" = "classic"
        "x-ha-policy" = "all"
        "x-queue-mode" = "lazy"
      }
    }
  ]
  
  bindings = [
    {
      queue = "document-processing"
      exchange = "mca.documents"
      routing_key = "document.#"
    },
    {
      queue = "data-extraction"
      exchange = "mca.documents"
      routing_key = "extraction.#"
    },
    {
      queue = "notification"
      exchange = "mca.documents"
      routing_key = "notification.#"
    }
  ]
}

# AWS MQ RabbitMQ broker resource
resource "aws_mq_broker" "rabbitmq" {
  broker_name = "mca-rabbitmq-${var.environment}"
  
  engine_type        = "RabbitMQ"
  engine_version     = "3.10.20"
  host_instance_type = local.settings.instance_type
  
  deployment_mode = local.settings.multi_az ? "CLUSTER_MULTI_AZ" : "SINGLE_INSTANCE"
  
  # Security settings
  security_groups    = [var.security_group_id]
  subnet_ids         = var.subnet_ids
  
  # Authentication
  authentication_strategy = "simple"
  users {
    username = var.username
    password = var.password
    
    # Grant admin access to the management console
    console_access = true
  }
  
  # Maintenance settings
  auto_minor_version_upgrade = local.settings.auto_minor_version_upgrade
  maintenance_window_start_time {
    day_of_week = "SUNDAY"
    time_of_day = "02:00"
    time_zone   = "UTC"
  }
  
  # Encryption settings
  encryption_options {
    use_aws_owned_key = false
    kms_key_id        = var.kms_key_id
  }
  
  # Logs
  logs {
    general = true
    audit   = true
  }
  
  # Apply common tags
  tags = local.common_tags
}

# Configure RabbitMQ provider to connect to the broker
provider "rabbitmq" {
  endpoint = "https://${aws_mq_broker.rabbitmq.instances[0].console_url}"
  username = var.username
  password = var.password
  
  # TLS settings
  insecure = false
  cacert_file = var.ca_cert_file
}

# Create exchanges
resource "rabbitmq_exchange" "exchanges" {
  count = length(local.exchanges)
  
  name  = local.exchanges[count.index].name
  vhost = "/"
  
  settings {
    type        = local.exchanges[count.index].type
    durable     = local.exchanges[count.index].durable
    auto_delete = local.exchanges[count.index].auto_delete
  }
  
  depends_on = [aws_mq_broker.rabbitmq]
}

# Create queues
resource "rabbitmq_queue" "queues" {
  count = length(local.queues)
  
  name  = local.queues[count.index].name
  vhost = "/"
  
  settings {
    durable     = local.queues[count.index].durable
    auto_delete = local.queues[count.index].auto_delete
    arguments   = local.queues[count.index].arguments
  }
  
  depends_on = [aws_mq_broker.rabbitmq]
}

# Create bindings between exchanges and queues
resource "rabbitmq_binding" "bindings" {
  count = length(local.bindings)
  
  source           = local.bindings[count.index].exchange
  destination      = local.bindings[count.index].queue
  destination_type = "queue"
  routing_key      = local.bindings[count.index].routing_key
  vhost            = "/"
  
  depends_on = [
    rabbitmq_exchange.exchanges,
    rabbitmq_queue.queues
  ]
}

# CloudWatch alarms for monitoring RabbitMQ
resource "aws_cloudwatch_metric_alarm" "rabbitmq_cpu" {
  alarm_name          = "mca-rabbitmq-${var.environment}-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CpuUtilization"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This alarm monitors RabbitMQ CPU utilization"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq.id
  }
  
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "rabbitmq_memory" {
  alarm_name          = "mca-rabbitmq-${var.environment}-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HeapUsage"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This alarm monitors RabbitMQ memory utilization"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq.id
  }
  
  tags = local.common_tags
}

# Output the RabbitMQ connection information
output "endpoint" {
  description = "The connection endpoint for the RabbitMQ broker"
  value       = "amqps://${aws_mq_broker.rabbitmq.instances[0].endpoints[0]}"
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