/**
 * RabbitMQ Cluster Terraform Module
 *
 * This module creates and configures a highly available RabbitMQ cluster with the following features:
 * - 3-node cluster for high availability
 * - Cross-AZ deployment for resilience
 * - Automatic failover with minimal downtime
 * - Message replication across nodes
 * - Partition tolerance and recovery
 */

# Variables for the RabbitMQ cluster configuration
variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where the RabbitMQ cluster will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs across multiple AZs for the RabbitMQ cluster (must be private subnets)"
  type        = list(string)
  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "At least 2 subnet IDs are required for CLUSTER_MULTI_AZ deployment."
  }
}

variable "security_group_ids" {
  description = "List of security group IDs for the RabbitMQ cluster"
  type        = list(string)
  default     = []
}

variable "instance_type" {
  description = "Instance type for the RabbitMQ nodes"
  type        = string
  default     = "mq.m5.large"
}

variable "engine_version" {
  description = "RabbitMQ engine version"
  type        = string
  default     = "3.10.20"
}

variable "deployment_mode" {
  description = "Deployment mode for the RabbitMQ cluster (SINGLE_INSTANCE, CLUSTER_MULTI_AZ)"
  type        = string
  default     = "CLUSTER_MULTI_AZ"
  validation {
    condition     = contains(["SINGLE_INSTANCE", "CLUSTER_MULTI_AZ"], var.deployment_mode)
    error_message = "Deployment mode must be either SINGLE_INSTANCE or CLUSTER_MULTI_AZ."
  }
}

variable "admin_username" {
  description = "Username for the RabbitMQ admin user"
  type        = string
  default     = "admin"
}

variable "admin_password" {
  description = "Password for the RabbitMQ admin user"
  type        = string
  sensitive   = true
}

variable "publicly_accessible" {
  description = "Whether the RabbitMQ cluster should be publicly accessible"
  type        = bool
  default     = false
}

variable "auto_minor_version_upgrade" {
  description = "Whether to automatically upgrade minor versions of the RabbitMQ engine"
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Whether to apply changes immediately or during the next maintenance window"
  type        = bool
  default     = false
}

variable "maintenance_window_start_time" {
  description = "Maintenance window start time configuration"
  type = object({
    day_of_week = string
    time_of_day = string
    time_zone   = string
  })
  default = {
    day_of_week = "SUNDAY"
    time_of_day = "02:00"
    time_zone   = "UTC"
  }
}

variable "logs_retention" {
  description = "Number of days to retain logs"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags to apply to the RabbitMQ cluster resources"
  type        = map(string)
  default     = {}
}

# Local variables for configuration
locals {
  name_prefix = "rabbitmq-${var.environment}"
  
  # Default RabbitMQ configuration for high availability and partition handling
  rabbitmq_config = <<-EOT
    # Cluster configuration
    cluster_formation.peer_discovery_backend = rabbit_peer_discovery_aws
    cluster_formation.aws.region = ${data.aws_region.current.name}
    cluster_formation.aws.use_autoscaling_group = false
    cluster_name = rabbitmq-${var.environment}-cluster
    
    # High availability and quorum configuration
    cluster_partition_handling = autoheal
    queue_master_locator = min-masters
    
    # Replication and synchronization settings
    ha-mode = all
    ha-sync-mode = automatic
    ha-sync-batch-size = 50
    
    # Quorum queue settings for consensus-based replication
    default_quorum_queue_version = 2
    default_quorum_initial_group_size = 3
    
    # Message persistence and durability
    disk_free_limit.absolute = 5GB
    vm_memory_high_watermark.relative = 0.8
    
    # Lazy queues for large message handling
    queue_index_embed_msgs_below = 4096
    
    # TLS configuration
    listeners.ssl.default = 5671
    ssl_options.verify = verify_peer
    ssl_options.fail_if_no_peer_cert = false
    
    # Heartbeat and timeout settings for failure detection
    heartbeat = 60
    consumer_timeout = 1800000
  EOT
}

# Data source for current AWS region
data "aws_region" "current" {}

# Security group for RabbitMQ cluster
resource "aws_security_group" "rabbitmq" {
  name        = "${local.name_prefix}-sg"
  description = "Security group for RabbitMQ cluster"
  vpc_id      = var.vpc_id

  # AMQP port
  ingress {
    from_port   = 5671
    to_port     = 5671
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.selected.cidr_block]
    description = "AMQP with TLS"
  }

  # Management UI port
  ingress {
    from_port   = 15671
    to_port     = 15671
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.selected.cidr_block]
    description = "Management UI with TLS"
  }

  # Cluster internal communication
  ingress {
    from_port   = 25672
    to_port     = 25672
    protocol    = "tcp"
    self        = true
    description = "Inter-node communication"
  }

  # Egress rule
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(
    var.tags,
    {
      Name = "${local.name_prefix}-sg"
    }
  )
}

# Data source for VPC
data "aws_vpc" "selected" {
  id = var.vpc_id
}

# AWS MQ RabbitMQ broker
resource "aws_mq_broker" "rabbitmq_cluster" {
  broker_name        = "${local.name_prefix}-cluster"
  engine_type        = "RabbitMQ"
  engine_version     = var.engine_version
  host_instance_type = var.instance_type
  deployment_mode    = var.deployment_mode
  
  security_groups    = concat(var.security_group_ids, [aws_security_group.rabbitmq.id])
  subnet_ids         = var.deployment_mode == "CLUSTER_MULTI_AZ" ? var.subnet_ids : [var.subnet_ids[0]]
  
  publicly_accessible = var.publicly_accessible
  
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  apply_immediately          = var.apply_immediately
  
  maintenance_window_start_time {
    day_of_week = var.maintenance_window_start_time.day_of_week
    time_of_day = var.maintenance_window_start_time.time_of_day
    time_zone   = var.maintenance_window_start_time.time_zone
  }
  
  logs {
    general = true
    # Note: Audit logs are not supported for RabbitMQ engine type
  }
  
  user {
    username = var.admin_username
    password = var.admin_password
    # Note: console_access is not supported for RabbitMQ users
  }
  
  configuration {
    id       = aws_mq_configuration.rabbitmq_config.id
    revision = aws_mq_configuration.rabbitmq_config.latest_revision
  }
  
  encryption_options {
    use_aws_owned_key = true
  }
  
  tags = merge(
    var.tags,
    {
      Name        = "${local.name_prefix}-cluster"
      Environment = var.environment
    }
  )
  
  lifecycle {
    prevent_destroy = true
  }
}

# RabbitMQ configuration
resource "aws_mq_configuration" "rabbitmq_config" {
  name           = "${local.name_prefix}-config"
  engine_type    = "RabbitMQ"
  engine_version = var.engine_version
  
  data = local.rabbitmq_config
  
  tags = merge(
    var.tags,
    {
      Name        = "${local.name_prefix}-config"
      Environment = var.environment
    }
  )
}

# CloudWatch Log Group for RabbitMQ logs
resource "aws_cloudwatch_log_group" "rabbitmq_logs" {
  name              = "/aws/amazonmq/${local.name_prefix}-cluster"
  retention_in_days = var.logs_retention
  
  tags = merge(
    var.tags,
    {
      Name        = "${local.name_prefix}-logs"
      Environment = var.environment
    }
  )
}

# CloudWatch Alarms for monitoring RabbitMQ cluster health
resource "aws_cloudwatch_metric_alarm" "rabbitmq_cpu_utilization" {
  alarm_name          = "${local.name_prefix}-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CpuUtilization"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This metric monitors RabbitMQ CPU utilization"
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
  }
  
  alarm_actions = []
  ok_actions    = []
  
  tags = merge(
    var.tags,
    {
      Name        = "${local.name_prefix}-cpu-alarm"
      Environment = var.environment
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "rabbitmq_memory_usage" {
  alarm_name          = "${local.name_prefix}-memory-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HeapUsage"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This metric monitors RabbitMQ memory usage"
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
  }
  
  alarm_actions = []
  ok_actions    = []
  
  tags = merge(
    var.tags,
    {
      Name        = "${local.name_prefix}-memory-alarm"
      Environment = var.environment
    }
  )
}

# Queue depth monitoring alarm
resource "aws_cloudwatch_metric_alarm" "rabbitmq_queue_depth" {
  alarm_name          = "${local.name_prefix}-queue-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "QueueDepth"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Maximum"
  threshold           = 10000
  alarm_description   = "This metric monitors RabbitMQ queue depth"
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
  }
  
  alarm_actions = []
  ok_actions    = []
  
  tags = merge(
    var.tags,
    {
      Name        = "${local.name_prefix}-queue-depth-alarm"
      Environment = var.environment
    }
  )
}

# Outputs
output "rabbitmq_endpoints" {
  description = "The endpoints of the RabbitMQ cluster"
  value = {
    amqp_endpoints     = aws_mq_broker.rabbitmq_cluster.instances.*.endpoints
    management_console = "https://${aws_mq_broker.rabbitmq_cluster.instances.0.console_url}"
  }
}

output "rabbitmq_id" {
  description = "The ID of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.id
}

output "rabbitmq_arn" {
  description = "The ARN of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.arn
}

output "rabbitmq_security_group_id" {
  description = "The ID of the security group for the RabbitMQ cluster"
  value       = aws_security_group.rabbitmq.id
}