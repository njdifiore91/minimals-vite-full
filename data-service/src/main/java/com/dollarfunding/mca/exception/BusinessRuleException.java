package com.dollarfunding.mca.exception;

import org.springframework.http.HttpStatus;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Exception thrown when a business rule violation occurs during application processing.
 * <p>
 * This exception extends BaseException with a default HTTP status code of 422 (Unprocessable Entity)
 * and provides support for rule identifiers and violation details. It is used by services to indicate
 * business logic failures, such as insufficient revenue for approval or missing required documents.
 * </p>
 */
public class BusinessRuleException extends BaseException {

    private final List<BusinessRuleViolation> ruleViolations;

    /**
     * Constructs a new BusinessRuleException with the specified message.
     *
     * @param message the detail message
     */
    public BusinessRuleException(String message) {
        super(message, HttpStatus.UNPROCESSABLE_ENTITY);
        this.ruleViolations = new ArrayList<>();
    }

    /**
     * Constructs a new BusinessRuleException with the specified message and cause.
     *
     * @param message the detail message
     * @param cause   the cause of this exception
     */
    public BusinessRuleException(String message, Throwable cause) {
        super(message, cause, HttpStatus.UNPROCESSABLE_ENTITY);
        this.ruleViolations = new ArrayList<>();
    }

    /**
     * Constructs a new BusinessRuleException with the specified message and a single rule violation.
     *
     * @param message      the detail message
     * @param ruleId       the identifier of the violated business rule
     * @param violationMsg the message describing the rule violation
     */
    public BusinessRuleException(String message, String ruleId, String violationMsg) {
        super(message, HttpStatus.UNPROCESSABLE_ENTITY);
        this.ruleViolations = new ArrayList<>();
        this.ruleViolations.add(new BusinessRuleViolation(ruleId, violationMsg));
    }

    /**
     * Constructs a new BusinessRuleException with the specified message and a single rule violation with a rejected value.
     *
     * @param message      the detail message
     * @param ruleId       the identifier of the violated business rule
     * @param violationMsg the message describing the rule violation
     * @param rejectedValue the value that violated the business rule
     */
    public BusinessRuleException(String message, String ruleId, String violationMsg, Object rejectedValue) {
        super(message, HttpStatus.UNPROCESSABLE_ENTITY);
        this.ruleViolations = new ArrayList<>();
        this.ruleViolations.add(new BusinessRuleViolation(ruleId, violationMsg, rejectedValue));
    }

    /**
     * Constructs a new BusinessRuleException with the specified message and a list of rule violations.
     *
     * @param message        the detail message
     * @param ruleViolations the list of business rule violations
     */
    public BusinessRuleException(String message, List<BusinessRuleViolation> ruleViolations) {
        super(message, HttpStatus.UNPROCESSABLE_ENTITY);
        this.ruleViolations = new ArrayList<>(ruleViolations);
    }

    /**
     * Constructs a new BusinessRuleException with the specified error code, message, and a list of rule violations.
     *
     * @param errorCode      the error code associated with this exception
     * @param message        the detail message
     * @param ruleViolations the list of business rule violations
     */
    public BusinessRuleException(String errorCode, String message, List<BusinessRuleViolation> ruleViolations) {
        super(message, HttpStatus.UNPROCESSABLE_ENTITY, errorCode);
        this.ruleViolations = new ArrayList<>(ruleViolations);
    }

    /**
     * Returns the list of business rule violations associated with this exception.
     *
     * @return an unmodifiable list of business rule violations
     */
    public List<BusinessRuleViolation> getRuleViolations() {
        return Collections.unmodifiableList(ruleViolations);
    }

    /**
     * Adds a business rule violation to the list of violations.
     *
     * @param ruleId       the identifier of the violated business rule
     * @param violationMsg the message describing the rule violation
     * @return this BusinessRuleException instance for method chaining
     */
    public BusinessRuleException addRuleViolation(String ruleId, String violationMsg) {
        this.ruleViolations.add(new BusinessRuleViolation(ruleId, violationMsg));
        return this;
    }

    /**
     * Adds a business rule violation with a rejected value to the list of violations.
     *
     * @param ruleId        the identifier of the violated business rule
     * @param violationMsg  the message describing the rule violation
     * @param rejectedValue the value that violated the business rule
     * @return this BusinessRuleException instance for method chaining
     */
    public BusinessRuleException addRuleViolation(String ruleId, String violationMsg, Object rejectedValue) {
        this.ruleViolations.add(new BusinessRuleViolation(ruleId, violationMsg, rejectedValue));
        return this;
    }

    /**
     * Adds multiple business rule violations to the list of violations.
     *
     * @param violations the list of business rule violations to add
     * @return this BusinessRuleException instance for method chaining
     */
    public BusinessRuleException addRuleViolations(List<BusinessRuleViolation> violations) {
        this.ruleViolations.addAll(violations);
        return this;
    }

    /**
     * Returns whether this exception has any business rule violations.
     *
     * @return true if this exception has business rule violations, false otherwise
     */
    public boolean hasRuleViolations() {
        return !ruleViolations.isEmpty();
    }

    /**
     * Returns the number of business rule violations associated with this exception.
     *
     * @return the number of business rule violations
     */
    public int getRuleViolationCount() {
        return ruleViolations.size();
    }

    /**
     * Nested class for business rule violation details.
     */
    public static class BusinessRuleViolation {
        private final String ruleId;
        private final String message;
        private final Object rejectedValue;

        /**
         * Constructs a new BusinessRuleViolation with the specified rule ID and message.
         *
         * @param ruleId  the identifier of the violated business rule
         * @param message the message describing the rule violation
         */
        public BusinessRuleViolation(String ruleId, String message) {
            this(ruleId, message, null);
        }

        /**
         * Constructs a new BusinessRuleViolation with the specified rule ID, message, and rejected value.
         *
         * @param ruleId        the identifier of the violated business rule
         * @param message       the message describing the rule violation
         * @param rejectedValue the value that violated the business rule
         */
        public BusinessRuleViolation(String ruleId, String message, Object rejectedValue) {
            this.ruleId = ruleId;
            this.message = message;
            this.rejectedValue = rejectedValue;
        }

        /**
         * Returns the identifier of the violated business rule.
         *
         * @return the rule identifier
         */
        public String getRuleId() {
            return ruleId;
        }

        /**
         * Returns the message describing the rule violation.
         *
         * @return the violation message
         */
        public String getMessage() {
            return message;
        }

        /**
         * Returns the value that violated the business rule, if available.
         *
         * @return the rejected value, or null if not available
         */
        public Object getRejectedValue() {
            return rejectedValue;
        }
    }
}