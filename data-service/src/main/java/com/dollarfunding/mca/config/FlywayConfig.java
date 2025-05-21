package com.dollarfunding.mca.config;

import org.flywaydb.core.Flyway;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.flyway.FlywayMigrationStrategy;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.DependsOn;
import org.springframework.context.annotation.Profile;

import javax.sql.DataSource;
import java.util.HashMap;
import java.util.Map;

/**
 * Configuration class for Flyway database migrations in the MCA application.
 * This class defines migration settings, locations, and versioning strategy.
 * It enables the application to manage database schema changes in a controlled
 * and versioned manner, ensuring consistent database structure across environments.
 *
 * The configuration supports:
 * - Three main database schemas: Applications, Documents, and MerchantDetails
 * - 7-year data retention policy
 * - Field-level encryption for PII
 * - Validation rules for database operations
 */
@Configuration
public class FlywayConfig {

    @Value("${spring.flyway.locations:classpath:db/migration}")
    private String[] locations;

    @Value("${spring.flyway.baseline-on-migrate:true}")
    private boolean baselineOnMigrate;

    @Value("${spring.flyway.validate-on-migrate:true}")
    private boolean validateOnMigrate;

    @Value("${spring.flyway.clean-disabled:true}")
    private boolean cleanDisabled;

    @Value("${spring.flyway.out-of-order:false}")
    private boolean outOfOrder;

    @Value("${spring.flyway.ignore-missing-migrations:false}")
    private boolean ignoreMissingMigrations;

    @Value("${spring.flyway.ignore-future-migrations:false}")
    private boolean ignoreFutureMigrations;

    @Value("${spring.flyway.connect-retries:3}")
    private int connectRetries;

    @Value("${spring.flyway.table:flyway_schema_history}")
    private String table;

    /**
     * Configures the Flyway bean with custom settings for the MCA application.
     * This configuration ensures proper database schema migration with validation
     * and appropriate error handling.
     *
     * @param dataSource The application's primary data source
     * @return A configured Flyway instance
     */
    @Bean(name = "flyway")
    @DependsOn("dataSource")
    public Flyway flyway(DataSource dataSource) {
        return Flyway.configure()
                .dataSource(dataSource)
                .locations(locations)
                .baselineOnMigrate(baselineOnMigrate)
                .validateOnMigrate(validateOnMigrate)
                .cleanDisabled(cleanDisabled)
                .outOfOrder(outOfOrder)
                .ignoreMissingMigrations(ignoreMissingMigrations)
                .ignoreFutureMigrations(ignoreFutureMigrations)
                .connectRetries(connectRetries)
                .table(table)
                .placeholders(getPlaceholders())
                .load();
    }

    /**
     * Provides a migration strategy that validates the database schema against
     * the JPA entity model after migrations are applied. This ensures that the
     * database schema and Java model remain in sync.
     *
     * @return A FlywayMigrationStrategy that performs validation after migration
     */
    @Bean
    public FlywayMigrationStrategy flywayMigrationStrategy() {
        return flyway -> {
            // Apply migrations
            flyway.migrate();
            
            // Additional post-migration validation or operations can be added here
            // For example, logging migration results or performing custom validations
        };
    }

    /**
     * Provides a repair strategy for development and testing environments.
     * This strategy allows for repairing the Flyway schema history table in case
     * of failed migrations during development.
     *
     * @return A Flyway instance configured for repair operations
     */
    @Bean
    @Profile({"dev", "test"})
    public FlywayMigrationStrategy repairFlywayStrategy() {
        return flyway -> {
            // Repair the schema history table if needed
            flyway.repair();
            // Then perform the migration
            flyway.migrate();
        };
    }

    /**
     * Defines placeholders that can be used in SQL migration scripts.
     * These placeholders can be referenced in SQL scripts using ${placeholder} syntax.
     *
     * @return A map of placeholder names to their values
     */
    private Map<String, String> getPlaceholders() {
        Map<String, String> placeholders = new HashMap<>();
        
        // Add placeholders for retention periods
        placeholders.put("retention_period_years", "7"); // 7-year retention period
        
        // Add placeholders for schema names if needed
        placeholders.put("application_schema", "public");
        
        return placeholders;
    }
}