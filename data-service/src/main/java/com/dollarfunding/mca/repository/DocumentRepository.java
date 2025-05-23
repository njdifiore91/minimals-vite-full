package com.dollarfunding.mca.repository;

import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentClassification;
import com.dollarfunding.mca.entity.DocumentType;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
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
 * The repository is used by DocumentService to manage document metadata while the actual document
 * content is stored in S3-compatible storage with AES-256 encryption.
 */
@Repository
public interface DocumentRepository extends JpaRepository<Document, UUID> {
    
    /**
     * Find a document by its ID.
     * 
     * @param id The document ID
     * @return Optional containing the document if found, empty otherwise
     */
    Optional<Document> findById(UUID id);
    
    /**
     * Find all documents associated with a specific application.
     * 
     * @param applicationId The application ID
     * @return List of documents associated with the specified application
     */
    List<Document> findByApplicationId(UUID applicationId);
    
    /**
     * Find all documents associated with a specific application, with pagination.
     * 
     * @param applicationId The application ID
     * @param pageable The pagination information
     * @return Page of documents associated with the specified application
     */
    Page<Document> findByApplicationId(UUID applicationId, Pageable pageable);
    
    /**
     * Find all documents of a specific type.
     * 
     * @param type The document type
     * @return List of documents of the specified type
     */
    List<Document> findByType(DocumentType type);
    
    /**
     * Find all documents of a specific type, with pagination.
     * 
     * @param type The document type
     * @param pageable The pagination information
     * @return Page of documents of the specified type
     */
    Page<Document> findByType(DocumentType type, Pageable pageable);
    
    /**
     * Find all documents with a specific classification.
     * 
     * @param classification The document classification
     * @return List of documents with the specified classification
     */
    List<Document> findByClassification(DocumentClassification classification);
    
    /**
     * Find all documents with a specific classification, with pagination.
     * 
     * @param classification The document classification
     * @param pageable The pagination information
     * @return Page of documents with the specified classification
     */
    Page<Document> findByClassification(DocumentClassification classification, Pageable pageable);
    
    /**
     * Find all documents associated with a specific application and of a specific type.
     * 
     * @param applicationId The application ID
     * @param type The document type
     * @return List of documents associated with the specified application and of the specified type
     */
    List<Document> findByApplicationIdAndType(UUID applicationId, DocumentType type);
    
    /**
     * Find all documents associated with a specific application and with a specific classification.
     * 
     * @param applicationId The application ID
     * @param classification The document classification
     * @return List of documents associated with the specified application and with the specified classification
     */
    List<Document> findByApplicationIdAndClassification(UUID applicationId, DocumentClassification classification);
    
    /**
     * Find all documents of a specific type and with a specific classification.
     * 
     * @param type The document type
     * @param classification The document classification
     * @return List of documents of the specified type and with the specified classification
     */
    List<Document> findByTypeAndClassification(DocumentType type, DocumentClassification classification);
    
    /**
     * Find all documents associated with a specific application, of a specific type, and with a specific classification.
     * 
     * @param applicationId The application ID
     * @param type The document type
     * @param classification The document classification
     * @return List of documents matching all criteria
     */
    List<Document> findByApplicationIdAndTypeAndClassification(
            UUID applicationId, DocumentType type, DocumentClassification classification);
    
    /**
     * Find all documents uploaded within a specific date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return List of documents uploaded within the specified date range
     */
    List<Document> findByUploadedAtBetween(LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all documents uploaded within a specific date range, with pagination.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @param pageable The pagination information
     * @return Page of documents uploaded within the specified date range
     */
    Page<Document> findByUploadedAtBetween(LocalDateTime startDate, LocalDateTime endDate, Pageable pageable);
    
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
     * Find all documents associated with a specific application and uploaded within a specific date range.
     * 
     * @param applicationId The application ID
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return List of documents associated with the specified application and uploaded within the specified date range
     */
    List<Document> findByApplicationIdAndUploadedAtBetween(
            UUID applicationId, LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all documents of a specific type and uploaded within a specific date range.
     * 
     * @param type The document type
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return List of documents of the specified type and uploaded within the specified date range
     */
    List<Document> findByTypeAndUploadedAtBetween(
            DocumentType type, LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all documents with a specific classification and uploaded within a specific date range.
     * 
     * @param classification The document classification
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return List of documents with the specified classification and uploaded within the specified date range
     */
    List<Document> findByClassificationAndUploadedAtBetween(
            DocumentClassification classification, LocalDateTime startDate, LocalDateTime endDate);
    
    /**
     * Find all documents with a specific storage path.
     * 
     * @param storagePath The storage path
     * @return List of documents with the specified storage path
     */
    List<Document> findByStoragePath(String storagePath);
    
    /**
     * Find all documents with a storage path containing a specific string.
     * 
     * @param pathFragment The path fragment to search for
     * @return List of documents with a storage path containing the specified string
     */
    List<Document> findByStoragePathContaining(String pathFragment);
    
    /**
     * Count the number of documents associated with a specific application.
     * 
     * @param applicationId The application ID
     * @return The number of documents associated with the specified application
     */
    long countByApplicationId(UUID applicationId);
    
    /**
     * Count the number of documents of a specific type.
     * 
     * @param type The document type
     * @return The number of documents of the specified type
     */
    long countByType(DocumentType type);
    
    /**
     * Count the number of documents with a specific classification.
     * 
     * @param classification The document classification
     * @return The number of documents with the specified classification
     */
    long countByClassification(DocumentClassification classification);
    
    /**
     * Count the number of documents associated with a specific application and of a specific type.
     * 
     * @param applicationId The application ID
     * @param type The document type
     * @return The number of documents associated with the specified application and of the specified type
     */
    long countByApplicationIdAndType(UUID applicationId, DocumentType type);
    
    /**
     * Count the number of documents uploaded within a specific date range.
     * 
     * @param startDate The start date of the range (inclusive)
     * @param endDate The end date of the range (inclusive)
     * @return The number of documents uploaded within the specified date range
     */
    long countByUploadedAtBetween(LocalDateTime startDate, LocalDateTime endDate);
    
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
     * Find all documents with metadata containing a specific key-value pair, with pagination.
     * 
     * @param keyValueJson The JSON string representing the key-value pair to search for
     * @param pageable The pagination information
     * @return Page of documents with metadata containing the specified key-value pair
     */
    @Query(value = "SELECT d FROM Document d WHERE d.metadataJson @> CAST(:keyValueJson AS jsonb)")
    Page<Document> findByMetadataContains(@Param("keyValueJson") String keyValueJson, Pageable pageable);
    
    /**
     * Find all documents with a confidence score above a specific threshold.
     * 
     * @param threshold The confidence score threshold
     * @return List of documents with a confidence score above the specified threshold
     */
    @Query("SELECT d FROM Document d WHERE CAST(d.metadataJson ->> 'confidenceScore' AS double) >= :threshold")
    List<Document> findByConfidenceScoreGreaterThanEqual(@Param("threshold") double threshold);
    
    /**
     * Find all documents with a confidence score below a specific threshold.
     * 
     * @param threshold The confidence score threshold
     * @return List of documents with a confidence score below the specified threshold
     */
    @Query("SELECT d FROM Document d WHERE CAST(d.metadataJson ->> 'confidenceScore' AS double) < :threshold")
    List<Document> findByConfidenceScoreLessThan(@Param("threshold") double threshold);
    
    /**
     * Find all documents that require manual review.
     * Documents require manual review if their classification is NEEDS_REVIEW or FLAGGED.
     * 
     * @return List of documents that require manual review
     */
    @Query("SELECT d FROM Document d WHERE d.classification.requiresManualReview = true")
    List<Document> findDocumentsRequiringManualReview();
    
    /**
     * Find all documents that require manual review, with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of documents that require manual review
     */
    @Query("SELECT d FROM Document d WHERE d.classification.requiresManualReview = true")
    Page<Document> findDocumentsRequiringManualReview(Pageable pageable);
    
    /**
     * Find all documents that are acceptable for processing.
     * Documents are acceptable if their classification is VERIFIED or NEEDS_REVIEW.
     * 
     * @return List of documents that are acceptable for processing
     */
    @Query("SELECT d FROM Document d WHERE d.classification.isAcceptable = true")
    List<Document> findAcceptableDocuments();
    
    /**
     * Find all documents that are acceptable for processing, with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of documents that are acceptable for processing
     */
    @Query("SELECT d FROM Document d WHERE d.classification.isAcceptable = true")
    Page<Document> findAcceptableDocuments(Pageable pageable);
    
    /**
     * Find all documents that have been rejected.
     * Documents are rejected if their classification is REJECTED.
     * 
     * @return List of rejected documents
     */
    @Query("SELECT d FROM Document d WHERE d.classification = 'REJECTED'")
    List<Document> findRejectedDocuments();
    
    /**
     * Find all documents that have been rejected, with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of rejected documents
     */
    @Query("SELECT d FROM Document d WHERE d.classification = 'REJECTED'")
    Page<Document> findRejectedDocuments(Pageable pageable);
    
    /**
     * Find all documents that have been verified.
     * Documents are verified if their classification is VERIFIED.
     * 
     * @return List of verified documents
     */
    @Query("SELECT d FROM Document d WHERE d.classification = 'VERIFIED'")
    List<Document> findVerifiedDocuments();
    
    /**
     * Find all documents that have been verified, with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of verified documents
     */
    @Query("SELECT d FROM Document d WHERE d.classification = 'VERIFIED'")
    Page<Document> findVerifiedDocuments(Pageable pageable);
    
    /**
     * Find all documents that have not yet been classified.
     * Documents are unclassified if their classification is UNCLASSIFIED.
     * 
     * @return List of unclassified documents
     */
    @Query("SELECT d FROM Document d WHERE d.classification = 'UNCLASSIFIED'")
    List<Document> findUnclassifiedDocuments();
    
    /**
     * Find all documents that have not yet been classified, with pagination.
     * 
     * @param pageable The pagination information
     * @return Page of unclassified documents
     */
    @Query("SELECT d FROM Document d WHERE d.classification = 'UNCLASSIFIED'")
    Page<Document> findUnclassifiedDocuments(Pageable pageable);
    
    /**
     * Find all documents associated with a specific application that require manual review.
     * 
     * @param applicationId The application ID
     * @return List of documents associated with the specified application that require manual review
     */
    @Query("SELECT d FROM Document d WHERE d.applicationId = :applicationId AND d.classification.requiresManualReview = true")
    List<Document> findDocumentsRequiringManualReviewByApplicationId(@Param("applicationId") UUID applicationId);
    
    /**
     * Find all documents of a specific type that require manual review.
     * 
     * @param type The document type
     * @return List of documents of the specified type that require manual review
     */
    @Query("SELECT d FROM Document d WHERE d.type = :type AND d.classification.requiresManualReview = true")
    List<Document> findDocumentsRequiringManualReviewByType(@Param("type") DocumentType type);
    
    /**
     * Find all documents with a specific file extension.
     * 
     * @param extension The file extension (e.g., "pdf", "jpg")
     * @return List of documents with the specified file extension
     */
    @Query("SELECT d FROM Document d WHERE LOWER(SUBSTRING(d.storagePath, LENGTH(d.storagePath) - LOCATE('.', REVERSE(d.storagePath)) + 2)) = LOWER(:extension)")
    List<Document> findByFileExtension(@Param("extension") String extension);
    
    /**
     * Find all documents with a specific MIME type.
     * 
     * @param mimeType The MIME type (e.g., "application/pdf", "image/jpeg")
     * @return List of documents with the specified MIME type
     */
    @Query("SELECT d FROM Document d WHERE d.getMimeType() = :mimeType")
    List<Document> findByMimeType(@Param("mimeType") String mimeType);
    
    /**
     * Find all documents in a specific S3 bucket.
     * 
     * @param bucketName The S3 bucket name
     * @return List of documents in the specified S3 bucket
     */
    @Query("SELECT d FROM Document d WHERE d.getBucketName() = :bucketName")
    List<Document> findByBucketName(@Param("bucketName") String bucketName);
    
    /**
     * Delete all documents associated with a specific application.
     * 
     * @param applicationId The application ID
     * @return The number of documents deleted
     */
    long deleteByApplicationId(UUID applicationId);
    
    /**
     * Delete all documents of a specific type.
     * 
     * @param type The document type
     * @return The number of documents deleted
     */
    long deleteByType(DocumentType type);
    
    /**
     * Delete all documents with a specific classification.
     * 
     * @param classification The document classification
     * @return The number of documents deleted
     */
    long deleteByClassification(DocumentClassification classification);
    
    /**
     * Delete all documents uploaded before a specific date.
     * 
     * @param date The date before which documents were uploaded
     * @return The number of documents deleted
     */
    long deleteByUploadedAtBefore(LocalDateTime date);
}