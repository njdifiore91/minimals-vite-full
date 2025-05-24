# -----------------------------------------------
# Development Environment Outputs
# -----------------------------------------------
# This file exports essential information from the development environment
# as Terraform outputs, including connection endpoints, credentials, and
# resource identifiers. These outputs are consumed by application configuration
# and developers to connect to the infrastructure services.
# -----------------------------------------------

# -----------------------------------------------
# PostgreSQL Outputs
# -----------------------------------------------

output "postgresql_endpoint" {
  description = "The endpoint of the PostgreSQL database"
  value       = module.postgresql.endpoint
}

output "postgresql_port" {
  description = "The port of the PostgreSQL database"
  value       = module.postgresql.port
}

output "postgresql_database" {
  description = "The name of the PostgreSQL database"
  value       = module.postgresql.database_name
}

output "postgresql_username" {
  description = "The username for the PostgreSQL database"
  value       = module.postgresql.username
}

output "postgresql_password" {
  description = "The password for the PostgreSQL database"
  value       = module.postgresql.password
  sensitive   = true
}

output "postgresql_connection_string" {
  description = "The connection string for the PostgreSQL database"
  value       = "postgresql://${module.postgresql.username}:${module.postgresql.password}@${module.postgresql.endpoint}:${module.postgresql.port}/${module.postgresql.database_name}"
  sensitive   = true
}

output "postgresql_jdbc_url" {
  description = "The JDBC URL for the PostgreSQL database (for Java applications)"
  value       = "jdbc:postgresql://${module.postgresql.endpoint}:${module.postgresql.port}/${module.postgresql.database_name}"
}

# -----------------------------------------------
# RabbitMQ Outputs
# -----------------------------------------------

output "rabbitmq_endpoint" {
  description = "The endpoint of the RabbitMQ service"
  value       = module.rabbitmq.endpoint
}

output "rabbitmq_port" {
  description = "The port of the RabbitMQ service"
  value       = module.rabbitmq.port
}

output "rabbitmq_username" {
  description = "The username for the RabbitMQ service"
  value       = module.rabbitmq.username
}

output "rabbitmq_password" {
  description = "The password for the RabbitMQ service"
  value       = module.rabbitmq.password
  sensitive   = true
}

output "rabbitmq_management_url" {
  description = "The URL for the RabbitMQ management interface"
  value       = "http://${module.rabbitmq.endpoint}:15672"
}

output "rabbitmq_connection_string" {
  description = "The connection string for the RabbitMQ service"
  value       = "amqp://${module.rabbitmq.username}:${module.rabbitmq.password}@${module.rabbitmq.endpoint}:${module.rabbitmq.port}"
  sensitive   = true
}

# -----------------------------------------------
# Redis Outputs
# -----------------------------------------------

# Cache Redis instance
output "redis_cache_endpoint" {
  description = "The endpoint of the Redis cache instance"
  value       = module.redis.cache_endpoint
}

output "redis_cache_port" {
  description = "The port of the Redis cache instance"
  value       = module.redis.cache_port
}

output "redis_cache_connection_string" {
  description = "The connection string for the Redis cache instance"
  value       = "redis://${module.redis.password}@${module.redis.cache_endpoint}:${module.redis.cache_port}/0"
  sensitive   = true
}

# Session Redis instance
output "redis_session_endpoint" {
  description = "The endpoint of the Redis session instance"
  value       = module.redis.session_endpoint
}

output "redis_session_port" {
  description = "The port of the Redis session instance"
  value       = module.redis.session_port
}

output "redis_session_connection_string" {
  description = "The connection string for the Redis session instance"
  value       = "redis://${module.redis.password}@${module.redis.session_endpoint}:${module.redis.session_port}/0"
  sensitive   = true
}

output "redis_password" {
  description = "The password for the Redis instances"
  value       = module.redis.password
  sensitive   = true
}

# -----------------------------------------------
# S3 Storage Outputs
# -----------------------------------------------

output "s3_bucket_name" {
  description = "The name of the S3 bucket for document storage"
  value       = module.s3_storage.bucket_name
}

output "s3_endpoint" {
  description = "The endpoint of the S3-compatible storage service"
  value       = module.s3_storage.endpoint
}

output "s3_region" {
  description = "The region of the S3-compatible storage service"
  value       = module.s3_storage.region
}

output "s3_access_key" {
  description = "The access key for the S3-compatible storage service"
  value       = module.s3_storage.access_key
}

output "s3_secret_key" {
  description = "The secret key for the S3-compatible storage service"
  value       = module.s3_storage.secret_key
  sensitive   = true
}

# -----------------------------------------------
# Development-specific Outputs
# -----------------------------------------------

output "development_environment" {
  description = "Indicator that this is the development environment"
  value       = "true"
}

output "local_development_urls" {
  description = "URLs for local development services"
  value = {
    api_gateway     = "http://localhost:8000"
    frontend        = "http://localhost:3000"
    email_service   = "http://localhost:3001"
    document_service = "http://localhost:3002"
    ocr_service     = "http://localhost:3003"
    data_service    = "http://localhost:8080"
    notification_service = "http://localhost:3004"
  }
}

# -----------------------------------------------
# Service Connection Configuration
# -----------------------------------------------

output "service_connection_config" {
  description = "Configuration for connecting to services in the development environment"
  value = {
    database = {
      host     = module.postgresql.endpoint
      port     = module.postgresql.port
      name     = module.postgresql.database_name
      username = module.postgresql.username
      password = module.postgresql.password
      ssl_mode = "disable"  # Development typically doesn't use SSL
    }
    rabbitmq = {
      host     = module.rabbitmq.endpoint
      port     = module.rabbitmq.port
      username = module.rabbitmq.username
      password = module.rabbitmq.password
      vhost    = "/"
      exchanges = {
        documents = "mca.documents"
      }
      queues = {
        document_processing = "document-processing"
        data_extraction    = "data-extraction"
        notification       = "notification"
      }
    }
    redis = {
      cache = {
        host     = module.redis.cache_endpoint
        port     = module.redis.cache_port
        password = module.redis.password
        database = 0
        ttl      = 900  # 15 minutes in seconds
      }
      session = {
        host     = module.redis.session_endpoint
        port     = module.redis.session_port
        password = module.redis.password
        database = 0
        ttl      = 86400  # 24 hours in seconds
      }
    }
    storage = {
      bucket   = module.s3_storage.bucket_name
      endpoint = module.s3_storage.endpoint
      region   = module.s3_storage.region
      access_key = module.s3_storage.access_key
      secret_key = module.s3_storage.secret_key
      encryption = "AES256"
      url_expiration = 900  # 15 minutes in seconds
    }
  }
  sensitive = true
}

# -----------------------------------------------
# Environment Variables for Applications
# -----------------------------------------------

output "environment_variables" {
  description = "Environment variables for configuring applications in the development environment"
  value = {
    # Database configuration
    DATABASE_URL      = "postgresql://${module.postgresql.username}:${module.postgresql.password}@${module.postgresql.endpoint}:${module.postgresql.port}/${module.postgresql.database_name}"
    DATABASE_HOST     = module.postgresql.endpoint
    DATABASE_PORT     = module.postgresql.port
    DATABASE_NAME     = module.postgresql.database_name
    DATABASE_USER     = module.postgresql.username
    DATABASE_PASSWORD = module.postgresql.password
    
    # RabbitMQ configuration
    RABBITMQ_URL      = "amqp://${module.rabbitmq.username}:${module.rabbitmq.password}@${module.rabbitmq.endpoint}:${module.rabbitmq.port}"
    RABBITMQ_HOST     = module.rabbitmq.endpoint
    RABBITMQ_PORT     = module.rabbitmq.port
    RABBITMQ_USER     = module.rabbitmq.username
    RABBITMQ_PASSWORD = module.rabbitmq.password
    
    # Redis configuration
    REDIS_CACHE_URL   = "redis://${module.redis.password}@${module.redis.cache_endpoint}:${module.redis.cache_port}/0"
    REDIS_SESSION_URL = "redis://${module.redis.password}@${module.redis.session_endpoint}:${module.redis.session_port}/0"
    REDIS_PASSWORD    = module.redis.password
    
    # S3 configuration
    S3_BUCKET         = module.s3_storage.bucket_name
    S3_ENDPOINT       = module.s3_storage.endpoint
    S3_REGION         = module.s3_storage.region
    S3_ACCESS_KEY     = module.s3_storage.access_key
    S3_SECRET_KEY     = module.s3_storage.secret_key
    
    # Application configuration
    NODE_ENV          = "development"
    LOG_LEVEL         = "debug"
    API_GATEWAY_URL   = "http://localhost:8000"
    
    # JWT configuration for development
    JWT_SECRET        = "dev-jwt-secret-key-for-local-development-only"
    JWT_EXPIRY        = "3600"  # 1 hour in seconds
    REFRESH_EXPIRY    = "604800"  # 7 days in seconds
  }
  sensitive = true
}