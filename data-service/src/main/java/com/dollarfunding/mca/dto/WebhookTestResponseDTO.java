package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;

/**
 * DTO class for returning webhook test results to clients.
 * This class provides comprehensive information about webhook test results
 * with appropriate serialization for API responses.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class WebhookTestResponseDTO {

    /**
     * Whether the webhook test was successful.
     */
    @JsonProperty("success")
    private Boolean success;

    /**
     * Timestamp when the webhook was delivered.
     */
    @JsonProperty("delivery_timestamp")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
    private LocalDateTime deliveryTimestamp;

    /**
     * HTTP status code from the webhook delivery.
     */
    @JsonProperty("response_code")
    private Integer responseCode;

    /**
     * Response body from the webhook delivery.
     */
    @JsonProperty("response_body")
    private String responseBody;

    /**
     * Error message if the webhook delivery failed.
     */
    @JsonProperty("error_message")
    private String errorMessage;

    /**
     * Whether the HMAC signature was verified successfully.
     */
    @JsonProperty("signature_verified")
    private Boolean signatureVerified;

    /**
     * The name of the signature header used (e.g., "X-Webhook-Signature").
     */
    @JsonProperty("signature_header")
    private String signatureHeader;

    /**
     * The HMAC signature that was sent with the webhook.
     */
    @JsonProperty("signature_sent")
    private String signatureSent;

    /**
     * The time it took to deliver the webhook in milliseconds.
     */
    @JsonProperty("delivery_time_ms")
    private Long deliveryTimeMs;

    /**
     * The URL where the webhook was delivered.
     */
    @JsonProperty("endpoint_url")
    private String endpointUrl;

    /**
     * The event type that triggered the webhook.
     */
    @JsonProperty("event_type")
    private String eventType;

    /**
     * Default constructor.
     */
    public WebhookTestResponseDTO() {
    }

    /**
     * Constructor with all fields.
     *
     * @param success           Whether the webhook test was successful
     * @param deliveryTimestamp Timestamp when the webhook was delivered
     * @param responseCode      HTTP status code from the webhook delivery
     * @param responseBody      Response body from the webhook delivery
     * @param errorMessage      Error message if the webhook delivery failed
     * @param signatureVerified Whether the HMAC signature was verified successfully
     * @param signatureHeader   The name of the signature header used
     * @param signatureSent     The HMAC signature that was sent with the webhook
     * @param deliveryTimeMs    The time it took to deliver the webhook in milliseconds
     * @param endpointUrl       The URL where the webhook was delivered
     * @param eventType         The event type that triggered the webhook
     */
    public WebhookTestResponseDTO(Boolean success, LocalDateTime deliveryTimestamp, Integer responseCode,
                                 String responseBody, String errorMessage, Boolean signatureVerified,
                                 String signatureHeader, String signatureSent, Long deliveryTimeMs,
                                 String endpointUrl, String eventType) {
        this.success = success;
        this.deliveryTimestamp = deliveryTimestamp;
        this.responseCode = responseCode;
        this.responseBody = responseBody;
        this.errorMessage = errorMessage;
        this.signatureVerified = signatureVerified;
        this.signatureHeader = signatureHeader;
        this.signatureSent = signatureSent;
        this.deliveryTimeMs = deliveryTimeMs;
        this.endpointUrl = endpointUrl;
        this.eventType = eventType;
    }

    /**
     * @return Whether the webhook test was successful
     */
    public Boolean getSuccess() {
        return success;
    }

    /**
     * @param success Whether the webhook test was successful
     */
    public void setSuccess(Boolean success) {
        this.success = success;
    }

    /**
     * @return Timestamp when the webhook was delivered
     */
    public LocalDateTime getDeliveryTimestamp() {
        return deliveryTimestamp;
    }

    /**
     * @param deliveryTimestamp Timestamp when the webhook was delivered
     */
    public void setDeliveryTimestamp(LocalDateTime deliveryTimestamp) {
        this.deliveryTimestamp = deliveryTimestamp;
    }

    /**
     * @return HTTP status code from the webhook delivery
     */
    public Integer getResponseCode() {
        return responseCode;
    }

    /**
     * @param responseCode HTTP status code from the webhook delivery
     */
    public void setResponseCode(Integer responseCode) {
        this.responseCode = responseCode;
    }

    /**
     * @return Response body from the webhook delivery
     */
    public String getResponseBody() {
        return responseBody;
    }

    /**
     * @param responseBody Response body from the webhook delivery
     */
    public void setResponseBody(String responseBody) {
        this.responseBody = responseBody;
    }

    /**
     * @return Error message if the webhook delivery failed
     */
    public String getErrorMessage() {
        return errorMessage;
    }

    /**
     * @param errorMessage Error message if the webhook delivery failed
     */
    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
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
     * @return The HMAC signature that was sent with the webhook
     */
    public String getSignatureSent() {
        return signatureSent;
    }

    /**
     * @param signatureSent The HMAC signature that was sent with the webhook
     */
    public void setSignatureSent(String signatureSent) {
        this.signatureSent = signatureSent;
    }

    /**
     * @return The time it took to deliver the webhook in milliseconds
     */
    public Long getDeliveryTimeMs() {
        return deliveryTimeMs;
    }

    /**
     * @param deliveryTimeMs The time it took to deliver the webhook in milliseconds
     */
    public void setDeliveryTimeMs(Long deliveryTimeMs) {
        this.deliveryTimeMs = deliveryTimeMs;
    }

    /**
     * @return The URL where the webhook was delivered
     */
    public String getEndpointUrl() {
        return endpointUrl;
    }

    /**
     * @param endpointUrl The URL where the webhook was delivered
     */
    public void setEndpointUrl(String endpointUrl) {
        this.endpointUrl = endpointUrl;
    }

    /**
     * @return The event type that triggered the webhook
     */
    public String getEventType() {
        return eventType;
    }

    /**
     * @param eventType The event type that triggered the webhook
     */
    public void setEventType(String eventType) {
        this.eventType = eventType;
    }

    /**
     * Builder class for creating WebhookTestResponseDTO instances.
     */
    public static class Builder {
        private Boolean success;
        private LocalDateTime deliveryTimestamp;
        private Integer responseCode;
        private String responseBody;
        private String errorMessage;
        private Boolean signatureVerified;
        private String signatureHeader;
        private String signatureSent;
        private Long deliveryTimeMs;
        private String endpointUrl;
        private String eventType;

        /**
         * Default constructor.
         */
        public Builder() {
        }

        /**
         * @param success Whether the webhook test was successful
         * @return The builder instance
         */
        public Builder success(Boolean success) {
            this.success = success;
            return this;
        }

        /**
         * @param deliveryTimestamp Timestamp when the webhook was delivered
         * @return The builder instance
         */
        public Builder deliveryTimestamp(LocalDateTime deliveryTimestamp) {
            this.deliveryTimestamp = deliveryTimestamp;
            return this;
        }

        /**
         * @param responseCode HTTP status code from the webhook delivery
         * @return The builder instance
         */
        public Builder responseCode(Integer responseCode) {
            this.responseCode = responseCode;
            return this;
        }

        /**
         * @param responseBody Response body from the webhook delivery
         * @return The builder instance
         */
        public Builder responseBody(String responseBody) {
            this.responseBody = responseBody;
            return this;
        }

        /**
         * @param errorMessage Error message if the webhook delivery failed
         * @return The builder instance
         */
        public Builder errorMessage(String errorMessage) {
            this.errorMessage = errorMessage;
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
         * @param signatureHeader The name of the signature header used
         * @return The builder instance
         */
        public Builder signatureHeader(String signatureHeader) {
            this.signatureHeader = signatureHeader;
            return this;
        }

        /**
         * @param signatureSent The HMAC signature that was sent with the webhook
         * @return The builder instance
         */
        public Builder signatureSent(String signatureSent) {
            this.signatureSent = signatureSent;
            return this;
        }

        /**
         * @param deliveryTimeMs The time it took to deliver the webhook in milliseconds
         * @return The builder instance
         */
        public Builder deliveryTimeMs(Long deliveryTimeMs) {
            this.deliveryTimeMs = deliveryTimeMs;
            return this;
        }

        /**
         * @param endpointUrl The URL where the webhook was delivered
         * @return The builder instance
         */
        public Builder endpointUrl(String endpointUrl) {
            this.endpointUrl = endpointUrl;
            return this;
        }

        /**
         * @param eventType The event type that triggered the webhook
         * @return The builder instance
         */
        public Builder eventType(String eventType) {
            this.eventType = eventType;
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
            dto.signatureVerified = this.signatureVerified;
            dto.signatureHeader = this.signatureHeader;
            dto.signatureSent = this.signatureSent;
            dto.deliveryTimeMs = this.deliveryTimeMs;
            dto.endpointUrl = this.endpointUrl;
            dto.eventType = this.eventType;
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
     * Creates a successful test response.
     *
     * @param endpointUrl       The URL where the webhook was delivered
     * @param responseCode      HTTP status code from the webhook delivery
     * @param responseBody      Response body from the webhook delivery
     * @param deliveryTimeMs    The time it took to deliver the webhook in milliseconds
     * @param signatureVerified Whether the HMAC signature was verified successfully
     * @return A new WebhookTestResponseDTO instance for a successful test
     */
    public static WebhookTestResponseDTO createSuccessResponse(String endpointUrl, Integer responseCode,
                                                             String responseBody, Long deliveryTimeMs,
                                                             Boolean signatureVerified) {
        return new Builder()
                .success(true)
                .deliveryTimestamp(LocalDateTime.now())
                .endpointUrl(endpointUrl)
                .responseCode(responseCode)
                .responseBody(responseBody)
                .deliveryTimeMs(deliveryTimeMs)
                .signatureVerified(signatureVerified)
                .build();
    }

    /**
     * Creates a failed test response.
     *
     * @param endpointUrl  The URL where the webhook was delivered
     * @param errorMessage Error message if the webhook delivery failed
     * @return A new WebhookTestResponseDTO instance for a failed test
     */
    public static WebhookTestResponseDTO createErrorResponse(String endpointUrl, String errorMessage) {
        return new Builder()
                .success(false)
                .deliveryTimestamp(LocalDateTime.now())
                .endpointUrl(endpointUrl)
                .errorMessage(errorMessage)
                .build();
    }

    @Override
    public String toString() {
        return "WebhookTestResponseDTO{" +
                "success=" + success +
                ", deliveryTimestamp=" + deliveryTimestamp +
                ", responseCode=" + responseCode +
                ", responseBody='" + responseBody + '\'' +
                ", errorMessage='" + errorMessage + '\'' +
                ", signatureVerified=" + signatureVerified +
                ", signatureHeader='" + signatureHeader + '\'' +
                ", signatureSent='" + signatureSent + '\'' +
                ", deliveryTimeMs=" + deliveryTimeMs +
                ", endpointUrl='" + endpointUrl + '\'' +
                ", eventType='" + eventType + '\'' +
                '}';
    }
}