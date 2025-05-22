# Main Terraform configuration file for Redis 7.0 Cache Infrastructure
# This file initializes the Redis cache module with environment-specific settings for the MCA Application Processing System

# Provider configuration based on the cloud platform
provider "aws" {
  region = local.aws_region

  # Default tags applied to all resources
  default_tags {
    tags = {
      Project     = "MCA Application Processing System"
      Environment = var.environment
      Terraform   = "true"
      Service     = "Redis Cache"
    }
  }
}

# Local variables for environment-specific settings
locals {
  # AWS region based on environment
  aws_region = {
    development = "us-west-2"
    staging     = "us-west-2"
    production  = "us-east-1"
  }[var.environment]

  # Environment-specific Redis node type
  redis_node_type = coalesce(
    var.redis_node_type,
    var.environment_defaults[var.environment].redis_node_type
  )

  # Environment-specific number of shards for application data
  app_data_num_shards = coalesce(
    var.app_data_num_shards,
    var.environment_defaults[var.environment].num_shards
  )

  # Environment-specific number of replicas per shard for application data
  app_data_replicas_per_shard = coalesce(
    var.app_data_replicas_per_shard,
    var.environment_defaults[var.environment].replicas_per_shard
  )

  # Environment-specific number of shards for user sessions
  user_sessions_num_shards = coalesce(
    var.user_sessions_num_shards,
    var.environment_defaults[var.environment].num_shards
  )

  # Environment-specific number of replicas per shard for user sessions
  user_sessions_replicas_per_shard = coalesce(
    var.user_sessions_replicas_per_shard,
    var.environment_defaults[var.environment].replicas_per_shard
  )

  # Determine if data tiering should be enabled based on node type
  enable_data_tiering = var.enable_data_tiering || startswith(local.redis_node_type, "cache.r6gd")

  # Common tags for all Redis resources
  common_tags = merge(var.tags, {
    Environment = var.environment
    Service     = "Redis Cache"
    Terraform   = "true"
  })

  # Environment-specific alarm thresholds
  cpu_threshold = var.environment == "production" ? 70 : 75
  memory_threshold = var.environment == "production" ? 75 : 80
}

# Redis module for application data cache (15-minute TTL)
module "redis_app_data" {
  source = "../modules/cache"

  # General configuration
  name_prefix         = "mca-app-data"
  environment         = var.environment
  vpc_id              = var.vpc_id
  subnet_ids          = var.redis_subnet_ids
  security_group_ids  = var.app_security_group_ids

  # Redis cluster configuration
  node_type           = local.redis_node_type
  engine_version      = "7.0"
  port                = 6379
  parameter_family    = "redis7"
  
  # Cluster mode configuration
  cluster_mode_enabled = var.enable_cluster_mode
  num_node_groups      = local.app_data_num_shards
  replicas_per_node_group = local.app_data_replicas_per_shard
  
  # High availability configuration
  multi_az_enabled    = var.enable_multi_az
  automatic_failover_enabled = var.enable_automatic_failover
  
  # Data tiering configuration
  data_tiering_enabled = local.enable_data_tiering
  
  # Security configuration
  transit_encryption_enabled = var.transit_encryption_enabled
  at_rest_encryption_enabled = var.at_rest_encryption_enabled
  
  # Backup configuration
  snapshot_retention_limit = var.snapshot_retention_limit
  snapshot_window          = var.snapshot_window
  
  # Maintenance configuration
  maintenance_window = var.maintenance_window
  
  # Redis parameters
  parameter_group_parameters = [
    {
      name  = "maxmemory-policy"
      value = var.app_data_eviction_policy
    },
    {
      name  = "activedefrag"
      value = "yes"
    },
    {
      name  = "lazyfree-lazy-eviction"
      value = "yes"
    },
    {
      name  = "maxmemory-samples"
      value = "10"
    },
    {
      name  = "lfu-decay-time"
      value = "1"
    },
    {
      name  = "lfu-log-factor"
      value = "10"
    }
  ]
  
  # Monitoring configuration
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  cpu_threshold       = local.cpu_threshold
  memory_threshold    = local.memory_threshold
  
  # Tags
  tags = merge(local.common_tags, {
    Purpose = "Application Data Cache"
    TTL     = "15-minutes"
  })
}

# Redis module for user sessions (24-hour TTL)
module "redis_user_sessions" {
  source = "../modules/cache"

  # General configuration
  name_prefix         = "mca-user-sessions"
  environment         = var.environment
  vpc_id              = var.vpc_id
  subnet_ids          = var.redis_subnet_ids
  security_group_ids  = var.app_security_group_ids

  # Redis cluster configuration
  node_type           = local.redis_node_type
  engine_version      = "7.0"
  port                = 6379
  parameter_family    = "redis7"
  
  # Cluster mode configuration
  cluster_mode_enabled = var.enable_cluster_mode
  num_node_groups      = local.user_sessions_num_shards
  replicas_per_node_group = local.user_sessions_replicas_per_shard
  
  # High availability configuration
  multi_az_enabled    = var.enable_multi_az
  automatic_failover_enabled = var.enable_automatic_failover
  
  # Data tiering configuration
  data_tiering_enabled = local.enable_data_tiering
  
  # Security configuration
  transit_encryption_enabled = var.transit_encryption_enabled
  at_rest_encryption_enabled = var.at_rest_encryption_enabled
  
  # Backup configuration
  snapshot_retention_limit = var.snapshot_retention_limit
  snapshot_window          = var.snapshot_window
  
  # Maintenance configuration
  maintenance_window = var.maintenance_window
  
  # Redis parameters
  parameter_group_parameters = [
    {
      name  = "maxmemory-policy"
      value = var.user_sessions_eviction_policy
    },
    {
      name  = "activedefrag"
      value = "yes"
    },
    {
      name  = "lazyfree-lazy-eviction"
      value = "yes"
    },
    {
      name  = "maxmemory-samples"
      value = "10"
    }
  ]
  
  # Monitoring configuration
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  cpu_threshold       = local.cpu_threshold
  memory_threshold    = local.memory_threshold
  
  # Tags
  tags = merge(local.common_tags, {
    Purpose = "User Sessions"
    TTL     = "24-hours"
  })
}

# Performance insights configuration for Redis clusters
resource "aws_cloudwatch_dashboard" "redis_performance_dashboard" {
  dashboard_name = "mca-redis-performance-${var.environment}"
  
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
            ["AWS/ElastiCache", "CPUUtilization", "ReplicationGroupId", module.redis_app_data.replication_group_id, { "label": "App Data CPU" }],
            ["AWS/ElastiCache", "CPUUtilization", "ReplicationGroupId", module.redis_user_sessions.replication_group_id, { "label": "User Sessions CPU" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.aws_region
          title   = "Redis CPU Utilization"
          period  = 60
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
            ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage", "ReplicationGroupId", module.redis_app_data.replication_group_id, { "label": "App Data Memory" }],
            ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage", "ReplicationGroupId", module.redis_user_sessions.replication_group_id, { "label": "User Sessions Memory" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.aws_region
          title   = "Redis Memory Usage"
          period  = 60
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
            ["AWS/ElastiCache", "CurrConnections", "ReplicationGroupId", module.redis_app_data.replication_group_id, { "label": "App Data Connections" }],
            ["AWS/ElastiCache", "CurrConnections", "ReplicationGroupId", module.redis_user_sessions.replication_group_id, { "label": "User Sessions Connections" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.aws_region
          title   = "Redis Connections"
          period  = 60
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
            ["AWS/ElastiCache", "CacheHits", "ReplicationGroupId", module.redis_app_data.replication_group_id, { "label": "App Data Cache Hits" }],
            ["AWS/ElastiCache", "CacheMisses", "ReplicationGroupId", module.redis_app_data.replication_group_id, { "label": "App Data Cache Misses" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.aws_region
          title   = "Redis Cache Hit/Miss"
          period  = 60
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
            ["AWS/ElastiCache", "Evictions", "ReplicationGroupId", module.redis_app_data.replication_group_id, { "label": "App Data Evictions" }],
            ["AWS/ElastiCache", "Evictions", "ReplicationGroupId", module.redis_user_sessions.replication_group_id, { "label": "User Sessions Evictions" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.aws_region
          title   = "Redis Evictions"
          period  = 60
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
            ["AWS/ElastiCache", "NetworkBytesIn", "ReplicationGroupId", module.redis_app_data.replication_group_id, { "label": "App Data Network In" }],
            ["AWS/ElastiCache", "NetworkBytesOut", "ReplicationGroupId", module.redis_app_data.replication_group_id, { "label": "App Data Network Out" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = local.aws_region
          title   = "Redis Network Traffic"
          period  = 60
        }
      }
    ]
  })
}

# SSM parameters for Redis connection information
resource "aws_ssm_parameter" "redis_app_data_endpoint" {
  name        = "/mca/${var.environment}/redis/app_data/endpoint"
  description = "Redis application data endpoint"
  type        = "String"
  value       = module.redis_app_data.primary_endpoint_address
  
  tags = local.common_tags
}

resource "aws_ssm_parameter" "redis_user_sessions_endpoint" {
  name        = "/mca/${var.environment}/redis/user_sessions/endpoint"
  description = "Redis user sessions endpoint"
  type        = "String"
  value       = module.redis_user_sessions.primary_endpoint_address
  
  tags = local.common_tags
}

resource "aws_ssm_parameter" "redis_app_data_connection_string" {
  name        = "/mca/${var.environment}/redis/app_data/connection_string"
  description = "Redis application data connection string"
  type        = "SecureString"
  value       = "rediss://${module.redis_app_data.primary_endpoint_address}:${module.redis_app_data.port}"
  
  tags = local.common_tags
}

resource "aws_ssm_parameter" "redis_user_sessions_connection_string" {
  name        = "/mca/${var.environment}/redis/user_sessions/connection_string"
  description = "Redis user sessions connection string"
  type        = "SecureString"
  value       = "rediss://${module.redis_user_sessions.primary_endpoint_address}:${module.redis_user_sessions.port}"
  
  tags = local.common_tags
}

# Output the Redis endpoints and connection information
output "redis_app_data_endpoint" {
  description = "Redis application data endpoint"
  value       = module.redis_app_data.primary_endpoint_address
}

output "redis_user_sessions_endpoint" {
  description = "Redis user sessions endpoint"
  value       = module.redis_user_sessions.primary_endpoint_address
}

output "redis_app_data_port" {
  description = "Redis application data port"
  value       = module.redis_app_data.port
}

output "redis_user_sessions_port" {
  description = "Redis user sessions port"
  value       = module.redis_user_sessions.port
}

output "redis_app_data_connection_string" {
  description = "Redis application data connection string"
  value       = "rediss://${module.redis_app_data.primary_endpoint_address}:${module.redis_app_data.port}"
  sensitive   = true
}

output "redis_user_sessions_connection_string" {
  description = "Redis user sessions connection string"
  value       = "rediss://${module.redis_user_sessions.primary_endpoint_address}:${module.redis_user_sessions.port}"
  sensitive   = true
}

output "redis_app_data_ttl" {
  description = "Redis application data TTL in seconds"
  value       = var.app_data_ttl_seconds
}

output "redis_user_sessions_ttl" {
  description = "Redis user sessions TTL in seconds"
  value       = var.user_sessions_ttl_seconds
}

output "redis_app_data_eviction_policy" {
  description = "Redis application data eviction policy"
  value       = var.app_data_eviction_policy
}

output "redis_user_sessions_eviction_policy" {
  description = "Redis user sessions eviction policy"
  value       = var.user_sessions_eviction_policy
}

output "redis_dashboard_url" {
  description = "URL to the Redis performance dashboard"
  value       = "https://${local.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${local.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.redis_performance_dashboard.dashboard_name}"
}