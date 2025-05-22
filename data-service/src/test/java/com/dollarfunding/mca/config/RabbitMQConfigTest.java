package com.dollarfunding.mca.config;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.amqp.core.*;
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
import org.springframework.boot.autoconfigure.amqp.RabbitProperties;
import org.springframework.retry.backoff.ExponentialBackOffPolicy;
import org.springframework.retry.policy.SimpleRetryPolicy;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.rabbitmq.client.impl.CredentialsProvider;

import java.time.Duration;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link RabbitMQConfig} class.
 * 
 * These tests verify the configuration of RabbitMQ messaging in the MCA application,
 * including connection factory with TLS, exchange and queue definitions, message converter setup,
 * and retry mechanism configuration for reliable asynchronous processing.
 */
public class RabbitMQConfigTest {

    private RabbitMQConfig rabbitMQConfig;
    
    @Mock
    private RabbitProperties rabbitProperties;
    
    @Mock
    private RabbitProperties.Ssl ssl;
    
    @Mock
    private RabbitProperties.Cache cache;
    
    @Mock
    private RabbitProperties.Cache.Channel channel;
    
    @Mock
    private RabbitProperties.Template template;
    
    @Mock
    private RabbitProperties.Template.Retry retry;
    
    @Mock
    private RabbitProperties.Listener listener;
    
    @Mock
    private RabbitProperties.Listener.Simple simple;
    
    @Mock
    private RabbitProperties.Listener.Simple.Retry listenerRetry;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
        rabbitMQConfig = new RabbitMQConfig();
        
        // Set default property values
        ReflectionTestUtils.setField(rabbitMQConfig, "documentsExchangeName", "mca.documents");
        ReflectionTestUtils.setField(rabbitMQConfig, "documentProcessingQueueName", "document-processing");
        ReflectionTestUtils.setField(rabbitMQConfig, "dataExtractionQueueName", "data-extraction");
        ReflectionTestUtils.setField(rabbitMQConfig, "notificationQueueName", "notification");
        ReflectionTestUtils.setField(rabbitMQConfig, "applicationName", "mca-data-service");
        
        // Configure RabbitProperties mock
        when(rabbitProperties.getHost()).thenReturn("rabbitmq.example.com");
        when(rabbitProperties.getPort()).thenReturn(5671); // TLS port
        when(rabbitProperties.getUsername()).thenReturn("mca-service");
        when(rabbitProperties.getPassword()).thenReturn("password");
        when(rabbitProperties.getVirtualHost()).thenReturn("/mca");
        when(rabbitProperties.getConnectionTimeout()).thenReturn(Duration.ofSeconds(30));
        
        // Configure SSL properties
        when(rabbitProperties.getSsl()).thenReturn(ssl);
        when(ssl.isEnabled()).thenReturn(true);
        when(ssl.getAlgorithm()).thenReturn("TLSv1.2");
        when(ssl.getKeyStore()).thenReturn("/path/to/keystore.p12");
        when(ssl.getKeyStorePassword()).thenReturn("keystorepass");
        when(ssl.getKeyStoreType()).thenReturn("PKCS12");
        when(ssl.getTrustStore()).thenReturn("/path/to/truststore.p12");
        when(ssl.getTrustStorePassword()).thenReturn("truststorepass");
        when(ssl.getTrustStoreType()).thenReturn("PKCS12");
        when(ssl.isVerifyHostname()).thenReturn(true);
        
        // Configure cache properties
        when(rabbitProperties.getCache()).thenReturn(cache);
        when(cache.getChannel()).thenReturn(channel);
        when(channel.getSize()).thenReturn(25);
        
        // Configure template properties
        when(rabbitProperties.getTemplate()).thenReturn(template);
        when(template.getRetry()).thenReturn(retry);
        when(retry.getInitialInterval()).thenReturn(Duration.ofMillis(1000));
        when(retry.getMaxInterval()).thenReturn(Duration.ofMillis(10000));
        when(retry.getMultiplier()).thenReturn(2.0);
        when(retry.getMaxAttempts()).thenReturn(3L);
        
        // Configure listener properties
        when(rabbitProperties.getListener()).thenReturn(listener);
        when(listener.getSimple()).thenReturn(simple);
        when(simple.getConcurrency()).thenReturn(5);
        when(simple.getMaxConcurrency()).thenReturn(10);
        when(simple.getPrefetch()).thenReturn(250);
        when(simple.getAcknowledgeMode()).thenReturn(AcknowledgeMode.AUTO);
        when(simple.getRetry()).thenReturn(listenerRetry);
        when(listenerRetry.isEnabled()).thenReturn(true);
    }

    @Test
    public void testConnectionFactory() {
        // When
        ConnectionFactory connectionFactory = rabbitMQConfig.connectionFactory(rabbitProperties);
        
        // Then
        assertNotNull(connectionFactory, "Connection factory should not be null");
        assertTrue(connectionFactory instanceof CachingConnectionFactory, "Connection factory should be a CachingConnectionFactory");
        
        CachingConnectionFactory cachingConnectionFactory = (CachingConnectionFactory) connectionFactory;
        assertEquals("rabbitmq.example.com", cachingConnectionFactory.getHost(), "Host should be set correctly");
        assertEquals(5671, cachingConnectionFactory.getPort(), "Port should be set correctly");
        assertEquals("mca-service", cachingConnectionFactory.getUsername(), "Username should be set correctly");
        assertEquals("/mca", cachingConnectionFactory.getVirtualHost(), "Virtual host should be set correctly");
        
        // Verify TLS configuration
        com.rabbitmq.client.ConnectionFactory rabbitConnectionFactory = cachingConnectionFactory.getRabbitConnectionFactory();
        assertTrue(cachingConnectionFactory.isUseSSL(), "SSL should be enabled");
        
        // Verify connection caching
        assertEquals(CachingConnectionFactory.CacheMode.CHANNEL, cachingConnectionFactory.getCacheMode(), 
                "Cache mode should be CHANNEL");
        assertEquals(25, cachingConnectionFactory.getChannelCacheSize(), "Channel cache size should be 25");
        
        // Verify connection timeout
        assertEquals(30000, cachingConnectionFactory.getConnectionTimeout(), "Connection timeout should be 30 seconds");
    }
    
    @Test
    public void testConnectionFactoryWithoutTLS() {
        // Given
        when(ssl.isEnabled()).thenReturn(false);
        
        // When
        ConnectionFactory connectionFactory = rabbitMQConfig.connectionFactory(rabbitProperties);
        
        // Then
        assertNotNull(connectionFactory, "Connection factory should not be null");
        assertTrue(connectionFactory instanceof CachingConnectionFactory, "Connection factory should be a CachingConnectionFactory");
        
        CachingConnectionFactory cachingConnectionFactory = (CachingConnectionFactory) connectionFactory;
        assertFalse(cachingConnectionFactory.isUseSSL(), "SSL should be disabled");
    }

    @Test
    public void testConnectionNameStrategy() {
        // When
        ConnectionNameStrategy strategy = rabbitMQConfig.connectionNameStrategy();
        
        // Then
        assertNotNull(strategy, "Connection name strategy should not be null");
        
        // Test the strategy
        String connectionName = strategy.obtainNewConnectionName(null);
        assertNotNull(connectionName, "Connection name should not be null");
        assertTrue(connectionName.startsWith("mca-data-service-"), 
                "Connection name should start with application name");
    }

    @Test
    public void testJsonMessageConverter() {
        // When
        MessageConverter converter = rabbitMQConfig.jsonMessageConverter();
        
        // Then
        assertNotNull(converter, "Message converter should not be null");
        assertTrue(converter instanceof Jackson2JsonMessageConverter, 
                "Message converter should be a Jackson2JsonMessageConverter");
        
        // Verify ObjectMapper configuration
        Jackson2JsonMessageConverter jsonConverter = (Jackson2JsonMessageConverter) converter;
        ObjectMapper objectMapper = (ObjectMapper) ReflectionTestUtils.getField(jsonConverter, "objectMapper");
        assertNotNull(objectMapper, "ObjectMapper should not be null");
        
        // Verify JavaTimeModule is registered
        boolean hasJavaTimeModule = objectMapper.getRegisteredModuleIds().stream()
                .anyMatch(id -> id.contains("JavaTimeModule"));
        assertTrue(hasJavaTimeModule, "ObjectMapper should have JavaTimeModule registered");
    }

    @Test
    public void testRetryTemplate() {
        // When
        RetryTemplate retryTemplate = rabbitMQConfig.retryTemplate(rabbitProperties);
        
        // Then
        assertNotNull(retryTemplate, "Retry template should not be null");
        
        // Verify backoff policy
        ExponentialBackOffPolicy backOffPolicy = (ExponentialBackOffPolicy) ReflectionTestUtils.getField(retryTemplate, "backOffPolicy");
        assertNotNull(backOffPolicy, "Backoff policy should not be null");
        assertEquals(1000, backOffPolicy.getInitialInterval(), "Initial interval should be 1000ms");
        assertEquals(2.0, backOffPolicy.getMultiplier(), "Multiplier should be 2.0");
        assertEquals(10000, backOffPolicy.getMaxInterval(), "Max interval should be 10000ms");
        
        // Verify retry policy
        SimpleRetryPolicy retryPolicy = (SimpleRetryPolicy) ReflectionTestUtils.getField(retryTemplate, "retryPolicy");
        assertNotNull(retryPolicy, "Retry policy should not be null");
        assertEquals(3, retryPolicy.getMaxAttempts(), "Max attempts should be 3");
    }

    @Test
    public void testRabbitTemplate() {
        // Given
        ConnectionFactory connectionFactory = mock(CachingConnectionFactory.class);
        MessageConverter messageConverter = mock(MessageConverter.class);
        RetryTemplate retryTemplate = mock(RetryTemplate.class);
        
        // When
        RabbitTemplate rabbitTemplate = rabbitMQConfig.rabbitTemplate(connectionFactory, messageConverter, retryTemplate);
        
        // Then
        assertNotNull(rabbitTemplate, "RabbitTemplate should not be null");
        assertSame(connectionFactory, rabbitTemplate.getConnectionFactory(), 
                "Connection factory should be set correctly");
        assertSame(messageConverter, rabbitTemplate.getMessageConverter(), 
                "Message converter should be set correctly");
        assertTrue(rabbitTemplate.isMandatory(), "Mandatory flag should be true");
        assertSame(retryTemplate, rabbitTemplate.getRetryTemplate(), 
                "Retry template should be set correctly");
        
        // Verify callback configuration
        assertNotNull(rabbitTemplate.getConfirmCallback(), "Confirm callback should be set");
        assertNotNull(rabbitTemplate.getReturnCallback(), "Return callback should be set");
        
        // Verify connection factory configuration
        verify(connectionFactory).setPublisherConfirmType(CachingConnectionFactory.ConfirmType.CORRELATED);
        verify(connectionFactory).setPublisherReturns(true);
    }

    @Test
    public void testAmqpAdmin() {
        // Given
        ConnectionFactory connectionFactory = mock(ConnectionFactory.class);
        
        // When
        AmqpAdmin amqpAdmin = rabbitMQConfig.amqpAdmin(connectionFactory);
        
        // Then
        assertNotNull(amqpAdmin, "AmqpAdmin should not be null");
        assertTrue(amqpAdmin instanceof RabbitAdmin, "AmqpAdmin should be a RabbitAdmin");
        
        RabbitAdmin rabbitAdmin = (RabbitAdmin) amqpAdmin;
        assertSame(connectionFactory, ReflectionTestUtils.getField(rabbitAdmin, "connectionFactory"), 
                "Connection factory should be set correctly");
    }

    @Test
    public void testDocumentsExchange() {
        // When
        FanoutExchange exchange = rabbitMQConfig.documentsExchange();
        
        // Then
        assertNotNull(exchange, "Documents exchange should not be null");
        assertEquals("mca.documents", exchange.getName(), "Exchange name should be 'mca.documents'");
        assertTrue(exchange.isDurable(), "Exchange should be durable");
        assertFalse(exchange.isAutoDelete(), "Exchange should not auto-delete");
    }

    @Test
    public void testDocumentProcessingQueue() {
        // When
        Queue queue = rabbitMQConfig.documentProcessingQueue();
        
        // Then
        assertNotNull(queue, "Document processing queue should not be null");
        assertEquals("document-processing", queue.getName(), "Queue name should be 'document-processing'");
        assertTrue(queue.isDurable(), "Queue should be durable");
        assertFalse(queue.isAutoDelete(), "Queue should not auto-delete");
        assertFalse(queue.isExclusive(), "Queue should not be exclusive");
        
        // Verify dead letter configuration
        Map<String, Object> arguments = queue.getArguments();
        assertNotNull(arguments, "Queue arguments should not be null");
        assertEquals("mca.dead-letter", arguments.get("x-dead-letter-exchange"), 
                "Dead letter exchange should be 'mca.dead-letter'");
    }

    @Test
    public void testDataExtractionQueue() {
        // When
        Queue queue = rabbitMQConfig.dataExtractionQueue();
        
        // Then
        assertNotNull(queue, "Data extraction queue should not be null");
        assertEquals("data-extraction", queue.getName(), "Queue name should be 'data-extraction'");
        assertTrue(queue.isDurable(), "Queue should be durable");
        assertFalse(queue.isAutoDelete(), "Queue should not auto-delete");
        assertFalse(queue.isExclusive(), "Queue should not be exclusive");
        
        // Verify dead letter configuration
        Map<String, Object> arguments = queue.getArguments();
        assertNotNull(arguments, "Queue arguments should not be null");
        assertEquals("mca.dead-letter", arguments.get("x-dead-letter-exchange"), 
                "Dead letter exchange should be 'mca.dead-letter'");
    }

    @Test
    public void testNotificationQueue() {
        // When
        Queue queue = rabbitMQConfig.notificationQueue();
        
        // Then
        assertNotNull(queue, "Notification queue should not be null");
        assertEquals("notification", queue.getName(), "Queue name should be 'notification'");
        assertTrue(queue.isDurable(), "Queue should be durable");
        assertFalse(queue.isAutoDelete(), "Queue should not auto-delete");
        assertFalse(queue.isExclusive(), "Queue should not be exclusive");
        
        // Verify dead letter configuration
        Map<String, Object> arguments = queue.getArguments();
        assertNotNull(arguments, "Queue arguments should not be null");
        assertEquals("mca.dead-letter", arguments.get("x-dead-letter-exchange"), 
                "Dead letter exchange should be 'mca.dead-letter'");
    }

    @Test
    public void testDocumentProcessingBinding() {
        // Given
        FanoutExchange exchange = new FanoutExchange("mca.documents");
        Queue queue = new Queue("document-processing");
        
        // When
        Binding binding = rabbitMQConfig.documentProcessingBinding(exchange, queue);
        
        // Then
        assertNotNull(binding, "Document processing binding should not be null");
        assertEquals("document-processing", binding.getDestination(), 
                "Binding destination should be 'document-processing'");
        assertEquals("mca.documents", binding.getExchange(), 
                "Binding exchange should be 'mca.documents'");
        assertEquals("", binding.getRoutingKey(), "Binding routing key should be empty for fanout exchange");
        assertEquals(Binding.DestinationType.QUEUE, binding.getDestinationType(), 
                "Binding destination type should be QUEUE");
    }

    @Test
    public void testDataExtractionBinding() {
        // Given
        FanoutExchange exchange = new FanoutExchange("mca.documents");
        Queue queue = new Queue("data-extraction");
        
        // When
        Binding binding = rabbitMQConfig.dataExtractionBinding(exchange, queue);
        
        // Then
        assertNotNull(binding, "Data extraction binding should not be null");
        assertEquals("data-extraction", binding.getDestination(), 
                "Binding destination should be 'data-extraction'");
        assertEquals("mca.documents", binding.getExchange(), 
                "Binding exchange should be 'mca.documents'");
        assertEquals("", binding.getRoutingKey(), "Binding routing key should be empty for fanout exchange");
        assertEquals(Binding.DestinationType.QUEUE, binding.getDestinationType(), 
                "Binding destination type should be QUEUE");
    }

    @Test
    public void testNotificationBinding() {
        // Given
        FanoutExchange exchange = new FanoutExchange("mca.documents");
        Queue queue = new Queue("notification");
        
        // When
        Binding binding = rabbitMQConfig.notificationBinding(exchange, queue);
        
        // Then
        assertNotNull(binding, "Notification binding should not be null");
        assertEquals("notification", binding.getDestination(), 
                "Binding destination should be 'notification'");
        assertEquals("mca.documents", binding.getExchange(), 
                "Binding exchange should be 'mca.documents'");
        assertEquals("", binding.getRoutingKey(), "Binding routing key should be empty for fanout exchange");
        assertEquals(Binding.DestinationType.QUEUE, binding.getDestinationType(), 
                "Binding destination type should be QUEUE");
    }

    @Test
    public void testDeadLetterExchange() {
        // When
        FanoutExchange exchange = rabbitMQConfig.deadLetterExchange();
        
        // Then
        assertNotNull(exchange, "Dead letter exchange should not be null");
        assertEquals("mca.dead-letter", exchange.getName(), "Exchange name should be 'mca.dead-letter'");
        assertTrue(exchange.isDurable(), "Exchange should be durable");
        assertFalse(exchange.isAutoDelete(), "Exchange should not auto-delete");
    }

    @Test
    public void testDeadLetterQueue() {
        // When
        Queue queue = rabbitMQConfig.deadLetterQueue();
        
        // Then
        assertNotNull(queue, "Dead letter queue should not be null");
        assertEquals("dead-letter-queue", queue.getName(), "Queue name should be 'dead-letter-queue'");
        assertTrue(queue.isDurable(), "Queue should be durable");
        assertFalse(queue.isAutoDelete(), "Queue should not auto-delete");
        assertFalse(queue.isExclusive(), "Queue should not be exclusive");
    }

    @Test
    public void testDeadLetterBinding() {
        // Given
        FanoutExchange exchange = new FanoutExchange("mca.dead-letter");
        Queue queue = new Queue("dead-letter-queue");
        
        // When
        Binding binding = rabbitMQConfig.deadLetterBinding(exchange, queue);
        
        // Then
        assertNotNull(binding, "Dead letter binding should not be null");
        assertEquals("dead-letter-queue", binding.getDestination(), 
                "Binding destination should be 'dead-letter-queue'");
        assertEquals("mca.dead-letter", binding.getExchange(), 
                "Binding exchange should be 'mca.dead-letter'");
        assertEquals("", binding.getRoutingKey(), "Binding routing key should be empty for fanout exchange");
        assertEquals(Binding.DestinationType.QUEUE, binding.getDestinationType(), 
                "Binding destination type should be QUEUE");
    }

    @Test
    public void testMessageRecoverer() {
        // Given
        RabbitTemplate rabbitTemplate = mock(RabbitTemplate.class);
        
        // When
        MessageRecoverer recoverer = rabbitMQConfig.messageRecoverer(rabbitTemplate);
        
        // Then
        assertNotNull(recoverer, "Message recoverer should not be null");
        assertTrue(recoverer instanceof RepublishMessageRecoverer, 
                "Message recoverer should be a RepublishMessageRecoverer");
        
        RepublishMessageRecoverer republishRecoverer = (RepublishMessageRecoverer) recoverer;
        assertEquals("mca.dead-letter", ReflectionTestUtils.getField(republishRecoverer, "errorExchangeName"), 
                "Error exchange name should be 'mca.dead-letter'");
        assertEquals("", ReflectionTestUtils.getField(republishRecoverer, "errorRoutingKey"), 
                "Error routing key should be empty");
        assertSame(rabbitTemplate, ReflectionTestUtils.getField(republishRecoverer, "errorTemplate"), 
                "Error template should be set correctly");
    }

    @Test
    public void testRabbitListenerContainerFactory() {
        // Given
        ConnectionFactory connectionFactory = mock(ConnectionFactory.class);
        MessageConverter messageConverter = mock(MessageConverter.class);
        MessageRecoverer messageRecoverer = mock(MessageRecoverer.class);
        RetryTemplate retryTemplate = mock(RetryTemplate.class);
        
        // Mock retry template creation
        doReturn(retryTemplate).when(rabbitProperties).getTemplate();
        
        // When
        SimpleRabbitListenerContainerFactory factory = rabbitMQConfig.rabbitListenerContainerFactory(
                connectionFactory, messageConverter, messageRecoverer, rabbitProperties);
        
        // Then
        assertNotNull(factory, "RabbitListenerContainerFactory should not be null");
        assertSame(connectionFactory, ReflectionTestUtils.getField(factory, "connectionFactory"), 
                "Connection factory should be set correctly");
        assertSame(messageConverter, ReflectionTestUtils.getField(factory, "messageConverter"), 
                "Message converter should be set correctly");
        
        // Verify concurrency settings
        assertEquals(5, factory.getConcurrentConsumers(), "Concurrent consumers should be 5");
        assertEquals(10, factory.getMaxConcurrentConsumers(), "Max concurrent consumers should be 10");
        
        // Verify prefetch count
        assertEquals(250, factory.getPrefetchCount(), "Prefetch count should be 250");
        
        // Verify acknowledgment mode
        assertEquals(AcknowledgeMode.AUTO, factory.getAcknowledgeMode(), 
                "Acknowledge mode should be AUTO");
        
        // Verify retry configuration
        assertNotNull(ReflectionTestUtils.getField(factory, "retryTemplate"), 
                "Retry template should be set");
        assertNotNull(ReflectionTestUtils.getField(factory, "recoveryCallback"), 
                "Recovery callback should be set");
        assertSame(messageRecoverer, ReflectionTestUtils.getField(factory, "messageRecoverer"), 
                "Message recoverer should be set correctly");
    }

    @Test
    public void testRabbitListenerContainerFactoryWithoutRetry() {
        // Given
        ConnectionFactory connectionFactory = mock(ConnectionFactory.class);
        MessageConverter messageConverter = mock(MessageConverter.class);
        MessageRecoverer messageRecoverer = mock(MessageRecoverer.class);
        
        // Disable retry
        when(listenerRetry.isEnabled()).thenReturn(false);
        
        // When
        SimpleRabbitListenerContainerFactory factory = rabbitMQConfig.rabbitListenerContainerFactory(
                connectionFactory, messageConverter, messageRecoverer, rabbitProperties);
        
        // Then
        assertNotNull(factory, "RabbitListenerContainerFactory should not be null");
        
        // Verify retry configuration is not set
        assertNull(ReflectionTestUtils.getField(factory, "retryTemplate"), 
                "Retry template should not be set");
        assertNull(ReflectionTestUtils.getField(factory, "recoveryCallback"), 
                "Recovery callback should not be set");
        assertNull(ReflectionTestUtils.getField(factory, "messageRecoverer"), 
                "Message recoverer should not be set");
    }
}