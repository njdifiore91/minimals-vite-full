package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Service interface for managing documents in the MCA application.
 * Provides methods for storing, retrieving, and managing documents and their metadata.
 * Integrates with S3-compatible storage with AES-256 encryption for secure document storage.
 */
public interface DocumentService {

    /**
     * Stores a document in S3-compatible storage with AES-256 encryption.
     * 
     * @param file The document file to store
     * @param documentRequest The document metadata
     * @return The stored document with metadata
     */
    DocumentResponseDTO storeDocument(MultipartFile file, DocumentRequestDTO documentRequest);
    
    /**
     * Retrieves a document by its ID.
     * 
     * @param id The document ID
     * @return The document if found
     */
    Optional<DocumentResponseDTO> getDocumentById(Long id);
    
    /**
     * Retrieves all documents associated with an application.
     * 
     * @param applicationId The application ID
     * @return List of documents associated with the application
     */
    List<DocumentResponseDTO> getDocumentsByApplicationId(Long applicationId);
    
    /**
     * Retrieves all documents associated with an application with pagination.
     * 
     * @param applicationId The application ID
     * @param pageable Pagination information
     * @return Page of documents associated with the application
     */
    Page<DocumentResponseDTO> getDocumentsByApplicationId(Long applicationId, Pageable pageable);
    
    /**
     * Retrieves documents by type.
     * 
     * @param documentType The document type
     * @param pageable Pagination information
     * @return Page of documents of the specified type
     */
    Page<DocumentResponseDTO> getDocumentsByType(DocumentType documentType, Pageable pageable);
    
    /**
     * Generates a secure, time-limited URL for accessing a document.
     * 
     * @param documentId The document ID
     * @param expirationMinutes The URL expiration time in minutes (default: 15)
     * @return The secure URL for document access
     */
    String generateSecureUrl(Long documentId, Integer expirationMinutes);
    
    /**
     * Generates a secure, time-limited URL for accessing a document with default expiration time.
     * 
     * @param documentId The document ID
     * @return The secure URL for document access
     */
    String generateSecureUrl(Long documentId);
    
    /**
     * Updates document metadata.
     * 
     * @param id The document ID
     * @param documentRequest The updated document metadata
     * @return The updated document
     */
    DocumentResponseDTO updateDocumentMetadata(Long id, DocumentRequestDTO documentRequest);
    
    /**
     * Deletes a document by its ID.
     * 
     * @param id The document ID
     * @return true if the document was deleted, false otherwise
     */
    boolean deleteDocument(Long id);
    
    /**
     * Associates a document with an application.
     * 
     * @param documentId The document ID
     * @param applicationId The application ID
     * @return The updated document
     */
    DocumentResponseDTO associateWithApplication(Long documentId, Long applicationId);
    
    /**
     * Retrieves the document content as an input stream.
     * 
     * @param documentId The document ID
     * @return The document content as an input stream
     */
    InputStream getDocumentContent(Long documentId);
    
    /**
     * Updates document classification metadata.
     * 
     * @param documentId The document ID
     * @param classification The document classification
     * @param confidenceScore The classification confidence score (0-100)
     * @return The updated document
     */
    DocumentResponseDTO updateDocumentClassification(Long documentId, String classification, Double confidenceScore);
    
    /**
     * Updates document classification metadata with additional metadata.
     * 
     * @param documentId The document ID
     * @param classification The document classification
     * @param confidenceScore The classification confidence score (0-100)
     * @param additionalMetadata Additional metadata as key-value pairs
     * @return The updated document
     */
    DocumentResponseDTO updateDocumentClassification(Long documentId, String classification, 
                                                   Double confidenceScore, Map<String, Object> additionalMetadata);
    
    /**
     * Searches for documents based on metadata criteria.
     * 
     * @param searchCriteria The search criteria as key-value pairs
     * @param pageable Pagination information
     * @return Page of documents matching the search criteria
     */
    Page<DocumentResponseDTO> searchDocuments(Map<String, Object> searchCriteria, Pageable pageable);
    
    /**
     * Checks if a document exists by ID.
     * 
     * @param id The document ID
     * @return true if the document exists, false otherwise
     */
    boolean documentExists(Long id);
    
    /**
     * Retrieves the total count of documents by type.
     * 
     * @param documentType The document type
     * @return The count of documents of the specified type
     */
    long countDocumentsByType(DocumentType documentType);
    
    /**
     * Retrieves the total count of documents by application ID.
     * 
     * @param applicationId The application ID
     * @return The count of documents associated with the application
     */
    long countDocumentsByApplicationId(Long applicationId);
    
    /**
     * Validates document metadata against business rules.
     * 
     * @param documentRequest The document metadata to validate
     * @return true if the document metadata is valid, false otherwise
     */
    boolean validateDocumentMetadata(DocumentRequestDTO documentRequest);
    
    /**
     * Processes a document for OCR and data extraction.
     * This method is typically called after document classification.
     * 
     * @param documentId The document ID
     * @return The processed document with extracted data
     */
    DocumentResponseDTO processDocumentForExtraction(Long documentId);
    
    /**
     * Retrieves documents that require manual review due to low confidence scores.
     * 
     * @param confidenceThreshold The confidence threshold (0-100)
     * @param pageable Pagination information
     * @return Page of documents requiring manual review
     */
    Page<DocumentResponseDTO> getDocumentsRequiringReview(Double confidenceThreshold, Pageable pageable);
    
    /**
     * Marks a document as reviewed by a user.
     * 
     * @param documentId The document ID
     * @param reviewerId The ID of the user who reviewed the document
     * @param approved Whether the document was approved
     * @param comments Review comments
     * @return The updated document
     */
    DocumentResponseDTO markDocumentAsReviewed(Long documentId, Long reviewerId, boolean approved, String comments);
    
    /**
     * Retrieves document versions history.
     * 
     * @param documentId The document ID
     * @return List of document versions
     */
    List<DocumentResponseDTO> getDocumentVersions(Long documentId);
    
    /**
     * Creates a new version of an existing document.
     * 
     * @param documentId The original document ID
     * @param file The new document file
     * @param documentRequest The new document metadata
     * @return The new document version
     */
    DocumentResponseDTO createDocumentVersion(Long documentId, MultipartFile file, DocumentRequestDTO documentRequest);
    
    /**
     * Converts a Document entity to a DocumentResponseDTO.
     * 
     * @param document The Document entity
     * @return The DocumentResponseDTO
     */
    DocumentResponseDTO convertToDTO(Document document);
    
    /**
     * Converts a DocumentRequestDTO to a Document entity.
     * 
     * @param documentRequest The DocumentRequestDTO
     * @return The Document entity
     */
    Document convertToEntity(DocumentRequestDTO documentRequest);
}