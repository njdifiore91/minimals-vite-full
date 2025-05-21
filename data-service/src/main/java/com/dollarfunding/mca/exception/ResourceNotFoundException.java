package com.dollarfunding.mca.exception;

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
     * Constructs a new ResourceNotFoundException with the specified resource type and identifier.
     *
     * @param resourceType the type of resource that was not found (e.g., "Application", "Document")
     * @param resourceId   the identifier of the resource that was not found
     */
    public ResourceNotFoundException(String resourceType, String resourceId) {
        super(
            String.format("%s with id %s not found", resourceType, resourceId),
            HttpStatus.NOT_FOUND
        );
        this.resourceType = resourceType;
        this.resourceId = resourceId;
    }

    /**
     * Constructs a new ResourceNotFoundException with the specified resource type, identifier, and cause.
     *
     * @param resourceType the type of resource that was not found (e.g., "Application", "Document")
     * @param resourceId   the identifier of the resource that was not found
     * @param cause        the cause of this exception
     */
    public ResourceNotFoundException(String resourceType, String resourceId, Throwable cause) {
        super(
            String.format("%s with id %s not found", resourceType, resourceId),
            cause,
            HttpStatus.NOT_FOUND
        );
        this.resourceType = resourceType;
        this.resourceId = resourceId;
    }

    /**
     * Constructs a new ResourceNotFoundException with a custom message.
     *
     * @param message the detail message
     */
    public ResourceNotFoundException(String message) {
        super(message, HttpStatus.NOT_FOUND);
        this.resourceType = "Resource";
        this.resourceId = "unknown";
    }

    /**
     * Constructs a new ResourceNotFoundException with a custom message and cause.
     *
     * @param message the detail message
     * @param cause   the cause of this exception
     */
    public ResourceNotFoundException(String message, Throwable cause) {
        super(message, cause, HttpStatus.NOT_FOUND);
        this.resourceType = "Resource";
        this.resourceId = "unknown";
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
     * Creates a ResourceNotFoundException for an application that was not found.
     *
     * @param applicationId the identifier of the application
     * @return a new ResourceNotFoundException
     */
    public static ResourceNotFoundException applicationNotFound(String applicationId) {
        return new ResourceNotFoundException("Application", applicationId);
    }

    /**
     * Creates a ResourceNotFoundException for a document that was not found.
     *
     * @param documentId the identifier of the document
     * @return a new ResourceNotFoundException
     */
    public static ResourceNotFoundException documentNotFound(String documentId) {
        return new ResourceNotFoundException("Document", documentId);
    }

    /**
     * Creates a ResourceNotFoundException for merchant details that were not found.
     *
     * @param merchantId the identifier of the merchant
     * @return a new ResourceNotFoundException
     */
    public static ResourceNotFoundException merchantNotFound(String merchantId) {
        return new ResourceNotFoundException("Merchant", merchantId);
    }

    /**
     * Creates a ResourceNotFoundException for a webhook configuration that was not found.
     *
     * @param webhookId the identifier of the webhook configuration
     * @return a new ResourceNotFoundException
     */
    public static ResourceNotFoundException webhookNotFound(String webhookId) {
        return new ResourceNotFoundException("Webhook", webhookId);
    }
}