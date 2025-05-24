package com.dollarfunding.mca.config;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.datasource.LazyConnectionDataSourceProxy;
import org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.context.annotation.EnableAspectJAutoProxy;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import javax.sql.DataSource;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Custom annotation to mark methods that should use read replicas.
 * This can be used in service methods that only perform read operations.
 * 
 * Example usage:
 * <pre>
 * {@code
 * @Service
 * public class ApplicationService {
 *     
 *     @ReadOnlyOperation
 *     public List<Application> findAllApplications() {
 *         // This method will use a read replica
 *         return applicationRepository.findAll();
 *     }
 *     
 *     public Application saveApplication(Application application) {
 *         // This method will use the primary database
 *         return applicationRepository.save(application);
 *     }
 * }
 * }
 * </pre>
 * 
 * The annotation works by wrapping the method execution in a read-only transaction,
 * which signals to the routing data source to use a read replica.
 */
@Target({ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
public @interface ReadOnlyOperation {
}

/**
 * Database configuration for the MCA application.
 * 
 * This class configures the PostgreSQL database connection with primary and read replica support.
 * It sets up connection pooling with HikariCP and configures transaction management.
 * 
 * Key features:
 * - Primary database for write operations
 * - Read replicas for read operations
 * - Connection pooling with optimized settings
 * - Transaction management with appropriate isolation levels
 * - Support for multiple environments (dev, staging, prod)
 * - @ReadOnlyOperation annotation for explicitly marking read-only methods
 * 
 * Read/Write Splitting:
 * This configuration automatically routes read operations to read replicas and write operations
 * to the primary database. It uses Spring's transaction synchronization to determine if a
 * transaction is read-only, and routes accordingly. There are two ways to trigger read-only routing:
 * 
 * 1. Using @Transactional(readOnly = true):
 *    <pre>
 *    {@code
 *    @Service
 *    public class ApplicationService {
 *        
 *        @Transactional(readOnly = true)
 *        public List<Application> findAllApplications() {
 *            // This method will use a read replica
 *            return applicationRepository.findAll();
 *        }
 *    }
 *    }
 *    </pre>
 * 
 * 2. Using the custom @ReadOnlyOperation annotation:
 *    <pre>
 *    {@code
 *    @Service
 *    public class ApplicationService {
 *        
 *        @ReadOnlyOperation
 *        public List<Application> findAllApplications() {
 *            // This method will use a read replica
 *            return applicationRepository.findAll();
 *        }
 *    }
 *    }
 *    </pre>
 * 
 * Load Balancing:
 * When multiple read replicas are configured, this implementation uses a round-robin
 * strategy to distribute read operations across all available replicas. This helps to
 * balance the load and improve overall system performance.
 */
@Configuration
@EnableTransactionManagement
@EnableAspectJAutoProxy
public class DatabaseConfig {

    @Autowired
    private Environment env;

    @Value("${spring.datasource.url}")
    private String primaryDbUrl;

    @Value("${spring.datasource.username}")
    private String username;

    @Value("${spring.datasource.password}")
    private String password;

    @Value("${spring.datasource.driver-class-name}")
    private String driverClassName;

    @Value("${spring.datasource.hikari.maximum-pool-size:10}")
    private int maximumPoolSize;

    @Value("${spring.datasource.hikari.minimum-idle:5}")
    private int minimumIdle;

    @Value("${spring.datasource.hikari.idle-timeout:30000}")
    private long idleTimeout;

    @Value("${spring.datasource.hikari.connection-timeout:30000}")
    private long connectionTimeout;

    @Value("${spring.datasource.hikari.max-lifetime:2000000}")
    private long maxLifetime;

    @Value("${spring.datasource.hikari.auto-commit:false}")
    private boolean autoCommit;

    @Value("${spring.datasource.hikari.pool-name:MCAHikariCP}")
    private String poolName;

    @Value("${spring.datasource.hikari.read-only-replicas:false}")
    private boolean readOnlyReplicas;

    @Value("${spring.datasource.hikari.replica-urls:}")
    private String replicaUrls;

    /**
     * Enum representing database types for routing.
     */
    public enum DbType {
        PRIMARY, REPLICA
    }

    /**
     * Creates the primary database data source with HikariCP connection pooling.
     * 
     * @return DataSource for the primary database
     */
    @Bean(name = "primaryDataSource")
    public DataSource primaryDataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(primaryDbUrl);
        config.setUsername(username);
        config.setPassword(password);
        config.setDriverClassName(driverClassName);
        config.setMaximumPoolSize(maximumPoolSize);
        config.setMinimumIdle(minimumIdle);
        config.setIdleTimeout(idleTimeout);
        config.setConnectionTimeout(connectionTimeout);
        config.setMaxLifetime(maxLifetime);
        config.setAutoCommit(autoCommit);
        config.setPoolName(poolName + "-Primary");
        
        // Set PostgreSQL specific properties
        config.addDataSourceProperty("cachePrepStmts", "true");
        config.addDataSourceProperty("prepStmtCacheSize", "250");
        config.addDataSourceProperty("prepStmtCacheSqlLimit", "2048");
        config.addDataSourceProperty("useServerPrepStmts", "true");
        
        // Set transaction isolation level to READ COMMITTED (PostgreSQL default)
        config.setTransactionIsolation("TRANSACTION_READ_COMMITTED");
        
        return new HikariDataSource(config);
    }

    /**
     * Creates read replica data sources with HikariCP connection pooling.
     * 
     * @return List of DataSource objects for read replicas
     */
    @Bean(name = "replicaDataSources")
    public List<DataSource> replicaDataSources() {
        if (!readOnlyReplicas || replicaUrls == null || replicaUrls.isEmpty()) {
            return List.of();
        }

        String[] replicaUrlArray = replicaUrls.split(",");
        return Arrays.stream(replicaUrlArray)
                .map(url -> {
                    HikariConfig config = new HikariConfig();
                    config.setJdbcUrl(url.trim());
                    config.setUsername(username);
                    config.setPassword(password);
                    config.setDriverClassName(driverClassName);
                    config.setMaximumPoolSize(maximumPoolSize);
                    config.setMinimumIdle(minimumIdle);
                    config.setIdleTimeout(idleTimeout);
                    config.setConnectionTimeout(connectionTimeout);
                    config.setMaxLifetime(maxLifetime);
                    config.setAutoCommit(autoCommit);
                    config.setReadOnly(true); // Read replicas are read-only
                    config.setPoolName(poolName + "-Replica-" + url.hashCode());
                    
                    // Set PostgreSQL specific properties
                    config.addDataSourceProperty("cachePrepStmts", "true");
                    config.addDataSourceProperty("prepStmtCacheSize", "250");
                    config.addDataSourceProperty("prepStmtCacheSqlLimit", "2048");
                    config.addDataSourceProperty("useServerPrepStmts", "true");
                    
                    // Set transaction isolation level to READ COMMITTED (PostgreSQL default)
                    config.setTransactionIsolation("TRANSACTION_READ_COMMITTED");
                    
                    return new HikariDataSource(config);
                })
                .toList();
    }

    /**
     * Custom implementation of AbstractRoutingDataSource that routes database requests
     * to either the primary database or a read replica based on the transaction context.
     * It implements a simple round-robin load balancing strategy for multiple replicas.
     */
    public static class RoutingDataSource extends AbstractRoutingDataSource {
        private final AtomicInteger replicaCounter = new AtomicInteger(0);
        private int replicaCount = 1;
        
        public void setReplicaCount(int count) {
            this.replicaCount = Math.max(1, count);
        }
        
        @Override
        protected Object determineCurrentLookupKey() {
            // Use read replica if the current transaction is read-only
            if (TransactionSynchronizationManager.isCurrentTransactionReadOnly()) {
                if (replicaCount <= 1) {
                    return DbType.REPLICA;
                } else {
                    // Round-robin load balancing across multiple replicas
                    int replicaIndex = replicaCounter.getAndIncrement() % replicaCount;
                    if (replicaCounter.get() > 10000) { // Reset to prevent overflow
                        replicaCounter.set(0);
                    }
                    return "REPLICA_" + replicaIndex;
                }
            }
            return DbType.PRIMARY;
        }
    }

    /**
     * Creates a routing data source that directs read operations to replicas
     * and write operations to the primary database.
     * 
     * @param primaryDataSource The primary database data source
     * @param replicaDataSources List of read replica data sources
     * @return RoutingDataSource that can switch between primary and replicas
     */
    @Bean(name = "routingDataSource")
    public DataSource routingDataSource(
            @Qualifier("primaryDataSource") DataSource primaryDataSource,
            @Qualifier("replicaDataSources") List<DataSource> replicaDataSources) {
        
        RoutingDataSource routingDataSource = new RoutingDataSource();
        
        Map<Object, Object> targetDataSources = new HashMap<>();
        targetDataSources.put(DbType.PRIMARY, primaryDataSource);
        
        if (replicaDataSources.isEmpty()) {
            // No replicas available, use primary for all operations
            targetDataSources.put(DbType.REPLICA, primaryDataSource);
            routingDataSource.setReplicaCount(1);
        } else if (replicaDataSources.size() == 1) {
            // Single replica available
            targetDataSources.put(DbType.REPLICA, replicaDataSources.get(0));
            routingDataSource.setReplicaCount(1);
        } else {
            // Multiple replicas available, set up load balancing
            for (int i = 0; i < replicaDataSources.size(); i++) {
                targetDataSources.put("REPLICA_" + i, replicaDataSources.get(i));
            }
            routingDataSource.setReplicaCount(replicaDataSources.size());
        }
        
        routingDataSource.setTargetDataSources(targetDataSources);
        routingDataSource.setDefaultTargetDataSource(primaryDataSource);
        
        return routingDataSource;
    }

    /**
     * Creates a lazy connection data source proxy to defer physical connection acquisition
     * until the connection is actually used.
     * 
     * @param routingDataSource The routing data source
     * @return LazyConnectionDataSourceProxy wrapping the routing data source
     */
    @Primary
    @Bean(name = "dataSource")
    public DataSource dataSource(@Qualifier("routingDataSource") DataSource routingDataSource) {
        return new LazyConnectionDataSourceProxy(routingDataSource);
    }

    /**
     * Creates a transaction manager that is aware of the read/write splitting configuration.
     * This ensures that read-only transactions are properly routed to replicas.
     * 
     * @param dataSource The configured data source
     * @return PlatformTransactionManager for managing transactions
     */
    @Bean
    public PlatformTransactionManager transactionManager(@Qualifier("dataSource") DataSource dataSource) {
        return new org.springframework.jdbc.datasource.DataSourceTransactionManager(dataSource);
    }

    /**
     * Configures JPA properties for the EntityManagerFactory.
     * 
     * @return Map of JPA properties
     */
    @Bean
    public Map<String, Object> jpaProperties() {
        Map<String, Object> props = new HashMap<>();
        props.put("hibernate.dialect", "org.hibernate.dialect.PostgreSQLDialect");
        props.put("hibernate.format_sql", env.getProperty("spring.jpa.properties.hibernate.format_sql", "true"));
        props.put("hibernate.jdbc.batch_size", env.getProperty("spring.jpa.properties.hibernate.jdbc.batch_size", Integer.class, 50));
        props.put("hibernate.order_inserts", env.getProperty("spring.jpa.properties.hibernate.order_inserts", "true"));
        props.put("hibernate.order_updates", env.getProperty("spring.jpa.properties.hibernate.order_updates", "true"));
        props.put("hibernate.jdbc.time_zone", "UTC");
        
        // Add second-level cache configuration if enabled
        if (Boolean.parseBoolean(env.getProperty("spring.jpa.properties.hibernate.cache.use_second_level_cache", "false"))) {
            props.put("hibernate.cache.use_second_level_cache", "true");
            props.put("hibernate.cache.use_query_cache", env.getProperty("spring.jpa.properties.hibernate.cache.use_query_cache", "false"));
            props.put("hibernate.cache.region.factory_class", env.getProperty(
                    "spring.jpa.properties.hibernate.cache.region.factory_class", 
                    "org.hibernate.cache.jcache.JCacheRegionFactory"));
        }
        
        // Performance optimizations
        props.put("hibernate.connection.provider_disables_autocommit", 
                env.getProperty("spring.jpa.properties.hibernate.connection.provider_disables_autocommit", "true"));
        props.put("hibernate.query.in_clause_parameter_padding", 
                env.getProperty("spring.jpa.properties.hibernate.query.in_clause_parameter_padding", "true"));
        props.put("hibernate.query.fail_on_pagination_over_collection_fetch", 
                env.getProperty("spring.jpa.properties.hibernate.query.fail_on_pagination_over_collection_fetch", "true"));
        
        return props;
    }
    
    /**
     * Aspect that handles the @ReadOnlyOperation annotation.
     * Methods annotated with @ReadOnlyOperation will be executed in a read-only transaction,
     * which will be routed to a read replica.
     */
    @Bean
    @Aspect
    public ReadOnlyOperationAspect readOnlyOperationAspect() {
        return new ReadOnlyOperationAspect();
    }
    
    /**
     * Aspect implementation for handling @ReadOnlyOperation annotation.
     */
    public static class ReadOnlyOperationAspect {
        
        /**
         * Intercepts methods annotated with @ReadOnlyOperation and executes them
         * in a read-only transaction context.
         * 
         * @param joinPoint The join point representing the intercepted method
         * @return The result of the method execution
         * @throws Throwable If an error occurs during method execution
         */
        @Around("@annotation(com.dollarfunding.mca.config.DatabaseConfig.ReadOnlyOperation)")
        @Transactional(readOnly = true, propagation = Propagation.REQUIRED)
        public Object enforceReadOnly(ProceedingJoinPoint joinPoint) throws Throwable {
            return joinPoint.proceed();
        }
    }
}