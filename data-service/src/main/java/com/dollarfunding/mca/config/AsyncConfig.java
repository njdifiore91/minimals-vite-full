package com.dollarfunding.mca.config;

import java.lang.reflect.Method;
import java.util.concurrent.Executor;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.aop.interceptor.AsyncUncaughtExceptionHandler;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.AsyncConfigurer;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

/**
 * Configuration class for asynchronous task execution in the MCA application.
 * 
 * This class configures thread pools, task executors, and exception handling for
 * asynchronous methods. It enables the application to process long-running operations
 * without blocking the main thread, improving responsiveness and throughput.
 *
 * Key features:
 * - Configurable thread pool sizes and queue capacity
 * - Custom thread naming for easier debugging
 * - Comprehensive exception handling for asynchronous methods
 * - Support for task timeouts
 * - Saturation policy to handle task rejection
 */
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {

    private static final Logger log = LoggerFactory.getLogger(AsyncConfig.class);

    @Value("${async.executor.core-pool-size:10}")
    private int corePoolSize;

    @Value("${async.executor.max-pool-size:50}")
    private int maxPoolSize;

    @Value("${async.executor.queue-capacity:100}")
    private int queueCapacity;

    @Value("${async.executor.keep-alive-seconds:60}")
    private int keepAliveSeconds;

    @Value("${async.executor.thread-name-prefix:mca-async-}")
    private String threadNamePrefix;

    /**
     * Creates and configures the primary task executor for asynchronous operations.
     * This executor is used by default for all @Async annotated methods.
     *
     * @return Configured ThreadPoolTaskExecutor
     */
    @Override
    @Bean(name = "taskExecutor")
    public Executor getAsyncExecutor() {
        log.info("Creating Async Task Executor with core pool size: {}, max pool size: {}, queue capacity: {}", 
                corePoolSize, maxPoolSize, queueCapacity);
        
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(corePoolSize);
        executor.setMaxPoolSize(maxPoolSize);
        executor.setQueueCapacity(queueCapacity);
        executor.setKeepAliveSeconds(keepAliveSeconds);
        executor.setThreadNamePrefix(threadNamePrefix);
        
        // Use CallerRunsPolicy to avoid task rejection when queue is full
        // This will execute the task in the caller's thread as a fallback mechanism
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        
        // This setting helps with proper shutdown of the executor
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(60);
        
        executor.initialize();
        return executor;
    }

    /**
     * Creates a dedicated task executor for document processing operations.
     * This executor is optimized for CPU-intensive tasks with appropriate thread sizing.
     *
     * @return Configured ThreadPoolTaskExecutor for document processing
     */
    @Bean(name = "documentProcessingExecutor")
    public Executor documentProcessingExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        // Use smaller pool for CPU-intensive tasks to avoid context switching overhead
        executor.setCorePoolSize(Runtime.getRuntime().availableProcessors());
        executor.setMaxPoolSize(Runtime.getRuntime().availableProcessors() * 2);
        executor.setQueueCapacity(50);
        executor.setThreadNamePrefix("doc-proc-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.initialize();
        return executor;
    }

    /**
     * Creates a dedicated task executor for webhook delivery operations.
     * This executor is optimized for I/O-bound tasks with larger thread pools.
     *
     * @return Configured ThreadPoolTaskExecutor for webhook delivery
     */
    @Bean(name = "webhookDeliveryExecutor")
    public Executor webhookDeliveryExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        // Use larger pool for I/O-bound tasks to maximize throughput
        executor.setCorePoolSize(20);
        executor.setMaxPoolSize(100);
        executor.setQueueCapacity(200);
        executor.setThreadNamePrefix("webhook-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.AbortPolicy());
        executor.initialize();
        return executor;
    }

    /**
     * Configures the exception handler for asynchronous methods.
     * This handler is invoked when an uncaught exception occurs in an @Async method with void return type.
     *
     * @return AsyncUncaughtExceptionHandler implementation
     */
    @Override
    public AsyncUncaughtExceptionHandler getAsyncUncaughtExceptionHandler() {
        return new MCAAsyncExceptionHandler();
    }

    /**
     * Custom implementation of AsyncUncaughtExceptionHandler to handle exceptions
     * thrown by asynchronous methods with void return type.
     */
    private static class MCAAsyncExceptionHandler implements AsyncUncaughtExceptionHandler {
        private final Logger logger = LoggerFactory.getLogger(MCAAsyncExceptionHandler.class);

        @Override
        public void handleUncaughtException(Throwable ex, Method method, Object... params) {
            if (ex instanceof RejectedExecutionException) {
                logger.error("Task execution rejected for method [{}] with parameters {}. Thread pool is saturated.", 
                        method.getName(), params, ex);
            } else {
                logger.error("Unexpected error occurred during async execution of method [{}] in class [{}] with parameters {}", 
                        method.getName(), method.getDeclaringClass().getName(), params, ex);
            }
            
            // Additional handling for specific exception types
            if (ex instanceof InterruptedException) {
                // Restore the interrupted status
                Thread.currentThread().interrupt();
                logger.warn("Async task interrupted: {}", method.getName());
            }
        }
    }
}