# Redis Cache Infrastructure Outputs
# This file exports essential Redis information as outputs, including connection endpoints,
# port numbers, and resource identifiers for the MCA Application Processing System.

# Application Data Cache Outputs

output "redis_app_data_id" {
  description = "ID of the Redis application data replication group"
  value       = aws_elasticache_replication_group.redis_app_data.id
}

output "redis_app_data_arn" {
  description = "ARN of the Redis application data replication group"
  value       = aws_elasticache_replication_group.redis_app_data.arn
}

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

output "redis_app_data_port" {
  description = "Port number for the Redis application data cluster"
  value       = aws_elasticache_replication_group.redis_app_data.port
}

output "redis_app_data_engine_version" {
  description = "Redis engine version for the application data cluster"
  value       = aws_elasticache_replication_group.redis_app_data.engine_version
}

# User Sessions Cache Outputs

output "redis_user_sessions_id" {
  description = "ID of the Redis user sessions replication group"
  value       = aws_elasticache_replication_group.redis_user_sessions.id
}

output "redis_user_sessions_arn" {
  description = "ARN of the Redis user sessions replication group"
  value       = aws_elasticache_replication_group.redis_user_sessions.arn
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

output "redis_user_sessions_port" {
  description = "Port number for the Redis user sessions cluster"
  value       = aws_elasticache_replication_group.redis_user_sessions.port
}

output "redis_user_sessions_engine_version" {
  description = "Redis engine version for the user sessions cluster"
  value       = aws_elasticache_replication_group.redis_user_sessions.engine_version
}

# Connection String Templates for Different Service Types

output "redis_app_data_connection_string" {
  description = "Connection string for the Redis application data cluster (format: redis://host:port)"
  value       = "redis://${aws_elasticache_replication_group.redis_app_data.primary_endpoint_address}:${aws_elasticache_replication_group.redis_app_data.port}"
  sensitive   = true
}

output "redis_app_data_connection_string_tls" {
  description = "TLS connection string for the Redis application data cluster (format: rediss://host:port)"
  value       = "rediss://${aws_elasticache_replication_group.redis_app_data.primary_endpoint_address}:${aws_elasticache_replication_group.redis_app_data.port}"
  sensitive   = true
}

output "redis_user_sessions_connection_string" {
  description = "Connection string for the Redis user sessions cluster (format: redis://host:port)"
  value       = "redis://${aws_elasticache_replication_group.redis_user_sessions.primary_endpoint_address}:${aws_elasticache_replication_group.redis_user_sessions.port}"
  sensitive   = true
}

output "redis_user_sessions_connection_string_tls" {
  description = "TLS connection string for the Redis user sessions cluster (format: rediss://host:port)"
  value       = "rediss://${aws_elasticache_replication_group.redis_user_sessions.primary_endpoint_address}:${aws_elasticache_replication_group.redis_user_sessions.port}"
  sensitive   = true
}

# ioredis 5.3.2 Compatible Connection Configuration

output "redis_app_data_ioredis_config" {
  description = "ioredis 5.3.2 compatible configuration for the Redis application data cluster"
  value = jsonencode({
    host      = aws_elasticache_replication_group.redis_app_data.primary_endpoint_address
    port      = aws_elasticache_replication_group.redis_app_data.port
    tls       = true
    db        = 0
    keyPrefix = "mca:app:"
    retryStrategy = {
      maxRetryTime = 10000
      retries      = 10
    }
    commandTimeout = 5000
    enableOfflineQueue = true
    connectTimeout = 10000
    maxRetriesPerRequest = 3
  })
  sensitive = true
}

output "redis_user_sessions_ioredis_config" {
  description = "ioredis 5.3.2 compatible configuration for the Redis user sessions cluster"
  value = jsonencode({
    host      = aws_elasticache_replication_group.redis_user_sessions.primary_endpoint_address
    port      = aws_elasticache_replication_group.redis_user_sessions.port
    tls       = true
    db        = 0
    keyPrefix = "mca:session:"
    retryStrategy = {
      maxRetryTime = 10000
      retries      = 10
    }
    commandTimeout = 5000
    enableOfflineQueue = true
    connectTimeout = 10000
    maxRetriesPerRequest = 3
  })
  sensitive = true
}

# Monitoring and Logging Configuration

output "redis_app_data_cloudwatch_alarms" {
  description = "CloudWatch alarm ARNs for the Redis application data cluster"
  value = {
    cpu_utilization = aws_cloudwatch_metric_alarm.redis_app_data_cpu.arn
    memory_usage    = aws_cloudwatch_metric_alarm.redis_app_data_memory.arn
  }
}

output "redis_user_sessions_cloudwatch_alarms" {
  description = "CloudWatch alarm ARNs for the Redis user sessions cluster"
  value = {
    cpu_utilization = aws_cloudwatch_metric_alarm.redis_user_sessions_cpu.arn
    memory_usage    = aws_cloudwatch_metric_alarm.redis_user_sessions_memory.arn
  }
}

output "redis_log_group_names" {
  description = "CloudWatch log group names for Redis slow logs"
  value = {
    app_data      = "/aws/elasticache/${aws_elasticache_replication_group.redis_app_data.id}/slowlog"
    user_sessions = "/aws/elasticache/${aws_elasticache_replication_group.redis_user_sessions.id}/slowlog"
  }
}

# Security Configuration

output "redis_security_group_id" {
  description = "ID of the security group for Redis clusters"
  value       = aws_security_group.redis_security_group.id
}

output "redis_subnet_group_name" {
  description = "Name of the subnet group for Redis clusters"
  value       = aws_elasticache_subnet_group.redis_subnet_group.name
}

# TTL and Eviction Policy Information

output "redis_app_data_ttl_info" {
  description = "TTL and eviction policy information for the Redis application data cluster"
  value = {
    ttl            = "15-minutes"
    eviction_policy = "allkeys-lru"
    parameter_group = aws_elasticache_parameter_group.redis_app_data_params.name
  }
}

output "redis_user_sessions_ttl_info" {
  description = "TTL and eviction policy information for the Redis user sessions cluster"
  value = {
    ttl            = "24-hours"
    eviction_policy = "noeviction"
    parameter_group = aws_elasticache_parameter_group.redis_user_sessions_params.name
  }
}

# Environment Information

output "redis_environment" {
  description = "Environment in which Redis clusters are deployed"
  value       = var.environment
}

# Cluster Configuration

output "redis_cluster_config" {
  description = "Cluster configuration for Redis instances"
  value = {
    app_data = {
      num_node_groups         = aws_elasticache_replication_group.redis_app_data.cluster_mode[0].num_node_groups
      replicas_per_node_group = aws_elasticache_replication_group.redis_app_data.cluster_mode[0].replicas_per_node_group
      node_type               = aws_elasticache_replication_group.redis_app_data.node_type
      data_tiering_enabled    = aws_elasticache_replication_group.redis_app_data.data_tiering_enabled
    }
    user_sessions = {
      num_node_groups         = aws_elasticache_replication_group.redis_user_sessions.cluster_mode[0].num_node_groups
      replicas_per_node_group = aws_elasticache_replication_group.redis_user_sessions.cluster_mode[0].replicas_per_node_group
      node_type               = aws_elasticache_replication_group.redis_user_sessions.node_type
      data_tiering_enabled    = aws_elasticache_replication_group.redis_user_sessions.data_tiering_enabled
    }
  }
}