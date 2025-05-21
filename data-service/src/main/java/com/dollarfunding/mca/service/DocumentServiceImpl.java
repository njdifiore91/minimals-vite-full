package com.dollarfunding.mca.service;

import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.StorageException;
import com.dollarfunding.mca.util.EncryptionUtil;
import com.dollarfunding.mca.util.JsonUtil;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PresignedGetObjectRequest;

import java.io.IOException;
import java.io.InputStream;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Implementation of the DocumentService interface that manages document storage, retrieval, and metadata
 * for the MCA application. It integrates with S3-compatible storage for document persistence, handles
 * document classification metadata, and manages document associations with applications.
 * 
 * This class implements AES-256 encryption for document storage and generates signed URLs for secure
 * document access with short expiration times.
 */
@Service
public class DocumentServiceImpl implements DocumentService {

    private static final Logger logger = LoggerFactory.getLogger(DocumentServiceImpl.class);
    
    private final DocumentRepository documentRepository;
    private final ApplicationRepository applicationRepository;
    private final S3Client s3Client;
    private final S3Presigner s3Presigner;
    private final EncryptionUtil encryptionUtil;
    private final JsonUtil jsonUtil;
    
    @Value("${s3.bucket.name}")
    private String bucketName;
    
    @Value("${s3.url.expiration:300}")
    private long urlExpirationSeconds;

    @Autowired
    public DocumentServiceImpl(DocumentRepository documentRepository,
                              ApplicationRepository applicationRepository,
                              S3Client s3Client,
                              S3Presigner s3Presigner,
                              EncryptionUtil encryptionUtil,
                              JsonUtil jsonUtil) {
        this.documentRepository = documentRepository;
        this.applicationRepository = applicationRepository;
        this.s3Client = s3Client;
        this.s3Presigner = s3Presigner;
        this.encryptionUtil = encryptionUtil;
        this.jsonUtil = jsonUtil;
    }

    /**
     * Stores a document in S3 storage with AES-256 encryption and saves its metadata in the database.
     * 
     * @param file The document file to store
     * @param documentRequest The document metadata
     * @return The stored document metadata with generated ID
     * @throws StorageException If there is an error storing the document
     * @throws ResourceNotFoundException If the associated application is not found
     */
    @Override
    @Transactional
    public DocumentResponseDTO storeDocument(MultipartFile file, DocumentRequestDTO documentRequest) {
        logger.info("Storing document with type: {}", documentRequest.getType());
        
        // Validate application exists
        Application application = applicationRepository.findById(documentRequest.getApplicationId())
                .orElseThrow(() -> new ResourceNotFoundException("Application not found with id: " + documentRequest.getApplicationId()));
        
        // Generate a unique storage path
        String storagePath = generateStoragePath(documentRequest.getApplicationId(), documentRequest.getType());
        
        try {
            // Store the document in S3 with AES-256 encryption
            storeDocumentInS3(file, storagePath);
            
            // Create and save document metadata
            Document document = new Document();
            document.setApplication(application);
            document.setType(documentRequest.getType());
            document.setStoragePath(storagePath);
            document.setClassification(documentRequest.getClassification());
            document.setUploadedAt(LocalDateTime.now());
            
            // Store metadata as JSON
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("originalFilename", file.getOriginalFilename());
            metadata.put("contentType", file.getContentType());
            metadata.put("size", file.getSize());
            metadata.put("classification", documentRequest.getClassification());
            
            // Add confidence scores if available
            if (documentRequest.getConfidenceScores() != null) {
                metadata.put("confidenceScores", documentRequest.getConfidenceScores());
            }
            
            document.setMetadata(jsonUtil.toJson(metadata));
            
            Document savedDocument = documentRepository.save(document);
            
            // Generate a signed URL for immediate access
            String signedUrl = generateSignedUrl(storagePath);
            
            return createDocumentResponseDTO(savedDocument, signedUrl);
        } catch (IOException e) {
            logger.error("Failed to store document", e);
            throw new StorageException("Failed to store document", e);
        }
    }

    /**
     * Retrieves a document by its ID, including a pre-signed URL for secure access.
     * 
     * @param id The document ID
     * @return The document metadata with a pre-signed URL
     * @throws ResourceNotFoundException If the document is not found
     */
    @Override
    public DocumentResponseDTO getDocumentById(Long id) {
        logger.info("Retrieving document with id: {}", id);
        
        Document document = documentRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Document not found with id: " + id));
        
        String signedUrl = generateSignedUrl(document.getStoragePath());
        
        return createDocumentResponseDTO(document, signedUrl);
    }

    /**
     * Retrieves all documents associated with an application.
     * 
     * @param applicationId The application ID
     * @param pageable Pagination information
     * @return A page of document metadata with pre-signed URLs
     * @throws ResourceNotFoundException If the application is not found
     */
    @Override
    public Page<DocumentResponseDTO> getDocumentsByApplicationId(Long applicationId, Pageable pageable) {
        logger.info("Retrieving documents for application id: {}", applicationId);
        
        // Verify application exists
        if (!applicationRepository.existsById(applicationId)) {
            throw new ResourceNotFoundException("Application not found with id: " + applicationId);
        }
        
        Page<Document> documents = documentRepository.findByApplicationId(applicationId, pageable);
        
        return documents.map(document -> {
            String signedUrl = generateSignedUrl(document.getStoragePath());
            return createDocumentResponseDTO(document, signedUrl);
        });
    }

    /**
     * Retrieves all documents of a specific type associated with an application.
     * 
     * @param applicationId The application ID
     * @param type The document type
     * @return A list of document metadata with pre-signed URLs
     * @throws ResourceNotFoundException If the application is not found
     */
    @Override
    public List<DocumentResponseDTO> getDocumentsByApplicationIdAndType(Long applicationId, DocumentType type) {
        logger.info("Retrieving documents for application id: {} and type: {}", applicationId, type);
        
        // Verify application exists
        if (!applicationRepository.existsById(applicationId)) {
            throw new ResourceNotFoundException("Application not found with id: " + applicationId);
        }
        
        List<Document> documents = documentRepository.findByApplicationIdAndType(applicationId, type);
        
        return documents.stream()
                .map(document -> {
                    String signedUrl = generateSignedUrl(document.getStoragePath());
                    return createDocumentResponseDTO(document, signedUrl);
                })
                .toList();
    }

    /**
     * Updates document metadata.
     * 
     * @param id The document ID
     * @param documentRequest The updated document metadata
     * @return The updated document metadata with a pre-signed URL
     * @throws ResourceNotFoundException If the document is not found
     */
    @Override
    @Transactional
    public DocumentResponseDTO updateDocumentMetadata(Long id, DocumentRequestDTO documentRequest) {
        logger.info("Updating metadata for document id: {}", id);
        
        Document document = documentRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Document not found with id: " + id));
        
        // Update fields if provided
        if (documentRequest.getType() != null) {
            document.setType(documentRequest.getType());
        }
        
        if (documentRequest.getClassification() != null) {
            document.setClassification(documentRequest.getClassification());
        }
        
        // Update metadata if provided
        if (documentRequest.getMetadata() != null) {
            try {
                // Parse existing metadata
                Map<String, Object> existingMetadata = jsonUtil.fromJson(document.getMetadata(), Map.class);
                
                // Merge with new metadata
                Map<String, Object> newMetadata = documentRequest.getMetadata();
                existingMetadata.putAll(newMetadata);
                
                document.setMetadata(jsonUtil.toJson(existingMetadata));
            } catch (Exception e) {
                logger.error("Failed to update document metadata", e);
                throw new StorageException("Failed to update document metadata", e);
            }
        }
        
        Document updatedDocument = documentRepository.save(document);
        String signedUrl = generateSignedUrl(updatedDocument.getStoragePath());
        
        return createDocumentResponseDTO(updatedDocument, signedUrl);
    }

    /**
     * Deletes a document by its ID, removing both metadata from the database and content from S3.
     * 
     * @param id The document ID
     * @throws ResourceNotFoundException If the document is not found
     * @throws StorageException If there is an error deleting the document from S3
     */
    @Override
    @Transactional
    public void deleteDocument(Long id) {
        logger.info("Deleting document with id: {}", id);
        
        Document document = documentRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Document not found with id: " + id));
        
        // Delete from S3 first
        try {
            deleteDocumentFromS3(document.getStoragePath());
        } catch (Exception e) {
            logger.error("Failed to delete document from S3", e);
            throw new StorageException("Failed to delete document from S3", e);
        }
        
        // Then delete metadata from database
        documentRepository.delete(document);
    }

    /**
     * Generates a pre-signed URL for secure document access with a short expiration time.
     * 
     * @param storagePath The S3 storage path of the document
     * @return A pre-signed URL for secure access
     */
    private String generateSignedUrl(String storagePath) {
        GetObjectRequest getObjectRequest = GetObjectRequest.builder()
                .bucket(bucketName)
                .key(storagePath)
                .build();
        
        GetObjectPresignRequest presignRequest = GetObjectPresignRequest.builder()
                .signatureDuration(Duration.ofSeconds(urlExpirationSeconds))
                .getObjectRequest(getObjectRequest)
                .build();
        
        PresignedGetObjectRequest presignedRequest = s3Presigner.presignGetObject(presignRequest);
        
        return presignedRequest.url().toString();
    }

    /**
     * Generates a unique storage path for a document in S3.
     * 
     * @param applicationId The application ID
     * @param documentType The document type
     * @return A unique storage path
     */
    private String generateStoragePath(Long applicationId, DocumentType documentType) {
        String uuid = UUID.randomUUID().toString();
        return String.format("applications/%d/%s/%s", applicationId, documentType.toString().toLowerCase(), uuid);
    }

    /**
     * Stores a document in S3 with AES-256 encryption.
     * 
     * @param file The document file to store
     * @param storagePath The S3 storage path
     * @throws IOException If there is an error reading the file
     * @throws StorageException If there is an error storing the file in S3
     */
    private void storeDocumentInS3(MultipartFile file, String storagePath) throws IOException {
        try (InputStream inputStream = file.getInputStream()) {
            // Configure AES-256 encryption for the object
            PutObjectRequest putObjectRequest = PutObjectRequest.builder()
                    .bucket(bucketName)
                    .key(storagePath)
                    .contentType(file.getContentType())
                    .serverSideEncryption("AES256")
                    .build();
            
            s3Client.putObject(putObjectRequest, RequestBody.fromInputStream(inputStream, file.getSize()));
            
            logger.info("Successfully stored document in S3: {}", storagePath);
        } catch (Exception e) {
            logger.error("Failed to store document in S3", e);
            throw new StorageException("Failed to store document in S3", e);
        }
    }

    /**
     * Deletes a document from S3.
     * 
     * @param storagePath The S3 storage path
     * @throws StorageException If there is an error deleting the file from S3
     */
    private void deleteDocumentFromS3(String storagePath) {
        try {
            DeleteObjectRequest deleteObjectRequest = DeleteObjectRequest.builder()
                    .bucket(bucketName)
                    .key(storagePath)
                    .build();
            
            s3Client.deleteObject(deleteObjectRequest);
            
            logger.info("Successfully deleted document from S3: {}", storagePath);
        } catch (Exception e) {
            logger.error("Failed to delete document from S3", e);
            throw new StorageException("Failed to delete document from S3", e);
        }
    }

    /**
     * Creates a DocumentResponseDTO from a Document entity and a signed URL.
     * 
     * @param document The Document entity
     * @param signedUrl The pre-signed URL for secure access
     * @return A DocumentResponseDTO
     */
    private DocumentResponseDTO createDocumentResponseDTO(Document document, String signedUrl) {
        DocumentResponseDTO responseDTO = new DocumentResponseDTO();
        responseDTO.setId(document.getId());
        responseDTO.setApplicationId(document.getApplication().getId());
        responseDTO.setType(document.getType());
        responseDTO.setClassification(document.getClassification());
        responseDTO.setUploadedAt(document.getUploadedAt());
        responseDTO.setMetadata(document.getMetadata());
        responseDTO.setSignedUrl(signedUrl);
        return responseDTO;
    }
}