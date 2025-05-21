package com.dollarfunding.mca.security;

import io.jsonwebtoken.*;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import io.jsonwebtoken.security.SignatureException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.stereotype.Component;

import java.security.Key;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Service for JWT token generation and validation using RS256 asymmetric key signing.
 * <p>
 * This class handles token creation with configurable expiration (60 minutes for access tokens,
 * 7 days for refresh tokens), token validation, and user details extraction from tokens.
 * It also supports public key rotation capabilities for enhanced security.
 * </p>
 */
@Component
public class JwtTokenProvider {

    private static final Logger logger = LoggerFactory.getLogger(JwtTokenProvider.class);
    
    private static final String AUTHORITIES_KEY = "auth";
    private static final String USER_ID_KEY = "uid";
    private static final String TOKEN_TYPE_KEY = "type";
    private static final String ACCESS_TOKEN = "access";
    private static final String REFRESH_TOKEN = "refresh";
    
    // Key rotation map with key ID as the map key
    private final Map<String, KeyPair> keyPairs = new ConcurrentHashMap<>();
    private String currentKeyId;
    
    private final UserDetailsService userDetailsService;
    
    @Value("${app.security.jwt.issuer:dollarfunding-mca}")
    private String issuer;
    
    @Value("${app.security.jwt.audience:mca-api}")
    private String audience;
    
    @Value("${app.security.jwt.access-token-expiration:3600}")
    private long accessTokenExpirationInSeconds; // 60 minutes default
    
    @Value("${app.security.jwt.refresh-token-expiration:604800}")
    private long refreshTokenExpirationInSeconds; // 7 days default
    
    @Value("${app.security.jwt.key-rotation-seconds:86400}")
    private long keyRotationInSeconds; // 24 hours default
    
    private long lastKeyRotationTime;
    
    public JwtTokenProvider(UserDetailsService userDetailsService) {
        this.userDetailsService = userDetailsService;
        initializeKeyPair();
    }
    
    /**
     * Initializes the RSA key pair for JWT signing.
     */
    private void initializeKeyPair() {
        try {
            KeyPairGenerator keyPairGenerator = KeyPairGenerator.getInstance("RSA");
            keyPairGenerator.initialize(2048); // Use 2048 bit keys for better security
            KeyPair keyPair = keyPairGenerator.generateKeyPair();
            
            currentKeyId = UUID.randomUUID().toString();
            keyPairs.put(currentKeyId, keyPair);
            lastKeyRotationTime = System.currentTimeMillis();
            
            logger.info("Initialized RSA key pair for JWT signing with key ID: {}", currentKeyId);
        } catch (Exception e) {
            logger.error("Failed to initialize RSA key pair for JWT signing", e);
            throw new RuntimeException("Failed to initialize RSA key pair for JWT signing", e);
        }
    }
    
    /**
     * Rotates the key pair if the rotation period has elapsed.
     * Keeps the previous key pair for a grace period to validate tokens signed with it.
     */
    private void rotateKeyPairIfNeeded() {
        long currentTime = System.currentTimeMillis();
        if (currentTime - lastKeyRotationTime > keyRotationInSeconds * 1000) {
            try {
                KeyPairGenerator keyPairGenerator = KeyPairGenerator.getInstance("RSA");
                keyPairGenerator.initialize(2048);
                KeyPair keyPair = keyPairGenerator.generateKeyPair();
                
                String newKeyId = UUID.randomUUID().toString();
                keyPairs.put(newKeyId, keyPair);
                currentKeyId = newKeyId;
                lastKeyRotationTime = currentTime;
                
                // Clean up old keys, but keep the most recent ones for validation
                // Keep at most 3 key pairs (current + 2 previous) to allow for validation of tokens
                // issued before key rotation
                if (keyPairs.size() > 3) {
                    List<String> keyIds = new ArrayList<>(keyPairs.keySet());
                    keyIds.sort(Comparator.naturalOrder());
                    for (int i = 0; i < keyIds.size() - 3; i++) {
                        keyPairs.remove(keyIds.get(i));
                    }
                }
                
                logger.info("Rotated RSA key pair for JWT signing with new key ID: {}", newKeyId);
            } catch (Exception e) {
                logger.error("Failed to rotate RSA key pair for JWT signing", e);
                // Continue using the current key pair if rotation fails
            }
        }
    }
    
    /**
     * Generates a JWT access token for the given authentication.
     *
     * @param authentication the authentication object containing user details
     * @return the generated JWT token
     */
    public String generateAccessToken(Authentication authentication) {
        rotateKeyPairIfNeeded();
        
        UserPrincipal userPrincipal = (UserPrincipal) authentication.getPrincipal();
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + accessTokenExpirationInSeconds * 1000);
        
        KeyPair currentKeyPair = keyPairs.get(currentKeyId);
        RSAPrivateKey privateKey = (RSAPrivateKey) currentKeyPair.getPrivate();
        
        String authorities = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .collect(Collectors.joining(","));
        
        return Jwts.builder()
                .setHeaderParam(JwsHeader.KEY_ID, currentKeyId)
                .setSubject(userPrincipal.getUsername())
                .setIssuer(issuer)
                .setAudience(audience)
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .claim(USER_ID_KEY, userPrincipal.getId())
                .claim(AUTHORITIES_KEY, authorities)
                .claim(TOKEN_TYPE_KEY, ACCESS_TOKEN)
                .signWith(privateKey, SignatureAlgorithm.RS256)
                .compact();
    }
    
    /**
     * Generates a JWT refresh token for the given authentication.
     *
     * @param authentication the authentication object containing user details
     * @return the generated refresh token
     */
    public String generateRefreshToken(Authentication authentication) {
        rotateKeyPairIfNeeded();
        
        UserPrincipal userPrincipal = (UserPrincipal) authentication.getPrincipal();
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + refreshTokenExpirationInSeconds * 1000);
        
        KeyPair currentKeyPair = keyPairs.get(currentKeyId);
        RSAPrivateKey privateKey = (RSAPrivateKey) currentKeyPair.getPrivate();
        
        return Jwts.builder()
                .setHeaderParam(JwsHeader.KEY_ID, currentKeyId)
                .setSubject(userPrincipal.getUsername())
                .setIssuer(issuer)
                .setAudience(audience)
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .claim(USER_ID_KEY, userPrincipal.getId())
                .claim(TOKEN_TYPE_KEY, REFRESH_TOKEN)
                .signWith(privateKey, SignatureAlgorithm.RS256)
                .compact();
    }
    
    /**
     * Validates the JWT token and returns the authentication object.
     *
     * @param token the JWT token to validate
     * @return the authentication object if the token is valid
     */
    public Authentication getAuthentication(String token) {
        Claims claims = parseToken(token);
        
        // Verify token type is ACCESS_TOKEN
        String tokenType = claims.get(TOKEN_TYPE_KEY, String.class);
        if (!ACCESS_TOKEN.equals(tokenType)) {
            throw new JwtException("Invalid token type. Expected access token.");
        }
        
        String username = claims.getSubject();
        UserDetails userDetails = userDetailsService.loadUserByUsername(username);
        
        Collection<? extends GrantedAuthority> authorities =
                Arrays.stream(claims.get(AUTHORITIES_KEY, String.class).split(","))
                        .filter(auth -> !auth.trim().isEmpty())
                        .map(SimpleGrantedAuthority::new)
                        .collect(Collectors.toList());
        
        return new UsernamePasswordAuthenticationToken(userDetails, "", authorities);
    }
    
    /**
     * Validates a refresh token and returns the username if valid.
     *
     * @param refreshToken the refresh token to validate
     * @return the username associated with the token
     * @throws JwtException if the token is invalid
     */
    public String getUsernameFromRefreshToken(String refreshToken) {
        Claims claims = parseToken(refreshToken);
        
        // Verify token type is REFRESH_TOKEN
        String tokenType = claims.get(TOKEN_TYPE_KEY, String.class);
        if (!REFRESH_TOKEN.equals(tokenType)) {
            throw new JwtException("Invalid token type. Expected refresh token.");
        }
        
        return claims.getSubject();
    }
    
    /**
     * Extracts the user ID from the token.
     *
     * @param token the JWT token
     * @return the user ID
     */
    public Long getUserIdFromToken(String token) {
        Claims claims = parseToken(token);
        return claims.get(USER_ID_KEY, Long.class);
    }
    
    /**
     * Validates the token and returns the claims if valid.
     *
     * @param token the JWT token to validate
     * @return the claims from the token
     * @throws JwtException if the token is invalid
     */
    private Claims parseToken(String token) {
        try {
            // Extract the key ID from the token header
            String keyId = extractKeyIdFromToken(token);
            if (keyId == null || !keyPairs.containsKey(keyId)) {
                throw new JwtException("Unknown key ID in token");
            }
            
            KeyPair keyPair = keyPairs.get(keyId);
            RSAPublicKey publicKey = (RSAPublicKey) keyPair.getPublic();
            
            return Jwts.parserBuilder()
                    .setSigningKey(publicKey)
                    .requireIssuer(issuer)
                    .requireAudience(audience)
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
        } catch (ExpiredJwtException e) {
            logger.debug("JWT token is expired: {}", e.getMessage());
            throw new JwtException("JWT token is expired", e);
        } catch (UnsupportedJwtException e) {
            logger.debug("JWT token is unsupported: {}", e.getMessage());
            throw new JwtException("JWT token is unsupported", e);
        } catch (MalformedJwtException e) {
            logger.debug("JWT token is malformed: {}", e.getMessage());
            throw new JwtException("JWT token is malformed", e);
        } catch (SignatureException e) {
            logger.debug("JWT signature validation failed: {}", e.getMessage());
            throw new JwtException("JWT signature validation failed", e);
        } catch (IllegalArgumentException e) {
            logger.debug("JWT token is invalid: {}", e.getMessage());
            throw new JwtException("JWT token is invalid", e);
        } catch (Exception e) {
            logger.debug("JWT token validation failed: {}", e.getMessage());
            throw new JwtException("JWT token validation failed", e);
        }
    }
    
    /**
     * Extracts the key ID from the token header.
     *
     * @param token the JWT token
     * @return the key ID or null if not found
     */
    private String extractKeyIdFromToken(String token) {
        try {
            // Split the token into parts
            String[] parts = token.split("\\.");
            if (parts.length < 2) {
                return null;
            }
            
            // Decode the header
            String headerJson = new String(Base64.getUrlDecoder().decode(parts[0]));
            
            // Extract the kid value using simple string operations
            // This avoids having to parse the JSON which would require additional dependencies
            int kidIndex = headerJson.indexOf("\"kid\":");
            if (kidIndex == -1) {
                return null;
            }
            
            int valueStartIndex = headerJson.indexOf('"', kidIndex + 6) + 1;
            int valueEndIndex = headerJson.indexOf('"', valueStartIndex);
            
            if (valueStartIndex == 0 || valueEndIndex == -1) {
                return null;
            }
            
            return headerJson.substring(valueStartIndex, valueEndIndex);
        } catch (Exception e) {
            logger.debug("Failed to extract key ID from token: {}", e.getMessage());
            return null;
        }
    }
    
    /**
     * Validates the token without throwing an exception.
     *
     * @param token the JWT token to validate
     * @return true if the token is valid, false otherwise
     */
    public boolean validateToken(String token) {
        try {
            parseToken(token);
            return true;
        } catch (JwtException e) {
            logger.debug("JWT validation failed: {}", e.getMessage());
            return false;
        }
    }
    
    /**
     * Gets the current public key in PEM format for external validation.
     *
     * @return the current public key in PEM format
     */
    public String getCurrentPublicKeyPem() {
        KeyPair currentKeyPair = keyPairs.get(currentKeyId);
        RSAPublicKey publicKey = (RSAPublicKey) currentKeyPair.getPublic();
        
        byte[] publicKeyBytes = publicKey.getEncoded();
        String base64PublicKey = Base64.getEncoder().encodeToString(publicKeyBytes);
        
        return "-----BEGIN PUBLIC KEY-----\n" + 
               base64PublicKey + 
               "\n-----END PUBLIC KEY-----";
    }
    
    /**
     * Gets all active public keys with their key IDs for external validation.
     *
     * @return a map of key IDs to public keys in PEM format
     */
    public Map<String, String> getAllPublicKeysPem() {
        Map<String, String> publicKeyMap = new HashMap<>();
        
        for (Map.Entry<String, KeyPair> entry : keyPairs.entrySet()) {
            RSAPublicKey publicKey = (RSAPublicKey) entry.getValue().getPublic();
            byte[] publicKeyBytes = publicKey.getEncoded();
            String base64PublicKey = Base64.getEncoder().encodeToString(publicKeyBytes);
            
            String pemKey = "-----BEGIN PUBLIC KEY-----\n" + 
                           base64PublicKey + 
                           "\n-----END PUBLIC KEY-----";
            
            publicKeyMap.put(entry.getKey(), pemKey);
        }
        
        return publicKeyMap;
    }
    
    /**
     * Gets the expiration date from the token.
     *
     * @param token the JWT token
     * @return the expiration date
     */
    public Date getExpirationDateFromToken(String token) {
        Claims claims = parseToken(token);
        return claims.getExpiration();
    }
    
    /**
     * Checks if the token is expired.
     *
     * @param token the JWT token
     * @return true if the token is expired, false otherwise
     */
    public boolean isTokenExpired(String token) {
        try {
            Date expiration = getExpirationDateFromToken(token);
            return expiration.before(new Date());
        } catch (JwtException e) {
            return true;
        }
    }
    
    /**
     * Gets the username from the token.
     *
     * @param token the JWT token
     * @return the username
     */
    public String getUsernameFromToken(String token) {
        Claims claims = parseToken(token);
        return claims.getSubject();
    }
    
    /**
     * Gets the token type from the token.
     *
     * @param token the JWT token
     * @return the token type (access or refresh)
     */
    public String getTokenType(String token) {
        Claims claims = parseToken(token);
        return claims.get(TOKEN_TYPE_KEY, String.class);
    }
    
    /**
     * Checks if the token is an access token.
     *
     * @param token the JWT token
     * @return true if the token is an access token, false otherwise
     */
    public boolean isAccessToken(String token) {
        try {
            return ACCESS_TOKEN.equals(getTokenType(token));
        } catch (JwtException e) {
            return false;
        }
    }
    
    /**
     * Checks if the token is a refresh token.
     *
     * @param token the JWT token
     * @return true if the token is a refresh token, false otherwise
     */
    public boolean isRefreshToken(String token) {
        try {
            return REFRESH_TOKEN.equals(getTokenType(token));
        } catch (JwtException e) {
            return false;
        }
    }
    
    /**
     * Forces a key rotation, useful for testing or when a key is compromised.
     */
    public void forceKeyRotation() {
        lastKeyRotationTime = 0;
        rotateKeyPairIfNeeded();
    }
}