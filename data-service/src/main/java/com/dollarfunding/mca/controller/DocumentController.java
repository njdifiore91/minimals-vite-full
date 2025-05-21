package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.dollarfunding.mca.dto.PageResponseDTO;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.service.DocumentService;
import com.dollarfunding.mca.service.ValidationService;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.Resource;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import javax.validation.Valid;
import javax.validation.constraints.NotNull;
import java.net.URI;
import java.util.List;
import java.util.Map;

/**
 * REST controller that handles document operations through the /api/v1/documents endpoint.
 * Provides functionality for document upload, download, classification, and metadata management.
 * Integrates with S3-compatible storage for document persistence and implements role-based access control.
 */
@RestController
@RequestMapping("/api/v1/documents")
@Validated
@Tag(name = "Documents", description = "API for document management operations")
public class DocumentController extends BaseController {

    private static final Logger logger = LoggerFactory.getLogger(DocumentController.class);

    private final DocumentService documentService;
    private final ValidationService validationService;

    @Autowired
    public DocumentController(DocumentService documentService, ValidationService validationService) {
        this.documentService = documentService;
        this.validationService = validationService;
    }

    /**
     * Upload a new document with metadata
     * 
     * @param file The document file to upload
     * @param documentRequestDTO Metadata for the document
     * @return ResponseEntity containing the uploaded document metadata
     */
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Upload a new document", description = "Uploads a document file with metadata and associates it with an application if specified")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "201", description = "Document uploaded successfully",
                    content = @Content(schema = @Schema(implementation = DocumentResponseDTO.class))),
        @ApiResponse(responseCode = "400", description = "Invalid request data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<DocumentResponseDTO> uploadDocument(
            @Parameter(description = "Document file to upload", required = true)
            @RequestPart("file") MultipartFile file,
            @Parameter(description = "Document metadata", required = true)
            @Valid @RequestPart("metadata") DocumentRequestDTO documentRequestDTO) {
        
        logger.info("Uploading document with type: {}", documentRequestDTO.getType());
        
        // Validate document data
        validationService.validateDocumentData(documentRequestDTO, file);
        
        // Upload document and save metadata
        DocumentResponseDTO uploadedDocument = documentService.storeDocument(file, documentRequestDTO);
        
        // Create URI for the new resource
        URI location = ServletUriComponentsBuilder
                .fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(uploadedDocument.getId())
                .toUri();
        
        return ResponseEntity.created(location).body(uploadedDocument);
    }

    /**
     * Get document by ID
     * 
     * @param id Document ID
     * @return ResponseEntity containing the document metadata
     */
    @GetMapping("/{id}")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Get document by ID", description = "Retrieves document metadata by its ID")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Document found",
                    content = @Content(schema = @Schema(implementation = DocumentResponseDTO.class))),
        @ApiResponse(responseCode = "404", description = "Document not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<DocumentResponseDTO> getDocumentById(
            @Parameter(description = "Document ID", required = true)
            @PathVariable("id") Long id) {
        
        logger.info("Retrieving document with ID: {}", id);
        DocumentResponseDTO document = documentService.getDocumentById(id);
        return ResponseEntity.ok(document);
    }

    /**
     * Download document content by ID
     * 
     * @param id Document ID
     * @return ResponseEntity containing the document content as a resource
     */
    @GetMapping("/{id}/content")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Download document content", description = "Downloads the actual document file content")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Document content retrieved successfully"),
        @ApiResponse(responseCode = "404", description = "Document not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<Resource> downloadDocument(
            @Parameter(description = "Document ID", required = true)
            @PathVariable("id") Long id) {
        
        logger.info("Downloading document content for ID: {}", id);
        
        // Get document content and metadata
        Map<String, Object> result = documentService.getDocumentContent(id);
        Resource resource = (Resource) result.get("resource");
        String filename = (String) result.get("filename");
        String contentType = (String) result.get("contentType");
        
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(contentType))
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .body(resource);
    }

    /**
     * Get documents by application ID
     * 
     * @param applicationId Application ID
     * @param pageable Pagination information
     * @return ResponseEntity containing a page of document metadata
     */
    @GetMapping("/application/{applicationId}")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Get documents by application ID", description = "Retrieves all documents associated with a specific application")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Documents retrieved successfully",
                    content = @Content(schema = @Schema(implementation = PageResponseDTO.class))),
        @ApiResponse(responseCode = "404", description = "Application not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<PageResponseDTO<DocumentResponseDTO>> getDocumentsByApplicationId(
            @Parameter(description = "Application ID", required = true)
            @PathVariable("applicationId") Long applicationId,
            @Parameter(description = "Pagination parameters")
            Pageable pageable) {
        
        logger.info("Retrieving documents for application ID: {}", applicationId);
        Page<DocumentResponseDTO> documents = documentService.getDocumentsByApplicationId(applicationId, pageable);
        PageResponseDTO<DocumentResponseDTO> response = new PageResponseDTO<>(documents);
        return ResponseEntity.ok(response);
    }

    /**
     * Get documents by type
     * 
     * @param type Document type
     * @param pageable Pagination information
     * @return ResponseEntity containing a page of document metadata
     */
    @GetMapping("/type/{type}")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Get documents by type", description = "Retrieves all documents of a specific type")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Documents retrieved successfully",
                    content = @Content(schema = @Schema(implementation = PageResponseDTO.class))),
        @ApiResponse(responseCode = "400", description = "Invalid document type",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<PageResponseDTO<DocumentResponseDTO>> getDocumentsByType(
            @Parameter(description = "Document type", required = true)
            @PathVariable("type") DocumentType type,
            @Parameter(description = "Pagination parameters")
            Pageable pageable) {
        
        logger.info("Retrieving documents of type: {}", type);
        Page<DocumentResponseDTO> documents = documentService.getDocumentsByType(type, pageable);
        PageResponseDTO<DocumentResponseDTO> response = new PageResponseDTO<>(documents);
        return ResponseEntity.ok(response);
    }

    /**
     * Update document metadata
     * 
     * @param id Document ID
     * @param documentRequestDTO Updated document metadata
     * @return ResponseEntity containing the updated document metadata
     */
    @PutMapping("/{id}")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Update document metadata", description = "Updates the metadata of an existing document")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Document metadata updated successfully",
                    content = @Content(schema = @Schema(implementation = DocumentResponseDTO.class))),
        @ApiResponse(responseCode = "400", description = "Invalid request data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "404", description = "Document not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<DocumentResponseDTO> updateDocumentMetadata(
            @Parameter(description = "Document ID", required = true)
            @PathVariable("id") Long id,
            @Parameter(description = "Updated document metadata", required = true)
            @Valid @RequestBody DocumentRequestDTO documentRequestDTO) {
        
        logger.info("Updating metadata for document ID: {}", id);
        
        // Validate document data
        validationService.validateDocumentData(documentRequestDTO, null);
        
        // Update document metadata
        DocumentResponseDTO updatedDocument = documentService.updateDocumentMetadata(id, documentRequestDTO);
        return ResponseEntity.ok(updatedDocument);
    }

    /**
     * Delete document by ID
     * 
     * @param id Document ID
     * @return ResponseEntity with no content
     */
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('" + RoleConstants.SYSTEM_ADMIN + "')")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(summary = "Delete document", description = "Deletes a document by its ID (System Admin only)")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "204", description = "Document deleted successfully"),
        @ApiResponse(responseCode = "404", description = "Document not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<Void> deleteDocument(
            @Parameter(description = "Document ID", required = true)
            @PathVariable("id") Long id) {
        
        logger.info("Deleting document with ID: {}", id);
        documentService.deleteDocument(id);
        return ResponseEntity.noContent().build();
    }

    /**
     * Classify document
     * 
     * @param id Document ID
     * @return ResponseEntity containing the classified document metadata
     */
    @PostMapping("/{id}/classify")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Classify document", description = "Triggers document classification for an existing document")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Document classified successfully",
                    content = @Content(schema = @Schema(implementation = DocumentResponseDTO.class))),
        @ApiResponse(responseCode = "404", description = "Document not found",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<DocumentResponseDTO> classifyDocument(
            @Parameter(description = "Document ID", required = true)
            @PathVariable("id") Long id) {
        
        logger.info("Classifying document with ID: {}", id);
        DocumentResponseDTO classifiedDocument = documentService.classifyDocument(id);
        return ResponseEntity.ok(classifiedDocument);
    }

    /**
     * Get document types
     * 
     * @return ResponseEntity containing a list of available document types
     */
    @GetMapping("/types")
    @Operation(summary = "Get document types", description = "Retrieves all available document types")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Document types retrieved successfully")
    })
    public ResponseEntity<List<Map<String, String>>> getDocumentTypes() {
        logger.info("Retrieving all document types");
        List<Map<String, String>> documentTypes = documentService.getDocumentTypes();
        return ResponseEntity.ok(documentTypes);
    }

    /**
     * Generate pre-signed URL for document upload
     * 
     * @param documentRequestDTO Document metadata
     * @return ResponseEntity containing the pre-signed URL and upload ID
     */
    @PostMapping("/presigned-url")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Generate pre-signed URL for document upload", 
               description = "Generates a pre-signed URL for direct document upload to S3 storage")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "200", description = "Pre-signed URL generated successfully"),
        @ApiResponse(responseCode = "400", description = "Invalid request data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<Map<String, String>> generatePresignedUrl(
            @Parameter(description = "Document metadata", required = true)
            @Valid @RequestBody DocumentRequestDTO documentRequestDTO) {
        
        logger.info("Generating pre-signed URL for document upload with type: {}", documentRequestDTO.getType());
        
        // Validate document data
        validationService.validateDocumentData(documentRequestDTO, null);
        
        // Generate pre-signed URL
        Map<String, String> presignedUrlData = documentService.generatePresignedUrl(documentRequestDTO);
        return ResponseEntity.ok(presignedUrlData);
    }

    /**
     * Complete multipart upload
     * 
     * @param uploadId Upload ID
     * @param documentRequestDTO Document metadata
     * @return ResponseEntity containing the uploaded document metadata
     */
    @PostMapping("/complete-upload/{uploadId}")
    @PreAuthorize("hasAnyRole('" + RoleConstants.OPERATIONS_STAFF + "','" + RoleConstants.SYSTEM_ADMIN + "')")
    @Operation(summary = "Complete multipart upload", 
               description = "Completes a multipart upload initiated with a pre-signed URL")
    @ApiResponses(value = {
        @ApiResponse(responseCode = "201", description = "Upload completed successfully",
                    content = @Content(schema = @Schema(implementation = DocumentResponseDTO.class))),
        @ApiResponse(responseCode = "400", description = "Invalid request data",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "401", description = "Unauthorized",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class))),
        @ApiResponse(responseCode = "403", description = "Forbidden",
                    content = @Content(schema = @Schema(implementation = ErrorResponseDTO.class)))
    })
    public ResponseEntity<DocumentResponseDTO> completeMultipartUpload(
            @Parameter(description = "Upload ID", required = true)
            @PathVariable("uploadId") String uploadId,
            @Parameter(description = "Document metadata", required = true)
            @Valid @RequestBody DocumentRequestDTO documentRequestDTO) {
        
        logger.info("Completing multipart upload with ID: {}", uploadId);
        
        // Complete upload and save metadata
        DocumentResponseDTO uploadedDocument = documentService.completeMultipartUpload(uploadId, documentRequestDTO);
        
        // Create URI for the new resource
        URI location = ServletUriComponentsBuilder
                .fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(uploadedDocument.getId())
                .toUri();
        
        return ResponseEntity.created(location).body(uploadedDocument);
    }
}