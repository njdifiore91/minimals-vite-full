package com.dollarfunding.mca.config;

import com.zaxxer.hikari.HikariDataSource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.datasource.LazyConnectionDataSourceProxy;
import org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import javax.sql.DataSource;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the {@link DatabaseConfig} class.
 * 
 * These tests verify the proper configuration of PostgreSQL database connections
 * with primary and read replica support, connection pooling settings, read replica
 * routing, and transaction management configuration.
 */
@ExtendWith(MockitoExtension.class)
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:postgresql://primary-db:5432/mca_application_db",
    "spring.datasource.username=mca_app_user",
    "spring.datasource.password=test_password",
    "spring.datasource.driver-class-name=org.postgresql.Driver",
    "spring.datasource.hikari.maximum-pool-size=10",
    "spring.datasource.hikari.minimum-idle=5",
    "spring.datasource.hikari.idle-timeout=30000",
    "spring.datasource.hikari.connection-timeout=30000",
    "spring.datasource.hikari.max-lifetime=2000000",
    "spring.datasource.hikari.auto-commit=false",
    "spring.datasource.hikari.pool-name=TestHikariCP",
    "spring.datasource.hikari.read-only-replicas=true",
    "spring.datasource.hikari.replica-urls=jdbc:postgresql://replica1:5432/mca_application_db,jdbc:postgresql://replica2:5432/mca_application_db"
})
public class DatabaseConfigTest {

    @Mock
    private Environment environment;

    @InjectMocks
    private DatabaseConfig databaseConfig;

    @BeforeEach
    public void setup() {
        // Set up required properties using reflection since @TestPropertySource doesn't work with @InjectMocks
        ReflectionTestUtils.setField(databaseConfig, "primaryDbUrl", "jdbc:postgresql://primary-db:5432/mca_application_db");
        ReflectionTestUtils.setField(databaseConfig, "username", "mca_app_user");
        ReflectionTestUtils.setField(databaseConfig, "password", "test_password");
        ReflectionTestUtils.setField(databaseConfig, "driverClassName", "org.postgresql.Driver");
        ReflectionTestUtils.setField(databaseConfig, "maximumPoolSize", 10);
        ReflectionTestUtils.setField(databaseConfig, "minimumIdle", 5);
        ReflectionTestUtils.setField(databaseConfig, "idleTimeout", 30000L);
        ReflectionTestUtils.setField(databaseConfig, "connectionTimeout", 30000L);
        ReflectionTestUtils.setField(databaseConfig, "maxLifetime", 2000000L);
        ReflectionTestUtils.setField(databaseConfig, "autoCommit", false);
        ReflectionTestUtils.setField(databaseConfig, "poolName", "TestHikariCP");
        ReflectionTestUtils.setField(databaseConfig, "readOnlyReplicas", true);
        ReflectionTestUtils.setField(databaseConfig, "replicaUrls", "jdbc:postgresql://replica1:5432/mca_application_db,jdbc:postgresql://replica2:5432/mca_application_db");

        // Mock environment properties for JPA configuration
        when(environment.getProperty("spring.jpa.properties.hibernate.format_sql", "true")).thenReturn("true");
        when(environment.getProperty("spring.jpa.properties.hibernate.jdbc.batch_size", Integer.class, 50)).thenReturn(50);
        when(environment.getProperty("spring.jpa.properties.hibernate.order_inserts", "true")).thenReturn("true");
        when(environment.getProperty("spring.jpa.properties.hibernate.order_updates", "true")).thenReturn("true");
        when(environment.getProperty("spring.jpa.properties.hibernate.cache.use_second_level_cache", "false")).thenReturn("false");
        when(environment.getProperty("spring.jpa.properties.hibernate.connection.provider_disables_autocommit", "true")).thenReturn("true");
        when(environment.getProperty("spring.jpa.properties.hibernate.query.in_clause_parameter_padding", "true")).thenReturn("true");
        when(environment.getProperty("spring.jpa.properties.hibernate.query.fail_on_pagination_over_collection_fetch", "true")).thenReturn("true");
    }

    @Test
    @DisplayName("Test primary data source configuration with HikariCP")
    public void testPrimaryDataSource() {
        // When
        DataSource dataSource = databaseConfig.primaryDataSource();

        // Then
        assertNotNull(dataSource, "Primary data source should not be null");
        assertTrue(dataSource instanceof HikariDataSource, "Primary data source should be a HikariDataSource");

        HikariDataSource hikariDataSource = (HikariDataSource) dataSource;
        assertEquals("jdbc:postgresql://primary-db:5432/mca_application_db", hikariDataSource.getJdbcUrl(), "JDBC URL should match");
        assertEquals("mca_app_user", hikariDataSource.getUsername(), "Username should match");
        assertEquals("test_password", hikariDataSource.getPassword(), "Password should match");
        assertEquals("org.postgresql.Driver", hikariDataSource.getDriverClassName(), "Driver class name should match");
        assertEquals(10, hikariDataSource.getMaximumPoolSize(), "Maximum pool size should match");
        assertEquals(5, hikariDataSource.getMinimumIdle(), "Minimum idle should match");
        assertEquals(30000, hikariDataSource.getIdleTimeout(), "Idle timeout should match");
        assertEquals(30000, hikariDataSource.getConnectionTimeout(), "Connection timeout should match");
        assertEquals(2000000, hikariDataSource.getMaxLifetime(), "Max lifetime should match");
        assertFalse(hikariDataSource.isAutoCommit(), "Auto commit should be false");
        assertEquals("TestHikariCP-Primary", hikariDataSource.getPoolName(), "Pool name should match");

        // Verify PostgreSQL specific properties
        assertEquals("true", hikariDataSource.getDataSourceProperties().getProperty("cachePrepStmts"), "cachePrepStmts should be true");
        assertEquals("250", hikariDataSource.getDataSourceProperties().getProperty("prepStmtCacheSize"), "prepStmtCacheSize should be 250");
        assertEquals("2048", hikariDataSource.getDataSourceProperties().getProperty("prepStmtCacheSqlLimit"), "prepStmtCacheSqlLimit should be 2048");
        assertEquals("true", hikariDataSource.getDataSourceProperties().getProperty("useServerPrepStmts"), "useServerPrepStmts should be true");

        // Verify transaction isolation level
        assertEquals("TRANSACTION_READ_COMMITTED", hikariDataSource.getTransactionIsolation(), "Transaction isolation level should be READ COMMITTED");
    }

    @Test
    @DisplayName("Test read replica data sources configuration")
    public void testReplicaDataSources() {
        // When
        List<DataSource> replicaDataSources = databaseConfig.replicaDataSources();

        // Then
        assertNotNull(replicaDataSources, "Replica data sources should not be null");
        assertEquals(2, replicaDataSources.size(), "Should have 2 replica data sources");

        for (int i = 0; i < replicaDataSources.size(); i++) {
            DataSource dataSource = replicaDataSources.get(i);
            assertTrue(dataSource instanceof HikariDataSource, "Replica data source should be a HikariDataSource");

            HikariDataSource hikariDataSource = (HikariDataSource) dataSource;
            assertTrue(hikariDataSource.getJdbcUrl().startsWith("jdbc:postgresql://replica"), "JDBC URL should be for a replica");
            assertEquals("mca_app_user", hikariDataSource.getUsername(), "Username should match");
            assertEquals("test_password", hikariDataSource.getPassword(), "Password should match");
            assertEquals("org.postgresql.Driver", hikariDataSource.getDriverClassName(), "Driver class name should match");
            assertEquals(10, hikariDataSource.getMaximumPoolSize(), "Maximum pool size should match");
            assertEquals(5, hikariDataSource.getMinimumIdle(), "Minimum idle should match");
            assertEquals(30000, hikariDataSource.getIdleTimeout(), "Idle timeout should match");
            assertEquals(30000, hikariDataSource.getConnectionTimeout(), "Connection timeout should match");
            assertEquals(2000000, hikariDataSource.getMaxLifetime(), "Max lifetime should match");
            assertFalse(hikariDataSource.isAutoCommit(), "Auto commit should be false");
            assertTrue(hikariDataSource.getPoolName().contains("TestHikariCP-Replica"), "Pool name should contain 'TestHikariCP-Replica'");
            
            // Verify read-only flag
            assertTrue(hikariDataSource.isReadOnly(), "Replica should be read-only");

            // Verify PostgreSQL specific properties
            assertEquals("true", hikariDataSource.getDataSourceProperties().getProperty("cachePrepStmts"), "cachePrepStmts should be true");
            assertEquals("250", hikariDataSource.getDataSourceProperties().getProperty("prepStmtCacheSize"), "prepStmtCacheSize should be 250");
            assertEquals("2048", hikariDataSource.getDataSourceProperties().getProperty("prepStmtCacheSqlLimit"), "prepStmtCacheSqlLimit should be 2048");
            assertEquals("true", hikariDataSource.getDataSourceProperties().getProperty("useServerPrepStmts"), "useServerPrepStmts should be true");

            // Verify transaction isolation level
            assertEquals("TRANSACTION_READ_COMMITTED", hikariDataSource.getTransactionIsolation(), "Transaction isolation level should be READ COMMITTED");
        }
    }

    @Test
    @DisplayName("Test routing data source configuration")
    public void testRoutingDataSource() throws Exception {
        // Given
        DataSource primaryDataSource = databaseConfig.primaryDataSource();
        List<DataSource> replicaDataSources = databaseConfig.replicaDataSources();

        // When
        DataSource routingDataSource = databaseConfig.routingDataSource(primaryDataSource, replicaDataSources);

        // Then
        assertNotNull(routingDataSource, "Routing data source should not be null");
        assertTrue(routingDataSource instanceof DatabaseConfig.RoutingDataSource, "Should be a RoutingDataSource");

        // Verify target data sources using reflection
        Field targetDataSourcesField = AbstractRoutingDataSource.class.getDeclaredField("targetDataSources");
        targetDataSourcesField.setAccessible(true);
        Map<Object, Object> targetDataSources = (Map<Object, Object>) targetDataSourcesField.get(routingDataSource);

        assertNotNull(targetDataSources, "Target data sources should not be null");
        assertEquals(3, targetDataSources.size(), "Should have 3 target data sources (1 primary + 2 replicas)");
        assertTrue(targetDataSources.containsKey(DatabaseConfig.DbType.PRIMARY), "Should contain PRIMARY key");
        assertTrue(targetDataSources.containsKey("REPLICA_0"), "Should contain REPLICA_0 key");
        assertTrue(targetDataSources.containsKey("REPLICA_1"), "Should contain REPLICA_1 key");

        // Verify default target data source using reflection
        Field defaultTargetDataSourceField = AbstractRoutingDataSource.class.getDeclaredField("defaultTargetDataSource");
        defaultTargetDataSourceField.setAccessible(true);
        Object defaultTargetDataSource = defaultTargetDataSourceField.get(routingDataSource);

        assertNotNull(defaultTargetDataSource, "Default target data source should not be null");
        assertSame(primaryDataSource, defaultTargetDataSource, "Default target data source should be the primary data source");

        // Verify replica count using reflection
        Field replicaCountField = DatabaseConfig.RoutingDataSource.class.getDeclaredField("replicaCount");
        replicaCountField.setAccessible(true);
        int replicaCount = (int) replicaCountField.get(routingDataSource);

        assertEquals(2, replicaCount, "Replica count should be 2");
    }

    @Test
    @DisplayName("Test routing logic for read-only transactions")
    public void testRoutingLogicForReadOnlyTransactions() throws Exception {
        // Given
        DataSource primaryDataSource = databaseConfig.primaryDataSource();
        List<DataSource> replicaDataSources = databaseConfig.replicaDataSources();
        DatabaseConfig.RoutingDataSource routingDataSource = 
            (DatabaseConfig.RoutingDataSource) databaseConfig.routingDataSource(primaryDataSource, replicaDataSources);

        // Mock TransactionSynchronizationManager for read-only transaction
        try (MockedStatic<TransactionSynchronizationManager> mockedStatic = Mockito.mockStatic(TransactionSynchronizationManager.class)) {
            mockedStatic.when(TransactionSynchronizationManager::isCurrentTransactionReadOnly).thenReturn(true);

            // When - First call
            Object lookupKey1 = routingDataSource.determineCurrentLookupKey();
            
            // Then - First call should return REPLICA_0 (first replica in round-robin)
            assertEquals("REPLICA_0", lookupKey1, "First lookup key should be REPLICA_0");

            // When - Second call
            Object lookupKey2 = routingDataSource.determineCurrentLookupKey();
            
            // Then - Second call should return REPLICA_1 (second replica in round-robin)
            assertEquals("REPLICA_1", lookupKey2, "Second lookup key should be REPLICA_1");

            // When - Third call
            Object lookupKey3 = routingDataSource.determineCurrentLookupKey();
            
            // Then - Third call should return REPLICA_0 again (round-robin wraps around)
            assertEquals("REPLICA_0", lookupKey3, "Third lookup key should be REPLICA_0 again");
        }
    }

    @Test
    @DisplayName("Test routing logic for write transactions")
    public void testRoutingLogicForWriteTransactions() throws Exception {
        // Given
        DataSource primaryDataSource = databaseConfig.primaryDataSource();
        List<DataSource> replicaDataSources = databaseConfig.replicaDataSources();
        DatabaseConfig.RoutingDataSource routingDataSource = 
            (DatabaseConfig.RoutingDataSource) databaseConfig.routingDataSource(primaryDataSource, replicaDataSources);

        // Mock TransactionSynchronizationManager for write transaction (not read-only)
        try (MockedStatic<TransactionSynchronizationManager> mockedStatic = Mockito.mockStatic(TransactionSynchronizationManager.class)) {
            mockedStatic.when(TransactionSynchronizationManager::isCurrentTransactionReadOnly).thenReturn(false);

            // When
            Object lookupKey = routingDataSource.determineCurrentLookupKey();
            
            // Then
            assertEquals(DatabaseConfig.DbType.PRIMARY, lookupKey, "Lookup key should be PRIMARY for write transactions");
        }
    }

    @Test
    @DisplayName("Test routing with no replicas available")
    public void testRoutingWithNoReplicas() throws Exception {
        // Given
        DataSource primaryDataSource = databaseConfig.primaryDataSource();
        List<DataSource> emptyReplicaList = List.of(); // Empty list to simulate no replicas
        DatabaseConfig.RoutingDataSource routingDataSource = 
            (DatabaseConfig.RoutingDataSource) databaseConfig.routingDataSource(primaryDataSource, emptyReplicaList);

        // Verify target data sources using reflection
        Field targetDataSourcesField = AbstractRoutingDataSource.class.getDeclaredField("targetDataSources");
        targetDataSourcesField.setAccessible(true);
        Map<Object, Object> targetDataSources = (Map<Object, Object>) targetDataSourcesField.get(routingDataSource);

        // Then
        assertEquals(2, targetDataSources.size(), "Should have 2 target data sources (PRIMARY and REPLICA both pointing to primary)");
        assertTrue(targetDataSources.containsKey(DatabaseConfig.DbType.PRIMARY), "Should contain PRIMARY key");
        assertTrue(targetDataSources.containsKey(DatabaseConfig.DbType.REPLICA), "Should contain REPLICA key");
        assertSame(targetDataSources.get(DatabaseConfig.DbType.PRIMARY), targetDataSources.get(DatabaseConfig.DbType.REPLICA), 
                "PRIMARY and REPLICA should point to the same data source when no replicas are available");

        // Mock TransactionSynchronizationManager for read-only transaction
        try (MockedStatic<TransactionSynchronizationManager> mockedStatic = Mockito.mockStatic(TransactionSynchronizationManager.class)) {
            mockedStatic.when(TransactionSynchronizationManager::isCurrentTransactionReadOnly).thenReturn(true);

            // When
            Object lookupKey = routingDataSource.determineCurrentLookupKey();
            
            // Then
            assertEquals(DatabaseConfig.DbType.REPLICA, lookupKey, "Lookup key should be REPLICA even when no replicas are available");
        }
    }

    @Test
    @DisplayName("Test routing with single replica")
    public void testRoutingWithSingleReplica() throws Exception {
        // Given
        DataSource primaryDataSource = databaseConfig.primaryDataSource();
        // Create a list with just one replica
        List<DataSource> singleReplicaList = List.of(databaseConfig.replicaDataSources().get(0));
        DatabaseConfig.RoutingDataSource routingDataSource = 
            (DatabaseConfig.RoutingDataSource) databaseConfig.routingDataSource(primaryDataSource, singleReplicaList);

        // Verify target data sources using reflection
        Field targetDataSourcesField = AbstractRoutingDataSource.class.getDeclaredField("targetDataSources");
        targetDataSourcesField.setAccessible(true);
        Map<Object, Object> targetDataSources = (Map<Object, Object>) targetDataSourcesField.get(routingDataSource);

        // Then
        assertEquals(2, targetDataSources.size(), "Should have 2 target data sources (PRIMARY and REPLICA)");
        assertTrue(targetDataSources.containsKey(DatabaseConfig.DbType.PRIMARY), "Should contain PRIMARY key");
        assertTrue(targetDataSources.containsKey(DatabaseConfig.DbType.REPLICA), "Should contain REPLICA key");
        assertNotSame(targetDataSources.get(DatabaseConfig.DbType.PRIMARY), targetDataSources.get(DatabaseConfig.DbType.REPLICA), 
                "PRIMARY and REPLICA should point to different data sources");

        // Verify replica count using reflection
        Field replicaCountField = DatabaseConfig.RoutingDataSource.class.getDeclaredField("replicaCount");
        replicaCountField.setAccessible(true);
        int replicaCount = (int) replicaCountField.get(routingDataSource);

        assertEquals(1, replicaCount, "Replica count should be 1");

        // Mock TransactionSynchronizationManager for read-only transaction
        try (MockedStatic<TransactionSynchronizationManager> mockedStatic = Mockito.mockStatic(TransactionSynchronizationManager.class)) {
            mockedStatic.when(TransactionSynchronizationManager::isCurrentTransactionReadOnly).thenReturn(true);

            // When
            Object lookupKey = routingDataSource.determineCurrentLookupKey();
            
            // Then
            assertEquals(DatabaseConfig.DbType.REPLICA, lookupKey, "Lookup key should be REPLICA for single replica");
        }
    }

    @Test
    @DisplayName("Test lazy connection data source proxy")
    public void testLazyConnectionDataSourceProxy() {
        // Given
        DataSource primaryDataSource = databaseConfig.primaryDataSource();
        List<DataSource> replicaDataSources = databaseConfig.replicaDataSources();
        DataSource routingDataSource = databaseConfig.routingDataSource(primaryDataSource, replicaDataSources);

        // When
        DataSource lazyDataSource = databaseConfig.dataSource(routingDataSource);

        // Then
        assertNotNull(lazyDataSource, "Lazy data source should not be null");
        assertTrue(lazyDataSource instanceof LazyConnectionDataSourceProxy, "Should be a LazyConnectionDataSourceProxy");

        LazyConnectionDataSourceProxy lazyProxy = (LazyConnectionDataSourceProxy) lazyDataSource;
        assertSame(routingDataSource, lazyProxy.getTargetDataSource(), "Target data source should be the routing data source");
    }

    @Test
    @DisplayName("Test transaction manager configuration")
    public void testTransactionManager() {
        // Given
        DataSource primaryDataSource = databaseConfig.primaryDataSource();
        List<DataSource> replicaDataSources = databaseConfig.replicaDataSources();
        DataSource routingDataSource = databaseConfig.routingDataSource(primaryDataSource, replicaDataSources);
        DataSource lazyDataSource = databaseConfig.dataSource(routingDataSource);

        // When
        PlatformTransactionManager transactionManager = databaseConfig.transactionManager(lazyDataSource);

        // Then
        assertNotNull(transactionManager, "Transaction manager should not be null");
        assertTrue(transactionManager instanceof org.springframework.jdbc.datasource.DataSourceTransactionManager, 
                "Should be a DataSourceTransactionManager");

        org.springframework.jdbc.datasource.DataSourceTransactionManager dsTransactionManager = 
                (org.springframework.jdbc.datasource.DataSourceTransactionManager) transactionManager;
        assertSame(lazyDataSource, dsTransactionManager.getDataSource(), "Data source should be the lazy data source");
    }

    @Test
    @DisplayName("Test JPA properties configuration")
    public void testJpaProperties() {
        // When
        Map<String, Object> jpaProperties = databaseConfig.jpaProperties();

        // Then
        assertNotNull(jpaProperties, "JPA properties should not be null");
        assertEquals("org.hibernate.dialect.PostgreSQLDialect", jpaProperties.get("hibernate.dialect"), 
                "Hibernate dialect should be PostgreSQLDialect");
        assertEquals("true", jpaProperties.get("hibernate.format_sql"), "format_sql should be true");
        assertEquals(50, jpaProperties.get("hibernate.jdbc.batch_size"), "batch_size should be 50");
        assertEquals("true", jpaProperties.get("hibernate.order_inserts"), "order_inserts should be true");
        assertEquals("true", jpaProperties.get("hibernate.order_updates"), "order_updates should be true");
        assertEquals("UTC", jpaProperties.get("hibernate.jdbc.time_zone"), "time_zone should be UTC");
        assertEquals("true", jpaProperties.get("hibernate.connection.provider_disables_autocommit"), 
                "provider_disables_autocommit should be true");
        assertEquals("true", jpaProperties.get("hibernate.query.in_clause_parameter_padding"), 
                "in_clause_parameter_padding should be true");
        assertEquals("true", jpaProperties.get("hibernate.query.fail_on_pagination_over_collection_fetch"), 
                "fail_on_pagination_over_collection_fetch should be true");

        // Verify second-level cache is not enabled by default
        assertFalse(jpaProperties.containsKey("hibernate.cache.use_second_level_cache"), 
                "Second-level cache should not be enabled by default");
    }

    @Test
    @DisplayName("Test JPA properties with second-level cache enabled")
    public void testJpaPropertiesWithSecondLevelCache() {
        // Given
        when(environment.getProperty("spring.jpa.properties.hibernate.cache.use_second_level_cache", "false")).thenReturn("true");
        when(environment.getProperty("spring.jpa.properties.hibernate.cache.use_query_cache", "false")).thenReturn("true");
        when(environment.getProperty("spring.jpa.properties.hibernate.cache.region.factory_class", 
                "org.hibernate.cache.jcache.JCacheRegionFactory"))
                .thenReturn("org.hibernate.cache.jcache.JCacheRegionFactory");

        // When
        Map<String, Object> jpaProperties = databaseConfig.jpaProperties();

        // Then
        assertNotNull(jpaProperties, "JPA properties should not be null");
        assertEquals("true", jpaProperties.get("hibernate.cache.use_second_level_cache"), 
                "Second-level cache should be enabled");
        assertEquals("true", jpaProperties.get("hibernate.cache.use_query_cache"), 
                "Query cache should be enabled");
        assertEquals("org.hibernate.cache.jcache.JCacheRegionFactory", jpaProperties.get("hibernate.cache.region.factory_class"), 
                "Cache region factory should be JCacheRegionFactory");
    }

    @Test
    @DisplayName("Test ReadOnlyOperation aspect")
    public void testReadOnlyOperationAspect() throws Throwable {
        // Given
        DatabaseConfig.ReadOnlyOperationAspect aspect = databaseConfig.readOnlyOperationAspect();
        assertNotNull(aspect, "ReadOnlyOperationAspect should not be null");

        // Create a mock ProceedingJoinPoint
        ProceedingJoinPoint joinPoint = mock(ProceedingJoinPoint.class);
        when(joinPoint.proceed()).thenReturn("test result");

        // When
        Object result = aspect.enforceReadOnly(joinPoint);

        // Then
        assertEquals("test result", result, "Result should match the mock result");
        verify(joinPoint, times(1)).proceed();

        // Note: We can't easily test that the transaction is read-only without a full Spring context,
        // but we can verify that the method is annotated with @Transactional(readOnly = true)
        Method enforceReadOnlyMethod = DatabaseConfig.ReadOnlyOperationAspect.class.getDeclaredMethod("enforceReadOnly", ProceedingJoinPoint.class);
        org.springframework.transaction.annotation.Transactional transactionalAnnotation = 
                enforceReadOnlyMethod.getAnnotation(org.springframework.transaction.annotation.Transactional.class);
        
        assertNotNull(transactionalAnnotation, "Method should be annotated with @Transactional");
        assertTrue(transactionalAnnotation.readOnly(), "Transaction should be read-only");
        assertEquals(Propagation.REQUIRED, transactionalAnnotation.propagation(), "Propagation should be REQUIRED");
    }
}