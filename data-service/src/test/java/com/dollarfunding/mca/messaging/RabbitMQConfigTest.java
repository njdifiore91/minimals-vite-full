package com.dollarfunding.mca.messaging;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
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
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.amqp.RabbitProperties;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.retry.support.RetryTemplate;
import org.springframework.test.context.ActiveProfiles;

import com.dollarfunding.mca.config.RabbitMQConfig;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Unit tests for the RabbitMQConfig class.
 * 
 * These tests verify that the RabbitMQ configuration is correctly set up,
 * including the connection factory, exchanges, queues, and bindings.
 */
@SpringBootTest
@ActiveProfiles("test")
public class RabbitMQConfigTest {

    @Autowired
    private ApplicationContext context;
    
    @MockBean
    private AmqpAdmin amqpAdmin;
    
    @Autowired
    private RabbitMQConfig rabbitMQConfig;
    
    @Autowired
    private ConnectionFactory connectionFactory;
    
    @Autowired
    private MessageConverter messageConverter;
    
    @Autowired
    private RabbitTemplate rabbitTemplate;
    
    @Autowired
    private FanoutExchange documentsExchange;
    
    @Autowired
    private Queue documentProcessingQueue;
    
    @Autowired
    private Queue dataExtractionQueue;
    
    @Autowired
    private Queue notificationQueue;
    
    @Autowired
    private Binding documentProcessingBinding;
    
    @Autowired
    private Binding dataExtractionBinding;
    
    @Autowired
    private Binding notificationBinding;
    
    @Autowired
    private FanoutExchange deadLetterExchange;
    
    @Autowired
    private Queue deadLetterQueue;
    
    @Autowired
    private Binding deadLetterBinding;
    
    @BeforeEach
    public void setup() {
        // Reset the mock before each test
        when(amqpAdmin.declareExchange(any())).thenReturn(true);
        when(amqpAdmin.declareQueue(any())).thenReturn(new HashMap<>());
        when(amqpAdmin.declareBinding(any())).thenReturn(true);
    }
    
    @Test
    @DisplayName("Test that the connection factory is configured correctly")
    public void testConnectionFactoryConfiguration() {
        // Verify that the connection factory is created
        assertNotNull(connectionFactory, "Connection factory should not be null");
        assertTrue(connectionFactory instanceof CachingConnectionFactory, 
                "Connection factory should be a CachingConnectionFactory");
        
        CachingConnectionFactory cachingConnectionFactory = (CachingConnectionFactory) connectionFactory;
        
        // Verify connection properties
        assertEquals("localhost", cachingConnectionFactory.getHost(), 
                "Connection factory host should be localhost");
        assertEquals(5672, cachingConnectionFactory.getPort(), 
                "Connection factory port should be 5672");
        assertEquals("/", cachingConnectionFactory.getVirtualHost(), 
                "Connection factory virtual host should be /");
    }
    
    @Test
    @DisplayName("Test that the message converter is configured correctly")
    public void testMessageConverterConfiguration() {
        // Verify that the message converter is created
        assertNotNull(messageConverter, "Message converter should not be null");
        assertTrue(messageConverter instanceof Jackson2JsonMessageConverter, 
                "Message converter should be a Jackson2JsonMessageConverter");
    }
    
    @Test
    @DisplayName("Test that the RabbitTemplate is configured correctly")
    public void testRabbitTemplateConfiguration() {
        // Verify that the RabbitTemplate is created
        assertNotNull(rabbitTemplate, "RabbitTemplate should not be null");
        
        // Verify that the RabbitTemplate uses the correct message converter
        assertEquals(messageConverter, rabbitTemplate.getMessageConverter(), 
                "RabbitTemplate should use the configured message converter");
        
        // Verify that the RabbitTemplate is configured for mandatory messages
        assertTrue(rabbitTemplate.isMandatory(), 
                "RabbitTemplate should be configured for mandatory messages");
    }
    
    @Test
    @DisplayName("Test that the documents exchange is declared correctly")
    public void testDocumentsExchangeDeclaration() {
        // Verify that the exchange is created with the correct name
        assertNotNull(documentsExchange, "Documents exchange should not be null");
        assertEquals("mca.documents", documentsExchange.getName(), 
                "Documents exchange should be named 'mca.documents'");
        assertTrue(documentsExchange.isDurable(), 
                "Documents exchange should be durable");
        
        // Verify that the exchange is declared to the broker
        verify(amqpAdmin, times(1)).declareExchange(eq(documentsExchange));
    }
    
    @Test
    @DisplayName("Test that the document processing queue is declared correctly")
    public void testDocumentProcessingQueueDeclaration() {
        // Verify that the queue is created with the correct name
        assertNotNull(documentProcessingQueue, "Document processing queue should not be null");
        assertEquals("document-processing", documentProcessingQueue.getName(), 
                "Document processing queue should be named 'document-processing'");
        assertTrue(documentProcessingQueue.isDurable(), 
                "Document processing queue should be durable");
        
        // Verify that the queue has the correct dead letter exchange argument
        Map<String, Object> arguments = documentProcessingQueue.getArguments();
        assertNotNull(arguments, "Queue arguments should not be null");
        assertEquals("mca.dead-letter", arguments.get("x-dead-letter-exchange"), 
                "Queue should have 'mca.dead-letter' as the dead letter exchange");
        
        // Verify that the queue is declared to the broker
        verify(amqpAdmin, times(1)).declareQueue(eq(documentProcessingQueue));
    }
    
    @Test
    @DisplayName("Test that the data extraction queue is declared correctly")
    public void testDataExtractionQueueDeclaration() {
        // Verify that the queue is created with the correct name
        assertNotNull(dataExtractionQueue, "Data extraction queue should not be null");
        assertEquals("data-extraction", dataExtractionQueue.getName(), 
                "Data extraction queue should be named 'data-extraction'");
        assertTrue(dataExtractionQueue.isDurable(), 
                "Data extraction queue should be durable");
        
        // Verify that the queue has the correct dead letter exchange argument
        Map<String, Object> arguments = dataExtractionQueue.getArguments();
        assertNotNull(arguments, "Queue arguments should not be null");
        assertEquals("mca.dead-letter", arguments.get("x-dead-letter-exchange"), 
                "Queue should have 'mca.dead-letter' as the dead letter exchange");
        
        // Verify that the queue is declared to the broker
        verify(amqpAdmin, times(1)).declareQueue(eq(dataExtractionQueue));
    }
    
    @Test
    @DisplayName("Test that the notification queue is declared correctly")
    public void testNotificationQueueDeclaration() {
        // Verify that the queue is created with the correct name
        assertNotNull(notificationQueue, "Notification queue should not be null");
        assertEquals("notification", notificationQueue.getName(), 
                "Notification queue should be named 'notification'");
        assertTrue(notificationQueue.isDurable(), 
                "Notification queue should be durable");
        
        // Verify that the queue has the correct dead letter exchange argument
        Map<String, Object> arguments = notificationQueue.getArguments();
        assertNotNull(arguments, "Queue arguments should not be null");
        assertEquals("mca.dead-letter", arguments.get("x-dead-letter-exchange"), 
                "Queue should have 'mca.dead-letter' as the dead letter exchange");
        
        // Verify that the queue is declared to the broker
        verify(amqpAdmin, times(1)).declareQueue(eq(notificationQueue));
    }
    
    @Test
    @DisplayName("Test that the document processing binding is declared correctly")
    public void testDocumentProcessingBindingDeclaration() {
        // Verify that the binding is created correctly
        assertNotNull(documentProcessingBinding, "Document processing binding should not be null");
        assertEquals(documentsExchange.getName(), documentProcessingBinding.getExchange(), 
                "Binding should be to the documents exchange");
        assertEquals(documentProcessingQueue.getName(), documentProcessingBinding.getDestination(), 
                "Binding destination should be the document processing queue");
        assertEquals(Binding.DestinationType.QUEUE, documentProcessingBinding.getDestinationType(), 
                "Binding destination type should be QUEUE");
        
        // Verify that the binding is declared to the broker
        verify(amqpAdmin, times(1)).declareBinding(eq(documentProcessingBinding));
    }
    
    @Test
    @DisplayName("Test that the data extraction binding is declared correctly")
    public void testDataExtractionBindingDeclaration() {
        // Verify that the binding is created correctly
        assertNotNull(dataExtractionBinding, "Data extraction binding should not be null");
        assertEquals(documentsExchange.getName(), dataExtractionBinding.getExchange(), 
                "Binding should be to the documents exchange");
        assertEquals(dataExtractionQueue.getName(), dataExtractionBinding.getDestination(), 
                "Binding destination should be the data extraction queue");
        assertEquals(Binding.DestinationType.QUEUE, dataExtractionBinding.getDestinationType(), 
                "Binding destination type should be QUEUE");
        
        // Verify that the binding is declared to the broker
        verify(amqpAdmin, times(1)).declareBinding(eq(dataExtractionBinding));
    }
    
    @Test
    @DisplayName("Test that the notification binding is declared correctly")
    public void testNotificationBindingDeclaration() {
        // Verify that the binding is created correctly
        assertNotNull(notificationBinding, "Notification binding should not be null");
        assertEquals(documentsExchange.getName(), notificationBinding.getExchange(), 
                "Binding should be to the documents exchange");
        assertEquals(notificationQueue.getName(), notificationBinding.getDestination(), 
                "Binding destination should be the notification queue");
        assertEquals(Binding.DestinationType.QUEUE, notificationBinding.getDestinationType(), 
                "Binding destination type should be QUEUE");
        
        // Verify that the binding is declared to the broker
        verify(amqpAdmin, times(1)).declareBinding(eq(notificationBinding));
    }
    
    @Test
    @DisplayName("Test that the dead letter exchange is declared correctly")
    public void testDeadLetterExchangeDeclaration() {
        // Verify that the exchange is created with the correct name
        assertNotNull(deadLetterExchange, "Dead letter exchange should not be null");
        assertEquals("mca.dead-letter", deadLetterExchange.getName(), 
                "Dead letter exchange should be named 'mca.dead-letter'");
        assertTrue(deadLetterExchange.isDurable(), 
                "Dead letter exchange should be durable");
        
        // Verify that the exchange is declared to the broker
        verify(amqpAdmin, times(1)).declareExchange(eq(deadLetterExchange));
    }
    
    @Test
    @DisplayName("Test that the dead letter queue is declared correctly")
    public void testDeadLetterQueueDeclaration() {
        // Verify that the queue is created with the correct name
        assertNotNull(deadLetterQueue, "Dead letter queue should not be null");
        assertEquals("dead-letter-queue", deadLetterQueue.getName(), 
                "Dead letter queue should be named 'dead-letter-queue'");
        assertTrue(deadLetterQueue.isDurable(), 
                "Dead letter queue should be durable");
        
        // Verify that the queue is declared to the broker
        verify(amqpAdmin, times(1)).declareQueue(eq(deadLetterQueue));
    }
    
    @Test
    @DisplayName("Test that the dead letter binding is declared correctly")
    public void testDeadLetterBindingDeclaration() {
        // Verify that the binding is created correctly
        assertNotNull(deadLetterBinding, "Dead letter binding should not be null");
        assertEquals(deadLetterExchange.getName(), deadLetterBinding.getExchange(), 
                "Binding should be to the dead letter exchange");
        assertEquals(deadLetterQueue.getName(), deadLetterBinding.getDestination(), 
                "Binding destination should be the dead letter queue");
        assertEquals(Binding.DestinationType.QUEUE, deadLetterBinding.getDestinationType(), 
                "Binding destination type should be QUEUE");
        
        // Verify that the binding is declared to the broker
        verify(amqpAdmin, times(1)).declareBinding(eq(deadLetterBinding));
    }
    
    @Test
    @DisplayName("Test that the RabbitMQ listener container factory is configured correctly")
    public void testRabbitListenerContainerFactoryConfiguration() {
        // Verify that the factory is created
        SimpleRabbitListenerContainerFactory factory = context.getBean(SimpleRabbitListenerContainerFactory.class);
        assertNotNull(factory, "RabbitListenerContainerFactory should not be null");
    }
    
    @Test
    @DisplayName("Test that the message recoverer is configured correctly")
    public void testMessageRecovererConfiguration() {
        // Verify that the message recoverer is created
        MessageRecoverer messageRecoverer = context.getBean(MessageRecoverer.class);
        assertNotNull(messageRecoverer, "MessageRecoverer should not be null");
    }
    
    @Test
    @DisplayName("Test that the retry template is configured correctly")
    public void testRetryTemplateConfiguration() {
        // Verify that the retry template is created
        RetryTemplate retryTemplate = context.getBean(RetryTemplate.class);
        assertNotNull(retryTemplate, "RetryTemplate should not be null");
    }
}