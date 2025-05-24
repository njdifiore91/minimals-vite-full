# RabbitMQ Queues, Exchanges, and Bindings for MCA Application Processing System
#
# This file defines and configures the RabbitMQ exchanges, queues, and bindings required
# by the MCA application processing system. It implements the specific message routing
# topology needed for document processing, data extraction, and notification delivery.
#
# Key components:
# - 'mca.documents' fanout exchange for document distribution
# - 'document-processing' queue for document classification
# - 'data-extraction' queue for OCR processing
# - 'notification' queue for status updates and alerts
# - Bindings between exchanges and queues with appropriate routing keys

# Local variables for queue configuration
locals {
  # Default queue settings based on environment
  default_queue_settings = {
    development = {
      max_length = 10000
      ttl        = 86400000  # 24 hours in milliseconds
    }
    staging = {
      max_length = 50000
      ttl        = 86400000  # 24 hours in milliseconds
    }
    production = {
      max_length = 100000
      ttl        = 86400000  # 24 hours in milliseconds
    }
  }

  # Determine if we should use quorum queues based on environment
  use_quorum_queues = var.environment != "development"

  # Queue arguments based on environment and queue type
  queue_arguments = {
    document-processing = merge(
      {
        # Common arguments for all environments
        "x-queue-mode" = "lazy"
        "x-max-length" = lookup(local.default_queue_settings, var.environment, local.default_queue_settings.development).max_length
        "x-message-ttl" = lookup(local.default_queue_settings, var.environment, local.default_queue_settings.development).ttl
      },
      # Add quorum queue settings if applicable
      local.use_quorum_queues ? {
        "x-queue-type" = "quorum"
        "x-quorum-initial-group-size" = min(var.cluster_size, 5)
      } : {}
    )
    data-extraction = merge(
      {
        # Common arguments for all environments
        "x-queue-mode" = "lazy"
        "x-max-length" = lookup(local.default_queue_settings, var.environment, local.default_queue_settings.development).max_length
        "x-message-ttl" = lookup(local.default_queue_settings, var.environment, local.default_queue_settings.development).ttl
      },
      # Add quorum queue settings if applicable
      local.use_quorum_queues ? {
        "x-queue-type" = "quorum"
        "x-quorum-initial-group-size" = min(var.cluster_size, 5)
      } : {}
    )
    notification = merge(
      {
        # Common arguments for all environments
        "x-queue-mode" = "lazy"
        "x-max-length" = lookup(local.default_queue_settings, var.environment, local.default_queue_settings.development).max_length
        "x-message-ttl" = lookup(local.default_queue_settings, var.environment, local.default_queue_settings.development).ttl
      },
      # Add quorum queue settings if applicable
      local.use_quorum_queues ? {
        "x-queue-type" = "quorum"
        "x-quorum-initial-group-size" = min(var.cluster_size, 5)
      } : {}
    )
  }
}

# Create the 'mca.documents' fanout exchange for document distribution
resource "rabbitmq_exchange" "mca_documents" {
  count  = var.create_default_resources ? 1 : 0
  name   = "mca.documents"
  vhost  = "/"
  
  settings {
    type        = "fanout"
    durable     = true
    auto_delete = false
  }

  # Depends on the RabbitMQ cluster being available
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create the 'document-processing' queue for document classification
resource "rabbitmq_queue" "document_processing" {
  count = var.create_default_resources ? 1 : 0
  name  = "document-processing"
  vhost = "/"
  
  settings {
    durable     = true
    auto_delete = false
    arguments   = local.queue_arguments.document-processing
  }

  # Depends on the RabbitMQ cluster being available
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create the 'data-extraction' queue for OCR processing
resource "rabbitmq_queue" "data_extraction" {
  count = var.create_default_resources ? 1 : 0
  name  = "data-extraction"
  vhost = "/"
  
  settings {
    durable     = true
    auto_delete = false
    arguments   = local.queue_arguments.data-extraction
  }

  # Depends on the RabbitMQ cluster being available
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create the 'notification' queue for status updates and alerts
resource "rabbitmq_queue" "notification" {
  count = var.create_default_resources ? 1 : 0
  name  = "notification"
  vhost = "/"
  
  settings {
    durable     = true
    auto_delete = false
    arguments   = local.queue_arguments.notification
  }

  # Depends on the RabbitMQ cluster being available
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create binding between 'mca.documents' exchange and 'document-processing' queue
resource "rabbitmq_binding" "documents_to_processing" {
  count            = var.create_default_resources ? 1 : 0
  source           = rabbitmq_exchange.mca_documents[0].name
  vhost            = "/"
  destination      = rabbitmq_queue.document_processing[0].name
  destination_type = "queue"
  routing_key      = "#"  # Fanout exchange will send to all queues regardless of routing key
  
  # Depends on both the exchange and queue being created
  depends_on = [
    rabbitmq_exchange.mca_documents,
    rabbitmq_queue.document_processing
  ]
}

# Create binding between 'mca.documents' exchange and 'data-extraction' queue
resource "rabbitmq_binding" "documents_to_extraction" {
  count            = var.create_default_resources ? 1 : 0
  source           = rabbitmq_exchange.mca_documents[0].name
  vhost            = "/"
  destination      = rabbitmq_queue.data_extraction[0].name
  destination_type = "queue"
  routing_key      = "#"  # Fanout exchange will send to all queues regardless of routing key
  
  # Depends on both the exchange and queue being created
  depends_on = [
    rabbitmq_exchange.mca_documents,
    rabbitmq_queue.data_extraction
  ]
}

# Create binding between 'mca.documents' exchange and 'notification' queue
resource "rabbitmq_binding" "documents_to_notification" {
  count            = var.create_default_resources ? 1 : 0
  source           = rabbitmq_exchange.mca_documents[0].name
  vhost            = "/"
  destination      = rabbitmq_queue.notification[0].name
  destination_type = "queue"
  routing_key      = "#"  # Fanout exchange will send to all queues regardless of routing key
  
  # Depends on both the exchange and queue being created
  depends_on = [
    rabbitmq_exchange.mca_documents,
    rabbitmq_queue.notification
  ]
}

# Create a direct exchange for routing messages to specific queues based on routing keys
resource "rabbitmq_exchange" "mca_direct" {
  count  = var.create_default_resources ? 1 : 0
  name   = "mca.direct"
  vhost  = "/"
  
  settings {
    type        = "direct"
    durable     = true
    auto_delete = false
  }

  # Depends on the RabbitMQ cluster being available
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create bindings for direct exchange to route messages based on document type and processing stage
resource "rabbitmq_binding" "direct_to_document_processing" {
  count            = var.create_default_resources ? 1 : 0
  source           = rabbitmq_exchange.mca_direct[0].name
  vhost            = "/"
  destination      = rabbitmq_queue.document_processing[0].name
  destination_type = "queue"
  routing_key      = "document.classification"
  
  # Depends on both the exchange and queue being created
  depends_on = [
    rabbitmq_exchange.mca_direct,
    rabbitmq_queue.document_processing
  ]
}

resource "rabbitmq_binding" "direct_to_data_extraction" {
  count            = var.create_default_resources ? 1 : 0
  source           = rabbitmq_exchange.mca_direct[0].name
  vhost            = "/"
  destination      = rabbitmq_queue.data_extraction[0].name
  destination_type = "queue"
  routing_key      = "document.extraction"
  
  # Depends on both the exchange and queue being created
  depends_on = [
    rabbitmq_exchange.mca_direct,
    rabbitmq_queue.data_extraction
  ]
}

resource "rabbitmq_binding" "direct_to_notification" {
  count            = var.create_default_resources ? 1 : 0
  source           = rabbitmq_exchange.mca_direct[0].name
  vhost            = "/"
  destination      = rabbitmq_queue.notification[0].name
  destination_type = "queue"
  routing_key      = "document.notification"
  
  # Depends on both the exchange and queue being created
  depends_on = [
    rabbitmq_exchange.mca_direct,
    rabbitmq_queue.notification
  ]
}

# Create a topic exchange for more complex routing patterns
resource "rabbitmq_exchange" "mca_topic" {
  count  = var.create_default_resources ? 1 : 0
  name   = "mca.topic"
  vhost  = "/"
  
  settings {
    type        = "topic"
    durable     = true
    auto_delete = false
  }

  # Depends on the RabbitMQ cluster being available
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create bindings for topic exchange with pattern matching for document types
resource "rabbitmq_binding" "topic_to_document_processing" {
  count            = var.create_default_resources ? 1 : 0
  source           = rabbitmq_exchange.mca_topic[0].name
  vhost            = "/"
  destination      = rabbitmq_queue.document_processing[0].name
  destination_type = "queue"
  routing_key      = "document.*.classify"
  
  # Depends on both the exchange and queue being created
  depends_on = [
    rabbitmq_exchange.mca_topic,
    rabbitmq_queue.document_processing
  ]
}

resource "rabbitmq_binding" "topic_to_data_extraction" {
  count            = var.create_default_resources ? 1 : 0
  source           = rabbitmq_exchange.mca_topic[0].name
  vhost            = "/"
  destination      = rabbitmq_queue.data_extraction[0].name
  destination_type = "queue"
  routing_key      = "document.*.extract"
  
  # Depends on both the exchange and queue being created
  depends_on = [
    rabbitmq_exchange.mca_topic,
    rabbitmq_queue.data_extraction
  ]
}

resource "rabbitmq_binding" "topic_to_notification" {
  count            = var.create_default_resources ? 1 : 0
  source           = rabbitmq_exchange.mca_topic[0].name
  vhost            = "/"
  destination      = rabbitmq_queue.notification[0].name
  destination_type = "queue"
  routing_key      = "document.*.notify"
  
  # Depends on both the exchange and queue being created
  depends_on = [
    rabbitmq_exchange.mca_topic,
    rabbitmq_queue.notification
  ]
}

# Create dead letter exchange for handling failed messages
resource "rabbitmq_exchange" "mca_dead_letter" {
  count  = var.create_default_resources ? 1 : 0
  name   = "mca.dead-letter"
  vhost  = "/"
  
  settings {
    type        = "direct"
    durable     = true
    auto_delete = false
  }

  # Depends on the RabbitMQ cluster being available
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create dead letter queue for failed messages
resource "rabbitmq_queue" "dead_letter" {
  count = var.create_default_resources ? 1 : 0
  name  = "dead-letter"
  vhost = "/"
  
  settings {
    durable     = true
    auto_delete = false
    arguments   = {
      "x-queue-mode" = "lazy"
      "x-max-length" = 100000
      "x-message-ttl" = 604800000  # 7 days in milliseconds
    }
  }

  # Depends on the RabbitMQ cluster being available
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create binding for dead letter exchange
resource "rabbitmq_binding" "dead_letter_binding" {
  count            = var.create_default_resources ? 1 : 0
  source           = rabbitmq_exchange.mca_dead_letter[0].name
  vhost            = "/"
  destination      = rabbitmq_queue.dead_letter[0].name
  destination_type = "queue"
  routing_key      = "#"
  
  # Depends on both the exchange and queue being created
  depends_on = [
    rabbitmq_exchange.mca_dead_letter,
    rabbitmq_queue.dead_letter
  ]
}

# Create policy for message TTL and dead letter routing
resource "rabbitmq_policy" "message_ttl_and_dead_letter" {
  count  = var.create_default_resources ? 1 : 0
  name   = "message-ttl-and-dead-letter"
  vhost  = "/"
  pattern = "^(document-processing|data-extraction|notification)$"
  
  policy {
    priority = 1
    apply_to = "queues"
    
    definition = {
      # Set message TTL based on environment
      "message-ttl" = lookup(local.default_queue_settings, var.environment, local.default_queue_settings.development).ttl
      
      # Configure dead letter exchange for failed messages
      "dead-letter-exchange" = rabbitmq_exchange.mca_dead_letter[0].name
      
      # Set queue mode to lazy for better performance with large messages
      "queue-mode" = "lazy"
      
      # Configure queue length limit based on environment
      "max-length" = lookup(local.default_queue_settings, var.environment, local.default_queue_settings.development).max_length
      
      # Configure overflow behavior
      "overflow" = "reject-publish"
    }
  }
  
  # Depends on the dead letter exchange being created
  depends_on = [rabbitmq_exchange.mca_dead_letter]
}

# Create policy for high availability (mirroring) if enabled and not using quorum queues
resource "rabbitmq_policy" "ha_policy" {
  count  = var.create_default_resources && var.enable_mirrored_queues && !local.use_quorum_queues ? 1 : 0
  name   = "ha-policy"
  vhost  = "/"
  pattern = ".*"
  
  policy {
    priority = 2
    apply_to = "queues"
    
    definition = {
      # Mirror queues to all nodes in the cluster
      "ha-mode" = "all"
      
      # Synchronize queue contents when a node joins
      "ha-sync-mode" = "automatic"
      
      # Set batch size for synchronization
      "ha-sync-batch-size" = var.mirror_sync_batch_size
    }
  }
  
  # Depends on the RabbitMQ cluster being available
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create policy for quorum queues if enabled
resource "rabbitmq_policy" "quorum_queue_policy" {
  count  = var.create_default_resources && local.use_quorum_queues ? 1 : 0
  name   = "quorum-queue-policy"
  vhost  = "/"
  pattern = "^(document-processing|data-extraction|notification)$"
  
  policy {
    priority = 3
    apply_to = "queues"
    
    definition = {
      # Set queue type to quorum
      "queue-type" = "quorum"
      
      # Configure initial group size based on cluster size
      "x-quorum-initial-group-size" = min(var.cluster_size, 5)
      
      # Configure delivery limit before sending to dead letter exchange
      "delivery-limit" = 10
    }
  }
  
  # Depends on the RabbitMQ cluster being available
  depends_on = [aws_mq_broker.rabbitmq_cluster]
}

# Create custom RabbitMQ configuration for the MCA application
resource "null_resource" "rabbitmq_definitions" {
  count = var.create_default_resources ? 1 : 0
  
  # This would typically be used to create a definitions.json file
  # that would be loaded by RabbitMQ on startup
  
  # For AWS MQ, this would be handled differently, potentially through
  # the AWS MQ configuration resource in main.tf
  
  # This is a placeholder for custom configuration that might be needed
  # in a self-managed RabbitMQ deployment
  
  triggers = {
    # Trigger recreation if any of these resources change
    cluster_id = aws_mq_broker.rabbitmq_cluster.id
    exchanges  = join(",", [for ex in rabbitmq_exchange.mca_documents : ex.id])
    queues     = join(",", [for q in rabbitmq_queue.document_processing : q.id])
  }
  
  # Depends on all resources being created
  depends_on = [
    rabbitmq_exchange.mca_documents,
    rabbitmq_exchange.mca_direct,
    rabbitmq_exchange.mca_topic,
    rabbitmq_exchange.mca_dead_letter,
    rabbitmq_queue.document_processing,
    rabbitmq_queue.data_extraction,
    rabbitmq_queue.notification,
    rabbitmq_queue.dead_letter,
    rabbitmq_binding.documents_to_processing,
    rabbitmq_binding.documents_to_extraction,
    rabbitmq_binding.documents_to_notification,
    rabbitmq_binding.direct_to_document_processing,
    rabbitmq_binding.direct_to_data_extraction,
    rabbitmq_binding.direct_to_notification,
    rabbitmq_binding.topic_to_document_processing,
    rabbitmq_binding.topic_to_data_extraction,
    rabbitmq_binding.topic_to_notification,
    rabbitmq_binding.dead_letter_binding,
    rabbitmq_policy.message_ttl_and_dead_letter
  ]
}