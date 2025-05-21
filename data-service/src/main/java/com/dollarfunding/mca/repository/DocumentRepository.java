package com.dollarfunding.mca.repository;

import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Spring Data JPA repository interface for Document entities.
 * 
 * This repository provides database access methods for documents associated with MCA applications.
 * It extends JpaRepository to inherit standard CRUD operations and adds custom query methods for
 * finding documents by application ID, type, classification, and upload date.
 * 
 * The actual document content is stored in S3-compatible storage with AES-256 encryption,
 * while this repository manages document metadata in the database.
 */
@Repository
public interface DocumentRepository extends JpaRepository<Document, UUID> {
    
    /**
     * Find all documents associated with a specific application.
     * 
     * @param applicationId The ID of the application
     * @return List of documents associated with the application
     */
    List<Document> findByApplicationId(UUID applicationId);
    
    /**
     * Find all documents associated with a specific application, ordered by upload date.
     * 
     * @param applicationId The ID of the application
     * @return List of documents associated with the application, ordered by upload date
     */
    List<Document> findByApplicationIdOrderByUploadedAtDesc(UUID applicationId);
    
    /**
     * Find a document by its ID and application ID.
     * 
     * @param id The document ID
     * @param applicationId The application ID
     * @return Optional containing the document if found, empty otherwise
     */
    Optional<Document> findByIdAndApplicationId(UUID id, UUID applicationId);
    
    /**
     * Find all documents of a specific type.
     * 
     * @param type The document type
     * @return List of documents of the specified type
     */
    List<Document> findByType(DocumentType type);
    
    /**
     * Find all documents of a specific type associated with an application.
     * 
     * @param applicationId The ID of the application
     * @param type The document type
     * @return List of documents of the specified type associated with the application
     */
    List<Document> findByApplicationIdAndType(UUID applicationId, DocumentType type);
    
    /**
     * Find all documents with a specific classification.
     * 
     * @param classification The document classification
     * @return List of documents with the specified classification
     */
    List<Document> findByClassification(String classification);
    
    /**
     * Find all documents with a specific classification associated with an application.
     * 
     * @param applicationId The ID of the application
     * @param classification The document classification
     * @return List of documents with the specified classification associated with the application
     */
    List<Document> findByApplicationIdAndClassification(UUID applicationId, String classification);
    
    /**
     * Find all documents uploaded within a specific date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return List of documents uploaded within the specified date range
     */
    List<Document> findByUploadedAtBetween(LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all documents uploaded within a specific date range for an application.
     * 
     * @param applicationId The ID of the application
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return List of documents uploaded within the specified date range for the application
     */
    List<Document> findByApplicationIdAndUploadedAtBetween(
            UUID applicationId, LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all documents uploaded after a specific date.
     * 
     * @param date The date after which documents were uploaded
     * @return List of documents uploaded after the specified date
     */
    List<Document> findByUploadedAtAfter(LocalDateTime date);
    
    /**
     * Find all documents uploaded before a specific date.
     * 
     * @param date The date before which documents were uploaded
     * @return List of documents uploaded before the specified date
     */
    List<Document> findByUploadedAtBefore(LocalDateTime date);
    
    /**
     * Count the number of documents associated with a specific application.
     * 
     * @param applicationId The ID of the application
     * @return The number of documents associated with the application
     */
    long countByApplicationId(UUID applicationId);
    
    /**
     * Count the number of documents of a specific type associated with an application.
     * 
     * @param applicationId The ID of the application
     * @param type The document type
     * @return The number of documents of the specified type associated with the application
     */
    long countByApplicationIdAndType(UUID applicationId, DocumentType type);
    
    /**
     * Check if a document with the specified ID exists for an application.
     * 
     * @param id The document ID
     * @param applicationId The application ID
     * @return true if the document exists, false otherwise
     */
    boolean existsByIdAndApplicationId(UUID id, UUID applicationId);
    
    /**
     * Delete all documents associated with a specific application.
     * 
     * @param applicationId The ID of the application
     */
    void deleteByApplicationId(UUID applicationId);
    
    /**
     * Find all documents with metadata containing a specific key.
     * 
     * @param key The metadata key to search for
     * @return List of documents with metadata containing the specified key
     */
    @Query(value = "SELECT d FROM Document d WHERE d.metadataJson @> CAST(:jsonPath AS jsonb)")
    List<Document> findByMetadataContainsKey(@Param("jsonPath") String key);
    
    /**
     * Find all documents with metadata containing a specific key-value pair.
     * 
     * @param keyValueJson The JSON string representing the key-value pair to search for
     * @return List of documents with metadata containing the specified key-value pair
     */
    @Query(value = "SELECT d FROM Document d WHERE d.metadataJson @> CAST(:keyValueJson AS jsonb)")
    List<Document> findByMetadataContains(@Param("keyValueJson") String keyValueJson);
    
    /**
     * Find all documents with a confidence score above a threshold for a specific field.
     * 
     * @param field The field name to check the confidence score for
     * @param threshold The minimum confidence score threshold
     * @return List of documents with a confidence score above the threshold for the specified field
     */
    @Query(value = "SELECT d FROM Document d WHERE d.metadataJson -> 'confidenceScores' ->> :field\\:\\:text > :threshold\\:\\:text")
    List<Document> findByConfidenceScoreGreaterThan(
            @Param("field") String field, @Param("threshold") double threshold);
    
    /**
     * Find all documents with a confidence score below a threshold for a specific field.
     * 
     * @param field The field name to check the confidence score for
     * @param threshold The maximum confidence score threshold
     * @return List of documents with a confidence score below the threshold for the specified field
     */
    @Query(value = "SELECT d FROM Document d WHERE d.metadataJson -> 'confidenceScores' ->> :field\\:\\:text < :threshold\\:\\:text")
    List<Document> findByConfidenceScoreLessThan(
            @Param("field") String field, @Param("threshold") double threshold);
    
    /**
     * Find all documents with a specific storage path pattern.
     * 
     * @param storagePathPattern The storage path pattern to search for (using SQL LIKE syntax)
     * @return List of documents with a storage path matching the specified pattern
     */
    @Query("SELECT d FROM Document d WHERE d.storagePath LIKE :storagePathPattern")
    List<Document> findByStoragePathPattern(@Param("storagePathPattern") String storagePathPattern);
    
    /**
     * Find all documents that need review based on confidence scores.
     * Documents need review if any confidence score is below the document type's threshold.
     * 
     * @return List of documents that need review
     */
    @Query("SELECT d FROM Document d WHERE EXISTS " +
           "(SELECT 1 FROM jsonb_each_text(d.metadataJson -> 'confidenceScores') AS score(field, value) " +
           "WHERE CAST(value AS double precision) < d.type.ocrConfidenceThreshold)")
    List<Document> findDocumentsNeedingReview();
    
    /**
     * Find all documents that need review for a specific application based on confidence scores.
     * 
     * @param applicationId The ID of the application
     * @return List of documents that need review for the specified application
     */
    @Query("SELECT d FROM Document d WHERE d.applicationId = :applicationId AND EXISTS " +
           "(SELECT 1 FROM jsonb_each_text(d.metadataJson -> 'confidenceScores') AS score(field, value) " +
           "WHERE CAST(value AS double precision) < d.type.ocrConfidenceThreshold)")
    List<Document> findDocumentsNeedingReviewByApplicationId(@Param("applicationId") UUID applicationId);
    
    /**
     * Find all documents with high-confidence classification (above the document type's threshold).
     * 
     * @return List of documents with high-confidence classification
     */
    @Query("SELECT d FROM Document d WHERE " +
           "CAST(d.metadataJson -> 'confidenceScores' ->> 'classification' AS double precision) >= d.type.ocrConfidenceThreshold")
    List<Document> findDocumentsWithHighConfidenceClassification();
    
    /**
     * Find all documents with low-confidence classification (below the document type's threshold).
     * 
     * @return List of documents with low-confidence classification
     */
    @Query("SELECT d FROM Document d WHERE " +
           "CAST(d.metadataJson -> 'confidenceScores' ->> 'classification' AS double precision) < d.type.ocrConfidenceThreshold")
    List<Document> findDocumentsWithLowConfidenceClassification();
    
    /**
     * Find all documents containing personally identifiable information (PII).
     * 
     * @return List of documents containing PII
     */
    @Query("SELECT d FROM Document d WHERE d.type IN (DocumentType.ID_VERIFICATION, DocumentType.TAX_RETURN)")
    List<Document> findDocumentsContainingPII();
    
    /**
     * Find all financial documents.
     * 
     * @return List of financial documents
     */
    @Query("SELECT d FROM Document d WHERE d.type IN (DocumentType.BANK_STATEMENT, DocumentType.TAX_RETURN, DocumentType.INVOICE)")
    List<Document> findFinancialDocuments();
    
    /**
     * Find all documents with valid storage information.
     * 
     * @return List of documents with valid storage information
     */
    @Query("SELECT d FROM Document d WHERE d.storagePath IS NOT NULL AND d.storagePath <> '' AND d.storagePath LIKE 's3://%'")
    List<Document> findDocumentsWithValidStorage();
    
    /**
     * Find all documents with invalid or missing storage information.
     * 
     * @return List of documents with invalid or missing storage information
     */
    @Query("SELECT d FROM Document d WHERE d.storagePath IS NULL OR d.storagePath = '' OR d.storagePath NOT LIKE 's3://%'")
    List<Document> findDocumentsWithInvalidStorage();
}