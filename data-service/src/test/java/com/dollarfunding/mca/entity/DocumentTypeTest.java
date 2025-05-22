package com.dollarfunding.mca.entity;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Arrays;
import java.util.Optional;

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
 * - Methods for finding document types by name or description
 * - Document categorization methods (financial, PII)
 * - OCR confidence threshold determination
 * - Conversion methods for serialization and deserialization
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

    @ParameterizedTest
    @EnumSource(DocumentType.class)
    @DisplayName("findByName() should find enum constant by name")
    public void findByName_ShouldFindEnumConstantByName(DocumentType documentType) {
        String name = documentType.name();
        Optional<DocumentType> result = DocumentType.findByName(name);
        
        assertTrue(result.isPresent(), "findByName() should find the enum constant");
        assertEquals(documentType, result.get(), "findByName() should return the correct enum constant");
    }

    @ParameterizedTest
    @EnumSource(DocumentType.class)
    @DisplayName("findByName() should find enum constant by name (case-insensitive)")
    public void findByName_ShouldBeCaseInsensitive(DocumentType documentType) {
        String lowerCaseName = documentType.name().toLowerCase();
        Optional<DocumentType> result = DocumentType.findByName(lowerCaseName);
        
        assertTrue(result.isPresent(), "findByName() should find the enum constant (case-insensitive)");
        assertEquals(documentType, result.get(), "findByName() should return the correct enum constant");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"INVALID_DOCUMENT_TYPE", "unknown"})
    @DisplayName("findByName() should return empty Optional for invalid name")
    public void findByName_ShouldReturnEmptyOptionalForInvalidName(String invalidName) {
        Optional<DocumentType> result = DocumentType.findByName(invalidName);
        assertFalse(result.isPresent(), "findByName() should return an empty Optional for invalid name");
    }

    @ParameterizedTest
    @EnumSource(DocumentType.class)
    @DisplayName("findByDescription() should find enum constant by description")
    public void findByDescription_ShouldFindEnumConstantByDescription(DocumentType documentType) {
        String description = documentType.getDescription();
        Optional<DocumentType> result = DocumentType.findByDescription(description);
        
        assertTrue(result.isPresent(), "findByDescription() should find the enum constant");
        assertEquals(documentType, result.get(), "findByDescription() should return the correct enum constant");
    }

    @ParameterizedTest
    @EnumSource(DocumentType.class)
    @DisplayName("findByDescription() should find enum constant by description (case-insensitive)")
    public void findByDescription_ShouldBeCaseInsensitive(DocumentType documentType) {
        String lowerCaseDescription = documentType.getDescription().toLowerCase();
        Optional<DocumentType> result = DocumentType.findByDescription(lowerCaseDescription);
        
        assertTrue(result.isPresent(), "findByDescription() should find the enum constant (case-insensitive)");
        assertEquals(documentType, result.get(), "findByDescription() should return the correct enum constant");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"Invalid Document Type", "Unknown Document"})
    @DisplayName("findByDescription() should return empty Optional for invalid description")
    public void findByDescription_ShouldReturnEmptyOptionalForInvalidDescription(String invalidDescription) {
        Optional<DocumentType> result = DocumentType.findByDescription(invalidDescription);
        assertFalse(result.isPresent(), "findByDescription() should return an empty Optional for invalid description");
    }

    @Test
    @DisplayName("isFinancialDocument() should correctly identify financial documents")
    public void isFinancialDocument_ShouldIdentifyFinancialDocuments() {
        assertTrue(DocumentType.BANK_STATEMENT.isFinancialDocument(), "BANK_STATEMENT should be a financial document");
        assertTrue(DocumentType.TAX_RETURN.isFinancialDocument(), "TAX_RETURN should be a financial document");
        assertTrue(DocumentType.INVOICE.isFinancialDocument(), "INVOICE should be a financial document");
        
        assertFalse(DocumentType.BUSINESS_LICENSE.isFinancialDocument(), "BUSINESS_LICENSE should not be a financial document");
        assertFalse(DocumentType.ID_VERIFICATION.isFinancialDocument(), "ID_VERIFICATION should not be a financial document");
        assertFalse(DocumentType.MISCELLANEOUS.isFinancialDocument(), "MISCELLANEOUS should not be a financial document");
    }

    @Test
    @DisplayName("containsPII() should correctly identify documents with PII")
    public void containsPII_ShouldIdentifyDocumentsWithPII() {
        assertTrue(DocumentType.ID_VERIFICATION.containsPII(), "ID_VERIFICATION should contain PII");
        assertTrue(DocumentType.TAX_RETURN.containsPII(), "TAX_RETURN should contain PII");
        
        assertFalse(DocumentType.BANK_STATEMENT.containsPII(), "BANK_STATEMENT should not contain PII");
        assertFalse(DocumentType.BUSINESS_LICENSE.containsPII(), "BUSINESS_LICENSE should not contain PII");
        assertFalse(DocumentType.INVOICE.containsPII(), "INVOICE should not contain PII");
        assertFalse(DocumentType.MISCELLANEOUS.containsPII(), "MISCELLANEOUS should not contain PII");
    }

    @Test
    @DisplayName("getOcrConfidenceThreshold() should return correct threshold for each document type")
    public void getOcrConfidenceThreshold_ShouldReturnCorrectThreshold() {
        assertEquals(0.85, DocumentType.BANK_STATEMENT.getOcrConfidenceThreshold(), 0.001, 
                "BANK_STATEMENT should have 0.85 OCR confidence threshold");
        assertEquals(0.80, DocumentType.TAX_RETURN.getOcrConfidenceThreshold(), 0.001, 
                "TAX_RETURN should have 0.80 OCR confidence threshold");
        assertEquals(0.75, DocumentType.INVOICE.getOcrConfidenceThreshold(), 0.001, 
                "INVOICE should have 0.75 OCR confidence threshold");
        assertEquals(0.70, DocumentType.BUSINESS_LICENSE.getOcrConfidenceThreshold(), 0.001, 
                "BUSINESS_LICENSE should have 0.70 OCR confidence threshold");
        assertEquals(0.90, DocumentType.ID_VERIFICATION.getOcrConfidenceThreshold(), 0.001, 
                "ID_VERIFICATION should have 0.90 OCR confidence threshold");
        assertEquals(0.65, DocumentType.MISCELLANEOUS.getOcrConfidenceThreshold(), 0.001, 
                "MISCELLANEOUS should have 0.65 OCR confidence threshold");
    }

    @ParameterizedTest
    @EnumSource(DocumentType.class)
    @DisplayName("fromString() should correctly convert string to enum constant")
    public void fromString_ShouldConvertStringToEnumConstant(DocumentType documentType) {
        // Test with enum name
        String name = documentType.name();
        DocumentType defaultType = DocumentType.MISCELLANEOUS;
        DocumentType result = DocumentType.fromString(name, defaultType);
        assertEquals(documentType, result, "fromString() should convert enum name to correct enum constant");
        
        // Test with description
        String description = documentType.getDescription();
        result = DocumentType.fromString(description, defaultType);
        assertEquals(documentType, result, "fromString() should convert description to correct enum constant");
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"INVALID_DOCUMENT_TYPE", "Unknown Document"})
    @DisplayName("fromString() should return default type for invalid string")
    public void fromString_ShouldReturnDefaultTypeForInvalidString(String invalidString) {
        DocumentType defaultType = DocumentType.MISCELLANEOUS;
        DocumentType result = DocumentType.fromString(invalidString, defaultType);
        assertEquals(defaultType, result, "fromString() should return the default type for invalid string");
    }

    @ParameterizedTest
    @EnumSource(DocumentType.class)
    @DisplayName("toString() should return the enum name")
    public void toString_ShouldReturnEnumName(DocumentType documentType) {
        assertEquals(documentType.name(), documentType.toString(), 
                "toString() should return the enum name");
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