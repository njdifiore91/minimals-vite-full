#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Security utilities for the OCR Service.

This module provides functions for handling encryption, HMAC signatures,
secure credential management, TLS configuration, and secure random token generation.

It implements AES-256 encryption for data at rest, HMAC-SHA256 for signature
generation and validation, secure credential handling, and TLS configuration helpers.

Note: This module requires the following packages:
    - cryptography (for AES encryption)
    - hmac, hashlib (for HMAC signatures)
    - os, base64 (for encoding/decoding)
    - ssl (for TLS configuration)
    - secrets (for secure random generation)
"""

import base64
import hashlib
import hmac
import os
import secrets
import ssl
import string
import sys
from typing import Dict, Optional, Tuple, Union, Any

# Try to import optional dependencies
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidTag
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


# ============================================================================
# AES-256 Encryption/Decryption Functions
# ============================================================================

def generate_key_from_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Generate an AES-256 key from a password using Scrypt KDF.
    
    Args:
        password: The password to derive the key from
        salt: Optional salt bytes. If not provided, a random salt will be generated.
        
    Returns:
        Tuple of (key, salt) where key is 32 bytes (256 bits) and salt is the salt used
        
    Raises:
        ImportError: If cryptography package is not available
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise ImportError("The 'cryptography' package is required for encryption operations")
        
    if salt is None:
        salt = os.urandom(16)  # Generate a random 16-byte salt
    
    # Use Scrypt KDF to derive a 32-byte key (256 bits)
    kdf = Scrypt(
        salt=salt,
        length=32,
        n=2**14,  # CPU/memory cost parameter
        r=8,       # Block size parameter
        p=1        # Parallelization parameter
    )
    
    key = kdf.derive(password.encode('utf-8'))
    return key, salt


def encrypt_data(data: Union[str, bytes], key: bytes) -> Dict[str, str]:
    """
    Encrypt data using AES-256-GCM.
    
    Args:
        data: The data to encrypt (string or bytes)
        key: The 32-byte encryption key
        
    Returns:
        Dictionary containing the encrypted data, nonce, and tag in base64 encoding
        
    Raises:
        ImportError: If cryptography package is not available
        ValueError: If the key is not 32 bytes
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise ImportError("The 'cryptography' package is required for encryption operations")
    
    if len(key) != 32:
        raise ValueError("Encryption key must be 32 bytes (256 bits)")
    
    # Convert string to bytes if necessary
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Generate a random 96-bit nonce (12 bytes)
    nonce = os.urandom(12)
    
    # Create an AES-GCM cipher with the key
    aesgcm = AESGCM(key)
    
    # Encrypt the data
    ciphertext = aesgcm.encrypt(nonce, data, None)
    
    # Return the encrypted data, nonce, and tag as base64-encoded strings
    return {
        'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
        'nonce': base64.b64encode(nonce).decode('utf-8')
    }


def decrypt_data(encrypted_data: Dict[str, str], key: bytes) -> bytes:
    """
    Decrypt data that was encrypted with AES-256-GCM.
    
    Args:
        encrypted_data: Dictionary containing the encrypted data and nonce in base64 encoding
        key: The 32-byte encryption key
        
    Returns:
        The decrypted data as bytes
        
    Raises:
        ImportError: If cryptography package is not available
        ValueError: If the key is not 32 bytes or if decryption fails
        KeyError: If the encrypted_data dictionary is missing required fields
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise ImportError("The 'cryptography' package is required for encryption operations")
    
    if len(key) != 32:
        raise ValueError("Decryption key must be 32 bytes (256 bits)")
    
    # Decode the base64-encoded ciphertext and nonce
    try:
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        nonce = base64.b64decode(encrypted_data['nonce'])
    except KeyError as e:
        raise KeyError(f"Missing required field in encrypted data: {e}")
    
    # Create an AES-GCM cipher with the key
    aesgcm = AESGCM(key)
    
    # Decrypt the data
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext
    except InvalidTag:
        raise ValueError("Decryption failed: Invalid key or corrupted data")


def encrypt_file(file_path: str, output_path: str, password: str) -> None:
    """
    Encrypt a file using AES-256-GCM with a password-derived key.
    
    Args:
        file_path: Path to the file to encrypt
        output_path: Path where the encrypted file will be saved
        password: Password to derive the encryption key from
        
    Raises:
        ImportError: If cryptography package is not available
        FileNotFoundError: If the input file does not exist
        IOError: If there is an error reading or writing files
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise ImportError("The 'cryptography' package is required for encryption operations")
    
    # Generate a key from the password
    key, salt = generate_key_from_password(password)
    
    try:
        # Read the file
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Encrypt the data
        encrypted = encrypt_data(data, key)
        
        # Add the salt to the encrypted data
        encrypted['salt'] = base64.b64encode(salt).decode('utf-8')
        
        # Write the encrypted data to the output file
        with open(output_path, 'w') as f:
            # Store as a simple JSON-like format
            for k, v in encrypted.items():
                f.write(f"{k}:{v}\n")
                
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {file_path}")
    except IOError as e:
        raise IOError(f"Error reading or writing files: {e}")


def decrypt_file(file_path: str, output_path: str, password: str) -> None:
    """
    Decrypt a file that was encrypted with encrypt_file().
    
    Args:
        file_path: Path to the encrypted file
        output_path: Path where the decrypted file will be saved
        password: Password used for encryption
        
    Raises:
        ImportError: If cryptography package is not available
        FileNotFoundError: If the input file does not exist
        IOError: If there is an error reading or writing files
        ValueError: If the file format is invalid or decryption fails
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise ImportError("The 'cryptography' package is required for encryption operations")
    
    try:
        # Read the encrypted file
        encrypted = {}
        with open(file_path, 'r') as f:
            for line in f:
                if ':' in line:
                    k, v = line.strip().split(':', 1)
                    encrypted[k] = v
        
        # Extract the salt and derive the key
        try:
            salt = base64.b64decode(encrypted.pop('salt'))
        except KeyError:
            raise ValueError("Invalid encrypted file format: missing salt")
        
        key, _ = generate_key_from_password(password, salt)
        
        # Decrypt the data
        decrypted = decrypt_data(encrypted, key)
        
        # Write the decrypted data to the output file
        with open(output_path, 'wb') as f:
            f.write(decrypted)
            
    except FileNotFoundError:
        raise FileNotFoundError(f"Encrypted file not found: {file_path}")
    except IOError as e:
        raise IOError(f"Error reading or writing files: {e}")


# ============================================================================
# HMAC Signature Generation and Validation
# ============================================================================

def generate_hmac_signature(data: Union[str, bytes], secret_key: Union[str, bytes]) -> str:
    """
    Generate an HMAC-SHA256 signature for the given data.
    
    Args:
        data: The data to sign (string or bytes)
        secret_key: The secret key for HMAC (string or bytes)
        
    Returns:
        The HMAC signature as a hexadecimal string
    """
    # Convert data and key to bytes if they are strings
    if isinstance(data, str):
        data = data.encode('utf-8')
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf-8')
    
    # Generate the HMAC signature using SHA-256
    signature = hmac.new(secret_key, data, hashlib.sha256).hexdigest()
    return signature


def verify_hmac_signature(data: Union[str, bytes], signature: str, secret_key: Union[str, bytes]) -> bool:
    """
    Verify an HMAC-SHA256 signature for the given data.
    
    Args:
        data: The data that was signed (string or bytes)
        signature: The HMAC signature to verify (hexadecimal string)
        secret_key: The secret key for HMAC (string or bytes)
        
    Returns:
        True if the signature is valid, False otherwise
    """
    # Generate a new signature for the data
    expected_signature = generate_hmac_signature(data, secret_key)
    
    # Compare the signatures using a constant-time comparison
    # to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


# ============================================================================
# Secure Credential Management
# ============================================================================

def get_credential(credential_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a credential from the environment or keyring.
    
    This function tries to get the credential from the following sources in order:
    1. Environment variable with the same name
    2. Keyring (if available)
    
    Args:
        credential_name: The name of the credential to get
        default: Default value to return if the credential is not found
        
    Returns:
        The credential value or the default value if not found
    """
    # Try to get the credential from the environment
    credential = os.environ.get(credential_name)
    if credential is not None:
        return credential
    
    # Try to get the credential from the keyring
    if KEYRING_AVAILABLE:
        try:
            credential = keyring.get_password("ocr-service", credential_name)
            if credential is not None:
                return credential
        except Exception:
            # Ignore keyring errors and fall back to the default
            pass
    
    return default


def set_credential(credential_name: str, value: str) -> bool:
    """
    Store a credential in the keyring.
    
    Args:
        credential_name: The name of the credential to store
        value: The value of the credential
        
    Returns:
        True if the credential was stored successfully, False otherwise
    """
    if not KEYRING_AVAILABLE:
        return False
    
    try:
        keyring.set_password("ocr-service", credential_name, value)
        return True
    except Exception:
        return False


def get_aws_credentials() -> Dict[str, Optional[str]]:
    """
    Get AWS credentials from the environment or keyring.
    
    Returns:
        Dictionary containing AWS credentials (access_key, secret_key, session_token)
    """
    return {
        'access_key': get_credential('AWS_ACCESS_KEY_ID'),
        'secret_key': get_credential('AWS_SECRET_ACCESS_KEY'),
        'session_token': get_credential('AWS_SESSION_TOKEN')
    }


# ============================================================================
# TLS Configuration Helpers
# ============================================================================

def create_tls_context(verify_cert: bool = True, ca_cert_path: Optional[str] = None) -> ssl.SSLContext:
    """
    Create a secure TLS context for client connections.
    
    Args:
        verify_cert: Whether to verify server certificates
        ca_cert_path: Optional path to a CA certificate file
        
    Returns:
        An SSLContext configured for secure TLS connections
    """
    # Create a context using TLS 1.3 (or the highest available protocol)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    
    # Set the minimum TLS version to 1.2
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Prefer TLS 1.3 if available
    if hasattr(ssl.TLSVersion, 'TLSv1_3'):
        context.maximum_version = ssl.TLSVersion.TLSv1_3
    
    # Set secure cipher suites
    context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20')
    
    # Disable insecure features
    context.options |= ssl.OP_NO_COMPRESSION  # Disable TLS compression
    context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE  # Prefer server's cipher choice
    
    # Certificate verification
    if verify_cert:
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True
        
        if ca_cert_path:
            context.load_verify_locations(cafile=ca_cert_path)
        else:
            # Use default system CA certificates
            context.load_default_certs()
    else:
        context.verify_mode = ssl.CERT_NONE
        context.check_hostname = False
    
    return context


def create_tls_server_context(cert_path: str, key_path: str) -> ssl.SSLContext:
    """
    Create a secure TLS context for server connections.
    
    Args:
        cert_path: Path to the server certificate file
        key_path: Path to the server private key file
        
    Returns:
        An SSLContext configured for secure TLS server connections
        
    Raises:
        FileNotFoundError: If the certificate or key file does not exist
        ssl.SSLError: If there is an error loading the certificate or key
    """
    # Create a context using TLS 1.3 (or the highest available protocol)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # Set the minimum TLS version to 1.2
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Prefer TLS 1.3 if available
    if hasattr(ssl.TLSVersion, 'TLSv1_3'):
        context.maximum_version = ssl.TLSVersion.TLSv1_3
    
    # Set secure cipher suites
    context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20')
    
    # Disable insecure features
    context.options |= ssl.OP_NO_COMPRESSION  # Disable TLS compression
    context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE  # Prefer server's cipher choice
    
    # Load the server certificate and private key
    context.load_cert_chain(cert_path, key_path)
    
    return context


# ============================================================================
# Secure Random String Generation
# ============================================================================

def generate_token_bytes(nbytes: Optional[int] = None) -> bytes:
    """
    Generate a secure random token as bytes.
    
    Args:
        nbytes: Number of random bytes to generate (default: 32)
        
    Returns:
        Random bytes
    """
    if nbytes is None:
        nbytes = 32  # 256 bits by default
    
    return secrets.token_bytes(nbytes)


def generate_token_hex(nbytes: Optional[int] = None) -> str:
    """
    Generate a secure random token as a hexadecimal string.
    
    Args:
        nbytes: Number of random bytes to generate (default: 32)
        
    Returns:
        Random hexadecimal string (twice the length of nbytes)
    """
    if nbytes is None:
        nbytes = 32  # 256 bits by default
    
    return secrets.token_hex(nbytes)


def generate_token_urlsafe(nbytes: Optional[int] = None) -> str:
    """
    Generate a secure URL-safe random token.
    
    Args:
        nbytes: Number of random bytes to generate (default: 32)
        
    Returns:
        Random URL-safe string
    """
    if nbytes is None:
        nbytes = 32  # 256 bits by default
    
    return secrets.token_urlsafe(nbytes)


def generate_password(length: int = 16, include_special: bool = True) -> str:
    """
    Generate a secure random password.
    
    Args:
        length: Length of the password (default: 16)
        include_special: Whether to include special characters (default: True)
        
    Returns:
        Secure random password
    """
    if length < 8:
        raise ValueError("Password length must be at least 8 characters")
    
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = string.punctuation if include_special else ''
    
    # Ensure at least one character from each required set
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits)
    ]
    
    if include_special and special:
        password.append(secrets.choice(special))
    
    # Fill the rest of the password with random characters
    all_chars = lowercase + uppercase + digits + special
    password.extend(secrets.choice(all_chars) for _ in range(length - len(password)))
    
    # Shuffle the password characters
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)