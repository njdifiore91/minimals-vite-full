package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonInclude;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;
import java.util.Map;

/**
 * Data Transfer Object for webhook test requests.
 * Used to validate and process webhook test requests in the REST API.
 * This DTO is used in the endpoint /api/v1/webhooks/{id}/test which is restricted to System Admin role.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class WebhookTestRequestDTO {

    /**
     * The ID of the webhook to test.
     * This field is required and must match the ID in the URL path.
     */
    @NotBlank(message = "Webhook ID is required")
    @Size(max = 36, message = "Webhook ID cannot exceed 36 characters")
    @JsonProperty("webhookId")
    private String webhookId;

    /**
     * Custom payload to send in the test webhook.
     * This can be any valid JSON structure.
     */
    @NotNull(message = "Test payload is required")
    @JsonProperty("testPayload")
    private Map<String, Object> testPayload;

    /**
     * Flag to determine if the webhook should be delivered asynchronously.
     * Default is false (synchronous delivery).
     */
    @JsonProperty("async")
    private Boolean async = false;

    /**
     * Flag to determine if the webhook delivery should be retried on failure.
     * Default is true.
     */
    @JsonProperty("retry")
    private Boolean retry = true;

    /**
     * Flag to determine if HMAC signature should be included in the test.
     * Default is true.
     */
    @JsonProperty("includeSignature")
    private Boolean includeSignature = true;

    /**
     * Default constructor for deserialization.
     */
    public WebhookTestRequestDTO() {
    }

    /**
     * Constructor with all fields.
     *
     * @param webhookId        ID of the webhook to test
     * @param testPayload      Custom payload to send
     * @param async            Whether to deliver asynchronously
     * @param retry            Whether to retry on failure
     * @param includeSignature Whether to include HMAC signature
     */
    public WebhookTestRequestDTO(String webhookId, Map<String, Object> testPayload, Boolean async, Boolean retry, Boolean includeSignature) {
        this.webhookId = webhookId;
        this.testPayload = testPayload;
        this.async = async;
        this.retry = retry;
        this.includeSignature = includeSignature;
    }

    /**
     * Get the webhook ID.
     *
     * @return The webhook ID
     */
    public String getWebhookId() {
        return webhookId;
    }

    /**
     * Set the webhook ID.
     *
     * @param webhookId The webhook ID to set
     */
    public void setWebhookId(String webhookId) {
        this.webhookId = webhookId;
    }

    /**
     * Get the test payload.
     *
     * @return The test payload as a Map
     */
    public Map<String, Object> getTestPayload() {
        return testPayload;
    }

    /**
     * Set the test payload.
     *
     * @param testPayload The test payload to set
     */
    public void setTestPayload(Map<String, Object> testPayload) {
        this.testPayload = testPayload;
    }

    /**
     * Check if the webhook should be delivered asynchronously.
     *
     * @return True if async delivery is enabled, false otherwise
     */
    public Boolean getAsync() {
        return async;
    }

    /**
     * Set whether the webhook should be delivered asynchronously.
     *
     * @param async True for async delivery, false for synchronous
     */
    public void setAsync(Boolean async) {
        this.async = async;
    }

    /**
     * Check if the webhook delivery should be retried on failure.
     *
     * @return True if retry is enabled, false otherwise
     */
    public Boolean getRetry() {
        return retry;
    }

    /**
     * Set whether the webhook delivery should be retried on failure.
     *
     * @param retry True to enable retry, false to disable
     */
    public void setRetry(Boolean retry) {
        this.retry = retry;
    }

    /**
     * Check if HMAC signature should be included in the test.
     *
     * @return True if signature should be included, false otherwise
     */
    public Boolean getIncludeSignature() {
        return includeSignature;
    }

    /**
     * Set whether HMAC signature should be included in the test.
     *
     * @param includeSignature True to include signature, false to exclude
     */
    public void setIncludeSignature(Boolean includeSignature) {
        this.includeSignature = includeSignature;
    }

    @Override
    public String toString() {
        return "WebhookTestRequestDTO{" +
                "webhookId='" + webhookId + '\'' +
                ", testPayload=" + testPayload +
                ", async=" + async +
                ", retry=" + retry +
                ", includeSignature=" + includeSignature +
                '}';
    }
}