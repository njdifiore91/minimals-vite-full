package com.dollarfunding.mca.config;

import com.zaxxer.hikari.HikariDataSource;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.jdbc.datasource.LazyConnectionDataSourceProxy;
import org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.orm.jpa.vendor.HibernateJpaVendorAdapter;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;

import javax.sql.DataSource;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;

/**
 * Database configuration for the MCA application.
 * 
 * This class configures the PostgreSQL database connection with primary and read replica support.
 * It sets up connection pooling, transaction management, and routing of read/write operations
 * to the appropriate database instance.
 * 
 * Key features:
 * - Primary database for write operations
 * - Read replicas for read operations to improve performance
 * - HikariCP connection pool with optimized settings
 * - Transaction management with appropriate isolation levels
 * - JPA/Hibernate properties for efficient database operations
 */
@Configuration
@EnableTransactionManagement
@EnableJpaRepositories(basePackages = "com.dollarfunding.mca.repository")
public class DatabaseConfig {

    /**
     * Enum representing the database operation type.
     * Used by the routing data source to determine which data source to use.
     */
    public enum OperationType {
        READ, WRITE
    }

    /**
     * ThreadLocal variable to store the current operation type.
     * This is used by the routing data source to determine which data source to use.
     */
    private static final ThreadLocal<OperationType> currentOperation = new ThreadLocal<OperationType>() {
        @Override
        protected OperationType initialValue() {
            return OperationType.WRITE; // Default to write operation
        }
    };

    /**
     * Sets the current operation type for the current thread.
     * 
     * @param operationType The operation type to set
     */
    public static void setCurrentOperation(OperationType operationType) {
        currentOperation.set(operationType);
    }

    /**
     * Gets the current operation type for the current thread.
     * 
     * @return The current operation type
     */
    public static OperationType getCurrentOperation() {
        return currentOperation.get();
    }

    /**
     * Clears the current operation type for the current thread.
     */
    public static void clearCurrentOperation() {
        currentOperation.remove();
    }

    /**
     * Primary data source properties configuration.
     * 
     * @return DataSourceProperties for the primary data source
     */
    @Bean
    @Primary
    @ConfigurationProperties("spring.datasource")
    public DataSourceProperties primaryDataSourceProperties() {
        return new DataSourceProperties();
    }

    /**
     * Primary data source configuration with HikariCP connection pool.
     * This data source is used for write operations.
     * 
     * @return The configured primary data source
     */
    @Bean
    @Primary
    @ConfigurationProperties("spring.datasource.hikari")
    public HikariDataSource primaryDataSource() {
        HikariDataSource dataSource = primaryDataSourceProperties()
                .initializeDataSourceBuilder()
                .type(HikariDataSource.class)
                .build();
        
        dataSource.setPoolName("PrimaryHikariPool");
        return dataSource;
    }

    /**
     * Read replica data source properties configuration.
     * 
     * @return DataSourceProperties for the read replica data source
     */
    @Bean
    @ConfigurationProperties("spring.datasource.replica")
    public DataSourceProperties replicaDataSourceProperties() {
        return new DataSourceProperties();
    }

    /**
     * Read replica data source configuration.
     * This method creates a data source for each read replica configured in the application properties.
     * 
     * @param replicaUrls List of replica URLs from application properties
     * @param replicaUsername Username for read replicas
     * @param replicaPassword Password for read replicas
     * @return Map of read replica data sources
     */
    @Bean
    public Map<String, DataSource> readReplicaDataSources(
            @Value("${spring.datasource.replica.nodes:#{null}}")
            List<Map<String, String>> replicaNodes,
            @Value("${spring.datasource.replica.enabled:false}")
            boolean replicaEnabled) {
        
        Map<String, DataSource> replicaDataSources = new HashMap<>();
        
        // If replicas are not enabled or no replica nodes are configured, return empty map
        if (!replicaEnabled || replicaNodes == null || replicaNodes.isEmpty()) {
            return replicaDataSources;
        }
        
        // Create a data source for each replica node
        for (int i = 0; i < replicaNodes.size(); i++) {
            Map<String, String> node = replicaNodes.get(i);
            String url = node.get("url");
            String username = node.get("username");
            String password = node.get("password");
            
            if (url != null && !url.isEmpty()) {
                HikariDataSource replicaDataSource = new HikariDataSource();
                replicaDataSource.setJdbcUrl(url);
                replicaDataSource.setUsername(username);
                replicaDataSource.setPassword(password);
                replicaDataSource.setPoolName("ReplicaHikariPool-" + i);
                
                // Copy connection pool settings from primary data source
                HikariDataSource primaryDs = primaryDataSource();
                replicaDataSource.setMaximumPoolSize(primaryDs.getMaximumPoolSize());
                replicaDataSource.setMinimumIdle(primaryDs.getMinimumIdle());
                replicaDataSource.setIdleTimeout(primaryDs.getIdleTimeout());
                replicaDataSource.setMaxLifetime(primaryDs.getMaxLifetime());
                replicaDataSource.setConnectionTimeout(primaryDs.getConnectionTimeout());
                replicaDataSource.setReadOnly(true); // Ensure replica is read-only
                
                replicaDataSources.put("replica-" + i, replicaDataSource);
            }
        }
        
        return replicaDataSources;
    }

    /**
     * Routing data source that directs read/write operations to the appropriate data source.
     * Write operations go to the primary data source, while read operations are distributed
     * across the read replicas.
     * 
     * @param primaryDataSource The primary data source
     * @param readReplicaDataSources Map of read replica data sources
     * @return The configured routing data source
     */
    @Bean
    public AbstractRoutingDataSource routingDataSource(
            @Qualifier("primaryDataSource") DataSource primaryDataSource,
            @Qualifier("readReplicaDataSources") Map<String, DataSource> readReplicaDataSources) {
        
        AbstractRoutingDataSource routingDataSource = new AbstractRoutingDataSource() {
            @Override
            protected Object determineCurrentLookupKey() {
                OperationType operationType = getCurrentOperation();
                
                // If operation is READ and we have replicas, use a replica
                if (operationType == OperationType.READ && !readReplicaDataSources.isEmpty()) {
                    // Simple round-robin selection among replicas
                    int replicaIndex = (int) (System.nanoTime() % readReplicaDataSources.size());
                    return "replica-" + replicaIndex;
                }
                
                // Default to primary for WRITE operations or if no replicas are available
                return "primary";
            }
        };
        
        // Set up data sources map
        Map<Object, Object> dataSources = new HashMap<>();
        dataSources.put("primary", primaryDataSource);
        readReplicaDataSources.forEach(dataSources::put);
        
        routingDataSource.setTargetDataSources(dataSources);
        routingDataSource.setDefaultTargetDataSource(primaryDataSource); // Default to primary
        
        return routingDataSource;
    }

    /**
     * Lazy connection data source proxy to defer actual connection acquisition until needed.
     * This improves performance by not acquiring a connection until it's actually used.
     * 
     * @param routingDataSource The routing data source
     * @return The lazy connection data source proxy
     */
    @Bean
    public LazyConnectionDataSourceProxy lazyConnectionDataSource(
            @Qualifier("routingDataSource") AbstractRoutingDataSource routingDataSource) {
        return new LazyConnectionDataSourceProxy(routingDataSource);
    }

    /**
     * The actual data source used by the application.
     * This is the data source that should be injected into repositories and services.
     * 
     * @param lazyConnectionDataSource The lazy connection data source proxy
     * @return The final data source
     */
    @Bean
    public DataSource dataSource(
            @Qualifier("lazyConnectionDataSource") LazyConnectionDataSourceProxy lazyConnectionDataSource) {
        return lazyConnectionDataSource;
    }

    /**
     * Entity manager factory configuration.
     * 
     * @param dataSource The data source
     * @return The configured entity manager factory
     */
    @Bean
    public LocalContainerEntityManagerFactoryBean entityManagerFactory(
            @Qualifier("dataSource") DataSource dataSource) {
        
        LocalContainerEntityManagerFactoryBean em = new LocalContainerEntityManagerFactoryBean();
        em.setDataSource(dataSource);
        em.setPackagesToScan("com.dollarfunding.mca.entity");
        
        HibernateJpaVendorAdapter vendorAdapter = new HibernateJpaVendorAdapter();
        vendorAdapter.setGenerateDdl(false); // We use Flyway for schema management
        em.setJpaVendorAdapter(vendorAdapter);
        
        // Set JPA properties
        Properties jpaProperties = new Properties();
        jpaProperties.put("hibernate.dialect", "org.hibernate.dialect.PostgreSQLDialect");
        jpaProperties.put("hibernate.jdbc.batch_size", 50);
        jpaProperties.put("hibernate.order_inserts", true);
        jpaProperties.put("hibernate.order_updates", true);
        jpaProperties.put("hibernate.jdbc.time_zone", "UTC");
        jpaProperties.put("hibernate.connection.provider_disables_autocommit", true);
        
        // Add query cache settings
        jpaProperties.put("hibernate.cache.use_second_level_cache", false);
        jpaProperties.put("hibernate.cache.use_query_cache", false);
        
        // Add statement cache settings
        jpaProperties.put("hibernate.jdbc.use_get_generated_keys", true);
        
        em.setJpaProperties(jpaProperties);
        
        return em;
    }

    /**
     * Transaction manager configuration.
     * 
     * @param entityManagerFactory The entity manager factory
     * @return The configured transaction manager
     */
    @Bean
    public PlatformTransactionManager transactionManager(
            LocalContainerEntityManagerFactoryBean entityManagerFactory) {
        
        JpaTransactionManager transactionManager = new JpaTransactionManager();
        transactionManager.setEntityManagerFactory(entityManagerFactory.getObject());
        
        return transactionManager;
    }

    /**
     * Production-specific database configuration.
     */
    @Configuration
    @Profile("production")
    public static class ProductionDatabaseConfig {
        
        /**
         * Production-specific HikariCP settings for the primary data source.
         * 
         * @param dataSource The primary data source
         * @return The configured primary data source with production settings
         */
        @Bean
        @Primary
        @ConfigurationProperties("spring.datasource.hikari")
        public HikariDataSource productionPrimaryDataSource(HikariDataSource dataSource) {
            // Production-specific settings
            dataSource.setMaximumPoolSize(20); // Higher pool size for production
            dataSource.setMinimumIdle(5);
            dataSource.setIdleTimeout(120000); // 2 minutes
            dataSource.setMaxLifetime(1800000); // 30 minutes
            
            return dataSource;
        }
    }

    /**
     * Development-specific database configuration.
     */
    @Configuration
    @Profile("development")
    public static class DevelopmentDatabaseConfig {
        
        /**
         * Development-specific HikariCP settings for the primary data source.
         * 
         * @param dataSource The primary data source
         * @return The configured primary data source with development settings
         */
        @Bean
        @Primary
        @ConfigurationProperties("spring.datasource.hikari")
        public HikariDataSource developmentPrimaryDataSource(HikariDataSource dataSource) {
            // Development-specific settings
            dataSource.setMaximumPoolSize(10); // Lower pool size for development
            dataSource.setMinimumIdle(5);
            dataSource.setIdleTimeout(300000); // 5 minutes
            dataSource.setMaxLifetime(1200000); // 20 minutes
            
            return dataSource;
        }
    }
}