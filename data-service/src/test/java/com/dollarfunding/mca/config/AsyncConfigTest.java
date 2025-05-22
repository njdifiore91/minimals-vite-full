package com.dollarfunding.mca.config;

import com.dollarfunding.mca.exception.BaseException;
import com.dollarfunding.mca.util.TraceUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockitoAnnotations;
import org.springframework.aop.interceptor.AsyncUncaughtExceptionHandler;
import org.springframework.core.task.TaskDecorator;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Method;
import java.util.concurrent.Executor;
import java.util.concurrent.RejectedExecutionHandler;
import java.util.concurrent.ThreadPoolExecutor;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link AsyncConfig} class.
 * 
 * These tests verify the configuration of asynchronous task execution in the MCA application,
 * including thread pool settings, task executors, exception handling, and task scheduling.
 */
public class AsyncConfigTest {

    private AsyncConfig asyncConfig;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
        asyncConfig = new AsyncConfig();
        
        // Set default property values
        ReflectionTestUtils.setField(asyncConfig, "corePoolSize", 10);
        ReflectionTestUtils.setField(asyncConfig, "maxPoolSize", 50);
        ReflectionTestUtils.setField(asyncConfig, "queueCapacity", 500);
        ReflectionTestUtils.setField(asyncConfig, "threadNamePrefix", "mca-async-");
        ReflectionTestUtils.setField(asyncConfig, "schedulerPoolSize", 5);
    }

    @Test
    public void testGetAsyncExecutor() {
        // When
        Executor executor = asyncConfig.getAsyncExecutor();
        
        // Then
        assertNotNull(executor, "Executor should not be null");
        assertTrue(executor instanceof ThreadPoolTaskExecutor, "Executor should be a ThreadPoolTaskExecutor");
        
        ThreadPoolTaskExecutor taskExecutor = (ThreadPoolTaskExecutor) executor;
        assertEquals(10, taskExecutor.getCorePoolSize(), "Core pool size should be 10");
        assertEquals(50, taskExecutor.getMaxPoolSize(), "Max pool size should be 50");
        assertEquals(500, taskExecutor.getQueueCapacity(), "Queue capacity should be 500");
        assertEquals("mca-async-", taskExecutor.getThreadNamePrefix(), "Thread name prefix should be 'mca-async-'");
        
        // Verify rejection policy
        RejectedExecutionHandler rejectionHandler = taskExecutor.getThreadPoolExecutor().getRejectedExecutionHandler();
        assertTrue(rejectionHandler instanceof ThreadPoolExecutor.CallerRunsPolicy, 
                "Rejection handler should be CallerRunsPolicy");
        
        // Verify task decorator is set
        assertTrue(ReflectionTestUtils.getField(taskExecutor, "taskDecorator") != null, 
                "Task decorator should be set");
    }

    @Test
    public void testDocumentProcessingExecutor() {
        // When
        Executor executor = asyncConfig.documentProcessingExecutor();
        
        // Then
        assertNotNull(executor, "Document processing executor should not be null");
        assertTrue(executor instanceof ThreadPoolTaskExecutor, "Executor should be a ThreadPoolTaskExecutor");
        
        ThreadPoolTaskExecutor taskExecutor = (ThreadPoolTaskExecutor) executor;
        int expectedCorePoolSize = Math.max(4, Runtime.getRuntime().availableProcessors() / 2);
        int expectedMaxPoolSize = Runtime.getRuntime().availableProcessors() * 2;
        
        assertEquals(expectedCorePoolSize, taskExecutor.getCorePoolSize(), 
                "Core pool size should be max(4, availableProcessors/2)");
        assertEquals(expectedMaxPoolSize, taskExecutor.getMaxPoolSize(), 
                "Max pool size should be availableProcessors*2");
        assertEquals(1000, taskExecutor.getQueueCapacity(), "Queue capacity should be 1000");
        assertEquals("doc-proc-", taskExecutor.getThreadNamePrefix(), "Thread name prefix should be 'doc-proc-'");
        
        // Verify rejection policy
        RejectedExecutionHandler rejectionHandler = taskExecutor.getThreadPoolExecutor().getRejectedExecutionHandler();
        assertTrue(rejectionHandler instanceof ThreadPoolExecutor.CallerRunsPolicy, 
                "Rejection handler should be CallerRunsPolicy");
        
        // Verify task decorator is set
        assertTrue(ReflectionTestUtils.getField(taskExecutor, "taskDecorator") != null, 
                "Task decorator should be set");
    }

    @Test
    public void testIoExecutor() {
        // When
        Executor executor = asyncConfig.ioExecutor();
        
        // Then
        assertNotNull(executor, "IO executor should not be null");
        assertTrue(executor instanceof ThreadPoolTaskExecutor, "Executor should be a ThreadPoolTaskExecutor");
        
        ThreadPoolTaskExecutor taskExecutor = (ThreadPoolTaskExecutor) executor;
        assertEquals(20, taskExecutor.getCorePoolSize(), "Core pool size should be 20");
        assertEquals(100, taskExecutor.getMaxPoolSize(), "Max pool size should be 100");
        assertEquals(200, taskExecutor.getQueueCapacity(), "Queue capacity should be 200");
        assertEquals("io-async-", taskExecutor.getThreadNamePrefix(), "Thread name prefix should be 'io-async-'");
        
        // Verify rejection policy
        RejectedExecutionHandler rejectionHandler = taskExecutor.getThreadPoolExecutor().getRejectedExecutionHandler();
        assertTrue(rejectionHandler instanceof ThreadPoolExecutor.DiscardOldestPolicy, 
                "Rejection handler should be DiscardOldestPolicy");
        
        // Verify task decorator is set
        assertTrue(ReflectionTestUtils.getField(taskExecutor, "taskDecorator") != null, 
                "Task decorator should be set");
    }

    @Test
    public void testNotificationExecutor() {
        // When
        Executor executor = asyncConfig.notificationExecutor();
        
        // Then
        assertNotNull(executor, "Notification executor should not be null");
        assertTrue(executor instanceof ThreadPoolTaskExecutor, "Executor should be a ThreadPoolTaskExecutor");
        
        ThreadPoolTaskExecutor taskExecutor = (ThreadPoolTaskExecutor) executor;
        assertEquals(15, taskExecutor.getCorePoolSize(), "Core pool size should be 15");
        assertEquals(50, taskExecutor.getMaxPoolSize(), "Max pool size should be 50");
        assertEquals(1000, taskExecutor.getQueueCapacity(), "Queue capacity should be 1000");
        assertEquals("notif-async-", taskExecutor.getThreadNamePrefix(), "Thread name prefix should be 'notif-async-'");
        
        // Verify rejection policy
        RejectedExecutionHandler rejectionHandler = taskExecutor.getThreadPoolExecutor().getRejectedExecutionHandler();
        assertTrue(rejectionHandler.getClass().getSimpleName().contains("NotificationRejectionHandler"), 
                "Rejection handler should be NotificationRejectionHandler");
        
        // Verify task decorator is set
        assertTrue(ReflectionTestUtils.getField(taskExecutor, "taskDecorator") != null, 
                "Task decorator should be set");
    }

    @Test
    public void testTaskScheduler() {
        // When
        ThreadPoolTaskScheduler scheduler = asyncConfig.taskScheduler();
        
        // Then
        assertNotNull(scheduler, "Task scheduler should not be null");
        assertEquals(5, scheduler.getPoolSize(), "Pool size should be 5");
        assertEquals("mca-sched-", scheduler.getThreadNamePrefix(), "Thread name prefix should be 'mca-sched-'");
        
        // Verify rejection policy
        RejectedExecutionHandler rejectionHandler = scheduler.getScheduledThreadPoolExecutor().getRejectedExecutionHandler();
        assertTrue(rejectionHandler instanceof ThreadPoolExecutor.CallerRunsPolicy, 
                "Rejection handler should be CallerRunsPolicy");
        
        // Verify error handler is set
        assertTrue(ReflectionTestUtils.getField(scheduler, "errorHandler") != null, 
                "Error handler should be set");
    }

    @Test
    public void testGetAsyncUncaughtExceptionHandler() {
        // When
        AsyncUncaughtExceptionHandler handler = asyncConfig.getAsyncUncaughtExceptionHandler();
        
        // Then
        assertNotNull(handler, "Async uncaught exception handler should not be null");
        assertTrue(handler.getClass().getSimpleName().contains("CustomAsyncExceptionHandler"), 
                "Handler should be CustomAsyncExceptionHandler");
        
        // Test the handler with a mock exception
        Method method = mock(Method.class);
        when(method.getName()).thenReturn("testMethod");
        when(method.getDeclaringClass()).thenReturn((Class) AsyncConfigTest.class);
        
        Exception exception = new RuntimeException("Test exception");
        Object[] params = new Object[] { "param1", 123 };
        
        // This should not throw any exceptions
        handler.handleUncaughtException(exception, method, params);
        
        // Test with a BaseException
        BaseException baseException = mock(BaseException.class);
        when(baseException.getErrorCode()).thenReturn("TEST-001");
        when(baseException.getMessage()).thenReturn("Test base exception");
        
        // This should not throw any exceptions
        handler.handleUncaughtException(baseException, method, params);
    }

    @Test
    public void testContextPropagationTaskDecorator() throws Exception {
        // Get the task executor to extract the task decorator
        ThreadPoolTaskExecutor executor = (ThreadPoolTaskExecutor) asyncConfig.getAsyncExecutor();
        TaskDecorator decorator = (TaskDecorator) ReflectionTestUtils.getField(executor, "taskDecorator");
        
        assertNotNull(decorator, "Task decorator should not be null");
        assertTrue(decorator.getClass().getSimpleName().contains("ContextPropagationTaskDecorator"), 
                "Decorator should be ContextPropagationTaskDecorator");
        
        // Set a correlation ID in the current thread
        String testCorrelationId = "test-correlation-id";
        TraceUtil.setCurrentCorrelationId(testCorrelationId);
        
        try {
            // Create a test runnable
            final boolean[] executed = { false };
            final String[] capturedCorrelationId = { null };
            
            Runnable originalRunnable = () -> {
                executed[0] = true;
                capturedCorrelationId[0] = TraceUtil.getCurrentCorrelationId();
            };
            
            // Decorate the runnable
            Runnable decoratedRunnable = decorator.decorate(originalRunnable);
            
            // Execute the decorated runnable
            decoratedRunnable.run();
            
            // Verify the runnable was executed
            assertTrue(executed[0], "Original runnable should have been executed");
            
            // Verify the correlation ID was propagated
            assertEquals(testCorrelationId, capturedCorrelationId[0], 
                    "Correlation ID should be propagated to the decorated runnable");
        } finally {
            // Clean up
            TraceUtil.clearCurrentCorrelationId();
        }
    }

    @Test
    public void testContextPropagationTaskDecoratorWithNoCorrelationId() throws Exception {
        // Get the task executor to extract the task decorator
        ThreadPoolTaskExecutor executor = (ThreadPoolTaskExecutor) asyncConfig.getAsyncExecutor();
        TaskDecorator decorator = (TaskDecorator) ReflectionTestUtils.getField(executor, "taskDecorator");
        
        assertNotNull(decorator, "Task decorator should not be null");
        
        // Clear any existing correlation ID
        TraceUtil.clearCurrentCorrelationId();
        
        // Create a test runnable
        final boolean[] executed = { false };
        final String[] capturedCorrelationId = { null };
        
        Runnable originalRunnable = () -> {
            executed[0] = true;
            capturedCorrelationId[0] = TraceUtil.getCurrentCorrelationId();
        };
        
        // Decorate the runnable
        Runnable decoratedRunnable = decorator.decorate(originalRunnable);
        
        // Execute the decorated runnable
        decoratedRunnable.run();
        
        // Verify the runnable was executed
        assertTrue(executed[0], "Original runnable should have been executed");
        
        // Verify a new correlation ID was generated
        assertNotNull(capturedCorrelationId[0], "A new correlation ID should have been generated");
    }

    @Test
    public void testNotificationRejectionHandler() throws Exception {
        // Get the notification executor to extract the rejection handler
        ThreadPoolTaskExecutor executor = (ThreadPoolTaskExecutor) asyncConfig.notificationExecutor();
        RejectedExecutionHandler rejectionHandler = executor.getThreadPoolExecutor().getRejectedExecutionHandler();
        
        assertNotNull(rejectionHandler, "Rejection handler should not be null");
        assertTrue(rejectionHandler.getClass().getSimpleName().contains("NotificationRejectionHandler"), 
                "Rejection handler should be NotificationRejectionHandler");
        
        // Create a mock runnable and thread pool executor
        Runnable runnable = mock(Runnable.class);
        ThreadPoolExecutor threadPoolExecutor = mock(ThreadPoolExecutor.class);
        
        // Execute the rejection handler
        rejectionHandler.rejectedExecution(runnable, threadPoolExecutor);
        
        // Verify the runnable was executed if the executor is not shutdown
        when(threadPoolExecutor.isShutdown()).thenReturn(false);
        rejectionHandler.rejectedExecution(runnable, threadPoolExecutor);
        verify(runnable, times(1)).run();
        
        // Verify the runnable was not executed if the executor is shutdown
        when(threadPoolExecutor.isShutdown()).thenReturn(true);
        rejectionHandler.rejectedExecution(runnable, threadPoolExecutor);
        // Still only called once from the previous test
        verify(runnable, times(1)).run();
    }

    @Test
    public void testNotificationRejectionHandlerWithException() throws Exception {
        // Get the notification executor to extract the rejection handler
        ThreadPoolTaskExecutor executor = (ThreadPoolTaskExecutor) asyncConfig.notificationExecutor();
        RejectedExecutionHandler rejectionHandler = executor.getThreadPoolExecutor().getRejectedExecutionHandler();
        
        // Create a mock runnable that throws an exception and a thread pool executor
        Runnable runnable = mock(Runnable.class);
        doThrow(new RuntimeException("Test exception")).when(runnable).run();
        
        ThreadPoolExecutor threadPoolExecutor = mock(ThreadPoolExecutor.class);
        when(threadPoolExecutor.isShutdown()).thenReturn(false);
        
        // Execute the rejection handler - this should not throw an exception
        rejectionHandler.rejectedExecution(runnable, threadPoolExecutor);
        
        // Verify the runnable was attempted to be executed
        verify(runnable, times(1)).run();
    }
}