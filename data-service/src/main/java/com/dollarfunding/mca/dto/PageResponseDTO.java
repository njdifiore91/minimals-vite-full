package com.dollarfunding.mca.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import org.springframework.data.domain.Page;

import java.util.List;
import java.util.Map;
import java.util.HashMap;

/**
 * Generic DTO class for paginated responses.
 * <p>
 * This class provides a standardized structure for returning paginated data with metadata
 * about the total count, page size, current page, and total pages. It is parameterized to work
 * with any response DTO type and includes navigation links for pagination.
 * </p>
 * <p>
 * The class includes conversion methods from Spring Page objects to simplify controller
 * implementations and ensure consistent pagination responses across all endpoints.
 * </p>
 *
 * @param <T> The type of data being paginated
 */
public class PageResponseDTO<T> {

    @JsonProperty("content")
    private List<T> content;

    @JsonProperty("page_metadata")
    private PageMetadata metadata;

    @JsonProperty("links")
    private Map<String, String> links;

    /**
     * Default constructor for serialization frameworks.
     */
    public PageResponseDTO() {
    }

    /**
     * Constructs a PageResponseDTO with the specified content, metadata, and links.
     *
     * @param content  The list of items for the current page
     * @param metadata The pagination metadata
     * @param links    The navigation links for pagination
     */
    public PageResponseDTO(List<T> content, PageMetadata metadata, Map<String, String> links) {
        this.content = content;
        this.metadata = metadata;
        this.links = links;
    }

    /**
     * Creates a PageResponseDTO from a Spring Page object.
     *
     * @param page     The Spring Page object
     * @param baseUrl  The base URL for pagination links (e.g., "/api/v1/applications")
     * @param <U>      The type of data in the Page
     * @return A new PageResponseDTO instance
     */
    public static <U> PageResponseDTO<U> fromPage(Page<U> page, String baseUrl) {
        PageMetadata metadata = new PageMetadata(
                page.getTotalElements(),
                page.getSize(),
                page.getNumber(),
                page.getTotalPages()
        );

        Map<String, String> links = new HashMap<>();
        // First page link
        links.put("first", buildPageLink(baseUrl, 0, page.getSize()));
        
        // Previous page link (if not on first page)
        if (page.getNumber() > 0) {
            links.put("prev", buildPageLink(baseUrl, page.getNumber() - 1, page.getSize()));
        }
        
        // Next page link (if not on last page)
        if (page.getNumber() < page.getTotalPages() - 1) {
            links.put("next", buildPageLink(baseUrl, page.getNumber() + 1, page.getSize()));
        }
        
        // Last page link
        if (page.getTotalPages() > 0) {
            links.put("last", buildPageLink(baseUrl, page.getTotalPages() - 1, page.getSize()));
        }

        return new PageResponseDTO<>(page.getContent(), metadata, links);
    }

    /**
     * Builds a pagination link with the specified parameters.
     *
     * @param baseUrl  The base URL for the endpoint
     * @param page     The page number
     * @param size     The page size
     * @return The formatted pagination link
     */
    private static String buildPageLink(String baseUrl, int page, int size) {
        return String.format("%s?page=%d&size=%d", baseUrl, page, size);
    }

    /**
     * Gets the content of the current page.
     *
     * @return The list of items for the current page
     */
    public List<T> getContent() {
        return content;
    }

    /**
     * Sets the content of the current page.
     *
     * @param content The list of items for the current page
     */
    public void setContent(List<T> content) {
        this.content = content;
    }

    /**
     * Gets the pagination metadata.
     *
     * @return The pagination metadata
     */
    public PageMetadata getMetadata() {
        return metadata;
    }

    /**
     * Sets the pagination metadata.
     *
     * @param metadata The pagination metadata
     */
    public void setMetadata(PageMetadata metadata) {
        this.metadata = metadata;
    }

    /**
     * Gets the navigation links for pagination.
     *
     * @return The navigation links
     */
    public Map<String, String> getLinks() {
        return links;
    }

    /**
     * Sets the navigation links for pagination.
     *
     * @param links The navigation links
     */
    public void setLinks(Map<String, String> links) {
        this.links = links;
    }

    /**
     * Inner class representing pagination metadata.
     */
    public static class PageMetadata {
        @JsonProperty("total_elements")
        private long totalElements;

        @JsonProperty("page_size")
        private int pageSize;

        @JsonProperty("current_page")
        private int currentPage;

        @JsonProperty("total_pages")
        private int totalPages;

        /**
         * Default constructor for serialization frameworks.
         */
        public PageMetadata() {
        }

        /**
         * Constructs PageMetadata with the specified values.
         *
         * @param totalElements The total number of elements across all pages
         * @param pageSize      The number of elements per page
         * @param currentPage   The current page number (0-based)
         * @param totalPages    The total number of pages
         */
        public PageMetadata(long totalElements, int pageSize, int currentPage, int totalPages) {
            this.totalElements = totalElements;
            this.pageSize = pageSize;
            this.currentPage = currentPage;
            this.totalPages = totalPages;
        }

        /**
         * Gets the total number of elements across all pages.
         *
         * @return The total number of elements
         */
        public long getTotalElements() {
            return totalElements;
        }

        /**
         * Sets the total number of elements across all pages.
         *
         * @param totalElements The total number of elements
         */
        public void setTotalElements(long totalElements) {
            this.totalElements = totalElements;
        }

        /**
         * Gets the number of elements per page.
         *
         * @return The page size
         */
        public int getPageSize() {
            return pageSize;
        }

        /**
         * Sets the number of elements per page.
         *
         * @param pageSize The page size
         */
        public void setPageSize(int pageSize) {
            this.pageSize = pageSize;
        }

        /**
         * Gets the current page number (0-based).
         *
         * @return The current page number
         */
        public int getCurrentPage() {
            return currentPage;
        }

        /**
         * Sets the current page number.
         *
         * @param currentPage The current page number
         */
        public void setCurrentPage(int currentPage) {
            this.currentPage = currentPage;
        }

        /**
         * Gets the total number of pages.
         *
         * @return The total number of pages
         */
        public int getTotalPages() {
            return totalPages;
        }

        /**
         * Sets the total number of pages.
         *
         * @param totalPages The total number of pages
         */
        public void setTotalPages(int totalPages) {
            this.totalPages = totalPages;
        }
    }
}