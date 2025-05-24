# Terraform configuration for MCA Application Processing System - Messaging Infrastructure
# This file defines the main Terraform configuration for the RabbitMQ messaging infrastructure,
# including provider settings, backend configuration, and module imports.

# Terraform version and required providers
terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.10.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.5.0"
    }
  }

  # Backend configuration for state management
  # Using S3 for remote state storage with DynamoDB for state locking
  backend "s3" {
    bucket         = "dollarfunding-terraform-state"
    key            = "mca/messaging/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

# Provider configuration
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "MCA-Application-Processing"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Kubernetes provider configuration for deploying RabbitMQ to Kubernetes
provider "kubernetes" {
  # Configuration will be loaded from the EKS module output
  # or from environment variables/kubeconfig
}

# Helm provider for deploying RabbitMQ using Helm charts
provider "helm" {
  kubernetes {
    # Configuration will be loaded from the EKS module output
    # or from environment variables/kubeconfig
  }
}

# Local variables for configuration
locals {
  # Environment-specific settings
  env_config = lookup(var.environment_defaults, var.environment, {
    cluster_size      = 3
    node_instance_type = "m5.large"
    node_disk_size    = 50
    memory_limit      = 2048
    cpu_limit         = 1000
  })

  # RabbitMQ exchange and queue configuration
  rabbitmq_config = {
    exchanges = var.exchanges
    queues    = var.queues
    bindings  = var.bindings
  }

  # Common tags for all resources
  common_tags = merge(var.tags, {
    Component = "Messaging"
    Service   = "RabbitMQ"
  })
}

# Data source to get the current AWS region
data "aws_region" "current" {}

# Data source to get the current AWS account ID
data "aws_caller_identity" "current" {}

# Data source for environment-specific VPC configuration
data "terraform_remote_state" "network" {
  backend = "s3"
  config = {
    bucket = "dollarfunding-terraform-state"
    key    = "mca/network/${var.environment}/terraform.tfstate"
    region = "us-east-1"
  }
}

# Module for RabbitMQ messaging infrastructure
module "rabbitmq" {
  source = "../modules/messaging"

  # Pass environment and region
  environment        = var.environment
  region             = var.region
  availability_zones = var.availability_zones

  # Cluster configuration
  cluster_name  = var.cluster_name
  cluster_size  = local.env_config.cluster_size
  instance_type = local.env_config.node_instance_type

  # Storage configuration
  storage_type = var.node_disk_type
  storage_size = local.env_config.node_disk_size
  storage_iops = var.environment == "production" ? 3000 : 1000

  # RabbitMQ configuration
  rabbitmq_version = "3.11"
  admin_username   = var.admin_username
  admin_password   = var.admin_password

  # Security configuration
  enable_tls          = var.enable_tls
  tls_certificate_arn = var.certificate_arn

  # Queue and exchange configuration
  create_default_resources = true
  exchanges               = local.rabbitmq_config.exchanges
  queues                  = local.rabbitmq_config.queues
  bindings                = local.rabbitmq_config.bindings

  # Monitoring and alerting
  enable_monitoring = true
  enable_dashboard  = true
  dashboard_port    = 15672

  # High availability settings
  enable_mirrored_queues = true
  mirror_sync_batch_size = 4096

  # Resource allocation
  memory_high_watermark = 0.7
  cpu_high_watermark    = 0.8

  # Tags
  tags = local.common_tags
}

# CloudWatch dashboard for RabbitMQ monitoring
resource "aws_cloudwatch_dashboard" "rabbitmq" {
  count          = var.environment != "development" ? 1 : 0
  dashboard_name = "${var.environment}-rabbitmq-dashboard"

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
            ["AWS/MQ", "ConnectionCount", "Broker", module.rabbitmq.broker_id]
          ]
          period = 60
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "RabbitMQ Connection Count"
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
            ["AWS/MQ", "QueueDepth", "Broker", module.rabbitmq.broker_id, "Queue", "document-processing", "VirtualHost", "/"],
            ["AWS/MQ", "QueueDepth", "Broker", module.rabbitmq.broker_id, "Queue", "data-extraction", "VirtualHost", "/"],
            ["AWS/MQ", "QueueDepth", "Broker", module.rabbitmq.broker_id, "Queue", "notification", "VirtualHost", "/"]
          ]
          period = 60
          stat   = "Maximum"
          region = data.aws_region.current.name
          title  = "Queue Depths"
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
            ["AWS/MQ", "MessageCount", "Broker", module.rabbitmq.broker_id, "Queue", "document-processing", "VirtualHost", "/"],
            ["AWS/MQ", "MessageCount", "Broker", module.rabbitmq.broker_id, "Queue", "data-extraction", "VirtualHost", "/"],
            ["AWS/MQ", "MessageCount", "Broker", module.rabbitmq.broker_id, "Queue", "notification", "VirtualHost", "/"]
          ]
          period = 60
          stat   = "Sum"
          region = data.aws_region.current.name
          title  = "Message Counts"
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
            ["AWS/MQ", "CpuUtilization", "Broker", module.rabbitmq.broker_id],
            ["AWS/MQ", "MemoryUtilization", "Broker", module.rabbitmq.broker_id]
          ]
          period = 60
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "Resource Utilization"
        }
      }
    ]
  })
}

# SNS topic for RabbitMQ alerts
resource "aws_sns_topic" "rabbitmq_alerts" {
  name = "${var.environment}-rabbitmq-alerts"
  
  tags = local.common_tags
}

# CloudWatch alarm for RabbitMQ queue depth
resource "aws_cloudwatch_metric_alarm" "queue_depth_alarm" {
  for_each = var.environment != "development" ? toset(["document-processing", "data-extraction", "notification"]) : toset([])
  
  alarm_name          = "${var.environment}-rabbitmq-${each.key}-queue-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "QueueDepth"
  namespace           = "AWS/MQ"
  period              = 60
  statistic           = "Maximum"
  threshold           = var.environment == "production" ? 1000 : 5000
  alarm_description   = "This alarm monitors the depth of the ${each.key} queue"
  
  dimensions = {
    Broker      = module.rabbitmq.broker_id
    Queue       = each.key
    VirtualHost = "/"
  }
  
  alarm_actions = [aws_sns_topic.rabbitmq_alerts.arn]
  ok_actions    = [aws_sns_topic.rabbitmq_alerts.arn]
}

# CloudWatch alarm for RabbitMQ CPU utilization
resource "aws_cloudwatch_metric_alarm" "cpu_alarm" {
  count               = var.environment != "development" ? 1 : 0
  
  alarm_name          = "${var.environment}-rabbitmq-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CpuUtilization"
  namespace           = "AWS/MQ"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This alarm monitors RabbitMQ CPU utilization"
  
  dimensions = {
    Broker = module.rabbitmq.broker_id
  }
  
  alarm_actions = [aws_sns_topic.rabbitmq_alerts.arn]
  ok_actions    = [aws_sns_topic.rabbitmq_alerts.arn]
}

# CloudWatch alarm for RabbitMQ memory utilization
resource "aws_cloudwatch_metric_alarm" "memory_alarm" {
  count               = var.environment != "development" ? 1 : 0
  
  alarm_name          = "${var.environment}-rabbitmq-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/MQ"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This alarm monitors RabbitMQ memory utilization"
  
  dimensions = {
    Broker = module.rabbitmq.broker_id
  }
  
  alarm_actions = [aws_sns_topic.rabbitmq_alerts.arn]
  ok_actions    = [aws_sns_topic.rabbitmq_alerts.arn]
}