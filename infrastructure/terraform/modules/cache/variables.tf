# Redis Cache Module Variables
# This file defines all input variables for the Redis caching infrastructure

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "name_prefix" {
  description = "Prefix to be used in naming the Redis resources"
  type        = string
  default     = "mca-redis"
}

# Cluster configuration
variable "node_type" {
  description = "The instance type of the Redis nodes"
  type        = string
  default     = "cache.t3.medium" # Default for development
}

variable "memory_size" {
  description = "Memory size for Redis nodes in GB"
  type        = number
  default     = 2
}

variable "shard_count" {
  description = "Number of shards in the Redis cluster"
  type        = number
  default     = 3 # Minimum 3 shards for horizontal scalability
}

variable "replica_count" {
  description = "Number of replicas per shard"
  type        = number
  default     = 1 # At least 1 replica per shard
}

# TTL settings
variable "data_ttl_seconds" {
  description = "TTL for application data in seconds (default: 15 minutes)"
  type        = number
  default     = 900 # 15 minutes
}

variable "session_ttl_seconds" {
  description = "TTL for user sessions in seconds (default: 24 hours)"
  type        = number
  default     = 86400 # 24 hours
}

# Eviction policy
variable "cache_eviction_policy" {
  description = "Eviction policy for the cache instance"
  type        = string
  default     = "allkeys-lru"
  validation {
    condition     = contains(["volatile-lru", "allkeys-lru", "volatile-lfu", "allkeys-lfu", "volatile-random", "allkeys-random", "volatile-ttl", "noeviction"], var.cache_eviction_policy)
    error_message = "Eviction policy must be one of the Redis supported policies."
  }
}

variable "session_eviction_policy" {
  description = "Eviction policy for the session instance"
  type        = string
  default     = "noeviction"
  validation {
    condition     = contains(["volatile-lru", "allkeys-lru", "volatile-lfu", "allkeys-lfu", "volatile-random", "allkeys-random", "volatile-ttl", "noeviction"], var.session_eviction_policy)
    error_message = "Eviction policy must be one of the Redis supported policies."
  }
}

# Persistence configuration
variable "enable_aof_persistence" {
  description = "Enable AOF persistence for Redis"
  type        = bool
  default     = true
}

variable "snapshot_interval_minutes" {
  description = "Interval in minutes between RDB snapshots"
  type        = number
  default     = 60 # 60 minutes as specified
}

# Security configuration
variable "enable_transit_encryption" {
  description = "Enable TLS for Redis connections"
  type        = bool
  default     = true
}

variable "enable_at_rest_encryption" {
  description = "Enable encryption at rest for Redis data"
  type        = bool
  default     = true
}

# High availability configuration
variable "enable_automatic_failover" {
  description = "Enable automatic failover with Redis Sentinel"
  type        = bool
  default     = true
}

variable "failover_timeout_seconds" {
  description = "Timeout in seconds for failover operation"
  type        = number
  default     = 15 # 15-second failover time as specified
}

# Multi-AZ deployment
variable "multi_az_enabled" {
  description = "Enable Multi-AZ deployment for Redis cluster"
  type        = bool
  default     = true
}

# Connection configuration
variable "connection_timeout_seconds" {
  description = "Connection timeout in seconds"
  type        = number
  default     = 30
}

variable "connection_pool_size" {
  description = "Size of the connection pool for Redis"
  type        = number
  default     = 50
}

# Monitoring configuration
variable "enable_enhanced_monitoring" {
  description = "Enable enhanced monitoring for Redis cluster"
  type        = bool
  default     = true
}

variable "alarm_cpu_threshold_percent" {
  description = "CPU utilization threshold for alarm in percentage"
  type        = number
  default     = 75
}

variable "alarm_memory_threshold_percent" {
  description = "Memory utilization threshold for alarm in percentage"
  type        = number
  default     = 80
}

# Environment-specific overrides
variable "environment_config" {
  description = "Environment-specific configuration overrides"
  type = map(object({
    node_type     = string
    memory_size   = number
    shard_count   = number
    replica_count = number
  }))
  default = {
    development = {
      node_type     = "cache.t3.small"
      memory_size   = 1
      shard_count   = 1
      replica_count = 0
    },
    staging = {
      node_type     = "cache.t3.medium"
      memory_size   = 2
      shard_count   = 2
      replica_count = 1
    },
    production = {
      node_type     = "cache.m5.large"
      memory_size   = 4
      shard_count   = 3
      replica_count = 1
    }
  }
}

# Tags
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}