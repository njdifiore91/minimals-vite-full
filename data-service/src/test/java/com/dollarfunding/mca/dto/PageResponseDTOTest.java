package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.when;

/**
 * Test class for {@link PageResponseDTO} that verifies the generic pagination structure,
 * JSON serialization/deserialization, and conversion from Spring Page objects.
 * 
 * Tests ensure that the DTO properly handles paginated data, includes appropriate metadata,
 * and supports different content types through type parameterization.
 */
public class PageResponseDTOTest {

    private ObjectMapper objectMapper;
    
    @BeforeEach
    void setUp() {
        // Configure ObjectMapper for testing
        objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
    }

    @Test
    @DisplayName("Should convert Spring Page to PageResponseDTO correctly")
    void shouldConvertPageToDTO() {
        // Given
        List<String> content = Arrays.asList("Item 1", "Item 2", "Item 3");
        Page<String> page = new PageImpl<>(content, PageRequest.of(0, 10), 25);
        String baseUrl = "/api/v1/applications";
        
        // When
        PageResponseDTO<String> responseDTO = PageResponseDTO.fromPage(page, baseUrl);
        
        // Then
        assertNotNull(responseDTO);
        assertEquals(content, responseDTO.getContent());
        assertNotNull(responseDTO.getMetadata());
        assertNotNull(responseDTO.getLinks());
        
        // Verify metadata
        assertEquals(25, responseDTO.getMetadata().getTotalElements());
        assertEquals(10, responseDTO.getMetadata().getPageSize());
        assertEquals(0, responseDTO.getMetadata().getCurrentPage());
        assertEquals(3, responseDTO.getMetadata().getTotalPages());
        
        // Verify links
        Map<String, String> links = responseDTO.getLinks();
        assertTrue(links.containsKey("first"));
        assertTrue(links.containsKey("next"));
        assertTrue(links.containsKey("last"));
        assertFalse(links.containsKey("prev"));
        assertEquals("/api/v1/applications?page=0&size=10", links.get("first"));
        assertEquals("/api/v1/applications?page=1&size=10", links.get("next"));
        assertEquals("/api/v1/applications?page=2&size=10", links.get("last"));
    }

    @Test
    @DisplayName("Should generate correct pagination links for middle page")
    void shouldGenerateCorrectLinksForMiddlePage() {
        // Given
        List<String> content = Arrays.asList("Item 11", "Item 12", "Item 13");
        Page<String> page = new PageImpl<>(content, PageRequest.of(1, 10), 35);
        String baseUrl = "/api/v1/applications";
        
        // When
        PageResponseDTO<String> responseDTO = PageResponseDTO.fromPage(page, baseUrl);
        
        // Then
        Map<String, String> links = responseDTO.getLinks();
        assertTrue(links.containsKey("first"));
        assertTrue(links.containsKey("prev"));
        assertTrue(links.containsKey("next"));
        assertTrue(links.containsKey("last"));
        assertEquals("/api/v1/applications?page=0&size=10", links.get("first"));
        assertEquals("/api/v1/applications?page=0&size=10", links.get("prev"));
        assertEquals("/api/v1/applications?page=2&size=10", links.get("next"));
        assertEquals("/api/v1/applications?page=3&size=10", links.get("last"));
    }

    @Test
    @DisplayName("Should generate correct pagination links for last page")
    void shouldGenerateCorrectLinksForLastPage() {
        // Given
        List<String> content = Arrays.asList("Item 21", "Item 22", "Item 23");
        Page<String> page = new PageImpl<>(content, PageRequest.of(2, 10), 23);
        String baseUrl = "/api/v1/applications";
        
        // When
        PageResponseDTO<String> responseDTO = PageResponseDTO.fromPage(page, baseUrl);
        
        // Then
        Map<String, String> links = responseDTO.getLinks();
        assertTrue(links.containsKey("first"));
        assertTrue(links.containsKey("prev"));
        assertFalse(links.containsKey("next"));
        assertTrue(links.containsKey("last"));
        assertEquals("/api/v1/applications?page=0&size=10", links.get("first"));
        assertEquals("/api/v1/applications?page=1&size=10", links.get("prev"));
        assertEquals("/api/v1/applications?page=2&size=10", links.get("last"));
    }

    @Test
    @DisplayName("Should handle empty page correctly")
    void shouldHandleEmptyPage() {
        // Given
        List<String> content = Collections.emptyList();
        Page<String> page = new PageImpl<>(content, PageRequest.of(0, 10), 0);
        String baseUrl = "/api/v1/applications";
        
        // When
        PageResponseDTO<String> responseDTO = PageResponseDTO.fromPage(page, baseUrl);
        
        // Then
        assertNotNull(responseDTO);
        assertTrue(responseDTO.getContent().isEmpty());
        assertEquals(0, responseDTO.getMetadata().getTotalElements());
        assertEquals(10, responseDTO.getMetadata().getPageSize());
        assertEquals(0, responseDTO.getMetadata().getCurrentPage());
        assertEquals(0, responseDTO.getMetadata().getTotalPages());
        
        // Verify links - should only have first link
        Map<String, String> links = responseDTO.getLinks();
        assertTrue(links.containsKey("first"));
        assertFalse(links.containsKey("prev"));
        assertFalse(links.containsKey("next"));
        assertFalse(links.containsKey("last"));
    }

    @Test
    @DisplayName("Should serialize and deserialize PageResponseDTO correctly")
    void shouldSerializeAndDeserializeCorrectly() throws IOException {
        // Given
        List<String> content = Arrays.asList("Item 1", "Item 2", "Item 3");
        PageResponseDTO.PageMetadata metadata = new PageResponseDTO.PageMetadata(25, 10, 0, 3);
        
        PageResponseDTO<String> responseDTO = new PageResponseDTO<>();
        responseDTO.setContent(content);
        responseDTO.setMetadata(metadata);
        
        Map<String, String> links = Map.of(
            "first", "/api/v1/applications?page=0&size=10",
            "next", "/api/v1/applications?page=1&size=10",
            "last", "/api/v1/applications?page=2&size=10"
        );
        responseDTO.setLinks(links);
        
        // When
        String json = objectMapper.writeValueAsString(responseDTO);
        PageResponseDTO<String> deserialized = objectMapper.readValue(json, 
                objectMapper.getTypeFactory().constructParametricType(PageResponseDTO.class, String.class));
        
        // Then
        assertNotNull(deserialized);
        assertEquals(content, deserialized.getContent());
        assertEquals(metadata.getTotalElements(), deserialized.getMetadata().getTotalElements());
        assertEquals(metadata.getPageSize(), deserialized.getMetadata().getPageSize());
        assertEquals(metadata.getCurrentPage(), deserialized.getMetadata().getCurrentPage());
        assertEquals(metadata.getTotalPages(), deserialized.getMetadata().getTotalPages());
        assertEquals(links, deserialized.getLinks());
        
        // Verify JSON structure
        assertTrue(json.contains("\"content\":"));
        assertTrue(json.contains("\"page_metadata\":"));
        assertTrue(json.contains("\"total_elements\":"));
        assertTrue(json.contains("\"page_size\":"));
        assertTrue(json.contains("\"current_page\":"));
        assertTrue(json.contains("\"total_pages\":"));
        assertTrue(json.contains("\"links\":"));
    }

    @Test
    @DisplayName("Should support type parameterization with different content types")
    void shouldSupportTypeParameterization() {
        // Given - Test with String content
        List<String> stringContent = Arrays.asList("Item 1", "Item 2");
        Page<String> stringPage = new PageImpl<>(stringContent, PageRequest.of(0, 10), 20);
        
        // When
        PageResponseDTO<String> stringResponseDTO = PageResponseDTO.fromPage(stringPage, "/api/strings");
        
        // Then
        assertNotNull(stringResponseDTO);
        assertEquals(stringContent, stringResponseDTO.getContent());
        
        // Given - Test with Integer content
        List<Integer> intContent = Arrays.asList(1, 2, 3);
        Page<Integer> intPage = new PageImpl<>(intContent, PageRequest.of(0, 10), 30);
        
        // When
        PageResponseDTO<Integer> intResponseDTO = PageResponseDTO.fromPage(intPage, "/api/integers");
        
        // Then
        assertNotNull(intResponseDTO);
        assertEquals(intContent, intResponseDTO.getContent());
        
        // Given - Test with custom object content
        TestDto dto1 = new TestDto(1, "Test 1");
        TestDto dto2 = new TestDto(2, "Test 2");
        List<TestDto> dtoContent = Arrays.asList(dto1, dto2);
        Page<TestDto> dtoPage = new PageImpl<>(dtoContent, PageRequest.of(0, 10), 20);
        
        // When
        PageResponseDTO<TestDto> dtoResponseDTO = PageResponseDTO.fromPage(dtoPage, "/api/dtos");
        
        // Then
        assertNotNull(dtoResponseDTO);
        assertEquals(dtoContent, dtoResponseDTO.getContent());
    }

    @Test
    @DisplayName("Should handle single page scenario correctly")
    void shouldHandleSinglePageScenario() {
        // Given
        List<String> content = Arrays.asList("Item 1", "Item 2", "Item 3");
        Page<String> page = new PageImpl<>(content, PageRequest.of(0, 10), 3);
        String baseUrl = "/api/v1/applications";
        
        // When
        PageResponseDTO<String> responseDTO = PageResponseDTO.fromPage(page, baseUrl);
        
        // Then
        assertNotNull(responseDTO);
        assertEquals(content, responseDTO.getContent());
        assertEquals(3, responseDTO.getMetadata().getTotalElements());
        assertEquals(10, responseDTO.getMetadata().getPageSize());
        assertEquals(0, responseDTO.getMetadata().getCurrentPage());
        assertEquals(1, responseDTO.getMetadata().getTotalPages());
        
        // Verify links - should have first and last links pointing to the same page
        Map<String, String> links = responseDTO.getLinks();
        assertTrue(links.containsKey("first"));
        assertFalse(links.containsKey("prev"));
        assertFalse(links.containsKey("next"));
        assertTrue(links.containsKey("last"));
        assertEquals("/api/v1/applications?page=0&size=10", links.get("first"));
        assertEquals("/api/v1/applications?page=0&size=10", links.get("last"));
    }

    @Test
    @DisplayName("Should create PageResponseDTO with constructor correctly")
    void shouldCreateWithConstructorCorrectly() {
        // Given
        List<String> content = Arrays.asList("Item 1", "Item 2");
        PageResponseDTO.PageMetadata metadata = new PageResponseDTO.PageMetadata(20, 10, 0, 2);
        Map<String, String> links = Map.of(
            "first", "/api/test?page=0&size=10",
            "last", "/api/test?page=1&size=10"
        );
        
        // When
        PageResponseDTO<String> responseDTO = new PageResponseDTO<>(content, metadata, links);
        
        // Then
        assertNotNull(responseDTO);
        assertEquals(content, responseDTO.getContent());
        assertEquals(metadata, responseDTO.getMetadata());
        assertEquals(links, responseDTO.getLinks());
    }

    @Test
    @DisplayName("Should create PageMetadata with constructor correctly")
    void shouldCreatePageMetadataWithConstructorCorrectly() {
        // Given
        long totalElements = 100;
        int pageSize = 10;
        int currentPage = 2;
        int totalPages = 10;
        
        // When
        PageResponseDTO.PageMetadata metadata = new PageResponseDTO.PageMetadata(totalElements, pageSize, currentPage, totalPages);
        
        // Then
        assertEquals(totalElements, metadata.getTotalElements());
        assertEquals(pageSize, metadata.getPageSize());
        assertEquals(currentPage, metadata.getCurrentPage());
        assertEquals(totalPages, metadata.getTotalPages());
    }

    /**
     * Test DTO class for type parameterization tests
     */
    static class TestDto {
        private int id;
        private String name;

        public TestDto() {
        }

        public TestDto(int id, String name) {
            this.id = id;
            this.name = name;
        }

        public int getId() {
            return id;
        }

        public void setId(int id) {
            this.id = id;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            TestDto testDto = (TestDto) o;
            return id == testDto.id && name.equals(testDto.name);
        }

        @Override
        public int hashCode() {
            return 31 * id + (name != null ? name.hashCode() : 0);
        }
    }
}