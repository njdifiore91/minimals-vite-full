package com.dollarfunding.mca.exception;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link BusinessRuleException} class.
 * 
 * These tests verify that the BusinessRuleException properly handles business rule
 * violations with appropriate HTTP status codes, rule identifiers, and violation details.
 */
public class BusinessRuleExceptionTest {

    private static final String RULE_ID = "TEST_RULE";
    private static final String ERROR_MESSAGE = "Test business rule violation";

    @Test
    public void testConstructorWithRuleIdAndMessage() {
        // When
        BusinessRuleException exception = new BusinessRuleException(RULE_ID, ERROR_MESSAGE);
        
        // Then
        assertEquals(RULE_ID, exception.getRuleId());
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY.value(), exception.getStatusCode());
        assertEquals("BUSINESS_RULE_VIOLATION", exception.getErrorCode());
        assertNotNull(exception.getViolationDetails());
        assertTrue(exception.getViolationDetails().isEmpty());
    }

    @Test
    public void testConstructorWithRuleIdMessageAndViolationDetails() {
        // Given
        Map<String, Object> details = new HashMap<>();
        details.put("key1", "value1");
        details.put("key2", 123);
        
        // When
        BusinessRuleException exception = new BusinessRuleException(RULE_ID, ERROR_MESSAGE, details);
        
        // Then
        assertEquals(RULE_ID, exception.getRuleId());
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertEquals("BUSINESS_RULE_VIOLATION", exception.getErrorCode());
        assertNotNull(exception.getViolationDetails());
        assertEquals(2, exception.getViolationDetails().size());
        assertEquals("value1", exception.getViolationDetails().get("key1"));
        assertEquals(123, exception.getViolationDetails().get("key2"));
    }

    @Test
    public void testConstructorWithRuleIdMessageAndCause() {
        // Given
        Throwable cause = new RuntimeException("Original cause");
        
        // When
        BusinessRuleException exception = new BusinessRuleException(RULE_ID, ERROR_MESSAGE, cause);
        
        // Then
        assertEquals(RULE_ID, exception.getRuleId());
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertEquals("BUSINESS_RULE_VIOLATION", exception.getErrorCode());
        assertSame(cause, exception.getCause());
        assertNotNull(exception.getViolationDetails());
        assertTrue(exception.getViolationDetails().isEmpty());
    }

    @Test
    public void testConstructorWithRuleIdMessageCauseAndViolationDetails() {
        // Given
        Throwable cause = new RuntimeException("Original cause");
        Map<String, Object> details = new HashMap<>();
        details.put("key1", "value1");
        details.put("key2", 123);
        
        // When
        BusinessRuleException exception = new BusinessRuleException(RULE_ID, ERROR_MESSAGE, cause, details);
        
        // Then
        assertEquals(RULE_ID, exception.getRuleId());
        assertEquals(ERROR_MESSAGE, exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertEquals("BUSINESS_RULE_VIOLATION", exception.getErrorCode());
        assertSame(cause, exception.getCause());
        assertNotNull(exception.getViolationDetails());
        assertEquals(2, exception.getViolationDetails().size());
        assertEquals("value1", exception.getViolationDetails().get("key1"));
        assertEquals(123, exception.getViolationDetails().get("key2"));
    }

    @Test
    public void testConstructorWithNullViolationDetails() {
        // When
        BusinessRuleException exception = new BusinessRuleException(RULE_ID, ERROR_MESSAGE, (Map<String, Object>) null);
        
        // Then
        assertNotNull(exception.getViolationDetails());
        assertTrue(exception.getViolationDetails().isEmpty());
    }

    @Test
    public void testAddViolationDetail() {
        // Given
        BusinessRuleException exception = new BusinessRuleException(RULE_ID, ERROR_MESSAGE);
        
        // When
        exception.addViolationDetail("key1", "value1");
        exception.addViolationDetail("key2", 123);
        
        // Then
        assertEquals(2, exception.getViolationDetails().size());
        assertEquals("value1", exception.getViolationDetails().get("key1"));
        assertEquals(123, exception.getViolationDetails().get("key2"));
    }

    @Test
    public void testViolationDetailsDefensiveCopy() {
        // Given
        Map<String, Object> details = new HashMap<>();
        details.put("key1", "value1");
        BusinessRuleException exception = new BusinessRuleException(RULE_ID, ERROR_MESSAGE, details);
        
        // When - modify the original map
        details.put("key2", "value2");
        
        // Then - exception's map should not be affected
        assertEquals(1, exception.getViolationDetails().size());
        assertFalse(exception.getViolationDetails().containsKey("key2"));
        
        // When - modify the returned map
        Map<String, Object> returnedDetails = exception.getViolationDetails();
        returnedDetails.put("key3", "value3");
        
        // Then - exception's internal map should not be affected
        assertFalse(exception.getViolationDetails().containsKey("key3"));
    }

    @Test
    public void testInsufficientRevenueFactory() {
        // Given
        double requiredRevenue = 100000.0;
        double actualRevenue = 75000.0;
        
        // When
        BusinessRuleException exception = BusinessRuleException.insufficientRevenue(requiredRevenue, actualRevenue);
        
        // Then
        assertEquals("INSUFFICIENT_REVENUE", exception.getRuleId());
        assertEquals("Merchant revenue does not meet the minimum requirement for approval", exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertEquals(requiredRevenue, exception.getViolationDetails().get("requiredRevenue"));
        assertEquals(actualRevenue, exception.getViolationDetails().get("actualRevenue"));
    }

    @Test
    public void testMissingRequiredDocumentFactory() {
        // Given
        String documentType = "BANK_STATEMENT";
        
        // When
        BusinessRuleException exception = BusinessRuleException.missingRequiredDocument(documentType);
        
        // Then
        assertEquals("MISSING_REQUIRED_DOCUMENT", exception.getRuleId());
        assertEquals("Required document is missing: BANK_STATEMENT", exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertEquals(documentType, exception.getViolationDetails().get("documentType"));
    }

    @Test
    public void testBusinessAgeTooNewFactory() {
        // Given
        int requiredMonths = 12;
        int actualMonths = 6;
        
        // When
        BusinessRuleException exception = BusinessRuleException.businessAgeTooNew(requiredMonths, actualMonths);
        
        // Then
        assertEquals("BUSINESS_AGE_REQUIREMENT_NOT_MET", exception.getRuleId());
        assertEquals("Business does not meet the minimum age requirement for approval", exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertEquals(requiredMonths, exception.getViolationDetails().get("requiredMonths"));
        assertEquals(actualMonths, exception.getViolationDetails().get("actualMonths"));
    }

    @Test
    public void testInvalidIndustryFactory() {
        // Given
        String industry = "GAMBLING";
        
        // When
        BusinessRuleException exception = BusinessRuleException.invalidIndustry(industry);
        
        // Then
        assertEquals("INVALID_INDUSTRY", exception.getRuleId());
        assertEquals("The industry is not eligible for funding: GAMBLING", exception.getMessage());
        assertEquals(HttpStatus.UNPROCESSABLE_ENTITY, exception.getHttpStatus());
        assertEquals(industry, exception.getViolationDetails().get("industry"));
    }
}