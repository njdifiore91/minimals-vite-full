package com.dollarfunding.mca.config;

import org.springframework.amqp.core.AmqpAdmin;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.FanoutExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.rabbit.connection.CachingConnectionFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.connection.ConnectionNameStrategy;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.rabbit.listener.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.retry.MessageRecoverer;
import org.springframework.amqp.rabbit.retry.RepublishMessageRecoverer;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.amqp.RabbitProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.retry.backoff.ExponentialBackOffPolicy;
import org.springframework.retry.policy.SimpleRetryPolicy;
import org.springframework.retry.support.RetryTemplate;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

import java.util.HashMap;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Configuration class for RabbitMQ messaging in the MCA application.
 * 
 * This class configures the RabbitMQ connection factory, message converter,
 * exchanges, queues, and bindings required for asynchronous communication
 * between microservices. It enables TLS with client certificate authentication
 * and configures retry mechanisms for reliable message delivery.
 */
@Configuration
@EnableConfigurationProperties(RabbitProperties.class)
public class RabbitMQConfig {

    private static final Logger log = LoggerFactory.getLogger(RabbitMQConfig.class);

    @Value("${application.messaging.exchanges.documents.name:mca.documents}")
    private String documentsExchangeName;
    
    @Value("${application.messaging.queues.document-processing.name:document-processing}")
    private String documentProcessingQueueName;
    
    @Value("${application.messaging.queues.data-extraction.name:data-extraction}")
    private String dataExtractionQueueName;
    
    @Value("${application.messaging.queues.notification.name:notification}")
    private String notificationQueueName;
    
    @Value("${spring.application.name:mca-data-service}")
    private String applicationName;

    /**
     * Creates a connection factory for RabbitMQ with TLS support.
     * 
     * @param rabbitProperties The RabbitMQ properties from application.yml
     * @return A configured connection factory
     */
    @Bean
    public ConnectionFactory connectionFactory(RabbitProperties rabbitProperties) {
        log.info("Configuring RabbitMQ connection factory with host={}, port={}, virtualHost={}", 
                rabbitProperties.getHost(), rabbitProperties.getPort(), rabbitProperties.getVirtualHost());
        
        CachingConnectionFactory connectionFactory = new CachingConnectionFactory();
        connectionFactory.setHost(rabbitProperties.getHost());
        connectionFactory.setPort(rabbitProperties.getPort());
        connectionFactory.setUsername(rabbitProperties.getUsername());
        connectionFactory.setPassword(rabbitProperties.getPassword());
        connectionFactory.setVirtualHost(rabbitProperties.getVirtualHost());
        
        // Configure connection caching
        connectionFactory.setCacheMode(CachingConnectionFactory.CacheMode.CHANNEL);
        connectionFactory.setChannelCacheSize(rabbitProperties.getCache().getChannel().getSize());
        
        // Set connection name for better identification in RabbitMQ management UI
        connectionFactory.setConnectionNameStrategy(connectionNameStrategy());
        
        // Configure TLS if enabled
        if (rabbitProperties.getSsl().isEnabled()) {
            log.info("Enabling TLS for RabbitMQ connection with algorithm={}", 
                    rabbitProperties.getSsl().getAlgorithm());
            connectionFactory.setUseSSL(true);
            connectionFactory.getRabbitConnectionFactory().useSslProtocol();
            
            // Configure SSL properties if provided
            if (rabbitProperties.getSsl().getKeyStore() != null && 
                !rabbitProperties.getSsl().getKeyStore().isEmpty()) {
                connectionFactory.getRabbitConnectionFactory().setKeyStore(
                    rabbitProperties.getSsl().getKeyStore());
                connectionFactory.getRabbitConnectionFactory().setKeyStorePassphrase(
                    rabbitProperties.getSsl().getKeyStorePassword());
                connectionFactory.getRabbitConnectionFactory().setKeyStoreType(
                    rabbitProperties.getSsl().getKeyStoreType());
            }
            
            if (rabbitProperties.getSsl().getTrustStore() != null && 
                !rabbitProperties.getSsl().getTrustStore().isEmpty()) {
                connectionFactory.getRabbitConnectionFactory().setTrustStore(
                    rabbitProperties.getSsl().getTrustStore());
                connectionFactory.getRabbitConnectionFactory().setTrustStorePassphrase(
                    rabbitProperties.getSsl().getTrustStorePassword());
                connectionFactory.getRabbitConnectionFactory().setTrustStoreType(
                    rabbitProperties.getSsl().getTrustStoreType());
            }
            
            // Set TLS protocol version if specified
            if (rabbitProperties.getSsl().getAlgorithm() != null) {
                connectionFactory.getRabbitConnectionFactory().setSslAlgorithm(
                    rabbitProperties.getSsl().getAlgorithm());
            }
            
            // Configure server certificate validation
            connectionFactory.getRabbitConnectionFactory().setVerifyHostname(
                rabbitProperties.getSsl().isVerifyHostname());
        }
        
        // Configure connection timeout
        connectionFactory.setConnectionTimeout(rabbitProperties.getConnectionTimeout().toMillis());
        
        return connectionFactory;
    }
    
    /**
     * Creates a connection name strategy to identify connections in RabbitMQ management UI.
     * 
     * @return A connection name strategy
     */
    @Bean
    public ConnectionNameStrategy connectionNameStrategy() {
        return connectionFactory -> applicationName + "-" + System.currentTimeMillis();
    }

    /**
     * Creates a message converter for serializing/deserializing messages to/from JSON.
     * 
     * @return A Jackson2JsonMessageConverter
     */
    @Bean
    public MessageConverter jsonMessageConverter() {
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
        return new Jackson2JsonMessageConverter(objectMapper);
    }

    /**
     * Creates a retry template for message publishing retries.
     * 
     * @param rabbitProperties The RabbitMQ properties from application.yml
     * @return A configured retry template
     */
    @Bean
    public RetryTemplate retryTemplate(RabbitProperties rabbitProperties) {
        RetryTemplate retryTemplate = new RetryTemplate();
        
        // Configure exponential backoff policy
        ExponentialBackOffPolicy backOffPolicy = new ExponentialBackOffPolicy();
        backOffPolicy.setInitialInterval(rabbitProperties.getTemplate().getRetry().getInitialInterval().toMillis());
        backOffPolicy.setMultiplier(rabbitProperties.getTemplate().getRetry().getMultiplier());
        backOffPolicy.setMaxInterval(rabbitProperties.getTemplate().getRetry().getMaxInterval().toMillis());
        retryTemplate.setBackOffPolicy(backOffPolicy);
        
        // Configure retry policy
        SimpleRetryPolicy retryPolicy = new SimpleRetryPolicy();
        retryPolicy.setMaxAttempts((int) rabbitProperties.getTemplate().getRetry().getMaxAttempts());
        retryTemplate.setRetryPolicy(retryPolicy);
        
        return retryTemplate;
    }

    /**
     * Creates a RabbitTemplate for sending messages to RabbitMQ.
     * 
     * @param connectionFactory The RabbitMQ connection factory
     * @param messageConverter The message converter for serialization/deserialization
     * @param retryTemplate The retry template for message publishing retries
     * @return A configured RabbitTemplate
     */
    @Bean
    public RabbitTemplate rabbitTemplate(
            ConnectionFactory connectionFactory,
            MessageConverter messageConverter,
            RetryTemplate retryTemplate) {
        RabbitTemplate rabbitTemplate = new RabbitTemplate(connectionFactory);
        rabbitTemplate.setMessageConverter(messageConverter);
        
        // Enable publisher confirms and returns
        connectionFactory.setPublisherConfirmType(CachingConnectionFactory.ConfirmType.CORRELATED);
        connectionFactory.setPublisherReturns(true);
        rabbitTemplate.setMandatory(true);
        
        // Enable publisher confirms and returns for reliable messaging
        rabbitTemplate.setConfirmCallback((correlationData, ack, cause) -> {
            if (!ack) {
                // Log failed message publishing
                if (correlationData != null) {
                    // Use SLF4J logger instead of System.err
                    log.error("Message publishing failed for correlation id {}: {}", 
                            correlationData.getId(), cause);
                } else {
                    log.error("Message publishing failed: {}", cause);
                }
                // This could be enhanced to store failed messages for later retry
                // or to trigger alerts
            }
        });
        
        rabbitTemplate.setReturnCallback((message, replyCode, replyText, exchange, routingKey) -> {
            // Log returned messages (messages that couldn't be routed)
            log.warn("Message returned: exchange={}, routingKey={}, replyCode={}, replyText={}", 
                    exchange, routingKey, replyCode, replyText);
        });
        
        // Set retry template if retry is enabled
        rabbitTemplate.setRetryTemplate(retryTemplate);
        
        return rabbitTemplate;
    }

    /**
     * Creates an AmqpAdmin for managing RabbitMQ objects (exchanges, queues, bindings).
     * 
     * @param connectionFactory The RabbitMQ connection factory
     * @return A configured RabbitAdmin
     */
    @Bean
    public AmqpAdmin amqpAdmin(ConnectionFactory connectionFactory) {
        return new RabbitAdmin(connectionFactory);
    }

    /**
     * Creates the documents fanout exchange.
     * 
     * @return A configured FanoutExchange
     */
    @Bean
    public FanoutExchange documentsExchange() {
        log.info("Creating fanout exchange: {}", documentsExchangeName);
        return new FanoutExchange(documentsExchangeName, true, false);
    }

    /**
     * Creates the document processing queue.
     * 
     * @return A configured Queue
     */
    @Bean
    public Queue documentProcessingQueue() {
        log.info("Creating durable queue with dead letter configuration: {}", documentProcessingQueueName);
        Map<String, Object> args = new HashMap<>();
        args.put("x-dead-letter-exchange", "mca.dead-letter");
        return new Queue(documentProcessingQueueName, true, false, false, args);
    }

    /**
     * Creates the data extraction queue.
     * 
     * @return A configured Queue
     */
    @Bean
    public Queue dataExtractionQueue() {
        log.info("Creating durable queue with dead letter configuration: {}", dataExtractionQueueName);
        Map<String, Object> args = new HashMap<>();
        args.put("x-dead-letter-exchange", "mca.dead-letter");
        return new Queue(dataExtractionQueueName, true, false, false, args);
    }

    /**
     * Creates the notification queue.
     * 
     * @return A configured Queue
     */
    @Bean
    public Queue notificationQueue() {
        log.info("Creating durable queue with dead letter configuration: {}", notificationQueueName);
        Map<String, Object> args = new HashMap<>();
        args.put("x-dead-letter-exchange", "mca.dead-letter");
        return new Queue(notificationQueueName, true, false, false, args);
    }

    /**
     * Creates a binding between the documents exchange and the document processing queue.
     * 
     * @param documentsExchange The documents exchange
     * @param documentProcessingQueue The document processing queue
     * @return A configured Binding
     */
    @Bean
    public Binding documentProcessingBinding(
            @Qualifier("documentsExchange") FanoutExchange documentsExchange,
            @Qualifier("documentProcessingQueue") Queue documentProcessingQueue) {
        log.info("Creating binding between exchange {} and queue {}", 
                documentsExchange.getName(), documentProcessingQueue.getName());
        return BindingBuilder.bind(documentProcessingQueue).to(documentsExchange);
    }

    /**
     * Creates a binding between the documents exchange and the data extraction queue.
     * 
     * @param documentsExchange The documents exchange
     * @param dataExtractionQueue The data extraction queue
     * @return A configured Binding
     */
    @Bean
    public Binding dataExtractionBinding(
            @Qualifier("documentsExchange") FanoutExchange documentsExchange,
            @Qualifier("dataExtractionQueue") Queue dataExtractionQueue) {
        log.info("Creating binding between exchange {} and queue {}", 
                documentsExchange.getName(), dataExtractionQueue.getName());
        return BindingBuilder.bind(dataExtractionQueue).to(documentsExchange);
    }

    /**
     * Creates a binding between the documents exchange and the notification queue.
     * 
     * @param documentsExchange The documents exchange
     * @param notificationQueue The notification queue
     * @return A configured Binding
     */
    @Bean
    public Binding notificationBinding(
            @Qualifier("documentsExchange") FanoutExchange documentsExchange,
            @Qualifier("notificationQueue") Queue notificationQueue) {
        log.info("Creating binding between exchange {} and queue {}", 
                documentsExchange.getName(), notificationQueue.getName());
        return BindingBuilder.bind(notificationQueue).to(documentsExchange);
    }
    
    /**
     * Creates a dead letter exchange for handling failed messages.
     * 
     * @return A configured FanoutExchange for dead letters
     */
    @Bean
    public FanoutExchange deadLetterExchange() {
        String exchangeName = "mca.dead-letter";
        log.info("Creating dead letter exchange: {}", exchangeName);
        return new FanoutExchange(exchangeName, true, false);
    }
    
    /**
     * Creates a dead letter queue for handling failed messages.
     * 
     * @return A configured Queue for dead letters
     */
    @Bean
    public Queue deadLetterQueue() {
        String queueName = "dead-letter-queue";
        log.info("Creating dead letter queue: {}", queueName);
        return new Queue(queueName, true);
    }
    
    /**
     * Creates a binding between the dead letter exchange and the dead letter queue.
     * 
     * @param deadLetterExchange The dead letter exchange
     * @param deadLetterQueue The dead letter queue
     * @return A configured Binding
     */
    @Bean
    public Binding deadLetterBinding(
            @Qualifier("deadLetterExchange") FanoutExchange deadLetterExchange,
            @Qualifier("deadLetterQueue") Queue deadLetterQueue) {
        log.info("Creating binding between exchange {} and queue {}", 
                deadLetterExchange.getName(), deadLetterQueue.getName());
        return BindingBuilder.bind(deadLetterQueue).to(deadLetterExchange);
    }
    
    /**
     * Creates a message recoverer that republishes failed messages to the dead letter exchange.
     * 
     * @param rabbitTemplate The RabbitTemplate for publishing messages
     * @return A configured MessageRecoverer
     */
    @Bean
    public MessageRecoverer messageRecoverer(RabbitTemplate rabbitTemplate) {
        return new RepublishMessageRecoverer(rabbitTemplate, "mca.dead-letter", "");
    }
    
    /**
     * Creates a SimpleRabbitListenerContainerFactory with retry capabilities.
     * 
     * @param connectionFactory The RabbitMQ connection factory
     * @param messageConverter The message converter for serialization/deserialization
     * @param messageRecoverer The message recoverer for handling failed messages
     * @param rabbitProperties The RabbitMQ properties from application.yml
     * @return A configured SimpleRabbitListenerContainerFactory
     */
    @Bean
    public SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            ConnectionFactory connectionFactory,
            MessageConverter messageConverter,
            MessageRecoverer messageRecoverer,
            RabbitProperties rabbitProperties) {
        
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(messageConverter);
        
        // Configure concurrency
        factory.setConcurrentConsumers(rabbitProperties.getListener().getSimple().getConcurrency());
        factory.setMaxConcurrentConsumers(rabbitProperties.getListener().getSimple().getMaxConcurrency());
        
        // Configure prefetch count
        factory.setPrefetchCount(rabbitProperties.getListener().getSimple().getPrefetch());
        
        // Configure acknowledgment mode
        factory.setAcknowledgeMode(rabbitProperties.getListener().getSimple().getAcknowledgeMode());
        
        // Configure retry
        if (rabbitProperties.getListener().getSimple().getRetry().isEnabled()) {
            factory.setRetryTemplate(retryTemplate(rabbitProperties));
            factory.setRecoveryCallback(context -> {
                Throwable throwable = context.getLastThrowable();
                log.error("Failed to process message after multiple attempts", throwable);
                return null;
            });
            factory.setMessageRecoverer(messageRecoverer);
        }
        
        log.info("Configured RabbitMQ listener container factory with concurrency={}/{}, prefetch={}, retry={}",
                rabbitProperties.getListener().getSimple().getConcurrency(),
                rabbitProperties.getListener().getSimple().getMaxConcurrency(),
                rabbitProperties.getListener().getSimple().getPrefetch(),
                rabbitProperties.getListener().getSimple().getRetry().isEnabled());
        
        return factory;
    }
}