package com.dollarfunding.mca.exception;

import org.springframework.http.HttpStatus;

import java.util.HashMap;
import java.util.Map;

/**
 * Exception thrown when a business rule violation occurs during application processing.
 * It extends BaseException with a default HTTP status code of 422 (Unprocessable Entity)
 * and provides support for rule identifiers and violation details.
 */
public class BusinessRuleException extends BaseException {

    private final String ruleId;
    private final Map<String, Object> violationDetails;

    /**
     * Constructs a new BusinessRuleException with the specified rule ID and message.
     *
     * @param ruleId  the identifier of the business rule that was violated
     * @param message the detail message
     */
    public BusinessRuleException(String ruleId, String message) {
        super("BUSINESS_RULE_VIOLATION", message, HttpStatus.UNPROCESSABLE_ENTITY);
        this.ruleId = ruleId;
        this.violationDetails = new HashMap<>();
    }

    /**
     * Constructs a new BusinessRuleException with the specified rule ID, message, and violation details.
     *
     * @param ruleId           the identifier of the business rule that was violated
     * @param message          the detail message
     * @param violationDetails a map containing details about the violation
     */
    public BusinessRuleException(String ruleId, String message, Map<String, Object> violationDetails) {
        super("BUSINESS_RULE_VIOLATION", message, HttpStatus.UNPROCESSABLE_ENTITY);
        this.ruleId = ruleId;
        this.violationDetails = violationDetails != null ? new HashMap<>(violationDetails) : new HashMap<>();
    }

    /**
     * Constructs a new BusinessRuleException with the specified rule ID, message, and cause.
     *
     * @param ruleId  the identifier of the business rule that was violated
     * @param message the detail message
     * @param cause   the cause of this exception
     */
    public BusinessRuleException(String ruleId, String message, Throwable cause) {
        super("BUSINESS_RULE_VIOLATION", message, cause, HttpStatus.UNPROCESSABLE_ENTITY);
        this.ruleId = ruleId;
        this.violationDetails = new HashMap<>();
    }

    /**
     * Constructs a new BusinessRuleException with the specified rule ID, message, cause, and violation details.
     *
     * @param ruleId           the identifier of the business rule that was violated
     * @param message          the detail message
     * @param cause            the cause of this exception
     * @param violationDetails a map containing details about the violation
     */
    public BusinessRuleException(String ruleId, String message, Throwable cause, Map<String, Object> violationDetails) {
        super("BUSINESS_RULE_VIOLATION", message, cause, HttpStatus.UNPROCESSABLE_ENTITY);
        this.ruleId = ruleId;
        this.violationDetails = violationDetails != null ? new HashMap<>(violationDetails) : new HashMap<>();
    }

    /**
     * Returns the identifier of the business rule that was violated.
     *
     * @return the rule identifier
     */
    public String getRuleId() {
        return ruleId;
    }

    /**
     * Returns the details about the violation.
     *
     * @return a map containing violation details
     */
    public Map<String, Object> getViolationDetails() {
        return new HashMap<>(violationDetails);
    }

    /**
     * Adds a detail about the violation.
     *
     * @param key   the key for the detail
     * @param value the value of the detail
     * @return this exception instance for method chaining
     */
    public BusinessRuleException addViolationDetail(String key, Object value) {
        this.violationDetails.put(key, value);
        return this;
    }

    /**
     * Creates a new BusinessRuleException for insufficient revenue scenario.
     *
     * @param requiredRevenue the minimum required revenue
     * @param actualRevenue   the actual revenue
     * @return a new BusinessRuleException instance
     */
    public static BusinessRuleException insufficientRevenue(double requiredRevenue, double actualRevenue) {
        Map<String, Object> details = new HashMap<>();
        details.put("requiredRevenue", requiredRevenue);
        details.put("actualRevenue", actualRevenue);
        return new BusinessRuleException(
                "INSUFFICIENT_REVENUE",
                "Merchant revenue does not meet the minimum requirement for approval",
                details
        );
    }

    /**
     * Creates a new BusinessRuleException for missing required document scenario.
     *
     * @param documentType the type of document that is missing
     * @return a new BusinessRuleException instance
     */
    public static BusinessRuleException missingRequiredDocument(String documentType) {
        Map<String, Object> details = new HashMap<>();
        details.put("documentType", documentType);
        return new BusinessRuleException(
                "MISSING_REQUIRED_DOCUMENT",
                "Required document is missing: " + documentType,
                details
        );
    }

    /**
     * Creates a new BusinessRuleException for business age requirement not met scenario.
     *
     * @param requiredMonths the minimum required business age in months
     * @param actualMonths   the actual business age in months
     * @return a new BusinessRuleException instance
     */
    public static BusinessRuleException businessAgeTooNew(int requiredMonths, int actualMonths) {
        Map<String, Object> details = new HashMap<>();
        details.put("requiredMonths", requiredMonths);
        details.put("actualMonths", actualMonths);
        return new BusinessRuleException(
                "BUSINESS_AGE_REQUIREMENT_NOT_MET",
                "Business does not meet the minimum age requirement for approval",
                details
        );
    }

    /**
     * Creates a new BusinessRuleException for invalid industry scenario.
     *
     * @param industry the invalid industry
     * @return a new BusinessRuleException instance
     */
    public static BusinessRuleException invalidIndustry(String industry) {
        Map<String, Object> details = new HashMap<>();
        details.put("industry", industry);
        return new BusinessRuleException(
                "INVALID_INDUSTRY",
                "The industry is not eligible for funding: " + industry,
                details
        );
    }
}