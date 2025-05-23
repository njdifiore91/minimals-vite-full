# Redis 7.0 Caching Infrastructure
# Main Terraform configuration file for Redis cache infrastructure
#
# This file initializes the Redis cache module with environment-specific settings
# and configures the Redis 7.0 cluster with appropriate memory allocation,
# eviction policies, and TTL settings as specified in the technical requirements.
#
# Key features:
# - Redis 7.0 for distributed caching and session management
# - Memory tiering with SSD persistence for cost optimization
# - TTL settings: 15 minutes for application data, 24 hours for user sessions
# - Different eviction policies for caching and sessions
# - Multi-AZ deployment for high availability

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
  }
  
  # Use remote state for production environments
  backend "s3" {
    # Backend configuration is partially provided via CLI arguments
    key     = "cache/terraform.tfstate"
    encrypt = true
  }
}

# Import global variables
data "terraform_remote_state" "global" {
  backend = "s3"
  
  config = {
    bucket = var.state_bucket
    key    = "global/terraform.tfstate"
    region = var.aws_region
  }
}

# Import network configuration
data "terraform_remote_state" "network" {
  backend = "s3"
  
  config = {
    bucket = var.state_bucket
    key    = "network/terraform.tfstate"
    region = var.aws_region
  }
}

# Local variables
locals {
  # Common tags for all resources
  common_tags = {
    Project     = "MCA Application Processing System"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Service     = "Redis Cache"
  }
  
  # VPC and subnet information from network state
  vpc_id     = data.terraform_remote_state.network.outputs.vpc_id
  subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids
  
  # Environment-specific Redis configuration
  redis_config = {
    development = {
      node_type     = "cache.t3.small"
      memory_size   = 1
      shard_count   = 1
      replica_count = 0
      multi_az      = false
    },
    staging = {
      node_type     = "cache.t3.medium"
      memory_size   = 2
      shard_count   = 2
      replica_count = 1
      multi_az      = true
    },
    production = {
      node_type     = "cache.m5.large"
      memory_size   = 4
      shard_count   = 3
      replica_count = 1
      multi_az      = true
    }
  }
}

# Redis cache module for the MCA Application Processing System
module "redis" {
  source = "../modules/cache"
  
  # Basic configuration
  environment = var.environment
  name_prefix = "mca-redis"
  
  # Network configuration
  vpc_id     = local.vpc_id
  subnet_ids = local.subnet_ids
  
  # Node configuration based on environment
  node_type     = local.redis_config[var.environment].node_type
  memory_size   = local.redis_config[var.environment].memory_size
  shard_count   = local.redis_config[var.environment].shard_count
  replica_count = local.redis_config[var.environment].replica_count
  
  # TTL settings as specified in requirements
  data_ttl_seconds    = 900    # 15 minutes for application data
  session_ttl_seconds = 86400  # 24 hours for user sessions
  
  # Eviction policies
  cache_eviction_policy   = "allkeys-lru"  # LRU eviction for cache
  session_eviction_policy = "noeviction"    # No eviction for sessions
  
  # Persistence configuration
  enable_aof_persistence    = true
  snapshot_interval_minutes = 60  # RDB snapshots every 60 minutes
  
  # Security configuration
  enable_transit_encryption = true
  enable_at_rest_encryption = true
  
  # High availability configuration
  enable_automatic_failover = true
  failover_timeout_seconds  = 15  # 15-second failover time
  multi_az_enabled          = local.redis_config[var.environment].multi_az
  
  # Connection configuration
  connection_timeout_seconds = 30
  connection_pool_size       = 50
  
  # Monitoring configuration
  enable_enhanced_monitoring    = true
  alarm_cpu_threshold_percent    = 75
  alarm_memory_threshold_percent = 80
  
  # Tags
  tags = local.common_tags
}

# Output the Redis endpoints and connection information
output "redis_cache_endpoint" {
  description = "Redis cache cluster endpoint for application data"
  value       = module.redis.redis_cache_endpoint
}

output "redis_session_endpoint" {
  description = "Redis session cluster endpoint for user sessions"
  value       = module.redis.redis_session_endpoint
}

output "redis_port" {
  description = "Redis port number"
  value       = module.redis.redis_port
}

output "redis_cache_connection_string" {
  description = "Redis cache connection string for application data"
  value       = "redis://${module.redis.redis_cache_endpoint}:${module.redis.redis_port}/0"
  sensitive   = true
}

output "redis_session_connection_string" {
  description = "Redis session connection string for user sessions"
  value       = "redis://${module.redis.redis_session_endpoint}:${module.redis.redis_port}/1"
  sensitive   = true
}

output "redis_security_group_id" {
  description = "Security group ID for Redis clusters"
  value       = module.redis.redis_security_group_id
}