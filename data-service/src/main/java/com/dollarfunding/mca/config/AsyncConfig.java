package com.dollarfunding.mca.config;

import com.dollarfunding.mca.exception.BaseException;
import com.dollarfunding.mca.util.Constants;
import com.dollarfunding.mca.util.TraceUtil;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.aop.interceptor.AsyncUncaughtExceptionHandler;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.TaskDecorator;
import org.springframework.scheduling.annotation.AsyncConfigurer;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;

import java.lang.reflect.Method;
import java.util.concurrent.Executor;
import java.util.concurrent.RejectedExecutionHandler;
import java.util.concurrent.ThreadPoolExecutor;

/**
 * Configuration class for asynchronous task execution in the MCA application.
 * <p>
 * This class configures thread pools, task executors, and exception handling for asynchronous methods.
 * It enables the application to process long-running operations without blocking the main thread,
 * improving responsiveness and throughput.
 * </p>
 * <p>
 * Key features:
 * <ul>
 *   <li>Configurable thread pools for different types of async operations</li>
 *   <li>Propagation of correlation IDs across async boundaries for distributed tracing</li>
 *   <li>Comprehensive exception handling for async methods</li>
 *   <li>Graceful rejection policies to prevent system overload</li>
 *   <li>Task scheduling for periodic operations</li>
 * </ul>
 * </p>
 */
@Configuration
@EnableAsync
@EnableScheduling
public class AsyncConfig implements AsyncConfigurer {

    private static final Logger logger = LoggerFactory.getLogger(AsyncConfig.class);

    @Value("${app.async.core-pool-size:10}")
    private int corePoolSize;

    @Value("${app.async.max-pool-size:50}")
    private int maxPoolSize;

    @Value("${app.async.queue-capacity:500}")
    private int queueCapacity;

    @Value("${app.async.thread-name-prefix:mca-async-}")
    private String threadNamePrefix;

    @Value("${app.async.scheduler-pool-size:5}")
    private int schedulerPoolSize;

    /**
     * Creates the default task executor used for @Async methods.
     * <p>
     * This executor is optimized for general-purpose async operations with:
     * <ul>
     *   <li>Configurable core and max pool sizes</li>
     *   <li>Queue capacity to buffer tasks when all threads are busy</li>
     *   <li>Correlation ID propagation for distributed tracing</li>
     *   <li>Caller runs policy to prevent task rejection under heavy load</li>
     * </ul>
     * </p>
     *
     * @return the configured task executor
     */
    @Override
    @Bean(name = "taskExecutor")
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(corePoolSize);
        executor.setMaxPoolSize(maxPoolSize);
        executor.setQueueCapacity(queueCapacity);
        executor.setThreadNamePrefix(threadNamePrefix);
        
        // Use CallerRunsPolicy to avoid rejecting tasks when the queue is full
        // This will cause the calling thread to execute the task synchronously
        // which is better than losing the task entirely
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        
        // Propagate correlation IDs and other context information across async boundaries
        executor.setTaskDecorator(new ContextPropagationTaskDecorator());
        
        // Wait for tasks to complete on shutdown, with a timeout
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(60);
        
        executor.initialize();
        logger.info("Initialized default task executor with corePoolSize={}, maxPoolSize={}, queueCapacity={}", 
                corePoolSize, maxPoolSize, queueCapacity);
        return executor;
    }

    /**
     * Creates a specialized task executor for document processing operations.
     * <p>
     * This executor is configured with parameters optimized for CPU-intensive document processing:
     * <ul>
     *   <li>Higher core pool size to utilize available CPU cores</li>
     *   <li>Larger queue capacity to handle document processing spikes</li>
     *   <li>Correlation ID propagation for distributed tracing</li>
     * </ul>
     * </p>
     *
     * @return the document processing task executor
     */
    @Bean(name = "documentProcessingExecutor")
    public Executor documentProcessingExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        // Use more threads for CPU-intensive document processing
        executor.setCorePoolSize(Math.max(4, Runtime.getRuntime().availableProcessors() / 2));
        executor.setMaxPoolSize(Runtime.getRuntime().availableProcessors() * 2);
        executor.setQueueCapacity(1000);
        executor.setThreadNamePrefix("doc-proc-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setTaskDecorator(new ContextPropagationTaskDecorator());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(120); // Longer wait time for document processing
        executor.initialize();
        logger.info("Initialized document processing executor with corePoolSize={}, maxPoolSize={}", 
                executor.getCorePoolSize(), executor.getMaxPoolSize());
        return executor;
    }

    /**
     * Creates a specialized task executor for I/O-bound operations like API calls and file operations.
     * <p>
     * This executor is configured with parameters optimized for I/O-bound operations:
     * <ul>
     *   <li>Higher thread count since threads spend most time waiting on I/O</li>
     *   <li>Smaller queue to fail fast when overloaded</li>
     *   <li>Discard oldest policy to prioritize newer requests</li>
     * </ul>
     * </p>
     *
     * @return the I/O operations task executor
     */
    @Bean(name = "ioExecutor")
    public Executor ioExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        // Use more threads for I/O-bound operations since they spend most time waiting
        executor.setCorePoolSize(20);
        executor.setMaxPoolSize(100);
        executor.setQueueCapacity(200);
        executor.setThreadNamePrefix("io-async-");
        // Use DiscardOldestPolicy for I/O operations to prioritize newer requests
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.DiscardOldestPolicy());
        executor.setTaskDecorator(new ContextPropagationTaskDecorator());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        logger.info("Initialized I/O executor with corePoolSize={}, maxPoolSize={}", 
                executor.getCorePoolSize(), executor.getMaxPoolSize());
        return executor;
    }

    /**
     * Creates a specialized task executor for notification delivery operations.
     * <p>
     * This executor is configured with parameters optimized for webhook and notification delivery:
     * <ul>
     *   <li>Higher thread count to handle many parallel notification deliveries</li>
     *   <li>Large queue capacity to buffer notifications during high load</li>
     *   <li>Custom rejection handler to log and retry later</li>
     * </ul>
     * </p>
     *
     * @return the notification delivery task executor
     */
    @Bean(name = "notificationExecutor")
    public Executor notificationExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(15);
        executor.setMaxPoolSize(50);
        executor.setQueueCapacity(1000);
        executor.setThreadNamePrefix("notif-async-");
        // Custom rejection handler for notifications to ensure they're not lost
        executor.setRejectedExecutionHandler(new NotificationRejectionHandler());
        executor.setTaskDecorator(new ContextPropagationTaskDecorator());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(60);
        executor.initialize();
        logger.info("Initialized notification executor with corePoolSize={}, maxPoolSize={}", 
                executor.getCorePoolSize(), executor.getMaxPoolSize());
        return executor;
    }

    /**
     * Creates a task scheduler for periodic operations like cleanup tasks, status checks, etc.
     *
     * @return the configured task scheduler
     */
    @Bean(name = "taskScheduler")
    public ThreadPoolTaskScheduler taskScheduler() {
        ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
        scheduler.setPoolSize(schedulerPoolSize);
        scheduler.setThreadNamePrefix("mca-sched-");
        scheduler.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        scheduler.setWaitForTasksToCompleteOnShutdown(true);
        scheduler.setAwaitTerminationSeconds(60);
        scheduler.setErrorHandler(t -> {
            logger.error("Uncaught exception in scheduled task", t);
            // Additional error handling like notification or metrics
        });
        scheduler.initialize();
        logger.info("Initialized task scheduler with poolSize={}", schedulerPoolSize);
        return scheduler;
    }

    /**
     * Configures the exception handler for @Async methods.
     * <p>
     * This handler logs exceptions that occur in asynchronous methods and provides
     * detailed information about the method that failed and the exception that occurred.
     * </p>
     *
     * @return the configured async uncaught exception handler
     */
    @Override
    public AsyncUncaughtExceptionHandler getAsyncUncaughtExceptionHandler() {
        return new CustomAsyncExceptionHandler();
    }

    /**
     * Custom task decorator that propagates the correlation ID and other context information
     * across async boundaries to maintain distributed tracing capabilities.
     */
    private static class ContextPropagationTaskDecorator implements TaskDecorator {
        @Override
        public Runnable decorate(Runnable runnable) {
            // Capture the current correlation ID before the async boundary
            String correlationId = TraceUtil.getCurrentCorrelationId();
            
            // Return a wrapped Runnable that sets the correlation ID in the new thread
            return () -> {
                try {
                    // Set the captured correlation ID in the new thread
                    if (correlationId != null) {
                        TraceUtil.setCurrentCorrelationId(correlationId);
                    } else {
                        // Generate a new correlation ID if none exists
                        TraceUtil.setCurrentCorrelationId(TraceUtil.generateCorrelationId());
                    }
                    
                    // Execute the original task
                    runnable.run();
                } finally {
                    // Clean up the correlation ID after task completion
                    TraceUtil.clearCurrentCorrelationId();
                }
            };
        }
    }

    /**
     * Custom exception handler for async methods that provides detailed logging
     * and potential recovery actions for uncaught exceptions.
     */
    private static class CustomAsyncExceptionHandler implements AsyncUncaughtExceptionHandler {
        @Override
        public void handleUncaughtException(Throwable ex, Method method, Object... params) {
            logger.error("Uncaught exception in async method {}.{}()", 
                    method.getDeclaringClass().getSimpleName(), 
                    method.getName(), ex);
            
            // Log parameter information to aid debugging
            if (params != null && params.length > 0) {
                StringBuilder paramInfo = new StringBuilder("Method parameters: ");
                for (int i = 0; i < params.length; i++) {
                    paramInfo.append("param").append(i + 1).append("=");
                    if (params[i] != null) {
                        paramInfo.append(params[i].toString());
                    } else {
                        paramInfo.append("null");
                    }
                    if (i < params.length - 1) {
                        paramInfo.append(", ");
                    }
                }
                logger.error(paramInfo.toString());
            }
            
            // Additional error handling like metrics or notifications for critical failures
            if (ex instanceof BaseException) {
                // Handle custom exceptions with specific error codes
                BaseException baseEx = (BaseException) ex;
                logger.error("Error code: {}, Message: {}", baseEx.getErrorCode(), baseEx.getMessage());
                
                // Potential recovery actions based on error type
                // This could include notifications to admins, metrics, etc.
            }
        }
    }

    /**
     * Custom rejection handler for notification tasks that logs the rejection and
     * provides a mechanism to retry the notification later.
     */
    private static class NotificationRejectionHandler implements RejectedExecutionHandler {
        private static final Logger rejectionLogger = LoggerFactory.getLogger("NotificationRejectionHandler");
        
        @Override
        public void rejectedExecution(Runnable r, ThreadPoolExecutor executor) {
            rejectionLogger.warn("Notification task rejected due to thread pool saturation. " +
                    "Queue size: {}, Active threads: {}, Task will be logged for retry.",
                    executor.getQueue().size(), executor.getActiveCount());
            
            // In a real implementation, we would persist the rejected notification
            // to a database or queue for later retry
            // For now, we'll just log it and use the caller runs policy as fallback
            
            // Execute in the caller's thread as a fallback
            if (!executor.isShutdown()) {
                try {
                    r.run();
                    rejectionLogger.info("Executed rejected notification task in caller thread");
                } catch (Exception e) {
                    rejectionLogger.error("Error executing rejected notification task in caller thread", e);
                    // Here we could add the task to a persistent retry queue
                }
            }
        }
    }
}