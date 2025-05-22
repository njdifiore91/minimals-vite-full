package com.dollarfunding.mca;

import com.amazonaws.services.s3.AmazonS3;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.jdbc.datasource.embedded.EmbeddedDatabaseBuilder;
import org.springframework.jdbc.datasource.embedded.EmbeddedDatabaseType;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.transaction.annotation.EnableTransactionManagement;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.orm.jpa.vendor.HibernateJpaVendorAdapter;
import org.springframework.transaction.PlatformTransactionManager;
import org.flywaydb.core.Flyway;

import java.util.Properties;

import javax.sql.DataSource;

/**
 * Test configuration class for the Data Service.
 * <p>
 * This class provides test-specific bean definitions, property sources, and configuration overrides
 * for the Spring application context during testing. It enables in-memory database configuration,
 * test-specific cache settings, mock messaging infrastructure, and security bypasses for isolated testing.
 * </p>
 */
@TestConfiguration
@EnableAutoConfiguration
@EnableJpaRepositories(basePackages = "com.dollarfunding.mca.repository")
@EntityScan(basePackages = "com.dollarfunding.mca.entity")
@EnableTransactionManagement
@EnableWebSecurity
public class TestConfig {

    /**
     * Configures an in-memory H2 database for testing.
     * <p>
     * This database is isolated from any external database and is recreated for each test run.
     * It allows for fast, isolated testing of repository and service layers without affecting
     * any persistent data.
     * </p>
     *
     * @return A configured H2 in-memory DataSource
     */
    @Bean
    @Primary
    public DataSource dataSource() {
        return new EmbeddedDatabaseBuilder()
                .setType(EmbeddedDatabaseType.H2)
                .setName("testdb;DB_CLOSE_DELAY=-1;MODE=PostgreSQL")
                .build();
    }
    
    /**
     * Configures Flyway for database migrations during testing.
     * <p>
     * This bean initializes Flyway with the test datasource and configures it to run
     * migrations from the test-specific migration scripts location. It ensures that
     * the database schema is properly set up for testing.
     * </p>
     *
     * @param dataSource The test datasource
     * @return A configured Flyway instance
     */
    @Bean
    public Flyway flyway(DataSource dataSource) {
        Flyway flyway = Flyway.configure()
                .dataSource(dataSource)
                .locations("classpath:db/migrations", "classpath:db/test-migrations")
                .baselineOnMigrate(true)
                .load();
        flyway.migrate();
        return flyway;
    }
    
    /**
     * Configures the JPA EntityManagerFactory for testing.
     * <p>
     * This bean sets up the EntityManagerFactory with Hibernate as the JPA provider,
     * configured to work with the H2 in-memory database. It includes settings for
     * schema generation and SQL formatting to aid in debugging.
     * </p>
     *
     * @param dataSource The test datasource
     * @return A configured LocalContainerEntityManagerFactoryBean
     */
    @Bean
    public LocalContainerEntityManagerFactoryBean entityManagerFactory(DataSource dataSource) {
        LocalContainerEntityManagerFactoryBean em = new LocalContainerEntityManagerFactoryBean();
        em.setDataSource(dataSource);
        em.setPackagesToScan("com.dollarfunding.mca.entity");
        
        HibernateJpaVendorAdapter vendorAdapter = new HibernateJpaVendorAdapter();
        vendorAdapter.setGenerateDdl(true);
        vendorAdapter.setShowSql(true);
        em.setJpaVendorAdapter(vendorAdapter);
        
        Properties properties = new Properties();
        properties.setProperty("hibernate.dialect", "org.hibernate.dialect.H2Dialect");
        properties.setProperty("hibernate.format_sql", "true");
        properties.setProperty("hibernate.hbm2ddl.auto", "create-drop");
        em.setJpaProperties(properties);
        
        return em;
    }
    
    /**
     * Configures the transaction manager for testing.
     * <p>
     * This bean sets up a JPA transaction manager that works with the test EntityManagerFactory.
     * It ensures that test transactions are properly managed and can be rolled back after test execution.
     * </p>
     *
     * @param entityManagerFactory The test EntityManagerFactory
     * @return A configured PlatformTransactionManager
     */
    @Bean
    public PlatformTransactionManager transactionManager(LocalContainerEntityManagerFactoryBean entityManagerFactory) {
        JpaTransactionManager transactionManager = new JpaTransactionManager();
        transactionManager.setEntityManagerFactory(entityManagerFactory.getObject());
        return transactionManager;
    }

    /**
     * Mock S3 client for testing.
     * <p>
     * This mock bean replaces the actual AWS S3 client during tests, allowing for
     * isolated testing without requiring actual AWS resources or credentials.
     * Test methods can use Mockito to define the behavior of this mock.
     * </p>
     */
    @MockBean
    private AmazonS3 amazonS3;

    /**
     * Mock RabbitMQ connection factory for testing.
     * <p>
     * This mock bean replaces the actual RabbitMQ connection factory during tests,
     * allowing for isolated testing without requiring an actual RabbitMQ server.
     * </p>
     */
    @MockBean
    private ConnectionFactory rabbitConnectionFactory;

    /**
     * Mock RabbitTemplate for testing.
     * <p>
     * This mock bean replaces the actual RabbitTemplate during tests, allowing for
     * isolated testing of components that use RabbitMQ for messaging.
     * Test methods can use Mockito to define the behavior of this mock.
     * </p>
     */
    @MockBean
    private RabbitTemplate rabbitTemplate;

    /**
     * Mock Redis connection factory for testing.
     * <p>
     * This mock bean replaces the actual Redis connection factory during tests,
     * allowing for isolated testing without requiring an actual Redis server.
     * </p>
     */
    @MockBean
    private RedisConnectionFactory redisConnectionFactory;

    /**
     * Mock RedisTemplate for testing.
     * <p>
     * This mock bean replaces the actual RedisTemplate during tests, allowing for
     * isolated testing of components that use Redis for caching.
     * Test methods can use Mockito to define the behavior of this mock.
     * </p>
     */
    @MockBean
    private RedisTemplate<String, Object> redisTemplate;

    /**
     * Configures test-specific properties for the application context.
     * <p>
     * This method can be extended to add additional test-specific configuration
     * properties as needed for different test scenarios.
     * </p>
     *
     * @return A bean with test-specific properties
     */
    @Bean
    public TestProperties testProperties() {
        TestProperties properties = new TestProperties();
        properties.setCacheTtl(15); // 15 minutes TTL for test cache
        properties.setSessionTtl(24 * 60); // 24 hours TTL for test sessions
        return properties;
    }
    
    /**
     * Configures security for testing purposes.
     * <p>
     * This bean configures a security filter chain that permits all requests during testing,
     * bypassing authentication and authorization checks that would be present in production.
     * </p>
     *
     * @param http The HttpSecurity to configure
     * @return A configured SecurityFilterChain
     * @throws Exception if configuration fails
     */
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf().disable()
            .authorizeRequests()
                .anyRequest().permitAll();
        return http.build();
    }
    
    /**
     * Provides test users with different roles for testing role-based access control.
     * <p>
     * This bean creates an in-memory user details service with predefined test users
     * having different roles (Operations Staff and System Admin) for testing
     * role-based access control functionality.
     * </p>
     *
     * @return A UserDetailsService with test users
     */
    @Bean
    public UserDetailsService userDetailsService() {
        UserDetails operationsUser = User.builder()
                .username("operations")
                .password("{noop}password")
                .roles("OPERATIONS_STAFF")
                .build();
                
        UserDetails adminUser = User.builder()
                .username("admin")
                .password("{noop}password")
                .roles("SYSTEM_ADMIN")
                .build();
                
        return new InMemoryUserDetailsManager(operationsUser, adminUser);
    }

    /**
     * Inner class to hold test-specific properties.
     */
    public static class TestProperties {
        private int cacheTtl;
        private int sessionTtl;

        public int getCacheTtl() {
            return cacheTtl;
        }

        public void setCacheTtl(int cacheTtl) {
            this.cacheTtl = cacheTtl;
        }

        public int getSessionTtl() {
            return sessionTtl;
        }

        public void setSessionTtl(int sessionTtl) {
            this.sessionTtl = sessionTtl;
        }
    }
}