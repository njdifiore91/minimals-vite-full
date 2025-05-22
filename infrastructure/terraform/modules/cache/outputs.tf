# Redis Cache Module Outputs
# These outputs provide essential Redis information for other Terraform modules and application configuration

# Resource Identifiers
output "redis_cache_cluster_id" {
  description = "The ID of the Redis cache cluster"
  value       = aws_elasticache_replication_group.cache.id
}

output "redis_session_cluster_id" {
  description = "The ID of the Redis session cluster"
  value       = aws_elasticache_replication_group.sessions.id
}

output "redis_security_group_id" {
  description = "The ID of the security group for Redis clusters"
  value       = aws_security_group.redis.id
}

# Connection Endpoints
output "redis_cache_primary_endpoint" {
  description = "The primary endpoint address for the Redis cache cluster"
  value       = aws_elasticache_replication_group.cache.primary_endpoint_address
}

output "redis_cache_reader_endpoint" {
  description = "The reader endpoint address for the Redis cache cluster"
  value       = aws_elasticache_replication_group.cache.reader_endpoint_address
}

output "redis_session_primary_endpoint" {
  description = "The primary endpoint address for the Redis session cluster"
  value       = aws_elasticache_replication_group.sessions.primary_endpoint_address
}

output "redis_session_reader_endpoint" {
  description = "The reader endpoint address for the Redis session cluster"
  value       = aws_elasticache_replication_group.sessions.reader_endpoint_address
}

# Port Information
output "redis_port" {
  description = "The port on which Redis is listening"
  value       = 6379
}

# Connection Strings for ioredis 5.3.2
output "redis_cache_connection_string" {
  description = "Connection string for Redis cache cluster compatible with ioredis 5.3.2"
  value       = "redis://${aws_elasticache_replication_group.cache.primary_endpoint_address}:6379/0"
  sensitive   = true
}

output "redis_session_connection_string" {
  description = "Connection string for Redis session cluster compatible with ioredis 5.3.2"
  value       = "redis://${aws_elasticache_replication_group.sessions.primary_endpoint_address}:6379/0"
  sensitive   = true
}

output "redis_cache_connection_string_tls" {
  description = "TLS connection string for Redis cache cluster compatible with ioredis 5.3.2"
  value       = "rediss://${aws_elasticache_replication_group.cache.primary_endpoint_address}:6379/0"
  sensitive   = true
}

output "redis_session_connection_string_tls" {
  description = "TLS connection string for Redis session cluster compatible with ioredis 5.3.2"
  value       = "rediss://${aws_elasticache_replication_group.sessions.primary_endpoint_address}:6379/0"
  sensitive   = true
}

# Cluster Configuration
output "redis_cache_configuration_endpoint" {
  description = "The configuration endpoint for the Redis cache cluster"
  value       = aws_elasticache_replication_group.cache.configuration_endpoint_address
}

output "redis_session_configuration_endpoint" {
  description = "The configuration endpoint for the Redis session cluster"
  value       = aws_elasticache_replication_group.sessions.configuration_endpoint_address
}

# Monitoring and Logging
output "redis_cache_cloudwatch_log_group" {
  description = "The CloudWatch log group for Redis cache cluster"
  value       = aws_cloudwatch_log_group.redis_cache_logs.name
}

output "redis_session_cloudwatch_log_group" {
  description = "The CloudWatch log group for Redis session cluster"
  value       = aws_cloudwatch_log_group.redis_session_logs.name
}

output "redis_cache_alarm_topic_arn" {
  description = "The ARN of the SNS topic for Redis cache cluster alarms"
  value       = aws_sns_topic.redis_cache_alarms.arn
}

output "redis_session_alarm_topic_arn" {
  description = "The ARN of the SNS topic for Redis session cluster alarms"
  value       = aws_sns_topic.redis_session_alarms.arn
}

# TTL Settings
output "redis_cache_ttl_seconds" {
  description = "TTL for application data in Redis cache (15 minutes)"
  value       = 900 # 15 minutes in seconds
}

output "redis_session_ttl_seconds" {
  description = "TTL for user sessions in Redis session store (24 hours)"
  value       = 86400 # 24 hours in seconds
}

# Cluster Information
output "redis_cache_node_type" {
  description = "The node type of the Redis cache cluster"
  value       = aws_elasticache_replication_group.cache.node_type
}

output "redis_session_node_type" {
  description = "The node type of the Redis session cluster"
  value       = aws_elasticache_replication_group.sessions.node_type
}

output "redis_cache_num_shards" {
  description = "The number of shards in the Redis cache cluster"
  value       = aws_elasticache_replication_group.cache.num_node_groups
}

output "redis_session_num_shards" {
  description = "The number of shards in the Redis session cluster"
  value       = aws_elasticache_replication_group.sessions.num_node_groups
}

output "redis_cache_replicas_per_shard" {
  description = "The number of replicas per shard in the Redis cache cluster"
  value       = aws_elasticache_replication_group.cache.replicas_per_node_group
}

output "redis_session_replicas_per_shard" {
  description = "The number of replicas per shard in the Redis session cluster"
  value       = aws_elasticache_replication_group.sessions.replicas_per_node_group
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