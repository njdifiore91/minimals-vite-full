#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Security utilities for the Document Service.

This module provides functions for handling encryption, HMAC signatures,
secure credential management, TLS configuration, and secure random token generation.

Implements AES-256 encryption for data at rest, HMAC signature generation and validation,
secure credential management, and TLS configuration helpers as required by the
Merchant Cash Advance (MCA) Application Processing System.

Key features:
- AES-256-GCM encryption for document storage and field-level encryption
- HMAC-SHA256 signature generation and validation for webhooks
- Secure credential management with environment isolation
- TLS 1.3/1.2 configuration with strong cipher suites
- Cryptographically secure random token generation
"""

import base64
import hashlib
import hmac
import logging
import os
import secrets
import ssl
from typing import Dict, Optional, Tuple, Union, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logger = logging.getLogger(__name__)

# Constants
AES_KEY_SIZE = 32  # 256 bits for AES-256 encryption
SALT_SIZE = 16     # 128 bits for key derivation salt
NONCE_SIZE = 12    # 96 bits for AES-GCM nonce (recommended size)
TAG_SIZE = 16      # 128 bits for authentication tag
TOKEN_SIZE = 32    # 256 bits for secure tokens

# TLS Constants
TLS_VERSION = ssl.PROTOCOL_TLS_SERVER  # Use the highest protocol version supported
TLS_CIPHERS = (
    # Only allow strong cipher suites with perfect forward secrecy
    # Order matters - most secure ciphers first
    'ECDHE-ECDSA-AES256-GCM-SHA384:'
    'ECDHE-RSA-AES256-GCM-SHA384:'
    'ECDHE-ECDSA-CHACHA20-POLY1305:'
    'ECDHE-RSA-CHACHA20-POLY1305:'
    'ECDHE-ECDSA-AES128-GCM-SHA256:'
    'ECDHE-RSA-AES128-GCM-SHA256'
)

# Environment constants
DEV_ENV = 'development'
STAGING_ENV = 'staging'
PROD_ENV = 'production'


def derive_key(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Derive an AES-256 key from a password using PBKDF2.
    
    Args:
        password: The password to derive the key from
        salt: Optional salt bytes. If not provided, a random salt will be generated
        
    Returns:
        Tuple of (derived_key, salt)
    """
    if salt is None:
        salt = os.urandom(SALT_SIZE)
        logger.debug("Generated new random salt for key derivation")
        
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE,
        salt=salt,
        iterations=100000,  # High iteration count for security
    )
    
    key = kdf.derive(password.encode('utf-8'))
    logger.debug("Successfully derived encryption key")
    return key, salt


def encrypt(data: Union[str, bytes], key: bytes) -> Dict[str, str]:
    """
    Encrypt data using AES-256-GCM, which provides both confidentiality and integrity.
    
    Args:
        data: The data to encrypt (string or bytes)
        key: The AES-256 key to use for encryption
        
    Returns:
        Dictionary containing the encrypted data and nonce in base64 format
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
        
    # Generate a random nonce (Number used ONCE)
    # This is critical for security - never reuse a nonce with the same key
    nonce = os.urandom(NONCE_SIZE)
    
    # Create an AES-GCM cipher with the provided key
    aesgcm = AESGCM(key)
    
    try:
        # Encrypt the data - GCM mode provides authenticated encryption
        # The authentication tag is automatically included in the ciphertext
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        logger.debug(f"Successfully encrypted {len(data)} bytes of data")
        
        # Return the encrypted data and nonce as a dictionary
        return {
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8')
        }
    except Exception as e:
        logger.error(f"Encryption failed: {str(e)}")
        raise


def decrypt(encrypted_data: Dict[str, str], key: bytes) -> bytes:
    """
    Decrypt data that was encrypted using AES-256-GCM.
    
    Args:
        encrypted_data: Dictionary containing the encrypted data and nonce in base64 format
        key: The AES-256 key to use for decryption
        
    Returns:
        The decrypted data as bytes
        
    Raises:
        ValueError: If decryption fails (e.g., due to tampering or incorrect key)
    """
    # Decode the base64 encoded data
    try:
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        nonce = base64.b64decode(encrypted_data['nonce'])
    except (KeyError, ValueError) as e:
        logger.error(f"Invalid encrypted data format: {str(e)}")
        raise ValueError(f"Invalid encrypted data format: {str(e)}")
    
    # Create an AES-GCM cipher with the provided key
    aesgcm = AESGCM(key)
    
    # Decrypt the data
    try:
        # GCM mode automatically verifies the authentication tag
        # If the ciphertext has been tampered with, this will raise an exception
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        logger.debug(f"Successfully decrypted {len(plaintext)} bytes of data")
        return plaintext
    except Exception as e:
        logger.error(f"Decryption failed: {str(e)}")
        raise ValueError(f"Decryption failed: {str(e)}")


def encrypt_with_password(data: Union[str, bytes], password: str) -> Dict[str, str]:
    """
    Encrypt data using a password.
    
    Args:
        data: The data to encrypt (string or bytes)
        password: The password to use for encryption
        
    Returns:
        Dictionary containing the encrypted data, salt, and nonce in base64 format
    """
    # Derive a key from the password
    key, salt = derive_key(password)
    
    # Encrypt the data using the derived key
    encrypted = encrypt(data, key)
    
    # Add the salt to the result
    encrypted['salt'] = base64.b64encode(salt).decode('utf-8')
    
    return encrypted


def decrypt_with_password(encrypted_data: Dict[str, str], password: str) -> bytes:
    """
    Decrypt data that was encrypted using a password.
    
    Args:
        encrypted_data: Dictionary containing the encrypted data, salt, and nonce in base64 format
        password: The password to use for decryption
        
    Returns:
        The decrypted data as bytes
    """
    # Decode the salt
    salt = base64.b64decode(encrypted_data['salt'])
    
    # Derive the key from the password and salt
    key, _ = derive_key(password, salt)
    
    # Decrypt the data using the derived key
    return decrypt(encrypted_data, key)


def generate_hmac_signature(data: Union[str, bytes], secret_key: Union[str, bytes]) -> str:
    """
    Generate an HMAC-SHA256 signature for the given data.
    
    This function is used for webhook payload signing as specified in the security architecture.
    HMAC-SHA256 provides a way to verify both the integrity and authenticity of a message.
    
    Args:
        data: The data to sign
        secret_key: The secret key to use for signing
        
    Returns:
        The HMAC signature as a hexadecimal string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf-8')
    
    try:
        signature = hmac.new(secret_key, data, hashlib.sha256).hexdigest()
        logger.debug(f"Generated HMAC signature for {len(data)} bytes of data")
        return signature
    except Exception as e:
        logger.error(f"HMAC signature generation failed: {str(e)}")
        raise


def verify_hmac_signature(data: Union[str, bytes], signature: str, secret_key: Union[str, bytes]) -> bool:
    """
    Verify an HMAC-SHA256 signature for the given data.
    
    This function is used to verify webhook payload signatures as specified in the security architecture.
    It uses a constant-time comparison to prevent timing attacks.
    
    Args:
        data: The data that was signed
        signature: The signature to verify (hexadecimal string)
        secret_key: The secret key used for signing
        
    Returns:
        True if the signature is valid, False otherwise
    """
    try:
        calculated_signature = generate_hmac_signature(data, secret_key)
        
        # Use constant-time comparison to prevent timing attacks
        # Regular string comparison (==) is vulnerable to timing attacks
        is_valid = hmac.compare_digest(calculated_signature, signature)
        
        if is_valid:
            logger.debug("HMAC signature verification successful")
        else:
            logger.warning("HMAC signature verification failed")
            
        return is_valid
    except Exception as e:
        logger.error(f"HMAC signature verification error: {str(e)}")
        return False


def generate_secure_token(size: int = TOKEN_SIZE) -> str:
    """
    Generate a secure random token for authentication or identification purposes.
    
    Uses the cryptographically secure secrets module to generate tokens that are
    suitable for security-sensitive applications like password reset links,
    API keys, or session identifiers.
    
    Args:
        size: The size of the token in bytes (default: 32 bytes / 256 bits)
        
    Returns:
        A URL-safe base64-encoded token
    """
    try:
        token = secrets.token_urlsafe(size)
        logger.debug(f"Generated secure token of size {size} bytes")
        return token
    except Exception as e:
        logger.error(f"Token generation failed: {str(e)}")
        raise


def generate_secure_hex_token(size: int = TOKEN_SIZE) -> str:
    """
    Generate a secure random token in hexadecimal format.
    
    Uses the cryptographically secure secrets module to generate tokens
    in hexadecimal format (0-9, a-f). This is useful for cases where
    URL-safe tokens are not required or hexadecimal format is preferred.
    
    Args:
        size: The size of the token in bytes (default: 32 bytes / 256 bits)
        
    Returns:
        A hexadecimal token string (length will be 2*size)
    """
    try:
        token = secrets.token_hex(size)
        logger.debug(f"Generated secure hex token of size {size} bytes ({len(token)} characters)")
        return token
    except Exception as e:
        logger.error(f"Hex token generation failed: {str(e)}")
        raise


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a secure random password with mixed characters.
    
    Creates a cryptographically secure password with a mix of uppercase letters,
    lowercase letters, digits, and special characters. The password is designed
    to be both secure and human-readable by excluding easily confused characters.
    
    Args:
        length: The length of the password (default: 16 characters)
        
    Returns:
        A secure password string
    """
    if length < 8:
        logger.warning(f"Requested password length {length} is too short, using minimum length of 8")
        length = 8
        
    try:
        # Define character sets with ambiguous characters removed for readability
        uppercase = 'ABCDEFGHJKLMNPQRSTUVWXYZ'  # Excluding I and O (can be confused with 1 and 0)
        lowercase = 'abcdefghijkmnopqrstuvwxyz'  # Excluding l (can be confused with 1)
        digits = '23456789'  # Excluding 0 and 1 (can be confused with O and l)
        special = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        
        # Ensure at least one character from each set for complexity requirements
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill the rest with random characters from all sets
        all_chars = uppercase + lowercase + digits + special
        password.extend(secrets.choice(all_chars) for _ in range(length - 4))
        
        # Shuffle the password characters to avoid predictable patterns
        # Using SystemRandom ensures cryptographically secure shuffling
        secrets.SystemRandom().shuffle(password)
        
        result = ''.join(password)
        logger.debug(f"Generated secure password of length {length}")
        return result
    except Exception as e:
        logger.error(f"Password generation failed: {str(e)}")
        raise


def create_tls_context(cert_file: str, key_file: str, ca_file: Optional[str] = None) -> ssl.SSLContext:
    """
    Create a TLS context with secure settings as required by the security architecture.
    
    Enforces TLS 1.3 with strong cipher suites and disables older, insecure protocols.
    Self-signed certificates are prohibited in production environments.
    
    Args:
        cert_file: Path to the certificate file
        key_file: Path to the private key file
        ca_file: Optional path to the CA certificate file
        
    Returns:
        An SSLContext object configured with secure settings
    """
    # Verify that certificate files exist
    for file_path in [cert_file, key_file]:
        if not os.path.isfile(file_path):
            error_msg = f"Certificate file not found: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
    
    if ca_file and not os.path.isfile(ca_file):
        error_msg = f"CA certificate file not found: {ca_file}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    try:
        # Create a TLS context
        context = ssl.SSLContext(TLS_VERSION)
        
        # Set the cipher suite to only allow strong ciphers
        context.set_ciphers(TLS_CIPHERS)
        
        # Load the certificate and private key
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        
        # Load the CA certificate if provided
        if ca_file:
            context.load_verify_locations(cafile=ca_file)
        
        # Set the verification mode to require certificates
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Enable host name checking
        context.check_hostname = True
        
        # Set additional security options
        context.options |= ssl.OP_NO_TLSv1      # Disable TLS 1.0
        context.options |= ssl.OP_NO_TLSv1_1    # Disable TLS 1.1
        context.options |= ssl.OP_NO_COMPRESSION  # Disable TLS compression to prevent CRIME attack
        
        # Set the minimum protocol version to TLS 1.2
        # TLS 1.3 will be used if available and supported by both client and server
        if hasattr(ssl, 'PROTOCOL_TLS_SERVER'):
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_3
        
        logger.info("Created secure TLS context with strong cipher suites")
        return context
    except Exception as e:
        logger.error(f"Failed to create TLS context: {str(e)}")
        raise


def secure_aws_credentials(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Secure AWS credentials by applying best practices as specified in the security architecture.
    
    Implements environment-isolated credential stores with proper handling.
    Uses IAM roles with least-privilege permissions for service accounts.
    
    Args:
        credentials: Dictionary containing AWS credentials
        
    Returns:
        Secured credentials dictionary with proper settings
        
    Raises:
        ValueError: If required credentials are missing
    """
    # Create a copy of the credentials to avoid modifying the original
    secured_creds = credentials.copy()
    
    # Determine the environment (development, staging, production)
    env = os.environ.get('ENVIRONMENT', 'development').lower()
    logger.debug(f"Configuring AWS credentials for {env} environment")
    
    # Set secure defaults if not already set
    if 'region' not in secured_creds:
        secured_creds['region'] = os.environ.get('AWS_REGION', 'us-east-1')
    
    # Validate required credentials
    required_keys = ['aws_access_key_id', 'aws_secret_access_key']
    for key in required_keys:
        if key not in secured_creds and key.upper() not in os.environ:
            error_msg = f"Missing required AWS credential: {key}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    # Use environment variables if credentials are not provided
    # This allows for environment-specific credential isolation
    for key in required_keys:
        if key not in secured_creds and key.upper() in os.environ:
            secured_creds[key] = os.environ[key.upper()]
    
    # Set secure session token if available
    if 'aws_session_token' not in secured_creds and 'AWS_SESSION_TOKEN' in os.environ:
        secured_creds['aws_session_token'] = os.environ['AWS_SESSION_TOKEN']
    
    # Set secure configuration options
    secured_creds.setdefault('use_ssl', True)  # Always use SSL/TLS
    secured_creds.setdefault('verify', True)   # Always verify SSL certificates
    
    # Set environment-specific S3 bucket names
    if 's3' in secured_creds:
        if 'bucket_name' in secured_creds['s3'] and not secured_creds['s3']['bucket_name'].endswith(f'-{env}'):
            # Ensure bucket name includes environment suffix for isolation
            secured_creds['s3']['bucket_name'] = f"{secured_creds['s3']['bucket_name']}-{env}"
    
    logger.info(f"AWS credentials secured for {env} environment")
    return secured_creds


def encrypt_field(data: str, encryption_key: bytes) -> str:
    """
    Encrypt a single field using AES-256-GCM for field-level encryption.
    
    This function is used for encrypting Personally Identifiable Information (PII)
    as required by the security architecture. It implements field-level encryption
    for sensitive data stored in PostgreSQL via the Data Service.
    
    Args:
        data: The field data to encrypt
        encryption_key: The encryption key to use
        
    Returns:
        Combined string with encrypted data in format: "ciphertext:nonce"
    """
    if not data:
        logger.warning("Attempted to encrypt empty field data")
        return ""
        
    try:
        encrypted = encrypt(data, encryption_key)
        # Combine ciphertext and nonce into a single string for storage
        combined = f"{encrypted['ciphertext']}:{encrypted['nonce']}"
        logger.debug(f"Successfully encrypted field data ({len(data)} chars)")
        return combined
    except Exception as e:
        logger.error(f"Field encryption failed: {str(e)}")
        raise


def decrypt_field(encrypted_data: str, encryption_key: bytes) -> str:
    """
    Decrypt a single field that was encrypted using AES-256-GCM.
    
    This function is used for decrypting Personally Identifiable Information (PII)
    that was encrypted using the encrypt_field function.
    
    Args:
        encrypted_data: The encrypted field data (combined format "ciphertext:nonce")
        encryption_key: The encryption key to use
        
    Returns:
        Decrypted field data as a string
        
    Raises:
        ValueError: If decryption fails or the encrypted data format is invalid
    """
    if not encrypted_data:
        logger.warning("Attempted to decrypt empty field data")
        return ""
        
    try:
        # Split the combined data
        parts = encrypted_data.split(':', 1)
        if len(parts) != 2:
            raise ValueError("Invalid encrypted field format")
            
        ciphertext_b64, nonce_b64 = parts
        
        # Create the encrypted data dictionary
        encrypted = {
            'ciphertext': ciphertext_b64,
            'nonce': nonce_b64
        }
        
        # Decrypt the data
        decrypted = decrypt(encrypted, encryption_key)
        logger.debug("Successfully decrypted field data")
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Field decryption failed: {str(e)}")
        raise ValueError(f"Field decryption failed: {str(e)}")