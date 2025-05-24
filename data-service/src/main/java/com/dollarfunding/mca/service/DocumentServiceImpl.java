package com.dollarfunding.mca.service;

import com.dollarfunding.mca.config.S3Config;
import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentClassification;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.exception.DocumentNotFoundException;
import com.dollarfunding.mca.exception.DocumentStorageException;
import com.dollarfunding.mca.exception.InvalidDocumentException;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.util.ErrorUtil;
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

import software.amazon.awssdk.core.ResponseInputStream;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.*;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;

import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Implementation of the DocumentService interface that manages document storage, retrieval, and metadata
 * for the MCA application. It integrates with S3-compatible storage for document persistence, handles
 * document classification metadata, and manages document associations with applications.
 * 
 * This class implements AES-256 encryption for document storage (via S3Config) and generates signed URLs
 * for secure document access. It uses DocumentRepository for database operations related to document metadata.
 */
@Service
public class DocumentServiceImpl implements DocumentService {

    private static final Logger logger = LoggerFactory.getLogger(DocumentServiceImpl.class);
    
    private final DocumentRepository documentRepository;
    private final S3Config s3Config;
    private final S3Client s3Client;
    private final S3Presigner s3Presigner;
    
    @Value("${document.url.expiration:15}")
    private int defaultUrlExpirationMinutes;
    
    @Value("${document.storage.path.prefix:documents/}")
    private String storagePathPrefix;
    
    // Cache for document content types to avoid repeated S3 HEAD requests
    private final Map<String, String> contentTypeCache = new ConcurrentHashMap<>();
    
    /**
     * Constructor with required dependencies.
     * 
     * @param documentRepository Repository for document metadata persistence
     * @param s3Config Configuration for S3-compatible storage
     * @param s3Client S3 client for storage operations
     * @param s3Presigner S3 presigner for generating signed URLs
     */
    @Autowired
    public DocumentServiceImpl(DocumentRepository documentRepository, 
                              S3Config s3Config,
                              S3Client s3Client,
                              S3Presigner s3Presigner) {
        this.documentRepository = documentRepository;
        this.s3Config = s3Config;
        this.s3Client = s3Client;
        this.s3Presigner = s3Presigner;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public DocumentResponseDTO storeDocument(MultipartFile file, DocumentRequestDTO documentRequest) {
        logger.info("Storing document for application ID: {}", documentRequest.getApplicationId());
        
        if (file == null || file.isEmpty()) {
            throw new InvalidDocumentException("Document file is empty or null");
        }
        
        if (!documentRequest.isValidForCreation()) {
            throw new InvalidDocumentException("Invalid document request: missing required fields");
        }
        
        try {
            // Generate a unique storage path for the document
            String fileName = generateUniqueFileName(file.getOriginalFilename());
            String storagePath = generateStoragePath(documentRequest.getApplicationId(), fileName);
            
            // Upload the document to S3 with AES-256 encryption (handled by S3Config)
            uploadToS3(file.getInputStream(), storagePath, file.getContentType(), file.getSize());
            
            // Create document metadata entity
            Document document = convertToEntity(documentRequest);
            document.setStoragePath(storagePath);
            document.setUploadedAt(LocalDateTime.now());
            
            // Add additional metadata
            Map<String, Object> metadata = documentRequest.getMetadata() != null ? 
                    new HashMap<>(documentRequest.getMetadata()) : new HashMap<>();
            metadata.put("originalFilename", file.getOriginalFilename());
            metadata.put("contentType", file.getContentType());
            metadata.put("fileSize", file.getSize());
            document.setMetadata(metadata);
            
            // Set initial classification if not provided
            if (document.getClassification() == null) {
                document.setClassification(DocumentClassification.UNCLASSIFIED);
            }
            
            // Save document metadata to database
            Document savedDocument = documentRepository.save(document);
            logger.debug("Document saved with ID: {}", savedDocument.getId());
            
            // Generate a secure URL for document access
            URL secureUrl = generateSignedUrl(savedDocument.getStoragePath(), defaultUrlExpirationMinutes);
            LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
            
            return new DocumentResponseDTO.Builder(savedDocument)
                    .withDownloadUrl(secureUrl.toString())
                    .withUrlExpiresAt(urlExpiresAt)
                    .build();
            
        } catch (IOException e) {
            logger.error("Failed to store document: {}", e.getMessage(), e);
            throw new DocumentStorageException("Failed to store document: " + e.getMessage(), e);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public Optional<DocumentResponseDTO> getDocumentById(Long id) {
        logger.debug("Retrieving document with ID: {}", id);
        
        return documentRepository.findById(UUID.fromString(id.toString()))
                .map(document -> {
                    // Generate a secure URL for document access
                    URL secureUrl = generateSignedUrl(document.getStoragePath(), defaultUrlExpirationMinutes);
                    LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
                    
                    return new DocumentResponseDTO.Builder(document)
                            .withDownloadUrl(secureUrl.toString())
                            .withUrlExpiresAt(urlExpiresAt)
                            .build();
                });
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public List<DocumentResponseDTO> getDocumentsByApplicationId(Long applicationId) {
        logger.debug("Retrieving documents for application ID: {}", applicationId);
        
        List<Document> documents = documentRepository.findByApplicationId(UUID.fromString(applicationId.toString()));
        return documents.stream()
                .map(document -> {
                    // Generate a secure URL for document access
                    URL secureUrl = generateSignedUrl(document.getStoragePath(), defaultUrlExpirationMinutes);
                    LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
                    
                    return new DocumentResponseDTO.Builder(document)
                            .withDownloadUrl(secureUrl.toString())
                            .withUrlExpiresAt(urlExpiresAt)
                            .build();
                })
                .collect(Collectors.toList());
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public Page<DocumentResponseDTO> getDocumentsByApplicationId(Long applicationId, Pageable pageable) {
        logger.debug("Retrieving documents for application ID: {} with pagination", applicationId);
        
        Page<Document> documentPage = documentRepository.findByApplicationId(
                UUID.fromString(applicationId.toString()), pageable);
        
        return documentPage.map(document -> {
            // Generate a secure URL for document access
            URL secureUrl = generateSignedUrl(document.getStoragePath(), defaultUrlExpirationMinutes);
            LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
            
            return new DocumentResponseDTO.Builder(document)
                    .withDownloadUrl(secureUrl.toString())
                    .withUrlExpiresAt(urlExpiresAt)
                    .build();
        });
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public Page<DocumentResponseDTO> getDocumentsByType(DocumentType documentType, Pageable pageable) {
        logger.debug("Retrieving documents of type: {} with pagination", documentType);
        
        Page<Document> documentPage = documentRepository.findByType(documentType, pageable);
        
        return documentPage.map(document -> {
            // Generate a secure URL for document access
            URL secureUrl = generateSignedUrl(document.getStoragePath(), defaultUrlExpirationMinutes);
            LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
            
            return new DocumentResponseDTO.Builder(document)
                    .withDownloadUrl(secureUrl.toString())
                    .withUrlExpiresAt(urlExpiresAt)
                    .build();
        });
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public String generateSecureUrl(Long documentId, Integer expirationMinutes) {
        logger.debug("Generating secure URL for document ID: {} with expiration: {} minutes", 
                documentId, expirationMinutes);
        
        Document document = documentRepository.findById(UUID.fromString(documentId.toString()))
                .orElseThrow(() -> new DocumentNotFoundException("Document not found with ID: " + documentId));
        
        int expiration = expirationMinutes != null ? expirationMinutes : defaultUrlExpirationMinutes;
        URL secureUrl = generateSignedUrl(document.getStoragePath(), expiration);
        
        return secureUrl.toString();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public String generateSecureUrl(Long documentId) {
        return generateSecureUrl(documentId, null);
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public DocumentResponseDTO updateDocumentMetadata(Long id, DocumentRequestDTO documentRequest) {
        logger.info("Updating metadata for document ID: {}", id);
        
        Document document = documentRepository.findById(UUID.fromString(id.toString()))
                .orElseThrow(() -> new DocumentNotFoundException("Document not found with ID: " + id));
        
        // Update document fields if provided in the request
        if (documentRequest.getType() != null) {
            document.setType(documentRequest.getType());
        }
        
        if (documentRequest.getClassification() != null) {
            document.setClassification(DocumentClassification.fromString(documentRequest.getClassification()));
        }
        
        // Update metadata if provided
        if (documentRequest.hasMetadata()) {
            Map<String, Object> currentMetadata = document.getMetadata();
            Map<String, Object> newMetadata = documentRequest.getMetadata();
            
            // Merge metadata, preserving existing values not in the request
            currentMetadata.putAll(newMetadata);
            document.setMetadata(currentMetadata);
        }
        
        // Update classification confidence if provided
        if (documentRequest.getClassificationConfidence() != null) {
            document.setConfidenceScore(documentRequest.getClassificationConfidence());
        }
        
        // Save updated document
        Document updatedDocument = documentRepository.save(document);
        
        // Generate a secure URL for document access
        URL secureUrl = generateSignedUrl(updatedDocument.getStoragePath(), defaultUrlExpirationMinutes);
        LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
        
        return new DocumentResponseDTO.Builder(updatedDocument)
                .withDownloadUrl(secureUrl.toString())
                .withUrlExpiresAt(urlExpiresAt)
                .build();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public boolean deleteDocument(Long id) {
        logger.info("Deleting document with ID: {}", id);
        
        Document document = documentRepository.findById(UUID.fromString(id.toString()))
                .orElseThrow(() -> new DocumentNotFoundException("Document not found with ID: " + id));
        
        try {
            // Delete document from S3
            deleteFromS3(document.getStoragePath());
            
            // Delete document metadata from database
            documentRepository.delete(document);
            
            logger.debug("Document deleted successfully: {}", id);
            return true;
        } catch (Exception e) {
            logger.error("Failed to delete document: {}", e.getMessage(), e);
            throw new DocumentStorageException("Failed to delete document: " + e.getMessage(), e);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public DocumentResponseDTO associateWithApplication(Long documentId, Long applicationId) {
        logger.info("Associating document ID: {} with application ID: {}", documentId, applicationId);
        
        Document document = documentRepository.findById(UUID.fromString(documentId.toString()))
                .orElseThrow(() -> new DocumentNotFoundException("Document not found with ID: " + documentId));
        
        // Update application ID
        document.setApplicationId(UUID.fromString(applicationId.toString()));
        
        // Save updated document
        Document updatedDocument = documentRepository.save(document);
        
        // Generate a secure URL for document access
        URL secureUrl = generateSignedUrl(updatedDocument.getStoragePath(), defaultUrlExpirationMinutes);
        LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
        
        return new DocumentResponseDTO.Builder(updatedDocument)
                .withDownloadUrl(secureUrl.toString())
                .withUrlExpiresAt(urlExpiresAt)
                .build();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public InputStream getDocumentContent(Long documentId) {
        logger.debug("Retrieving content for document ID: {}", documentId);
        
        Document document = documentRepository.findById(UUID.fromString(documentId.toString()))
                .orElseThrow(() -> new DocumentNotFoundException("Document not found with ID: " + documentId));
        
        try {
            // Get document content from S3
            return getFromS3(document.getStoragePath());
        } catch (Exception e) {
            logger.error("Failed to retrieve document content: {}", e.getMessage(), e);
            throw new DocumentStorageException("Failed to retrieve document content: " + e.getMessage(), e);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public DocumentResponseDTO updateDocumentClassification(Long documentId, String classification, 
                                                         Double confidenceScore) {
        return updateDocumentClassification(documentId, classification, confidenceScore, null);
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public DocumentResponseDTO updateDocumentClassification(Long documentId, String classification, 
                                                         Double confidenceScore, 
                                                         Map<String, Object> additionalMetadata) {
        logger.info("Updating classification for document ID: {} to {}", documentId, classification);
        
        Document document = documentRepository.findById(UUID.fromString(documentId.toString()))
                .orElseThrow(() -> new DocumentNotFoundException("Document not found with ID: " + documentId));
        
        // Update classification
        document.setClassification(DocumentClassification.fromString(classification));
        
        // Update confidence score
        if (confidenceScore != null) {
            document.setConfidenceScore(confidenceScore);
        }
        
        // Update additional metadata if provided
        if (additionalMetadata != null && !additionalMetadata.isEmpty()) {
            Map<String, Object> currentMetadata = document.getMetadata();
            currentMetadata.putAll(additionalMetadata);
            document.setMetadata(currentMetadata);
        }
        
        // Save updated document
        Document updatedDocument = documentRepository.save(document);
        
        // Generate a secure URL for document access
        URL secureUrl = generateSignedUrl(updatedDocument.getStoragePath(), defaultUrlExpirationMinutes);
        LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
        
        return new DocumentResponseDTO.Builder(updatedDocument)
                .withDownloadUrl(secureUrl.toString())
                .withUrlExpiresAt(urlExpiresAt)
                .build();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public Page<DocumentResponseDTO> searchDocuments(Map<String, Object> searchCriteria, Pageable pageable) {
        logger.debug("Searching documents with criteria: {}", searchCriteria);
        
        // Convert search criteria to JSON for PostgreSQL JSONB query
        String searchJson;
        try {
            searchJson = JsonUtil.toJson(searchCriteria);
        } catch (JsonUtil.JsonConversionException e) {
            logger.error("Failed to convert search criteria to JSON: {}", e.getMessage(), e);
            throw new InvalidDocumentException("Invalid search criteria: " + e.getMessage(), e);
        }
        
        // Search documents by metadata
        Page<Document> documentPage = documentRepository.findByMetadataContains(searchJson, pageable);
        
        return documentPage.map(document -> {
            // Generate a secure URL for document access
            URL secureUrl = generateSignedUrl(document.getStoragePath(), defaultUrlExpirationMinutes);
            LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
            
            return new DocumentResponseDTO.Builder(document)
                    .withDownloadUrl(secureUrl.toString())
                    .withUrlExpiresAt(urlExpiresAt)
                    .build();
        });
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public boolean documentExists(Long id) {
        return documentRepository.existsById(UUID.fromString(id.toString()));
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public long countDocumentsByType(DocumentType documentType) {
        return documentRepository.countByType(documentType);
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public long countDocumentsByApplicationId(Long applicationId) {
        return documentRepository.countByApplicationId(UUID.fromString(applicationId.toString()));
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public boolean validateDocumentMetadata(DocumentRequestDTO documentRequest) {
        logger.debug("Validating document metadata");
        
        if (documentRequest == null) {
            return false;
        }
        
        // Check required fields
        if (documentRequest.getApplicationId() == null || documentRequest.getType() == null) {
            return false;
        }
        
        // Validate classification if provided
        if (documentRequest.getClassification() != null && 
                !DocumentClassification.isValid(documentRequest.getClassification())) {
            return false;
        }
        
        // Validate confidence score if provided
        if (documentRequest.getClassificationConfidence() != null && 
                (documentRequest.getClassificationConfidence() < 0 || 
                 documentRequest.getClassificationConfidence() > 1)) {
            return false;
        }
        
        return true;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public DocumentResponseDTO processDocumentForExtraction(Long documentId) {
        logger.info("Processing document for extraction: {}", documentId);
        
        Document document = documentRepository.findById(UUID.fromString(documentId.toString()))
                .orElseThrow(() -> new DocumentNotFoundException("Document not found with ID: " + documentId));
        
        // In a real implementation, this would trigger OCR processing via RabbitMQ
        // For now, we'll just update the metadata to indicate processing has started
        Map<String, Object> metadata = document.getMetadata();
        metadata.put("processingStarted", LocalDateTime.now().toString());
        metadata.put("processingStatus", "IN_PROGRESS");
        document.setMetadata(metadata);
        
        // Save updated document
        Document updatedDocument = documentRepository.save(document);
        
        // Generate a secure URL for document access
        URL secureUrl = generateSignedUrl(updatedDocument.getStoragePath(), defaultUrlExpirationMinutes);
        LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
        
        return new DocumentResponseDTO.Builder(updatedDocument)
                .withDownloadUrl(secureUrl.toString())
                .withUrlExpiresAt(urlExpiresAt)
                .build();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public Page<DocumentResponseDTO> getDocumentsRequiringReview(Double confidenceThreshold, Pageable pageable) {
        logger.debug("Retrieving documents requiring review with confidence threshold: {}", confidenceThreshold);
        
        // Find documents with confidence score below threshold
        Page<Document> documentPage = documentRepository.findByConfidenceScoreLessThan(confidenceThreshold, pageable);
        
        return documentPage.map(document -> {
            // Generate a secure URL for document access
            URL secureUrl = generateSignedUrl(document.getStoragePath(), defaultUrlExpirationMinutes);
            LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
            
            return new DocumentResponseDTO.Builder(document)
                    .withDownloadUrl(secureUrl.toString())
                    .withUrlExpiresAt(urlExpiresAt)
                    .build();
        });
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public DocumentResponseDTO markDocumentAsReviewed(Long documentId, Long reviewerId, boolean approved, 
                                                   String comments) {
        logger.info("Marking document ID: {} as reviewed by reviewer ID: {}", documentId, reviewerId);
        
        Document document = documentRepository.findById(UUID.fromString(documentId.toString()))
                .orElseThrow(() -> new DocumentNotFoundException("Document not found with ID: " + documentId));
        
        // Update document metadata with review information
        Map<String, Object> metadata = document.getMetadata();
        Map<String, Object> reviewInfo = new HashMap<>();
        reviewInfo.put("reviewerId", reviewerId);
        reviewInfo.put("reviewDate", LocalDateTime.now().toString());
        reviewInfo.put("approved", approved);
        reviewInfo.put("comments", comments);
        
        // Add review info to metadata
        metadata.put("review", reviewInfo);
        document.setMetadata(metadata);
        
        // Update classification based on review result
        if (approved) {
            document.setClassification(DocumentClassification.VERIFIED);
        } else {
            document.setClassification(DocumentClassification.REJECTED);
        }
        
        // Save updated document
        Document updatedDocument = documentRepository.save(document);
        
        // Generate a secure URL for document access
        URL secureUrl = generateSignedUrl(updatedDocument.getStoragePath(), defaultUrlExpirationMinutes);
        LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
        
        return new DocumentResponseDTO.Builder(updatedDocument)
                .withDownloadUrl(secureUrl.toString())
                .withUrlExpiresAt(urlExpiresAt)
                .build();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional(readOnly = true)
    public List<DocumentResponseDTO> getDocumentVersions(Long documentId) {
        logger.debug("Retrieving versions for document ID: {}", documentId);
        
        Document document = documentRepository.findById(UUID.fromString(documentId.toString()))
                .orElseThrow(() -> new DocumentNotFoundException("Document not found with ID: " + documentId));
        
        // In a real implementation, this would retrieve version history from S3
        // For now, we'll return a list with just the current version
        List<DocumentResponseDTO> versions = new ArrayList<>();
        
        // Generate a secure URL for document access
        URL secureUrl = generateSignedUrl(document.getStoragePath(), defaultUrlExpirationMinutes);
        LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
        
        versions.add(new DocumentResponseDTO.Builder(document)
                .withDownloadUrl(secureUrl.toString())
                .withUrlExpiresAt(urlExpiresAt)
                .build());
        
        return versions;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @Transactional
    public DocumentResponseDTO createDocumentVersion(Long documentId, MultipartFile file, 
                                                  DocumentRequestDTO documentRequest) {
        logger.info("Creating new version for document ID: {}", documentId);
        
        Document originalDocument = documentRepository.findById(UUID.fromString(documentId.toString()))
                .orElseThrow(() -> new DocumentNotFoundException("Document not found with ID: " + documentId));
        
        if (file == null || file.isEmpty()) {
            throw new InvalidDocumentException("Document file is empty or null");
        }
        
        try {
            // Generate a unique storage path for the new version
            String fileName = generateUniqueFileName(file.getOriginalFilename());
            String storagePath = generateStoragePath(originalDocument.getApplicationId(), fileName);
            
            // Upload the document to S3 with AES-256 encryption (handled by S3Config)
            uploadToS3(file.getInputStream(), storagePath, file.getContentType(), file.getSize());
            
            // Create document metadata entity for the new version
            Document document = new Document();
            document.setApplicationId(originalDocument.getApplicationId());
            document.setType(originalDocument.getType());
            document.setStoragePath(storagePath);
            document.setUploadedAt(LocalDateTime.now());
            document.setClassification(DocumentClassification.UNCLASSIFIED);
            
            // Add metadata from request if provided, otherwise use original document metadata
            Map<String, Object> metadata = documentRequest.hasMetadata() ? 
                    new HashMap<>(documentRequest.getMetadata()) : new HashMap<>(originalDocument.getMetadata());
            
            // Add version information to metadata
            metadata.put("originalFilename", file.getOriginalFilename());
            metadata.put("contentType", file.getContentType());
            metadata.put("fileSize", file.getSize());
            metadata.put("previousVersionId", originalDocument.getId().toString());
            metadata.put("versionCreatedAt", LocalDateTime.now().toString());
            
            document.setMetadata(metadata);
            
            // Save document metadata to database
            Document savedDocument = documentRepository.save(document);
            logger.debug("New document version saved with ID: {}", savedDocument.getId());
            
            // Generate a secure URL for document access
            URL secureUrl = generateSignedUrl(savedDocument.getStoragePath(), defaultUrlExpirationMinutes);
            LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
            
            return new DocumentResponseDTO.Builder(savedDocument)
                    .withDownloadUrl(secureUrl.toString())
                    .withUrlExpiresAt(urlExpiresAt)
                    .build();
            
        } catch (IOException e) {
            logger.error("Failed to create document version: {}", e.getMessage(), e);
            throw new DocumentStorageException("Failed to create document version: " + e.getMessage(), e);
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public DocumentResponseDTO convertToDTO(Document document) {
        if (document == null) {
            return null;
        }
        
        // Generate a secure URL for document access
        URL secureUrl = generateSignedUrl(document.getStoragePath(), defaultUrlExpirationMinutes);
        LocalDateTime urlExpiresAt = LocalDateTime.now().plusMinutes(defaultUrlExpirationMinutes);
        
        return new DocumentResponseDTO.Builder(document)
                .withDownloadUrl(secureUrl.toString())
                .withUrlExpiresAt(urlExpiresAt)
                .build();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public Document convertToEntity(DocumentRequestDTO documentRequest) {
        if (documentRequest == null) {
            return null;
        }
        
        Document document = new Document();
        document.setApplicationId(documentRequest.getApplicationId());
        document.setType(documentRequest.getType());
        
        if (documentRequest.getClassification() != null) {
            document.setClassification(DocumentClassification.fromString(documentRequest.getClassification()));
        } else {
            document.setClassification(DocumentClassification.UNCLASSIFIED);
        }
        
        if (documentRequest.hasMetadata()) {
            document.setMetadata(documentRequest.getMetadata());
        }
        
        if (documentRequest.getClassificationConfidence() != null) {
            document.setConfidenceScore(documentRequest.getClassificationConfidence());
        }
        
        return document;
    }
    
    /**
     * Generates a unique file name for a document.
     * 
     * @param originalFilename The original file name
     * @return A unique file name
     */
    private String generateUniqueFileName(String originalFilename) {
        String timestamp = String.valueOf(System.currentTimeMillis());
        String uuid = UUID.randomUUID().toString().substring(0, 8);
        
        if (originalFilename == null || originalFilename.isEmpty()) {
            return timestamp + "_" + uuid + ".bin";
        }
        
        int lastDotIndex = originalFilename.lastIndexOf('.');
        if (lastDotIndex > 0) {
            String name = originalFilename.substring(0, lastDotIndex);
            String extension = originalFilename.substring(lastDotIndex);
            return name + "_" + timestamp + "_" + uuid + extension;
        } else {
            return originalFilename + "_" + timestamp + "_" + uuid;
        }
    }
    
    /**
     * Generates a storage path for a document in S3.
     * 
     * @param applicationId The application ID
     * @param fileName The file name
     * @return A storage path in the format "documents/{applicationId}/{fileName}"
     */
    private String generateStoragePath(UUID applicationId, String fileName) {
        return storagePathPrefix + applicationId.toString() + "/" + fileName;
    }
    
    /**
     * Uploads a document to S3 with AES-256 encryption.
     * 
     * @param inputStream The document content as an input stream
     * @param storagePath The storage path in S3
     * @param contentType The content type of the document
     * @param contentLength The content length in bytes
     * @throws IOException If an I/O error occurs
     */
    private void uploadToS3(InputStream inputStream, String storagePath, String contentType, long contentLength) 
            throws IOException {
        try {
            // Prepare request
            PutObjectRequest request = PutObjectRequest.builder()
                    .bucket(s3Config.getBucketName())
                    .key(storagePath)
                    .contentType(contentType)
                    .build();
            
            // Upload to S3 (AES-256 encryption is handled by S3Config)
            s3Client.putObject(request, RequestBody.fromInputStream(inputStream, contentLength));
            
            // Cache content type for future reference
            contentTypeCache.put(storagePath, contentType);
            
            logger.debug("Document uploaded to S3: {}", storagePath);
        } catch (S3Exception e) {
            logger.error("S3 error uploading document: {}", e.getMessage(), e);
            throw new DocumentStorageException("Failed to upload document to S3: " + e.getMessage(), e);
        }
    }
    
    /**
     * Retrieves a document from S3.
     * 
     * @param storagePath The storage path in S3
     * @return The document content as an input stream
     */
    private InputStream getFromS3(String storagePath) {
        try {
            // Prepare request
            GetObjectRequest request = GetObjectRequest.builder()
                    .bucket(s3Config.getBucketName())
                    .key(storagePath)
                    .build();
            
            // Get from S3
            ResponseInputStream<GetObjectResponse> response = s3Client.getObject(request);
            
            // Cache content type for future reference
            contentTypeCache.put(storagePath, response.response().contentType());
            
            logger.debug("Document retrieved from S3: {}", storagePath);
            return response;
        } catch (S3Exception e) {
            logger.error("S3 error retrieving document: {}", e.getMessage(), e);
            throw new DocumentStorageException("Failed to retrieve document from S3: " + e.getMessage(), e);
        }
    }
    
    /**
     * Deletes a document from S3.
     * 
     * @param storagePath The storage path in S3
     */
    private void deleteFromS3(String storagePath) {
        try {
            // Prepare request
            DeleteObjectRequest request = DeleteObjectRequest.builder()
                    .bucket(s3Config.getBucketName())
                    .key(storagePath)
                    .build();
            
            // Delete from S3
            s3Client.deleteObject(request);
            
            // Remove from content type cache
            contentTypeCache.remove(storagePath);
            
            logger.debug("Document deleted from S3: {}", storagePath);
        } catch (S3Exception e) {
            logger.error("S3 error deleting document: {}", e.getMessage(), e);
            throw new DocumentStorageException("Failed to delete document from S3: " + e.getMessage(), e);
        }
    }
    
    /**
     * Generates a signed URL for accessing a document in S3.
     * 
     * @param storagePath The storage path in S3
     * @param expirationMinutes The URL expiration time in minutes
     * @return A pre-signed URL with a short expiration time
     */
    private URL generateSignedUrl(String storagePath, int expirationMinutes) {
        try {
            return s3Config.generateSignedUrl(storagePath);
        } catch (Exception e) {
            logger.error("Error generating signed URL: {}", e.getMessage(), e);
            throw new DocumentStorageException("Failed to generate signed URL: " + e.getMessage(), e);
        }
    }
    
    /**
     * Gets the content type of a document from cache or S3.
     * 
     * @param storagePath The storage path in S3
     * @return The content type of the document
     */
    private String getContentType(String storagePath) {
        // Check cache first
        String cachedContentType = contentTypeCache.get(storagePath);
        if (cachedContentType != null) {
            return cachedContentType;
        }
        
        try {
            // Get content type from S3
            HeadObjectRequest request = HeadObjectRequest.builder()
                    .bucket(s3Config.getBucketName())
                    .key(storagePath)
                    .build();
            
            HeadObjectResponse response = s3Client.headObject(request);
            String contentType = response.contentType();
            
            // Cache for future reference
            contentTypeCache.put(storagePath, contentType);
            
            return contentType;
        } catch (S3Exception e) {
            logger.error("S3 error getting content type: {}", e.getMessage(), e);
            throw new DocumentStorageException("Failed to get content type from S3: " + e.getMessage(), e);
        }
    }
}