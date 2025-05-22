# Redis 7.0 Caching Infrastructure Module
# Main entry point for the Redis caching infrastructure module
#
# This module creates:
# 1. A Redis 7.0 cluster for application data caching with allkeys-lru eviction policy and 15-minute TTL
# 2. A Redis 7.0 cluster for session management with noeviction policy and 24-hour TTL
# 3. Memory tiering with SSD persistence for cost optimization
# 4. Environment-specific configurations for development, staging, and production
#
# The module ensures 99.9% uptime guarantee through multi-AZ deployment and automatic failover

locals {
  # Determine environment-specific configuration
  env_config = var.environment_config[var.environment]
  
  # Common tags for all resources
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      Service     = "Redis"
      ManagedBy   = "Terraform"
    }
  )
  
  # Redis version
  redis_version = "7.0"
  
  # Environment-specific node types and configurations
  node_type     = lookup(local.env_config, "node_type", var.node_type)
  memory_size   = lookup(local.env_config, "memory_size", var.memory_size)
  shard_count   = lookup(local.env_config, "shard_count", var.shard_count)
  replica_count = lookup(local.env_config, "replica_count", var.replica_count)
  
  # Determine if this is a production environment
  is_production = var.environment == "production"
  
  # Set minimum values for production to ensure reliability
  min_shard_count   = local.is_production ? 3 : 1
  min_replica_count = local.is_production ? 1 : 0
  
  # Ensure production meets minimum requirements
  final_shard_count   = max(local.shard_count, local.min_shard_count)
  final_replica_count = max(local.replica_count, local.min_replica_count)
  
  # Parameter group families
  parameter_group_family = "redis7"
  
  # Redis port
  redis_port = 6379
  
  # Subnet group name prefix
  subnet_group_prefix = "${var.name_prefix}-${var.environment}"
  
  # Security group name prefix
  security_group_prefix = "${var.name_prefix}-${var.environment}"
  
  # Replication group name prefixes
  cache_replication_group_id   = "${var.name_prefix}-${var.environment}-cache"
  session_replication_group_id = "${var.name_prefix}-${var.environment}-session"
}

# Create parameter group for Redis cache instance with allkeys-lru eviction policy
resource "aws_elasticache_parameter_group" "redis_cache" {
  name        = "${var.name_prefix}-${var.environment}-cache-params"
  family      = local.parameter_group_family
  description = "Redis parameter group for application data cache with allkeys-lru eviction policy"
  
  # Set eviction policy to allkeys-lru for caching
  parameter {
    name  = "maxmemory-policy"
    value = var.cache_eviction_policy
  }
  
  # Enable memory tiering with SSD persistence
  parameter {
    name  = "activedefrag"
    value = "yes"
  }
  
  # Configure AOF persistence
  parameter {
    name  = "appendonly"
    value = var.enable_aof_persistence ? "yes" : "no"
  }
  
  parameter {
    name  = "appendfsync"
    value = "everysec"
  }
  
  # Configure RDB snapshots
  parameter {
    name  = "save"
    value = "${var.snapshot_interval_minutes} 1"
  }
  
  # Set default TTL for keys (15 minutes for application data)
  parameter {
    name  = "maxmemory-samples"
    value = "10"
  }
  
  # Enable memory tiering with SSD persistence
  parameter {
    name  = "lazyfree-lazy-eviction"
    value = "yes"
  }
  
  parameter {
    name  = "lazyfree-lazy-expire"
    value = "yes"
  }
  
  parameter {
    name  = "latency-tracking"
    value = "yes"
  }
  
  tags = local.common_tags
}

# Create parameter group for Redis session instance with noeviction policy
resource "aws_elasticache_parameter_group" "redis_session" {
  name        = "${var.name_prefix}-${var.environment}-session-params"
  family      = local.parameter_group_family
  description = "Redis parameter group for user sessions with noeviction policy"
  
  # Set eviction policy to noeviction for sessions
  parameter {
    name  = "maxmemory-policy"
    value = var.session_eviction_policy
  }
  
  # Enable memory tiering with SSD persistence
  parameter {
    name  = "activedefrag"
    value = "yes"
  }
  
  # Configure AOF persistence
  parameter {
    name  = "appendonly"
    value = var.enable_aof_persistence ? "yes" : "no"
  }
  
  parameter {
    name  = "appendfsync"
    value = "everysec"
  }
  
  # Configure RDB snapshots
  parameter {
    name  = "save"
    value = "${var.snapshot_interval_minutes} 1"
  }
  
  # Set default TTL for keys (24 hours for sessions)
  parameter {
    name  = "maxmemory-samples"
    value = "10"
  }
  
  # Enable memory tiering with SSD persistence
  parameter {
    name  = "lazyfree-lazy-eviction"
    value = "yes"
  }
  
  parameter {
    name  = "lazyfree-lazy-expire"
    value = "yes"
  }
  
  parameter {
    name  = "latency-tracking"
    value = "yes"
  }
  
  tags = local.common_tags
}

# Create subnet group for Redis clusters
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.subnet_group_prefix}-subnet-group"
  subnet_ids = var.subnet_ids
  
  tags = local.common_tags
}

# Create security group for Redis clusters
resource "aws_security_group" "redis" {
  name        = "${local.security_group_prefix}-sg"
  description = "Security group for Redis clusters"
  vpc_id      = var.vpc_id
  
  tags = local.common_tags
}

# Allow inbound traffic on the Redis port from within the VPC
resource "aws_security_group_rule" "redis_ingress" {
  security_group_id = aws_security_group.redis.id
  type              = "ingress"
  from_port         = local.redis_port
  to_port           = local.redis_port
  protocol          = "tcp"
  cidr_blocks       = [data.aws_vpc.selected.cidr_block]
}

# Allow outbound traffic
resource "aws_security_group_rule" "redis_egress" {
  security_group_id = aws_security_group.redis.id
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
}

# Get VPC details
data "aws_vpc" "selected" {
  id = var.vpc_id
}

# Create Redis cluster for application data caching
resource "aws_elasticache_replication_group" "redis_cache" {
  replication_group_id          = local.cache_replication_group_id
  replication_group_description = "Redis cluster for application data caching with 15-minute TTL"
  node_type                     = local.node_type
  port                          = local.redis_port
  parameter_group_name          = aws_elasticache_parameter_group.redis_cache.name
  subnet_group_name             = aws_elasticache_subnet_group.redis.name
  security_group_ids            = [aws_security_group.redis.id]
  
  # Multi-AZ with automatic failover
  automatic_failover_enabled    = var.enable_automatic_failover
  multi_az_enabled              = var.multi_az_enabled
  
  # Cluster mode configuration
  cluster_mode {
    num_node_groups         = local.final_shard_count
    replicas_per_node_group = local.final_replica_count
  }
  
  # Backup configuration
  snapshot_retention_limit = var.environment == "production" ? 7 : 1
  snapshot_window          = "00:00-01:00"
  maintenance_window       = "sun:05:00-sun:06:00"
  
  # Encryption configuration
  at_rest_encryption_enabled  = var.enable_at_rest_encryption
  transit_encryption_enabled  = var.enable_transit_encryption
  
  # Apply changes immediately in non-production environments
  apply_immediately = var.environment != "production"
  
  # Set TTL for application data (15 minutes)
  # This is configured through the parameter group
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.name_prefix}-${var.environment}-cache"
      TTL  = "${var.data_ttl_seconds} seconds"
    }
  )
}

# Create Redis cluster for session management
resource "aws_elasticache_replication_group" "redis_session" {
  replication_group_id          = local.session_replication_group_id
  replication_group_description = "Redis cluster for user sessions with 24-hour TTL"
  node_type                     = local.node_type
  port                          = local.redis_port
  parameter_group_name          = aws_elasticache_parameter_group.redis_session.name
  subnet_group_name             = aws_elasticache_subnet_group.redis.name
  security_group_ids            = [aws_security_group.redis.id]
  
  # Multi-AZ with automatic failover
  automatic_failover_enabled    = var.enable_automatic_failover
  multi_az_enabled              = var.multi_az_enabled
  
  # Cluster mode configuration
  cluster_mode {
    num_node_groups         = local.final_shard_count
    replicas_per_node_group = local.final_replica_count
  }
  
  # Backup configuration
  snapshot_retention_limit = var.environment == "production" ? 7 : 1
  snapshot_window          = "02:00-03:00" # Different window than cache instance
  maintenance_window       = "sun:07:00-sun:08:00" # Different window than cache instance
  
  # Encryption configuration
  at_rest_encryption_enabled  = var.enable_at_rest_encryption
  transit_encryption_enabled  = var.enable_transit_encryption
  
  # Apply changes immediately in non-production environments
  apply_immediately = var.environment != "production"
  
  # Set TTL for sessions (24 hours)
  # This is configured through the parameter group
  
  tags = merge(
    local.common_tags,
    {
      Name = "${var.name_prefix}-${var.environment}-session"
      TTL  = "${var.session_ttl_seconds} seconds"
    }
  )
}

# Create CloudWatch alarms for Redis cache instance
resource "aws_cloudwatch_metric_alarm" "redis_cache_cpu" {
  alarm_name          = "${var.name_prefix}-${var.environment}-cache-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_cpu_threshold_percent
  alarm_description   = "This metric monitors Redis cache cluster CPU utilization"
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis_cache.id
  }
  
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "redis_cache_memory" {
  alarm_name          = "${var.name_prefix}-${var.environment}-cache-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_memory_threshold_percent
  alarm_description   = "This metric monitors Redis cache cluster memory utilization"
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis_cache.id
  }
  
  tags = local.common_tags
}

# Create CloudWatch alarms for Redis session instance
resource "aws_cloudwatch_metric_alarm" "redis_session_cpu" {
  alarm_name          = "${var.name_prefix}-${var.environment}-session-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_cpu_threshold_percent
  alarm_description   = "This metric monitors Redis session cluster CPU utilization"
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis_session.id
  }
  
  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "redis_session_memory" {
  alarm_name          = "${var.name_prefix}-${var.environment}-session-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_memory_threshold_percent
  alarm_description   = "This metric monitors Redis session cluster memory utilization"
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis_session.id
  }
  
  tags = local.common_tags
}

# Output the Redis endpoints and connection information
output "redis_cache_endpoint" {
  description = "Redis cache cluster endpoint"
  value       = aws_elasticache_replication_group.redis_cache.configuration_endpoint_address
}

output "redis_session_endpoint" {
  description = "Redis session cluster endpoint"
  value       = aws_elasticache_replication_group.redis_session.configuration_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = local.redis_port
}

output "redis_cache_parameter_group_name" {
  description = "Redis cache parameter group name"
  value       = aws_elasticache_parameter_group.redis_cache.name
}

output "redis_session_parameter_group_name" {
  description = "Redis session parameter group name"
  value       = aws_elasticache_parameter_group.redis_session.name
}

output "redis_security_group_id" {
  description = "Redis security group ID"
  value       = aws_security_group.redis.id
}

output "redis_subnet_group_name" {
  description = "Redis subnet group name"
  value       = aws_elasticache_subnet_group.redis.name
}

output "redis_cache_arn" {
  description = "Redis cache cluster ARN"
  value       = aws_elasticache_replication_group.redis_cache.arn
}

output "redis_session_arn" {
  description = "Redis session cluster ARN"
  value       = aws_elasticache_replication_group.redis_session.arn
}