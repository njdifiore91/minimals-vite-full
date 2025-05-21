import json
import logging
import ssl
import time
from typing import Any, Callable, Dict, Optional, Union

import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.exceptions import AMQPConnectionError, AMQPChannelError

from ..config import rabbitmq_config
from ..types.messages import (
    MessagePayload, MessageHeaders, PublishOptions, ConsumeOptions,
    ExchangeConfig, QueueConfig, BindingConfig, DeliveryMode, ExchangeType
)
from ..types.errors import ServiceError, MessagingError, Result

logger = logging.getLogger(__name__)

class QueueService:
    """
    Service for handling RabbitMQ message queue operations.
    
    This service provides functionality for connecting to RabbitMQ,
    consuming messages from the 'document-processing' queue, and
    publishing classification results to the 'data-extraction' queue.
    
    Attributes:
        connection (Optional[BlockingConnection]): The RabbitMQ connection
        channel (Optional[BlockingChannel]): The RabbitMQ channel
        is_connected (bool): Flag indicating if the service is connected to RabbitMQ
        config (Dict): RabbitMQ configuration parameters
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the QueueService with RabbitMQ configuration.
        
        Args:
            config (Dict, optional): RabbitMQ configuration parameters.
                If not provided, loads from rabbitmq_config.
        """
        self.connection: Optional[BlockingConnection] = None
        self.channel: Optional[BlockingChannel] = None
        self.is_connected: bool = False
        self.config = config or rabbitmq_config.RABBITMQ_CONFIG
        
        # Initialize connection parameters
        self._connection_params = None
        self._setup_connection_params()
    
    def _setup_connection_params(self) -> None:
        """
        Set up RabbitMQ connection parameters with TLS configuration.
        
        This method configures the connection to RabbitMQ with TLS and client
        certificate authentication as required in the technical specification.
        """
        try:
            # Create SSL context for TLS connection
            ssl_context = ssl.create_default_context(
                cafile=self.config['tls']['ca_cert_path']
            )
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.load_cert_chain(
                certfile=self.config['tls']['client_cert_path'],
                keyfile=self.config['tls']['client_key_path']
            )
            
            # Create SSL options for pika
            ssl_options = pika.SSLOptions(
                context=ssl_context,
                server_hostname=self.config['host']
            )
            
            # Set up connection parameters
            self._connection_params = pika.ConnectionParameters(
                host=self.config['host'],
                port=self.config['port'],
                virtual_host=self.config['virtual_host'],
                credentials=pika.PlainCredentials(
                    username=self.config['username'],
                    password=self.config['password']
                ),
                ssl_options=ssl_options,
                heartbeat=self.config['heartbeat'],
                connection_attempts=self.config['connection_attempts'],
                retry_delay=self.config['retry_delay'],
                client_properties={
                    "product": "Document Service",
                    "platform": "Python",
                    "connection_name": "document-service-rabbitmq"
                }
            )
            
            logger.info("RabbitMQ connection parameters configured with TLS")
        except Exception as e:
            logger.error(f"Failed to set up RabbitMQ connection parameters: {str(e)}")
            raise ServiceError(
                message="RabbitMQ connection setup failed",
                context={"host": self.config['host'], "port": self.config['port']},
                original_exception=e
            )
    
    def connect(self) -> bool:
        """
        Establish connection to RabbitMQ server with TLS.
        
        This method connects to RabbitMQ, declares the exchange and queues,
        and binds the queues to the exchange as specified in the technical
        specification.
        
        Returns:
            bool: True if connection is successful, False otherwise
        
        Raises:
            ServiceError: If connection fails after all retry attempts
        """
        if self.is_connected:
            return True
        
        try:
            logger.info(f"Connecting to RabbitMQ at {self.config['host']}:{self.config['port']}")
            self.connection = pika.BlockingConnection(self._connection_params)
            self.channel = self.connection.channel()
            
            # Declare exchange
            exchange_config = ExchangeConfig.document_exchange()
            self.channel.exchange_declare(
                exchange=exchange_config.name,
                exchange_type=exchange_config.exchange_type.value,
                durable=exchange_config.durable,
                auto_delete=exchange_config.auto_delete,
                arguments=exchange_config.arguments
            )
            
            # Declare document processing queue
            doc_queue = QueueConfig.document_processing_queue()
            self.channel.queue_declare(
                queue=doc_queue.name,
                durable=doc_queue.durable,
                exclusive=doc_queue.exclusive,
                auto_delete=doc_queue.auto_delete,
                arguments=doc_queue.arguments
            )
            
            # Declare data extraction queue
            data_queue = QueueConfig.classification_results_queue()
            self.channel.queue_declare(
                queue=data_queue.name,
                durable=data_queue.durable,
                exclusive=data_queue.exclusive,
                auto_delete=data_queue.auto_delete,
                arguments=data_queue.arguments
            )
            
            # Bind queues to exchange
            doc_binding = BindingConfig.document_processing_binding()
            self.channel.queue_bind(
                exchange=doc_binding.exchange,
                queue=doc_binding.queue,
                routing_key=doc_binding.routing_key,
                arguments=doc_binding.arguments
            )
            
            data_binding = BindingConfig.classification_results_binding()
            self.channel.queue_bind(
                exchange=data_binding.exchange,
                queue=data_binding.queue,
                routing_key=data_binding.routing_key,
                arguments=data_binding.arguments
            )
            
            self.is_connected = True
            logger.info("Successfully connected to RabbitMQ")
            return True
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            self.is_connected = False
            raise ServiceError(
                message="RabbitMQ connection failed",
                context={"host": self.config['host'], "port": self.config['port']},
                original_exception=e
            )
    
    def disconnect(self) -> None:
        """
        Close the RabbitMQ connection and channel.
        
        This method gracefully closes the RabbitMQ connection and channel
        to ensure proper cleanup of resources.
        """
        try:
            if self.channel and self.channel.is_open:
                logger.info("Closing RabbitMQ channel")
                self.channel.close()
            
            if self.connection and self.connection.is_open:
                logger.info("Closing RabbitMQ connection")
                self.connection.close()
        except Exception as e:
            logger.warning(f"Error during RabbitMQ disconnect: {str(e)}")
        finally:
            self.channel = None
            self.connection = None
            self.is_connected = False
    
    def consume_messages(self, callback: Callable[[MessagePayload, MessageHeaders], None], 
                         options: Optional[ConsumeOptions] = None) -> None:
        """
        Start consuming messages from the document-processing queue.
        
        This method sets up a consumer for the document-processing queue
        and processes incoming messages with the provided callback function.
        
        Args:
            callback: Function to call when a message is received
            options: Optional consume options
        
        Raises:
            ServiceError: If consumption fails
        """
        if not self.is_connected:
            self.connect()
        
        # Use default options if not provided
        if options is None:
            options = ConsumeOptions.for_document_processing(
                prefetch_count=self.config.get('prefetch_count', 10)
            )
        
        try:
            def message_handler(ch, method, properties, body):
                try:
                    # Parse message body
                    message_str = body.decode('utf-8')
                    message = MessagePayload.from_json(message_str)
                    
                    # Extract headers from properties
                    headers = MessageHeaders(properties.headers or {})
                    
                    logger.info(f"Received message from queue: {options.queue}")
                    logger.debug(f"Message content: {message}")
                    
                    # Process message with callback
                    callback(message, headers)
                    
                    # Acknowledge message
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {str(e)}")
                    # Reject message with requeue=False to avoid infinite loop
                    ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    # Reject message with requeue=True to retry later
                    ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
            
            # Set prefetch count to limit number of unacknowledged messages
            self.channel.basic_qos(prefetch_count=options.prefetch_count)
            
            # Start consuming messages
            self.channel.basic_consume(
                queue=options.queue,
                on_message_callback=message_handler,
                auto_ack=options.no_ack,
                exclusive=options.exclusive,
                consumer_tag=options.consumer_tag,
                arguments=options.arguments
            )
            
            logger.info(f"Started consuming messages from queue: {options.queue}")
            logger.info("Waiting for messages. To exit press CTRL+C")
            
            # Start consuming (blocks until channel is closed)
            self.channel.start_consuming()
        except AMQPChannelError as e:
            logger.error(f"Channel error: {str(e)}")
            raise ServiceError(
                message="RabbitMQ channel error",
                context={"queue": options.queue},
                original_exception=e
            )
        except Exception as e:
            logger.error(f"Failed to consume messages: {str(e)}")
            raise ServiceError(
                message="Message consumption failed",
                context={"queue": options.queue},
                original_exception=e
            )
    
    def publish_message(self, 
                       message: Union[Dict[str, Any], MessagePayload], 
                       options: Optional[PublishOptions] = None) -> bool:
        """
        Publish a message to the data-extraction queue.
        
        This method publishes a message to the data-extraction queue for
        processing by the OCR Service.
        
        Args:
            message: Message payload to publish
            options: Optional publishing options
        
        Returns:
            bool: True if message was published successfully
        
        Raises:
            ServiceError: If publishing fails
        """
        if not self.is_connected:
            self.connect()
        
        # Use default options if not provided
        if options is None:
            options = PublishOptions.for_classification_result()
        
        try:
            # Convert message to MessagePayload if it's a dict
            if isinstance(message, dict) and not isinstance(message, MessagePayload):
                message = MessagePayload(message)
            
            # Prepare message properties
            properties = pika.BasicProperties(
                delivery_mode=options.headers.get('delivery_mode', DeliveryMode.PERSISTENT.value),
                content_type=options.headers.get('content_type', 'application/json'),
                content_encoding=options.headers.get('content_encoding', 'utf-8'),
                headers=dict(options.headers),
                message_id=options.headers.get('message_id'),
                correlation_id=options.headers.get('correlation_id'),
                reply_to=options.headers.get('reply_to'),
                expiration=options.headers.get('expiration'),
                timestamp=options.headers.get('timestamp'),
                app_id=options.headers.get('app_id', 'document-service'),
                priority=options.headers.get('priority', 0)
            )
            
            # Serialize message to JSON
            message_body = message.to_json().encode('utf-8')
            
            # Publish message to exchange with routing key
            self.channel.basic_publish(
                exchange=options.exchange,
                routing_key=options.routing_key,
                body=message_body,
                properties=properties,
                mandatory=options.mandatory
            )
            
            logger.info(f"Published message to exchange: {options.exchange} with routing key: {options.routing_key}")
            logger.debug(f"Message content: {message}")
            return True
        except AMQPChannelError as e:
            logger.error(f"Channel error during publish: {str(e)}")
            # Try to reconnect and retry once
            if self.reconnect():
                try:
                    # Retry publish after reconnection
                    self.channel.basic_publish(
                        exchange=options.exchange,
                        routing_key=options.routing_key,
                        body=message.to_json().encode('utf-8'),
                        properties=properties,
                        mandatory=options.mandatory
                    )
                    logger.info(f"Successfully republished message after reconnection")
                    return True
                except Exception as retry_e:
                    logger.error(f"Failed to republish message after reconnection: {str(retry_e)}")
                    raise MessagingError(
                        message="Message publishing failed after reconnection",
                        context={
                            "exchange": options.exchange,
                            "routing_key": options.routing_key
                        },
                        original_exception=retry_e
                    )
            else:
                raise MessagingError(
                    message="Failed to reconnect for message republishing",
                    context={
                        "exchange": options.exchange,
                        "routing_key": options.routing_key
                    },
                    original_exception=e
                )
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise MessagingError(
                message="Message publishing failed",
                context={
                    "exchange": options.exchange,
                    "routing_key": options.routing_key
                },
                original_exception=e
            )
    
    def publish_classification_result(self, message: MessagePayload, correlation_id: Optional[str] = None) -> bool:
        """
        Publish a classification result to the data-extraction queue.
        
        This is a convenience method that wraps publish_message with the appropriate
        options for publishing classification results.
        
        Args:
            message: Classification result payload
            correlation_id: Optional correlation ID for tracking related messages
            
        Returns:
            bool: True if message was published successfully
            
        Raises:
            ServiceError: If publishing fails
        """
        options = PublishOptions.for_classification_result(correlation_id=correlation_id)
        return self.publish_message(message, options)
    
    def reconnect(self) -> bool:
        """
        Reconnect to RabbitMQ after connection failure.
        
        This method implements an exponential backoff strategy for reconnection
        attempts to avoid overwhelming the RabbitMQ server during outages.
        
        Returns:
            bool: True if reconnection is successful
        """
        logger.info("Attempting to reconnect to RabbitMQ")
        self.disconnect()
        
        # Implement exponential backoff for reconnection attempts
        max_attempts = self.config.get('reconnect_attempts', 5)
        retry_delay = self.config.get('retry_delay', 1)
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Reconnection attempt {attempt}/{max_attempts}")
                self.connect()
                return True
            except ServiceError as e:
                logger.warning(f"Reconnection attempt {attempt} failed: {str(e)}")
                if attempt < max_attempts:
                    # Exponential backoff with jitter
                    delay = retry_delay * (2 ** (attempt - 1))
                    # Add jitter to avoid thundering herd problem
                    delay = delay * (0.8 + 0.4 * (time.time() % 1))
                    time.sleep(delay)
        
        logger.error(f"Failed to reconnect after {max_attempts} attempts")
        return False
    
    def __enter__(self):
        """
        Context manager entry point.
        
        Allows using the QueueService with a 'with' statement for automatic
        connection management.
        """
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit point.
        
        Ensures the RabbitMQ connection is properly closed when exiting
        the 'with' block, even if an exception occurs.
        """
        self.disconnect()