"""RabbitMQ configuration for the OCR Service.

This module provides configuration for RabbitMQ connection, exchanges, queues,
and message handling for the OCR Service. It enables the service to consume
messages from the Document Service and publish extraction results to the Data Service.

Key features:
- TLS/SSL connection with client certificate authentication
- Fanout exchange 'mca.documents' for document processing
- Durable queues with dead-letter exchanges for error handling
- Connection recovery with exponential backoff
- JSON message serialization for consistent data format
- Prefetch count configuration for optimal throughput

As specified in the technical specification, this configuration implements:
- Asynchronous messaging between services with guaranteed delivery
- Dead letter exchanges for failed message handling
- Consumer configuration with prefetch counts
- Connection error handling and recovery strategies
"""

import os
import ssl
import json
import time
from pathlib import Path
from typing import Dict, Optional, Any, cast, Callable, List

from ..types.config import RabbitMQConfig, validate_config

# Default RabbitMQ configuration based on technical specification requirements
# See section 0.2.3 for exchange and queue names
# See section 3.2.3 for security requirements (TLS with client certificate auth)
DEFAULT_RABBITMQ_CONFIG: RabbitMQConfig = {
    # Connection parameters
    "host": os.environ.get("RABBITMQ_HOST", "localhost"),
    "port": int(os.environ.get("RABBITMQ_PORT", "5671")),  # Default to TLS port
    "username": os.environ.get("RABBITMQ_USERNAME", "guest"),
    "password": os.environ.get("RABBITMQ_PASSWORD", "guest"),
    "vhost": os.environ.get("RABBITMQ_VHOST", "/"),
    
    # Exchange and queue configuration as specified in section 0.2.3
    "exchange": os.environ.get("RABBITMQ_EXCHANGE", "mca.documents"),  # Fanout exchange
    "queue_data_extraction": os.environ.get("RABBITMQ_QUEUE_DATA_EXTRACTION", "data-extraction"),
    "queue_data_processing": os.environ.get("RABBITMQ_QUEUE_DATA_PROCESSING", "data-processing"),
    "routing_key": os.environ.get("RABBITMQ_ROUTING_KEY", "ocr.result"),
    
    # TLS/SSL configuration as required by section 3.2.3
    "ssl": os.environ.get("RABBITMQ_SSL", "True").lower() in ("true", "1", "t"),  # Default to enabled
    "ssl_cert_path": os.environ.get("RABBITMQ_SSL_CERT_PATH"),  # Client certificate
    "ssl_key_path": os.environ.get("RABBITMQ_SSL_KEY_PATH"),    # Client key
    "ssl_ca_certs": os.environ.get("RABBITMQ_SSL_CA_CERTS"),    # CA certificate
    
    # Connection tuning parameters
    "heartbeat": int(os.environ.get("RABBITMQ_HEARTBEAT", "60")),  # Heartbeat interval in seconds
    "connection_timeout": int(os.environ.get("RABBITMQ_CONNECTION_TIMEOUT", "30")),  # Connection timeout in seconds
    "prefetch_count": int(os.environ.get("RABBITMQ_PREFETCH_COUNT", "10")),  # Number of unacknowledged messages
}


def get_rabbitmq_config() -> RabbitMQConfig:
    """Get the RabbitMQ configuration with environment variable overrides.
    
    Loads the RabbitMQ configuration from environment variables with defaults,
    and validates the configuration to ensure it meets the requirements
    specified in the technical specification (section 3.2.3).
    
    Returns:
        RabbitMQ configuration dictionary with validated settings.
    
    Raises:
        ValueError: If the configuration is invalid, particularly if SSL is
                   enabled but certificate paths are not properly configured.
    """
    config = DEFAULT_RABBITMQ_CONFIG.copy()
    
    # Validate the configuration
    # This is a partial validation since we're only validating the RabbitMQ config
    # The full validation happens in app_config.py
    if config["ssl"] and not all([config["ssl_cert_path"], config["ssl_key_path"], config["ssl_ca_certs"]]):
        raise ValueError("SSL is enabled but certificate paths are not properly configured")
    
    return config


def get_rabbitmq_connection_parameters(config: RabbitMQConfig) -> Dict[str, Any]:
    """Get connection parameters for RabbitMQ.
    
    Configures the RabbitMQ connection with TLS/SSL and client certificate
    authentication as required by the technical specification (section 3.2.3).
    
    The SSL context is configured with:
    - Client certificate authentication
    - Certificate verification
    - Hostname verification
    
    Args:
        config: RabbitMQ configuration.
        
    Returns:
        Dictionary of connection parameters for pika, including SSL context
        if SSL is enabled.
    """
    params = {
        "host": config["host"],
        "port": config["port"],
        "virtual_host": config["vhost"],
        "credentials": {
            "username": config["username"],
            "password": config["password"],
        },
        "heartbeat": config["heartbeat"],
        "connection_timeout": config["connection_timeout"],
        "client_properties": {
            "connection_name": "ocr-service",
            "product": "MCA OCR Service",
        },
    }
    
    # Add SSL context if SSL is enabled
    if config["ssl"]:
        ssl_context = ssl.create_default_context(cafile=config["ssl_ca_certs"])
        ssl_context.load_cert_chain(
            certfile=cast(str, config["ssl_cert_path"]),
            keyfile=cast(str, config["ssl_key_path"]),
        )
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        
        params["ssl_options"] = {
            "context": ssl_context,
        }
    
    return params


def get_rabbitmq_exchange_config(config: RabbitMQConfig) -> Dict[str, Any]:
    """Get exchange configuration for RabbitMQ.
    
    Configures the 'mca.documents' fanout exchange as specified in the technical
    specification (section 0.2.3). This exchange is used for document processing
    messages between services.
    
    Args:
        config: RabbitMQ configuration.
        
    Returns:
        Dictionary of exchange configuration with the following keys:
        - exchange: Exchange name ('mca.documents')
        - exchange_type: Exchange type ('fanout')
        - durable: Whether the exchange survives broker restarts
        - auto_delete: Whether the exchange is deleted when no queues are bound
    """
    return {
        "exchange": config["exchange"],
        "exchange_type": "fanout",  # Using fanout as specified in the technical spec
        "durable": True,  # Survive broker restarts
        "auto_delete": False,  # Don't delete when no queues are bound
    }


def get_rabbitmq_queue_config(config: RabbitMQConfig) -> Dict[str, Any]:
    """Get queue configuration for RabbitMQ.
    
    Configures the OCR processing queues as specified in the technical
    specification (section 0.2.3). The OCR Service consumes from the
    'data-extraction' queue and publishes to the 'data-processing' queue.
    
    Both queues are configured with:
    - Durability to survive broker restarts
    - Dead-letter exchanges for failed message handling
    - Message TTL to prevent queue overflow
    
    Args:
        config: RabbitMQ configuration.
        
    Returns:
        Dictionary of queue configurations for 'data-extraction' and
        'data-processing' queues.
    """
    return {
        "data_extraction": {
            "queue": config["queue_data_extraction"],
            "durable": True,  # Survive broker restarts
            "exclusive": False,  # Allow multiple consumers
            "auto_delete": False,  # Don't delete when no consumers
            "arguments": {
                "x-dead-letter-exchange": f"{config['exchange']}.dlx",  # Dead letter exchange
                "x-message-ttl": 1000 * 60 * 60 * 24,  # 24 hours in milliseconds
            },
        },
        "data_processing": {
            "queue": config["queue_data_processing"],
            "durable": True,
            "exclusive": False,
            "auto_delete": False,
            "arguments": {
                "x-dead-letter-exchange": f"{config['exchange']}.dlx",
                "x-message-ttl": 1000 * 60 * 60 * 24,  # 24 hours in milliseconds
            },
        },
    }


def get_rabbitmq_consumer_config(config: RabbitMQConfig) -> Dict[str, Any]:
    """Get consumer configuration for RabbitMQ.
    
    Configures the RabbitMQ consumer with:
    - Prefetch count to limit the number of unacknowledged messages
    - Explicit acknowledgement requirement for reliable processing
    
    This ensures that the OCR Service processes messages from the
    'data-extraction' queue reliably and efficiently, as specified in
    the technical specification (section 4.1.8).
    
    Args:
        config: RabbitMQ configuration.
        
    Returns:
        Dictionary of consumer configuration for reliable message processing.
    """
    return {
        "prefetch_count": config["prefetch_count"],
        "no_ack": False,  # Require explicit acknowledgement
    }


def get_rabbitmq_publisher_config(config: RabbitMQConfig) -> Dict[str, Any]:
    """Get publisher configuration for RabbitMQ.
    
    Configures the RabbitMQ publisher with:
    - Mandatory flag to ensure messages are routed
    - Persistent delivery mode for message durability
    - JSON content type for consistent message serialization
    
    This ensures that messages from the OCR Service to the Data Service
    are delivered reliably and in a consistent format, as specified in the
    technical specification (section 4.1.8).
    
    Args:
        config: RabbitMQ configuration.
        
    Returns:
        Dictionary of publisher configuration for reliable message delivery.
    """
    return {
        "mandatory": True,  # Raise exception if message cannot be routed
        "properties": {
            "delivery_mode": 2,  # Persistent
            "content_type": "application/json",  # JSON serialization
        },
    }


def get_rabbitmq_retry_config() -> Dict[str, Any]:
    """Get retry configuration for RabbitMQ connection.
    
    This implements an exponential backoff strategy for connection retries,
    as specified in the technical specification. The retry mechanism helps
    ensure resilience against temporary RabbitMQ unavailability.
    
    Returns:
        Dictionary of retry configuration with the following keys:
        - max_retries: Maximum number of retry attempts
        - initial_delay: Initial delay between retries in seconds
        - max_delay: Maximum delay between retries in seconds
        - backoff_factor: Multiplicative factor for exponential backoff
    """
    return {
        "max_retries": int(os.environ.get("RABBITMQ_MAX_RETRIES", "5")),
        "initial_delay": float(os.environ.get("RABBITMQ_INITIAL_DELAY", "1.0")),  # seconds
        "max_delay": float(os.environ.get("RABBITMQ_MAX_DELAY", "30.0")),  # seconds
        "backoff_factor": float(os.environ.get("RABBITMQ_BACKOFF_FACTOR", "2.0")),
    }


def get_message_serializer() -> Callable[[Any], bytes]:
    """Get a message serializer function for RabbitMQ messages.
    
    Returns a function that serializes Python objects to JSON bytes for
    publishing to RabbitMQ. This ensures consistent message format across
    all services, as specified in the technical specification (section 4.1.8).
    
    Returns:
        A function that takes a Python object and returns JSON bytes.
    """
    def serialize_message(message: Any) -> bytes:
        """Serialize a message to JSON bytes.
        
        Args:
            message: The message to serialize.
            
        Returns:
            JSON bytes representation of the message.
        """
        return json.dumps(message, ensure_ascii=False, default=str).encode('utf-8')
    
    return serialize_message


def get_message_deserializer() -> Callable[[bytes], Any]:
    """Get a message deserializer function for RabbitMQ messages.
    
    Returns a function that deserializes JSON bytes from RabbitMQ to Python
    objects. This ensures consistent message parsing across all services,
    as specified in the technical specification (section 4.1.8).
    
    Returns:
        A function that takes JSON bytes and returns a Python object.
    """
    def deserialize_message(message_bytes: bytes) -> Any:
        """Deserialize JSON bytes to a Python object.
        
        Args:
            message_bytes: The JSON bytes to deserialize.
            
        Returns:
            Python object representation of the JSON bytes.
            
        Raises:
            json.JSONDecodeError: If the message is not valid JSON.
        """
        return json.loads(message_bytes.decode('utf-8'))
    
    return deserialize_message


def create_ocr_result_message(document_id: str, extracted_data: Dict[str, Any], 
                             confidence_scores: Dict[str, float], 
                             low_confidence_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Create a standardized OCR result message for publishing to RabbitMQ.
    
    This function creates a standardized message format for OCR results,
    including extracted data, confidence scores, and flags for low-confidence
    fields that may require human verification, as specified in the technical
    specification (section 4.1.8).
    
    Args:
        document_id: The ID of the processed document.
        extracted_data: The extracted data from the document.
        confidence_scores: Confidence scores for each extracted field.
        low_confidence_fields: List of fields with low confidence scores.
        
    Returns:
        A standardized message dictionary ready for serialization and publishing.
    """
    return {
        "document_id": document_id,
        "extracted_data": extracted_data,
        "confidence_scores": confidence_scores,
        "low_confidence_fields": low_confidence_fields or [],
        "requires_review": bool(low_confidence_fields),
        "processing_timestamp": int(time.time() * 1000),  # Milliseconds since epoch
    }


# Export the configuration functions
__all__ = [
    "get_rabbitmq_config",
    "get_rabbitmq_connection_parameters",
    "get_rabbitmq_exchange_config",
    "get_rabbitmq_queue_config",
    "get_rabbitmq_consumer_config",
    "get_rabbitmq_publisher_config",
    "get_rabbitmq_retry_config",
    "get_message_serializer",
    "get_message_deserializer",
    "create_ocr_result_message",
]