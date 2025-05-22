package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.dto.ErrorResponseDTO;
import com.dollarfunding.mca.dto.PageResponseDTO;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.exception.ResourceNotFoundException;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.service.DocumentService;
import com.dollarfunding.mca.service.ValidationService;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.Resource;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.test.web.servlet.result.MockMvcResultMatchers;

import java.time.LocalDateTime;
import java.util.*;

import static org.hamcrest.Matchers.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Unit and integration tests for the DocumentController class that handles document operations
 * through the /api/v1/documents endpoint.
 * <p>
 * Tests verify document upload, download, classification, and metadata management functionality.
 * Includes tests for S3-compatible storage integration, role-based access control, document
 * association with applications, and proper validation of document data and formats.
 * </p>
 * <p>
 * Uses MockMvc to simulate HTTP requests and mock services to isolate the controller from
 * external dependencies.
 * </p>
 */
@WebMvcTest(DocumentController.class)
public class DocumentControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private DocumentService documentService;

    @MockBean
    private ValidationService validationService;

    private DocumentRequestDTO validDocumentRequest;
    private DocumentResponseDTO documentResponse;
    private UUID testDocumentId;
    private UUID testApplicationId;

    @BeforeEach
    void setUp() {
        testDocumentId = UUID.randomUUID();
        testApplicationId = UUID.randomUUID();

        // Create a valid document request
        validDocumentRequest = new DocumentRequestDTO();
        validDocumentRequest.setApplicationId(testApplicationId);
        validDocumentRequest.setType(DocumentType.BANK_STATEMENT);
        validDocumentRequest.setClassification("Monthly Bank Statement");
        validDocumentRequest.setOriginalFilename("bank_statement_jan_2023.pdf");
        validDocumentRequest.setContentType("application/pdf");

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("bankName", "First National Bank");
        metadata.put("accountNumber", "XXXX1234");
        metadata.put("statementDate", "2023-01-31");
        validDocumentRequest.setMetadata(metadata);

        Map<String, Double> confidenceScores = new HashMap<>();
        confidenceScores.put("classification", 0.95);
        confidenceScores.put("accountNumber", 0.89);
        confidenceScores.put("statementDate", 0.92);
        validDocumentRequest.setConfidenceScores(confidenceScores);

        // Create a document response
        Document document = new Document(testApplicationId, DocumentType.BANK_STATEMENT, "s3://mca-documents-production/applications/" + testApplicationId + "/bank_statement_jan_2023.pdf");
        document.setId(testDocumentId);
        document.setClassification("Monthly Bank Statement");
        document.setUploadedAt(LocalDateTime.now());
        document.setMetadata(metadata);

        documentResponse = new DocumentResponseDTO(document);
        documentResponse.setPresignedUrl("https://mca-documents-production.s3.amazonaws.com/applications/" + testApplicationId + "/bank_statement_jan_2023.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...");
        documentResponse.setConfidenceScores(confidenceScores);
    }

    @Test
    @DisplayName("Should upload document when user has OPERATIONS_STAFF role")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldUploadDocumentWhenUserHasOperationsStaffRole() throws Exception {
        // Given
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "bank_statement_jan_2023.pdf",
                "application/pdf",
                "PDF content".getBytes()
        );

        MockMultipartFile metadata = new MockMultipartFile(
                "metadata",
                "",
                "application/json",
                objectMapper.writeValueAsBytes(validDocumentRequest)
        );

        when(documentService.storeDocument(any(MockMultipartFile.class), any(DocumentRequestDTO.class)))
                .thenReturn(documentResponse);

        // When & Then
        mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                .file(file)
                .file(metadata)
                .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.applicationId").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.type").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$.classification").value("Monthly Bank Statement"))
                .andExpect(jsonPath("$.metadata.bankName").value("First National Bank"))
                .andExpect(jsonPath("$.confidenceScores.classification").value(0.95));

        // Verify that the service method was called with the correct parameters
        verify(validationService).validateDocumentData(any(DocumentRequestDTO.class), any(MockMultipartFile.class));
        verify(documentService).storeDocument(any(MockMultipartFile.class), any(DocumentRequestDTO.class));
    }

    @Test
    @DisplayName("Should upload document when user has SYSTEM_ADMIN role")
    @WithMockUser(roles = {RoleConstants.SYSTEM_ADMIN})
    void shouldUploadDocumentWhenUserHasSystemAdminRole() throws Exception {
        // Given
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "bank_statement_jan_2023.pdf",
                "application/pdf",
                "PDF content".getBytes()
        );

        MockMultipartFile metadata = new MockMultipartFile(
                "metadata",
                "",
                "application/json",
                objectMapper.writeValueAsBytes(validDocumentRequest)
        );

        when(documentService.storeDocument(any(MockMultipartFile.class), any(DocumentRequestDTO.class)))
                .thenReturn(documentResponse);

        // When & Then
        mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                .file(file)
                .file(metadata)
                .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.applicationId").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.type").value("BANK_STATEMENT"));

        // Verify that the service method was called with the correct parameters
        verify(validationService).validateDocumentData(any(DocumentRequestDTO.class), any(MockMultipartFile.class));
        verify(documentService).storeDocument(any(MockMultipartFile.class), any(DocumentRequestDTO.class));
    }

    @Test
    @DisplayName("Should return 403 when uploading document without required role")
    @WithMockUser(roles = {"GUEST"})
    void shouldReturn403WhenUploadingDocumentWithoutRequiredRole() throws Exception {
        // Given
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "bank_statement_jan_2023.pdf",
                "application/pdf",
                "PDF content".getBytes()
        );

        MockMultipartFile metadata = new MockMultipartFile(
                "metadata",
                "",
                "application/json",
                objectMapper.writeValueAsBytes(validDocumentRequest)
        );

        // When & Then
        mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                .file(file)
                .file(metadata)
                .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isForbidden());

        // Verify that the service methods were not called
        verify(validationService, never()).validateDocumentData(any(DocumentRequestDTO.class), any(MockMultipartFile.class));
        verify(documentService, never()).storeDocument(any(MockMultipartFile.class), any(DocumentRequestDTO.class));
    }

    @Test
    @DisplayName("Should return 400 when uploading document with invalid data")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldReturn400WhenUploadingDocumentWithInvalidData() throws Exception {
        // Given
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "bank_statement_jan_2023.pdf",
                "application/pdf",
                "PDF content".getBytes()
        );

        // Create an invalid document request (missing required fields)
        DocumentRequestDTO invalidRequest = new DocumentRequestDTO();
        // Missing applicationId and type

        MockMultipartFile metadata = new MockMultipartFile(
                "metadata",
                "",
                "application/json",
                objectMapper.writeValueAsBytes(invalidRequest)
        );

        // When & Then
        mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                .file(file)
                .file(metadata)
                .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.error").value("Bad Request"))
                .andExpect(jsonPath("$.validationErrors").exists());

        // Verify that the service methods were not called
        verify(documentService, never()).storeDocument(any(MockMultipartFile.class), any(DocumentRequestDTO.class));
    }

    @Test
    @DisplayName("Should return 400 when validation service throws ValidationException")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldReturn400WhenValidationServiceThrowsValidationException() throws Exception {
        // Given
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "bank_statement_jan_2023.pdf",
                "application/pdf",
                "PDF content".getBytes()
        );

        MockMultipartFile metadata = new MockMultipartFile(
                "metadata",
                "",
                "application/json",
                objectMapper.writeValueAsBytes(validDocumentRequest)
        );

        // Set up validation service to throw ValidationException
        Map<String, String> validationErrors = new HashMap<>();
        validationErrors.put("file", "File size exceeds maximum allowed size");
        doThrow(new ValidationException("Validation failed", validationErrors))
                .when(validationService).validateDocumentData(any(DocumentRequestDTO.class), any(MockMultipartFile.class));

        // When & Then
        mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                .file(file)
                .file(metadata)
                .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.error").value("Bad Request"))
                .andExpect(jsonPath("$.message").value("Validation failed"))
                .andExpect(jsonPath("$.validationErrors.file").value("File size exceeds maximum allowed size"));

        // Verify that the document service method was not called
        verify(documentService, never()).storeDocument(any(MockMultipartFile.class), any(DocumentRequestDTO.class));
    }

    @Test
    @DisplayName("Should get document by ID when user has OPERATIONS_STAFF role")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldGetDocumentByIdWhenUserHasOperationsStaffRole() throws Exception {
        // Given
        when(documentService.getDocumentById(eq(testDocumentId))).thenReturn(documentResponse);

        // When & Then
        mockMvc.perform(get("/api/v1/documents/{id}", testDocumentId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.applicationId").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.type").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$.classification").value("Monthly Bank Statement"))
                .andExpect(jsonPath("$.metadata.bankName").value("First National Bank"))
                .andExpect(jsonPath("$.confidenceScores.classification").value(0.95));

        // Verify that the service method was called with the correct parameters
        verify(documentService).getDocumentById(eq(testDocumentId));
    }

    @Test
    @DisplayName("Should return 404 when getting non-existent document")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldReturn404WhenGettingNonExistentDocument() throws Exception {
        // Given
        when(documentService.getDocumentById(eq(testDocumentId)))
                .thenThrow(new ResourceNotFoundException("Document", testDocumentId.toString()));

        // When & Then
        mockMvc.perform(get("/api/v1/documents/{id}", testDocumentId))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.error").value("Not Found"))
                .andExpect(jsonPath("$.message").value("Document with id " + testDocumentId + " not found"));

        // Verify that the service method was called with the correct parameters
        verify(documentService).getDocumentById(eq(testDocumentId));
    }

    @Test
    @DisplayName("Should download document content when user has OPERATIONS_STAFF role")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldDownloadDocumentContentWhenUserHasOperationsStaffRole() throws Exception {
        // Given
        byte[] documentContent = "PDF document content".getBytes();
        Resource resource = new ByteArrayResource(documentContent);
        Map<String, Object> contentResult = new HashMap<>();
        contentResult.put("resource", resource);
        contentResult.put("filename", "bank_statement_jan_2023.pdf");
        contentResult.put("contentType", "application/pdf");

        when(documentService.getDocumentContent(eq(testDocumentId))).thenReturn(contentResult);

        // When & Then
        mockMvc.perform(get("/api/v1/documents/{id}/content", testDocumentId))
                .andExpect(status().isOk())
                .andExpect(header().string(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"bank_statement_jan_2023.pdf\""))
                .andExpect(header().string(HttpHeaders.CONTENT_TYPE, "application/pdf"))
                .andExpect(content().bytes(documentContent));

        // Verify that the service method was called with the correct parameters
        verify(documentService).getDocumentContent(eq(testDocumentId));
    }

    @Test
    @DisplayName("Should return 404 when downloading content of non-existent document")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldReturn404WhenDownloadingContentOfNonExistentDocument() throws Exception {
        // Given
        when(documentService.getDocumentContent(eq(testDocumentId)))
                .thenThrow(new ResourceNotFoundException("Document", testDocumentId.toString()));

        // When & Then
        mockMvc.perform(get("/api/v1/documents/{id}/content", testDocumentId))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status").value(404))
                .andExpect(jsonPath("$.error").value("Not Found"))
                .andExpect(jsonPath("$.message").value("Document with id " + testDocumentId + " not found"));

        // Verify that the service method was called with the correct parameters
        verify(documentService).getDocumentContent(eq(testDocumentId));
    }

    @Test
    @DisplayName("Should get documents by application ID when user has OPERATIONS_STAFF role")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldGetDocumentsByApplicationIdWhenUserHasOperationsStaffRole() throws Exception {
        // Given
        List<DocumentResponseDTO> documents = Arrays.asList(documentResponse);
        Page<DocumentResponseDTO> page = new PageImpl<>(documents, PageRequest.of(0, 10), 1);

        when(documentService.getDocumentsByApplicationId(eq(testApplicationId), any(Pageable.class)))
                .thenReturn(page);

        // When & Then
        mockMvc.perform(get("/api/v1/documents/application/{applicationId}", testApplicationId)
                .param("page", "0")
                .param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content").isArray())
                .andExpect(jsonPath("$.content", hasSize(1)))
                .andExpect(jsonPath("$.content[0].id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.content[0].applicationId").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.content[0].type").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$.metadata.totalElements").value(1))
                .andExpect(jsonPath("$.metadata.totalPages").value(1))
                .andExpect(jsonPath("$.metadata.currentPage").value(0))
                .andExpect(jsonPath("$.metadata.pageSize").value(10));

        // Verify that the service method was called with the correct parameters
        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        verify(documentService).getDocumentsByApplicationId(eq(testApplicationId), pageableCaptor.capture());
        assertEquals(0, pageableCaptor.getValue().getPageNumber());
        assertEquals(10, pageableCaptor.getValue().getPageSize());
    }

    @Test
    @DisplayName("Should get documents by type when user has OPERATIONS_STAFF role")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldGetDocumentsByTypeWhenUserHasOperationsStaffRole() throws Exception {
        // Given
        List<DocumentResponseDTO> documents = Arrays.asList(documentResponse);
        Page<DocumentResponseDTO> page = new PageImpl<>(documents, PageRequest.of(0, 10), 1);

        when(documentService.getDocumentsByType(eq(DocumentType.BANK_STATEMENT), any(Pageable.class)))
                .thenReturn(page);

        // When & Then
        mockMvc.perform(get("/api/v1/documents/type/{type}", "BANK_STATEMENT")
                .param("page", "0")
                .param("size", "10"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content").isArray())
                .andExpect(jsonPath("$.content", hasSize(1)))
                .andExpect(jsonPath("$.content[0].id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.content[0].type").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$.metadata.totalElements").value(1))
                .andExpect(jsonPath("$.metadata.totalPages").value(1));

        // Verify that the service method was called with the correct parameters
        ArgumentCaptor<Pageable> pageableCaptor = ArgumentCaptor.forClass(Pageable.class);
        verify(documentService).getDocumentsByType(eq(DocumentType.BANK_STATEMENT), pageableCaptor.capture());
        assertEquals(0, pageableCaptor.getValue().getPageNumber());
        assertEquals(10, pageableCaptor.getValue().getPageSize());
    }

    @Test
    @DisplayName("Should update document metadata when user has OPERATIONS_STAFF role")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldUpdateDocumentMetadataWhenUserHasOperationsStaffRole() throws Exception {
        // Given
        DocumentRequestDTO updateRequest = new DocumentRequestDTO();
        updateRequest.setApplicationId(testApplicationId);
        updateRequest.setType(DocumentType.BANK_STATEMENT);
        updateRequest.setClassification("Updated Classification");

        Map<String, Object> updatedMetadata = new HashMap<>();
        updatedMetadata.put("bankName", "Updated Bank Name");
        updatedMetadata.put("accountNumber", "XXXX5678");
        updateRequest.setMetadata(updatedMetadata);

        DocumentResponseDTO updatedResponse = new DocumentResponseDTO(documentResponse);
        updatedResponse.setClassification("Updated Classification");
        updatedResponse.setMetadata(updatedMetadata);

        when(documentService.updateDocumentMetadata(eq(testDocumentId), any(DocumentRequestDTO.class)))
                .thenReturn(updatedResponse);

        // When & Then
        mockMvc.perform(put("/api/v1/documents/{id}", testDocumentId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updateRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.applicationId").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.type").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$.classification").value("Updated Classification"))
                .andExpect(jsonPath("$.metadata.bankName").value("Updated Bank Name"))
                .andExpect(jsonPath("$.metadata.accountNumber").value("XXXX5678"));

        // Verify that the service methods were called with the correct parameters
        verify(validationService).validateDocumentData(any(DocumentRequestDTO.class), eq(null));
        verify(documentService).updateDocumentMetadata(eq(testDocumentId), any(DocumentRequestDTO.class));
    }

    @Test
    @DisplayName("Should delete document when user has SYSTEM_ADMIN role")
    @WithMockUser(roles = {RoleConstants.SYSTEM_ADMIN})
    void shouldDeleteDocumentWhenUserHasSystemAdminRole() throws Exception {
        // Given
        doNothing().when(documentService).deleteDocument(eq(testDocumentId));

        // When & Then
        mockMvc.perform(delete("/api/v1/documents/{id}", testDocumentId))
                .andExpect(status().isNoContent());

        // Verify that the service method was called with the correct parameters
        verify(documentService).deleteDocument(eq(testDocumentId));
    }

    @Test
    @DisplayName("Should return 403 when deleting document without SYSTEM_ADMIN role")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldReturn403WhenDeletingDocumentWithoutSystemAdminRole() throws Exception {
        // When & Then
        mockMvc.perform(delete("/api/v1/documents/{id}", testDocumentId))
                .andExpect(status().isForbidden());

        // Verify that the service method was not called
        verify(documentService, never()).deleteDocument(any(UUID.class));
    }

    @Test
    @DisplayName("Should classify document when user has OPERATIONS_STAFF role")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldClassifyDocumentWhenUserHasOperationsStaffRole() throws Exception {
        // Given
        DocumentResponseDTO classifiedResponse = new DocumentResponseDTO(documentResponse);
        classifiedResponse.setClassification("Classified Bank Statement");

        Map<String, Double> updatedConfidenceScores = new HashMap<>(documentResponse.getConfidenceScores());
        updatedConfidenceScores.put("classification", 0.98);
        classifiedResponse.setConfidenceScores(updatedConfidenceScores);

        when(documentService.classifyDocument(eq(testDocumentId))).thenReturn(classifiedResponse);

        // When & Then
        mockMvc.perform(post("/api/v1/documents/{id}/classify", testDocumentId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.applicationId").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.type").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$.classification").value("Classified Bank Statement"))
                .andExpect(jsonPath("$.confidenceScores.classification").value(0.98));

        // Verify that the service method was called with the correct parameters
        verify(documentService).classifyDocument(eq(testDocumentId));
    }

    @Test
    @DisplayName("Should get document types")
    void shouldGetDocumentTypes() throws Exception {
        // Given
        List<Map<String, String>> documentTypes = Arrays.asList(
                Map.of("name", "BANK_STATEMENT", "description", "Bank Statement"),
                Map.of("name", "TAX_RETURN", "description", "Tax Return"),
                Map.of("name", "BUSINESS_LICENSE", "description", "Business License"),
                Map.of("name", "INVOICE", "description", "Invoice"),
                Map.of("name", "ID_VERIFICATION", "description", "Identity Verification"),
                Map.of("name", "MISCELLANEOUS", "description", "Miscellaneous")
        );

        when(documentService.getDocumentTypes()).thenReturn(documentTypes);

        // When & Then
        mockMvc.perform(get("/api/v1/documents/types"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$", hasSize(6)))
                .andExpect(jsonPath("$[0].name").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$[0].description").value("Bank Statement"))
                .andExpect(jsonPath("$[1].name").value("TAX_RETURN"))
                .andExpect(jsonPath("$[1].description").value("Tax Return"));

        // Verify that the service method was called
        verify(documentService).getDocumentTypes();
    }

    @Test
    @DisplayName("Should generate pre-signed URL when user has OPERATIONS_STAFF role")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldGeneratePresignedUrlWhenUserHasOperationsStaffRole() throws Exception {
        // Given
        Map<String, String> presignedUrlData = new HashMap<>();
        presignedUrlData.put("uploadId", "test-upload-id-123");
        presignedUrlData.put("presignedUrl", "https://mca-documents-production.s3.amazonaws.com/applications/" + testApplicationId + "/bank_statement_jan_2023.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...");

        when(documentService.generatePresignedUrl(any(DocumentRequestDTO.class))).thenReturn(presignedUrlData);

        // When & Then
        mockMvc.perform(post("/api/v1/documents/presigned-url")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(validDocumentRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.uploadId").value("test-upload-id-123"))
                .andExpect(jsonPath("$.presignedUrl").value(containsString("https://mca-documents-production.s3.amazonaws.com")));

        // Verify that the service methods were called with the correct parameters
        verify(validationService).validateDocumentData(any(DocumentRequestDTO.class), eq(null));
        verify(documentService).generatePresignedUrl(any(DocumentRequestDTO.class));
    }

    @Test
    @DisplayName("Should complete multipart upload when user has OPERATIONS_STAFF role")
    @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
    void shouldCompleteMultipartUploadWhenUserHasOperationsStaffRole() throws Exception {
        // Given
        String uploadId = "test-upload-id-123";

        when(documentService.completeMultipartUpload(eq(uploadId), any(DocumentRequestDTO.class)))
                .thenReturn(documentResponse);

        // When & Then
        mockMvc.perform(post("/api/v1/documents/complete-upload/{uploadId}", uploadId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(validDocumentRequest)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.applicationId").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.type").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$.classification").value("Monthly Bank Statement"));

        // Verify that the service method was called with the correct parameters
        verify(documentService).completeMultipartUpload(eq(uploadId), any(DocumentRequestDTO.class));
    }
}