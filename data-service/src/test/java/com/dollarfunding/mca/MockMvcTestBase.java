package com.dollarfunding.mca;

import com.dollarfunding.mca.security.JwtTokenProvider;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.security.UserPrincipal;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.ResultMatcher;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.test.web.servlet.result.MockMvcResultHandlers;
import org.springframework.test.web.servlet.result.MockMvcResultMatchers;

import java.io.UnsupportedEncodingException;
import java.util.Collections;
import java.util.List;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Abstract base class for controller tests using MockMvc.
 * <p>
 * This class provides common setup for Spring MVC tests, including MockMvc configuration,
 * authentication setup, and result verification helpers. It standardizes the approach to
 * testing REST controllers across the application, ensuring consistent test structure
 * and reducing boilerplate code.
 * <p>
 * Features:
 * - Configures MockMvc for testing Spring MVC controllers
 * - Provides authentication utilities for testing with different user roles
 * - Includes helpers for JSON serialization/deserialization
 * - Offers methods for request building and response validation
 * <p>
 * Usage:
 * Extend this class in your controller test classes and use the provided helper methods
 * to simplify test implementation. Override setup methods as needed for specific test requirements.
 */
@AutoConfigureMockMvc
public abstract class MockMvcTestBase {

    @Autowired
    protected MockMvc mockMvc;

    @Autowired
    protected ObjectMapper objectMapper;

    @MockBean
    protected JwtTokenProvider jwtTokenProvider;

    /**
     * Setup method that runs before each test.
     * Override this method in subclasses to add additional setup logic.
     */
    @BeforeEach
    public void setUp() {
        // Setup mock behavior for JWT token provider if needed
    }

    /**
     * Creates a UserPrincipal with the specified role for testing purposes.
     *
     * @param role The role to assign to the user principal
     * @return A UserPrincipal object with the specified role
     */
    protected UserPrincipal createUserPrincipal(String role) {
        return UserPrincipal.builder()
                .id(1L)
                .username("test-user")
                .email("test@dollarfunding.com")
                .authorities(Collections.singletonList(new SimpleGrantedAuthority(role)))
                .build();
    }

    /**
     * Creates a JWT token for testing purposes with the Operations Staff role.
     *
     * @return A JWT token string
     */
    protected String createOperationsStaffToken() {
        return createTokenWithRole(RoleConstants.ROLE_OPERATIONS_STAFF);
    }

    /**
     * Creates a JWT token for testing purposes with the System Admin role.
     *
     * @return A JWT token string
     */
    protected String createSystemAdminToken() {
        return createTokenWithRole(RoleConstants.ROLE_SYSTEM_ADMIN);
    }

    /**
     * Creates a JWT token for testing purposes with the specified role.
     *
     * @param role The role to include in the token
     * @return A JWT token string
     */
    protected String createTokenWithRole(String role) {
        UserPrincipal principal = createUserPrincipal(role);
        return jwtTokenProvider.generateToken(principal);
    }

    /**
     * Creates a JWT token for testing purposes with the specified roles.
     *
     * @param roles The roles to include in the token
     * @return A JWT token string
     */
    protected String createTokenWithRoles(List<String> roles) {
        UserPrincipal principal = UserPrincipal.builder()
                .id(1L)
                .username("test-user")
                .email("test@dollarfunding.com")
                .authorities(roles.stream()
                        .map(SimpleGrantedAuthority::new)
                        .toList())
                .build();
        return jwtTokenProvider.generateToken(principal);
    }

    /**
     * Creates an expired JWT token for testing error scenarios.
     *
     * @return An expired JWT token string
     */
    protected String createExpiredToken() {
        return jwtTokenProvider.generateTokenWithCustomExpiration(
                createUserPrincipal(RoleConstants.ROLE_OPERATIONS_STAFF),
                -3600 // Expired 1 hour ago
        );
    }

    /**
     * Builds a GET request with the specified URL and authentication token.
     *
     * @param url   The URL to send the request to
     * @param token The authentication token to include in the request
     * @return A configured MockHttpServletRequestBuilder
     */
    protected MockHttpServletRequestBuilder getRequest(String url, String token) {
        return MockMvcRequestBuilders.get(url)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON);
    }

    /**
     * Builds a POST request with the specified URL, request body, and authentication token.
     *
     * @param url         The URL to send the request to
     * @param requestBody The object to include as the request body
     * @param token       The authentication token to include in the request
     * @return A configured MockHttpServletRequestBuilder
     * @throws JsonProcessingException If the request body cannot be serialized to JSON
     */
    protected MockHttpServletRequestBuilder postRequest(String url, Object requestBody, String token) throws JsonProcessingException {
        return MockMvcRequestBuilders.post(url)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(requestBody));
    }

    /**
     * Builds a PUT request with the specified URL, request body, and authentication token.
     *
     * @param url         The URL to send the request to
     * @param requestBody The object to include as the request body
     * @param token       The authentication token to include in the request
     * @return A configured MockHttpServletRequestBuilder
     * @throws JsonProcessingException If the request body cannot be serialized to JSON
     */
    protected MockHttpServletRequestBuilder putRequest(String url, Object requestBody, String token) throws JsonProcessingException {
        return MockMvcRequestBuilders.put(url)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(requestBody));
    }

    /**
     * Builds a DELETE request with the specified URL and authentication token.
     *
     * @param url   The URL to send the request to
     * @param token The authentication token to include in the request
     * @return A configured MockHttpServletRequestBuilder
     */
    protected MockHttpServletRequestBuilder deleteRequest(String url, String token) {
        return MockMvcRequestBuilders.delete(url)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON);
    }

    /**
     * Performs a request and expects a successful response (HTTP 200 OK).
     *
     * @param requestBuilder The request builder to use
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performRequestAndExpectSuccess(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andDo(MockMvcResultHandlers.print())
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON));
    }

    /**
     * Performs a request and expects a created response (HTTP 201 Created).
     *
     * @param requestBuilder The request builder to use
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performRequestAndExpectCreated(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andDo(MockMvcResultHandlers.print())
                .andExpect(status().isCreated())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON));
    }

    /**
     * Performs a request and expects a no content response (HTTP 204 No Content).
     *
     * @param requestBuilder The request builder to use
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performRequestAndExpectNoContent(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andDo(MockMvcResultHandlers.print())
                .andExpect(status().isNoContent());
    }

    /**
     * Performs a request and expects a bad request response (HTTP 400 Bad Request).
     *
     * @param requestBuilder The request builder to use
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performRequestAndExpectBadRequest(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andDo(MockMvcResultHandlers.print())
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON));
    }

    /**
     * Performs a request and expects an unauthorized response (HTTP 401 Unauthorized).
     *
     * @param requestBuilder The request builder to use
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performRequestAndExpectUnauthorized(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andDo(MockMvcResultHandlers.print())
                .andExpect(status().isUnauthorized())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON));
    }

    /**
     * Performs a request and expects a forbidden response (HTTP 403 Forbidden).
     *
     * @param requestBuilder The request builder to use
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performRequestAndExpectForbidden(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andDo(MockMvcResultHandlers.print())
                .andExpect(status().isForbidden())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON));
    }

    /**
     * Performs a request and expects a not found response (HTTP 404 Not Found).
     *
     * @param requestBuilder The request builder to use
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performRequestAndExpectNotFound(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andDo(MockMvcResultHandlers.print())
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON));
    }

    /**
     * Performs a request and expects a specific status code.
     *
     * @param requestBuilder The request builder to use
     * @param statusMatcher  The status matcher to use
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performRequestAndExpectStatus(MockHttpServletRequestBuilder requestBuilder, ResultMatcher statusMatcher) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andDo(MockMvcResultHandlers.print())
                .andExpect(statusMatcher);
    }

    /**
     * Extracts the response body from an MVC result as a string.
     *
     * @param result The MVC result to extract the response body from
     * @return The response body as a string
     * @throws UnsupportedEncodingException If the response encoding is not supported
     */
    protected String getResponseBodyAsString(MvcResult result) throws UnsupportedEncodingException {
        return result.getResponse().getContentAsString();
    }

    /**
     * Extracts the response body from an MVC result and deserializes it to the specified type.
     *
     * @param result        The MVC result to extract the response body from
     * @param responseClass The class to deserialize the response body to
     * @param <T>           The type of the response
     * @return The deserialized response body
     * @throws Exception If an error occurs during deserialization
     */
    protected <T> T getResponseBodyAs(MvcResult result, Class<T> responseClass) throws Exception {
        String responseBody = getResponseBodyAsString(result);
        return objectMapper.readValue(responseBody, responseClass);
    }

    /**
     * Performs a request and returns the result.
     *
     * @param requestBuilder The request builder to use
     * @return The MVC result
     * @throws Exception If an error occurs during the request
     */
    protected MvcResult performRequest(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andDo(MockMvcResultHandlers.print())
                .andReturn();
    }

    /**
     * Expects that the JSON response contains a field with the specified value.
     *
     * @param fieldPath The JSON path to the field
     * @param value     The expected value
     * @return A ResultMatcher that checks for the field value
     */
    protected ResultMatcher jsonPath(String fieldPath, Object value) {
        return MockMvcResultMatchers.jsonPath(fieldPath).value(value);
    }

    /**
     * Expects that the JSON response contains a field.
     *
     * @param fieldPath The JSON path to the field
     * @return A ResultMatcher that checks for the field existence
     */
    protected ResultMatcher jsonPathExists(String fieldPath) {
        return MockMvcResultMatchers.jsonPath(fieldPath).exists();
    }

    /**
     * Expects that the JSON response does not contain a field.
     *
     * @param fieldPath The JSON path to the field
     * @return A ResultMatcher that checks for the field non-existence
     */
    protected ResultMatcher jsonPathDoesNotExist(String fieldPath) {
        return MockMvcResultMatchers.jsonPath(fieldPath).doesNotExist();
    }

    /**
     * Expects that the JSON response contains a field with a value that is not empty.
     *
     * @param fieldPath The JSON path to the field
     * @return A ResultMatcher that checks for a non-empty field value
     */
    protected ResultMatcher jsonPathIsNotEmpty(String fieldPath) {
        return MockMvcResultMatchers.jsonPath(fieldPath).isNotEmpty();
    }

    /**
     * Expects that the JSON response contains a field with an array of the specified size.
     *
     * @param fieldPath The JSON path to the array field
     * @param size      The expected array size
     * @return A ResultMatcher that checks the array size
     */
    protected ResultMatcher jsonPathArrayHasSize(String fieldPath, int size) {
        return MockMvcResultMatchers.jsonPath(fieldPath + ".length()").value(size);
    }
}