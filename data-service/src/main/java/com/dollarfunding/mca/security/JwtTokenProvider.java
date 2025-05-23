package com.dollarfunding.mca.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.UnsupportedJwtException;
import io.jsonwebtoken.security.Keys;
import io.jsonwebtoken.security.SignatureException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.User;
import org.springframework.stereotype.Component;

import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.Key;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.NoSuchAlgorithmException;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.spec.EncodedKeySpec;
import java.security.spec.InvalidKeySpecException;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Service class for JWT token generation and validation using RS256 asymmetric key signing.
 * This class handles token creation with configurable expiration (60 minutes for access tokens,
 * 7 days for refresh tokens), token validation, and user details extraction from tokens.
 */
@Component
public class JwtTokenProvider {

    private static final Logger logger = LoggerFactory.getLogger(JwtTokenProvider.class);

    // Token expiration times in milliseconds
    private static final long ACCESS_TOKEN_EXPIRATION_TIME = 60 * 60 * 1000; // 60 minutes
    private static final long REFRESH_TOKEN_EXPIRATION_TIME = 7 * 24 * 60 * 60 * 1000; // 7 days

    // JWT claims keys
    private static final String AUTHORITIES_KEY = "auth";
    private static final String USER_ID_KEY = "uid";
    private static final String TOKEN_TYPE_KEY = "type";
    
    // Token types
    private static final String ACCESS_TOKEN = "access";
    private static final String REFRESH_TOKEN = "refresh";

    @Value("${jwt.issuer:dollarfunding-mca}")
    private String issuer;

    @Value("${jwt.audience:mca-api}")
    private String audience;

    @Value("${jwt.private-key-path:}")
    private String privateKeyPath;

    @Value("${jwt.public-key-path:}")
    private String publicKeyPath;

    @Value("${jwt.auto-generate-keys:true}")
    private boolean autoGenerateKeys;

    @Value("${jwt.key-rotation-days:30}")
    private int keyRotationDays;

    private PrivateKey privateKey;
    private PublicKey publicKey;
    private Date keyGenerationDate;

    /**
     * Initialize the JWT token provider by loading or generating RSA keys.
     */
    @PostConstruct
    public void init() {
        try {
            if (autoGenerateKeys || privateKeyPath.isEmpty() || publicKeyPath.isEmpty()) {
                logger.info("Generating new RSA key pair for JWT signing");
                generateKeyPair();
            } else {
                logger.info("Loading RSA keys from configured paths");
                loadKeys();
            }
            keyGenerationDate = new Date();
        } catch (Exception e) {
            logger.error("Failed to initialize JWT token provider", e);
            throw new RuntimeException("Could not initialize JWT token provider", e);
        }
    }

    /**
     * Generate a new RSA key pair for JWT signing.
     */
    private void generateKeyPair() throws NoSuchAlgorithmException {
        KeyPairGenerator keyPairGenerator = KeyPairGenerator.getInstance("RSA");
        keyPairGenerator.initialize(2048); // Use 2048 bits for strong security
        KeyPair keyPair = keyPairGenerator.generateKeyPair();
        this.privateKey = keyPair.getPrivate();
        this.publicKey = keyPair.getPublic();
        
        // Save keys to file if paths are provided
        if (!privateKeyPath.isEmpty() && !publicKeyPath.isEmpty()) {
            try {
                savePrivateKey();
                savePublicKey();
            } catch (IOException e) {
                logger.warn("Failed to save generated keys to disk", e);
            }
        }
    }

    /**
     * Load RSA keys from configured file paths.
     */
    private void loadKeys() throws IOException, NoSuchAlgorithmException, InvalidKeySpecException {
        // Load private key
        if (!privateKeyPath.isEmpty()) {
            byte[] privateKeyBytes = Files.readAllBytes(Paths.get(privateKeyPath));
            KeyFactory keyFactory = KeyFactory.getInstance("RSA");
            EncodedKeySpec privateKeySpec = new PKCS8EncodedKeySpec(privateKeyBytes);
            this.privateKey = keyFactory.generatePrivate(privateKeySpec);
        }
        
        // Load public key
        if (!publicKeyPath.isEmpty()) {
            byte[] publicKeyBytes = Files.readAllBytes(Paths.get(publicKeyPath));
            KeyFactory keyFactory = KeyFactory.getInstance("RSA");
            EncodedKeySpec publicKeySpec = new X509EncodedKeySpec(publicKeyBytes);
            this.publicKey = keyFactory.generatePublic(publicKeySpec);
        }
    }

    /**
     * Save the private key to the configured file path.
     */
    private void savePrivateKey() throws IOException {
        byte[] privateKeyBytes = privateKey.getEncoded();
        Files.write(Paths.get(privateKeyPath), privateKeyBytes);
    }

    /**
     * Save the public key to the configured file path.
     */
    private void savePublicKey() throws IOException {
        byte[] publicKeyBytes = publicKey.getEncoded();
        Files.write(Paths.get(publicKeyPath), publicKeyBytes);
    }

    /**
     * Check if key rotation is needed based on the configured rotation period.
     */
    private boolean isKeyRotationNeeded() {
        if (keyGenerationDate == null) {
            return true;
        }
        
        long rotationMillis = keyRotationDays * 24 * 60 * 60 * 1000L;
        return System.currentTimeMillis() - keyGenerationDate.getTime() > rotationMillis;
    }

    /**
     * Rotate keys if needed based on the configured rotation period.
     */
    private void rotateKeysIfNeeded() {
        if (isKeyRotationNeeded()) {
            try {
                logger.info("Performing scheduled key rotation");
                generateKeyPair();
                keyGenerationDate = new Date();
            } catch (NoSuchAlgorithmException e) {
                logger.error("Failed to rotate keys", e);
            }
        }
    }

    /**
     * Generate an access token for the given authentication.
     *
     * @param authentication the authentication object containing user details
     * @return the generated JWT token string
     */
    public String generateAccessToken(Authentication authentication) {
        rotateKeysIfNeeded();
        
        UserPrincipal userPrincipal = (UserPrincipal) authentication.getPrincipal();
        
        Map<String, Object> claims = new HashMap<>();
        claims.put(USER_ID_KEY, userPrincipal.getId());
        claims.put(TOKEN_TYPE_KEY, ACCESS_TOKEN);
        
        String authorities = userPrincipal.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .collect(Collectors.joining(","));
        claims.put(AUTHORITIES_KEY, authorities);
        
        return buildToken(claims, userPrincipal.getUsername(), ACCESS_TOKEN_EXPIRATION_TIME);
    }

    /**
     * Generate a refresh token for the given authentication.
     *
     * @param authentication the authentication object containing user details
     * @return the generated JWT refresh token string
     */
    public String generateRefreshToken(Authentication authentication) {
        rotateKeysIfNeeded();
        
        UserPrincipal userPrincipal = (UserPrincipal) authentication.getPrincipal();
        
        Map<String, Object> claims = new HashMap<>();
        claims.put(USER_ID_KEY, userPrincipal.getId());
        claims.put(TOKEN_TYPE_KEY, REFRESH_TOKEN);
        
        return buildToken(claims, userPrincipal.getUsername(), REFRESH_TOKEN_EXPIRATION_TIME);
    }

    /**
     * Build a JWT token with the given claims, subject, and expiration time.
     *
     * @param claims additional claims to include in the token
     * @param subject the subject of the token (typically username)
     * @param expirationTime the expiration time in milliseconds
     * @return the generated JWT token string
     */
    private String buildToken(Map<String, Object> claims, String subject, long expirationTime) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + expirationTime);
        
        return Jwts.builder()
                .setClaims(claims)
                .setSubject(subject)
                .setIssuer(issuer)
                .setAudience(audience)
                .setIssuedAt(now)
                .setExpiration(expiryDate)
                .signWith(privateKey, SignatureAlgorithm.RS256)
                .compact();
    }

    /**
     * Get the user ID from the token.
     *
     * @param token the JWT token
     * @return the user ID extracted from the token
     */
    public Long getUserIdFromToken(String token) {
        Claims claims = getClaims(token);
        return Long.parseLong(claims.get(USER_ID_KEY).toString());
    }

    /**
     * Get the username from the token.
     *
     * @param token the JWT token
     * @return the username extracted from the token
     */
    public String getUsernameFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.getSubject();
    }

    /**
     * Get the token type from the token.
     *
     * @param token the JWT token
     * @return the token type (access or refresh)
     */
    public String getTokenType(String token) {
        Claims claims = getClaims(token);
        return claims.get(TOKEN_TYPE_KEY, String.class);
    }

    /**
     * Check if the token is a refresh token.
     *
     * @param token the JWT token
     * @return true if the token is a refresh token, false otherwise
     */
    public boolean isRefreshToken(String token) {
        return REFRESH_TOKEN.equals(getTokenType(token));
    }
    
    /**
     * Check if the token is an access token.
     *
     * @param token the JWT token
     * @return true if the token is an access token, false otherwise
     */
    public boolean isAccessToken(String token) {
        return ACCESS_TOKEN.equals(getTokenType(token));
    }

    /**
     * Get the authorities from the token.
     *
     * @param token the JWT token
     * @return a collection of granted authorities extracted from the token
     */
    public Collection<? extends GrantedAuthority> getAuthoritiesFromToken(String token) {
        Claims claims = getClaims(token);
        
        String authoritiesString = claims.get(AUTHORITIES_KEY, String.class);
        if (authoritiesString == null || authoritiesString.isEmpty()) {
            return List.of();
        }
        
        return List.of(authoritiesString.split(",")).stream()
                .map(SimpleGrantedAuthority::new)
                .collect(Collectors.toList());
    }

    /**
     * Create an authentication object from the token.
     *
     * @param token the JWT token
     * @return an authentication object containing user details extracted from the token
     */
    public Authentication getAuthentication(String token) {
        String username = getUsernameFromToken(token);
        Collection<? extends GrantedAuthority> authorities = getAuthoritiesFromToken(token);
        
        User principal = new User(username, "", authorities);
        return new UsernamePasswordAuthenticationToken(principal, token, authorities);
    }

    /**
     * Validate the token.
     *
     * @param token the JWT token to validate
     * @return true if the token is valid, false otherwise
     */
    public boolean validateToken(String token) {
        try {
            getClaims(token);
            return true;
        } catch (SignatureException e) {
            logger.error("Invalid JWT signature: {}", e.getMessage());
        } catch (MalformedJwtException e) {
            logger.error("Invalid JWT token: {}", e.getMessage());
        } catch (ExpiredJwtException e) {
            logger.error("JWT token is expired: {}", e.getMessage());
        } catch (UnsupportedJwtException e) {
            logger.error("JWT token is unsupported: {}", e.getMessage());
        } catch (IllegalArgumentException e) {
            logger.error("JWT claims string is empty: {}", e.getMessage());
        }
        
        return false;
    }

    /**
     * Get the claims from the token.
     *
     * @param token the JWT token
     * @return the claims extracted from the token
     */
    private Claims getClaims(String token) {
        return Jwts.parserBuilder()
                .setSigningKey(publicKey)
                .build()
                .parseClaimsJws(token)
                .getBody();
    }

    /**
     * Get the public key as a Base64 encoded string.
     *
     * @return the Base64 encoded public key
     */
    public String getEncodedPublicKey() {
        return Base64.getEncoder().encodeToString(publicKey.getEncoded());
    }

    /**
     * Get the public key.
     *
     * @return the public key
     */
    public PublicKey getPublicKey() {
        return publicKey;
    }
}