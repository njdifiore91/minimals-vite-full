"""
Type definitions for RabbitMQ message structures, exchange configurations, and queue operations.

This module provides type definitions for consuming document messages from the Document Service
and publishing extraction results to the Data Service via RabbitMQ. It includes types for message
payloads, headers, and delivery options.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, TypedDict, Literal, Protocol, TypeVar, Generic, Callable
from enum import Enum
import json
from datetime import datetime

# Type aliases for common message components
JsonValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JsonDict = Dict[str, JsonValue]


class MessageHeaders(TypedDict, total=False):
    """Message headers for RabbitMQ messages with routing and metadata information."""
    message_id: str  # Unique identifier for the message
    correlation_id: str  # ID for tracking related messages
    timestamp: str  # ISO 8601 formatted timestamp
    content_type: str  # Content type (default: application/json)
    content_encoding: str  # Content encoding (default: utf-8)
    reply_to: Optional[str]  # Queue to reply to if needed
    expiration: Optional[str]  # Message expiration time in milliseconds
    priority: Optional[int]  # Message priority (0-9)
    app_id: str  # Application identifier (default: ocr-service)
    user_id: Optional[str]  # User identifier if applicable
    type: str  # Message type for routing
    delivery_mode: int  # 1 = non-persistent, 2 = persistent


class MessagePayload(TypedDict, total=False):
    """Standard message payload structure for OCR processing messages."""
    document_id: str  # Unique identifier for the document
    application_id: str  # Associated application ID
    document_type: str  # Type of document (application, tax_return, etc.)
    storage_path: str  # S3 storage path for the document
    mime_type: str  # MIME type of the document
    file_name: str  # Original filename
    file_size: int  # Size in bytes
    created_at: str  # ISO 8601 timestamp
    metadata: JsonDict  # Additional document metadata
    classification: JsonDict  # Document classification details
    extraction_config: Optional[JsonDict]  # Configuration for extraction
    priority: Optional[int]  # Processing priority (1-5)
    retry_count: Optional[int]  # Number of processing retries
    extraction_results: Optional[JsonDict]  # OCR extraction results
    confidence_scores: Optional[Dict[str, float]]  # Confidence scores for extracted fields
    processing_time_ms: Optional[int]  # Processing time in milliseconds
    error: Optional[JsonDict]  # Error details if processing failed


class ExchangeType(Enum):
    """RabbitMQ exchange types."""
    DIRECT = "direct"
    FANOUT = "fanout"
    TOPIC = "topic"
    HEADERS = "headers"


class ExchangeConfig(TypedDict, total=False):
    """Configuration for RabbitMQ exchanges."""
    name: str  # Exchange name
    type: str  # Exchange type (direct, fanout, topic, headers)
    durable: bool  # Survive broker restart
    auto_delete: bool  # Delete when no queues bound
    internal: bool  # Can't be published to directly
    passive: bool  # Check if exchange exists without creating
    arguments: Optional[Dict[str, Any]]  # Additional arguments


class QueueConfig(TypedDict, total=False):
    """Configuration for RabbitMQ queues."""
    name: str  # Queue name
    durable: bool  # Survive broker restart
    exclusive: bool  # Used by only one connection
    auto_delete: bool  # Delete when consumer disconnects
    passive: bool  # Check if queue exists without creating
    arguments: Optional[Dict[str, Any]]  # Additional arguments like TTL
    prefetch_count: int  # Maximum unacknowledged messages
    prefetch_size: Optional[int]  # Maximum unacknowledged message size
    consumer_tag: Optional[str]  # Consumer identifier


class BindingConfig(TypedDict, total=False):
    """Configuration for binding a queue to an exchange."""
    queue: str  # Queue name
    exchange: str  # Exchange name
    routing_key: str  # Routing key
    arguments: Optional[Dict[str, Any]]  # Additional arguments


class PublishOptions(TypedDict, total=False):
    """Options for publishing messages to RabbitMQ."""
    exchange: str  # Exchange name
    routing_key: str  # Routing key
    mandatory: bool  # Return message if it can't be routed
    immediate: bool  # Return message if it can't be delivered immediately
    properties: MessageHeaders  # Message properties
    correlation_id: Optional[str]  # Correlation ID for request-reply pattern
    reply_to: Optional[str]  # Queue to reply to
    expiration: Optional[str]  # Message expiration time in milliseconds
    message_id: Optional[str]  # Message ID
    timestamp: Optional[int]  # Message timestamp
    app_id: Optional[str]  # Application ID
    delivery_mode: Optional[int]  # 1 = non-persistent, 2 = persistent


class ConsumeOptions(TypedDict, total=False):
    """Options for consuming messages from RabbitMQ."""
    queue: str  # Queue name
    consumer_tag: Optional[str]  # Consumer identifier
    no_local: bool  # Don't receive messages published by this connection
    no_ack: bool  # Don't require acknowledgements
    exclusive: bool  # Only this consumer can access the queue
    arguments: Optional[Dict[str, Any]]  # Additional arguments
    prefetch_count: Optional[int]  # Maximum unacknowledged messages
    prefetch_size: Optional[int]  # Maximum unacknowledged message size


class ConnectionConfig(TypedDict, total=False):
    """Configuration for RabbitMQ connection."""
    host: str  # RabbitMQ host
    port: int  # RabbitMQ port
    virtual_host: str  # Virtual host
    username: str  # Username
    password: str  # Password
    heartbeat: int  # Heartbeat interval in seconds
    blocked_connection_timeout: Optional[int]  # Timeout for blocked connections
    connection_attempts: int  # Number of connection attempts
    retry_delay: float  # Delay between connection attempts
    ssl: bool  # Use SSL/TLS
    ssl_options: Optional[Dict[str, Any]]  # SSL/TLS options
    client_properties: Optional[Dict[str, Any]]  # Client properties


class RetryConfig(TypedDict, total=False):
    """Configuration for message retry handling."""
    max_retries: int  # Maximum number of retries
    initial_delay: float  # Initial delay in seconds
    max_delay: float  # Maximum delay in seconds
    backoff_factor: float  # Backoff factor for exponential backoff
    retry_on_exceptions: List[str]  # Exception names to retry on


T = TypeVar('T')


class MessageResult(Generic[T]):
    """Result of a message operation with error handling."""
    def __init__(self, success: bool, value: Optional[T] = None, error: Optional[Exception] = None):
        self.success = success
        self.value = value
        self.error = error

    @classmethod
    def ok(cls, value: T) -> MessageResult[T]:
        """Create a successful result."""
        return cls(True, value)

    @classmethod
    def error(cls, error: Exception) -> MessageResult[T]:
        """Create an error result."""
        return cls(False, error=error)

    def __bool__(self) -> bool:
        return self.success


class MessageHandler(Protocol):
    """Protocol for message handlers."""
    def __call__(self, payload: MessagePayload, headers: MessageHeaders) -> None:
        """Handle a message."""
        ...


class MessageSerializer:
    """Serializer for RabbitMQ messages."""
    @staticmethod
    def serialize(payload: MessagePayload) -> bytes:
        """Serialize a message payload to JSON bytes."""
        return json.dumps(payload, ensure_ascii=False).encode('utf-8')

    @staticmethod
    def deserialize(body: bytes) -> MessagePayload:
        """Deserialize JSON bytes to a message payload."""
        return json.loads(body.decode('utf-8'))


# Default configurations based on technical specification
DEFAULT_EXCHANGE: ExchangeConfig = {
    "name": "mca.documents",
    "type": ExchangeType.FANOUT.value,
    "durable": True,
    "auto_delete": False,
}

DOCUMENT_PROCESSING_QUEUE: QueueConfig = {
    "name": "document-processing",
    "durable": True,
    "exclusive": False,
    "auto_delete": False,
    "prefetch_count": 10,
}

DATA_EXTRACTION_QUEUE: QueueConfig = {
    "name": "data-extraction",
    "durable": True,
    "exclusive": False,
    "auto_delete": False,
    "prefetch_count": 10,
}

NOTIFICATION_QUEUE: QueueConfig = {
    "name": "notification",
    "durable": True,
    "exclusive": False,
    "auto_delete": False,
    "prefetch_count": 50,
}

DEFAULT_CONNECTION: ConnectionConfig = {
    "host": "rabbitmq",
    "port": 5672,
    "virtual_host": "/",
    "heartbeat": 60,
    "connection_attempts": 5,
    "retry_delay": 1.0,
    "ssl": True,  # TLS required as per section 3.2.3
}

DEFAULT_RETRY: RetryConfig = {
    "max_retries": 3,
    "initial_delay": 1.0,
    "max_delay": 30.0,
    "backoff_factor": 2.0,
    "retry_on_exceptions": [
        "ConnectionError",
        "ChannelError",
        "AMQPError",
        "TimeoutError",
    ],
}