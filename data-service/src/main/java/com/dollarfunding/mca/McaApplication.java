package com.dollarfunding.mca;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.transaction.annotation.EnableTransactionManagement;

/**
 * Main Spring Boot application class for the Merchant Cash Advance (MCA) application processing system.
 * This class serves as the entry point for the application and initializes the Spring Boot application context.
 * 
 * The MCA application is designed to automate email-based application processing with the following capabilities:
 * - Process applications in under 5 minutes from receipt to completion
 * - Maintain 99% data extraction accuracy through AI and machine learning
 * - Support field-level encryption for PII (Personally Identifiable Information)
 * - Implement validation rules for application data
 */
@SpringBootApplication
@EnableTransactionManagement
public class McaApplication {

    /**
     * Main method that launches the Spring Boot application.
     * This method bootstraps the entire application and starts the embedded server.
     * 
     * @param args Command line arguments passed to the application
     */
    public static void main(String[] args) {
        SpringApplication.run(McaApplication.class, args);
    }
}