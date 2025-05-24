# RabbitMQ Messaging Module Outputs
#
# This file exports essential RabbitMQ information as module outputs, including connection endpoints,
# port numbers, virtual hosts, and resource identifiers. These outputs are consumed by other Terraform
# modules and application configuration.
#
# Key output categories:
# 1. Connection information for microservices integration
# 2. Management interface access for administration
# 3. Integration with monitoring and logging systems
# 4. Support for amqplib 0.10.3 client library
# 5. Secure connection string handling

# -----------------------------------------------------------------------------
# Connection Information
# -----------------------------------------------------------------------------

output "rabbitmq_endpoints" {
  description = "The AMQP endpoints of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.instances.*.endpoints
}

output "rabbitmq_ssl_endpoints" {
  description = "The AMQPS (SSL) endpoints of the RabbitMQ cluster"
  value = [for instance in aws_mq_broker.rabbitmq_cluster.instances : {
    host = split(":", instance.endpoints[0])[1]
    port = 5671
  }]
}

output "rabbitmq_host" {
  description = "The primary host of the RabbitMQ cluster"
  value       = split(":", aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0])[1]
}

output "rabbitmq_port" {
  description = "The AMQP port of the RabbitMQ cluster"
  value       = 5672
}

output "rabbitmq_ssl_port" {
  description = "The AMQPS (SSL) port of the RabbitMQ cluster"
  value       = 5671
}

output "rabbitmq_vhosts" {
  description = "The virtual hosts configured in the RabbitMQ cluster"
  value = {
    default            = "/"
    document_processing = "document-processing"
    data_extraction    = "data-extraction"
    notification       = "notification"
  }
}

# -----------------------------------------------------------------------------
# Management Interface
# -----------------------------------------------------------------------------

output "rabbitmq_management_endpoint" {
  description = "The management UI endpoint of the RabbitMQ cluster"
  value       = "https://${aws_mq_broker.rabbitmq_cluster.instances[0].console_url}"
}

output "rabbitmq_management_port" {
  description = "The management UI port of the RabbitMQ cluster"
  value       = 15671
}

output "rabbitmq_admin_secret_arn" {
  description = "The ARN of the secret containing RabbitMQ admin credentials"
  value       = aws_secretsmanager_secret.rabbitmq_admin.arn
}

# -----------------------------------------------------------------------------
# Resource Identifiers
# -----------------------------------------------------------------------------

output "rabbitmq_id" {
  description = "The ID of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.id
}

output "rabbitmq_arn" {
  description = "The ARN of the RabbitMQ cluster"
  value       = aws_mq_broker.rabbitmq_cluster.arn
}

output "rabbitmq_security_group_id" {
  description = "The ID of the security group for the RabbitMQ cluster"
  value       = aws_security_group.rabbitmq_cluster.id
}

output "rabbitmq_kms_key_arn" {
  description = "The ARN of the KMS key used for RabbitMQ encryption"
  value       = aws_kms_key.rabbitmq_encryption.arn
}

output "rabbitmq_certificates_bucket" {
  description = "The name of the S3 bucket containing RabbitMQ certificates"
  value       = aws_s3_bucket.rabbitmq_certificates.id
}

# -----------------------------------------------------------------------------
# Connection Strings
# -----------------------------------------------------------------------------

output "rabbitmq_connection_string" {
  description = "The connection string for RabbitMQ (without credentials)"
  value       = "amqp://${aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0]}"
}

output "rabbitmq_ssl_connection_string" {
  description = "The SSL connection string for RabbitMQ (without credentials)"
  value       = "amqps://${aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0]}"
}

output "rabbitmq_connection_string_template" {
  description = "Template for RabbitMQ connection string (replace USERNAME and PASSWORD)"
  value       = "amqp://USERNAME:PASSWORD@${split(":", aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0])[1]}:5672"
}

output "rabbitmq_ssl_connection_string_template" {
  description = "Template for RabbitMQ SSL connection string (replace USERNAME and PASSWORD)"
  value       = "amqps://USERNAME:PASSWORD@${split(":", aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0])[1]}:5671"
}

# -----------------------------------------------------------------------------
# Service-Specific Connection Options
# -----------------------------------------------------------------------------

output "rabbitmq_amqplib_options" {
  description = "Connection options for amqplib 0.10.3 client library"
  value = {
    protocol    = var.enable_tls ? "amqps" : "amqp"
    hostname    = split(":", aws_mq_broker.rabbitmq_cluster.instances[0].endpoints[0])[1]
    port        = var.enable_tls ? 5671 : 5672
    vhost       = "/"
    heartbeat   = 60
    frameMax    = 0
    channelMax  = 2048
    ssl         = var.enable_tls
    sslOptions  = var.enable_tls ? {
      ca          = "${aws_s3_bucket.rabbitmq_certificates.bucket_regional_domain_name}/certs/ca_certificate.pem"
      cert        = "${aws_s3_bucket.rabbitmq_certificates.bucket_regional_domain_name}/certs/client_certificate.pem"
      key         = "${aws_s3_bucket.rabbitmq_certificates.bucket_regional_domain_name}/certs/client_key.pem"
      passphrase  = ""
      rejectUnauthorized = true
    } : null
  }
}

output "rabbitmq_service_connection_params" {
  description = "Service-specific connection parameters for RabbitMQ"
  value = {
    email_service = {
      vhost       = "/"
      exchange    = "mca.documents"
      queue       = null
      routing_key = null
    }
    document_service = {
      vhost       = "document-processing"
      exchange    = null
      queue       = "document-processing"
      routing_key = "document.classification"
    }
    ocr_service = {
      vhost       = "data-extraction"
      exchange    = null
      queue       = "data-extraction"
      routing_key = "document.extraction"
    }
    data_service = {
      vhost       = "/"
      exchange    = "mca.direct"
      queue       = null
      routing_key = null
    }
    notification_service = {
      vhost       = "notification"
      exchange    = null
      queue       = "notification"
      routing_key = "document.notification"
    }
  }
}

# -----------------------------------------------------------------------------
# Monitoring and Logging
# -----------------------------------------------------------------------------

output "rabbitmq_cloudwatch_log_group" {
  description = "The CloudWatch log group for RabbitMQ logs"
  value       = aws_cloudwatch_log_group.rabbitmq_logs.name
}

output "rabbitmq_cloudwatch_log_group_arn" {
  description = "The ARN of the CloudWatch log group for RabbitMQ logs"
  value       = aws_cloudwatch_log_group.rabbitmq_logs.arn
}

output "rabbitmq_cloudwatch_dashboard" {
  description = "The CloudWatch dashboard for RabbitMQ monitoring"
  value       = var.enable_monitoring && var.enable_dashboard ? aws_cloudwatch_dashboard.rabbitmq[0].dashboard_name : null
}

output "rabbitmq_cloudwatch_alarms" {
  description = "The CloudWatch alarms for RabbitMQ monitoring"
  value = {
    cpu_utilization = var.enable_monitoring ? aws_cloudwatch_metric_alarm.rabbitmq_cpu_utilization.arn : null
    memory_usage    = var.enable_monitoring ? aws_cloudwatch_metric_alarm.rabbitmq_memory_usage.arn : null
    queue_depth     = var.enable_monitoring ? aws_cloudwatch_metric_alarm.rabbitmq_queue_depth.arn : null
  }
}

# -----------------------------------------------------------------------------
# Queue and Exchange Information
# -----------------------------------------------------------------------------

output "rabbitmq_exchanges" {
  description = "The exchanges configured in the RabbitMQ cluster"
  value = var.create_default_resources ? {
    documents   = rabbitmq_exchange.mca_documents[0].name
    direct      = rabbitmq_exchange.mca_direct[0].name
    topic       = rabbitmq_exchange.mca_topic[0].name
    dead_letter = rabbitmq_exchange.mca_dead_letter[0].name
  } : null
}

output "rabbitmq_queues" {
  description = "The queues configured in the RabbitMQ cluster"
  value = var.create_default_resources ? {
    document_processing = rabbitmq_queue.document_processing[0].name
    data_extraction     = rabbitmq_queue.data_extraction[0].name
    notification        = rabbitmq_queue.notification[0].name
    dead_letter         = rabbitmq_queue.dead_letter[0].name
  } : null
}

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------

output "rabbitmq_features" {
  description = "Feature flags for RabbitMQ configuration"
  value = {
    tls_enabled           = var.enable_tls
    monitoring_enabled    = var.enable_monitoring
    dashboard_enabled     = var.enable_dashboard && var.enable_monitoring
    mirrored_queues       = var.enable_mirrored_queues && !local.use_quorum_queues
    quorum_queues         = local.use_quorum_queues
    default_resources     = var.create_default_resources
    multi_az              = local.is_multi_az
    cluster_size          = local.actual_cluster_size
  }
}