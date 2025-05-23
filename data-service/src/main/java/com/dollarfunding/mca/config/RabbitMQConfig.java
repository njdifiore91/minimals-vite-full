package com.dollarfunding.mca.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.connection.CachingConnectionFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.retry.backoff.ExponentialBackOffPolicy;
import org.springframework.retry.support.RetryTemplate;

import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;
import java.io.FileInputStream;
import java.security.KeyStore;

/**
 * Configuration class for RabbitMQ messaging in the MCA application.
 * 
 * This class configures the RabbitMQ connection factory, message converter,
 * exchanges, queues, and bindings required for asynchronous communication
 * between microservices. It enables secure messaging with TLS and client
 * certificate authentication.
 */
@Configuration
public class RabbitMQConfig {

    private static final Logger logger = LoggerFactory.getLogger(RabbitMQConfig.class);

    // RabbitMQ connection properties
    @Value("${spring.rabbitmq.host}")
    private String host;

    @Value("${spring.rabbitmq.port}")
    private int port;

    @Value("${spring.rabbitmq.username}")
    private String username;

    @Value("${spring.rabbitmq.password}")
    private String password;

    @Value("${spring.rabbitmq.virtual-host}")
    private String virtualHost;

    // SSL/TLS properties
    @Value("${spring.rabbitmq.ssl.enabled}")
    private boolean sslEnabled;

    @Value("${spring.rabbitmq.ssl.algorithm:TLSv1.3}")
    private String sslAlgorithm;

    @Value("${spring.rabbitmq.ssl.key-store:#{null}}")
    private String keyStorePath;

    @Value("${spring.rabbitmq.ssl.key-store-password:#{null}}")
    private String keyStorePassword;

    @Value("${spring.rabbitmq.ssl.trust-store:#{null}}")
    private String trustStorePath;

    @Value("${spring.rabbitmq.ssl.trust-store-password:#{null}}")
    private String trustStorePassword;

    // Exchange and queue properties
    @Value("${application.messaging.exchanges.documents.name}")
    private String documentsExchangeName;

    @Value("${application.messaging.exchanges.documents.type}")
    private String documentsExchangeType;

    @Value("${application.messaging.exchanges.documents.durable}")
    private boolean documentsExchangeDurable;

    @Value("${application.messaging.queues.document-processing.name}")
    private String documentProcessingQueueName;

    @Value("${application.messaging.queues.document-processing.durable}")
    private boolean documentProcessingQueueDurable;

    @Value("${application.messaging.queues.data-extraction.name}")
    private String dataExtractionQueueName;

    @Value("${application.messaging.queues.data-extraction.durable}")
    private boolean dataExtractionQueueDurable;

    @Value("${application.messaging.queues.notification.name}")
    private String notificationQueueName;

    @Value("${application.messaging.queues.notification.durable}")
    private boolean notificationQueueDurable;

    // Retry properties
    @Value("${spring.rabbitmq.template.retry.initial-interval}")
    private long retryInitialInterval;

    @Value("${spring.rabbitmq.template.retry.max-interval}")
    private long retryMaxInterval;

    @Value("${spring.rabbitmq.template.retry.multiplier}")
    private double retryMultiplier;

    @Value("${spring.rabbitmq.template.retry.max-attempts}")
    private int retryMaxAttempts;

    /**
     * Creates a connection factory for RabbitMQ with TLS and client certificate authentication if enabled.
     * 
     * @return the configured connection factory
     */
    @Bean
    public ConnectionFactory connectionFactory() {
        CachingConnectionFactory connectionFactory = new CachingConnectionFactory();
        connectionFactory.setHost(host);
        connectionFactory.setPort(port);
        connectionFactory.setUsername(username);
        connectionFactory.setPassword(password);
        connectionFactory.setVirtualHost(virtualHost);

        // Configure SSL/TLS if enabled
        if (sslEnabled) {
            try {
                // Set up SSL context with client certificate authentication
                SSLContext sslContext = SSLContext.getInstance(sslAlgorithm);
                
                // Set up key store for client certificate
                KeyStore keyStore = KeyStore.getInstance("PKCS12");
                try (FileInputStream keyStoreInputStream = new FileInputStream(keyStorePath)) {
                    keyStore.load(keyStoreInputStream, keyStorePassword.toCharArray());
                }
                KeyManagerFactory keyManagerFactory = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
                keyManagerFactory.init(keyStore, keyStorePassword.toCharArray());
                
                // Set up trust store for server certificate validation
                KeyStore trustStore = KeyStore.getInstance("JKS");
                try (FileInputStream trustStoreInputStream = new FileInputStream(trustStorePath)) {
                    trustStore.load(trustStoreInputStream, trustStorePassword.toCharArray());
                }
                TrustManagerFactory trustManagerFactory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
                trustManagerFactory.init(trustStore);
                
                // Initialize SSL context with key and trust managers
                sslContext.init(
                    keyManagerFactory.getKeyManagers(),
                    trustManagerFactory.getTrustManagers(),
                    null
                );
                
                // Apply SSL context to connection factory
                connectionFactory.getRabbitConnectionFactory().useSslProtocol(sslContext);
                
                logger.info("SSL/TLS configuration for RabbitMQ completed successfully");
            } catch (Exception e) {
                logger.error("Failed to configure SSL for RabbitMQ", e);
                throw new RuntimeException("Failed to configure SSL for RabbitMQ", e);
            }
        }

        return connectionFactory;
    }

    /**
     * Creates a RabbitMQ admin for managing exchanges and queues.
     * 
     * @param connectionFactory the RabbitMQ connection factory
     * @return the RabbitMQ admin
     */
    @Bean
    public RabbitAdmin rabbitAdmin(ConnectionFactory connectionFactory) {
        return new RabbitAdmin(connectionFactory);
    }

    /**
     * Creates a message converter for serializing and deserializing messages to/from JSON.
     * 
     * @return the JSON message converter
     */
    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    /**
     * Creates a retry template for handling failed message delivery.
     * 
     * @return the retry template
     */
    @Bean
    public RetryTemplate retryTemplate() {
        RetryTemplate retryTemplate = new RetryTemplate();
        
        ExponentialBackOffPolicy backOffPolicy = new ExponentialBackOffPolicy();
        backOffPolicy.setInitialInterval(retryInitialInterval);
        backOffPolicy.setMaxInterval(retryMaxInterval);
        backOffPolicy.setMultiplier(retryMultiplier);
        
        retryTemplate.setBackOffPolicy(backOffPolicy);
        retryTemplate.setRetryPolicy(new org.springframework.retry.policy.SimpleRetryPolicy(retryMaxAttempts));
        
        return retryTemplate;
    }

    /**
     * Creates a RabbitTemplate for sending messages to RabbitMQ.
     * 
     * @param connectionFactory the RabbitMQ connection factory
     * @param messageConverter the message converter
     * @param retryTemplate the retry template
     * @return the configured RabbitTemplate
     */
    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory, 
                                         MessageConverter messageConverter,
                                         RetryTemplate retryTemplate) {
        RabbitTemplate rabbitTemplate = new RabbitTemplate(connectionFactory);
        rabbitTemplate.setMessageConverter(messageConverter);
        rabbitTemplate.setRetryTemplate(retryTemplate);
        rabbitTemplate.setConfirmCallback((correlationData, ack, cause) -> {
            if (!ack) {
                // Log failed message delivery
                // In a production environment, you might want to store failed messages for later retry
                // or trigger an alert
                logger.error("Message delivery failed: {}", cause);
            }
        });
        return rabbitTemplate;
    }

    /**
     * Creates the 'mca.documents' fanout exchange.
     * 
     * @return the exchange
     */
    @Bean
    public Exchange documentsExchange() {
        return ExchangeBuilder
                .fanoutExchange(documentsExchangeName)
                .durable(documentsExchangeDurable)
                .build();
    }

    /**
     * Creates the 'document-processing' queue.
     * 
     * @return the queue
     */
    @Bean
    public Queue documentProcessingQueue() {
        return QueueBuilder
                .durable(documentProcessingQueueName)
                .build();
    }

    /**
     * Creates the 'data-extraction' queue.
     * 
     * @return the queue
     */
    @Bean
    public Queue dataExtractionQueue() {
        return QueueBuilder
                .durable(dataExtractionQueueName)
                .build();
    }

    /**
     * Creates the 'notification' queue.
     * 
     * @return the queue
     */
    @Bean
    public Queue notificationQueue() {
        return QueueBuilder
                .durable(notificationQueueName)
                .build();
    }

    /**
     * Creates a binding between the 'mca.documents' exchange and the 'document-processing' queue.
     * 
     * @param documentsExchange the documents exchange
     * @param documentProcessingQueue the document processing queue
     * @return the binding
     */
    @Bean
    public Binding documentProcessingBinding(Exchange documentsExchange, Queue documentProcessingQueue) {
        return BindingBuilder
                .bind(documentProcessingQueue)
                .to(documentsExchange)
                .with("") // Empty routing key for fanout exchange
                .noargs();
    }

    /**
     * Creates a binding between the 'mca.documents' exchange and the 'data-extraction' queue.
     * 
     * @param documentsExchange the documents exchange
     * @param dataExtractionQueue the data extraction queue
     * @return the binding
     */
    @Bean
    public Binding dataExtractionBinding(Exchange documentsExchange, Queue dataExtractionQueue) {
        return BindingBuilder
                .bind(dataExtractionQueue)
                .to(documentsExchange)
                .with("") // Empty routing key for fanout exchange
                .noargs();
    }

    /**
     * Creates a binding between the 'mca.documents' exchange and the 'notification' queue.
     * 
     * @param documentsExchange the documents exchange
     * @param notificationQueue the notification queue
     * @return the binding
     */
    @Bean
    public Binding notificationBinding(Exchange documentsExchange, Queue notificationQueue) {
        return BindingBuilder
                .bind(notificationQueue)
                .to(documentsExchange)
                .with("") // Empty routing key for fanout exchange
                .noargs();
    }
}