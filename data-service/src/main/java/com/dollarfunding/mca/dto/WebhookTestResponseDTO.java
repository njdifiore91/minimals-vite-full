package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;

/**
 * DTO class for returning webhook test results to clients.
 * This class provides comprehensive information about webhook test results
 * including delivery status, response details, and error information.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class WebhookTestResponseDTO {

    /**
     * Indicates whether the webhook test was successful.
     */
    @JsonProperty("success")
    private boolean success;

    /**
     * Timestamp when the webhook was delivered.
     */
    @JsonProperty("delivery_timestamp")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime deliveryTimestamp;

    /**
     * HTTP response code received from the webhook endpoint.
     */
    @JsonProperty("response_code")
    private Integer responseCode;

    /**
     * Response body received from the webhook endpoint.
     */
    @JsonProperty("response_body")
    private String responseBody;

    /**
     * Error message if the webhook delivery failed.
     */
    @JsonProperty("error_message")
    private String errorMessage;

    /**
     * Detailed error information if available.
     */
    @JsonProperty("error_details")
    private String errorDetails;

    /**
     * Time taken to deliver the webhook in milliseconds.
     */
    @JsonProperty("delivery_time_ms")
    private Long deliveryTimeMs;

    /**
     * Indicates whether the HMAC signature was verified successfully.
     */
    @JsonProperty("signature_verified")
    private Boolean signatureVerified;

    /**
     * The HMAC signature that was generated for the test.
     */
    @JsonProperty("generated_signature")
    private String generatedSignature;

    /**
     * The name of the signature header used (e.g., "X-Webhook-Signature").
     */
    @JsonProperty("signature_header")
    private String signatureHeader;

    /**
     * Default constructor.
     */
    public WebhookTestResponseDTO() {
    }

    /**
     * Constructor for successful webhook test.
     *
     * @param deliveryTimestamp The timestamp when the webhook was delivered
     * @param responseCode      The HTTP response code received
     * @param responseBody      The response body received
     * @param deliveryTimeMs    The time taken to deliver the webhook in milliseconds
     * @param signatureVerified Whether the signature was verified successfully
     * @param generatedSignature The HMAC signature that was generated
     * @param signatureHeader   The name of the signature header used
     */
    public WebhookTestResponseDTO(LocalDateTime deliveryTimestamp, Integer responseCode, String responseBody,
                                 Long deliveryTimeMs, Boolean signatureVerified, String generatedSignature,
                                 String signatureHeader) {
        this.success = true;
        this.deliveryTimestamp = deliveryTimestamp;
        this.responseCode = responseCode;
        this.responseBody = responseBody;
        this.deliveryTimeMs = deliveryTimeMs;
        this.signatureVerified = signatureVerified;
        this.generatedSignature = generatedSignature;
        this.signatureHeader = signatureHeader;
    }

    /**
     * Constructor for failed webhook test.
     *
     * @param errorMessage The error message
     * @param errorDetails Detailed error information
     * @param signatureVerified Whether the signature was verified successfully
     * @param generatedSignature The HMAC signature that was generated
     * @param signatureHeader   The name of the signature header used
     */
    public WebhookTestResponseDTO(String errorMessage, String errorDetails, Boolean signatureVerified,
                                 String generatedSignature, String signatureHeader) {
        this.success = false;
        this.deliveryTimestamp = LocalDateTime.now();
        this.errorMessage = errorMessage;
        this.errorDetails = errorDetails;
        this.signatureVerified = signatureVerified;
        this.generatedSignature = generatedSignature;
        this.signatureHeader = signatureHeader;
    }

    /**
     * @return Whether the webhook test was successful
     */
    public boolean isSuccess() {
        return success;
    }

    /**
     * @param success Whether the webhook test was successful
     */
    public void setSuccess(boolean success) {
        this.success = success;
    }

    /**
     * @return The timestamp when the webhook was delivered
     */
    public LocalDateTime getDeliveryTimestamp() {
        return deliveryTimestamp;
    }

    /**
     * @param deliveryTimestamp The timestamp when the webhook was delivered
     */
    public void setDeliveryTimestamp(LocalDateTime deliveryTimestamp) {
        this.deliveryTimestamp = deliveryTimestamp;
    }

    /**
     * @return The HTTP response code received
     */
    public Integer getResponseCode() {
        return responseCode;
    }

    /**
     * @param responseCode The HTTP response code received
     */
    public void setResponseCode(Integer responseCode) {
        this.responseCode = responseCode;
    }

    /**
     * @return The response body received
     */
    public String getResponseBody() {
        return responseBody;
    }

    /**
     * @param responseBody The response body received
     */
    public void setResponseBody(String responseBody) {
        this.responseBody = responseBody;
    }

    /**
     * @return The error message if the webhook delivery failed
     */
    public String getErrorMessage() {
        return errorMessage;
    }

    /**
     * @param errorMessage The error message if the webhook delivery failed
     */
    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }

    /**
     * @return Detailed error information if available
     */
    public String getErrorDetails() {
        return errorDetails;
    }

    /**
     * @param errorDetails Detailed error information if available
     */
    public void setErrorDetails(String errorDetails) {
        this.errorDetails = errorDetails;
    }

    /**
     * @return The time taken to deliver the webhook in milliseconds
     */
    public Long getDeliveryTimeMs() {
        return deliveryTimeMs;
    }

    /**
     * @param deliveryTimeMs The time taken to deliver the webhook in milliseconds
     */
    public void setDeliveryTimeMs(Long deliveryTimeMs) {
        this.deliveryTimeMs = deliveryTimeMs;
    }

    /**
     * @return Whether the HMAC signature was verified successfully
     */
    public Boolean getSignatureVerified() {
        return signatureVerified;
    }

    /**
     * @param signatureVerified Whether the HMAC signature was verified successfully
     */
    public void setSignatureVerified(Boolean signatureVerified) {
        this.signatureVerified = signatureVerified;
    }

    /**
     * @return The HMAC signature that was generated for the test
     */
    public String getGeneratedSignature() {
        return generatedSignature;
    }

    /**
     * @param generatedSignature The HMAC signature that was generated for the test
     */
    public void setGeneratedSignature(String generatedSignature) {
        this.generatedSignature = generatedSignature;
    }

    /**
     * @return The name of the signature header used
     */
    public String getSignatureHeader() {
        return signatureHeader;
    }

    /**
     * @param signatureHeader The name of the signature header used
     */
    public void setSignatureHeader(String signatureHeader) {
        this.signatureHeader = signatureHeader;
    }

    /**
     * Builder class for creating WebhookTestResponseDTO instances.
     */
    public static class Builder {
        private boolean success;
        private LocalDateTime deliveryTimestamp;
        private Integer responseCode;
        private String responseBody;
        private String errorMessage;
        private String errorDetails;
        private Long deliveryTimeMs;
        private Boolean signatureVerified;
        private String generatedSignature;
        private String signatureHeader;

        /**
         * Default constructor.
         */
        public Builder() {
            this.deliveryTimestamp = LocalDateTime.now();
        }

        /**
         * @param success Whether the webhook test was successful
         * @return The builder instance
         */
        public Builder success(boolean success) {
            this.success = success;
            return this;
        }

        /**
         * @param deliveryTimestamp The timestamp when the webhook was delivered
         * @return The builder instance
         */
        public Builder deliveryTimestamp(LocalDateTime deliveryTimestamp) {
            this.deliveryTimestamp = deliveryTimestamp;
            return this;
        }

        /**
         * @param responseCode The HTTP response code received
         * @return The builder instance
         */
        public Builder responseCode(Integer responseCode) {
            this.responseCode = responseCode;
            return this;
        }

        /**
         * @param responseBody The response body received
         * @return The builder instance
         */
        public Builder responseBody(String responseBody) {
            this.responseBody = responseBody;
            return this;
        }

        /**
         * @param errorMessage The error message if the webhook delivery failed
         * @return The builder instance
         */
        public Builder errorMessage(String errorMessage) {
            this.errorMessage = errorMessage;
            return this;
        }

        /**
         * @param errorDetails Detailed error information if available
         * @return The builder instance
         */
        public Builder errorDetails(String errorDetails) {
            this.errorDetails = errorDetails;
            return this;
        }

        /**
         * @param deliveryTimeMs The time taken to deliver the webhook in milliseconds
         * @return The builder instance
         */
        public Builder deliveryTimeMs(Long deliveryTimeMs) {
            this.deliveryTimeMs = deliveryTimeMs;
            return this;
        }

        /**
         * @param signatureVerified Whether the HMAC signature was verified successfully
         * @return The builder instance
         */
        public Builder signatureVerified(Boolean signatureVerified) {
            this.signatureVerified = signatureVerified;
            return this;
        }

        /**
         * @param generatedSignature The HMAC signature that was generated for the test
         * @return The builder instance
         */
        public Builder generatedSignature(String generatedSignature) {
            this.generatedSignature = generatedSignature;
            return this;
        }

        /**
         * @param signatureHeader The name of the signature header used
         * @return The builder instance
         */
        public Builder signatureHeader(String signatureHeader) {
            this.signatureHeader = signatureHeader;
            return this;
        }

        /**
         * Builds a new WebhookTestResponseDTO instance.
         *
         * @return A new WebhookTestResponseDTO instance
         */
        public WebhookTestResponseDTO build() {
            WebhookTestResponseDTO dto = new WebhookTestResponseDTO();
            dto.success = this.success;
            dto.deliveryTimestamp = this.deliveryTimestamp;
            dto.responseCode = this.responseCode;
            dto.responseBody = this.responseBody;
            dto.errorMessage = this.errorMessage;
            dto.errorDetails = this.errorDetails;
            dto.deliveryTimeMs = this.deliveryTimeMs;
            dto.signatureVerified = this.signatureVerified;
            dto.generatedSignature = this.generatedSignature;
            dto.signatureHeader = this.signatureHeader;
            return dto;
        }
    }

    /**
     * Creates a new builder instance.
     *
     * @return A new builder instance
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Creates a successful response with the given parameters.
     *
     * @param responseCode The HTTP response code received
     * @param responseBody The response body received
     * @param deliveryTimeMs The time taken to deliver the webhook in milliseconds
     * @param signatureVerified Whether the signature was verified successfully
     * @param generatedSignature The HMAC signature that was generated
     * @param signatureHeader The name of the signature header used
     * @return A new WebhookTestResponseDTO instance for a successful test
     */
    public static WebhookTestResponseDTO success(Integer responseCode, String responseBody, Long deliveryTimeMs,
                                               Boolean signatureVerified, String generatedSignature,
                                               String signatureHeader) {
        return builder()
                .success(true)
                .responseCode(responseCode)
                .responseBody(responseBody)
                .deliveryTimeMs(deliveryTimeMs)
                .signatureVerified(signatureVerified)
                .generatedSignature(generatedSignature)
                .signatureHeader(signatureHeader)
                .build();
    }

    /**
     * Creates a failed response with the given parameters.
     *
     * @param errorMessage The error message
     * @param errorDetails Detailed error information
     * @param signatureVerified Whether the signature was verified successfully
     * @param generatedSignature The HMAC signature that was generated
     * @param signatureHeader The name of the signature header used
     * @return A new WebhookTestResponseDTO instance for a failed test
     */
    public static WebhookTestResponseDTO failure(String errorMessage, String errorDetails, Boolean signatureVerified,
                                               String generatedSignature, String signatureHeader) {
        return builder()
                .success(false)
                .errorMessage(errorMessage)
                .errorDetails(errorDetails)
                .signatureVerified(signatureVerified)
                .generatedSignature(generatedSignature)
                .signatureHeader(signatureHeader)
                .build();
    }
}