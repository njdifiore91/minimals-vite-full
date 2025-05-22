package com.dollarfunding.mca.util;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the ValidationUtil class.
 * Tests validation of email addresses, phone numbers, tax IDs, business names,
 * addresses, bank account numbers, routing numbers, and complete application data.
 */
@DisplayName("ValidationUtil Tests")
public class ValidationUtilTest {

    @DisplayName("Test email validation with valid emails")
    @ParameterizedTest
    @ValueSource(strings = {
        "test@example.com",
        "user.name@domain.com",
        "user+tag@example.com",
        "customer-support@company-name.com",
        "info@dollarfunding.com",
        "submissions@dollarfunding.com"
    })
    void isValidEmail_withValidEmails_shouldReturnTrue(String email) {
        assertTrue(ValidationUtil.isValidEmail(email), "Valid email " + email + " should be accepted");
    }

    @DisplayName("Test email validation with invalid emails")
    @ParameterizedTest
    @ValueSource(strings = {
        "plainaddress",
        "@domain.com",
        "user@",
        "user@.com",
        "user@domain@domain.com",
        "user..name@domain.com",
        ".user@domain.com",
        "user.@domain.com",
        "user@domain..com"
    })
    @NullAndEmptySource
    void isValidEmail_withInvalidEmails_shouldReturnFalse(String email) {
        assertFalse(ValidationUtil.isValidEmail(email), "Invalid email " + email + " should be rejected");
    }

    @DisplayName("Test phone number validation with valid phone numbers")
    @ParameterizedTest
    @ValueSource(strings = {
        "(223) 456-7890",
        "223-456-7890",
        "2234567890",
        "(800) 555-1234",
        "800-555-1234",
        "8005551234",
        "(555) 123-4567",
        "555.123.4567"
    })
    void isValidPhoneNumber_withValidPhoneNumbers_shouldReturnTrue(String phoneNumber) {
        assertTrue(ValidationUtil.isValidPhoneNumber(phoneNumber), 
                 "Valid phone number " + phoneNumber + " should be accepted");
    }

    @DisplayName("Test phone number validation with invalid phone numbers")
    @ParameterizedTest
    @ValueSource(strings = {
        "123-456-7890", // Invalid area code starting with 1
        "(123) 456-7890", // Invalid area code starting with 1
        "1234567890", // Invalid area code starting with 1
        "(023) 456-7890", // Invalid area code starting with 0
        "023-456-7890", // Invalid area code starting with 0
        "0234567890", // Invalid area code starting with 0
        "223-45-7890", // Too few digits
        "223-456-78901", // Too many digits
        "223-456-789a", // Contains non-numeric characters
        "22-3456-7890", // Incorrect format
        "22345678901234567890" // Way too long
    })
    @NullAndEmptySource
    void isValidPhoneNumber_withInvalidPhoneNumbers_shouldReturnFalse(String phoneNumber) {
        assertFalse(ValidationUtil.isValidPhoneNumber(phoneNumber), 
                  "Invalid phone number " + phoneNumber + " should be rejected");
    }

    @DisplayName("Test tax ID validation with valid tax IDs")
    @ParameterizedTest
    @ValueSource(strings = {
        "12-3456789",
        "123456789",
        "55-1234567",
        "551234567",
        "20-1234567",
        "201234567",
        "98-7654321",
        "987654321"
    })
    void isValidTaxId_withValidTaxIds_shouldReturnTrue(String taxId) {
        assertTrue(ValidationUtil.isValidTaxId(taxId), 
                 "Valid tax ID " + taxId + " should be accepted");
    }

    @DisplayName("Test tax ID validation with invalid tax IDs")
    @ParameterizedTest
    @ValueSource(strings = {
        "00-1234567", // Invalid prefix
        "001234567", // Invalid prefix
        "12-345678", // Too short
        "12-34567890", // Too long
        "12-345678A", // Contains non-numeric characters
        "12345678A", // Contains non-numeric characters
        "12--3456789", // Incorrect format
        "11-1111111", // All same digits
        "111111111", // All same digits
        "99-9999999", // Invalid prefix
        "999999999" // Invalid prefix
    })
    @NullAndEmptySource
    void isValidTaxId_withInvalidTaxIds_shouldReturnFalse(String taxId) {
        assertFalse(ValidationUtil.isValidTaxId(taxId), 
                  "Invalid tax ID " + taxId + " should be rejected");
    }

    @DisplayName("Test business name validation with valid business names")
    @ParameterizedTest
    @ValueSource(strings = {
        "ABC Corp",
        "Smith & Sons, LLC",
        "Johnson's Hardware",
        "123 Tech Solutions",
        "Global Enterprises Inc.",
        "Main Street Cafe",
        "Dollar Funding Services",
        "A-1 Auto Parts"
    })
    void isValidBusinessName_withValidBusinessNames_shouldReturnTrue(String businessName) {
        assertTrue(ValidationUtil.isValidBusinessName(businessName), 
                 "Valid business name " + businessName + " should be accepted");
    }

    @DisplayName("Test business name validation with invalid business names")
    @ParameterizedTest
    @ValueSource(strings = {
        "A", // Too short
        "This business name is way too long and exceeds the maximum character limit of one hundred characters which is not allowed in our system", // Too long
        "Business Name with @ symbol", // Invalid character
        "Business Name with # symbol", // Invalid character
        "Business Name with $ symbol", // Invalid character
        "Business Name with % symbol", // Invalid character
        "Business Name with ^ symbol" // Invalid character
    })
    @NullAndEmptySource
    void isValidBusinessName_withInvalidBusinessNames_shouldReturnFalse(String businessName) {
        assertFalse(ValidationUtil.isValidBusinessName(businessName), 
                  "Invalid business name " + businessName + " should be rejected");
    }

    @DisplayName("Test address validation with valid addresses")
    @ParameterizedTest
    @ValueSource(strings = {
        "123 Main St, Anytown, CA 12345",
        "456 Oak Avenue, Suite 789, Big City, NY 10001",
        "1 Corporate Drive, Building A, Floor 3, Business Park, TX 75001",
        "789 Residential Lane, Apt 42, Hometown, FL 33101",
        "555 Industrial Blvd, Unit 100, Factoryville, MI 48001",
        "42 Technology Way, Tech Park, CA 94043"
    })
    void isValidAddress_withValidAddresses_shouldReturnTrue(String address) {
        assertTrue(ValidationUtil.isValidAddress(address), 
                 "Valid address " + address + " should be accepted");
    }

    @DisplayName("Test address validation with invalid addresses")
    @ParameterizedTest
    @ValueSource(strings = {
        "123", // Too short
        "A St", // Too short
        "This address is extremely long and exceeds the maximum character limit. It contains way too many unnecessary details and would not fit properly in our database fields. The address should be concise and contain only the essential information needed for delivery or identification purposes. We cannot accept addresses that are this verbose and detailed as they cause issues with our systems.", // Too long
        "123 Main St, Anytown, CA 12345 @", // Invalid character
        "123 Main St, Anytown, CA 12345 #", // Invalid character
        "123 Main St, Anytown, CA 12345 $", // Invalid character
        "123 Main St, Anytown, CA 12345 %" // Invalid character
    })
    @NullAndEmptySource
    void isValidAddress_withInvalidAddresses_shouldReturnFalse(String address) {
        assertFalse(ValidationUtil.isValidAddress(address), 
                  "Invalid address " + address + " should be rejected");
    }

    @DisplayName("Test bank account validation with valid account numbers")
    @ParameterizedTest
    @ValueSource(strings = {
        "123456789", // 9 digits
        "1234567890", // 10 digits
        "12345678901", // 11 digits
        "123456789012", // 12 digits
        "1234567890123", // 13 digits
        "12345678901234", // 14 digits
        "123456789012345", // 15 digits
        "1234567890123456", // 16 digits
        "12345678901234567" // 17 digits
    })
    void isValidBankAccount_withValidAccountNumbers_shouldReturnTrue(String accountNumber) {
        assertTrue(ValidationUtil.isValidBankAccount(accountNumber), 
                 "Valid account number " + accountNumber + " should be accepted");
    }

    @DisplayName("Test bank account validation with invalid account numbers")
    @ParameterizedTest
    @ValueSource(strings = {
        "12345678", // Too short (8 digits)
        "123456789012345678", // Too long (18 digits)
        "12345-6789", // Contains non-digit characters
        "123456789A", // Contains non-digit characters
        "ABCDEFGHI" // Non-numeric
    })
    @NullAndEmptySource
    void isValidBankAccount_withInvalidAccountNumbers_shouldReturnFalse(String accountNumber) {
        assertFalse(ValidationUtil.isValidBankAccount(accountNumber), 
                  "Invalid account number " + accountNumber + " should be rejected");
    }

    @DisplayName("Test routing number validation with valid routing numbers")
    @ParameterizedTest
    @ValueSource(strings = {
        "021000021", // JPMorgan Chase
        "026009593", // Bank of America
        "011401533", // First National Bank
        "091000022", // US Bank
        "071000013", // PNC Bank
        "061000104", // SunTrust Bank
        "121000248", // Wells Fargo
        "122105155"  // US Bank
    })
    void isValidRoutingNumber_withValidRoutingNumbers_shouldReturnTrue(String routingNumber) {
        assertTrue(ValidationUtil.isValidRoutingNumber(routingNumber), 
                 "Valid routing number " + routingNumber + " should be accepted");
    }

    @DisplayName("Test routing number validation with invalid routing numbers")
    @ParameterizedTest
    @ValueSource(strings = {
        "12345678", // Too short (8 digits)
        "1234567890", // Too long (10 digits)
        "123456789", // Invalid checksum
        "000000000", // Invalid (all zeros)
        "999999999", // Invalid checksum
        "12345-678", // Contains non-digit characters
        "12345678A", // Contains non-digit characters
        "ABCDEFGHI" // Non-numeric
    })
    @NullAndEmptySource
    void isValidRoutingNumber_withInvalidRoutingNumbers_shouldReturnFalse(String routingNumber) {
        assertFalse(ValidationUtil.isValidRoutingNumber(routingNumber), 
                  "Invalid routing number " + routingNumber + " should be rejected");
    }

    @Test
    @DisplayName("Test application data validation with null application data")
    void validateApplicationData_withNullApplicationData_shouldReturnFalse() {
        List<String> validationErrors = new ArrayList<>();
        assertFalse(ValidationUtil.validateApplicationData(null, validationErrors));
        assertFalse(validationErrors.isEmpty(), "Validation errors list should not be empty");
        assertEquals("Application data cannot be null", validationErrors.get(0));
    }

    @Test
    @DisplayName("Test application data validation with overloaded method")
    void validateApplicationData_withOverloadedMethod_shouldReturnSameResult() {
        // Since the implementation of validateApplicationData is a placeholder,
        // we're just testing that the overloaded method calls the main method correctly
        // This test would be expanded in a real implementation
        
        // Create a mock application data object
        Object mockApplicationData = new Object();
        
        // Test both methods with the same input
        List<String> validationErrors = new ArrayList<>();
        boolean resultWithErrorList = ValidationUtil.validateApplicationData(mockApplicationData, validationErrors);
        boolean resultWithoutErrorList = ValidationUtil.validateApplicationData(mockApplicationData);
        
        // Both methods should return the same result
        assertEquals(resultWithErrorList, resultWithoutErrorList, 
                    "Both validateApplicationData methods should return the same result");
    }

    /**
     * This test would be expanded in a real implementation to test actual application data validation.
     * For now, it's a placeholder that tests the basic functionality of the method.
     */
    @Test
    @DisplayName("Test application data validation with mock application data")
    void validateApplicationData_withMockApplicationData_shouldValidateCorrectly() {
        // Create a mock application data object
        // In a real implementation, this would be a proper application data object
        // with all the required fields
        Object mockApplicationData = new Object();
        
        List<String> validationErrors = new ArrayList<>();
        boolean result = ValidationUtil.validateApplicationData(mockApplicationData, validationErrors);
        
        // Since the implementation is a placeholder that always returns true for non-null input,
        // we expect the result to be true and the validation errors list to be empty
        assertTrue(result, "Validation should pass for non-null application data");
        assertTrue(validationErrors.isEmpty(), "Validation errors list should be empty for valid application data");
    }
}