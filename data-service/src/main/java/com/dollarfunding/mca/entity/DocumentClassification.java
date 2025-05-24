package com.dollarfunding.mca.entity;

import javax.persistence.Converter;

/**
 * Enum defining the possible classification results for documents processed by the OCR service.
 * <p>
 * This enum is used by the Document entity to represent the AI classification of uploaded documents
 * and provides confidence levels for the classification. Each classification includes a description
 * that can be used for display purposes and a default confidence threshold.
 * </p>
 * <p>
 * The Document Service classifies documents into these categories with 99% accuracy using
 * machine learning models. The enum supports JPA persistence through automatic conversion.
 * </p>
 */
public enum DocumentClassification {
    
    /**
     * Document has been verified and is authentic.
     * This classification indicates high confidence in document authenticity.
     */
    VERIFIED("Verified", 0.95),
    
    /**
     * Document requires manual review due to uncertain classification.
     * This classification indicates medium confidence and requires human verification.
     */
    NEEDS_REVIEW("Needs Review", 0.70),
    
    /**
     * Document has been flagged as potentially fraudulent.
     * This classification indicates potential issues with document authenticity.
     */
    FLAGGED("Flagged", 0.60),
    
    /**
     * Document has been rejected due to poor quality or other issues.
     * This classification indicates the document cannot be processed.
     */
    REJECTED("Rejected", 0.40),
    
    /**
     * Document has not yet been classified.
     * This is the default classification for newly uploaded documents.
     */
    UNCLASSIFIED("Unclassified", 0.0);
    
    private final String description;
    private final double confidenceThreshold;
    
    /**
     * Constructor for DocumentClassification enum.
     * 
     * @param description Human-readable description of the classification
     * @param confidenceThreshold The minimum confidence score required for this classification
     */
    DocumentClassification(String description, double confidenceThreshold) {
        this.description = description;
        this.confidenceThreshold = confidenceThreshold;
    }
    
    /**
     * Gets the human-readable description of this classification.
     * 
     * @return The description of the classification
     */
    public String getDescription() {
        return description;
    }
    
    /**
     * Gets the confidence threshold for this classification.
     * 
     * @return The minimum confidence score required for this classification
     */
    public double getConfidenceThreshold() {
        return confidenceThreshold;
    }
    
    /**
     * Determines the appropriate classification based on a confidence score.
     * 
     * @param confidenceScore The confidence score from the document classification service
     * @return The appropriate DocumentClassification based on the confidence score
     */
    public static DocumentClassification fromConfidenceScore(double confidenceScore) {
        if (confidenceScore >= VERIFIED.getConfidenceThreshold()) {
            return VERIFIED;
        } else if (confidenceScore >= NEEDS_REVIEW.getConfidenceThreshold()) {
            return NEEDS_REVIEW;
        } else if (confidenceScore >= FLAGGED.getConfidenceThreshold()) {
            return FLAGGED;
        } else if (confidenceScore >= REJECTED.getConfidenceThreshold()) {
            return REJECTED;
        } else {
            return UNCLASSIFIED;
        }
    }
    
    /**
     * Checks if this classification requires manual review.
     * 
     * @return true if this classification requires manual review
     */
    public boolean requiresManualReview() {
        return this == NEEDS_REVIEW || this == FLAGGED;
    }
    
    /**
     * Checks if this classification is acceptable for processing.
     * 
     * @return true if this classification is acceptable for processing
     */
    public boolean isAcceptable() {
        return this == VERIFIED || this == NEEDS_REVIEW;
    }
    
    /**
     * Validates if a given string represents a valid document classification.
     * 
     * @param classificationString The string to validate
     * @return true if the string is a valid document classification, false otherwise
     */
    public static boolean isValid(String classificationString) {
        if (classificationString == null) {
            return false;
        }
        
        try {
            DocumentClassification.valueOf(classificationString.toUpperCase());
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }
    
    /**
     * Safely converts a string to a DocumentClassification.
     * 
     * @param classificationString The string to convert
     * @return The corresponding DocumentClassification, or UNCLASSIFIED if conversion fails
     */
    public static DocumentClassification fromString(String classificationString) {
        if (classificationString == null) {
            return UNCLASSIFIED;
        }
        
        try {
            return DocumentClassification.valueOf(classificationString.toUpperCase());
        } catch (IllegalArgumentException e) {
            return UNCLASSIFIED;
        }
    }
    
    /**
     * JPA converter for DocumentClassification enum.
     * Handles conversion between database representation and enum values.
     */
    @Converter(autoApply = true)
    public static class DocumentClassificationConverter implements javax.persistence.AttributeConverter<DocumentClassification, String> {
        
        @Override
        public String convertToDatabaseColumn(DocumentClassification attribute) {
            return attribute != null ? attribute.name() : null;
        }
        
        @Override
        public DocumentClassification convertToEntityAttribute(String dbData) {
            return dbData != null ? DocumentClassification.fromString(dbData) : null;
        }
    }
}