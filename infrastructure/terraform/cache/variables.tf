# Variables for Redis 7.0 Cache Infrastructure
# This file defines all input variables for the Redis cache infrastructure used in the MCA Application Processing System

# Environment Configuration
variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

# Network Configuration
variable "vpc_id" {
  description = "VPC ID where Redis clusters will be deployed"
  type        = string
}

variable "redis_subnet_ids" {
  description = "List of subnet IDs for the Redis subnet group"
  type        = list(string)
}

variable "app_security_group_ids" {
  description = "List of security group IDs for application servers that need access to Redis"
  type        = list(string)
}

# Redis Instance Configuration
variable "redis_node_type" {
  description = "Redis node type (instance size)"
  type        = string
  default     = "cache.r6g.large"
}

variable "enable_data_tiering" {
  description = "Enable data tiering (requires r6gd node type)"
  type        = bool
  default     = false
}

# Cluster Configuration
variable "app_data_num_shards" {
  description = "Number of shards (node groups) for application data Redis cluster"
  type        = number
  default     = 3
}

variable "app_data_replicas_per_shard" {
  description = "Number of replicas per shard for application data Redis cluster"
  type        = number
  default     = 1
}

variable "user_sessions_num_shards" {
  description = "Number of shards (node groups) for user sessions Redis cluster"
  type        = number
  default     = 3
}

variable "user_sessions_replicas_per_shard" {
  description = "Number of replicas per shard for user sessions Redis cluster"
  type        = number
  default     = 1
}

# TTL Settings
variable "app_data_ttl_seconds" {
  description = "TTL for application data in seconds (default: 15 minutes)"
  type        = number
  default     = 900 # 15 minutes
}

variable "user_sessions_ttl_seconds" {
  description = "TTL for user sessions in seconds (default: 24 hours)"
  type        = number
  default     = 86400 # 24 hours
}

# Eviction Policy Configuration
variable "app_data_eviction_policy" {
  description = "Eviction policy for application data Redis cluster"
  type        = string
  default     = "allkeys-lru"
  validation {
    condition     = contains(["noeviction", "allkeys-lru", "volatile-lru", "allkeys-random", "volatile-random", "volatile-ttl"], var.app_data_eviction_policy)
    error_message = "Eviction policy must be one of: noeviction, allkeys-lru, volatile-lru, allkeys-random, volatile-random, volatile-ttl."
  }
}

variable "user_sessions_eviction_policy" {
  description = "Eviction policy for user sessions Redis cluster"
  type        = string
  default     = "noeviction"
  validation {
    condition     = contains(["noeviction", "allkeys-lru", "volatile-lru", "allkeys-random", "volatile-random", "volatile-ttl"], var.user_sessions_eviction_policy)
    error_message = "Eviction policy must be one of: noeviction, allkeys-lru, volatile-lru, allkeys-random, volatile-random, volatile-ttl."
  }
}

# Persistence Configuration
variable "enable_aof_persistence" {
  description = "Enable AOF persistence for Redis clusters"
  type        = bool
  default     = true
}

variable "aof_persistence_interval" {
  description = "AOF persistence fsync interval (appendfsync parameter)"
  type        = string
  default     = "everysec"
  validation {
    condition     = contains(["always", "everysec", "no"], var.aof_persistence_interval)
    error_message = "AOF persistence interval must be one of: always, everysec, no."
  }
}

# Backup Configuration
variable "snapshot_retention_limit" {
  description = "Number of days to retain automatic Redis snapshots"
  type        = number
  default     = 7
}

variable "snapshot_window" {
  description = "Daily time range during which automated snapshots are created"
  type        = string
  default     = "00:00-05:00"
}

# Maintenance Configuration
variable "maintenance_window" {
  description = "Weekly time range during which system maintenance can occur"
  type        = string
  default     = "sun:05:00-sun:09:00"
}

# Security Configuration
variable "transit_encryption_enabled" {
  description = "Enable encryption in transit for Redis clusters"
  type        = bool
  default     = true
}

variable "at_rest_encryption_enabled" {
  description = "Enable encryption at rest for Redis clusters"
  type        = bool
  default     = true
}

# Monitoring Configuration
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

variable "cpu_threshold" {
  description = "CPU utilization threshold percentage for Redis alarms"
  type        = number
  default     = 75
}

variable "memory_threshold" {
  description = "Memory usage threshold percentage for Redis alarms"
  type        = number
  default     = 80
}

# Environment-specific defaults
variable "environment_defaults" {
  description = "Default values for different environments"
  type = object({
    development = object({
      redis_node_type = string
      num_shards      = number
      replicas_per_shard = number
    })
    staging = object({
      redis_node_type = string
      num_shards      = number
      replicas_per_shard = number
    })
    production = object({
      redis_node_type = string
      num_shards      = number
      replicas_per_shard = number
    })
  })
  default = {
    development = {
      redis_node_type = "cache.r6g.large"
      num_shards      = 1
      replicas_per_shard = 1
    }
    staging = {
      redis_node_type = "cache.r6g.xlarge"
      num_shards      = 2
      replicas_per_shard = 1
    }
    production = {
      redis_node_type = "cache.r6g.2xlarge"
      num_shards      = 3
      replicas_per_shard = 1
    }
  }
}

# Feature Flags
variable "enable_multi_az" {
  description = "Enable Multi-AZ deployment for Redis clusters"
  type        = bool
  default     = true
}

variable "enable_automatic_failover" {
  description = "Enable automatic failover for Redis clusters"
  type        = bool
  default     = true
}

variable "enable_cluster_mode" {
  description = "Enable cluster mode for Redis clusters"
  type        = bool
  default     = true
}

variable "enable_performance_insights" {
  description = "Enable performance insights for Redis clusters"
  type        = bool
  default     = true
}

# Tags
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}