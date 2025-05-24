# RabbitMQ Terraform Configuration for MCA Application Processing System

# -----------------------------------------------------------------------------
# Amazon MQ RabbitMQ Broker Configuration
# -----------------------------------------------------------------------------

resource "aws_mq_broker" "rabbitmq_cluster" {
  broker_name        = "mca-rabbitmq-cluster"
  engine_type        = "RabbitMQ"
  engine_version     = "3.11.20"
  host_instance_type = "mq.m5.large"
  security_groups    = [aws_security_group.rabbitmq_sg.id]
  subnet_ids         = var.private_subnet_ids

  # Configure multi-AZ deployment with 3 nodes for high availability
  deployment_mode = "CLUSTER_MULTI_AZ"

  # Enable automatic minor version upgrades
  auto_minor_version_upgrade = true

  # Configure maintenance window during off-peak hours
  maintenance_window_start_time {
    day_of_week = "Sunday"
    time_of_day = "02:00"
    time_zone   = "UTC"
  }

  # Configure logs
  logs {
    general = true
    audit   = true
  }

  # Configure user credentials
  user {
    username = var.rabbitmq_admin_username
    password = var.rabbitmq_admin_password
  }

  # Apply changes immediately
  apply_immediately = true

  # Add tags
  tags = {
    Name        = "mca-rabbitmq-cluster"
    Environment = var.environment
    Service     = "mca-application-processing"
    Managed     = "terraform"
  }
}

# -----------------------------------------------------------------------------
# Security Group for RabbitMQ
# -----------------------------------------------------------------------------

resource "aws_security_group" "rabbitmq_sg" {
  name        = "mca-rabbitmq-sg"
  description = "Security group for RabbitMQ cluster"
  vpc_id      = var.vpc_id

  # AMQP protocol
  ingress {
    from_port       = 5671
    to_port         = 5671
    protocol        = "tcp"
    security_groups = var.service_security_group_ids
    description     = "AMQP TLS"
  }

  # Management UI
  ingress {
    from_port       = 15671
    to_port         = 15671
    protocol        = "tcp"
    security_groups = var.management_security_group_ids
    description     = "Management UI TLS"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "mca-rabbitmq-sg"
    Environment = var.environment
    Service     = "mca-application-processing"
    Managed     = "terraform"
  }
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms for RabbitMQ Monitoring
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "rabbitmq_cpu_utilization" {
  alarm_name          = "mca-rabbitmq-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CpuUtilization"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This metric monitors RabbitMQ CPU utilization"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]

  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
  }

  tags = {
    Name        = "mca-rabbitmq-cpu-utilization"
    Environment = var.environment
    Service     = "mca-application-processing"
    Managed     = "terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "rabbitmq_memory_usage" {
  alarm_name          = "mca-rabbitmq-memory-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HeapUsage"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This metric monitors RabbitMQ memory usage"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]

  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
  }

  tags = {
    Name        = "mca-rabbitmq-memory-usage"
    Environment = var.environment
    Service     = "mca-application-processing"
    Managed     = "terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "rabbitmq_queue_depth" {
  alarm_name          = "mca-rabbitmq-queue-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "QueueDepth"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Maximum"
  threshold           = 10000
  alarm_description   = "This metric monitors RabbitMQ queue depth"
  alarm_actions       = [var.sns_topic_arn]
  ok_actions          = [var.sns_topic_arn]

  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
    Queue  = "*"
    VirtualHost = "*"
  }

  tags = {
    Name        = "mca-rabbitmq-queue-depth"
    Environment = var.environment
    Service     = "mca-application-processing"
    Managed     = "terraform"
  }
}

# -----------------------------------------------------------------------------
# RabbitMQ Provider Configuration
# -----------------------------------------------------------------------------

provider "rabbitmq" {
  endpoint = "https://${aws_mq_broker.rabbitmq_cluster.instances.0.console_url}"
  username = var.rabbitmq_admin_username
  password = var.rabbitmq_admin_password
  insecure = false
}

# -----------------------------------------------------------------------------
# RabbitMQ Exchange, Queue, and Binding Configuration
# -----------------------------------------------------------------------------

# Create the main exchange for document processing
resource "rabbitmq_exchange" "mca_documents" {
  name  = "mca.documents"
  vhost = "/"

  settings {
    type        = "fanout"
    durable     = true
    auto_delete = false
  }

  # Ensure the broker is fully provisioned before configuring exchanges
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create document processing queue
resource "rabbitmq_queue" "document_processing" {
  name  = "document-processing"
  vhost = "/"

  settings {
    durable     = true
    auto_delete = false
    arguments = {
      # Configure as lazy queue to optimize memory usage for large messages
      "x-queue-mode" = "lazy"
      # Configure queue mirroring for high availability
      "x-ha-policy" = "all"
      # Enable automatic synchronization of mirrored queues
      "x-ha-sync-mode" = "automatic"
      # Set message TTL to 7 days (in milliseconds)
      "x-message-ttl" = 604800000
    }
  }

  # Ensure the broker is fully provisioned before configuring queues
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create data extraction queue
resource "rabbitmq_queue" "data_extraction" {
  name  = "data-extraction"
  vhost = "/"

  settings {
    durable     = true
    auto_delete = false
    arguments = {
      # Configure as lazy queue to optimize memory usage for large messages
      "x-queue-mode" = "lazy"
      # Configure queue mirroring for high availability
      "x-ha-policy" = "all"
      # Enable automatic synchronization of mirrored queues
      "x-ha-sync-mode" = "automatic"
      # Set message TTL to 7 days (in milliseconds)
      "x-message-ttl" = 604800000
    }
  }

  # Ensure the broker is fully provisioned before configuring queues
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create notification queue
resource "rabbitmq_queue" "notification" {
  name  = "notification"
  vhost = "/"

  settings {
    durable     = true
    auto_delete = false
    arguments = {
      # Configure as lazy queue to optimize memory usage for large messages
      "x-queue-mode" = "lazy"
      # Configure queue mirroring for high availability
      "x-ha-policy" = "all"
      # Enable automatic synchronization of mirrored queues
      "x-ha-sync-mode" = "automatic"
      # Set message TTL to 7 days (in milliseconds)
      "x-message-ttl" = 604800000
    }
  }

  # Ensure the broker is fully provisioned before configuring queues
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Bind document processing queue to the exchange
resource "rabbitmq_binding" "document_processing_binding" {
  source          = rabbitmq_exchange.mca_documents.name
  vhost           = "/"
  destination     = rabbitmq_queue.document_processing.name
  destination_type = "queue"
  routing_key     = "#"

  # Ensure the exchange and queue exist before creating the binding
  depends_on = [
    rabbitmq_exchange.mca_documents,
    rabbitmq_queue.document_processing
  ]
}

# Bind data extraction queue to the exchange
resource "rabbitmq_binding" "data_extraction_binding" {
  source          = rabbitmq_exchange.mca_documents.name
  vhost           = "/"
  destination     = rabbitmq_queue.data_extraction.name
  destination_type = "queue"
  routing_key     = "#"

  # Ensure the exchange and queue exist before creating the binding
  depends_on = [
    rabbitmq_exchange.mca_documents,
    rabbitmq_queue.data_extraction
  ]
}

# Bind notification queue to the exchange
resource "rabbitmq_binding" "notification_binding" {
  source          = rabbitmq_exchange.mca_documents.name
  vhost           = "/"
  destination     = rabbitmq_queue.notification.name
  destination_type = "queue"
  routing_key     = "#"

  # Ensure the exchange and queue exist before creating the binding
  depends_on = [
    rabbitmq_exchange.mca_documents,
    rabbitmq_queue.notification
  ]
}

# -----------------------------------------------------------------------------
# RabbitMQ Policy for Queue Mirroring and Persistence
# -----------------------------------------------------------------------------

resource "rabbitmq_policy" "ha_policy" {
  name  = "ha-policy"
  vhost = "/"
  
  policy {
    pattern  = ".*"
    priority = 1
    apply_to = "queues"
    
    definition = {
      "ha-mode"           = "all"
      "ha-sync-mode"      = "automatic"
      "queue-mode"        = "lazy"
      "message-ttl"       = 604800000
      "ha-sync-batch-size" = 1000
    }
  }

  # Ensure the broker is fully provisioned before configuring policies
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
  default     = "production"
}

variable "vpc_id" {
  description = "ID of the VPC where RabbitMQ will be deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for RabbitMQ deployment (minimum 3 for multi-AZ)"
  type        = list(string)
}

variable "service_security_group_ids" {
  description = "List of security group IDs that need access to RabbitMQ AMQP port"
  type        = list(string)
}

variable "management_security_group_ids" {
  description = "List of security group IDs that need access to RabbitMQ management UI"
  type        = list(string)
}

variable "rabbitmq_admin_username" {
  description = "Username for RabbitMQ admin user"
  type        = string
  sensitive   = true
}

variable "rabbitmq_admin_password" {
  description = "Password for RabbitMQ admin user"
  type        = string
  sensitive   = true
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for CloudWatch alarms"
  type        = string
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "rabbitmq_endpoints" {
  description = "The broker's wire-level protocol endpoints"
  value       = aws_mq_broker.rabbitmq_cluster.instances.*.endpoints
}

output "rabbitmq_console_url" {
  description = "The URL of the RabbitMQ web console"
  value       = "https://${aws_mq_broker.rabbitmq_cluster.instances.0.console_url}"
}

output "rabbitmq_id" {
  description = "The ID of the RabbitMQ broker"
  value       = aws_mq_broker.rabbitmq_cluster.id
}

output "rabbitmq_arn" {
  description = "The ARN of the RabbitMQ broker"
  value       = aws_mq_broker.rabbitmq_cluster.arn
}