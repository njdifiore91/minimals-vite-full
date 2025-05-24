# -----------------------------------------------
# Staging Environment Outputs
# -----------------------------------------------
# This file exports essential information from the staging environment as Terraform outputs,
# including connection endpoints, credentials, and resource identifiers. These outputs are
# consumed by application configuration and CI/CD pipelines to connect to the infrastructure services.

# -----------------------------------------------
# PostgreSQL Database Outputs
# -----------------------------------------------

output "database_primary_endpoint" {
  description = "The connection endpoint for the primary PostgreSQL instance in staging"
  value       = module.database.primary_endpoint
}

output "database_replica_endpoints" {
  description = "The connection endpoints for the PostgreSQL read replicas in staging"
  value       = module.database.replica_endpoints
}

output "database_name" {
  description = "The name of the PostgreSQL database in staging"
  value       = module.database.database_name
}

output "database_username" {
  description = "The master username for the PostgreSQL database in staging"
  value       = module.database.database_username
  sensitive   = true
}

output "database_connection_pooling_endpoint" {
  description = "The endpoint for the PgBouncer connection pooling instance in staging"
  value       = module.database.pgbouncer_endpoints[0]
}

output "database_connection_pooling_port" {
  description = "The port for the PgBouncer connection pooling instance in staging"
  value       = module.database.pgbouncer_port
}

# Service-specific connection strings
output "database_java_connection_string" {
  description = "JDBC connection string for the primary PostgreSQL instance in staging"
  value       = module.database.spring_datasource_url
}

output "database_java_replica_connection_string" {
  description = "JDBC connection string for the PostgreSQL read replicas in staging"
  value       = module.database.spring_replica_datasource_url
}

output "database_node_connection_string" {
  description = "Node.js connection string for the primary PostgreSQL instance in staging"
  value       = module.database.node_connection_string
  sensitive   = true
}

output "database_node_replica_connection_string" {
  description = "Node.js connection string for the PostgreSQL read replicas in staging"
  value       = module.database.node_replica_connection_string
  sensitive   = true
}

output "database_python_connection_string" {
  description = "Python connection string for the primary PostgreSQL instance in staging"
  value       = module.database.python_connection_string
  sensitive   = true
}

output "database_python_replica_connection_string" {
  description = "Python connection string for the PostgreSQL read replicas in staging"
  value       = module.database.python_replica_connection_string
  sensitive   = true
}

# -----------------------------------------------
# RabbitMQ Messaging Outputs
# -----------------------------------------------

output "rabbitmq_endpoints" {
  description = "The AMQP endpoints of the RabbitMQ cluster in staging"
  value       = module.messaging.rabbitmq_endpoints
}

output "rabbitmq_ssl_endpoints" {
  description = "The AMQPS (SSL) endpoints of the RabbitMQ cluster in staging"
  value       = module.messaging.rabbitmq_ssl_endpoints
}

output "rabbitmq_host" {
  description = "The primary host of the RabbitMQ cluster in staging"
  value       = module.messaging.rabbitmq_host
}

output "rabbitmq_port" {
  description = "The AMQP port of the RabbitMQ cluster in staging"
  value       = module.messaging.rabbitmq_port
}

output "rabbitmq_ssl_port" {
  description = "The AMQPS (SSL) port of the RabbitMQ cluster in staging"
  value       = module.messaging.rabbitmq_ssl_port
}

output "rabbitmq_management_endpoint" {
  description = "The management UI endpoint of the RabbitMQ cluster in staging"
  value       = module.messaging.rabbitmq_management_endpoint
}

output "rabbitmq_management_port" {
  description = "The management UI port of the RabbitMQ cluster in staging"
  value       = module.messaging.rabbitmq_management_port
}

output "rabbitmq_admin_secret_arn" {
  description = "The ARN of the secret containing RabbitMQ admin credentials in staging"
  value       = module.messaging.rabbitmq_admin_secret_arn
}

# Service-specific connection parameters
output "rabbitmq_service_connection_params" {
  description = "Service-specific connection parameters for RabbitMQ in staging"
  value       = module.messaging.rabbitmq_service_connection_params
}

# Connection strings for amqplib 0.10.3
output "rabbitmq_connection_string" {
  description = "The connection string for RabbitMQ in staging (without credentials)"
  value       = module.messaging.rabbitmq_connection_string
}

output "rabbitmq_ssl_connection_string" {
  description = "The SSL connection string for RabbitMQ in staging (without credentials)"
  value       = module.messaging.rabbitmq_ssl_connection_string
}

output "rabbitmq_amqplib_options" {
  description = "Connection options for amqplib 0.10.3 client library in staging"
  value       = module.messaging.rabbitmq_amqplib_options
}

# Queue and exchange information
output "rabbitmq_exchanges" {
  description = "The exchanges configured in the RabbitMQ cluster in staging"
  value       = module.messaging.rabbitmq_exchanges
}

output "rabbitmq_queues" {
  description = "The queues configured in the RabbitMQ cluster in staging"
  value       = module.messaging.rabbitmq_queues
}

# -----------------------------------------------
# Redis Cache Outputs
# -----------------------------------------------

# Application data cache (15-minute TTL)
output "redis_cache_endpoint" {
  description = "Redis cache cluster configuration endpoint address for application data caching in staging (15-minute TTL)"
  value       = module.cache.redis_cache_endpoint
}

output "redis_cache_primary_endpoint" {
  description = "Redis cache cluster primary endpoint address in staging (for non-clustered clients)"
  value       = module.cache.redis_cache_primary_endpoint
}

output "redis_cache_reader_endpoint" {
  description = "Redis cache cluster reader endpoint address for read operations in staging"
  value       = module.cache.redis_cache_reader_endpoint
}

# Session management cache (24-hour TTL)
output "redis_session_endpoint" {
  description = "Redis session cluster configuration endpoint address for session management in staging (24-hour TTL)"
  value       = module.cache.redis_session_endpoint
}

output "redis_session_primary_endpoint" {
  description = "Redis session cluster primary endpoint address in staging (for non-clustered clients)"
  value       = module.cache.redis_session_primary_endpoint
}

output "redis_session_reader_endpoint" {
  description = "Redis session cluster reader endpoint address for read operations in staging"
  value       = module.cache.redis_session_reader_endpoint
}

output "redis_port" {
  description = "Port number for Redis connections in staging"
  value       = module.cache.redis_port
}

# Connection strings for ioredis 5.3.2
output "redis_cache_connection_string" {
  description = "Connection string template for Redis cache cluster in staging using ioredis 5.3.2"
  value       = module.cache.redis_cache_connection_string
  sensitive   = true
}

output "redis_session_connection_string" {
  description = "Connection string template for Redis session cluster in staging using ioredis 5.3.2"
  value       = module.cache.redis_session_connection_string
  sensitive   = true
}

# ioredis 5.3.2 client configuration templates
output "redis_cache_ioredis_config" {
  description = "Configuration template for Redis cache cluster in staging using ioredis 5.3.2"
  value       = module.cache.redis_cache_ioredis_config
  sensitive   = true
}

output "redis_session_ioredis_config" {
  description = "Configuration template for Redis session cluster in staging using ioredis 5.3.2"
  value       = module.cache.redis_session_ioredis_config
  sensitive   = true
}

# Service integration details
output "redis_cache_service_integration" {
  description = "Integration details for connecting services to Redis cache cluster in staging"
  value       = module.cache.redis_cache_service_integration
  sensitive   = true
}

output "redis_session_service_integration" {
  description = "Integration details for connecting services to Redis session cluster in staging"
  value       = module.cache.redis_session_service_integration
  sensitive   = true
}

# -----------------------------------------------
# S3 Storage Outputs
# -----------------------------------------------

output "document_bucket_name" {
  description = "Name of the staging document storage bucket"
  value       = module.storage.staging_bucket_name
}

output "document_bucket_arn" {
  description = "ARN of the staging document storage bucket"
  value       = module.storage.staging_bucket_arn
}

output "document_bucket_domain_name" {
  description = "Domain name of the staging document storage bucket"
  value       = module.storage.staging_bucket_domain_name
}

output "document_bucket_regional_domain_name" {
  description = "Regional domain name of the staging document storage bucket"
  value       = module.storage.staging_bucket_regional_domain_name
}

output "document_bucket_region" {
  description = "Region of the staging document storage bucket"
  value       = module.storage.staging_bucket_region
}

output "document_bucket_url_prefix" {
  description = "URL prefix for staging bucket objects (without protocol)"
  value       = module.storage.staging_bucket_url_prefix
}

# Replica bucket information (if enabled)
output "document_replica_bucket_name" {
  description = "Name of the staging replica document storage bucket (if replication is enabled)"
  value       = module.storage.staging_replica_bucket_name
}

output "document_replica_bucket_arn" {
  description = "ARN of the staging replica document storage bucket (if replication is enabled)"
  value       = module.storage.staging_replica_bucket_arn
}

output "document_replica_bucket_domain_name" {
  description = "Domain name of the staging replica document storage bucket (if replication is enabled)"
  value       = module.storage.staging_replica_bucket_domain_name
}

output "document_replica_bucket_region" {
  description = "Region of the staging replica document storage bucket (if replication is enabled)"
  value       = module.storage.staging_replica_bucket_region
}

output "document_replica_bucket_url_prefix" {
  description = "URL prefix for staging replica bucket objects (without protocol) (if replication is enabled)"
  value       = module.storage.staging_replica_bucket_url_prefix
}

# Storage configuration information
output "storage_encryption_algorithm" {
  description = "Server-side encryption algorithm used for buckets in staging"
  value       = module.storage.encryption_algorithm
}

output "storage_versioning_enabled" {
  description = "Whether versioning is enabled for the buckets in staging"
  value       = module.storage.versioning_enabled
}

output "storage_replication_enabled" {
  description = "Whether cross-region replication is enabled in staging"
  value       = module.storage.replication_enabled
}

output "storage_signed_url_expiration" {
  description = "Default expiration time in seconds for signed URLs in staging"
  value       = module.storage.signed_url_expiration
}

# -----------------------------------------------
# Consolidated Service Connection Information
# -----------------------------------------------

# This output provides a consolidated view of all connection information needed by services
output "service_connection_info" {
  description = "Consolidated connection information for all services in the staging environment"
  value = {
    environment = "staging"
    
    database = {
      primary_endpoint = module.database.primary_endpoint
      replica_endpoints = module.database.replica_endpoints
      pooling_endpoint = module.database.pgbouncer_endpoints[0]
      pooling_port = module.database.pgbouncer_port
      database_name = module.database.database_name
      java_connection_string = module.database.spring_datasource_url
      node_connection_string = "Use node_connection_string (sensitive)"
      python_connection_string = "Use python_connection_string (sensitive)"
    }
    
    messaging = {
      host = module.messaging.rabbitmq_host
      port = module.messaging.rabbitmq_port
      ssl_port = module.messaging.rabbitmq_ssl_port
      management_endpoint = module.messaging.rabbitmq_management_endpoint
      exchanges = module.messaging.rabbitmq_exchanges
      queues = module.messaging.rabbitmq_queues
    }
    
    cache = {
      application_data = {
        endpoint = module.cache.redis_cache_endpoint
        primary_endpoint = module.cache.redis_cache_primary_endpoint
        reader_endpoint = module.cache.redis_cache_reader_endpoint
        port = module.cache.redis_port
        ttl_seconds = 900  # 15 minutes
      }
      session = {
        endpoint = module.cache.redis_session_endpoint
        primary_endpoint = module.cache.redis_session_primary_endpoint
        reader_endpoint = module.cache.redis_session_reader_endpoint
        port = module.cache.redis_port
        ttl_seconds = 86400  # 24 hours
      }
    }
    
    storage = {
      bucket_name = module.storage.staging_bucket_name
      bucket_domain_name = module.storage.staging_bucket_domain_name
      bucket_regional_domain_name = module.storage.staging_bucket_regional_domain_name
      bucket_url_prefix = module.storage.staging_bucket_url_prefix
      encryption_algorithm = module.storage.encryption_algorithm
      versioning_enabled = module.storage.versioning_enabled
      signed_url_expiration = module.storage.signed_url_expiration
    }
  }
}

# -----------------------------------------------
# Microservice-Specific Connection Information
# -----------------------------------------------

# Email Service connection information
output "email_service_connection_info" {
  description = "Connection information for the Email Service in staging"
  value = {
    database = {
      connection_string = "Use node_connection_string (sensitive)"
    }
    messaging = {
      host = module.messaging.rabbitmq_host
      port = module.messaging.rabbitmq_port
      ssl_port = module.messaging.rabbitmq_ssl_port
      vhost = module.messaging.rabbitmq_service_connection_params.email_service.vhost
      exchange = module.messaging.rabbitmq_service_connection_params.email_service.exchange
    }
    storage = {
      bucket_name = module.storage.staging_bucket_name
      bucket_url_prefix = module.storage.staging_bucket_url_prefix
    }
  }
}

# Document Service connection information
output "document_service_connection_info" {
  description = "Connection information for the Document Service in staging"
  value = {
    database = {
      connection_string = "Use python_connection_string (sensitive)"
    }
    messaging = {
      host = module.messaging.rabbitmq_host
      port = module.messaging.rabbitmq_port
      ssl_port = module.messaging.rabbitmq_ssl_port
      vhost = module.messaging.rabbitmq_service_connection_params.document_service.vhost
      queue = module.messaging.rabbitmq_service_connection_params.document_service.queue
      routing_key = module.messaging.rabbitmq_service_connection_params.document_service.routing_key
    }
    storage = {
      bucket_name = module.storage.staging_bucket_name
      bucket_url_prefix = module.storage.staging_bucket_url_prefix
    }
    cache = {
      endpoint = module.cache.redis_cache_endpoint
      port = module.cache.redis_port
    }
  }
}

# OCR Service connection information
output "ocr_service_connection_info" {
  description = "Connection information for the OCR Service in staging"
  value = {
    database = {
      connection_string = "Use python_connection_string (sensitive)"
    }
    messaging = {
      host = module.messaging.rabbitmq_host
      port = module.messaging.rabbitmq_port
      ssl_port = module.messaging.rabbitmq_ssl_port
      vhost = module.messaging.rabbitmq_service_connection_params.ocr_service.vhost
      queue = module.messaging.rabbitmq_service_connection_params.ocr_service.queue
      routing_key = module.messaging.rabbitmq_service_connection_params.ocr_service.routing_key
    }
    storage = {
      bucket_name = module.storage.staging_bucket_name
      bucket_url_prefix = module.storage.staging_bucket_url_prefix
    }
    cache = {
      endpoint = module.cache.redis_cache_endpoint
      port = module.cache.redis_port
    }
  }
}

# Data Service connection information
output "data_service_connection_info" {
  description = "Connection information for the Data Service in staging"
  value = {
    database = {
      primary_endpoint = module.database.primary_endpoint
      replica_endpoints = module.database.replica_endpoints
      pooling_endpoint = module.database.pgbouncer_endpoints[0]
      pooling_port = module.database.pgbouncer_port
      database_name = module.database.database_name
      connection_string = module.database.spring_datasource_url
    }
    messaging = {
      host = module.messaging.rabbitmq_host
      port = module.messaging.rabbitmq_port
      ssl_port = module.messaging.rabbitmq_ssl_port
      vhost = module.messaging.rabbitmq_service_connection_params.data_service.vhost
      exchange = module.messaging.rabbitmq_service_connection_params.data_service.exchange
    }
    storage = {
      bucket_name = module.storage.staging_bucket_name
      bucket_url_prefix = module.storage.staging_bucket_url_prefix
    }
    cache = {
      application_data = {
        endpoint = module.cache.redis_cache_endpoint
        port = module.cache.redis_port
      }
      session = {
        endpoint = module.cache.redis_session_endpoint
        port = module.cache.redis_port
      }
    }
  }
}

# Notification Service connection information
output "notification_service_connection_info" {
  description = "Connection information for the Notification Service in staging"
  value = {
    database = {
      connection_string = "Use node_connection_string (sensitive)"
    }
    messaging = {
      host = module.messaging.rabbitmq_host
      port = module.messaging.rabbitmq_port
      ssl_port = module.messaging.rabbitmq_ssl_port
      vhost = module.messaging.rabbitmq_service_connection_params.notification_service.vhost
      queue = module.messaging.rabbitmq_service_connection_params.notification_service.queue
      routing_key = module.messaging.rabbitmq_service_connection_params.notification_service.routing_key
    }
    cache = {
      endpoint = module.cache.redis_cache_endpoint
      port = module.cache.redis_port
    }
  }
}

# Frontend connection information
output "frontend_connection_info" {
  description = "Connection information for the Frontend in staging"
  value = {
    api_gateway = {
      endpoint = "https://api-staging.dollarfunding.com"
      version = "v1"
    }
    storage = {
      document_bucket_url_prefix = module.storage.staging_bucket_url_prefix
    }
  }
}