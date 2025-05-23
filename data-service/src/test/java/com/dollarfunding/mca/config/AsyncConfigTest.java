package com.dollarfunding.mca.config;

import org.junit.jupiter.api.Test;
import org.springframework.core.task.TaskExecutor;
import org.springframework.scheduling.annotation.AsyncConfigurer;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;
import java.util.concurrent.RejectedExecutionHandler;
import java.util.concurrent.ThreadPoolExecutor;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the AsyncConfig class that configures asynchronous task execution.
 * Tests verify thread pool configuration, task executor setup with appropriate queue sizes
 * and rejection policies, exception handling configuration, timeout settings, and task
 * scheduling configuration.
 */
public class AsyncConfigTest {

    /**
     * Test that the async executor is properly configured with the expected thread pool settings.
     * Verifies core pool size, max pool size, queue capacity, thread name prefix, and rejection policy.
     */
    @Test
    public void testAsyncExecutorConfiguration() {
        // Arrange
        AsyncConfig asyncConfig = new AsyncConfig();
        
        // Act
        Executor executor = asyncConfig.getAsyncExecutor();
        
        // Assert
        assertNotNull(executor, "Executor should not be null");
        assertTrue(executor instanceof ThreadPoolTaskExecutor, "Executor should be a ThreadPoolTaskExecutor");
        
        ThreadPoolTaskExecutor taskExecutor = (ThreadPoolTaskExecutor) executor;
        assertEquals(10, taskExecutor.getCorePoolSize(), "Core pool size should be 10");
        assertEquals(50, taskExecutor.getMaxPoolSize(), "Max pool size should be 50");
        assertEquals(100, taskExecutor.getQueueCapacity(), "Queue capacity should be 100");
        assertEquals("mca-async-", taskExecutor.getThreadNamePrefix(), "Thread name prefix should be 'mca-async-'");
        
        // Verify rejection policy is CallerRunsPolicy
        RejectedExecutionHandler rejectionHandler = taskExecutor.getThreadPoolExecutor().getRejectedExecutionHandler();
        assertTrue(rejectionHandler instanceof ThreadPoolExecutor.CallerRunsPolicy, 
                "Rejection policy should be CallerRunsPolicy");
    }
    
    /**
     * Test that the async exception handler is properly configured.
     * Verifies that a custom AsyncUncaughtExceptionHandler is returned.
     */
    @Test
    public void testAsyncExceptionHandlerConfiguration() {
        // Arrange
        AsyncConfig asyncConfig = new AsyncConfig();
        
        // Act
        AsyncConfigurer.AsyncUncaughtExceptionHandler exceptionHandler = 
                asyncConfig.getAsyncUncaughtExceptionHandler();
        
        // Assert
        assertNotNull(exceptionHandler, "Exception handler should not be null");
        assertTrue(exceptionHandler instanceof CustomAsyncExceptionHandler, 
                "Exception handler should be a CustomAsyncExceptionHandler");
    }
    
    /**
     * Test that the task scheduler is properly configured for periodic operations.
     * Verifies pool size and thread name prefix for the scheduler.
     */
    @Test
    public void testTaskSchedulerConfiguration() {
        // Arrange
        AsyncConfig asyncConfig = new AsyncConfig();
        
        // Act
        TaskExecutor taskScheduler = asyncConfig.taskScheduler();
        
        // Assert
        assertNotNull(taskScheduler, "Task scheduler should not be null");
        assertTrue(taskScheduler instanceof ThreadPoolTaskExecutor, 
                "Task scheduler should be a ThreadPoolTaskExecutor");
        
        ThreadPoolTaskExecutor scheduler = (ThreadPoolTaskExecutor) taskScheduler;
        assertEquals(5, scheduler.getCorePoolSize(), "Scheduler core pool size should be 5");
        assertEquals("mca-scheduler-", scheduler.getThreadNamePrefix(), 
                "Scheduler thread name prefix should be 'mca-scheduler-'");
    }
    
    /**
     * Test that the application task executor is properly configured for MVC async requests.
     * Verifies core pool size, max pool size, queue capacity, and thread name prefix.
     */
    @Test
    public void testApplicationTaskExecutorConfiguration() {
        // Arrange
        AsyncConfig asyncConfig = new AsyncConfig();
        
        // Act
        TaskExecutor appTaskExecutor = asyncConfig.applicationTaskExecutor();
        
        // Assert
        assertNotNull(appTaskExecutor, "Application task executor should not be null");
        assertTrue(appTaskExecutor instanceof ThreadPoolTaskExecutor, 
                "Application task executor should be a ThreadPoolTaskExecutor");
        
        ThreadPoolTaskExecutor taskExecutor = (ThreadPoolTaskExecutor) appTaskExecutor;
        assertEquals(8, taskExecutor.getCorePoolSize(), "Core pool size should be 8");
        assertEquals(16, taskExecutor.getMaxPoolSize(), "Max pool size should be 16");
        assertEquals(100, taskExecutor.getQueueCapacity(), "Queue capacity should be 100");
        assertEquals("mca-app-task-", taskExecutor.getThreadNamePrefix(), 
                "Thread name prefix should be 'mca-app-task-'");
    }
    
    /**
     * Test that the timeout settings for async methods are properly configured.
     * Verifies that the timeout is set to 5 minutes (300000 ms) to meet the requirement
     * of processing applications in under 5 minutes.
     */
    @Test
    public void testAsyncMethodTimeoutConfiguration() {
        // Arrange
        AsyncConfig asyncConfig = new AsyncConfig();
        
        // Act
        long timeout = asyncConfig.getAsyncMethodTimeout();
        
        // Assert
        assertEquals(300000, timeout, "Async method timeout should be 5 minutes (300000 ms)");
    }
}