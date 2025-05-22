# RabbitMQ Queues, Exchanges, and Bindings for MCA Application Processing System
#
# This file defines the messaging infrastructure for the Merchant Cash Advance (MCA)
# Application Processing System. It configures the RabbitMQ exchanges, queues, and bindings
# required for asynchronous communication between microservices.
#
# The messaging topology implements the following workflow:
# 1. Email Service monitors submissions inbox and publishes to mca.documents exchange
# 2. Document Service consumes from document-processing queue for classification
# 3. OCR Service processes documents and publishes to data-extraction queue
# 4. Data Service processes extracted data and publishes status updates
# 5. Notification Service delivers notifications via webhooks
#
# All queues are configured with:
# - Durability for message persistence across broker restarts
# - Dead letter exchange routing for failed messages
# - Message TTL to prevent queue overflow
# - Environment-specific tagging

# Main document exchange - fanout type to distribute documents to multiple processing queues
resource "rabbitmq_exchange" "mca_documents" {
  name       = "mca.documents"
  vhost      = var.rabbitmq_vhost
  type       = "fanout"
  durable    = true
  auto_delete = false

  # Apply environment-specific tags
  arguments = {
    "x-environment" = var.environment
    "x-owner"      = "mca-system"
  }
}

# Document processing exchange - topic type for routing based on document type
resource "rabbitmq_exchange" "document_processing" {
  name       = "document.processing"
  vhost      = var.rabbitmq_vhost
  type       = "topic"
  durable    = true
  auto_delete = false

  arguments = {
    "x-environment" = var.environment
    "x-owner"      = "mca-system"
  }
}

# Data processing exchange - topic type for routing based on data type
resource "rabbitmq_exchange" "data_processing" {
  name       = "data.processing"
  vhost      = var.rabbitmq_vhost
  type       = "topic"
  durable    = true
  auto_delete = false

  arguments = {
    "x-environment" = var.environment
    "x-owner"      = "mca-system"
  }
}

# Document processing queue - for document classification service
resource "rabbitmq_queue" "document_processing" {
  name       = "document-processing"
  vhost      = var.rabbitmq_vhost
  durable    = true
  auto_delete = false

  # Configure queue settings
  arguments = {
    # Set message TTL to 24 hours (in milliseconds)
    "x-message-ttl"          = 86400000
    # Enable dead letter exchange for unprocessed messages
    "x-dead-letter-exchange" = "mca.dead-letter"
    # Set max queue length to prevent memory issues
    "x-max-length"           = 100000
    # Apply environment tag
    "x-environment"          = var.environment
  }
}

# Data extraction queue - for OCR service
resource "rabbitmq_queue" "data_extraction" {
  name       = "data-extraction"
  vhost      = var.rabbitmq_vhost
  durable    = true
  auto_delete = false

  # Configure queue settings
  arguments = {
    # Set message TTL to 24 hours (in milliseconds)
    "x-message-ttl"          = 86400000
    # Enable dead letter exchange for unprocessed messages
    "x-dead-letter-exchange" = "mca.dead-letter"
    # Set max queue length to prevent memory issues
    "x-max-length"           = 100000
    # Apply environment tag
    "x-environment"          = var.environment
  }
}

# Notification queue - for notification service
resource "rabbitmq_queue" "notification" {
  name       = "notification"
  vhost      = var.rabbitmq_vhost
  durable    = true
  auto_delete = false

  # Configure queue settings
  arguments = {
    # Set message TTL to 24 hours (in milliseconds)
    "x-message-ttl"          = 86400000
    # Enable dead letter exchange for unprocessed messages
    "x-dead-letter-exchange" = "mca.dead-letter"
    # Set max queue length to prevent memory issues
    "x-max-length"           = 50000
    # Apply environment tag
    "x-environment"          = var.environment
  }
}

# Dead letter exchange for handling failed messages
resource "rabbitmq_exchange" "mca_dead_letter" {
  name       = "mca.dead-letter"
  vhost      = var.rabbitmq_vhost
  type       = "topic"
  durable    = true
  auto_delete = false

  arguments = {
    "x-environment" = var.environment
    "x-owner"      = "mca-system"
  }
}

# Dead letter queue for storing failed messages
resource "rabbitmq_queue" "dead_letter" {
  name       = "dead-letter"
  vhost      = var.rabbitmq_vhost
  durable    = true
  auto_delete = false

  arguments = {
    # Set message TTL to 7 days (in milliseconds) for investigation
    "x-message-ttl" = 604800000
    # Apply environment tag
    "x-environment" = var.environment
  }
}

# Bind dead letter queue to dead letter exchange
resource "rabbitmq_binding" "dead_letter_binding" {
  source           = rabbitmq_exchange.mca_dead_letter.name
  vhost            = var.rabbitmq_vhost
  destination      = rabbitmq_queue.dead_letter.name
  destination_type = "queue"
  routing_key      = "#"
}

# Bind document processing queue to mca.documents exchange
resource "rabbitmq_binding" "document_processing_binding" {
  source           = rabbitmq_exchange.mca_documents.name
  vhost            = var.rabbitmq_vhost
  destination      = rabbitmq_queue.document_processing.name
  destination_type = "queue"
  # For fanout exchanges, routing key is ignored but required by the provider
  routing_key      = "document.new"
}

# Bind data extraction queue to mca.documents exchange
resource "rabbitmq_binding" "data_extraction_binding" {
  source           = rabbitmq_exchange.mca_documents.name
  vhost            = var.rabbitmq_vhost
  destination      = rabbitmq_queue.data_extraction.name
  destination_type = "queue"
  # For fanout exchanges, routing key is ignored but required by the provider
  routing_key      = "document.processed"
}

# Bind notification queue to mca.documents exchange
resource "rabbitmq_binding" "notification_binding" {
  source           = rabbitmq_exchange.mca_documents.name
  vhost            = var.rabbitmq_vhost
  destination      = rabbitmq_queue.notification.name
  destination_type = "queue"
  # For fanout exchanges, routing key is ignored but required by the provider
  routing_key      = "notification.status"
}

# Bind document processing exchange to document processing queue
resource "rabbitmq_binding" "document_processing_exchange_binding" {
  source           = rabbitmq_exchange.document_processing.name
  vhost            = var.rabbitmq_vhost
  destination      = rabbitmq_queue.document_processing.name
  destination_type = "queue"
  routing_key      = "document.#"
}

# Bind data processing exchange to data extraction queue
resource "rabbitmq_binding" "data_processing_exchange_binding" {
  source           = rabbitmq_exchange.data_processing.name
  vhost            = var.rabbitmq_vhost
  destination      = rabbitmq_queue.data_extraction.name
  destination_type = "queue"
  routing_key      = "data.#"
}

# Create exchange-to-exchange binding for document flow
resource "rabbitmq_binding" "documents_to_document_processing" {
  source           = rabbitmq_exchange.mca_documents.name
  vhost            = var.rabbitmq_vhost
  destination      = rabbitmq_exchange.document_processing.name
  destination_type = "exchange"
  routing_key      = "document.new"
}

# Create exchange-to-exchange binding for data flow
resource "rabbitmq_binding" "documents_to_data_processing" {
  source           = rabbitmq_exchange.mca_documents.name
  vhost            = var.rabbitmq_vhost
  destination      = rabbitmq_exchange.data_processing.name
  destination_type = "exchange"
  routing_key      = "data.extracted"
}