package com.dollarfunding.mca.util;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Utility class for validating data in the MCA application.
 * Provides methods for validating common data formats such as email addresses,
 * phone numbers, tax IDs, and business information according to business rules.
 */
public class ValidationUtil {

    // Email validation pattern
    private static final Pattern EMAIL_PATTERN = 
        Pattern.compile("^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$");
    
    // Phone number validation pattern (US format)
    private static final Pattern PHONE_PATTERN = 
        Pattern.compile("^(\\([2-9]|[2-9])(\\d{2}|\\d{2}\\))(-|.|\\s)?\\d{3}(-|.|\\s)?\\d{4}$");
    
    // Tax ID (EIN/TIN) validation pattern
    private static final Pattern TAX_ID_PATTERN = 
        Pattern.compile("^([07][1-7]|1[0-6]|2[0-7]|[35][0-9]|[468][0-8]|9[0-589])-?\\d{7}$");
    
    // Business name validation pattern
    private static final Pattern BUSINESS_NAME_PATTERN = 
        Pattern.compile("^[a-zA-Z0-9\\s,.'-]{2,100}$");
    
    // Address validation pattern
    private static final Pattern ADDRESS_PATTERN = 
        Pattern.compile("^[a-zA-Z0-9\\s,.'-]{5,200}$");
    
    // Bank account number validation pattern
    private static final Pattern BANK_ACCOUNT_PATTERN = 
        Pattern.compile("^[0-9]{9,17}$");
    
    // Bank routing number validation pattern
    private static final Pattern ROUTING_NUMBER_PATTERN = 
        Pattern.compile("^[0-9]{9}$");

    /**
     * Validates if the provided email address is in a valid format.
     *
     * @param email The email address to validate
     * @return true if the email is valid, false otherwise
     */
    public static boolean isValidEmail(String email) {
        if (email == null || email.trim().isEmpty()) {
            return false;
        }
        
        Matcher matcher = EMAIL_PATTERN.matcher(email);
        return matcher.matches();
    }

    /**
     * Validates if the provided phone number is in a valid format.
     * Accepts formats like: 223-123-1234, (223) 123-1234, 2231231234
     *
     * @param phoneNumber The phone number to validate
     * @return true if the phone number is valid, false otherwise
     */
    public static boolean isValidPhoneNumber(String phoneNumber) {
        if (phoneNumber == null || phoneNumber.trim().isEmpty()) {
            return false;
        }
        
        // Remove any non-digit characters for additional validation
        String digitsOnly = phoneNumber.replaceAll("\\D", "");
        
        // Check if the phone number has the correct number of digits
        if (digitsOnly.length() < 10 || digitsOnly.length() > 11) {
            return false;
        }
        
        // If it's 11 digits, the first digit should be 1 (country code)
        if (digitsOnly.length() == 11 && digitsOnly.charAt(0) != '1') {
            return false;
        }
        
        Matcher matcher = PHONE_PATTERN.matcher(phoneNumber);
        return matcher.matches();
    }

    /**
     * Validates if the provided tax ID (EIN/TIN) is in a valid format.
     * Accepts formats like: 12-3456789 or 123456789
     *
     * @param taxId The tax ID to validate
     * @return true if the tax ID is valid, false otherwise
     */
    public static boolean isValidTaxId(String taxId) {
        if (taxId == null || taxId.trim().isEmpty()) {
            return false;
        }
        
        // Remove any non-digit or non-hyphen characters
        String cleanTaxId = taxId.replaceAll("[^0-9-]", "");
        
        // Check if all digits are the same (e.g., 11-1111111)
        String digitsOnly = cleanTaxId.replaceAll("-", "");
        if (digitsOnly.matches("(\\d)\\1{8}")) {
            return false;
        }
        
        Matcher matcher = TAX_ID_PATTERN.matcher(cleanTaxId);
        return matcher.matches();
    }

    /**
     * Validates if the provided business name is in a valid format.
     * Business names should be 2-100 characters and contain only letters, numbers,
     * spaces, and common punctuation.
     *
     * @param businessName The business name to validate
     * @return true if the business name is valid, false otherwise
     */
    public static boolean isValidBusinessName(String businessName) {
        if (businessName == null || businessName.trim().isEmpty()) {
            return false;
        }
        
        // Check if the business name is too short or too long
        if (businessName.length() < 2 || businessName.length() > 100) {
            return false;
        }
        
        Matcher matcher = BUSINESS_NAME_PATTERN.matcher(businessName);
        return matcher.matches();
    }

    /**
     * Validates if the provided address is in a valid format.
     * Addresses should be 5-200 characters and contain only letters, numbers,
     * spaces, and common punctuation.
     *
     * @param address The address to validate
     * @return true if the address is valid, false otherwise
     */
    public static boolean isValidAddress(String address) {
        if (address == null || address.trim().isEmpty()) {
            return false;
        }
        
        // Check if the address is too short or too long
        if (address.length() < 5 || address.length() > 200) {
            return false;
        }
        
        Matcher matcher = ADDRESS_PATTERN.matcher(address);
        return matcher.matches();
    }

    /**
     * Validates if the provided bank account number is in a valid format.
     * Bank account numbers should be 9-17 digits.
     *
     * @param accountNumber The bank account number to validate
     * @return true if the bank account number is valid, false otherwise
     */
    public static boolean isValidBankAccount(String accountNumber) {
        if (accountNumber == null || accountNumber.trim().isEmpty()) {
            return false;
        }
        
        // Remove any non-digit characters
        String digitsOnly = accountNumber.replaceAll("\\D", "");
        
        Matcher matcher = BANK_ACCOUNT_PATTERN.matcher(digitsOnly);
        return matcher.matches();
    }

    /**
     * Validates if the provided bank routing number is in a valid format.
     * Bank routing numbers should be 9 digits.
     *
     * @param routingNumber The bank routing number to validate
     * @return true if the bank routing number is valid, false otherwise
     */
    public static boolean isValidRoutingNumber(String routingNumber) {
        if (routingNumber == null || routingNumber.trim().isEmpty()) {
            return false;
        }
        
        // Remove any non-digit characters
        String digitsOnly = routingNumber.replaceAll("\\D", "");
        
        Matcher matcher = ROUTING_NUMBER_PATTERN.matcher(digitsOnly);
        
        if (!matcher.matches()) {
            return false;
        }
        
        // Additional validation: Apply the ABA routing number checksum algorithm
        // The 9th digit is a checksum of the first 8 digits
        return validateRoutingNumberChecksum(digitsOnly);
    }
    
    /**
     * Validates the checksum of a routing number using the ABA algorithm.
     * The algorithm is: [3(d1 + d4 + d7) + 7(d2 + d5 + d8) + (d3 + d6 + d9)] mod 10 = 0
     *
     * @param routingNumber The routing number (digits only)
     * @return true if the checksum is valid, false otherwise
     */
    private static boolean validateRoutingNumberChecksum(String routingNumber) {
        if (routingNumber.length() != 9) {
            return false;
        }
        
        int sum = 0;
        
        // Apply the ABA routing number checksum algorithm
        sum += 3 * (Character.getNumericValue(routingNumber.charAt(0)) + 
                    Character.getNumericValue(routingNumber.charAt(3)) + 
                    Character.getNumericValue(routingNumber.charAt(6)));
                    
        sum += 7 * (Character.getNumericValue(routingNumber.charAt(1)) + 
                    Character.getNumericValue(routingNumber.charAt(4)) + 
                    Character.getNumericValue(routingNumber.charAt(7)));
                    
        sum += Character.getNumericValue(routingNumber.charAt(2)) + 
               Character.getNumericValue(routingNumber.charAt(5)) + 
               Character.getNumericValue(routingNumber.charAt(8));
        
        return (sum % 10 == 0);
    }

    /**
     * Validates a complete application data object against business rules.
     * This method aggregates multiple validation checks to ensure the entire
     * application meets all business requirements.
     *
     * @param applicationData The application data object to validate
     * @param validationErrors A list to store validation error messages
     * @return true if the application data is valid, false otherwise
     */
    public static boolean validateApplicationData(Object applicationData, List<String> validationErrors) {
        // This is a placeholder for the comprehensive application validation logic
        // In a real implementation, this would validate all required fields and business rules
        // based on the application data structure
        
        if (applicationData == null) {
            validationErrors.add("Application data cannot be null");
            return false;
        }
        
        boolean isValid = true;
        
        // Example validation logic (to be replaced with actual implementation):
        // 1. Check if all required fields are present
        // 2. Validate each field using the appropriate validation method
        // 3. Apply business-specific validation rules
        // 4. Check for data consistency across fields
        
        // This method would typically extract fields from the applicationData object
        // and validate them using the individual validation methods in this class.
        // For each validation failure, add a descriptive error message to the validationErrors list.
        
        return isValid;
    }
    
    /**
     * Overloaded method for validateApplicationData that doesn't require an error list.
     *
     * @param applicationData The application data object to validate
     * @return true if the application data is valid, false otherwise
     */
    public static boolean validateApplicationData(Object applicationData) {
        List<String> validationErrors = new ArrayList<>();
        return validateApplicationData(applicationData, validationErrors);
    }
}