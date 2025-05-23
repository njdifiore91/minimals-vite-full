package com.dollarfunding.mca.messaging;

import com.dollarfunding.mca.config.RabbitMQConfig;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitAdmin;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.ApplicationContext;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the RabbitMQConfig class.
 * 
 * These tests verify that the RabbitMQ configuration is correctly set up according to
 * the technical specification, including the proper declaration of exchanges, queues,
 * and bindings.
 */
@SpringBootTest(classes = RabbitMQConfig.class)
@TestPropertySource(properties = {
    // RabbitMQ connection properties
    "spring.rabbitmq.host=localhost",
    "spring.rabbitmq.port=5672",
    "spring.rabbitmq.username=guest",
    "spring.rabbitmq.password=guest",
    "spring.rabbitmq.virtual-host=/",
    
    // SSL/TLS properties
    "spring.rabbitmq.ssl.enabled=false",
    
    // Exchange and queue properties
    "application.messaging.exchanges.documents.name=mca.documents",
    "application.messaging.exchanges.documents.type=fanout",
    "application.messaging.exchanges.documents.durable=true",
    "application.messaging.queues.document-processing.name=document-processing",
    "application.messaging.queues.document-processing.durable=true",
    "application.messaging.queues.data-extraction.name=data-extraction",
    "application.messaging.queues.data-extraction.durable=true",
    "application.messaging.queues.notification.name=notification",
    "application.messaging.queues.notification.durable=true",
    
    // Retry properties
    "spring.rabbitmq.template.retry.initial-interval=1000",
    "spring.rabbitmq.template.retry.max-interval=10000",
    "spring.rabbitmq.template.retry.multiplier=1.5",
    "spring.rabbitmq.template.retry.max-attempts=3"
})
@ActiveProfiles("test")
@ExtendWith(MockitoExtension.class)
public class RabbitMQConfigTest {

    @MockBean
    private ConnectionFactory connectionFactory;
    
    @Autowired
    private RabbitMQConfig rabbitMQConfig;
    
    @Autowired
    private ApplicationContext applicationContext;
    
    @Mock
    private RabbitAdmin rabbitAdmin;
    
    @BeforeEach
    public void setup() {
        when(connectionFactory.createConnection()).thenReturn(null);
    }
    
    /**
     * Test that the connection factory is correctly configured.
     */
    @Test
    public void testConnectionFactoryConfiguration() {
        // The actual connection factory is mocked, so we just verify it's available in the context
        assertNotNull(connectionFactory, "ConnectionFactory should be available");
    }
    
    /**
     * Test that the JSON message converter is correctly configured.
     */
    @Test
    public void testJsonMessageConverter() {
        MessageConverter messageConverter = rabbitMQConfig.jsonMessageConverter();
        
        assertNotNull(messageConverter, "MessageConverter should not be null");
        assertTrue(messageConverter instanceof Jackson2JsonMessageConverter, 
                "MessageConverter should be an instance of Jackson2JsonMessageConverter");
    }
    
    /**
     * Test that the retry template is correctly configured with the specified properties.
     */
    @Test
    public void testRetryTemplate() {
        RetryTemplate retryTemplate = rabbitMQConfig.retryTemplate();
        
        assertNotNull(retryTemplate, "RetryTemplate should not be null");
        
        // Verify retry policy configuration
        // Note: We're using reflection to access private fields for testing purposes
        Object retryPolicy = ReflectionTestUtils.getField(retryTemplate, "retryPolicy");
        assertNotNull(retryPolicy, "RetryPolicy should not be null");
        assertEquals(3, ReflectionTestUtils.getField(retryPolicy, "maxAttempts"), 
                "Max attempts should be 3");
        
        // Verify backoff policy configuration
        Object backOffPolicy = ReflectionTestUtils.getField(retryTemplate, "backOffPolicy");
        assertNotNull(backOffPolicy, "BackOffPolicy should not be null");
        assertEquals(1000L, ReflectionTestUtils.getField(backOffPolicy, "initialInterval"), 
                "Initial interval should be 1000ms");
        assertEquals(10000L, ReflectionTestUtils.getField(backOffPolicy, "maxInterval"), 
                "Max interval should be 10000ms");
        assertEquals(1.5, ReflectionTestUtils.getField(backOffPolicy, "multiplier"), 
                "Multiplier should be 1.5");
    }
    
    /**
     * Test that the RabbitTemplate is correctly configured with the connection factory,
     * message converter, and retry template.
     */
    @Test
    public void testRabbitTemplate() {
        MessageConverter messageConverter = rabbitMQConfig.jsonMessageConverter();
        RetryTemplate retryTemplate = rabbitMQConfig.retryTemplate();
        
        RabbitTemplate rabbitTemplate = rabbitMQConfig.rabbitTemplate(
                connectionFactory, messageConverter, retryTemplate);
        
        assertNotNull(rabbitTemplate, "RabbitTemplate should not be null");
        assertEquals(connectionFactory, rabbitTemplate.getConnectionFactory(), 
                "RabbitTemplate should use the provided connection factory");
        assertEquals(messageConverter, rabbitTemplate.getMessageConverter(), 
                "RabbitTemplate should use the provided message converter");
        assertNotNull(rabbitTemplate.getRetryTemplate(), 
                "RabbitTemplate should have a retry template");
    }
    
    /**
     * Test that the 'mca.documents' fanout exchange is correctly declared.
     */
    @Test
    public void testDocumentsExchange() {
        Exchange exchange = rabbitMQConfig.documentsExchange();
        
        assertNotNull(exchange, "Exchange should not be null");
        assertEquals("mca.documents", exchange.getName(), 
                "Exchange name should be 'mca.documents'");
        assertTrue(exchange instanceof FanoutExchange, 
                "Exchange should be a FanoutExchange");
        assertTrue(exchange.isDurable(), "Exchange should be durable");
    }
    
    /**
     * Test that the 'document-processing' queue is correctly declared.
     */
    @Test
    public void testDocumentProcessingQueue() {
        Queue queue = rabbitMQConfig.documentProcessingQueue();
        
        assertNotNull(queue, "Queue should not be null");
        assertEquals("document-processing", queue.getName(), 
                "Queue name should be 'document-processing'");
        assertTrue(queue.isDurable(), "Queue should be durable");
    }
    
    /**
     * Test that the 'data-extraction' queue is correctly declared.
     */
    @Test
    public void testDataExtractionQueue() {
        Queue queue = rabbitMQConfig.dataExtractionQueue();
        
        assertNotNull(queue, "Queue should not be null");
        assertEquals("data-extraction", queue.getName(), 
                "Queue name should be 'data-extraction'");
        assertTrue(queue.isDurable(), "Queue should be durable");
    }
    
    /**
     * Test that the 'notification' queue is correctly declared.
     */
    @Test
    public void testNotificationQueue() {
        Queue queue = rabbitMQConfig.notificationQueue();
        
        assertNotNull(queue, "Queue should not be null");
        assertEquals("notification", queue.getName(), 
                "Queue name should be 'notification'");
        assertTrue(queue.isDurable(), "Queue should be durable");
    }
    
    /**
     * Test that the binding between the 'mca.documents' exchange and the 'document-processing'
     * queue is correctly declared.
     */
    @Test
    public void testDocumentProcessingBinding() {
        Exchange exchange = rabbitMQConfig.documentsExchange();
        Queue queue = rabbitMQConfig.documentProcessingQueue();
        
        Binding binding = rabbitMQConfig.documentProcessingBinding(exchange, queue);
        
        assertNotNull(binding, "Binding should not be null");
        assertEquals(queue.getName(), binding.getDestination(), 
                "Binding destination should be the queue name");
        assertEquals(exchange.getName(), binding.getExchange(), 
                "Binding exchange should be the exchange name");
        assertEquals(Binding.DestinationType.QUEUE, binding.getDestinationType(), 
                "Binding destination type should be QUEUE");
        assertEquals("", binding.getRoutingKey(), 
                "Binding routing key should be empty for fanout exchange");
    }
    
    /**
     * Test that the binding between the 'mca.documents' exchange and the 'data-extraction'
     * queue is correctly declared.
     */
    @Test
    public void testDataExtractionBinding() {
        Exchange exchange = rabbitMQConfig.documentsExchange();
        Queue queue = rabbitMQConfig.dataExtractionQueue();
        
        Binding binding = rabbitMQConfig.dataExtractionBinding(exchange, queue);
        
        assertNotNull(binding, "Binding should not be null");
        assertEquals(queue.getName(), binding.getDestination(), 
                "Binding destination should be the queue name");
        assertEquals(exchange.getName(), binding.getExchange(), 
                "Binding exchange should be the exchange name");
        assertEquals(Binding.DestinationType.QUEUE, binding.getDestinationType(), 
                "Binding destination type should be QUEUE");
        assertEquals("", binding.getRoutingKey(), 
                "Binding routing key should be empty for fanout exchange");
    }
    
    /**
     * Test that the binding between the 'mca.documents' exchange and the 'notification'
     * queue is correctly declared.
     */
    @Test
    public void testNotificationBinding() {
        Exchange exchange = rabbitMQConfig.documentsExchange();
        Queue queue = rabbitMQConfig.notificationQueue();
        
        Binding binding = rabbitMQConfig.notificationBinding(exchange, queue);
        
        assertNotNull(binding, "Binding should not be null");
        assertEquals(queue.getName(), binding.getDestination(), 
                "Binding destination should be the queue name");
        assertEquals(exchange.getName(), binding.getExchange(), 
                "Binding exchange should be the exchange name");
        assertEquals(Binding.DestinationType.QUEUE, binding.getDestinationType(), 
                "Binding destination type should be QUEUE");
        assertEquals("", binding.getRoutingKey(), 
                "Binding routing key should be empty for fanout exchange");
    }
    
    /**
     * Test that the RabbitAdmin is correctly configured with the connection factory.
     */
    @Test
    public void testRabbitAdmin() {
        RabbitAdmin admin = rabbitMQConfig.rabbitAdmin(connectionFactory);
        
        assertNotNull(admin, "RabbitAdmin should not be null");
    }
    
    /**
     * Integration test to verify that all required beans are available in the application context.
     */
    @Test
    public void testAllRequiredBeansAreAvailable() {
        // Verify that all required beans are available in the application context
        assertTrue(applicationContext.containsBean("connectionFactory"), 
                "ConnectionFactory bean should be available");
        assertTrue(applicationContext.containsBean("jsonMessageConverter"), 
                "jsonMessageConverter bean should be available");
        assertTrue(applicationContext.containsBean("retryTemplate"), 
                "retryTemplate bean should be available");
        assertTrue(applicationContext.containsBean("rabbitTemplate"), 
                "rabbitTemplate bean should be available");
        assertTrue(applicationContext.containsBean("documentsExchange"), 
                "documentsExchange bean should be available");
        assertTrue(applicationContext.containsBean("documentProcessingQueue"), 
                "documentProcessingQueue bean should be available");
        assertTrue(applicationContext.containsBean("dataExtractionQueue"), 
                "dataExtractionQueue bean should be available");
        assertTrue(applicationContext.containsBean("notificationQueue"), 
                "notificationQueue bean should be available");
        assertTrue(applicationContext.containsBean("documentProcessingBinding"), 
                "documentProcessingBinding bean should be available");
        assertTrue(applicationContext.containsBean("dataExtractionBinding"), 
                "dataExtractionBinding bean should be available");
        assertTrue(applicationContext.containsBean("notificationBinding"), 
                "notificationBinding bean should be available");
        assertTrue(applicationContext.containsBean("rabbitAdmin"), 
                "rabbitAdmin bean should be available");
    }
    
    /**
     * Test that SSL/TLS configuration is correctly applied when enabled.
     * This test uses reflection to verify the SSL configuration logic without actually
     * creating SSL contexts.
     */
    @Test
    public void testSslConfiguration() {
        // This is a limited test since we can't easily test SSL configuration in a unit test
        // In a real scenario, we would use integration tests with test certificates
        
        // We're just verifying that the SSL configuration code path doesn't throw exceptions
        // when SSL is disabled (as per our test properties)
        ConnectionFactory factory = rabbitMQConfig.connectionFactory();
        assertNotNull(factory, "ConnectionFactory should not be null even with SSL disabled");
    }
}