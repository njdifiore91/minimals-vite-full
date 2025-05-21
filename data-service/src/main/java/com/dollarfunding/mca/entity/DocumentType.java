package com.dollarfunding.mca.entity;

import java.util.Arrays;
import java.util.Optional;

/**
 * Enumeration of document types for MCA application documents.
 * 
 * This enum defines the possible document types that can be processed by the
 * Merchant Cash Advance (MCA) Application Processing System. Each document type
 * has a description and is used to categorize uploaded documents for appropriate
 * processing and data extraction.
 */
public enum DocumentType {
    
    /**
     * Bank statements showing account activity and balances.
     * Used for financial assessment and verification of cash flow.
     */
    BANK_STATEMENT("Bank Statement"),
    
    /**
     * Tax return documents such as 1040, Schedule C, or business tax returns.
     * Used for income verification and business performance assessment.
     */
    TAX_RETURN("Tax Return"),
    
    /**
     * Business license or permit documentation.
     * Used to verify business legitimacy and operational status.
     */
    BUSINESS_LICENSE("Business License"),
    
    /**
     * Business invoices showing sales activity.
     * Used to verify revenue claims and business operations.
     */
    INVOICE("Invoice"),
    
    /**
     * Identity verification documents such as driver's license, passport, or state ID.
     * Used to verify the identity of business owners or authorized representatives.
     */
    ID_VERIFICATION("Identity Verification"),
    
    /**
     * Miscellaneous documents that don't fit into other categories.
     * May include additional supporting documentation for the application.
     */
    MISCELLANEOUS("Miscellaneous");
    
    private final String description;
    
    /**
     * Constructor for DocumentType enum.
     * 
     * @param description Human-readable description of the document type
     */
    DocumentType(String description) {
        this.description = description;
    }
    
    /**
     * Get the human-readable description of the document type.
     * 
     * @return The description of the document type
     */
    public String getDescription() {
        return description;
    }
    
    /**
     * Find a DocumentType by its name (case-insensitive).
     * 
     * @param name The name of the document type to find
     * @return An Optional containing the matching DocumentType, or empty if not found
     */
    public static Optional<DocumentType> findByName(String name) {
        if (name == null || name.isEmpty()) {
            return Optional.empty();
        }
        
        return Arrays.stream(DocumentType.values())
                .filter(type -> type.name().equalsIgnoreCase(name))
                .findFirst();
    }
    
    /**
     * Find a DocumentType by its description (case-insensitive).
     * 
     * @param description The description of the document type to find
     * @return An Optional containing the matching DocumentType, or empty if not found
     */
    public static Optional<DocumentType> findByDescription(String description) {
        if (description == null || description.isEmpty()) {
            return Optional.empty();
        }
        
        return Arrays.stream(DocumentType.values())
                .filter(type -> type.getDescription().equalsIgnoreCase(description))
                .findFirst();
    }
    
    /**
     * Determine if a document type is financial in nature.
     * Financial documents require special handling for data extraction.
     * 
     * @return true if the document type is financial, false otherwise
     */
    public boolean isFinancialDocument() {
        return this == BANK_STATEMENT || this == TAX_RETURN || this == INVOICE;
    }
    
    /**
     * Determine if a document type contains personally identifiable information (PII).
     * Documents with PII require special security handling and encryption.
     * 
     * @return true if the document type contains PII, false otherwise
     */
    public boolean containsPII() {
        return this == ID_VERIFICATION || this == TAX_RETURN;
    }
    
    /**
     * Get the expected OCR confidence threshold for this document type.
     * Different document types have different expected OCR accuracy levels.
     * 
     * @return The minimum confidence threshold (0.0-1.0) for OCR extraction
     */
    public double getOcrConfidenceThreshold() {
        switch (this) {
            case BANK_STATEMENT:
                return 0.85; // Structured format, high confidence expected
            case TAX_RETURN:
                return 0.80; // Semi-structured, relatively high confidence
            case INVOICE:
                return 0.75; // Variable format, moderate confidence
            case BUSINESS_LICENSE:
                return 0.70; // Variable format, moderate confidence
            case ID_VERIFICATION:
                return 0.90; // Critical information, very high confidence required
            case MISCELLANEOUS:
            default:
                return 0.65; // Unknown format, lower confidence acceptable
        }
    }
    
    /**
     * Get the document type from a string representation, with a default fallback.
     * 
     * @param typeString The string representation of the document type
     * @param defaultType The default type to return if the string doesn't match any type
     * @return The matching DocumentType or the provided default
     */
    public static DocumentType fromString(String typeString, DocumentType defaultType) {
        if (typeString == null || typeString.isEmpty()) {
            return defaultType;
        }
        
        return findByName(typeString)
                .orElse(findByDescription(typeString)
                        .orElse(defaultType));
    }
    
    /**
     * Convert the enum to a string representation suitable for database storage.
     * 
     * @return The string representation of this document type
     */
    @Override
    public String toString() {
        return name();
    }
}