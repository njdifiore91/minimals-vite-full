package com.dollarfunding.mca.config;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Aspect that routes read-only operations to read replicas.
 * 
 * This aspect intercepts methods annotated with @Transactional(readOnly = true)
 * and routes them to read replica databases by setting the current operation type
 * to READ in the DatabaseConfig.
 */
@Aspect
@Order(0) // High precedence to ensure it runs before transaction aspects
@Component
public class ReadOnlyRoutingAspect {

    /**
     * Intercepts methods annotated with @Transactional(readOnly = true) and routes them to read replicas.
     * 
     * @param joinPoint The join point representing the intercepted method
     * @return The result of the method execution
     * @throws Throwable If an error occurs during method execution
     */
    @Around("@annotation(transactional)")
    public Object routeReadOnlyOperations(ProceedingJoinPoint joinPoint, Transactional transactional) throws Throwable {
        // Check if the transaction is read-only
        if (transactional.readOnly()) {
            try {
                // Set operation type to READ to route to read replicas
                DatabaseConfig.setCurrentOperation(DatabaseConfig.OperationType.READ);
                return joinPoint.proceed();
            } finally {
                // Reset operation type after method execution
                DatabaseConfig.clearCurrentOperation();
            }
        } else {
            // For write operations, use the default (WRITE) operation type
            return joinPoint.proceed();
        }
    }

    /**
     * Intercepts methods in repositories with names starting with "find", "get", "read", "query", or "count"
     * and routes them to read replicas.
     * 
     * @param joinPoint The join point representing the intercepted method
     * @return The result of the method execution
     * @throws Throwable If an error occurs during method execution
     */
    @Around("execution(* com.dollarfunding.mca.repository.*Repository.find*(..)) || " +
            "execution(* com.dollarfunding.mca.repository.*Repository.get*(..)) || " +
            "execution(* com.dollarfunding.mca.repository.*Repository.read*(..)) || " +
            "execution(* com.dollarfunding.mca.repository.*Repository.query*(..)) || " +
            "execution(* com.dollarfunding.mca.repository.*Repository.count*(..))")
    public Object routeReadOperations(ProceedingJoinPoint joinPoint) throws Throwable {
        try {
            // Set operation type to READ to route to read replicas
            DatabaseConfig.setCurrentOperation(DatabaseConfig.OperationType.READ);
            return joinPoint.proceed();
        } finally {
            // Reset operation type after method execution
            DatabaseConfig.clearCurrentOperation();
        }
    }
}