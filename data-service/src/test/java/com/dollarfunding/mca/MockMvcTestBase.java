package com.dollarfunding.mca;

import com.dollarfunding.mca.security.JwtTokenProvider;
import com.dollarfunding.mca.security.RoleConstants;
import com.dollarfunding.mca.security.UserPrincipal;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.ResultMatcher;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.test.web.servlet.result.MockMvcResultMatchers;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import java.io.UnsupportedEncodingException;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;

/**
 * Abstract base class for controller tests using MockMvc.
 * <p>
 * This class provides common setup for Spring MVC tests, including MockMvc configuration,
 * authentication setup, and result verification helpers. It standardizes the approach to
 * testing REST controllers across the application, ensuring consistent test structure
 * and reducing boilerplate code.
 * </p>
 */
public abstract class MockMvcTestBase {

    @Autowired
    protected WebApplicationContext webApplicationContext;

    @Autowired
    protected ObjectMapper objectMapper;

    @MockBean
    protected JwtTokenProvider jwtTokenProvider;

    protected MockMvc mockMvc;

    /**
     * Sets up MockMvc with Spring Security before each test.
     */
    @BeforeEach
    public void setup() {
        this.mockMvc = MockMvcBuilders
                .webAppContextSetup(webApplicationContext)
                .apply(springSecurity())
                .build();
    }

    /**
     * Authenticates the test context with Operations Staff role.
     * <p>
     * This method sets up the SecurityContext with an authenticated user having
     * the Operations Staff role, allowing tests to simulate requests from users
     * with this role.
     * </p>
     */
    protected void authenticateAsOperationsStaff() {
        authenticateWithRoles(RoleConstants.ROLE_OPERATIONS_STAFF);
    }

    /**
     * Authenticates the test context with System Admin role.
     * <p>
     * This method sets up the SecurityContext with an authenticated user having
     * the System Admin role, allowing tests to simulate requests from users
     * with this role.
     * </p>
     */
    protected void authenticateAsSystemAdmin() {
        authenticateWithRoles(RoleConstants.ROLE_SYSTEM_ADMIN);
    }

    /**
     * Authenticates the test context with the specified roles.
     * <p>
     * This method sets up the SecurityContext with an authenticated user having
     * the specified roles, allowing tests to simulate requests from users
     * with these roles.
     * </p>
     *
     * @param roles The roles to assign to the authenticated user
     */
    protected void authenticateWithRoles(String... roles) {
        List<SimpleGrantedAuthority> authorities = Arrays.stream(roles)
                .map(role -> new SimpleGrantedAuthority(role))
                .collect(Collectors.toList());

        UserPrincipal userPrincipal = UserPrincipal.builder()
                .id(1L)
                .username("testuser")
                .email("test@example.com")
                .authorities(authorities)
                .build();

        Authentication authentication = new UsernamePasswordAuthenticationToken(
                userPrincipal, null, authorities);

        SecurityContextHolder.getContext().setAuthentication(authentication);
    }

    /**
     * Clears the authentication context.
     * <p>
     * This method clears the SecurityContext, removing any authenticated user
     * and allowing tests to simulate requests from unauthenticated users.
     * </p>
     */
    protected void clearAuthentication() {
        SecurityContextHolder.clearContext();
    }

    /**
     * Creates a GET request builder for the specified URL.
     *
     * @param url The URL to send the GET request to
     * @return A MockHttpServletRequestBuilder for a GET request
     */
    protected MockHttpServletRequestBuilder get(String url) {
        return MockMvcRequestBuilders.get(url)
                .contentType(MediaType.APPLICATION_JSON);
    }

    /**
     * Creates a POST request builder for the specified URL with the given content.
     *
     * @param url     The URL to send the POST request to
     * @param content The content to include in the request body
     * @return A MockHttpServletRequestBuilder for a POST request
     */
    protected MockHttpServletRequestBuilder post(String url, Object content) {
        try {
            return MockMvcRequestBuilders.post(url)
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(content));
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize request content", e);
        }
    }

    /**
     * Creates a PUT request builder for the specified URL with the given content.
     *
     * @param url     The URL to send the PUT request to
     * @param content The content to include in the request body
     * @return A MockHttpServletRequestBuilder for a PUT request
     */
    protected MockHttpServletRequestBuilder put(String url, Object content) {
        try {
            return MockMvcRequestBuilders.put(url)
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(content));
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize request content", e);
        }
    }

    /**
     * Creates a PATCH request builder for the specified URL with the given content.
     *
     * @param url     The URL to send the PATCH request to
     * @param content The content to include in the request body
     * @return A MockHttpServletRequestBuilder for a PATCH request
     */
    protected MockHttpServletRequestBuilder patch(String url, Object content) {
        try {
            return MockMvcRequestBuilders.patch(url)
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(content));
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize request content", e);
        }
    }

    /**
     * Creates a DELETE request builder for the specified URL.
     *
     * @param url The URL to send the DELETE request to
     * @return A MockHttpServletRequestBuilder for a DELETE request
     */
    protected MockHttpServletRequestBuilder delete(String url) {
        return MockMvcRequestBuilders.delete(url)
                .contentType(MediaType.APPLICATION_JSON);
    }

    /**
     * Adds a JWT authorization header to the request builder.
     *
     * @param requestBuilder The request builder to add the header to
     * @param token          The JWT token to include in the header
     * @return The updated request builder with the authorization header
     */
    protected MockHttpServletRequestBuilder withJwtAuth(MockHttpServletRequestBuilder requestBuilder, String token) {
        return requestBuilder.header(HttpHeaders.AUTHORIZATION, "Bearer " + token);
    }

    /**
     * Performs the request and expects a 2xx status code.
     *
     * @param requestBuilder The request builder to perform
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performAndExpectSuccess(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andExpect(MockMvcResultMatchers.status().is2xxSuccessful());
    }

    /**
     * Performs the request and expects a 4xx status code.
     *
     * @param requestBuilder The request builder to perform
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performAndExpectClientError(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andExpect(MockMvcResultMatchers.status().is4xxClientError());
    }

    /**
     * Performs the request and expects a 5xx status code.
     *
     * @param requestBuilder The request builder to perform
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performAndExpectServerError(MockHttpServletRequestBuilder requestBuilder) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andExpect(MockMvcResultMatchers.status().is5xxServerError());
    }

    /**
     * Performs the request and expects the specified status code.
     *
     * @param requestBuilder The request builder to perform
     * @param status         The expected status code
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performAndExpectStatus(MockHttpServletRequestBuilder requestBuilder, int status) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andExpect(MockMvcResultMatchers.status().is(status));
    }

    /**
     * Performs the request and expects the specified status code and content type.
     *
     * @param requestBuilder The request builder to perform
     * @param status         The expected status code
     * @param contentType    The expected content type
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performAndExpectStatusAndContentType(MockHttpServletRequestBuilder requestBuilder, int status, String contentType) throws Exception {
        return mockMvc.perform(requestBuilder)
                .andExpect(MockMvcResultMatchers.status().is(status))
                .andExpect(MockMvcResultMatchers.content().contentType(contentType));
    }

    /**
     * Performs the request and expects the specified status code and JSON content type.
     *
     * @param requestBuilder The request builder to perform
     * @param status         The expected status code
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performAndExpectStatusAndJsonContent(MockHttpServletRequestBuilder requestBuilder, int status) throws Exception {
        return performAndExpectStatusAndContentType(requestBuilder, status, MediaType.APPLICATION_JSON_VALUE);
    }

    /**
     * Performs the request and expects the specified status code and JSON path to exist.
     *
     * @param requestBuilder The request builder to perform
     * @param status         The expected status code
     * @param jsonPath       The JSON path to check for existence
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performAndExpectJsonPath(MockHttpServletRequestBuilder requestBuilder, int status, String jsonPath) throws Exception {
        return performAndExpectStatusAndJsonContent(requestBuilder, status)
                .andExpect(MockMvcResultMatchers.jsonPath(jsonPath).exists());
    }

    /**
     * Performs the request and expects the specified status code and JSON path to have the specified value.
     *
     * @param requestBuilder The request builder to perform
     * @param status         The expected status code
     * @param jsonPath       The JSON path to check
     * @param expectedValue  The expected value at the JSON path
     * @return The ResultActions for further assertions
     * @throws Exception If an error occurs during the request
     */
    protected ResultActions performAndExpectJsonPathValue(MockHttpServletRequestBuilder requestBuilder, int status, String jsonPath, Object expectedValue) throws Exception {
        return performAndExpectStatusAndJsonContent(requestBuilder, status)
                .andExpect(MockMvcResultMatchers.jsonPath(jsonPath).value(expectedValue));
    }

    /**
     * Extracts the response content as a string from the MVC result.
     *
     * @param result The MVC result to extract the content from
     * @return The response content as a string
     * @throws UnsupportedEncodingException If the response encoding is not supported
     */
    protected String getContentAsString(MvcResult result) throws UnsupportedEncodingException {
        return result.getResponse().getContentAsString();
    }

    /**
     * Extracts the response content as an object of the specified type from the MVC result.
     *
     * @param result        The MVC result to extract the content from
     * @param responseClass The class to deserialize the response content to
     * @param <T>           The type of the response object
     * @return The response content as an object of the specified type
     * @throws Exception If an error occurs during deserialization
     */
    protected <T> T getContentAsObject(MvcResult result, Class<T> responseClass) throws Exception {
        String content = getContentAsString(result);
        return objectMapper.readValue(content, responseClass);
    }

    /**
     * Creates a result matcher that checks if the response content contains the specified substring.
     *
     * @param substring The substring to check for in the response content
     * @return A result matcher that checks if the response content contains the specified substring
     */
    protected ResultMatcher contentContains(String substring) {
        return result -> {
            String content = getContentAsString(result);
            if (!content.contains(substring)) {
                throw new AssertionError("Response content does not contain '" + substring + "'. Content: " + content);
            }
        };
    }

    /**
     * Creates a result matcher that checks if the response content equals the specified string.
     *
     * @param expected The expected response content
     * @return A result matcher that checks if the response content equals the specified string
     */
    protected ResultMatcher contentEquals(String expected) {
        return result -> {
            String content = getContentAsString(result);
            if (!content.equals(expected)) {
                throw new AssertionError("Response content does not equal '" + expected + "'. Content: " + content);
            }
        };
    }

    /**
     * Creates a result matcher that checks if the response content matches the specified JSON.
     *
     * @param expectedJson The expected JSON content
     * @return A result matcher that checks if the response content matches the specified JSON
     */
    protected ResultMatcher contentJson(String expectedJson) {
        return result -> {
            String content = getContentAsString(result);
            // Use ObjectMapper to compare JSON semantically (ignoring whitespace, order, etc.)
            Object expectedObj = objectMapper.readTree(expectedJson);
            Object actualObj = objectMapper.readTree(content);
            if (!expectedObj.equals(actualObj)) {
                throw new AssertionError("Response JSON does not match expected JSON.\nExpected: " + expectedJson + "\nActual: " + content);
            }
        };
    }

    /**
     * Creates a result matcher that checks if the response content matches the specified object as JSON.
     *
     * @param expected The expected object to match as JSON
     * @return A result matcher that checks if the response content matches the specified object as JSON
     */
    protected ResultMatcher contentJson(Object expected) {
        try {
            String expectedJson = objectMapper.writeValueAsString(expected);
            return contentJson(expectedJson);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize expected object to JSON", e);
        }
    }
}