package com.dollarfunding.mca.controller;

import com.dollarfunding.mca.dto.DocumentRequestDTO;
import com.dollarfunding.mca.dto.DocumentResponseDTO;
import com.dollarfunding.mca.dto.PageResponseDTO;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.service.DocumentService;
import com.dollarfunding.mca.service.ValidationService;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.Resource;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.*;

import static org.hamcrest.Matchers.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Unit and integration tests for the DocumentController class.
 * 
 * These tests verify document upload, download, classification, and metadata management functionality.
 * They also test S3-compatible storage integration, role-based access control, document association with
 * applications, and proper validation of document data and formats.
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

    private UUID testDocumentId;
    private UUID testApplicationId;
    private DocumentRequestDTO testDocumentRequest;
    private DocumentResponseDTO testDocumentResponse;
    private MockMultipartFile testFile;

    @BeforeEach
    void setUp() {
        // Initialize test data
        testDocumentId = UUID.randomUUID();
        testApplicationId = UUID.randomUUID();
        
        // Create test document request
        testDocumentRequest = new DocumentRequestDTO();
        testDocumentRequest.setApplicationId(testApplicationId);
        testDocumentRequest.setType(DocumentType.BANK_STATEMENT);
        testDocumentRequest.setClassification("Bank Statement");
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("accountNumber", "XXXX1234");
        metadata.put("bankName", "Test Bank");
        testDocumentRequest.setMetadata(metadata);
        testDocumentRequest.setFilename("test-bank-statement.pdf");
        testDocumentRequest.setContentType("application/pdf");
        testDocumentRequest.setContainsPii(true);
        testDocumentRequest.setIsFinancial(true);
        
        // Create test document response
        testDocumentResponse = new DocumentResponseDTO();
        testDocumentResponse.setId(testDocumentId);
        testDocumentResponse.setApplicationId(testApplicationId);
        testDocumentResponse.setType("BANK_STATEMENT");
        testDocumentResponse.setStoragePath("applications/" + testApplicationId + "/documents/" + testDocumentId);
        testDocumentResponse.setClassification("Bank Statement");
        testDocumentResponse.setUploadedAt(LocalDateTime.now());
        testDocumentResponse.setMetadata(metadata);
        testDocumentResponse.setDownloadUrl("https://s3.example.com/documents/" + testDocumentId);
        testDocumentResponse.setUrlExpiresAt(LocalDateTime.now().plusMinutes(15));
        testDocumentResponse.setClassificationConfidence(0.95);
        
        // Create test file
        byte[] fileContent = "Test PDF content".getBytes();
        testFile = new MockMultipartFile(
            "file", 
            "test-bank-statement.pdf", 
            "application/pdf", 
            fileContent
        );
    }

    @Nested
    @DisplayName("Document Upload Tests")
    class DocumentUploadTests {
        
        @Test
        @DisplayName("Should upload document successfully with operations staff role")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldUploadDocumentSuccessfullyWithOperationsStaffRole() throws Exception {
            // Given
            String metadataJson = objectMapper.writeValueAsString(testDocumentRequest);
            when(documentService.storeDocument(any(MultipartFile.class), any(DocumentRequestDTO.class)))
                .thenReturn(testDocumentResponse);
            
            // When & Then
            mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                    .file(testFile)
                    .file("metadata", metadataJson.getBytes())
                    .with(csrf())
                    .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.application_id").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.type").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$.classification").value("Bank Statement"))
                .andExpect(jsonPath("$.metadata.accountNumber").value("XXXX1234"))
                .andExpect(jsonPath("$.metadata.bankName").value("Test Bank"))
                .andExpect(jsonPath("$.download_url").exists())
                .andExpect(jsonPath("$.classification_confidence").value(0.95));
            
            // Verify service method was called with correct parameters
            ArgumentCaptor<MultipartFile> fileCaptor = ArgumentCaptor.forClass(MultipartFile.class);
            ArgumentCaptor<DocumentRequestDTO> dtoCaptor = ArgumentCaptor.forClass(DocumentRequestDTO.class);
            verify(documentService).storeDocument(fileCaptor.capture(), dtoCaptor.capture());
            
            assertEquals(testFile.getOriginalFilename(), fileCaptor.getValue().getOriginalFilename());
            assertEquals(testApplicationId, dtoCaptor.getValue().getApplicationId());
            assertEquals(DocumentType.BANK_STATEMENT, dtoCaptor.getValue().getType());
        }
        
        @Test
        @DisplayName("Should upload document successfully with system admin role")
        @WithMockUser(roles = {RoleConstants.SYSTEM_ADMIN})
        void shouldUploadDocumentSuccessfullyWithSystemAdminRole() throws Exception {
            // Given
            String metadataJson = objectMapper.writeValueAsString(testDocumentRequest);
            when(documentService.storeDocument(any(MultipartFile.class), any(DocumentRequestDTO.class)))
                .thenReturn(testDocumentResponse);
            
            // When & Then
            mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                    .file(testFile)
                    .file("metadata", metadataJson.getBytes())
                    .with(csrf())
                    .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").exists());
        }
        
        @Test
        @DisplayName("Should return 403 when user is not authenticated")
        void shouldReturn403WhenUserIsNotAuthenticated() throws Exception {
            // Given
            String metadataJson = objectMapper.writeValueAsString(testDocumentRequest);
            
            // When & Then
            mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                    .file(testFile)
                    .file("metadata", metadataJson.getBytes())
                    .with(csrf())
                    .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isForbidden());
            
            // Verify service method was not called
            verify(documentService, never()).storeDocument(any(), any());
        }
        
        @Test
        @DisplayName("Should validate document data before upload")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldValidateDocumentDataBeforeUpload() throws Exception {
            // Given
            String metadataJson = objectMapper.writeValueAsString(testDocumentRequest);
            doThrow(new IllegalArgumentException("Invalid document data"))
                .when(validationService).validateDocumentData(any(DocumentRequestDTO.class), any(MultipartFile.class));
            
            // When & Then
            mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                    .file(testFile)
                    .file("metadata", metadataJson.getBytes())
                    .with(csrf())
                    .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isBadRequest());
            
            // Verify validation was called but storage was not
            verify(validationService).validateDocumentData(any(DocumentRequestDTO.class), any(MultipartFile.class));
            verify(documentService, never()).storeDocument(any(), any());
        }
        
        @Test
        @DisplayName("Should handle missing file in upload request")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldHandleMissingFileInUploadRequest() throws Exception {
            // Given
            String metadataJson = objectMapper.writeValueAsString(testDocumentRequest);
            
            // When & Then
            mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                    .file("metadata", metadataJson.getBytes())
                    .with(csrf())
                    .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isBadRequest());
            
            // Verify service method was not called
            verify(documentService, never()).storeDocument(any(), any());
        }
        
        @Test
        @DisplayName("Should handle missing metadata in upload request")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldHandleMissingMetadataInUploadRequest() throws Exception {
            // When & Then
            mockMvc.perform(MockMvcRequestBuilders.multipart("/api/v1/documents")
                    .file(testFile)
                    .with(csrf())
                    .contentType(MediaType.MULTIPART_FORM_DATA_VALUE))
                .andExpect(status().isBadRequest());
            
            // Verify service method was not called
            verify(documentService, never()).storeDocument(any(), any());
        }
    }
    
    @Nested
    @DisplayName("Document Retrieval Tests")
    class DocumentRetrievalTests {
        
        @Test
        @DisplayName("Should get document by ID successfully")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldGetDocumentByIdSuccessfully() throws Exception {
            // Given
            when(documentService.getDocumentById(any(Long.class)))
                .thenReturn(testDocumentResponse);
            
            // When & Then
            mockMvc.perform(get("/api/v1/documents/1")
                    .with(csrf()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.application_id").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.type").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$.classification").value("Bank Statement"));
            
            // Verify service method was called with correct ID
            verify(documentService).getDocumentById(1L);
        }
        
        @Test
        @DisplayName("Should return 404 when document is not found")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldReturn404WhenDocumentIsNotFound() throws Exception {
            // Given
            when(documentService.getDocumentById(any(Long.class)))
                .thenThrow(new NoSuchElementException("Document not found"));
            
            // When & Then
            mockMvc.perform(get("/api/v1/documents/999")
                    .with(csrf()))
                .andExpect(status().isNotFound());
            
            // Verify service method was called
            verify(documentService).getDocumentById(999L);
        }
        
        @Test
        @DisplayName("Should download document content successfully")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldDownloadDocumentContentSuccessfully() throws Exception {
            // Given
            byte[] fileContent = "Test PDF content".getBytes();
            Resource resource = new ByteArrayResource(fileContent);
            Map<String, Object> contentResult = new HashMap<>();
            contentResult.put("resource", resource);
            contentResult.put("filename", "test-bank-statement.pdf");
            contentResult.put("contentType", "application/pdf");
            
            when(documentService.getDocumentContent(any(Long.class)))
                .thenReturn(contentResult);
            
            // When & Then
            mockMvc.perform(get("/api/v1/documents/1/content")
                    .with(csrf()))
                .andExpect(status().isOk())
                .andExpect(header().string(HttpHeaders.CONTENT_DISPOSITION, 
                        containsString("attachment; filename=\"test-bank-statement.pdf\"")))
                .andExpect(content().contentType(MediaType.APPLICATION_PDF))
                .andExpect(content().bytes(fileContent));
            
            // Verify service method was called
            verify(documentService).getDocumentContent(1L);
        }
        
        @Test
        @DisplayName("Should get documents by application ID successfully")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldGetDocumentsByApplicationIdSuccessfully() throws Exception {
            // Given
            List<DocumentResponseDTO> documents = Arrays.asList(testDocumentResponse);
            Page<DocumentResponseDTO> page = new PageImpl<>(documents);
            
            when(documentService.getDocumentsByApplicationId(any(Long.class), any(Pageable.class)))
                .thenReturn(page);
            
            // When & Then
            mockMvc.perform(get("/api/v1/documents/application/1")
                    .with(csrf()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content").isArray())
                .andExpect(jsonPath("$.content[0].id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.content[0].application_id").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.totalElements").value(1));
            
            // Verify service method was called
            verify(documentService).getDocumentsByApplicationId(eq(1L), any(Pageable.class));
        }
        
        @Test
        @DisplayName("Should get documents by type successfully")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldGetDocumentsByTypeSuccessfully() throws Exception {
            // Given
            List<DocumentResponseDTO> documents = Arrays.asList(testDocumentResponse);
            Page<DocumentResponseDTO> page = new PageImpl<>(documents);
            
            when(documentService.getDocumentsByType(any(DocumentType.class), any(Pageable.class)))
                .thenReturn(page);
            
            // When & Then
            mockMvc.perform(get("/api/v1/documents/type/BANK_STATEMENT")
                    .with(csrf()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content").isArray())
                .andExpect(jsonPath("$.content[0].id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.content[0].type").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$.totalElements").value(1));
            
            // Verify service method was called
            verify(documentService).getDocumentsByType(eq(DocumentType.BANK_STATEMENT), any(Pageable.class));
        }
        
        @Test
        @DisplayName("Should get document types successfully")
        void shouldGetDocumentTypesSuccessfully() throws Exception {
            // Given
            List<Map<String, String>> documentTypes = Arrays.asList(
                Map.of("code", "BANK_STATEMENT", "description", "Bank Statement"),
                Map.of("code", "TAX_RETURN", "description", "Tax Return")
            );
            
            when(documentService.getDocumentTypes()).thenReturn(documentTypes);
            
            // When & Then
            mockMvc.perform(get("/api/v1/documents/types")
                    .with(csrf()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$[0].code").value("BANK_STATEMENT"))
                .andExpect(jsonPath("$[0].description").value("Bank Statement"))
                .andExpect(jsonPath("$[1].code").value("TAX_RETURN"))
                .andExpect(jsonPath("$[1].description").value("Tax Return"));
            
            // Verify service method was called
            verify(documentService).getDocumentTypes();
        }
    }
    
    @Nested
    @DisplayName("Document Update Tests")
    class DocumentUpdateTests {
        
        @Test
        @DisplayName("Should update document metadata successfully")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldUpdateDocumentMetadataSuccessfully() throws Exception {
            // Given
            when(documentService.updateDocumentMetadata(any(Long.class), any(DocumentRequestDTO.class)))
                .thenReturn(testDocumentResponse);
            
            // When & Then
            mockMvc.perform(put("/api/v1/documents/1")
                    .with(csrf())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(testDocumentRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.application_id").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.type").value("BANK_STATEMENT"));
            
            // Verify service methods were called
            verify(validationService).validateDocumentData(any(DocumentRequestDTO.class), eq(null));
            verify(documentService).updateDocumentMetadata(eq(1L), any(DocumentRequestDTO.class));
        }
        
        @Test
        @DisplayName("Should return 404 when updating non-existent document")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldReturn404WhenUpdatingNonExistentDocument() throws Exception {
            // Given
            when(documentService.updateDocumentMetadata(any(Long.class), any(DocumentRequestDTO.class)))
                .thenThrow(new NoSuchElementException("Document not found"));
            
            // When & Then
            mockMvc.perform(put("/api/v1/documents/999")
                    .with(csrf())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(testDocumentRequest)))
                .andExpect(status().isNotFound());
            
            // Verify service method was called
            verify(documentService).updateDocumentMetadata(eq(999L), any(DocumentRequestDTO.class));
        }
        
        @Test
        @DisplayName("Should validate document data before update")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldValidateDocumentDataBeforeUpdate() throws Exception {
            // Given
            doThrow(new IllegalArgumentException("Invalid document data"))
                .when(validationService).validateDocumentData(any(DocumentRequestDTO.class), eq(null));
            
            // When & Then
            mockMvc.perform(put("/api/v1/documents/1")
                    .with(csrf())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(testDocumentRequest)))
                .andExpect(status().isBadRequest());
            
            // Verify validation was called but update was not
            verify(validationService).validateDocumentData(any(DocumentRequestDTO.class), eq(null));
            verify(documentService, never()).updateDocumentMetadata(anyLong(), any());
        }
    }
    
    @Nested
    @DisplayName("Document Classification Tests")
    class DocumentClassificationTests {
        
        @Test
        @DisplayName("Should classify document successfully")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldClassifyDocumentSuccessfully() throws Exception {
            // Given
            when(documentService.classifyDocument(any(Long.class)))
                .thenReturn(testDocumentResponse);
            
            // When & Then
            mockMvc.perform(post("/api/v1/documents/1/classify")
                    .with(csrf()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.classification").value("Bank Statement"))
                .andExpect(jsonPath("$.classification_confidence").value(0.95));
            
            // Verify service method was called
            verify(documentService).classifyDocument(1L);
        }
        
        @Test
        @DisplayName("Should return 404 when classifying non-existent document")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldReturn404WhenClassifyingNonExistentDocument() throws Exception {
            // Given
            when(documentService.classifyDocument(any(Long.class)))
                .thenThrow(new NoSuchElementException("Document not found"));
            
            // When & Then
            mockMvc.perform(post("/api/v1/documents/999/classify")
                    .with(csrf()))
                .andExpect(status().isNotFound());
            
            // Verify service method was called
            verify(documentService).classifyDocument(999L);
        }
    }
    
    @Nested
    @DisplayName("Document Deletion Tests")
    class DocumentDeletionTests {
        
        @Test
        @DisplayName("Should delete document successfully with system admin role")
        @WithMockUser(roles = {RoleConstants.SYSTEM_ADMIN})
        void shouldDeleteDocumentSuccessfullyWithSystemAdminRole() throws Exception {
            // Given
            doNothing().when(documentService).deleteDocument(any(Long.class));
            
            // When & Then
            mockMvc.perform(delete("/api/v1/documents/1")
                    .with(csrf()))
                .andExpect(status().isNoContent());
            
            // Verify service method was called
            verify(documentService).deleteDocument(1L);
        }
        
        @Test
        @DisplayName("Should return 403 when operations staff tries to delete document")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldReturn403WhenOperationsStaffTriesToDeleteDocument() throws Exception {
            // When & Then
            mockMvc.perform(delete("/api/v1/documents/1")
                    .with(csrf()))
                .andExpect(status().isForbidden());
            
            // Verify service method was not called
            verify(documentService, never()).deleteDocument(anyLong());
        }
        
        @Test
        @DisplayName("Should return 404 when deleting non-existent document")
        @WithMockUser(roles = {RoleConstants.SYSTEM_ADMIN})
        void shouldReturn404WhenDeletingNonExistentDocument() throws Exception {
            // Given
            doThrow(new NoSuchElementException("Document not found"))
                .when(documentService).deleteDocument(any(Long.class));
            
            // When & Then
            mockMvc.perform(delete("/api/v1/documents/999")
                    .with(csrf()))
                .andExpect(status().isNotFound());
            
            // Verify service method was called
            verify(documentService).deleteDocument(999L);
        }
    }
    
    @Nested
    @DisplayName("Presigned URL Tests")
    class PresignedUrlTests {
        
        @Test
        @DisplayName("Should generate presigned URL successfully")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldGeneratePresignedUrlSuccessfully() throws Exception {
            // Given
            Map<String, String> presignedUrlData = new HashMap<>();
            presignedUrlData.put("uploadUrl", "https://s3.example.com/upload/123");
            presignedUrlData.put("uploadId", "upload-123");
            presignedUrlData.put("expiresAt", "2023-12-31T23:59:59Z");
            
            when(documentService.generatePresignedUrl(any(DocumentRequestDTO.class)))
                .thenReturn(presignedUrlData);
            
            // When & Then
            mockMvc.perform(post("/api/v1/documents/presigned-url")
                    .with(csrf())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(testDocumentRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.uploadUrl").value("https://s3.example.com/upload/123"))
                .andExpect(jsonPath("$.uploadId").value("upload-123"))
                .andExpect(jsonPath("$.expiresAt").value("2023-12-31T23:59:59Z"));
            
            // Verify service methods were called
            verify(validationService).validateDocumentData(any(DocumentRequestDTO.class), eq(null));
            verify(documentService).generatePresignedUrl(any(DocumentRequestDTO.class));
        }
        
        @Test
        @DisplayName("Should validate document data before generating presigned URL")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldValidateDocumentDataBeforeGeneratingPresignedUrl() throws Exception {
            // Given
            doThrow(new IllegalArgumentException("Invalid document data"))
                .when(validationService).validateDocumentData(any(DocumentRequestDTO.class), eq(null));
            
            // When & Then
            mockMvc.perform(post("/api/v1/documents/presigned-url")
                    .with(csrf())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(testDocumentRequest)))
                .andExpect(status().isBadRequest());
            
            // Verify validation was called but generation was not
            verify(validationService).validateDocumentData(any(DocumentRequestDTO.class), eq(null));
            verify(documentService, never()).generatePresignedUrl(any());
        }
        
        @Test
        @DisplayName("Should complete multipart upload successfully")
        @WithMockUser(roles = {RoleConstants.OPERATIONS_STAFF})
        void shouldCompleteMultipartUploadSuccessfully() throws Exception {
            // Given
            when(documentService.completeMultipartUpload(anyString(), any(DocumentRequestDTO.class)))
                .thenReturn(testDocumentResponse);
            
            // When & Then
            mockMvc.perform(post("/api/v1/documents/complete-upload/upload-123")
                    .with(csrf())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(testDocumentRequest)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(testDocumentId.toString()))
                .andExpect(jsonPath("$.application_id").value(testApplicationId.toString()))
                .andExpect(jsonPath("$.type").value("BANK_STATEMENT"));
            
            // Verify service method was called
            verify(documentService).completeMultipartUpload(eq("upload-123"), any(DocumentRequestDTO.class));
        }
    }
}