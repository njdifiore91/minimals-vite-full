# RabbitMQ Messaging Infrastructure for MCA Application Processing System
#
# This is the primary Terraform configuration file for the RabbitMQ messaging infrastructure.
# It defines the main RabbitMQ cluster with high availability, disk-based persistence,
# mirrored queues, and environment-specific settings to support the MCA document processing pipeline.
#
# Key features:
# - 3-node RabbitMQ cluster for high availability (99.9% uptime)
# - Disk-based persistence for message durability
# - Mirrored queues across all nodes for redundancy
# - Environment-specific resource allocation
# - Integration with monitoring and alerting systems
# - Support for the complete MCA document processing pipeline

# Local variables for environment-specific settings
locals {
  # Environment-specific node count
  node_count = {
    development = 1
    staging     = 3
    production  = 3
  }

  # Environment-specific instance types
  instance_type = {
    development = "t3.medium"
    staging     = "m5.large"
    production  = "m5.xlarge"
  }

  # Environment-specific storage sizes
  storage_size = {
    development = 50
    staging     = 100
    production  = 200
  }

  # Environment-specific queue settings
  queue_settings = {
    development = {
      max_length = 10000
      ttl        = 86400000  # 24 hours in milliseconds
    }
    staging = {
      max_length = 50000
      ttl        = 86400000  # 24 hours in milliseconds
    }
    production = {
      max_length = 100000
      ttl        = 86400000  # 24 hours in milliseconds
    }
  }

  # Common tags for all resources
  common_tags = merge(var.tags, {
    Environment = var.environment
    Service     = "mca-messaging"
    ManagedBy   = "terraform"
  })

  # Determine if this is a multi-AZ deployment
  is_multi_az = var.environment != "development"

  # Determine actual cluster size based on environment
  actual_cluster_size = local.is_multi_az ? var.cluster_size : 1

  # Determine actual instance type based on environment
  actual_instance_type = lookup(local.instance_type, var.environment, var.instance_type)

  # Determine actual storage size based on environment
  actual_storage_size = lookup(local.storage_size, var.environment, var.storage_size)
}

# Data source to get the current AWS region
data "aws_region" "current" {}

# Data source to get the current AWS account ID
data "aws_caller_identity" "current" {}

# AWS RabbitMQ cluster configuration
resource "aws_mq_broker" "rabbitmq_cluster" {
  broker_name        = "${var.environment}-${var.cluster_name}"
  engine_type        = "RabbitMQ"
  engine_version     = var.rabbitmq_version
  host_instance_type = local.actual_instance_type
  
  # Configure deployment mode based on environment
  deployment_mode    = local.is_multi_az ? "CLUSTER_MULTI_AZ" : "SINGLE_INSTANCE"
  
  # Security settings will be configured in security.tf
  publicly_accessible = false
  
  # Authentication
  users {
    username = var.admin_username
    password = var.admin_password
    console_access = true
  }

  # Configure maintenance window during off-peak hours
  maintenance_window_start_time {
    day_of_week = "SUNDAY"
    time_of_day = "02:00"
    time_zone   = "UTC"
  }

  # Enable CloudWatch logs
  logs {
    general = true
    audit   = var.environment == "production" ? true : false
  }

  # Apply tags for resource management
  tags = local.common_tags

  # Advanced broker configuration
  configuration {
    id       = aws_mq_configuration.rabbitmq_config.id
    revision = aws_mq_configuration.rabbitmq_config.latest_revision
  }
}

# RabbitMQ configuration resource for advanced settings
resource "aws_mq_configuration" "rabbitmq_config" {
  name           = "${var.environment}-${var.cluster_name}-config"
  engine_type    = "RabbitMQ"
  engine_version = var.rabbitmq_version
  
  # RabbitMQ configuration in JSON format
  data = jsonencode({
    # Configure quorum queues as the default queue type for high availability
    "rabbitmq.conf" = {
      # Default queue type set to quorum for high availability
      "default_queue_type" = "quorum"
      
      # Quorum queue settings for high availability
      "quorum_queue.max_in_memory_length" = 10000
      "quorum_queue.max_in_memory_bytes" = 104857600  # 100MB
      
      # Cluster partition handling strategy
      "cluster_partition_handling" = "pause_minority"
      
      # Heartbeat and connection timeout settings
      "heartbeat" = 60
      "vm_memory_high_watermark.relative" = var.memory_high_watermark
      
      # Enable management plugins
      "management.load_definitions" = "/etc/rabbitmq/definitions.json"
      "management.disable_stats" = false
      "management.enable_queue_totals" = true
      
      # TLS/SSL settings if enabled
      "listeners.ssl.default" = var.enable_tls ? 5671 : null
      "ssl_options.cacertfile" = var.enable_tls ? "/etc/rabbitmq/ca_certificate.pem" : null
      "ssl_options.certfile" = var.enable_tls ? "/etc/rabbitmq/server_certificate.pem" : null
      "ssl_options.keyfile" = var.enable_tls ? "/etc/rabbitmq/server_key.pem" : null
      "ssl_options.verify" = var.enable_tls ? "verify_peer" : null
      "ssl_options.fail_if_no_peer_cert" = var.enable_tls ? false : null
    }
  })
  
  # Apply tags for resource management
  tags = local.common_tags
}

# CloudWatch alarm for cluster health monitoring
resource "aws_cloudwatch_metric_alarm" "rabbitmq_health" {
  count               = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.environment}-${var.cluster_name}-health"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "RabbitMQClusterStatus"
  namespace           = "AWS/MQ"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "This alarm monitors RabbitMQ cluster health"
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
  }
  
  # Alarm actions would be defined in variables or in a separate module
}

# CloudWatch alarm for queue depth monitoring
resource "aws_cloudwatch_metric_alarm" "queue_depth" {
  count               = var.enable_monitoring ? length(["document-processing", "data-extraction", "notification"]) : 0
  
  alarm_name          = "${var.environment}-${var.cluster_name}-queue-depth-${element(["document-processing", "data-extraction", "notification"], count.index)}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "QueueDepth"
  namespace           = "AWS/MQ"
  period              = 60
  statistic           = "Maximum"
  threshold           = var.environment == "production" ? 1000 : 5000
  alarm_description   = "This alarm monitors the depth of the ${element(["document-processing", "data-extraction", "notification"], count.index)} queue"
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
    Queue  = element(["document-processing", "data-extraction", "notification"], count.index)
    VirtualHost = "/"
  }
  
  # Alarm actions would be defined in variables or in a separate module
}

# CloudWatch dashboard for RabbitMQ monitoring
resource "aws_cloudwatch_dashboard" "rabbitmq" {
  count          = var.enable_monitoring && var.enable_dashboard ? 1 : 0
  dashboard_name = "${var.environment}-${var.cluster_name}-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/MQ", "RabbitMQClusterStatus", "Broker", aws_mq_broker.rabbitmq_cluster.id]
          ]
          period = 60
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "RabbitMQ Cluster Status"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/MQ", "ConnectionCount", "Broker", aws_mq_broker.rabbitmq_cluster.id]
          ]
          period = 60
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "RabbitMQ Connection Count"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          metrics = [
            ["AWS/MQ", "QueueDepth", "Broker", aws_mq_broker.rabbitmq_cluster.id, "Queue", "document-processing", "VirtualHost", "/"],
            ["AWS/MQ", "QueueDepth", "Broker", aws_mq_broker.rabbitmq_cluster.id, "Queue", "data-extraction", "VirtualHost", "/"],
            ["AWS/MQ", "QueueDepth", "Broker", aws_mq_broker.rabbitmq_cluster.id, "Queue", "notification", "VirtualHost", "/"]
          ]
          period = 60
          stat   = "Maximum"
          region = data.aws_region.current.name
          title  = "Queue Depths"
        }
      }
    ]
  })
}

# Auto recovery lambda function for RabbitMQ cluster (production only)
resource "aws_lambda_function" "rabbitmq_recovery" {
  count           = var.environment == "production" ? 1 : 0
  function_name   = "${var.environment}-${var.cluster_name}-recovery"
  role            = aws_iam_role.rabbitmq_recovery[0].arn
  handler         = "index.handler"
  runtime         = "nodejs18.x"
  timeout         = 300
  memory_size     = 128
  
  # This would typically point to a Lambda deployment package
  filename        = "${path.module}/files/rabbitmq-recovery.zip"
  source_code_hash = filebase64sha256("${path.module}/files/rabbitmq-recovery.zip")
  
  environment {
    variables = {
      BROKER_ID = aws_mq_broker.rabbitmq_cluster.id
      REGION    = data.aws_region.current.name
    }
  }
  
  tags = local.common_tags
}

# IAM role for RabbitMQ recovery lambda (production only)
resource "aws_iam_role" "rabbitmq_recovery" {
  count = var.environment == "production" ? 1 : 0
  name  = "${var.environment}-${var.cluster_name}-recovery-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

# IAM policy for RabbitMQ recovery lambda (production only)
resource "aws_iam_policy" "rabbitmq_recovery" {
  count       = var.environment == "production" ? 1 : 0
  name        = "${var.environment}-${var.cluster_name}-recovery-policy"
  description = "Policy for RabbitMQ recovery lambda"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "mq:RebootBroker",
          "mq:DescribeBroker"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Attach IAM policy to IAM role for RabbitMQ recovery (production only)
resource "aws_iam_role_policy_attachment" "rabbitmq_recovery" {
  count      = var.environment == "production" ? 1 : 0
  role       = aws_iam_role.rabbitmq_recovery[0].name
  policy_arn = aws_iam_policy.rabbitmq_recovery[0].arn
}