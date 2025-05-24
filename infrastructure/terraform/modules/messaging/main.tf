/**
 * RabbitMQ Messaging Infrastructure Module
 *
 * This Terraform module creates and configures a highly available RabbitMQ cluster for the
 * Merchant Cash Advance (MCA) Application Processing System. It provides asynchronous messaging
 * between microservices with guaranteed delivery, message persistence, and high availability.
 *
 * Key features:
 * - 3-node RabbitMQ cluster for high availability (99.9% uptime)
 * - Disk-based persistence for message durability
 * - Mirrored queues across all nodes
 * - Environment-specific settings (production vs staging)
 * - Resource allocation based on expected message volume
 * - Support for the MCA document processing pipeline
 */

# -----------------------------------------------------------------------------
# Terraform Configuration
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "vpc_id" {
  description = "ID of the VPC where the RabbitMQ cluster will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs across multiple AZs for the RabbitMQ cluster (must be private subnets)"
  type        = list(string)
}

variable "cluster_size" {
  description = "Number of nodes in the RabbitMQ cluster"
  type        = number
  default     = 3
  validation {
    condition     = var.cluster_size >= 1 && var.cluster_size <= 5
    error_message = "Cluster size must be between 1 and 5."
  }
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

variable "enable_tls" {
  description = "Whether to enable TLS for RabbitMQ connections"
  type        = bool
  default     = true
}

variable "enable_monitoring" {
  description = "Whether to enable CloudWatch monitoring for RabbitMQ"
  type        = bool
  default     = true
}

variable "enable_dashboard" {
  description = "Whether to create a CloudWatch dashboard for RabbitMQ monitoring"
  type        = bool
  default     = true
}

variable "enable_mirrored_queues" {
  description = "Whether to enable mirrored queues for high availability"
  type        = bool
  default     = true
}

variable "mirror_sync_batch_size" {
  description = "Batch size for synchronizing mirrored queues"
  type        = number
  default     = 50
}

variable "create_default_resources" {
  description = "Whether to create default exchanges, queues, and bindings"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to connect to RabbitMQ AMQP port"
  type        = list(string)
  default     = []
}

variable "management_cidr_blocks" {
  description = "List of CIDR blocks allowed to connect to RabbitMQ management UI"
  type        = list(string)
  default     = []
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
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

# -----------------------------------------------------------------------------
# Local Variables
# -----------------------------------------------------------------------------

locals {
  name_prefix = "rabbitmq-${var.environment}"
  
  # Determine if we should use multi-AZ deployment based on environment and subnet count
  is_multi_az = var.environment != "development" && length(var.subnet_ids) >= 2
  
  # Determine actual cluster size based on environment
  actual_cluster_size = var.environment == "development" ? 1 : var.cluster_size
  
  # Deployment mode based on cluster size and multi-AZ setting
  deployment_mode = local.is_multi_az && local.actual_cluster_size > 1 ? "CLUSTER_MULTI_AZ" : "SINGLE_INSTANCE"
  
  # Environment-specific resource allocation
  resource_allocation = {
    development = {
      instance_type = "mq.t3.micro"
      storage_type  = "efs"
    }
    staging = {
      instance_type = "mq.m5.large"
      storage_type  = "ebs"
    }
    production = {
      instance_type = "mq.m5.xlarge"
      storage_type  = "ebs"
    }
  }
  
  # Use environment-specific resource allocation or default to provided values
  instance_type = lookup(lookup(local.resource_allocation, var.environment, {}), "instance_type", var.instance_type)
  storage_type  = lookup(lookup(local.resource_allocation, var.environment, {}), "storage_type", "ebs")
  
  # RabbitMQ configuration for high availability and message persistence
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
    ha-sync-batch-size = ${var.mirror_sync_batch_size}
    
    # Quorum queue settings for consensus-based replication
    default_quorum_queue_version = 2
    default_quorum_initial_group_size = ${min(local.actual_cluster_size, 5)}
    
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
    
    # Environment-specific settings
    ${var.environment == "production" ? "log.file.level = info" : "log.file.level = debug"}
    ${var.environment == "production" ? "collect_statistics_interval = 60000" : "collect_statistics_interval = 30000"}
  EOT
  
  # Common tags for all resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      Component   = "messaging"
      ManagedBy   = "terraform"
    }
  )
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------

data "aws_region" "current" {}

data "aws_vpc" "selected" {
  id = var.vpc_id
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group for RabbitMQ Logs
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "rabbitmq_logs" {
  name              = "/aws/amazonmq/${local.name_prefix}-cluster"
  retention_in_days = var.logs_retention
  
  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# RabbitMQ Configuration
# -----------------------------------------------------------------------------

resource "aws_mq_configuration" "rabbitmq_config" {
  name           = "${local.name_prefix}-config"
  engine_type    = "RabbitMQ"
  engine_version = var.engine_version
  
  data = local.rabbitmq_config
  
  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# AWS MQ RabbitMQ Broker
# -----------------------------------------------------------------------------

resource "aws_mq_broker" "rabbitmq_cluster" {
  broker_name        = "${local.name_prefix}-cluster"
  engine_type        = "RabbitMQ"
  engine_version     = var.engine_version
  host_instance_type = local.instance_type
  deployment_mode    = local.deployment_mode
  storage_type       = local.storage_type
  
  security_groups    = [aws_security_group.rabbitmq_cluster.id]
  subnet_ids         = local.deployment_mode == "CLUSTER_MULTI_AZ" ? slice(var.subnet_ids, 0, 2) : [var.subnet_ids[0]]
  
  publicly_accessible = false
  
  auto_minor_version_upgrade = true
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
    use_aws_owned_key = false
    kms_key_id        = aws_kms_key.rabbitmq_encryption.arn
  }
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-cluster"
    }
  )
  
  # Prevent accidental deletion of the RabbitMQ cluster
  lifecycle {
    prevent_destroy = true
  }
}

# -----------------------------------------------------------------------------
# CloudWatch Dashboard for RabbitMQ Monitoring
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_dashboard" "rabbitmq" {
  count          = var.enable_monitoring && var.enable_dashboard ? 1 : 0
  dashboard_name = "${local.name_prefix}-dashboard"
  
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
            ["AWS/AmazonMQ", "CpuUtilization", "Broker", aws_mq_broker.rabbitmq_cluster.id]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "CPU Utilization"
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
            ["AWS/AmazonMQ", "HeapUsage", "Broker", aws_mq_broker.rabbitmq_cluster.id]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "Memory Usage"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/AmazonMQ", "TotalMessageCount", "Broker", aws_mq_broker.rabbitmq_cluster.id]
          ]
          period = 300
          stat   = "Sum"
          region = data.aws_region.current.name
          title  = "Total Message Count"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/AmazonMQ", "QueueDepth", "Broker", aws_mq_broker.rabbitmq_cluster.id]
          ]
          period = 300
          stat   = "Maximum"
          region = data.aws_region.current.name
          title  = "Queue Depth"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/AmazonMQ", "NetworkIn", "Broker", aws_mq_broker.rabbitmq_cluster.id],
            ["AWS/AmazonMQ", "NetworkOut", "Broker", aws_mq_broker.rabbitmq_cluster.id]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "Network Traffic"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/AmazonMQ", "ConnectionCount", "Broker", aws_mq_broker.rabbitmq_cluster.id]
          ]
          period = 300
          stat   = "Maximum"
          region = data.aws_region.current.name
          title  = "Connection Count"
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms for RabbitMQ Monitoring
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "rabbitmq_cpu_utilization" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${local.name_prefix}-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CpuUtilization"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Average"
  threshold           = var.environment == "production" ? 80 : 90
  alarm_description   = "This metric monitors RabbitMQ CPU utilization"
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
  }
  
  alarm_actions = []
  ok_actions    = []
  
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "rabbitmq_memory_usage" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${local.name_prefix}-memory-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HeapUsage"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Average"
  threshold           = var.environment == "production" ? 80 : 90
  alarm_description   = "This metric monitors RabbitMQ memory usage"
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
  }
  
  alarm_actions = []
  ok_actions    = []
  
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "rabbitmq_queue_depth" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${local.name_prefix}-queue-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "QueueDepth"
  namespace           = "AWS/AmazonMQ"
  period              = 300
  statistic           = "Maximum"
  threshold           = var.environment == "production" ? 10000 : 5000
  alarm_description   = "This metric monitors RabbitMQ queue depth"
  
  dimensions = {
    Broker = aws_mq_broker.rabbitmq_cluster.id
  }
  
  alarm_actions = []
  ok_actions    = []
  
  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# RabbitMQ Provider Configuration
# -----------------------------------------------------------------------------

provider "rabbitmq" {
  endpoint = "https://${aws_mq_broker.rabbitmq_cluster.instances[0].console_url}/api/"
  username = var.admin_username
  password = var.admin_password
  
  # Ensure TLS is used for the RabbitMQ API connection
  insecure = false
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

# Outputs are defined in outputs.tf