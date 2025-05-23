package com.dollarfunding.mca.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Field;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.util.Collection;
import java.util.Date;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Test class for {@link JwtTokenProvider} that verifies the correct implementation of JWT token
 * generation, validation, and user details extraction using RS256 asymmetric key signing.
 * 
 * Tests token creation with configurable expiration (60 minutes for access tokens, 7 days for refresh tokens),
 * token validation, and public key rotation capabilities.
 */
@ExtendWith(MockitoExtension.class)
public class JwtTokenProviderTest {

    @Spy
    @InjectMocks
    private JwtTokenProvider jwtTokenProvider;

    @Mock
    private Authentication authentication;

    @Mock
    private UserPrincipal userPrincipal;

    private KeyPair keyPair;
    private static final String TEST_USERNAME = "test.user@dollarfunding.com";
    private static final Long TEST_USER_ID = 1L;
    private static final String TEST_ROLE = "ROLE_OPERATIONS_STAFF";
    private static final String TEST_ISSUER = "dollarfunding-mca";
    private static final String TEST_AUDIENCE = "mca-api";

    @BeforeEach
    public void setUp() throws Exception {
        // Generate a test key pair for JWT signing
        KeyPairGenerator keyPairGenerator = KeyPairGenerator.getInstance("RSA");
        keyPairGenerator.initialize(2048);
        keyPair = keyPairGenerator.generateKeyPair();

        // Set up the JwtTokenProvider with test values
        ReflectionTestUtils.setField(jwtTokenProvider, "privateKey", keyPair.getPrivate());
        ReflectionTestUtils.setField(jwtTokenProvider, "publicKey", keyPair.getPublic());
        ReflectionTestUtils.setField(jwtTokenProvider, "issuer", TEST_ISSUER);
        ReflectionTestUtils.setField(jwtTokenProvider, "audience", TEST_AUDIENCE);
        ReflectionTestUtils.setField(jwtTokenProvider, "keyGenerationDate", new Date());

        // Mock the authentication and user principal
        when(authentication.getPrincipal()).thenReturn(userPrincipal);
        when(userPrincipal.getUsername()).thenReturn(TEST_USERNAME);
        when(userPrincipal.getId()).thenReturn(TEST_USER_ID);
        when(userPrincipal.getAuthorities()).thenReturn(
                List.of(new SimpleGrantedAuthority(TEST_ROLE)));
    }

    @Test
    @DisplayName("Should generate access token with RS256 algorithm")
    public void testGenerateAccessToken() {
        // When
        String token = jwtTokenProvider.generateAccessToken(authentication);

        // Then
        assertNotNull(token, "Token should not be null");
        assertTrue(token.split("\\.").length == 3, "Token should have three parts");
        
        // Verify token can be parsed with the public key
        Claims claims = Jwts.parserBuilder()
                .setSigningKey(keyPair.getPublic())
                .build()
                .parseClaimsJws(token)
                .getBody();
        
        // Verify token claims
        assertEquals(TEST_USERNAME, claims.getSubject(), "Subject should be the username");
        assertEquals(TEST_USER_ID.toString(), claims.get("uid").toString(), "User ID should match");
        assertEquals("access", claims.get("type"), "Token type should be 'access'");
        assertEquals(TEST_ROLE, claims.get("auth"), "Authorities should match");
        assertEquals(TEST_ISSUER, claims.getIssuer(), "Issuer should match");
        assertEquals(TEST_AUDIENCE, claims.getAudience(), "Audience should match");
        
        // Verify token was signed with RS256
        assertEquals(SignatureAlgorithm.RS256.getValue(), 
                Jwts.parserBuilder()
                        .setSigningKey(keyPair.getPublic())
                        .build()
                        .parseClaimsJws(token)
                        .getHeader()
                        .getAlgorithm(), 
                "Token should be signed with RS256");
    }

    @Test
    @DisplayName("Should generate refresh token with RS256 algorithm")
    public void testGenerateRefreshToken() {
        // When
        String token = jwtTokenProvider.generateRefreshToken(authentication);

        // Then
        assertNotNull(token, "Token should not be null");
        assertTrue(token.split("\\.").length == 3, "Token should have three parts");
        
        // Verify token can be parsed with the public key
        Claims claims = Jwts.parserBuilder()
                .setSigningKey(keyPair.getPublic())
                .build()
                .parseClaimsJws(token)
                .getBody();
        
        // Verify token claims
        assertEquals(TEST_USERNAME, claims.getSubject(), "Subject should be the username");
        assertEquals(TEST_USER_ID.toString(), claims.get("uid").toString(), "User ID should match");
        assertEquals("refresh", claims.get("type"), "Token type should be 'refresh'");
        assertEquals(TEST_ISSUER, claims.getIssuer(), "Issuer should match");
        assertEquals(TEST_AUDIENCE, claims.getAudience(), "Audience should match");
        
        // Verify token was signed with RS256
        assertEquals(SignatureAlgorithm.RS256.getValue(), 
                Jwts.parserBuilder()
                        .setSigningKey(keyPair.getPublic())
                        .build()
                        .parseClaimsJws(token)
                        .getHeader()
                        .getAlgorithm(), 
                "Token should be signed with RS256");
    }

    @Test
    @DisplayName("Should validate a properly signed token")
    public void testValidateToken() {
        // Given
        String token = jwtTokenProvider.generateAccessToken(authentication);

        // When
        boolean isValid = jwtTokenProvider.validateToken(token);

        // Then
        assertTrue(isValid, "Token should be valid");
    }

    @Test
    @DisplayName("Should reject a token with invalid signature")
    public void testValidateTokenWithInvalidSignature() throws Exception {
        // Given
        String token = jwtTokenProvider.generateAccessToken(authentication);
        
        // Generate a different key pair to create an invalid signature
        KeyPairGenerator keyPairGenerator = KeyPairGenerator.getInstance("RSA");
        keyPairGenerator.initialize(2048);
        KeyPair differentKeyPair = keyPairGenerator.generateKeyPair();
        
        // Replace the public key with a different one to simulate invalid signature
        PublicKey originalPublicKey = (PublicKey) ReflectionTestUtils.getField(jwtTokenProvider, "publicKey");
        ReflectionTestUtils.setField(jwtTokenProvider, "publicKey", differentKeyPair.getPublic());

        // When
        boolean isValid = jwtTokenProvider.validateToken(token);

        // Then
        assertFalse(isValid, "Token should be invalid due to signature mismatch");
        
        // Restore the original public key
        ReflectionTestUtils.setField(jwtTokenProvider, "publicKey", originalPublicKey);
    }

    @Test
    @DisplayName("Should extract username from token")
    public void testGetUsernameFromToken() {
        // Given
        String token = jwtTokenProvider.generateAccessToken(authentication);

        // When
        String username = jwtTokenProvider.getUsernameFromToken(token);

        // Then
        assertEquals(TEST_USERNAME, username, "Extracted username should match");
    }

    @Test
    @DisplayName("Should extract user ID from token")
    public void testGetUserIdFromToken() {
        // Given
        String token = jwtTokenProvider.generateAccessToken(authentication);

        // When
        Long userId = jwtTokenProvider.getUserIdFromToken(token);

        // Then
        assertEquals(TEST_USER_ID, userId, "Extracted user ID should match");
    }

    @Test
    @DisplayName("Should extract authorities from token")
    public void testGetAuthoritiesFromToken() {
        // Given
        String token = jwtTokenProvider.generateAccessToken(authentication);

        // When
        Collection<?> authorities = jwtTokenProvider.getAuthoritiesFromToken(token);

        // Then
        assertNotNull(authorities, "Authorities should not be null");
        assertEquals(1, authorities.size(), "Should have one authority");
        assertTrue(authorities.iterator().next().toString().equals(TEST_ROLE), 
                "Authority should match the test role");
    }

    @Test
    @DisplayName("Should create authentication from token")
    public void testGetAuthentication() {
        // Given
        String token = jwtTokenProvider.generateAccessToken(authentication);

        // When
        Authentication resultAuth = jwtTokenProvider.getAuthentication(token);

        // Then
        assertNotNull(resultAuth, "Authentication should not be null");
        assertEquals(TEST_USERNAME, resultAuth.getName(), "Username should match");
        assertEquals(1, resultAuth.getAuthorities().size(), "Should have one authority");
        assertTrue(resultAuth.getAuthorities().iterator().next().toString().equals(TEST_ROLE), 
                "Authority should match the test role");
        assertTrue(resultAuth instanceof UsernamePasswordAuthenticationToken, 
                "Should be a UsernamePasswordAuthenticationToken");
    }

    @Test
    @DisplayName("Should identify token type correctly")
    public void testTokenTypeIdentification() {
        // Given
        String accessToken = jwtTokenProvider.generateAccessToken(authentication);
        String refreshToken = jwtTokenProvider.generateRefreshToken(authentication);

        // When & Then
        assertTrue(jwtTokenProvider.isAccessToken(accessToken), "Should identify access token");
        assertFalse(jwtTokenProvider.isRefreshToken(accessToken), "Access token should not be identified as refresh token");
        
        assertTrue(jwtTokenProvider.isRefreshToken(refreshToken), "Should identify refresh token");
        assertFalse(jwtTokenProvider.isAccessToken(refreshToken), "Refresh token should not be identified as access token");
    }

    @Test
    @DisplayName("Should verify access token expiration time is 60 minutes")
    public void testAccessTokenExpiration() {
        // Given
        String token = jwtTokenProvider.generateAccessToken(authentication);

        // When
        Claims claims = Jwts.parserBuilder()
                .setSigningKey(keyPair.getPublic())
                .build()
                .parseClaimsJws(token)
                .getBody();
        
        // Then
        Date issuedAt = claims.getIssuedAt();
        Date expiration = claims.getExpiration();
        
        // Calculate the difference in milliseconds and convert to minutes
        long diffInMillis = expiration.getTime() - issuedAt.getTime();
        long diffInMinutes = diffInMillis / (60 * 1000);
        
        assertEquals(60, diffInMinutes, "Access token should expire in 60 minutes");
    }

    @Test
    @DisplayName("Should verify refresh token expiration time is 7 days")
    public void testRefreshTokenExpiration() {
        // Given
        String token = jwtTokenProvider.generateRefreshToken(authentication);

        // When
        Claims claims = Jwts.parserBuilder()
                .setSigningKey(keyPair.getPublic())
                .build()
                .parseClaimsJws(token)
                .getBody();
        
        // Then
        Date issuedAt = claims.getIssuedAt();
        Date expiration = claims.getExpiration();
        
        // Calculate the difference in milliseconds and convert to days
        long diffInMillis = expiration.getTime() - issuedAt.getTime();
        long diffInDays = diffInMillis / (24 * 60 * 60 * 1000);
        
        assertEquals(7, diffInDays, "Refresh token should expire in 7 days");
    }

    @Test
    @DisplayName("Should rotate keys when needed")
    public void testKeyRotation() throws Exception {
        // Given
        // Set key generation date to 31 days ago to trigger rotation
        Date oldDate = new Date(System.currentTimeMillis() - 31 * 24 * 60 * 60 * 1000L);
        ReflectionTestUtils.setField(jwtTokenProvider, "keyGenerationDate", oldDate);
        ReflectionTestUtils.setField(jwtTokenProvider, "keyRotationDays", 30);
        
        // Store the original keys
        PrivateKey originalPrivateKey = (PrivateKey) ReflectionTestUtils.getField(jwtTokenProvider, "privateKey");
        PublicKey originalPublicKey = (PublicKey) ReflectionTestUtils.getField(jwtTokenProvider, "publicKey");
        
        // When - generating a token should trigger key rotation
        String token = jwtTokenProvider.generateAccessToken(authentication);
        
        // Then
        PrivateKey newPrivateKey = (PrivateKey) ReflectionTestUtils.getField(jwtTokenProvider, "privateKey");
        PublicKey newPublicKey = (PublicKey) ReflectionTestUtils.getField(jwtTokenProvider, "publicKey");
        Date newKeyGenerationDate = (Date) ReflectionTestUtils.getField(jwtTokenProvider, "keyGenerationDate");
        
        // Keys should have been rotated
        assertNotEquals(originalPrivateKey, newPrivateKey, "Private key should have been rotated");
        assertNotEquals(originalPublicKey, newPublicKey, "Public key should have been rotated");
        
        // Key generation date should have been updated
        assertTrue(newKeyGenerationDate.after(oldDate), "Key generation date should have been updated");
        
        // Token should be valid with the new keys
        assertTrue(jwtTokenProvider.validateToken(token), "Token should be valid with new keys");
    }

    @Test
    @DisplayName("Should not rotate keys when not needed")
    public void testNoKeyRotationWhenNotNeeded() throws Exception {
        // Given
        // Set key generation date to 29 days ago (less than rotation period)
        Date recentDate = new Date(System.currentTimeMillis() - 29 * 24 * 60 * 60 * 1000L);
        ReflectionTestUtils.setField(jwtTokenProvider, "keyGenerationDate", recentDate);
        ReflectionTestUtils.setField(jwtTokenProvider, "keyRotationDays", 30);
        
        // Store the original keys
        PrivateKey originalPrivateKey = (PrivateKey) ReflectionTestUtils.getField(jwtTokenProvider, "privateKey");
        PublicKey originalPublicKey = (PublicKey) ReflectionTestUtils.getField(jwtTokenProvider, "publicKey");
        
        // When - generating a token should not trigger key rotation
        String token = jwtTokenProvider.generateAccessToken(authentication);
        
        // Then
        PrivateKey newPrivateKey = (PrivateKey) ReflectionTestUtils.getField(jwtTokenProvider, "privateKey");
        PublicKey newPublicKey = (PublicKey) ReflectionTestUtils.getField(jwtTokenProvider, "publicKey");
        Date newKeyGenerationDate = (Date) ReflectionTestUtils.getField(jwtTokenProvider, "keyGenerationDate");
        
        // Keys should not have been rotated
        assertEquals(originalPrivateKey, newPrivateKey, "Private key should not have been rotated");
        assertEquals(originalPublicKey, newPublicKey, "Public key should not have been rotated");
        
        // Key generation date should not have been updated
        assertEquals(recentDate, newKeyGenerationDate, "Key generation date should not have been updated");
        
        // Token should be valid
        assertTrue(jwtTokenProvider.validateToken(token), "Token should be valid");
    }

    @Test
    @DisplayName("Should provide encoded public key for clients")
    public void testGetEncodedPublicKey() {
        // When
        String encodedPublicKey = jwtTokenProvider.getEncodedPublicKey();
        
        // Then
        assertNotNull(encodedPublicKey, "Encoded public key should not be null");
        assertFalse(encodedPublicKey.isEmpty(), "Encoded public key should not be empty");
    }
}