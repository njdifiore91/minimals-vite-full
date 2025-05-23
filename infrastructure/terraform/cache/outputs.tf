# Redis Cache Infrastructure Outputs
# These outputs provide essential Redis information for other Terraform modules and application configuration

# Resource Identifiers
output "redis_app_data_replication_group_id" {
  description = "The ID of the Redis application data replication group"
  value       = module.redis_app_data.replication_group_id
}

output "redis_user_sessions_replication_group_id" {
  description = "The ID of the Redis user sessions replication group"
  value       = module.redis_user_sessions.replication_group_id
}

# Connection Endpoints - Primary
output "redis_app_data_primary_endpoint" {
  description = "The primary endpoint address for the Redis application data cluster"
  value       = module.redis_app_data.primary_endpoint_address
}

output "redis_user_sessions_primary_endpoint" {
  description = "The primary endpoint address for the Redis user sessions cluster"
  value       = module.redis_user_sessions.primary_endpoint_address
}

# Connection Endpoints - Reader
output "redis_app_data_reader_endpoint" {
  description = "The reader endpoint address for the Redis application data cluster"
  value       = module.redis_app_data.reader_endpoint_address
}

output "redis_user_sessions_reader_endpoint" {
  description = "The reader endpoint address for the Redis user sessions cluster"
  value       = module.redis_user_sessions.reader_endpoint_address
}

# Configuration Endpoints (for cluster mode)
output "redis_app_data_configuration_endpoint" {
  description = "The configuration endpoint for the Redis application data cluster (cluster mode)"
  value       = module.redis_app_data.configuration_endpoint_address
}

output "redis_user_sessions_configuration_endpoint" {
  description = "The configuration endpoint for the Redis user sessions cluster (cluster mode)"
  value       = module.redis_user_sessions.configuration_endpoint_address
}

# Port Information
output "redis_app_data_port" {
  description = "The port on which Redis application data cluster is listening"
  value       = module.redis_app_data.port
}

output "redis_user_sessions_port" {
  description = "The port on which Redis user sessions cluster is listening"
  value       = module.redis_user_sessions.port
}

# Connection Strings for ioredis 5.3.2 (non-TLS)
output "redis_app_data_connection_string" {
  description = "Connection string for Redis application data cluster compatible with ioredis 5.3.2"
  value       = "redis://${module.redis_app_data.primary_endpoint_address}:${module.redis_app_data.port}/0"
  sensitive   = true
}

output "redis_user_sessions_connection_string" {
  description = "Connection string for Redis user sessions cluster compatible with ioredis 5.3.2"
  value       = "redis://${module.redis_user_sessions.primary_endpoint_address}:${module.redis_user_sessions.port}/0"
  sensitive   = true
}

# Connection Strings for ioredis 5.3.2 (TLS)
output "redis_app_data_connection_string_tls" {
  description = "TLS connection string for Redis application data cluster compatible with ioredis 5.3.2"
  value       = "rediss://${module.redis_app_data.primary_endpoint_address}:${module.redis_app_data.port}/0"
  sensitive   = true
}

output "redis_user_sessions_connection_string_tls" {
  description = "TLS connection string for Redis user sessions cluster compatible with ioredis 5.3.2"
  value       = "rediss://${module.redis_user_sessions.primary_endpoint_address}:${module.redis_user_sessions.port}/0"
  sensitive   = true
}

# Cluster Mode Connection Strings (for ioredis cluster mode)
output "redis_app_data_cluster_connection_string" {
  description = "Cluster mode connection string for Redis application data cluster"
  value       = var.enable_cluster_mode ? "redis://${module.redis_app_data.configuration_endpoint_address}:${module.redis_app_data.port}" : null
  sensitive   = true
}

output "redis_user_sessions_cluster_connection_string" {
  description = "Cluster mode connection string for Redis user sessions cluster"
  value       = var.enable_cluster_mode ? "redis://${module.redis_user_sessions.configuration_endpoint_address}:${module.redis_user_sessions.port}" : null
  sensitive   = true
}

# Cluster Mode Connection Strings with TLS
output "redis_app_data_cluster_connection_string_tls" {
  description = "Cluster mode TLS connection string for Redis application data cluster"
  value       = var.enable_cluster_mode ? "rediss://${module.redis_app_data.configuration_endpoint_address}:${module.redis_app_data.port}" : null
  sensitive   = true
}

output "redis_user_sessions_cluster_connection_string_tls" {
  description = "Cluster mode TLS connection string for Redis user sessions cluster"
  value       = var.enable_cluster_mode ? "rediss://${module.redis_user_sessions.configuration_endpoint_address}:${module.redis_user_sessions.port}" : null
  sensitive   = true
}

# TTL Settings
output "redis_app_data_ttl_seconds" {
  description = "TTL for application data in Redis cache (15 minutes)"
  value       = var.app_data_ttl_seconds
}

output "redis_user_sessions_ttl_seconds" {
  description = "TTL for user sessions in Redis session store (24 hours)"
  value       = var.user_sessions_ttl_seconds
}

# Eviction Policies
output "redis_app_data_eviction_policy" {
  description = "Eviction policy for Redis application data cluster"
  value       = var.app_data_eviction_policy
}

output "redis_user_sessions_eviction_policy" {
  description = "Eviction policy for Redis user sessions cluster"
  value       = var.user_sessions_eviction_policy
}

# Monitoring and Logging
output "redis_dashboard_url" {
  description = "URL to the Redis performance dashboard in CloudWatch"
  value       = "https://${local.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${local.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.redis_performance_dashboard.dashboard_name}"
}

output "redis_app_data_alarm_actions" {
  description = "List of ARNs of actions to take when Redis application data alarms are triggered"
  value       = var.alarm_actions
}

output "redis_user_sessions_alarm_actions" {
  description = "List of ARNs of actions to take when Redis user sessions alarms are triggered"
  value       = var.alarm_actions
}

# SSM Parameter Paths
output "redis_app_data_endpoint_ssm_parameter" {
  description = "SSM parameter path for Redis application data endpoint"
  value       = aws_ssm_parameter.redis_app_data_endpoint.name
}

output "redis_user_sessions_endpoint_ssm_parameter" {
  description = "SSM parameter path for Redis user sessions endpoint"
  value       = aws_ssm_parameter.redis_user_sessions_endpoint.name
}

output "redis_app_data_connection_string_ssm_parameter" {
  description = "SSM parameter path for Redis application data connection string"
  value       = aws_ssm_parameter.redis_app_data_connection_string.name
}

output "redis_user_sessions_connection_string_ssm_parameter" {
  description = "SSM parameter path for Redis user sessions connection string"
  value       = aws_ssm_parameter.redis_user_sessions_connection_string.name
}

# Cluster Information
output "redis_app_data_node_type" {
  description = "The node type of the Redis application data cluster"
  value       = local.redis_node_type
}

output "redis_user_sessions_node_type" {
  description = "The node type of the Redis user sessions cluster"
  value       = local.redis_node_type
}

output "redis_app_data_num_shards" {
  description = "The number of shards in the Redis application data cluster"
  value       = local.app_data_num_shards
}

output "redis_user_sessions_num_shards" {
  description = "The number of shards in the Redis user sessions cluster"
  value       = local.user_sessions_num_shards
}

output "redis_app_data_replicas_per_shard" {
  description = "The number of replicas per shard in the Redis application data cluster"
  value       = local.app_data_replicas_per_shard
}

output "redis_user_sessions_replicas_per_shard" {
  description = "The number of replicas per shard in the Redis user sessions cluster"
  value       = local.user_sessions_replicas_per_shard
}

# Version Information
output "redis_version" {
  description = "The version of Redis used in the clusters"
  value       = "7.0"
}

output "ioredis_client_version" {
  description = "The recommended ioredis client version for connecting to Redis"
  value       = "5.3.2"
}

# Security Information
output "redis_transit_encryption_enabled" {
  description = "Whether transit encryption is enabled for Redis clusters"
  value       = var.transit_encryption_enabled
}

output "redis_at_rest_encryption_enabled" {
  description = "Whether at-rest encryption is enabled for Redis clusters"
  value       = var.at_rest_encryption_enabled
}

# High Availability Information
output "redis_multi_az_enabled" {
  description = "Whether multi-AZ is enabled for Redis clusters"
  value       = var.enable_multi_az
}

output "redis_automatic_failover_enabled" {
  description = "Whether automatic failover is enabled for Redis clusters"
  value       = var.enable_automatic_failover
}

# Data Tiering Information
output "redis_data_tiering_enabled" {
  description = "Whether data tiering is enabled for Redis clusters"
  value       = local.enable_data_tiering
}