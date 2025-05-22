# Redis 7.0 Cluster Configuration for MCA Application Processing System
# This file configures the Redis 7.0 cluster with specific settings for caching and session management

# Provider configuration is assumed to be defined elsewhere

# Parameter group for application data cache with allkeys-lru eviction policy
resource "aws_elasticache_parameter_group" "redis_app_data_params" {
  name        = "mca-redis-app-data-params"
  family      = "redis7"
  description = "Redis parameter group for application data cache with 15-minute TTL"

  # Set eviction policy to allkeys-lru for application data cache
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  # Additional parameters for performance optimization
  parameter {
    name  = "activedefrag"
    value = "yes"
  }

  parameter {
    name  = "lazyfree-lazy-eviction"
    value = "yes"
  }
}

# Parameter group for user sessions with noeviction policy
resource "aws_elasticache_parameter_group" "redis_user_sessions_params" {
  name        = "mca-redis-user-sessions-params"
  family      = "redis7"
  description = "Redis parameter group for user sessions with 24-hour TTL"

  # Set eviction policy to noeviction for user sessions
  parameter {
    name  = "maxmemory-policy"
    value = "noeviction"
  }

  # Additional parameters for performance optimization
  parameter {
    name  = "activedefrag"
    value = "yes"
  }

  parameter {
    name  = "lazyfree-lazy-eviction"
    value = "yes"
  }
}

# Subnet group for Redis clusters
resource "aws_elasticache_subnet_group" "redis_subnet_group" {
  name        = "mca-redis-subnet-group"
  description = "Subnet group for MCA Redis clusters"
  subnet_ids  = var.redis_subnet_ids
}

# Security group for Redis clusters
resource "aws_security_group" "redis_security_group" {
  name        = "mca-redis-security-group"
  description = "Security group for MCA Redis clusters"
  vpc_id      = var.vpc_id

  # Redis port access from application servers
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.app_security_group_ids
  }

  # Outbound internet access
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "mca-redis-security-group"
    Environment = var.environment
  }
}

# Redis cluster for application data with 15-minute TTL
resource "aws_elasticache_replication_group" "redis_app_data" {
  replication_group_id       = "mca-redis-app-data-${var.environment}"
  description                = "Redis cluster for MCA application data with 15-minute TTL"
  node_type                  = var.redis_node_type
  port                       = 6379
  parameter_group_name       = aws_elasticache_parameter_group.redis_app_data_params.name
  subnet_group_name          = aws_elasticache_subnet_group.redis_subnet_group.name
  security_group_ids         = [aws_security_group.redis_security_group.id]
  automatic_failover_enabled = true
  engine_version             = "7.0"
  
  # Enable encryption in transit
  transit_encryption_enabled = true
  
  # Enable at-rest encryption
  at_rest_encryption_enabled = true
  
  # Configure snapshot settings
  snapshot_retention_limit = 7
  snapshot_window          = "00:00-05:00"
  
  # Configure maintenance window
  maintenance_window = "sun:05:00-sun:09:00"
  
  # Enable Multi-AZ
  multi_az_enabled = true
  
  # Configure data tiering if using r6gd node type
  data_tiering_enabled = var.enable_data_tiering
  
  # Configure cluster mode with 3 shards and 1 replica per shard
  cluster_mode {
    num_node_groups         = 3
    replicas_per_node_group = 1
  }
  
  tags = {
    Name        = "mca-redis-app-data"
    Environment = var.environment
    TTL         = "15-minutes"
    Purpose     = "Application Data Cache"
  }
}

# Redis cluster for user sessions with 24-hour TTL
resource "aws_elasticache_replication_group" "redis_user_sessions" {
  replication_group_id       = "mca-redis-user-sessions-${var.environment}"
  description                = "Redis cluster for MCA user sessions with 24-hour TTL"
  node_type                  = var.redis_node_type
  port                       = 6379
  parameter_group_name       = aws_elasticache_parameter_group.redis_user_sessions_params.name
  subnet_group_name          = aws_elasticache_subnet_group.redis_subnet_group.name
  security_group_ids         = [aws_security_group.redis_security_group.id]
  automatic_failover_enabled = true
  engine_version             = "7.0"
  
  # Enable encryption in transit
  transit_encryption_enabled = true
  
  # Enable at-rest encryption
  at_rest_encryption_enabled = true
  
  # Configure snapshot settings
  snapshot_retention_limit = 7
  snapshot_window          = "00:00-05:00"
  
  # Configure maintenance window
  maintenance_window = "sun:05:00-sun:09:00"
  
  # Enable Multi-AZ
  multi_az_enabled = true
  
  # Configure data tiering if using r6gd node type
  data_tiering_enabled = var.enable_data_tiering
  
  # Configure cluster mode with 3 shards and 1 replica per shard
  cluster_mode {
    num_node_groups         = 3
    replicas_per_node_group = 1
  }
  
  tags = {
    Name        = "mca-redis-user-sessions"
    Environment = var.environment
    TTL         = "24-hours"
    Purpose     = "User Sessions"
  }
}

# CloudWatch alarms for Redis monitoring
resource "aws_cloudwatch_metric_alarm" "redis_app_data_cpu" {
  alarm_name          = "mca-redis-app-data-cpu-utilization-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "60"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors Redis app data CPU utilization"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis_app_data.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_user_sessions_cpu" {
  alarm_name          = "mca-redis-user-sessions-cpu-utilization-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "60"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors Redis user sessions CPU utilization"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis_user_sessions.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_app_data_memory" {
  alarm_name          = "mca-redis-app-data-memory-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "60"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors Redis app data memory usage"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis_app_data.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_user_sessions_memory" {
  alarm_name          = "mca-redis-user-sessions-memory-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "60"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors Redis user sessions memory usage"
  alarm_actions       = var.alarm_actions
  ok_actions          = var.ok_actions
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis_user_sessions.id
  }
}

# Variables used in this module
variable "environment" {
  description = "Environment name (e.g., development, staging, production)"
  type        = string
}

variable "redis_subnet_ids" {
  description = "List of subnet IDs for the Redis subnet group"
  type        = list(string)
}

variable "vpc_id" {
  description = "VPC ID where Redis clusters will be deployed"
  type        = string
}

variable "app_security_group_ids" {
  description = "List of security group IDs for application servers that need access to Redis"
  type        = list(string)
}

variable "redis_node_type" {
  description = "Redis node type (e.g., cache.r6g.large or cache.r6gd.large for data tiering)"
  type        = string
  default     = "cache.r6g.large"
}

variable "enable_data_tiering" {
  description = "Enable data tiering (requires r6gd node type)"
  type        = bool
  default     = false
}

variable "alarm_actions" {
  description = "List of ARNs to notify when Redis alarms transition to ALARM state"
  type        = list(string)
  default     = []
}

variable "ok_actions" {
  description = "List of ARNs to notify when Redis alarms transition to OK state"
  type        = list(string)
  default     = []
}

# Outputs for Redis endpoints
output "redis_app_data_primary_endpoint" {
  description = "Primary endpoint for the Redis application data cluster"
  value       = aws_elasticache_replication_group.redis_app_data.primary_endpoint_address
}

output "redis_app_data_reader_endpoint" {
  description = "Reader endpoint for the Redis application data cluster"
  value       = aws_elasticache_replication_group.redis_app_data.reader_endpoint_address
}

output "redis_app_data_configuration_endpoint" {
  description = "Configuration endpoint for the Redis application data cluster"
  value       = aws_elasticache_replication_group.redis_app_data.configuration_endpoint_address
}

output "redis_user_sessions_primary_endpoint" {
  description = "Primary endpoint for the Redis user sessions cluster"
  value       = aws_elasticache_replication_group.redis_user_sessions.primary_endpoint_address
}

output "redis_user_sessions_reader_endpoint" {
  description = "Reader endpoint for the Redis user sessions cluster"
  value       = aws_elasticache_replication_group.redis_user_sessions.reader_endpoint_address
}

output "redis_user_sessions_configuration_endpoint" {
  description = "Configuration endpoint for the Redis user sessions cluster"
  value       = aws_elasticache_replication_group.redis_user_sessions.configuration_endpoint_address
}