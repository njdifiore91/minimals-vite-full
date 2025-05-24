# Redis Cache Module Outputs
# This file exports essential Redis information as module outputs, including connection endpoints,
# port numbers, and resource identifiers. These outputs are consumed by other Terraform modules
# and application configuration.

# ---------------------------------------------------------------------------------------------------------------------
# Redis Cache Cluster Outputs
# ---------------------------------------------------------------------------------------------------------------------

output "redis_cache_endpoint" {
  description = "Redis cache cluster configuration endpoint address for application data caching (15-minute TTL)"
  value       = aws_elasticache_replication_group.redis_cache.configuration_endpoint_address
}

output "redis_cache_primary_endpoint" {
  description = "Redis cache cluster primary endpoint address (for non-clustered clients)"
  value       = aws_elasticache_replication_group.redis_cache.primary_endpoint_address
}

output "redis_cache_reader_endpoint" {
  description = "Redis cache cluster reader endpoint address for read operations"
  value       = aws_elasticache_replication_group.redis_cache.reader_endpoint_address
}

output "redis_cache_nodes" {
  description = "List of node objects including id, address, port, and availability zone"
  value       = aws_elasticache_replication_group.redis_cache.member_clusters
}

output "redis_cache_arn" {
  description = "ARN of the Redis cache cluster"
  value       = aws_elasticache_replication_group.redis_cache.arn
}

output "redis_cache_id" {
  description = "ID of the Redis cache cluster"
  value       = aws_elasticache_replication_group.redis_cache.id
}

output "redis_cache_engine_version" {
  description = "Redis engine version for the cache cluster"
  value       = aws_elasticache_replication_group.redis_cache.engine_version_actual
}

# ---------------------------------------------------------------------------------------------------------------------
# Redis Session Cluster Outputs
# ---------------------------------------------------------------------------------------------------------------------

output "redis_session_endpoint" {
  description = "Redis session cluster configuration endpoint address for session management (24-hour TTL)"
  value       = aws_elasticache_replication_group.redis_session.configuration_endpoint_address
}

output "redis_session_primary_endpoint" {
  description = "Redis session cluster primary endpoint address (for non-clustered clients)"
  value       = aws_elasticache_replication_group.redis_session.primary_endpoint_address
}

output "redis_session_reader_endpoint" {
  description = "Redis session cluster reader endpoint address for read operations"
  value       = aws_elasticache_replication_group.redis_session.reader_endpoint_address
}

output "redis_session_nodes" {
  description = "List of node objects including id, address, port, and availability zone"
  value       = aws_elasticache_replication_group.redis_session.member_clusters
}

output "redis_session_arn" {
  description = "ARN of the Redis session cluster"
  value       = aws_elasticache_replication_group.redis_session.arn
}

output "redis_session_id" {
  description = "ID of the Redis session cluster"
  value       = aws_elasticache_replication_group.redis_session.id
}

output "redis_session_engine_version" {
  description = "Redis engine version for the session cluster"
  value       = aws_elasticache_replication_group.redis_session.engine_version_actual
}

# ---------------------------------------------------------------------------------------------------------------------
# Common Redis Configuration Outputs
# ---------------------------------------------------------------------------------------------------------------------

output "redis_port" {
  description = "Port number for Redis connections"
  value       = local.redis_port
}

output "redis_security_group_id" {
  description = "ID of the security group for Redis clusters"
  value       = aws_security_group.redis.id
}

output "redis_subnet_group_name" {
  description = "Name of the subnet group for Redis clusters"
  value       = aws_elasticache_subnet_group.redis.name
}

output "redis_cache_parameter_group_name" {
  description = "Name of the parameter group for Redis cache cluster"
  value       = aws_elasticache_parameter_group.redis_cache.name
}

output "redis_session_parameter_group_name" {
  description = "Name of the parameter group for Redis session cluster"
  value       = aws_elasticache_parameter_group.redis_session.name
}

# ---------------------------------------------------------------------------------------------------------------------
# Connection String Templates for ioredis 5.3.2 Client Library
# ---------------------------------------------------------------------------------------------------------------------

output "redis_cache_connection_string" {
  description = "Connection string template for Redis cache cluster using ioredis 5.3.2"
  value       = "redis://${aws_elasticache_replication_group.redis_cache.configuration_endpoint_address}:${local.redis_port}"
  sensitive   = true
}

output "redis_session_connection_string" {
  description = "Connection string template for Redis session cluster using ioredis 5.3.2"
  value       = "redis://${aws_elasticache_replication_group.redis_session.configuration_endpoint_address}:${local.redis_port}"
  sensitive   = true
}

output "redis_cache_connection_string_with_auth" {
  description = "Connection string template with authentication for Redis cache cluster using ioredis 5.3.2"
  value       = var.enable_transit_encryption ? "rediss://:${aws_secretsmanager_secret.redis_auth_token.arn}@${aws_elasticache_replication_group.redis_cache.configuration_endpoint_address}:${local.redis_port}" : "redis://:${aws_secretsmanager_secret.redis_auth_token.arn}@${aws_elasticache_replication_group.redis_cache.configuration_endpoint_address}:${local.redis_port}"
  sensitive   = true
}

output "redis_session_connection_string_with_auth" {
  description = "Connection string template with authentication for Redis session cluster using ioredis 5.3.2"
  value       = var.enable_transit_encryption ? "rediss://:${aws_secretsmanager_secret.redis_auth_token.arn}@${aws_elasticache_replication_group.redis_session.configuration_endpoint_address}:${local.redis_port}" : "redis://:${aws_secretsmanager_secret.redis_auth_token.arn}@${aws_elasticache_replication_group.redis_session.configuration_endpoint_address}:${local.redis_port}"
  sensitive   = true
}

# ---------------------------------------------------------------------------------------------------------------------
# ioredis 5.3.2 Client Configuration Templates
# ---------------------------------------------------------------------------------------------------------------------

output "redis_cache_ioredis_config" {
  description = "Configuration template for Redis cache cluster using ioredis 5.3.2"
  value = {
    host                  = aws_elasticache_replication_group.redis_cache.configuration_endpoint_address
    port                  = local.redis_port
    password              = aws_secretsmanager_secret.redis_auth_token.arn
    tls                   = var.enable_transit_encryption
    db                    = 0
    keyPrefix             = "cache:"
    connectTimeout        = var.connection_timeout_seconds * 1000
    maxRetriesPerRequest  = 3
    enableReadyCheck      = true
    enableOfflineQueue    = true
    connectionName        = "${var.name_prefix}-${var.environment}-cache"
    lazyConnect           = false
    retryStrategy         = "function(times) { return Math.min(times * 50, 2000); }"
    defaultTTL            = var.data_ttl_seconds
  }
  sensitive = true
}

output "redis_session_ioredis_config" {
  description = "Configuration template for Redis session cluster using ioredis 5.3.2"
  value = {
    host                  = aws_elasticache_replication_group.redis_session.configuration_endpoint_address
    port                  = local.redis_port
    password              = aws_secretsmanager_secret.redis_auth_token.arn
    tls                   = var.enable_transit_encryption
    db                    = 0
    keyPrefix             = "session:"
    connectTimeout        = var.connection_timeout_seconds * 1000
    maxRetriesPerRequest  = 3
    enableReadyCheck      = true
    enableOfflineQueue    = true
    connectionName        = "${var.name_prefix}-${var.environment}-session"
    lazyConnect           = false
    retryStrategy         = "function(times) { return Math.min(times * 50, 2000); }"
    defaultTTL            = var.session_ttl_seconds
  }
  sensitive = true
}

# ---------------------------------------------------------------------------------------------------------------------
# Monitoring and Logging Outputs
# ---------------------------------------------------------------------------------------------------------------------

output "redis_cache_cloudwatch_log_group" {
  description = "CloudWatch log group for Redis cache cluster"
  value       = aws_cloudwatch_log_group.redis_cache_logs.name
}

output "redis_session_cloudwatch_log_group" {
  description = "CloudWatch log group for Redis session cluster"
  value       = aws_cloudwatch_log_group.redis_session_logs.name
}

output "redis_cache_alarm_cpu" {
  description = "CloudWatch alarm for Redis cache cluster CPU utilization"
  value       = aws_cloudwatch_metric_alarm.redis_cache_cpu.arn
}

output "redis_cache_alarm_memory" {
  description = "CloudWatch alarm for Redis cache cluster memory utilization"
  value       = aws_cloudwatch_metric_alarm.redis_cache_memory.arn
}

output "redis_session_alarm_cpu" {
  description = "CloudWatch alarm for Redis session cluster CPU utilization"
  value       = aws_cloudwatch_metric_alarm.redis_session_cpu.arn
}

output "redis_session_alarm_memory" {
  description = "CloudWatch alarm for Redis session cluster memory utilization"
  value       = aws_cloudwatch_metric_alarm.redis_session_memory.arn
}

output "redis_cache_sns_topic" {
  description = "SNS topic for Redis cache cluster alarms"
  value       = aws_sns_topic.redis_cache_alarms.arn
}

output "redis_session_sns_topic" {
  description = "SNS topic for Redis session cluster alarms"
  value       = aws_sns_topic.redis_session_alarms.arn
}

# ---------------------------------------------------------------------------------------------------------------------
# Security Outputs
# ---------------------------------------------------------------------------------------------------------------------

output "redis_auth_token_secret_arn" {
  description = "ARN of the secret containing the Redis authentication token"
  value       = aws_secretsmanager_secret.redis_auth_token.arn
  sensitive   = true
}

output "redis_encryption_kms_key_arn" {
  description = "ARN of the KMS key used for Redis encryption at rest (if enabled)"
  value       = var.enable_at_rest_encryption ? aws_kms_key.redis_encryption[0].arn : null
  sensitive   = true
}

output "redis_cache_user_id" {
  description = "ID of the Redis user for cache cluster"
  value       = aws_elasticache_user.redis_cache_user.user_id
}

output "redis_session_user_id" {
  description = "ID of the Redis user for session cluster"
  value       = aws_elasticache_user.redis_session_user.user_id
}

output "redis_cache_user_group_id" {
  description = "ID of the Redis user group for cache cluster"
  value       = aws_elasticache_user_group.redis_cache_user_group.user_group_id
}

output "redis_session_user_group_id" {
  description = "ID of the Redis user group for session cluster"
  value       = aws_elasticache_user_group.redis_session_user_group.user_group_id
}

# ---------------------------------------------------------------------------------------------------------------------
# Service Integration Outputs
# ---------------------------------------------------------------------------------------------------------------------

output "redis_cache_service_integration" {
  description = "Integration details for connecting services to Redis cache cluster"
  value = {
    endpoint             = aws_elasticache_replication_group.redis_cache.configuration_endpoint_address
    port                 = local.redis_port
    auth_token_secret    = aws_secretsmanager_secret.redis_auth_token.arn
    security_group_id    = aws_security_group.redis.id
    parameter_group_name = aws_elasticache_parameter_group.redis_cache.name
    ttl_seconds          = var.data_ttl_seconds
    eviction_policy      = var.cache_eviction_policy
    tls_enabled          = var.enable_transit_encryption
    key_prefix           = "cache:"
  }
  sensitive = true
}

output "redis_session_service_integration" {
  description = "Integration details for connecting services to Redis session cluster"
  value = {
    endpoint             = aws_elasticache_replication_group.redis_session.configuration_endpoint_address
    port                 = local.redis_port
    auth_token_secret    = aws_secretsmanager_secret.redis_auth_token.arn
    security_group_id    = aws_security_group.redis.id
    parameter_group_name = aws_elasticache_parameter_group.redis_session.name
    ttl_seconds          = var.session_ttl_seconds
    eviction_policy      = var.session_eviction_policy
    tls_enabled          = var.enable_transit_encryption
    key_prefix           = "session:"
  }
  sensitive = true
}