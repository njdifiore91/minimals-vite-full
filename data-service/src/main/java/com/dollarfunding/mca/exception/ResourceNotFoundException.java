package com.dollarfunding.mca.exception;

import com.dollarfunding.mca.util.Constants;
import org.springframework.http.HttpStatus;

/**
 * Exception thrown when a requested resource cannot be found in the system.
 * <p>
 * This exception extends BaseException with a default HTTP status code of 404 (Not Found)
 * and provides constructors for specifying the resource type and identifier. It is used
 * throughout the application to indicate missing resources such as applications, documents,
 * or merchant details.
 * </p>
 */
public class ResourceNotFoundException extends BaseException {

    private final String resourceType;
    private final String resourceId;

    /**
     * Constructs a new ResourceNotFoundException with the specified message.
     *
     * @param message the detail message
     */
    public ResourceNotFoundException(String message) {
        super(message, HttpStatus.NOT_FOUND);
        this.resourceType = "unknown";
        this.resourceId = "unknown";
    }

    /**
     * Constructs a new ResourceNotFoundException with the specified message and cause.
     *
     * @param message the detail message
     * @param cause   the cause of this exception
     */
    public ResourceNotFoundException(String message, Throwable cause) {
        super(message, cause, HttpStatus.NOT_FOUND);
        this.resourceType = "unknown";
        this.resourceId = "unknown";
    }

    /**
     * Constructs a new ResourceNotFoundException with the specified resource type and identifier.
     *
     * @param resourceType the type of resource that was not found
     * @param resourceId   the identifier of the resource that was not found
     */
    public ResourceNotFoundException(String resourceType, String resourceId) {
        super(formatMessage(resourceType, resourceId), HttpStatus.NOT_FOUND, determineErrorCode(resourceType));
        this.resourceType = resourceType;
        this.resourceId = resourceId;
    }

    /**
     * Constructs a new ResourceNotFoundException with the specified resource type, identifier, and cause.
     *
     * @param resourceType the type of resource that was not found
     * @param resourceId   the identifier of the resource that was not found
     * @param cause        the cause of this exception
     */
    public ResourceNotFoundException(String resourceType, String resourceId, Throwable cause) {
        super(formatMessage(resourceType, resourceId), cause, HttpStatus.NOT_FOUND, determineErrorCode(resourceType));
        this.resourceType = resourceType;
        this.resourceId = resourceId;
    }

    /**
     * Returns the type of resource that was not found.
     *
     * @return the resource type
     */
    public String getResourceType() {
        return resourceType;
    }

    /**
     * Returns the identifier of the resource that was not found.
     *
     * @return the resource identifier
     */
    public String getResourceId() {
        return resourceId;
    }

    /**
     * Formats a standard error message for resource not found exceptions.
     *
     * @param resourceType the type of resource that was not found
     * @param resourceId   the identifier of the resource that was not found
     * @return a formatted error message
     */
    private static String formatMessage(String resourceType, String resourceId) {
        return String.format("%s with id '%s' not found", resourceType, resourceId);
    }

    /**
     * Determines the appropriate error code based on the resource type.
     *
     * @param resourceType the type of resource that was not found
     * @return the appropriate error code
     */
    private static String determineErrorCode(String resourceType) {
        if (resourceType == null) {
            return Constants.ErrorCode.NOT_FOUND;
        }

        switch (resourceType.toUpperCase()) {
            case "APPLICATION":
                return Constants.ErrorCode.APPLICATION_NOT_FOUND;
            case "DOCUMENT":
                return Constants.ErrorCode.DOCUMENT_NOT_FOUND;
            default:
                return Constants.ErrorCode.NOT_FOUND;
        }
    }

    /**
     * Creates a new ResourceNotFoundException for an application that was not found.
     *
     * @param applicationId the identifier of the application that was not found
     * @return a new ResourceNotFoundException instance
     */
    public static ResourceNotFoundException applicationNotFound(String applicationId) {
        return new ResourceNotFoundException("Application", applicationId);
    }

    /**
     * Creates a new ResourceNotFoundException for a document that was not found.
     *
     * @param documentId the identifier of the document that was not found
     * @return a new ResourceNotFoundException instance
     */
    public static ResourceNotFoundException documentNotFound(String documentId) {
        return new ResourceNotFoundException("Document", documentId);
    }

    /**
     * Creates a new ResourceNotFoundException for merchant details that were not found.
     *
     * @param merchantId the identifier of the merchant details that were not found
     * @return a new ResourceNotFoundException instance
     */
    public static ResourceNotFoundException merchantNotFound(String merchantId) {
        return new ResourceNotFoundException("Merchant", merchantId);
    }

    /**
     * Creates a new ResourceNotFoundException for a webhook configuration that was not found.
     *
     * @param webhookId the identifier of the webhook configuration that was not found
     * @return a new ResourceNotFoundException instance
     */
    public static ResourceNotFoundException webhookNotFound(String webhookId) {
        return new ResourceNotFoundException("Webhook", webhookId);
    }
}