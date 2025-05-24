"""
Type definitions for RabbitMQ message structures, exchange configurations, and queue operations.

This module provides type definitions for consuming document messages from the Email Service
and publishing classification results to the OCR Service. It includes types for message
payloads, headers, and delivery options to ensure type safety for message queue operations.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, TypeVar, Union, Callable
from datetime import datetime
import json
import uuid
from enum import Enum, auto

# Import from relative paths to avoid circular imports
from .errors import Result, ServiceError, MessagingError
from .documents import Document, DocumentType


class DeliveryMode(Enum):
    """Enumeration of RabbitMQ message delivery modes.
    
    These modes determine the persistence of messages in the queue.
    """
    # Non-persistent (faster but messages may be lost if broker restarts)
    NON_PERSISTENT = 1
    # Persistent (slower but messages survive broker restarts)
    PERSISTENT = 2


class ExchangeType(Enum):
    """Enumeration of RabbitMQ exchange types.
    
    These types determine how messages are routed to queues.
    """
    # Routes messages to queues based on routing key
    DIRECT = "direct"
    # Routes messages to all bound queues
    FANOUT = "fanout"
    # Routes messages based on pattern matching of routing keys
    TOPIC = "topic"
    # Routes messages based on message headers
    HEADERS = "headers"


class MessageHeaders(Dict[str, Any]):
    """Type definition for message headers.
    
    Contains metadata and routing information for RabbitMQ messages.
    """
    
    @classmethod
    def create(
        cls,
        message_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        content_type: str = "application/json",
        content_encoding: str = "utf-8",
        delivery_mode: DeliveryMode = DeliveryMode.PERSISTENT,
        priority: int = 0,
        app_id: str = "document-service",
        timestamp: Optional[datetime] = None,
        **custom_headers: Any
    ) -> MessageHeaders:
        """Create a new message headers dictionary.
        
        Args:
            message_id: Unique identifier for the message (generated if not provided)
            correlation_id: ID for correlating related messages (for request/reply pattern)
            reply_to: Queue name to reply to (for request/reply pattern)
            content_type: MIME type of the message content
            content_encoding: Encoding of the message content
            delivery_mode: Persistence mode for the message
            priority: Message priority (0-9)
            app_id: Identifier for the sending application
            timestamp: Message timestamp (defaults to now)
            **custom_headers: Additional custom headers
            
        Returns:
            A new MessageHeaders instance
        """
        headers = cls({
            "message_id": message_id or str(uuid.uuid4()),
            "content_type": content_type,
            "content_encoding": content_encoding,
            "delivery_mode": delivery_mode.value,
            "priority": priority,
            "app_id": app_id,
            "timestamp": int((timestamp or datetime.utcnow()).timestamp())
        })
        
        if correlation_id:
            headers["correlation_id"] = correlation_id
            
        if reply_to:
            headers["reply_to"] = reply_to
            
        # Add custom headers
        for key, value in custom_headers.items():
            headers[key] = value
            
        return headers


class MessagePayload(Dict[str, Any]):
    """Type definition for message payloads.
    
    Contains the actual data being sent in RabbitMQ messages.
    """
    
    @classmethod
    def from_document(
        cls,
        document: Document,
        include_content: bool = False
    ) -> MessagePayload:
        """Create a message payload from a document.
        
        Args:
            document: The document to create a payload from
            include_content: Whether to include the document binary content
            
        Returns:
            A new MessagePayload instance
        """
        payload = cls(document.to_dict())
        
        # Add binary content if requested (base64 encoded)
        if include_content and document.content:
            import base64
            payload["content_base64"] = base64.b64encode(document.content).decode("utf-8")
            
        return payload
    
    @classmethod
    def create_classification_result(
        cls,
        document_id: str,
        document_type: DocumentType,
        confidence: float,
        confidence_scores: Dict[str, float],
        requires_review: bool,
        model_version: str,
        features_used: List[str],
        classified_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MessagePayload:
        """Create a classification result payload.
        
        Args:
            document_id: ID of the classified document
            document_type: Classified document type
            confidence: Overall confidence score (0-1)
            confidence_scores: Confidence scores for each possible type
            requires_review: Whether human review is recommended
            model_version: Version of the classification model used
            features_used: List of features used for classification
            classified_at: When the classification was performed
            metadata: Additional metadata about the classification
            
        Returns:
            A new MessagePayload instance
        """
        return cls({
            "document_id": document_id,
            "document_type": document_type.value,
            "confidence": confidence,
            "confidence_scores": confidence_scores,
            "requires_review": requires_review,
            "model_version": model_version,
            "features_used": features_used,
            "classified_at": (classified_at or datetime.utcnow()).isoformat(),
            "metadata": metadata or {}
        })
    
    def to_json(self) -> str:
        """Convert the payload to a JSON string.
        
        Returns:
            JSON string representation of the payload
        """
        return json.dumps(self, default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o))
    
    @classmethod
    def from_json(cls, json_str: str) -> MessagePayload:
        """Create a payload from a JSON string.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            A new MessagePayload instance
            
        Raises:
            MessagingError: If the JSON is invalid
        """
        try:
            return cls(json.loads(json_str))
        except json.JSONDecodeError as e:
            raise MessagingError(
                message="Failed to parse message payload JSON",
                context={"json_str": json_str[:100] + "..." if len(json_str) > 100 else json_str},
                original_exception=e
            )


class ExchangeConfig:
    """Configuration for a RabbitMQ exchange.
    
    Contains all parameters needed to declare and use a RabbitMQ exchange.
    """
    
    def __init__(
        self,
        name: str,
        exchange_type: ExchangeType = ExchangeType.DIRECT,
        durable: bool = True,
        auto_delete: bool = False,
        arguments: Optional[Dict[str, Any]] = None
    ):
        """Initialize a new exchange configuration.
        
        Args:
            name: Name of the exchange
            exchange_type: Type of the exchange
            durable: Whether the exchange survives broker restarts
            auto_delete: Whether the exchange is deleted when no longer used
            arguments: Additional exchange arguments
        """
        self.name = name
        self.exchange_type = exchange_type
        self.durable = durable
        self.auto_delete = auto_delete
        self.arguments = arguments or {}
    
    @classmethod
    def document_exchange(cls) -> ExchangeConfig:
        """Create the standard document exchange configuration.
        
        Returns:
            Exchange configuration for the document exchange
        """
        return cls(
            name="mca.documents",
            exchange_type=ExchangeType.FANOUT,
            durable=True
        )
    
    @classmethod
    def classification_exchange(cls) -> ExchangeConfig:
        """Create the standard classification exchange configuration.
        
        Returns:
            Exchange configuration for the classification exchange
        """
        return cls(
            name="mca.classification",
            exchange_type=ExchangeType.DIRECT,
            durable=True
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the exchange configuration to a dictionary.
        
        Returns:
            Dictionary representation of the exchange configuration
        """
        return {
            "name": self.name,
            "exchange_type": self.exchange_type.value,
            "durable": self.durable,
            "auto_delete": self.auto_delete,
            "arguments": self.arguments
        }


class QueueConfig:
    """Configuration for a RabbitMQ queue.
    
    Contains all parameters needed to declare and use a RabbitMQ queue.
    """
    
    def __init__(
        self,
        name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: Optional[Dict[str, Any]] = None
    ):
        """Initialize a new queue configuration.
        
        Args:
            name: Name of the queue
            durable: Whether the queue survives broker restarts
            exclusive: Whether the queue is exclusive to the connection
            auto_delete: Whether the queue is deleted when no longer used
            arguments: Additional queue arguments
        """
        self.name = name
        self.durable = durable
        self.exclusive = exclusive
        self.auto_delete = auto_delete
        self.arguments = arguments or {}
    
    @classmethod
    def document_processing_queue(cls) -> QueueConfig:
        """Create the standard document processing queue configuration.
        
        Returns:
            Queue configuration for the document processing queue
        """
        return cls(
            name="document-processing",
            durable=True,
            arguments={
                "x-dead-letter-exchange": "mca.dead-letter",
                "x-dead-letter-routing-key": "document-processing.dead",
                "x-message-ttl": 1000 * 60 * 60 * 24  # 24 hours
            }
        )
    
    @classmethod
    def classification_results_queue(cls) -> QueueConfig:
        """Create the standard classification results queue configuration.
        
        Returns:
            Queue configuration for the classification results queue
        """
        return cls(
            name="classification-results",
            durable=True,
            arguments={
                "x-dead-letter-exchange": "mca.dead-letter",
                "x-dead-letter-routing-key": "classification-results.dead",
                "x-message-ttl": 1000 * 60 * 60 * 24  # 24 hours
            }
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the queue configuration to a dictionary.
        
        Returns:
            Dictionary representation of the queue configuration
        """
        return {
            "name": self.name,
            "durable": self.durable,
            "exclusive": self.exclusive,
            "auto_delete": self.auto_delete,
            "arguments": self.arguments
        }


class BindingConfig:
    """Configuration for binding a queue to an exchange.
    
    Contains all parameters needed to bind a queue to an exchange.
    """
    
    def __init__(
        self,
        exchange: Union[str, ExchangeConfig],
        queue: Union[str, QueueConfig],
        routing_key: str = "",
        arguments: Optional[Dict[str, Any]] = None
    ):
        """Initialize a new binding configuration.
        
        Args:
            exchange: Exchange name or configuration
            queue: Queue name or configuration
            routing_key: Routing key for the binding
            arguments: Additional binding arguments
        """
        self.exchange = exchange.name if isinstance(exchange, ExchangeConfig) else exchange
        self.queue = queue.name if isinstance(queue, QueueConfig) else queue
        self.routing_key = routing_key
        self.arguments = arguments or {}
    
    @classmethod
    def document_processing_binding(cls) -> BindingConfig:
        """Create the standard document processing binding configuration.
        
        Returns:
            Binding configuration for the document processing queue
        """
        return cls(
            exchange=ExchangeConfig.document_exchange(),
            queue=QueueConfig.document_processing_queue()
        )
    
    @classmethod
    def classification_results_binding(cls) -> BindingConfig:
        """Create the standard classification results binding configuration.
        
        Returns:
            Binding configuration for the classification results queue
        """
        return cls(
            exchange=ExchangeConfig.classification_exchange(),
            queue=QueueConfig.classification_results_queue(),
            routing_key="classification.results"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the binding configuration to a dictionary.
        
        Returns:
            Dictionary representation of the binding configuration
        """
        return {
            "exchange": self.exchange,
            "queue": self.queue,
            "routing_key": self.routing_key,
            "arguments": self.arguments
        }


class PublishOptions:
    """Options for publishing messages to RabbitMQ.
    
    Contains all parameters needed to publish a message to RabbitMQ.
    """
    
    def __init__(
        self,
        exchange: Union[str, ExchangeConfig],
        routing_key: str = "",
        mandatory: bool = True,
        headers: Optional[MessageHeaders] = None,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        expiration: Optional[int] = None,
        delivery_mode: DeliveryMode = DeliveryMode.PERSISTENT,
        priority: int = 0,
        app_id: str = "document-service"
    ):
        """Initialize new publish options.
        
        Args:
            exchange: Exchange name or configuration
            routing_key: Routing key for the message
            mandatory: Whether to raise an exception if the message can't be routed
            headers: Message headers
            correlation_id: ID for correlating related messages
            reply_to: Queue name to reply to
            expiration: Message expiration time in milliseconds
            delivery_mode: Persistence mode for the message
            priority: Message priority (0-9)
            app_id: Identifier for the sending application
        """
        self.exchange = exchange.name if isinstance(exchange, ExchangeConfig) else exchange
        self.routing_key = routing_key
        self.mandatory = mandatory
        
        # Create headers if not provided
        self.headers = headers or MessageHeaders.create(
            correlation_id=correlation_id,
            reply_to=reply_to,
            delivery_mode=delivery_mode,
            priority=priority,
            app_id=app_id
        )
        
        # Add expiration if provided
        if expiration is not None:
            self.headers["expiration"] = str(expiration)
    
    @classmethod
    def for_classification_result(
        cls,
        correlation_id: Optional[str] = None,
        priority: int = 0
    ) -> PublishOptions:
        """Create publish options for classification results.
        
        Args:
            correlation_id: ID for correlating related messages
            priority: Message priority (0-9)
            
        Returns:
            PublishOptions for publishing classification results
        """
        return cls(
            exchange=ExchangeConfig.classification_exchange(),
            routing_key="classification.results",
            correlation_id=correlation_id,
            priority=priority
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the publish options to a dictionary.
        
        Returns:
            Dictionary representation of the publish options
        """
        return {
            "exchange": self.exchange,
            "routing_key": self.routing_key,
            "mandatory": self.mandatory,
            "properties": dict(self.headers)
        }


class ConsumeOptions:
    """Options for consuming messages from RabbitMQ.
    
    Contains all parameters needed to consume messages from RabbitMQ.
    """
    
    def __init__(
        self,
        queue: Union[str, QueueConfig],
        consumer_tag: Optional[str] = None,
        exclusive: bool = False,
        no_local: bool = False,
        no_ack: bool = False,
        prefetch_count: int = 10,
        arguments: Optional[Dict[str, Any]] = None
    ):
        """Initialize new consume options.
        
        Args:
            queue: Queue name or configuration
            consumer_tag: Consumer identifier
            exclusive: Whether to request exclusive consumer access
            no_local: Don't deliver messages published by this connection
            no_ack: Whether to auto-acknowledge messages
            prefetch_count: Maximum number of unacknowledged messages
            arguments: Additional consume arguments
        """
        self.queue = queue.name if isinstance(queue, QueueConfig) else queue
        self.consumer_tag = consumer_tag or f"document-service-{str(uuid.uuid4())[:8]}"
        self.exclusive = exclusive
        self.no_local = no_local
        self.no_ack = no_ack
        self.prefetch_count = prefetch_count
        self.arguments = arguments or {}
    
    @classmethod
    def for_document_processing(cls, prefetch_count: int = 10) -> ConsumeOptions:
        """Create consume options for document processing.
        
        Args:
            prefetch_count: Maximum number of unacknowledged messages
            
        Returns:
            ConsumeOptions for consuming document processing messages
        """
        return cls(
            queue=QueueConfig.document_processing_queue(),
            prefetch_count=prefetch_count
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the consume options to a dictionary.
        
        Returns:
            Dictionary representation of the consume options
        """
        return {
            "queue": self.queue,
            "consumer_tag": self.consumer_tag,
            "exclusive": self.exclusive,
            "no_local": self.no_local,
            "no_ack": self.no_ack,
            "arguments": self.arguments
        }


# Type for message handler callbacks
T = TypeVar('T')
MessageHandler = Callable[[MessagePayload, MessageHeaders], Result[T, ServiceError]]


class ConnectionConfig:
    """Configuration for a RabbitMQ connection.
    
    Contains all parameters needed to connect to RabbitMQ.
    """
    
    def __init__(
        self,
        host: str,
        port: int = 5672,
        virtual_host: str = "/",
        username: str = "guest",
        password: str = "guest",
        heartbeat: int = 60,
        connection_attempts: int = 3,
        retry_delay: int = 5,
        ssl: bool = True,
        ssl_options: Optional[Dict[str, Any]] = None,
        client_properties: Optional[Dict[str, Any]] = None
    ):
        """Initialize a new connection configuration.
        
        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            virtual_host: RabbitMQ virtual host
            username: RabbitMQ username
            password: RabbitMQ password
            heartbeat: Heartbeat interval in seconds
            connection_attempts: Number of connection attempts
            retry_delay: Delay between connection attempts in seconds
            ssl: Whether to use SSL/TLS
            ssl_options: SSL/TLS options
            client_properties: Additional client properties
        """
        self.host = host
        self.port = port
        self.virtual_host = virtual_host
        self.username = username
        self.password = password
        self.heartbeat = heartbeat
        self.connection_attempts = connection_attempts
        self.retry_delay = retry_delay
        self.ssl = ssl
        self.ssl_options = ssl_options or {}
        self.client_properties = client_properties or {
            "product": "Document Service",
            "platform": "Python",
            "connection_name": f"document-service-{str(uuid.uuid4())[:8]}"
        }
    
    @classmethod
    def from_env(cls) -> ConnectionConfig:
        """Create a connection configuration from environment variables.
        
        Returns:
            ConnectionConfig from environment variables
        """
        import os
        
        return cls(
            host=os.environ.get("RABBITMQ_HOST", "localhost"),
            port=int(os.environ.get("RABBITMQ_PORT", "5672")),
            virtual_host=os.environ.get("RABBITMQ_VHOST", "/"),
            username=os.environ.get("RABBITMQ_USERNAME", "guest"),
            password=os.environ.get("RABBITMQ_PASSWORD", "guest"),
            heartbeat=int(os.environ.get("RABBITMQ_HEARTBEAT", "60")),
            ssl=os.environ.get("RABBITMQ_SSL", "true").lower() in ("true", "1", "yes")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the connection configuration to a dictionary.
        
        Returns:
            Dictionary representation of the connection configuration
        """
        return {
            "host": self.host,
            "port": self.port,
            "virtual_host": self.virtual_host,
            "credentials": {
                "username": self.username,
                # Password is masked for security
                "password": "*****"
            },
            "heartbeat": self.heartbeat,
            "connection_attempts": self.connection_attempts,
            "retry_delay": self.retry_delay,
            "ssl": self.ssl,
            "ssl_options": {k: "..." for k in self.ssl_options.keys()},
            "client_properties": self.client_properties
        }
    
    def get_connection_parameters(self) -> Dict[str, Any]:
        """Get connection parameters for pika.
        
        Returns:
            Connection parameters for pika
        """
        return {
            "host": self.host,
            "port": self.port,
            "virtual_host": self.virtual_host,
            "credentials": {
                "username": self.username,
                "password": self.password
            },
            "heartbeat": self.heartbeat,
            "connection_attempts": self.connection_attempts,
            "retry_delay": self.retry_delay,
            "ssl": self.ssl,
            "ssl_options": self.ssl_options,
            "client_properties": self.client_properties
        }