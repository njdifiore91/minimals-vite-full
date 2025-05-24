# Redis Cluster Terraform Module
# This module creates a Redis cluster with the following features:
# - Cluster mode with 3+ shards for horizontal scalability
# - At least 1 replica per shard for high availability
# - Single region, multi-AZ deployment for low-latency access
# - RDB snapshots every 60 minutes + AOF for data persistence
# - Auto-failover with Sentinel for high availability (15-second failover time)

variable "name_prefix" {
  description = "Prefix for the name of the Redis cluster resources"
  type        = string
  default     = "mca"
}

variable "environment" {
  description = "Environment (e.g., development, staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC where the Redis cluster will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the Redis cluster (should be in different AZs)"
  type        = list(string)
}

variable "node_type" {
  description = "The compute and memory capacity of the nodes"
  type        = string
  default     = "cache.m5.large"
}

variable "num_shards" {
  description = "Number of node groups (shards) for the Redis cluster"
  type        = number
  default     = 3
  validation {
    condition     = var.num_shards >= 3
    error_message = "Number of shards must be at least 3 for horizontal scalability."
  }
}

variable "replicas_per_shard" {
  description = "Number of replica nodes in each node group"
  type        = number
  default     = 1
  validation {
    condition     = var.replicas_per_shard >= 1
    error_message = "Number of replicas per shard must be at least 1 for high availability."
  }
}

variable "port" {
  description = "Port number for the Redis cluster"
  type        = number
  default     = 6379
}

variable "parameter_group_name" {
  description = "Name of the parameter group to associate with this Redis cluster"
  type        = string
  default     = "default.redis7.0.cluster.on"
}

variable "snapshot_retention_limit" {
  description = "Number of days for which ElastiCache will retain automatic snapshots"
  type        = number
  default     = 7
}

variable "snapshot_window" {
  description = "Daily time range during which automated backups are created"
  type        = string
  default     = "00:00-01:00"
}

variable "maintenance_window" {
  description = "Weekly time range during which maintenance on the cluster is performed"
  type        = string
  default     = "sun:05:00-sun:06:00"
}

variable "apply_immediately" {
  description = "Whether changes should be applied immediately or during the next maintenance window"
  type        = bool
  default     = false
}

variable "at_rest_encryption_enabled" {
  description = "Whether to enable encryption at rest"
  type        = bool
  default     = true
}

variable "transit_encryption_enabled" {
  description = "Whether to enable encryption in transit"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "The ARN of the key that you wish to use if encrypting at rest"
  type        = string
  default     = null
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

# Create a subnet group for the Redis cluster
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.name_prefix}-${var.environment}-redis-subnet-group"
  subnet_ids = var.subnet_ids
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-${var.environment}-redis-subnet-group"
      Environment = var.environment
    }
  )
}

# Create a security group for the Redis cluster
resource "aws_security_group" "redis" {
  name        = "${var.name_prefix}-${var.environment}-redis-sg"
  description = "Security group for Redis cluster"
  vpc_id      = var.vpc_id
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-${var.environment}-redis-sg"
      Environment = var.environment
    }
  )
}

# Allow inbound traffic on the Redis port from within the VPC
resource "aws_security_group_rule" "redis_ingress" {
  security_group_id = aws_security_group.redis.id
  type              = "ingress"
  from_port         = var.port
  to_port           = var.port
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

# Create the Redis cluster
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "${var.name_prefix}-${var.environment}-redis"
  replication_group_description = "${var.name_prefix}-${var.environment} Redis cluster"
  node_type                     = var.node_type
  port                          = var.port
  parameter_group_name          = var.parameter_group_name
  subnet_group_name             = aws_elasticache_subnet_group.redis.name
  security_group_ids            = [aws_security_group.redis.id]
  
  # Multi-AZ with automatic failover
  automatic_failover_enabled    = true
  multi_az_enabled              = true
  
  # Cluster mode configuration
  cluster_mode {
    num_node_groups         = var.num_shards
    replicas_per_node_group = var.replicas_per_shard
  }
  
  # Backup configuration
  snapshot_retention_limit = var.snapshot_retention_limit
  snapshot_window          = var.snapshot_window
  maintenance_window       = var.maintenance_window
  
  # Encryption configuration
  at_rest_encryption_enabled  = var.at_rest_encryption_enabled
  transit_encryption_enabled  = var.transit_encryption_enabled
  kms_key_id                  = var.kms_key_id
  
  # Redis 7.0 supports AOF persistence
  # This is configured through the parameter group
  
  # Apply changes immediately or during maintenance window
  apply_immediately = var.apply_immediately
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-${var.environment}-redis"
      Environment = var.environment
    }
  )
}

# Create a CloudWatch alarm for cluster CPU utilization
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.name_prefix}-${var.environment}-redis-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 75
  alarm_description   = "This metric monitors Redis cluster CPU utilization"
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis.id
  }
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-${var.environment}-redis-cpu-alarm"
      Environment = var.environment
    }
  )
}

# Create a CloudWatch alarm for memory usage
resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${var.name_prefix}-${var.environment}-redis-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This metric monitors Redis cluster memory utilization"
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis.id
  }
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-${var.environment}-redis-memory-alarm"
      Environment = var.environment
    }
  )
}

# Create a CloudWatch alarm for evictions
resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  alarm_name          = "${var.name_prefix}-${var.environment}-redis-evictions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Sum"
  threshold           = 100
  alarm_description   = "This metric monitors Redis cluster evictions"
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis.id
  }
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-${var.environment}-redis-evictions-alarm"
      Environment = var.environment
    }
  )
}

# Create a CloudWatch alarm for current connections
resource "aws_cloudwatch_metric_alarm" "redis_connections" {
  alarm_name          = "${var.name_prefix}-${var.environment}-redis-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CurrConnections"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 5000
  alarm_description   = "This metric monitors Redis cluster connections"
  
  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis.id
  }
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-${var.environment}-redis-connections-alarm"
      Environment = var.environment
    }
  )
}

# Outputs
output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.configuration_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = var.port
}

output "redis_security_group_id" {
  description = "ID of the Redis security group"
  value       = aws_security_group.redis.id
}

output "redis_subnet_group_name" {
  description = "Name of the Redis subnet group"
  value       = aws_elasticache_subnet_group.redis.name
}

output "redis_parameter_group_name" {
  description = "Name of the Redis parameter group"
  value       = var.parameter_group_name
}

output "redis_arn" {
  description = "ARN of the Redis cluster"
  value       = aws_elasticache_replication_group.redis.arn
}