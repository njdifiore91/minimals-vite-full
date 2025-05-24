"""Type definitions for RabbitMQ message structures used by the OCR Service.

This module provides type hints for RabbitMQ message structures, exchange configurations,
and queue operations used by the OCR Service. It includes types for message payloads,
headers, and delivery options to ensure type safety for message queue operations.

The OCR Service consumes document messages from the Document Service and publishes
extraction results to the Data Service via RabbitMQ, using standardized JSON formats.
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Union, TypeVar, cast


class MessagePriority(enum.IntEnum):
    """Priority levels for RabbitMQ messages.
    
    These priority levels correspond to the standard RabbitMQ message priorities,
    with higher values indicating higher priority.
    """
    
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class DeliveryMode(enum.IntEnum):
    """Delivery modes for RabbitMQ messages.
    
    These delivery modes determine whether messages are persisted to disk:
    - NON_PERSISTENT: Messages are not persisted to disk and may be lost on broker restart
    - PERSISTENT: Messages are persisted to disk and survive broker restarts
    """
    
    NON_PERSISTENT = 1
    PERSISTENT = 2


class MessageStatus(enum.Enum):
    """Status values for document processing messages.
    
    These status values indicate the current state of document processing:
    - RECEIVED: Document has been received but not yet processed
    - PROCESSING: Document is currently being processed
    - COMPLETED: Document processing has been completed successfully
    - FAILED: Document processing has failed
    - PENDING_VERIFICATION: Document requires human verification
    """
    
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING_VERIFICATION = "pending_verification"


class MessageHeaders(TypedDict, total=False):
    """Headers for RabbitMQ messages.
    
    This type represents the headers attached to RabbitMQ messages,
    including routing information, correlation IDs, and metadata.
    The 'total=False' parameter indicates that all fields are optional.
    """
    
    document_id: str  # ID of the document being processed
    application_id: str  # ID of the application this document belongs to
    correlation_id: str  # Correlation ID for request-response pattern
    reply_to: str  # Queue name for response messages
    content_type: str  # MIME type of the message content
    content_encoding: str  # Encoding of the message content
    delivery_mode: int  # Delivery mode (1=non-persistent, 2=persistent)
    priority: int  # Message priority (1-10)
    timestamp: int  # Unix timestamp in seconds
    expiration: str  # Message expiration time in milliseconds as string
    message_id: str  # Unique identifier for the message
    user_id: str  # User who created the message
    app_id: str  # Application that created the message
    source_service: str  # Service that published the message
    destination_service: str  # Service that should consume the message
    retry_count: int  # Number of retry attempts for this message
    x_death: List[Dict[str, Any]]  # Dead letter information


class MessagePayload(TypedDict, total=False):
    """Payload for RabbitMQ messages in the OCR Service.
    
    This type represents the payload of RabbitMQ messages used in the OCR Service,
    including document information, processing status, and extraction results.
    The 'total=False' parameter indicates that all fields are optional.
    """
    
    message_id: str  # Unique identifier for the message
    document_id: str  # ID of the document being processed
    document_type: str  # Type of document (application_form, tax_return, etc.)
    application_id: str  # ID of the application this document belongs to
    storage_path: str  # S3 storage path for the document
    content_type: str  # MIME type of the document
    timestamp: str  # ISO 8601 timestamp
    source_service: str  # Service that published the message
    status: str  # Processing status of the document
    metadata: Dict[str, Any]  # Additional document metadata
    extraction_results: Dict[str, Any]  # OCR extraction results
    confidence_scores: Dict[str, float]  # Confidence scores for extracted fields
    error: Dict[str, Any]  # Error information if processing failed
    processing_time_ms: float  # Processing time in milliseconds
    requires_verification: bool  # Whether human verification is required
    verification_fields: List[str]  # Fields requiring verification


def create_message_payload(
    document_id: str,
    document_type: str,
    application_id: str,
    storage_path: str,
    content_type: str,
    source_service: str,
    status: str,
    metadata: Optional[Dict[str, Any]] = None,
    extraction_results: Optional[Dict[str, Any]] = None,
    confidence_scores: Optional[Dict[str, float]] = None,
    error: Optional[Dict[str, Any]] = None,
    processing_time_ms: Optional[float] = None,
    requires_verification: Optional[bool] = None,
    verification_fields: Optional[List[str]] = None
) -> MessagePayload:
    """Create a standardized message payload for OCR processing.
    
    Args:
        document_id: ID of the document being processed
        document_type: Type of document
        application_id: ID of the application this document belongs to
        storage_path: S3 storage path for the document
        content_type: MIME type of the document
        source_service: Service that published the message
        status: Processing status of the document
        metadata: Additional document metadata
        extraction_results: OCR extraction results (if available)
        confidence_scores: Confidence scores for extracted fields
        error: Error information (if processing failed)
        processing_time_ms: Processing time in milliseconds
        requires_verification: Whether human verification is required
        verification_fields: Fields requiring verification
        
    Returns:
        MessagePayload: A new message payload instance
    """
    import uuid
    from datetime import datetime
    
    # Generate a unique message ID
    message_id = str(uuid.uuid4())
    
    # Get current timestamp in ISO 8601 format
    timestamp = datetime.now().isoformat()
    
    # Create the payload
    payload: MessagePayload = {
        "message_id": message_id,
        "document_id": document_id,
        "document_type": document_type,
        "application_id": application_id,
        "storage_path": storage_path,
        "content_type": content_type,
        "timestamp": timestamp,
        "source_service": source_service,
        "status": status,
        "metadata": metadata or {},
    }
    
    # Add optional fields if provided
    if extraction_results is not None:
        payload["extraction_results"] = extraction_results
        
    if confidence_scores is not None:
        payload["confidence_scores"] = confidence_scores
        
    if error is not None:
        payload["error"] = error
        
    if processing_time_ms is not None:
        payload["processing_time_ms"] = processing_time_ms
        
    if requires_verification is not None:
        payload["requires_verification"] = requires_verification
        
    if verification_fields is not None:
        payload["verification_fields"] = verification_fields
        
    return payload


@dataclass
class ExchangeConfig:
    """Configuration for RabbitMQ exchanges.
    
    This class represents the configuration for a RabbitMQ exchange,
    including its name, type, and durability settings.
    
    Attributes:
        name: Name of the exchange
        exchange_type: Type of exchange (direct, fanout, topic, headers)
        durable: Whether the exchange survives broker restarts
        auto_delete: Whether the exchange is deleted when no longer used
        internal: Whether the exchange is internal (not directly publishable)
        arguments: Additional exchange arguments
    """
    
    name: str
    exchange_type: str = "fanout"  # direct, fanout, topic, headers
    durable: bool = True
    auto_delete: bool = False
    internal: bool = False
    arguments: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def default_exchange(cls) -> ExchangeConfig:
        """Create the default exchange configuration for the OCR Service.
        
        Returns:
            ExchangeConfig: Default exchange configuration
        """
        return cls(
            name="mca.documents",
            exchange_type="fanout",
            durable=True,
            auto_delete=False
        )
    
    @classmethod
    def data_processing_exchange(cls) -> ExchangeConfig:
        """Create the data processing exchange configuration.
        
        Returns:
            ExchangeConfig: Data processing exchange configuration
        """
        return cls(
            name="mca.data.processing",
            exchange_type="direct",
            durable=True,
            auto_delete=False
        )


@dataclass
class QueueConfig:
    """Configuration for RabbitMQ queues.
    
    This class represents the configuration for a RabbitMQ queue,
    including its name, durability settings, and binding parameters.
    
    Attributes:
        name: Name of the queue
        durable: Whether the queue survives broker restarts
        exclusive: Whether the queue is exclusive to the connection
        auto_delete: Whether the queue is deleted when no longer used
        arguments: Additional queue arguments
        bindings: List of exchange bindings for this queue
    """
    
    name: str
    durable: bool = True
    exclusive: bool = False
    auto_delete: bool = False
    arguments: Dict[str, Any] = field(default_factory=dict)
    bindings: List[Dict[str, Any]] = field(default_factory=list)
    
    @classmethod
    def ocr_request_queue(cls) -> QueueConfig:
        """Create the OCR request queue configuration.
        
        Returns:
            QueueConfig: OCR request queue configuration
        """
        return cls(
            name="ocr.request",
            durable=True,
            exclusive=False,
            auto_delete=False,
            arguments={
                "x-message-ttl": 3600000,  # 1 hour in milliseconds
                "x-dead-letter-exchange": "mca.dead-letter",
                "x-dead-letter-routing-key": "ocr.request.dead-letter"
            },
            bindings=[
                {
                    "exchange": "mca.documents",
                    "routing_key": "document.classified"
                }
            ]
        )
    
    @classmethod
    def data_processing_queue(cls) -> QueueConfig:
        """Create the data processing queue configuration.
        
        Returns:
            QueueConfig: Data processing queue configuration
        """
        return cls(
            name="data.processing",
            durable=True,
            exclusive=False,
            auto_delete=False,
            arguments={
                "x-message-ttl": 3600000,  # 1 hour in milliseconds
                "x-dead-letter-exchange": "mca.dead-letter",
                "x-dead-letter-routing-key": "data.processing.dead-letter"
            },
            bindings=[
                {
                    "exchange": "mca.data.processing",
                    "routing_key": "data.extraction.complete"
                }
            ]
        )


@dataclass
class PublishOptions:
    """Options for publishing messages to RabbitMQ.
    
    This class represents the options for publishing messages to RabbitMQ,
    including delivery mode, priority, and expiration settings.
    
    Attributes:
        exchange: Exchange to publish to
        routing_key: Routing key for the message
        mandatory: Whether the message must be routable
        immediate: Whether the message must be delivered immediately
        delivery_mode: Delivery mode (1=non-persistent, 2=persistent)
        priority: Message priority (1-10)
        expiration: Message expiration time in milliseconds
        app_id: Application identifier
        timestamp: Whether to include a timestamp
        headers: Message headers
        correlation_id: Correlation ID for request-response pattern
        reply_to: Queue name for response messages
        message_id: Unique identifier for the message
        content_type: MIME type of the message content
        content_encoding: Encoding of the message content
    """
    
    exchange: str
    routing_key: str
    mandatory: bool = True
    immediate: bool = False
    delivery_mode: DeliveryMode = DeliveryMode.PERSISTENT
    priority: MessagePriority = MessagePriority.NORMAL
    expiration: Optional[int] = None  # in milliseconds
    app_id: str = "ocr-service"
    timestamp: bool = True
    headers: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    message_id: Optional[str] = None
    content_type: str = "application/json"
    content_encoding: str = "utf-8"
    
    @classmethod
    def for_data_service(cls, document_id: str, routing_key: str = "data.extraction.complete") -> PublishOptions:
        """Create publish options for sending messages to the Data Service.
        
        Args:
            document_id: ID of the document being processed
            routing_key: Routing key for the message
            
        Returns:
            PublishOptions: Publish options for the Data Service
        """
        import uuid
        
        return cls(
            exchange="mca.data.processing",
            routing_key=routing_key,
            mandatory=True,
            delivery_mode=DeliveryMode.PERSISTENT,
            priority=MessagePriority.NORMAL,
            app_id="ocr-service",
            headers={
                "document_id": document_id,
                "source_service": "ocr-service",
                "destination_service": "data-service"
            },
            correlation_id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            content_type="application/json",
            content_encoding="utf-8"
        )


@dataclass
class ConsumeOptions:
    """Options for consuming messages from RabbitMQ.
    
    This class represents the options for consuming messages from RabbitMQ,
    including queue name, consumer tag, and acknowledgment settings.
    
    Attributes:
        queue: Queue to consume from
        consumer_tag: Consumer identifier
        exclusive: Whether the consumer has exclusive access to the queue
        auto_ack: Whether to automatically acknowledge messages
        prefetch_count: Maximum number of unacknowledged messages
        arguments: Additional consumer arguments
    """
    
    queue: str
    consumer_tag: Optional[str] = None
    exclusive: bool = False
    auto_ack: bool = False
    prefetch_count: int = 10
    arguments: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def for_ocr_requests(cls, consumer_tag: Optional[str] = None, prefetch_count: int = 10) -> ConsumeOptions:
        """Create consume options for OCR request messages.
        
        Args:
            consumer_tag: Consumer identifier (optional)
            prefetch_count: Maximum number of unacknowledged messages
            
        Returns:
            ConsumeOptions: Consume options for OCR requests
        """
        return cls(
            queue="ocr.request",
            consumer_tag=consumer_tag,
            exclusive=False,
            auto_ack=False,
            prefetch_count=prefetch_count
        )


@dataclass
class RabbitMQConfig:
    """Configuration for RabbitMQ connection and channels.
    
    This class represents the configuration for connecting to RabbitMQ,
    including connection parameters, exchange and queue settings, and
    security options.
    
    Attributes:
        host: RabbitMQ host
        port: RabbitMQ port
        virtual_host: RabbitMQ virtual host
        username: RabbitMQ username
        password: RabbitMQ password
        use_ssl: Whether to use SSL/TLS
        ssl_options: SSL/TLS options
        connection_attempts: Number of connection attempts
        retry_delay: Delay between connection attempts in seconds
        heartbeat: Heartbeat interval in seconds
        blocked_connection_timeout: Timeout for blocked connections in seconds
        exchanges: Exchange configurations
        queues: Queue configurations
        consumer_prefetch: Default prefetch count for consumers
    """
    
    host: str = "rabbitmq"
    port: int = 5672
    virtual_host: str = "/"
    username: str = "guest"
    password: str = "guest"
    use_ssl: bool = True
    ssl_options: Dict[str, Any] = field(default_factory=dict)
    connection_attempts: int = 5
    retry_delay: float = 1.0
    heartbeat: int = 60
    blocked_connection_timeout: int = 300
    exchanges: List[ExchangeConfig] = field(default_factory=list)
    queues: List[QueueConfig] = field(default_factory=list)
    consumer_prefetch: int = 10
    
    def __post_init__(self):
        """Initialize default exchanges and queues if not provided."""
        if not self.exchanges:
            self.exchanges = [
                ExchangeConfig.default_exchange(),
                ExchangeConfig.data_processing_exchange()
            ]
            
        if not self.queues:
            self.queues = [
                QueueConfig.ocr_request_queue(),
                QueueConfig.data_processing_queue()
            ]
            
        # Initialize SSL options if using SSL
        if self.use_ssl and not self.ssl_options:
            self.ssl_options = {
                "cert_reqs": 2,  # ssl.CERT_REQUIRED
                "ssl_version": 5,  # ssl.PROTOCOL_TLSv1_2
            }
    
    @classmethod
    def from_env(cls) -> RabbitMQConfig:
        """Create a RabbitMQConfig instance from environment variables.
        
        Returns:
            RabbitMQConfig: Configuration instance with values from environment variables
        """
        import os
        
        return cls(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            virtual_host=os.getenv("RABBITMQ_VIRTUAL_HOST", "/"),
            username=os.getenv("RABBITMQ_USERNAME", "guest"),
            password=os.getenv("RABBITMQ_PASSWORD", "guest"),
            use_ssl=os.getenv("RABBITMQ_USE_SSL", "true").lower() == "true",
            connection_attempts=int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "5")),
            retry_delay=float(os.getenv("RABBITMQ_RETRY_DELAY", "1.0")),
            heartbeat=int(os.getenv("RABBITMQ_HEARTBEAT", "60")),
            blocked_connection_timeout=int(os.getenv("RABBITMQ_BLOCKED_CONNECTION_TIMEOUT", "300")),
            consumer_prefetch=int(os.getenv("RABBITMQ_CONSUMER_PREFETCH", "10"))
        )