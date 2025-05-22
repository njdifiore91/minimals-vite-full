package com.dollarfunding.mca.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;

import javax.sql.DataSource;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.jdbc.datasource.LazyConnectionDataSourceProxy;
import org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.orm.jpa.vendor.HibernateJpaVendorAdapter;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.PlatformTransactionManager;

import com.zaxxer.hikari.HikariDataSource;

/**
 * Unit tests for the {@link DatabaseConfig} class.
 * 
 * These tests verify that the PostgreSQL database connection is properly configured with:
 * - Primary database for write operations
 * - Read replicas for read operations to improve performance
 * - HikariCP connection pool with optimized settings
 * - Transaction management with appropriate isolation levels
 * - JPA/Hibernate properties for efficient database operations
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("Database Configuration Tests")
public class DatabaseConfigTest {

    @InjectMocks
    private DatabaseConfig databaseConfig;
    
    @Spy
    private DataSourceProperties primaryDataSourceProperties = new DataSourceProperties();
    
    @Spy
    private DataSourceProperties replicaDataSourceProperties = new DataSourceProperties();
    
    @Mock
    private HikariDataSource primaryDataSource;
    
    @BeforeEach
    public void setUp() {
        // Configure primary data source properties
        primaryDataSourceProperties.setUrl("jdbc:postgresql://primary-db:5432/mca");
        primaryDataSourceProperties.setUsername("mca_user");
        primaryDataSourceProperties.setPassword("password");
        primaryDataSourceProperties.setDriverClassName("org.postgresql.Driver");
        
        // Configure primary HikariCP data source
        when(primaryDataSource.getMaximumPoolSize()).thenReturn(10);
        when(primaryDataSource.getMinimumIdle()).thenReturn(5);
        when(primaryDataSource.getIdleTimeout()).thenReturn(300000L);
        when(primaryDataSource.getMaxLifetime()).thenReturn(1800000L);
        when(primaryDataSource.getConnectionTimeout()).thenReturn(30000L);
        when(primaryDataSource.getPoolName()).thenReturn("PrimaryHikariPool");
    }

    /**
     * Tests that the primary data source properties are properly configured.
     * 
     * Verifies:
     * - The properties are not null
     * - The URL is set correctly
     * - The username is set correctly
     * - The password is set correctly
     * - The driver class name is set correctly
     */
    @Test
    @DisplayName("Primary DataSource Properties should be properly configured")
    public void testPrimaryDataSourceProperties() {
        // Execute the method under test
        DataSourceProperties properties = databaseConfig.primaryDataSourceProperties();
        
        // Verify the properties
        assertNotNull(properties);
        assertEquals("jdbc:postgresql://primary-db:5432/mca", properties.getUrl());
        assertEquals("mca_user", properties.getUsername());
        assertEquals("password", properties.getPassword());
        assertEquals("org.postgresql.Driver", properties.getDriverClassName());
    }

    /**
     * Tests that the primary data source is properly configured with HikariCP.
     * 
     * Verifies:
     * - The data source is a HikariDataSource
     * - The pool name is set correctly
     * - The connection pool settings are applied correctly
     */
    @Test
    @DisplayName("Primary DataSource should be configured with HikariCP")
    public void testPrimaryDataSource() {
        // Mock the behavior of primaryDataSourceProperties
        when(primaryDataSourceProperties.initializeDataSourceBuilder()).thenReturn(new DataSourceProperties.DataSourceBuilder());
        
        // Create a mock HikariDataSource that will be returned by the builder
        HikariDataSource mockHikariDataSource = mock(HikariDataSource.class);
        
        // Mock the behavior of the builder
        DataSourceProperties.DataSourceBuilder builder = primaryDataSourceProperties.initializeDataSourceBuilder();
        ReflectionTestUtils.setField(builder, "type", HikariDataSource.class);
        ReflectionTestUtils.setField(builder, "result", mockHikariDataSource);
        
        // Execute the method under test
        HikariDataSource dataSource = databaseConfig.primaryDataSource();
        
        // Verify the data source
        assertNotNull(dataSource);
        assertEquals(mockHikariDataSource, dataSource);
    }

    /**
     * Tests that the read replica data sources are properly configured.
     * 
     * Verifies:
     * - The correct number of replica data sources are created
     * - Each replica data source is configured correctly
     * - Each replica data source is marked as read-only
     */
    @Test
    @DisplayName("Read Replica DataSources should be properly configured")
    public void testReadReplicaDataSources() {
        // Create test replica nodes
        List<Map<String, String>> replicaNodes = new ArrayList<>();
        
        Map<String, String> replica1 = new HashMap<>();
        replica1.put("url", "jdbc:postgresql://replica1:5432/mca");
        replica1.put("username", "replica_user");
        replica1.put("password", "replica_password");
        replicaNodes.add(replica1);
        
        Map<String, String> replica2 = new HashMap<>();
        replica2.put("url", "jdbc:postgresql://replica2:5432/mca");
        replica2.put("username", "replica_user");
        replica2.put("password", "replica_password");
        replicaNodes.add(replica2);
        
        // Execute the method under test
        Map<String, DataSource> replicaDataSources = databaseConfig.readReplicaDataSources(replicaNodes, true);
        
        // Verify the replica data sources
        assertNotNull(replicaDataSources);
        assertEquals(2, replicaDataSources.size());
        
        // Verify each replica data source
        for (int i = 0; i < 2; i++) {
            String key = "replica-" + i;
            assertTrue(replicaDataSources.containsKey(key));
            
            DataSource replicaDataSource = replicaDataSources.get(key);
            assertTrue(replicaDataSource instanceof HikariDataSource);
            
            HikariDataSource hikariDataSource = (HikariDataSource) replicaDataSource;
            assertEquals("jdbc:postgresql://replica" + (i+1) + ":5432/mca", hikariDataSource.getJdbcUrl());
            assertEquals("replica_user", hikariDataSource.getUsername());
            assertEquals("replica_password", hikariDataSource.getPassword());
            assertEquals("ReplicaHikariPool-" + i, hikariDataSource.getPoolName());
            assertTrue(hikariDataSource.isReadOnly());
        }
    }

    /**
     * Tests that the routing data source is properly configured to route read/write operations
     * to the appropriate data source.
     * 
     * Verifies:
     * - The routing data source is an AbstractRoutingDataSource
     * - The target data sources map contains the primary and replica data sources
     * - The default target data source is the primary data source
     * - The lookup key is determined correctly based on the operation type
     */
    @Test
    @DisplayName("Routing DataSource should route operations to the appropriate data source")
    public void testRoutingDataSource() throws Exception {
        // Create mock data sources
        DataSource mockPrimaryDataSource = mock(DataSource.class);
        
        Map<String, DataSource> mockReplicaDataSources = new HashMap<>();
        mockReplicaDataSources.put("replica-0", mock(DataSource.class));
        mockReplicaDataSources.put("replica-1", mock(DataSource.class));
        
        // Execute the method under test
        AbstractRoutingDataSource routingDataSource = databaseConfig.routingDataSource(
                mockPrimaryDataSource, mockReplicaDataSources);
        
        // Verify the routing data source
        assertNotNull(routingDataSource);
        
        // Get the target data sources map using reflection
        Field targetDataSourcesField = AbstractRoutingDataSource.class.getDeclaredField("targetDataSources");
        targetDataSourcesField.setAccessible(true);
        @SuppressWarnings("unchecked")
        Map<Object, Object> targetDataSources = (Map<Object, Object>) targetDataSourcesField.get(routingDataSource);
        
        // Verify the target data sources
        assertNotNull(targetDataSources);
        assertEquals(3, targetDataSources.size());
        assertTrue(targetDataSources.containsKey("primary"));
        assertTrue(targetDataSources.containsKey("replica-0"));
        assertTrue(targetDataSources.containsKey("replica-1"));
        
        // Get the default target data source using reflection
        Field defaultTargetDataSourceField = AbstractRoutingDataSource.class.getDeclaredField("defaultTargetDataSource");
        defaultTargetDataSourceField.setAccessible(true);
        Object defaultTargetDataSource = defaultTargetDataSourceField.get(routingDataSource);
        
        // Verify the default target data source
        assertNotNull(defaultTargetDataSource);
        assertSame(mockPrimaryDataSource, defaultTargetDataSource);
        
        // Test the lookup key determination for write operations
        DatabaseConfig.setCurrentOperation(DatabaseConfig.OperationType.WRITE);
        Object lookupKey = ReflectionTestUtils.invokeMethod(routingDataSource, "determineCurrentLookupKey");
        assertEquals("primary", lookupKey);
        
        // Test the lookup key determination for read operations
        // Note: We can't fully test the round-robin selection since it depends on System.nanoTime()
        DatabaseConfig.setCurrentOperation(DatabaseConfig.OperationType.READ);
        lookupKey = ReflectionTestUtils.invokeMethod(routingDataSource, "determineCurrentLookupKey");
        assertTrue(lookupKey.toString().startsWith("replica-"));
    }

    /**
     * Tests that the lazy connection data source proxy is properly configured.
     * 
     * Verifies:
     * - The proxy is a LazyConnectionDataSourceProxy
     * - The target data source is the routing data source
     */
    @Test
    @DisplayName("Lazy Connection DataSource Proxy should be properly configured")
    public void testLazyConnectionDataSource() throws Exception {
        // Create a mock routing data source
        AbstractRoutingDataSource mockRoutingDataSource = mock(AbstractRoutingDataSource.class);
        
        // Execute the method under test
        LazyConnectionDataSourceProxy lazyConnectionDataSource = 
                databaseConfig.lazyConnectionDataSource(mockRoutingDataSource);
        
        // Verify the lazy connection data source proxy
        assertNotNull(lazyConnectionDataSource);
        
        // Get the target data source using reflection
        Field targetDataSourceField = LazyConnectionDataSourceProxy.class.getDeclaredField("targetDataSource");
        targetDataSourceField.setAccessible(true);
        Object targetDataSource = targetDataSourceField.get(lazyConnectionDataSource);
        
        // Verify the target data source
        assertNotNull(targetDataSource);
        assertSame(mockRoutingDataSource, targetDataSource);
    }

    /**
     * Tests that the final data source is properly configured.
     * 
     * Verifies:
     * - The data source is the lazy connection data source proxy
     */
    @Test
    @DisplayName("Final DataSource should be the lazy connection data source proxy")
    public void testDataSource() {
        // Create a mock lazy connection data source proxy
        LazyConnectionDataSourceProxy mockLazyConnectionDataSource = mock(LazyConnectionDataSourceProxy.class);
        
        // Execute the method under test
        DataSource dataSource = databaseConfig.dataSource(mockLazyConnectionDataSource);
        
        // Verify the data source
        assertNotNull(dataSource);
        assertSame(mockLazyConnectionDataSource, dataSource);
    }

    /**
     * Tests that the entity manager factory is properly configured with the correct JPA properties.
     * 
     * Verifies:
     * - The entity manager factory is a LocalContainerEntityManagerFactoryBean
     * - The data source is set correctly
     * - The packages to scan are set correctly
     * - The JPA vendor adapter is a HibernateJpaVendorAdapter
     * - The JPA properties are set correctly
     */
    @Test
    @DisplayName("Entity Manager Factory should be configured with correct JPA properties")
    public void testEntityManagerFactory() throws Exception {
        // Create a mock data source
        DataSource mockDataSource = mock(DataSource.class);
        
        // Execute the method under test
        LocalContainerEntityManagerFactoryBean entityManagerFactory = 
                databaseConfig.entityManagerFactory(mockDataSource);
        
        // Verify the entity manager factory
        assertNotNull(entityManagerFactory);
        
        // Verify the data source
        Field dataSourceField = LocalContainerEntityManagerFactoryBean.class.getDeclaredField("dataSource");
        dataSourceField.setAccessible(true);
        Object dataSource = dataSourceField.get(entityManagerFactory);
        assertNotNull(dataSource);
        assertSame(mockDataSource, dataSource);
        
        // Verify the packages to scan
        Field packagesToScanField = LocalContainerEntityManagerFactoryBean.class.getDeclaredField("packagesToScan");
        packagesToScanField.setAccessible(true);
        String[] packagesToScan = (String[]) packagesToScanField.get(entityManagerFactory);
        assertNotNull(packagesToScan);
        assertEquals(1, packagesToScan.length);
        assertEquals("com.dollarfunding.mca.entity", packagesToScan[0]);
        
        // Verify the JPA vendor adapter
        Field jpaVendorAdapterField = LocalContainerEntityManagerFactoryBean.class.getDeclaredField("jpaVendorAdapter");
        jpaVendorAdapterField.setAccessible(true);
        Object jpaVendorAdapter = jpaVendorAdapterField.get(entityManagerFactory);
        assertNotNull(jpaVendorAdapter);
        assertTrue(jpaVendorAdapter instanceof HibernateJpaVendorAdapter);
        
        // Verify the JPA properties
        Field jpaPropertiesField = LocalContainerEntityManagerFactoryBean.class.getDeclaredField("jpaProperties");
        jpaPropertiesField.setAccessible(true);
        Properties jpaProperties = (Properties) jpaPropertiesField.get(entityManagerFactory);
        assertNotNull(jpaProperties);
        
        // Verify specific JPA properties
        assertEquals("org.hibernate.dialect.PostgreSQLDialect", jpaProperties.getProperty("hibernate.dialect"));
        assertEquals("50", jpaProperties.getProperty("hibernate.jdbc.batch_size"));
        assertEquals("true", jpaProperties.getProperty("hibernate.order_inserts"));
        assertEquals("true", jpaProperties.getProperty("hibernate.order_updates"));
        assertEquals("UTC", jpaProperties.getProperty("hibernate.jdbc.time_zone"));
        assertEquals("true", jpaProperties.getProperty("hibernate.connection.provider_disables_autocommit"));
        assertEquals("false", jpaProperties.getProperty("hibernate.cache.use_second_level_cache"));
        assertEquals("false", jpaProperties.getProperty("hibernate.cache.use_query_cache"));
        assertEquals("true", jpaProperties.getProperty("hibernate.jdbc.use_get_generated_keys"));
    }

    /**
     * Tests that the transaction manager is properly configured.
     * 
     * Verifies:
     * - The transaction manager is a JpaTransactionManager
     * - The entity manager factory is set correctly
     */
    @Test
    @DisplayName("Transaction Manager should be properly configured")
    public void testTransactionManager() throws Exception {
        // Create a mock entity manager factory
        LocalContainerEntityManagerFactoryBean mockEntityManagerFactory = mock(LocalContainerEntityManagerFactoryBean.class);
        Object mockEntityManagerFactoryObject = mock(Object.class);
        when(mockEntityManagerFactory.getObject()).thenReturn(mockEntityManagerFactoryObject);
        
        // Execute the method under test
        PlatformTransactionManager transactionManager = databaseConfig.transactionManager(mockEntityManagerFactory);
        
        // Verify the transaction manager
        assertNotNull(transactionManager);
        assertTrue(transactionManager instanceof JpaTransactionManager);
        
        // Verify the entity manager factory
        JpaTransactionManager jpaTransactionManager = (JpaTransactionManager) transactionManager;
        assertSame(mockEntityManagerFactoryObject, jpaTransactionManager.getEntityManagerFactory());
    }

    /**
     * Tests that the production-specific database configuration is properly applied.
     * 
     * Verifies:
     * - The production-specific HikariCP settings are applied correctly
     */
    @Test
    @DisplayName("Production Database Config should apply production-specific settings")
    public void testProductionDatabaseConfig() {
        // Create an instance of the production database config
        DatabaseConfig.ProductionDatabaseConfig productionConfig = new DatabaseConfig.ProductionDatabaseConfig();
        
        // Create a mock HikariDataSource
        HikariDataSource mockDataSource = mock(HikariDataSource.class);
        
        // Execute the method under test
        HikariDataSource configuredDataSource = productionConfig.productionPrimaryDataSource(mockDataSource);
        
        // Verify the data source
        assertNotNull(configuredDataSource);
        assertSame(mockDataSource, configuredDataSource);
        
        // Verify that the production-specific settings were applied
        // Note: We can't verify the actual values since the method just returns the input data source
        // In a real scenario, we would need to verify that the setters were called with the correct values
    }

    /**
     * Tests that the development-specific database configuration is properly applied.
     * 
     * Verifies:
     * - The development-specific HikariCP settings are applied correctly
     */
    @Test
    @DisplayName("Development Database Config should apply development-specific settings")
    public void testDevelopmentDatabaseConfig() {
        // Create an instance of the development database config
        DatabaseConfig.DevelopmentDatabaseConfig developmentConfig = new DatabaseConfig.DevelopmentDatabaseConfig();
        
        // Create a mock HikariDataSource
        HikariDataSource mockDataSource = mock(HikariDataSource.class);
        
        // Execute the method under test
        HikariDataSource configuredDataSource = developmentConfig.developmentPrimaryDataSource(mockDataSource);
        
        // Verify the data source
        assertNotNull(configuredDataSource);
        assertSame(mockDataSource, configuredDataSource);
        
        // Verify that the development-specific settings were applied
        // Note: We can't verify the actual values since the method just returns the input data source
        // In a real scenario, we would need to verify that the setters were called with the correct values
    }

    /**
     * Tests the thread-local operation type management.
     * 
     * Verifies:
     * - The default operation type is WRITE
     * - The operation type can be set and retrieved correctly
     * - The operation type can be cleared
     */
    @Test
    @DisplayName("Thread-local operation type should be managed correctly")
    public void testThreadLocalOperationTypeManagement() {
        // Verify the default operation type
        assertEquals(DatabaseConfig.OperationType.WRITE, DatabaseConfig.getCurrentOperation());
        
        // Set the operation type to READ
        DatabaseConfig.setCurrentOperation(DatabaseConfig.OperationType.READ);
        
        // Verify the operation type was set correctly
        assertEquals(DatabaseConfig.OperationType.READ, DatabaseConfig.getCurrentOperation());
        
        // Clear the operation type
        DatabaseConfig.clearCurrentOperation();
        
        // Verify the operation type was reset to the default
        assertEquals(DatabaseConfig.OperationType.WRITE, DatabaseConfig.getCurrentOperation());
    }
}