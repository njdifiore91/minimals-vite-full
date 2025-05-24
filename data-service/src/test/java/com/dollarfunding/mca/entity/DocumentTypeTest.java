package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Unit tests for the {@link DocumentType} enum.
 * <p>
 * These tests verify the behavior of the DocumentType enum, including:
 * - Enum constants and their descriptions
 * - Methods for document type identification based on content
 * - Validation and conversion methods
 * - JPA persistence through the DocumentTypeConverter
 * </p>
 */
public class DocumentTypeTest {

    @Test
    @DisplayName("Should have the expected number of enum constants")
    public void shouldHaveExpectedNumberOfConstants() {
        assertEquals(6, DocumentType.values().length, "DocumentType should have exactly 6 constants");
    }

    @ParameterizedTest
    @EnumSource(DocumentType.class)
    @DisplayName("Should have non-null description for each enum constant")
    public void shouldHaveNonNullDescription(DocumentType documentType) {
        assertNotNull(documentType.getDescription(), "Description should not be null");
        assertFalse(documentType.getDescription().isEmpty(), "Description should not be empty");
    }

    @Test
    @DisplayName("Should have correct descriptions for each enum constant")
    public void shouldHaveCorrectDescriptions() {
        assertEquals("Bank Statement", DocumentType.BANK_STATEMENT.getDescription());
        assertEquals("Tax Return", DocumentType.TAX_RETURN.getDescription());
        assertEquals("Business License", DocumentType.BUSINESS_LICENSE.getDescription());
        assertEquals("Invoice", DocumentType.INVOICE.getDescription());
        assertEquals("Identity Verification", DocumentType.ID_VERIFICATION.getDescription());
        assertEquals("Miscellaneous", DocumentType.MISCELLANEOUS.getDescription());
    }

    @Test
    @DisplayName("identifyFromContent() should correctly identify document types from filenames")
    public void identifyFromContent_ShouldIdentifyDocumentTypesFromFilenames() {
        // Bank statements
        assertEquals(DocumentType.BANK_STATEMENT, 
                DocumentType.identifyFromContent("application/pdf", "bank_statement_march.pdf"));
        assertEquals(DocumentType.BANK_STATEMENT, 
                DocumentType.identifyFromContent("application/pdf", "Chase_Statement_2023.pdf"));
        
        // Tax returns
        assertEquals(DocumentType.TAX_RETURN, 
                DocumentType.identifyFromContent("application/pdf", "2022_tax_return.pdf"));
        assertEquals(DocumentType.TAX_RETURN, 
                DocumentType.identifyFromContent("application/pdf", "Form_1040_Schedule_C.pdf"));
        
        // Business licenses
        assertEquals(DocumentType.BUSINESS_LICENSE, 
                DocumentType.identifyFromContent("application/pdf", "business_license_2023.pdf"));
        assertEquals(DocumentType.BUSINESS_LICENSE, 
                DocumentType.identifyFromContent("application/pdf", "NYC_Business_Permit.pdf"));
        
        // Invoices
        assertEquals(DocumentType.INVOICE, 
                DocumentType.identifyFromContent("application/pdf", "invoice_123456.pdf"));
        assertEquals(DocumentType.INVOICE, 
                DocumentType.identifyFromContent("application/pdf", "customer_receipt_may.pdf"));
        
        // ID verification
        assertEquals(DocumentType.ID_VERIFICATION, 
                DocumentType.identifyFromContent("image/jpeg", "passport_scan.jpg"));
        assertEquals(DocumentType.ID_VERIFICATION, 
                DocumentType.identifyFromContent("image/jpeg", "drivers_license_front.jpg"));
        
        // Miscellaneous (default)
        assertEquals(DocumentType.MISCELLANEOUS, 
                DocumentType.identifyFromContent("application/pdf", "document.pdf"));
    }

    @Test
    @DisplayName("identifyFromContent() should return MISCELLANEOUS for null filename")
    public void identifyFromContent_ShouldReturnMiscellaneousForNullFilename() {
        assertEquals(DocumentType.MISCELLANEOUS, 
                DocumentType.identifyFromContent("application/pdf", null));
    }

    @ParameterizedTest
    @EnumSource(DocumentType.class)
    @DisplayName("isValid() should return true for valid document type names")
    public void isValid_ShouldReturnTrueForValidNames(DocumentType documentType) {
        String name = documentType.name();
        assertTrue(DocumentType.isValid(name), "isValid() should return true for valid document type name");
        
        // Test case-insensitivity
        String upperCaseName = name.toUpperCase();
        assertTrue(DocumentType.isValid(upperCaseName), "isValid() should handle uppercase names");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"INVALID_DOCUMENT_TYPE", "unknown", "bank statement"})
    @DisplayName("isValid() should return false for invalid document type names")
    public void isValid_ShouldReturnFalseForInvalidNames(String invalidName) {
        assertFalse(DocumentType.isValid(invalidName), "isValid() should return false for invalid document type name");
    }

    @ParameterizedTest
    @EnumSource(DocumentType.class)
    @DisplayName("fromString() should convert valid string to DocumentType")
    public void fromString_ShouldConvertValidString(DocumentType documentType) {
        String name = documentType.name();
        assertEquals(documentType, DocumentType.fromString(name), 
                "fromString() should return the correct enum constant");
        
        // Test case-insensitivity
        String lowerCaseName = name.toLowerCase();
        assertEquals(documentType, DocumentType.fromString(lowerCaseName), 
                "fromString() should be case-insensitive");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"INVALID_DOCUMENT_TYPE", "unknown", "bank statement"})
    @DisplayName("fromString() should return MISCELLANEOUS for invalid strings")
    public void fromString_ShouldReturnMiscellaneousForInvalidStrings(String invalidName) {
        assertEquals(DocumentType.MISCELLANEOUS, DocumentType.fromString(invalidName), 
                "fromString() should return MISCELLANEOUS for invalid document type name");
    }

    @Test
    @DisplayName("DocumentTypeConverter should convert enum to database column")
    public void documentTypeConverter_ShouldConvertEnumToDatabaseColumn() {
        DocumentType.DocumentTypeConverter converter = new DocumentType.DocumentTypeConverter();
        
        // Test all enum values
        for (DocumentType documentType : DocumentType.values()) {
            String dbValue = converter.convertToDatabaseColumn(documentType);
            assertEquals(documentType.name(), dbValue, 
                    "Converter should store enum name in database column");
        }
        
        // Test null handling
        assertNull(converter.convertToDatabaseColumn(null), 
                "Converter should handle null enum value");
    }

    @Test
    @DisplayName("DocumentTypeConverter should convert database column to enum")
    public void documentTypeConverter_ShouldConvertDatabaseColumnToEnum() {
        DocumentType.DocumentTypeConverter converter = new DocumentType.DocumentTypeConverter();
        
        // Test all enum values
        for (DocumentType documentType : DocumentType.values()) {
            DocumentType result = converter.convertToEntityAttribute(documentType.name());
            assertEquals(documentType, result, 
                    "Converter should restore correct enum from database column");
        }
        
        // Test case-insensitivity
        assertEquals(DocumentType.BANK_STATEMENT, 
                converter.convertToEntityAttribute("bank_statement"), 
                "Converter should handle case variations");
        
        // Test invalid value (should return MISCELLANEOUS)
        assertEquals(DocumentType.MISCELLANEOUS, 
                converter.convertToEntityAttribute("INVALID_TYPE"), 
                "Converter should return MISCELLANEOUS for invalid database value");
        
        // Test null handling
        assertNull(converter.convertToEntityAttribute(null), 
                "Converter should handle null database value");
    }

    @Test
    @DisplayName("All enum constants should be unique")
    public void allEnumConstantsShouldBeUnique() {
        DocumentType[] values = DocumentType.values();
        assertEquals(values.length, Arrays.stream(values)
                .map(DocumentType::name)
                .distinct()
                .count(), 
                "All enum constants should have unique names");
    }

    @Test
    @DisplayName("All enum descriptions should be unique")
    public void allEnumDescriptionsShouldBeUnique() {
        DocumentType[] values = DocumentType.values();
        assertEquals(values.length, Arrays.stream(values)
                .map(DocumentType::getDescription)
                .distinct()
                .count(), 
                "All enum constants should have unique descriptions");
    }
}