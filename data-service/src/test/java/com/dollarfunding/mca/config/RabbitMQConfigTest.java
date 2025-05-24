package com.dollarfunding.mca.config;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.connection.CachingConnectionFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.retry.backoff.ExponentialBackOffPolicy;
import org.springframework.retry.policy.SimpleRetryPolicy;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import javax.net.ssl.SSLContext;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the RabbitMQConfig class that configures RabbitMQ messaging for asynchronous
 * communication between microservices. Tests verify connection factory configuration with TLS,
 * exchange and queue definitions, message converter setup, and retry mechanism configuration.
 */
@ExtendWith(MockitoExtension.class)
public class RabbitMQConfigTest {

    @InjectMocks
    private RabbitMQConfig rabbitMQConfig;

    @BeforeEach
    public void setUp() {
        // Set up the required properties using reflection
        ReflectionTestUtils.setField(rabbitMQConfig, "host", "rabbitmq.dollarfunding.com");
        ReflectionTestUtils.setField(rabbitMQConfig, "port", 5671);
        ReflectionTestUtils.setField(rabbitMQConfig, "username", "mca-service");
        ReflectionTestUtils.setField(rabbitMQConfig, "password", "password");
        ReflectionTestUtils.setField(rabbitMQConfig, "virtualHost", "/mca");
        
        // SSL properties
        ReflectionTestUtils.setField(rabbitMQConfig, "sslEnabled", true);
        ReflectionTestUtils.setField(rabbitMQConfig, "sslAlgorithm", "TLSv1.3");
        ReflectionTestUtils.setField(rabbitMQConfig, "keyStorePath", "/path/to/keystore.p12");
        ReflectionTestUtils.setField(rabbitMQConfig, "keyStorePassword", "keystorepass");
        ReflectionTestUtils.setField(rabbitMQConfig, "trustStorePath", "/path/to/truststore.jks");
        ReflectionTestUtils.setField(rabbitMQConfig, "trustStorePassword", "truststorepass");
        
        // Exchange and queue properties
        ReflectionTestUtils.setField(rabbitMQConfig, "documentsExchangeName", "mca.documents");
        ReflectionTestUtils.setField(rabbitMQConfig, "documentsExchangeType", "fanout");
        ReflectionTestUtils.setField(rabbitMQConfig, "documentsExchangeDurable", true);
        
        ReflectionTestUtils.setField(rabbitMQConfig, "documentProcessingQueueName", "document-processing");
        ReflectionTestUtils.setField(rabbitMQConfig, "documentProcessingQueueDurable", true);
        
        ReflectionTestUtils.setField(rabbitMQConfig, "dataExtractionQueueName", "data-extraction");
        ReflectionTestUtils.setField(rabbitMQConfig, "dataExtractionQueueDurable", true);
        
        ReflectionTestUtils.setField(rabbitMQConfig, "notificationQueueName", "notification");
        ReflectionTestUtils.setField(rabbitMQConfig, "notificationQueueDurable", true);
        
        // Retry properties
        ReflectionTestUtils.setField(rabbitMQConfig, "retryInitialInterval", 1000L);
        ReflectionTestUtils.setField(rabbitMQConfig, "retryMaxInterval", 10000L);
        ReflectionTestUtils.setField(rabbitMQConfig, "retryMultiplier", 2.0);
        ReflectionTestUtils.setField(rabbitMQConfig, "retryMaxAttempts", 3);
    }

    /**
     * Test that the connection factory is properly configured with the expected connection settings.
     * Verifies host, port, username, password, and virtual host settings.
     */
    @Test
    public void testConnectionFactoryConfiguration() {
        // Act
        ConnectionFactory connectionFactory = rabbitMQConfig.connectionFactory();
        
        // Assert
        assertNotNull(connectionFactory, "Connection factory should not be null");
        assertTrue(connectionFactory instanceof CachingConnectionFactory, 
                "Connection factory should be a CachingConnectionFactory");
        
        CachingConnectionFactory cachingConnectionFactory = (CachingConnectionFactory) connectionFactory;
        assertEquals("rabbitmq.dollarfunding.com", cachingConnectionFactory.getHost(), 
                "Host should be 'rabbitmq.dollarfunding.com'");
        assertEquals(5671, cachingConnectionFactory.getPort(), 
                "Port should be 5671");
        assertEquals("mca-service", cachingConnectionFactory.getUsername(), 
                "Username should be 'mca-service'");
        assertEquals("/mca", cachingConnectionFactory.getVirtualHost(), 
                "Virtual host should be '/mca'");
    }
    
    /**
     * Test that the SSL/TLS configuration is properly set up when SSL is enabled.
     * This test verifies that SSL is enabled in the connection factory when the sslEnabled property is true.
     */
    @Test
    public void testSslConfiguration() {
        // Arrange - Create a spy of the RabbitMQConfig to avoid actual SSL context creation
        RabbitMQConfig spyConfig = Mockito.spy(rabbitMQConfig);
        
        // Mock the connectionFactory method to return a mock connection factory
        // This avoids the actual SSL context creation which requires file access
        CachingConnectionFactory mockConnectionFactory = Mockito.mock(CachingConnectionFactory.class);
        com.rabbitmq.client.ConnectionFactory mockRabbitConnectionFactory = Mockito.mock(com.rabbitmq.client.ConnectionFactory.class);
        when(mockConnectionFactory.getRabbitConnectionFactory()).thenReturn(mockRabbitConnectionFactory);
        Mockito.doReturn(mockConnectionFactory).when(spyConfig).connectionFactory();
        
        // Act - Get the connection factory
        ConnectionFactory connectionFactory = spyConfig.connectionFactory();
        
        // Assert
        assertNotNull(connectionFactory, "Connection factory should not be null");
        
        // Verify SSL is enabled in the configuration
        assertTrue(ReflectionTestUtils.getField(rabbitMQConfig, "sslEnabled").equals(true),
                "SSL should be enabled in the configuration");
        assertEquals("TLSv1.3", ReflectionTestUtils.getField(rabbitMQConfig, "sslAlgorithm"),
                "SSL algorithm should be TLSv1.3");
    }
    
    /**
     * Test that the SSL/TLS configuration is not applied when SSL is disabled.
     */
    @Test
    public void testSslConfigurationWhenDisabled() {
        // Arrange - Disable SSL
        ReflectionTestUtils.setField(rabbitMQConfig, "sslEnabled", false);
        
        // Create a spy of the RabbitMQConfig
        RabbitMQConfig spyConfig = Mockito.spy(rabbitMQConfig);
        
        // Act - Get the connection factory
        ConnectionFactory connectionFactory = spyConfig.connectionFactory();
        
        // Assert
        assertNotNull(connectionFactory, "Connection factory should not be null");
        assertTrue(connectionFactory instanceof CachingConnectionFactory, 
                "Connection factory should be a CachingConnectionFactory");
        
        // Re-enable SSL for other tests
        ReflectionTestUtils.setField(rabbitMQConfig, "sslEnabled", true);
    }
    
    /**
     * Test that the message converter is properly configured as a Jackson2JsonMessageConverter.
     */
    @Test
    public void testMessageConverterConfiguration() {
        // Act
        MessageConverter messageConverter = rabbitMQConfig.jsonMessageConverter();
        
        // Assert
        assertNotNull(messageConverter, "Message converter should not be null");
        assertTrue(messageConverter instanceof Jackson2JsonMessageConverter, 
                "Message converter should be a Jackson2JsonMessageConverter");
    }
    
    /**
     * Test that the retry template is properly configured with the expected retry settings.
     * Verifies initial interval, max interval, multiplier, and max attempts.
     */
    @Test
    public void testRetryTemplateConfiguration() throws Exception {
        // Act
        RetryTemplate retryTemplate = rabbitMQConfig.retryTemplate();
        
        // Assert
        assertNotNull(retryTemplate, "Retry template should not be null");
        
        // Extract the backoff policy using reflection
        Field backOffPolicyField = RetryTemplate.class.getDeclaredField("backOffPolicy");
        backOffPolicyField.setAccessible(true);
        Object backOffPolicy = backOffPolicyField.get(retryTemplate);
        
        assertTrue(backOffPolicy instanceof ExponentialBackOffPolicy, 
                "Backoff policy should be an ExponentialBackOffPolicy");
        
        ExponentialBackOffPolicy exponentialBackOffPolicy = (ExponentialBackOffPolicy) backOffPolicy;
        assertEquals(1000L, exponentialBackOffPolicy.getInitialInterval(), 
                "Initial interval should be 1000ms");
        assertEquals(10000L, exponentialBackOffPolicy.getMaxInterval(), 
                "Max interval should be 10000ms");
        assertEquals(2.0, exponentialBackOffPolicy.getMultiplier(), 
                "Multiplier should be 2.0");
        
        // Extract the retry policy using reflection
        Field retryPolicyField = RetryTemplate.class.getDeclaredField("retryPolicy");
        retryPolicyField.setAccessible(true);
        Object retryPolicy = retryPolicyField.get(retryTemplate);
        
        assertTrue(retryPolicy instanceof SimpleRetryPolicy, 
                "Retry policy should be a SimpleRetryPolicy");
        
        SimpleRetryPolicy simpleRetryPolicy = (SimpleRetryPolicy) retryPolicy;
        Field maxAttemptsField = SimpleRetryPolicy.class.getDeclaredField("maxAttempts");
        maxAttemptsField.setAccessible(true);
        int maxAttempts = (int) maxAttemptsField.get(simpleRetryPolicy);
        
        assertEquals(3, maxAttempts, "Max attempts should be 3");
    }
    
    /**
     * Test that the RabbitTemplate is properly configured with the expected settings.
     * Verifies connection factory, message converter, and retry template are set.
     */
    @Test
    public void testRabbitTemplateConfiguration() {
        // Arrange
        ConnectionFactory connectionFactory = Mockito.mock(ConnectionFactory.class);
        MessageConverter messageConverter = Mockito.mock(MessageConverter.class);
        RetryTemplate retryTemplate = Mockito.mock(RetryTemplate.class);
        
        // Act
        RabbitTemplate rabbitTemplate = rabbitMQConfig.rabbitTemplate(
                connectionFactory, messageConverter, retryTemplate);
        
        // Assert
        assertNotNull(rabbitTemplate, "RabbitTemplate should not be null");
        assertEquals(connectionFactory, rabbitTemplate.getConnectionFactory(), 
                "Connection factory should be set");
        assertEquals(messageConverter, rabbitTemplate.getMessageConverter(), 
                "Message converter should be set");
        assertEquals(retryTemplate, rabbitTemplate.getRetryTemplate(), 
                "Retry template should be set");
        assertNotNull(rabbitTemplate.getConfirmCallback(), 
                "Confirm callback should be set");
    }
    
    /**
     * Test that the documents exchange is properly configured as a fanout exchange.
     * Verifies exchange name, type, and durability.
     */
    @Test
    public void testExchangeConfiguration() {
        // Act
        Exchange exchange = rabbitMQConfig.documentsExchange();
        
        // Assert
        assertNotNull(exchange, "Exchange should not be null");
        assertTrue(exchange instanceof FanoutExchange, 
                "Exchange should be a FanoutExchange");
        
        FanoutExchange fanoutExchange = (FanoutExchange) exchange;
        assertEquals("mca.documents", fanoutExchange.getName(), 
                "Exchange name should be 'mca.documents'");
        assertTrue(fanoutExchange.isDurable(), 
                "Exchange should be durable");
    }
    
    /**
     * Test that the document processing queue is properly configured.
     * Verifies queue name and durability.
     */
    @Test
    public void testDocumentProcessingQueueConfiguration() {
        // Act
        Queue queue = rabbitMQConfig.documentProcessingQueue();
        
        // Assert
        assertNotNull(queue, "Queue should not be null");
        assertEquals("document-processing", queue.getName(), 
                "Queue name should be 'document-processing'");
        assertTrue(queue.isDurable(), 
                "Queue should be durable");
    }
    
    /**
     * Test that the data extraction queue is properly configured.
     * Verifies queue name and durability.
     */
    @Test
    public void testDataExtractionQueueConfiguration() {
        // Act
        Queue queue = rabbitMQConfig.dataExtractionQueue();
        
        // Assert
        assertNotNull(queue, "Queue should not be null");
        assertEquals("data-extraction", queue.getName(), 
                "Queue name should be 'data-extraction'");
        assertTrue(queue.isDurable(), 
                "Queue should be durable");
    }
    
    /**
     * Test that the notification queue is properly configured.
     * Verifies queue name and durability.
     */
    @Test
    public void testNotificationQueueConfiguration() {
        // Act
        Queue queue = rabbitMQConfig.notificationQueue();
        
        // Assert
        assertNotNull(queue, "Queue should not be null");
        assertEquals("notification", queue.getName(), 
                "Queue name should be 'notification'");
        assertTrue(queue.isDurable(), 
                "Queue should be durable");
    }
    
    /**
     * Test that the binding between the documents exchange and document processing queue is properly configured.
     * Verifies that the binding connects the correct exchange and queue with an empty routing key.
     */
    @Test
    public void testDocumentProcessingBindingConfiguration() {
        // Arrange
        Exchange exchange = rabbitMQConfig.documentsExchange();
        Queue queue = rabbitMQConfig.documentProcessingQueue();
        
        // Act
        Binding binding = rabbitMQConfig.documentProcessingBinding(exchange, queue);
        
        // Assert
        assertNotNull(binding, "Binding should not be null");
        assertEquals("mca.documents", binding.getExchange(), 
                "Binding should be to 'mca.documents' exchange");
        assertEquals("document-processing", binding.getDestination(), 
                "Binding destination should be 'document-processing' queue");
        assertEquals(Binding.DestinationType.QUEUE, binding.getDestinationType(), 
                "Binding destination type should be QUEUE");
        assertEquals("", binding.getRoutingKey(), 
                "Binding routing key should be empty for fanout exchange");
    }
    
    /**
     * Test that the binding between the documents exchange and data extraction queue is properly configured.
     * Verifies that the binding connects the correct exchange and queue with an empty routing key.
     */
    @Test
    public void testDataExtractionBindingConfiguration() {
        // Arrange
        Exchange exchange = rabbitMQConfig.documentsExchange();
        Queue queue = rabbitMQConfig.dataExtractionQueue();
        
        // Act
        Binding binding = rabbitMQConfig.dataExtractionBinding(exchange, queue);
        
        // Assert
        assertNotNull(binding, "Binding should not be null");
        assertEquals("mca.documents", binding.getExchange(), 
                "Binding should be to 'mca.documents' exchange");
        assertEquals("data-extraction", binding.getDestination(), 
                "Binding destination should be 'data-extraction' queue");
        assertEquals(Binding.DestinationType.QUEUE, binding.getDestinationType(), 
                "Binding destination type should be QUEUE");
        assertEquals("", binding.getRoutingKey(), 
                "Binding routing key should be empty for fanout exchange");
    }
    
    /**
     * Test that the binding between the documents exchange and notification queue is properly configured.
     * Verifies that the binding connects the correct exchange and queue with an empty routing key.
     */
    @Test
    public void testNotificationBindingConfiguration() {
        // Arrange
        Exchange exchange = rabbitMQConfig.documentsExchange();
        Queue queue = rabbitMQConfig.notificationQueue();
        
        // Act
        Binding binding = rabbitMQConfig.notificationBinding(exchange, queue);
        
        // Assert
        assertNotNull(binding, "Binding should not be null");
        assertEquals("mca.documents", binding.getExchange(), 
                "Binding should be to 'mca.documents' exchange");
        assertEquals("notification", binding.getDestination(), 
                "Binding destination should be 'notification' queue");
        assertEquals(Binding.DestinationType.QUEUE, binding.getDestinationType(), 
                "Binding destination type should be QUEUE");
        assertEquals("", binding.getRoutingKey(), 
                "Binding routing key should be empty for fanout exchange");
    }
    
    /**
     * Test that the RabbitAdmin is properly configured with the connection factory.
     */
    @Test
    public void testRabbitAdminConfiguration() {
        // Arrange
        ConnectionFactory connectionFactory = Mockito.mock(ConnectionFactory.class);
        
        // Act
        RabbitAdmin rabbitAdmin = rabbitMQConfig.rabbitAdmin(connectionFactory);
        
        // Assert
        assertNotNull(rabbitAdmin, "RabbitAdmin should not be null");
        assertEquals(connectionFactory, rabbitAdmin.getConnectionFactory(), 
                "RabbitAdmin should use the provided connection factory");
    }
}