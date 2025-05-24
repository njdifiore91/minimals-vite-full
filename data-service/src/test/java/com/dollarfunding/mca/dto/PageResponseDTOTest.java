package com.dollarfunding.mca.dto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.util.Arrays;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Test class for {@link PageResponseDTO}.
 * 
 * Verifies the generic pagination structure, JSON serialization/deserialization,
 * and conversion from Spring Page objects.
 */
public class PageResponseDTOTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Test the creation of PageResponseDTO from a Spring Page object.
     */
    @Test
    public void testCreateFromPage() {
        // Arrange
        List<String> content = Arrays.asList("item1", "item2", "item3");
        Pageable pageable = PageRequest.of(0, 10);
        Page<String> page = new PageImpl<>(content, pageable, 30);

        // Act
        PageResponseDTO<String> response = PageResponseDTO.fromPage(page);

        // Assert
        assertNotNull(response);
        assertEquals(content, response.getContent());
        assertEquals(30, response.getTotalElements());
        assertEquals(3, response.getTotalPages());
        assertEquals(0, response.getPage());
        assertEquals(10, response.getSize());
    }

    /**
     * Test the pagination metadata calculation.
     */
    @Test
    public void testPaginationMetadata() {
        // Arrange
        List<String> content = Arrays.asList("item1", "item2", "item3");
        Pageable pageable = PageRequest.of(1, 3);
        Page<String> page = new PageImpl<>(content, pageable, 10);

        // Act
        PageResponseDTO<String> response = PageResponseDTO.fromPage(page);

        // Assert
        assertEquals(10, response.getTotalElements());
        assertEquals(4, response.getTotalPages());
        assertEquals(1, response.getPage());
        assertEquals(3, response.getSize());
        assertEquals(content.size(), response.getNumberOfElements());
        assertTrue(response.isHasContent());
        assertTrue(response.isHasNext());
        assertTrue(response.isHasPrevious());
    }

    /**
     * Test the navigation link generation.
     */
    @Test
    public void testNavigationLinks() {
        // Arrange
        List<String> content = Arrays.asList("item1", "item2", "item3");
        Pageable pageable = PageRequest.of(1, 3);
        Page<String> page = new PageImpl<>(content, pageable, 10);
        String baseUrl = "/api/v1/applications";

        // Act
        PageResponseDTO<String> response = PageResponseDTO.fromPage(page, baseUrl);

        // Assert
        assertNotNull(response.getLinks());
        assertEquals("/api/v1/applications?page=0&size=3", response.getLinks().getFirst());
        assertEquals("/api/v1/applications?page=0&size=3", response.getLinks().getPrev());
        assertEquals("/api/v1/applications?page=2&size=3", response.getLinks().getNext());
        assertEquals("/api/v1/applications?page=3&size=3", response.getLinks().getLast());
    }

    /**
     * Test the JSON serialization and deserialization.
     */
    @Test
    public void testJsonSerialization() throws Exception {
        // Arrange
        List<String> content = Arrays.asList("item1", "item2", "item3");
        Pageable pageable = PageRequest.of(0, 10);
        Page<String> page = new PageImpl<>(content, pageable, 30);
        PageResponseDTO<String> response = PageResponseDTO.fromPage(page);

        // Act
        String json = objectMapper.writeValueAsString(response);
        PageResponseDTO<?> deserialized = objectMapper.readValue(json, PageResponseDTO.class);

        // Assert
        assertNotNull(deserialized);
        assertEquals(response.getTotalElements(), deserialized.getTotalElements());
        assertEquals(response.getTotalPages(), deserialized.getTotalPages());
        assertEquals(response.getPage(), deserialized.getPage());
        assertEquals(response.getSize(), deserialized.getSize());
    }

    /**
     * Test the type parameterization with different content types.
     */
    @Test
    public void testTypeParameterization() {
        // Arrange - Test with String content
        List<String> stringContent = Arrays.asList("item1", "item2");
        Pageable pageable = PageRequest.of(0, 10);
        Page<String> stringPage = new PageImpl<>(stringContent, pageable, 20);
        
        // Act
        PageResponseDTO<String> stringResponse = PageResponseDTO.fromPage(stringPage);
        
        // Assert
        assertEquals(String.class, stringResponse.getContent().get(0).getClass());
        
        // Arrange - Test with Integer content
        List<Integer> intContent = Arrays.asList(1, 2, 3);
        Page<Integer> intPage = new PageImpl<>(intContent, pageable, 30);
        
        // Act
        PageResponseDTO<Integer> intResponse = PageResponseDTO.fromPage(intPage);
        
        // Assert
        assertEquals(Integer.class, intResponse.getContent().get(0).getClass());
        
        // Arrange - Test with custom DTO content
        TestDTO dto1 = new TestDTO("test1", 1);
        TestDTO dto2 = new TestDTO("test2", 2);
        List<TestDTO> dtoContent = Arrays.asList(dto1, dto2);
        Page<TestDTO> dtoPage = new PageImpl<>(dtoContent, pageable, 10);
        
        // Act
        PageResponseDTO<TestDTO> dtoResponse = PageResponseDTO.fromPage(dtoPage);
        
        // Assert
        assertEquals(TestDTO.class, dtoResponse.getContent().get(0).getClass());
        assertEquals("test1", dtoResponse.getContent().get(0).getName());
        assertEquals(1, dtoResponse.getContent().get(0).getValue());
    }
    
    /**
     * Test the empty page handling.
     */
    @Test
    public void testEmptyPage() {
        // Arrange
        List<String> content = Arrays.asList();
        Pageable pageable = PageRequest.of(0, 10);
        Page<String> page = new PageImpl<>(content, pageable, 0);

        // Act
        PageResponseDTO<String> response = PageResponseDTO.fromPage(page);

        // Assert
        assertNotNull(response);
        assertTrue(response.getContent().isEmpty());
        assertEquals(0, response.getTotalElements());
        assertEquals(0, response.getTotalPages());
        assertEquals(0, response.getPage());
        assertEquals(10, response.getSize());
        assertEquals(0, response.getNumberOfElements());
        assertEquals(false, response.isHasContent());
        assertEquals(false, response.isHasNext());
        assertEquals(false, response.isHasPrevious());
    }
    
    /**
     * Test DTO class for type parameterization tests.
     */
    static class TestDTO {
        private String name;
        private int value;
        
        public TestDTO() {
        }
        
        public TestDTO(String name, int value) {
            this.name = name;
            this.value = value;
        }
        
        public String getName() {
            return name;
        }
        
        public void setName(String name) {
            this.name = name;
        }
        
        public int getValue() {
            return value;
        }
        
        public void setValue(int value) {
            this.value = value;
        }
    }
}