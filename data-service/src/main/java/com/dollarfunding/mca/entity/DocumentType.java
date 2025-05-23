package com.dollarfunding.mca.entity;

import javax.persistence.Converter;

/**
 * Enum defining the possible document types for MCA application documents.
 * <p>
 * This enum is used by the Document entity to categorize uploaded documents and
 * provides type safety and validation for document type values throughout the application.
 * Each document type includes a description that can be used for display purposes.
 * </p>
 * <p>
 * The enum supports JPA persistence through automatic conversion and provides
 * utility methods for document type identification and validation.
 * </p>
 */
public enum DocumentType {
    
    /**
     * Bank statements showing financial transaction history and account balances.
     * Used for financial assessment and verification of business cash flow.
     */
    BANK_STATEMENT("Bank Statement"),
    
    /**
     * Tax returns filed with tax authorities showing business income and expenses.
     * Used for verification of reported business revenue and tax compliance.
     */
    TAX_RETURN("Tax Return"),
    
    /**
     * Business licenses and permits issued by government authorities.
     * Used to verify business legitimacy and regulatory compliance.
     */
    BUSINESS_LICENSE("Business License"),
    
    /**
     * Invoices for goods or services provided by the merchant.
     * Used to verify business operations and revenue streams.
     */
    INVOICE("Invoice"),
    
    /**
     * Identity verification documents such as driver's licenses, passports, etc.
     * Used to verify the identity of business owners or authorized representatives.
     */
    ID_VERIFICATION("Identity Verification"),
    
    /**
     * Any other document type that doesn't fit into the above categories.
     * Used for supplementary documentation that may support the application.
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
     * Gets the human-readable description of this document type.
     * 
     * @return The description of the document type
     */
    public String getDescription() {
        return description;
    }
    
    /**
     * Attempts to identify a document type based on its content or metadata.
     * This method can be enhanced with more sophisticated document analysis logic.
     * 
     * @param contentType The MIME type of the document
     * @param fileName The name of the document file
     * @return The most likely document type, or MISCELLANEOUS if type cannot be determined
     */
    public static DocumentType identifyFromContent(String contentType, String fileName) {
        if (fileName == null) {
            return MISCELLANEOUS;
        }
        
        String lowerFileName = fileName.toLowerCase();
        
        // Simple pattern matching based on filename
        if (lowerFileName.contains("bank") || lowerFileName.contains("statement")) {
            return BANK_STATEMENT;
        } else if (lowerFileName.contains("tax") || lowerFileName.contains("return") || 
                  lowerFileName.contains("1040") || lowerFileName.contains("schedule")) {
            return TAX_RETURN;
        } else if (lowerFileName.contains("license") || lowerFileName.contains("permit") || 
                  lowerFileName.contains("certificate")) {
            return BUSINESS_LICENSE;
        } else if (lowerFileName.contains("invoice") || lowerFileName.contains("bill") || 
                  lowerFileName.contains("receipt")) {
            return INVOICE;
        } else if (lowerFileName.contains("id") || lowerFileName.contains("passport") || 
                  lowerFileName.contains("license") || lowerFileName.contains("identification")) {
            return ID_VERIFICATION;
        }
        
        return MISCELLANEOUS;
    }
    
    /**
     * Validates if a given string represents a valid document type.
     * 
     * @param typeString The string to validate
     * @return true if the string is a valid document type, false otherwise
     */
    public static boolean isValid(String typeString) {
        if (typeString == null) {
            return false;
        }
        
        try {
            DocumentType.valueOf(typeString.toUpperCase());
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }
    
    /**
     * Safely converts a string to a DocumentType.
     * 
     * @param typeString The string to convert
     * @return The corresponding DocumentType, or MISCELLANEOUS if conversion fails
     */
    public static DocumentType fromString(String typeString) {
        if (typeString == null) {
            return MISCELLANEOUS;
        }
        
        try {
            return DocumentType.valueOf(typeString.toUpperCase());
        } catch (IllegalArgumentException e) {
            return MISCELLANEOUS;
        }
    }
    
    /**
     * JPA converter for DocumentType enum.
     * Handles conversion between database representation and enum values.
     */
    @Converter(autoApply = true)
    public static class DocumentTypeConverter implements javax.persistence.AttributeConverter<DocumentType, String> {
        
        @Override
        public String convertToDatabaseColumn(DocumentType attribute) {
            return attribute != null ? attribute.name() : null;
        }
        
        @Override
        public DocumentType convertToEntityAttribute(String dbData) {
            return dbData != null ? DocumentType.fromString(dbData) : null;
        }
    }
}