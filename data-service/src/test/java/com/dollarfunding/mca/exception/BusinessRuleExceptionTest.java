package com.dollarfunding.mca.exception;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the {@link BusinessRuleException} class.
 * <p>
 * These tests verify that the BusinessRuleException properly handles business rule violations
 * with appropriate HTTP status codes, error messages, and rule violation details.
 * </p>
 */
public class BusinessRuleExceptionTest {

    @Test
    @DisplayName("Should create BusinessRuleException with message only")
    public void testCreateWithMessageOnly() {
        // Arrange & Act
        String message = "Business rule violation occurred";
        BusinessRuleException exception = new BusinessRuleException(message);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY.value(), exception.getStatusCode());
        assertFalse(exception.hasRuleViolations());
        assertEquals(0, exception.getRuleViolationCount());
        assertTrue(exception.getRuleViolations().isEmpty());
    }
    
    @Test
    @DisplayName("Should create BusinessRuleException with message and cause")
    public void testCreateWithMessageAndCause() {
        // Arrange & Act
        String message = "Business rule violation occurred";
        IllegalArgumentException cause = new IllegalArgumentException("Invalid argument");
        BusinessRuleException exception = new BusinessRuleException(message, cause);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertEquals(cause, exception.getCause());
        assertFalse(exception.hasRuleViolations());
        assertEquals(0, exception.getRuleViolationCount());
        assertTrue(exception.getRuleViolations().isEmpty());
    }
    
    @Test
    @DisplayName("Should create BusinessRuleException with message, rule ID, and violation message")
    public void testCreateWithMessageRuleIdAndViolationMessage() {
        // Arrange & Act
        String message = "Business rule violation occurred";
        String ruleId = "REVENUE_MIN";
        String violationMsg = "Revenue must be at least $100,000";
        BusinessRuleException exception = new BusinessRuleException(message, ruleId, violationMsg);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertTrue(exception.hasRuleViolations());
        assertEquals(1, exception.getRuleViolationCount());
        
        List<BusinessRuleException.BusinessRuleViolation> violations = exception.getRuleViolations();
        assertEquals(1, violations.size());
        assertEquals(ruleId, violations.get(0).getRuleId());
        assertEquals(violationMsg, violations.get(0).getMessage());
        assertNull(violations.get(0).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should create BusinessRuleException with message, rule ID, violation message, and rejected value")
    public void testCreateWithMessageRuleIdViolationMessageAndRejectedValue() {
        // Arrange & Act
        String message = "Business rule violation occurred";
        String ruleId = "REVENUE_MIN";
        String violationMsg = "Revenue must be at least $100,000";
        Integer rejectedValue = 50000;
        BusinessRuleException exception = new BusinessRuleException(message, ruleId, violationMsg, rejectedValue);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertTrue(exception.hasRuleViolations());
        assertEquals(1, exception.getRuleViolationCount());
        
        List<BusinessRuleException.BusinessRuleViolation> violations = exception.getRuleViolations();
        assertEquals(1, violations.size());
        assertEquals(ruleId, violations.get(0).getRuleId());
        assertEquals(violationMsg, violations.get(0).getMessage());
        assertEquals(rejectedValue, violations.get(0).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should create BusinessRuleException with message and rule violations list")
    public void testCreateWithMessageAndRuleViolationsList() {
        // Arrange
        String message = "Multiple business rule violations occurred";
        List<BusinessRuleException.BusinessRuleViolation> ruleViolations = new ArrayList<>();
        ruleViolations.add(new BusinessRuleException.BusinessRuleViolation("REVENUE_MIN", "Revenue must be at least $100,000"));
        ruleViolations.add(new BusinessRuleException.BusinessRuleViolation("TIME_IN_BUSINESS", "Business must be operating for at least 2 years"));
        
        // Act
        BusinessRuleException exception = new BusinessRuleException(message, ruleViolations);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertTrue(exception.hasRuleViolations());
        assertEquals(2, exception.getRuleViolationCount());
        
        List<BusinessRuleException.BusinessRuleViolation> violations = exception.getRuleViolations();
        assertEquals(2, violations.size());
        assertEquals("REVENUE_MIN", violations.get(0).getRuleId());
        assertEquals("Revenue must be at least $100,000", violations.get(0).getMessage());
        assertEquals("TIME_IN_BUSINESS", violations.get(1).getRuleId());
        assertEquals("Business must be operating for at least 2 years", violations.get(1).getMessage());
    }
    
    @Test
    @DisplayName("Should create BusinessRuleException with error code, message, and rule violations list")
    public void testCreateWithErrorCodeMessageAndRuleViolationsList() {
        // Arrange
        String errorCode = "BR-001";
        String message = "Multiple business rule violations occurred";
        List<BusinessRuleException.BusinessRuleViolation> ruleViolations = new ArrayList<>();
        ruleViolations.add(new BusinessRuleException.BusinessRuleViolation("REVENUE_MIN", "Revenue must be at least $100,000"));
        ruleViolations.add(new BusinessRuleException.BusinessRuleViolation("TIME_IN_BUSINESS", "Business must be operating for at least 2 years"));
        
        // Act
        BusinessRuleException exception = new BusinessRuleException(errorCode, message, ruleViolations);
        
        // Assert
        assertEquals(message, exception.getMessage());
        assertEquals(errorCode, exception.getErrorCode());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertTrue(exception.hasRuleViolations());
        assertEquals(2, exception.getRuleViolationCount());
        
        List<BusinessRuleException.BusinessRuleViolation> violations = exception.getRuleViolations();
        assertEquals(2, violations.size());
        assertEquals("REVENUE_MIN", violations.get(0).getRuleId());
        assertEquals("Revenue must be at least $100,000", violations.get(0).getMessage());
        assertEquals("TIME_IN_BUSINESS", violations.get(1).getRuleId());
        assertEquals("Business must be operating for at least 2 years", violations.get(1).getMessage());
    }
    
    @Test
    @DisplayName("Should add rule violation to existing exception")
    public void testAddRuleViolation() {
        // Arrange
        BusinessRuleException exception = new BusinessRuleException("Business rule violation occurred");
        
        // Act
        exception.addRuleViolation("REVENUE_MIN", "Revenue must be at least $100,000");
        
        // Assert
        assertTrue(exception.hasRuleViolations());
        assertEquals(1, exception.getRuleViolationCount());
        
        List<BusinessRuleException.BusinessRuleViolation> violations = exception.getRuleViolations();
        assertEquals(1, violations.size());
        assertEquals("REVENUE_MIN", violations.get(0).getRuleId());
        assertEquals("Revenue must be at least $100,000", violations.get(0).getMessage());
        
        // Add another rule violation
        exception.addRuleViolation("TIME_IN_BUSINESS", "Business must be operating for at least 2 years");
        
        // Assert again
        assertTrue(exception.hasRuleViolations());
        assertEquals(2, exception.getRuleViolationCount());
        
        violations = exception.getRuleViolations();
        assertEquals(2, violations.size());
        assertEquals("REVENUE_MIN", violations.get(0).getRuleId());
        assertEquals("Revenue must be at least $100,000", violations.get(0).getMessage());
        assertEquals("TIME_IN_BUSINESS", violations.get(1).getRuleId());
        assertEquals("Business must be operating for at least 2 years", violations.get(1).getMessage());
    }
    
    @Test
    @DisplayName("Should add rule violation with rejected value to existing exception")
    public void testAddRuleViolationWithRejectedValue() {
        // Arrange
        BusinessRuleException exception = new BusinessRuleException("Business rule violation occurred");
        
        // Act
        exception.addRuleViolation("REVENUE_MIN", "Revenue must be at least $100,000", 50000);
        
        // Assert
        assertTrue(exception.hasRuleViolations());
        assertEquals(1, exception.getRuleViolationCount());
        
        List<BusinessRuleException.BusinessRuleViolation> violations = exception.getRuleViolations();
        assertEquals(1, violations.size());
        assertEquals("REVENUE_MIN", violations.get(0).getRuleId());
        assertEquals("Revenue must be at least $100,000", violations.get(0).getMessage());
        assertEquals(50000, violations.get(0).getRejectedValue());
        
        // Add another rule violation with rejected value
        exception.addRuleViolation("TIME_IN_BUSINESS", "Business must be operating for at least 2 years", 1);
        
        // Assert again
        assertTrue(exception.hasRuleViolations());
        assertEquals(2, exception.getRuleViolationCount());
        
        violations = exception.getRuleViolations();
        assertEquals(2, violations.size());
        assertEquals("REVENUE_MIN", violations.get(0).getRuleId());
        assertEquals("Revenue must be at least $100,000", violations.get(0).getMessage());
        assertEquals(50000, violations.get(0).getRejectedValue());
        assertEquals("TIME_IN_BUSINESS", violations.get(1).getRuleId());
        assertEquals("Business must be operating for at least 2 years", violations.get(1).getMessage());
        assertEquals(1, violations.get(1).getRejectedValue());
    }
    
    @Test
    @DisplayName("Should add multiple rule violations to existing exception")
    public void testAddRuleViolations() {
        // Arrange
        BusinessRuleException exception = new BusinessRuleException("Business rule violation occurred");
        List<BusinessRuleException.BusinessRuleViolation> ruleViolations = new ArrayList<>();
        ruleViolations.add(new BusinessRuleException.BusinessRuleViolation("REVENUE_MIN", "Revenue must be at least $100,000"));
        ruleViolations.add(new BusinessRuleException.BusinessRuleViolation("TIME_IN_BUSINESS", "Business must be operating for at least 2 years"));
        
        // Act
        exception.addRuleViolations(ruleViolations);
        
        // Assert
        assertTrue(exception.hasRuleViolations());
        assertEquals(2, exception.getRuleViolationCount());
        
        List<BusinessRuleException.BusinessRuleViolation> violations = exception.getRuleViolations();
        assertEquals(2, violations.size());
        assertEquals("REVENUE_MIN", violations.get(0).getRuleId());
        assertEquals("Revenue must be at least $100,000", violations.get(0).getMessage());
        assertEquals("TIME_IN_BUSINESS", violations.get(1).getRuleId());
        assertEquals("Business must be operating for at least 2 years", violations.get(1).getMessage());
        
        // Add more rule violations
        List<BusinessRuleException.BusinessRuleViolation> moreViolations = new ArrayList<>();
        moreViolations.add(new BusinessRuleException.BusinessRuleViolation("CREDIT_SCORE", "Credit score must be at least 650"));
        moreViolations.add(new BusinessRuleException.BusinessRuleViolation("REQUIRED_DOCS", "All required documents must be submitted"));
        exception.addRuleViolations(moreViolations);
        
        // Assert again
        assertTrue(exception.hasRuleViolations());
        assertEquals(4, exception.getRuleViolationCount());
        
        violations = exception.getRuleViolations();
        assertEquals(4, violations.size());
        assertEquals("REVENUE_MIN", violations.get(0).getRuleId());
        assertEquals("Revenue must be at least $100,000", violations.get(0).getMessage());
        assertEquals("TIME_IN_BUSINESS", violations.get(1).getRuleId());
        assertEquals("Business must be operating for at least 2 years", violations.get(1).getMessage());
        assertEquals("CREDIT_SCORE", violations.get(2).getRuleId());
        assertEquals("Credit score must be at least 650", violations.get(2).getMessage());
        assertEquals("REQUIRED_DOCS", violations.get(3).getRuleId());
        assertEquals("All required documents must be submitted", violations.get(3).getMessage());
    }
    
    @Test
    @DisplayName("Should verify rule violations are unmodifiable")
    public void testRuleViolationsAreUnmodifiable() {
        // Arrange
        BusinessRuleException exception = new BusinessRuleException("Business rule violation occurred", "REVENUE_MIN", "Revenue must be at least $100,000");
        
        // Act & Assert
        assertThrows(UnsupportedOperationException.class, () -> {
            exception.getRuleViolations().add(new BusinessRuleException.BusinessRuleViolation("TIME_IN_BUSINESS", "Business must be operating for at least 2 years"));
        });
    }
    
    @Test
    @DisplayName("Should verify hasRuleViolations and getRuleViolationCount methods")
    public void testHasRuleViolationsAndGetRuleViolationCount() {
        // Arrange & Act
        BusinessRuleException emptyException = new BusinessRuleException("Business rule violation occurred");
        
        // Assert
        assertFalse(emptyException.hasRuleViolations());
        assertEquals(0, emptyException.getRuleViolationCount());
        
        // Arrange & Act
        BusinessRuleException exceptionWithViolations = new BusinessRuleException("Business rule violation occurred", "REVENUE_MIN", "Revenue must be at least $100,000");
        
        // Assert
        assertTrue(exceptionWithViolations.hasRuleViolations());
        assertEquals(1, exceptionWithViolations.getRuleViolationCount());
        
        // Add more violations
        exceptionWithViolations.addRuleViolation("TIME_IN_BUSINESS", "Business must be operating for at least 2 years");
        
        // Assert again
        assertTrue(exceptionWithViolations.hasRuleViolations());
        assertEquals(2, exceptionWithViolations.getRuleViolationCount());
    }
    
    @Test
    @DisplayName("Should verify method chaining for addRuleViolation")
    public void testMethodChainingForAddRuleViolation() {
        // Arrange
        BusinessRuleException exception = new BusinessRuleException("Business rule violation occurred");
        
        // Act
        exception
            .addRuleViolation("REVENUE_MIN", "Revenue must be at least $100,000")
            .addRuleViolation("TIME_IN_BUSINESS", "Business must be operating for at least 2 years")
            .addRuleViolation("CREDIT_SCORE", "Credit score must be at least 650");
        
        // Assert
        assertTrue(exception.hasRuleViolations());
        assertEquals(3, exception.getRuleViolationCount());
        
        List<BusinessRuleException.BusinessRuleViolation> violations = exception.getRuleViolations();
        assertEquals(3, violations.size());
        assertEquals("REVENUE_MIN", violations.get(0).getRuleId());
        assertEquals("Revenue must be at least $100,000", violations.get(0).getMessage());
        assertEquals("TIME_IN_BUSINESS", violations.get(1).getRuleId());
        assertEquals("Business must be operating for at least 2 years", violations.get(1).getMessage());
        assertEquals("CREDIT_SCORE", violations.get(2).getRuleId());
        assertEquals("Credit score must be at least 650", violations.get(2).getMessage());
    }
    
    @Test
    @DisplayName("Should verify method chaining for addRuleViolations")
    public void testMethodChainingForAddRuleViolations() {
        // Arrange
        BusinessRuleException exception = new BusinessRuleException("Business rule violation occurred");
        List<BusinessRuleException.BusinessRuleViolation> firstBatch = new ArrayList<>();
        firstBatch.add(new BusinessRuleException.BusinessRuleViolation("REVENUE_MIN", "Revenue must be at least $100,000"));
        firstBatch.add(new BusinessRuleException.BusinessRuleViolation("TIME_IN_BUSINESS", "Business must be operating for at least 2 years"));
        
        List<BusinessRuleException.BusinessRuleViolation> secondBatch = new ArrayList<>();
        secondBatch.add(new BusinessRuleException.BusinessRuleViolation("CREDIT_SCORE", "Credit score must be at least 650"));
        secondBatch.add(new BusinessRuleException.BusinessRuleViolation("REQUIRED_DOCS", "All required documents must be submitted"));
        
        // Act
        exception
            .addRuleViolations(firstBatch)
            .addRuleViolations(secondBatch);
        
        // Assert
        assertTrue(exception.hasRuleViolations());
        assertEquals(4, exception.getRuleViolationCount());
        
        List<BusinessRuleException.BusinessRuleViolation> violations = exception.getRuleViolations();
        assertEquals(4, violations.size());
        assertEquals("REVENUE_MIN", violations.get(0).getRuleId());
        assertEquals("Revenue must be at least $100,000", violations.get(0).getMessage());
        assertEquals("TIME_IN_BUSINESS", violations.get(1).getRuleId());
        assertEquals("Business must be operating for at least 2 years", violations.get(1).getMessage());
        assertEquals("CREDIT_SCORE", violations.get(2).getRuleId());
        assertEquals("Credit score must be at least 650", violations.get(2).getMessage());
        assertEquals("REQUIRED_DOCS", violations.get(3).getRuleId());
        assertEquals("All required documents must be submitted", violations.get(3).getMessage());
    }
    
    @Test
    @DisplayName("Should test BusinessRuleViolation class with and without rejected value")
    public void testBusinessRuleViolationClass() {
        // Arrange & Act
        BusinessRuleException.BusinessRuleViolation violationWithoutRejectedValue = 
            new BusinessRuleException.BusinessRuleViolation("REVENUE_MIN", "Revenue must be at least $100,000");
        
        BusinessRuleException.BusinessRuleViolation violationWithRejectedValue = 
            new BusinessRuleException.BusinessRuleViolation("REVENUE_MIN", "Revenue must be at least $100,000", 50000);
        
        // Assert
        assertEquals("REVENUE_MIN", violationWithoutRejectedValue.getRuleId());
        assertEquals("Revenue must be at least $100,000", violationWithoutRejectedValue.getMessage());
        assertNull(violationWithoutRejectedValue.getRejectedValue());
        
        assertEquals("REVENUE_MIN", violationWithRejectedValue.getRuleId());
        assertEquals("Revenue must be at least $100,000", violationWithRejectedValue.getMessage());
        assertEquals(50000, violationWithRejectedValue.getRejectedValue());
    }
}