package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.entity.DocumentType;

import org.springframework.core.io.Resource;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

/**
 * Service interface that defines the contract for document management in the MCA application.
 * It provides methods for storing, retrieving, and managing documents and their metadata.
 * This interface is implemented by DocumentServiceImpl and used by DocumentController to handle
 * document-related operations, including S3 storage integration, classification metadata management,
 * and document association with applications.
 */
public interface DocumentService {

    /**
     * Stores a document file with its metadata and associates it with an application if specified.
     * Implements AES-256 encryption for document storage in S3-compatible storage.
     *
     * @param file The document file to be stored
     * @param documentRequestDTO Metadata for the document including type and application association
     * @return DocumentResponseDTO containing the stored document metadata and access URL
     */
    DocumentResponseDTO storeDocument(MultipartFile file, DocumentRequestDTO documentRequestDTO);

    /**
     * Retrieves document metadata by its ID.
     *
     * @param id The document ID
     * @return DocumentResponseDTO containing the document metadata and access URL
     */
    DocumentResponseDTO getDocumentById(Long id);

    /**
     * Retrieves the actual content of a document by its ID.
     * Returns a map containing the document resource, filename, and content type.
     *
     * @param id The document ID
     * @return Map containing the document resource, filename, and content type
     */
    Map<String, Object> getDocumentContent(Long id);

    /**
     * Retrieves all documents associated with a specific application.
     *
     * @param applicationId The application ID
     * @param pageable Pagination information
     * @return Page of DocumentResponseDTO objects
     */
    Page<DocumentResponseDTO> getDocumentsByApplicationId(Long applicationId, Pageable pageable);

    /**
     * Retrieves all documents of a specific type.
     *
     * @param type The document type
     * @param pageable Pagination information
     * @return Page of DocumentResponseDTO objects
     */
    Page<DocumentResponseDTO> getDocumentsByType(DocumentType type, Pageable pageable);

    /**
     * Updates the metadata of an existing document.
     *
     * @param id The document ID
     * @param documentRequestDTO Updated document metadata
     * @return DocumentResponseDTO containing the updated document metadata
     */
    DocumentResponseDTO updateDocumentMetadata(Long id, DocumentRequestDTO documentRequestDTO);

    /**
     * Deletes a document by its ID.
     * This removes both the metadata from the database and the actual file from S3 storage.
     *
     * @param id The document ID
     */
    void deleteDocument(Long id);

    /**
     * Triggers document classification for an existing document.
     * This process analyzes the document content and updates its classification metadata.
     *
     * @param id The document ID
     * @return DocumentResponseDTO containing the classified document metadata
     */
    DocumentResponseDTO classifyDocument(Long id);

    /**
     * Retrieves a list of all available document types with their descriptions.
     *
     * @return List of maps containing document type values and descriptions
     */
    List<Map<String, String>> getDocumentTypes();

    /**
     * Generates a pre-signed URL for direct document upload to S3 storage.
     * This allows clients to upload large files directly to S3 without going through the application server.
     *
     * @param documentRequestDTO Document metadata including type and filename
     * @return Map containing the pre-signed URL and upload ID
     */
    Map<String, String> generatePresignedUrl(DocumentRequestDTO documentRequestDTO);

    /**
     * Completes a multipart upload initiated with a pre-signed URL.
     * This finalizes the upload and saves the document metadata in the database.
     *
     * @param uploadId The upload ID from the pre-signed URL process
     * @param documentRequestDTO Document metadata
     * @return DocumentResponseDTO containing the uploaded document metadata
     */
    DocumentResponseDTO completeMultipartUpload(String uploadId, DocumentRequestDTO documentRequestDTO);

    /**
     * Generates a secure, time-limited URL for accessing a document.
     * Implements security controls to ensure only authorized users can access documents.
     *
     * @param id The document ID
     * @param expirationMinutes Number of minutes until the URL expires (default: 15)
     * @return String containing the secure URL
     */
    String generateSecureUrl(Long id, Integer expirationMinutes);

    /**
     * Associates an existing document with an application.
     * This is used when documents are uploaded before an application is created.
     *
     * @param documentId The document ID
     * @param applicationId The application ID
     * @return DocumentResponseDTO containing the updated document metadata
     */
    DocumentResponseDTO associateDocumentWithApplication(Long documentId, Long applicationId);

    /**
     * Extracts text content from a document using OCR if necessary.
     * This is used for document searching and indexing.
     *
     * @param id The document ID
     * @return String containing the extracted text content
     */
    String extractDocumentText(Long id);

    /**
     * Validates a document's structure and content against expected templates.
     * This is used to ensure documents meet required standards before processing.
     *
     * @param id The document ID
     * @return Map containing validation results with confidence scores
     */
    Map<String, Object> validateDocumentStructure(Long id);
}