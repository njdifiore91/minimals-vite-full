#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for security utilities in the Document Service.

Tests verify that the encryption, HMAC signature, and secure credential management 
functions work correctly. Ensures that data security measures are properly implemented.
"""

import os
import ssl
import base64
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Tuple

from document_service.utils.security_utils import (
    derive_key,
    encrypt,
    decrypt,
    encrypt_with_password,
    decrypt_with_password,
    generate_hmac_signature,
    verify_hmac_signature,
    generate_secure_token,
    generate_secure_hex_token,
    generate_secure_password,
    create_tls_context,
    secure_aws_credentials,
    encrypt_field,
    decrypt_field,
    AES_KEY_SIZE,
    SALT_SIZE,
    NONCE_SIZE,
    TOKEN_SIZE
)


# ============================================================================
# Test Key Derivation Functions
# ============================================================================

class TestKeyDerivation:
    """Tests for the key derivation functions."""

    def test_derive_key_generates_correct_size(self):
        """Test that derive_key generates a key of the correct size."""
        password = "test-password"
        key, salt = derive_key(password)
        
        assert len(key) == AES_KEY_SIZE, f"Key should be {AES_KEY_SIZE} bytes, got {len(key)}"
        assert len(salt) == SALT_SIZE, f"Salt should be {SALT_SIZE} bytes, got {len(salt)}"

    def test_derive_key_is_deterministic_with_same_salt(self):
        """Test that derive_key produces the same key when given the same password and salt."""
        password = "test-password"
        
        # First derivation
        key1, salt = derive_key(password)
        
        # Second derivation with the same salt
        key2, _ = derive_key(password, salt)
        
        assert key1 == key2, "Keys should be identical when derived with the same password and salt"

    def test_derive_key_different_with_different_passwords(self):
        """Test that derive_key produces different keys for different passwords with the same salt."""
        password1 = "test-password-1"
        password2 = "test-password-2"
        salt = os.urandom(SALT_SIZE)
        
        key1, _ = derive_key(password1, salt)
        key2, _ = derive_key(password2, salt)
        
        assert key1 != key2, "Keys should be different when derived with different passwords"

    def test_derive_key_different_with_different_salts(self):
        """Test that derive_key produces different keys for the same password with different salts."""
        password = "test-password"
        
        # First derivation with random salt
        key1, _ = derive_key(password)
        
        # Second derivation with a different random salt
        key2, _ = derive_key(password)
        
        assert key1 != key2, "Keys should be different when derived with different salts"


# ============================================================================
# Test Encryption and Decryption Functions
# ============================================================================

class TestEncryptionDecryption:
    """Tests for the encryption and decryption functions."""

    @pytest.fixture
    def test_key(self) -> bytes:
        """Provides a test encryption key."""
        return os.urandom(AES_KEY_SIZE)

    def test_encrypt_produces_valid_format(self, test_key):
        """Test that encrypt produces a dictionary with the expected fields."""
        data = "test-data"
        encrypted = encrypt(data, test_key)
        
        assert 'ciphertext' in encrypted, "Encrypted data should contain 'ciphertext' field"
        assert 'nonce' in encrypted, "Encrypted data should contain 'nonce' field"
        
        # Verify base64 encoding
        try:
            base64.b64decode(encrypted['ciphertext'])
            base64.b64decode(encrypted['nonce'])
        except Exception as e:
            pytest.fail(f"Encrypted data fields should be valid base64: {e}")

    def test_encrypt_different_nonce_each_time(self, test_key):
        """Test that encrypt uses a different nonce each time."""
        data = "test-data"
        
        encrypted1 = encrypt(data, test_key)
        encrypted2 = encrypt(data, test_key)
        
        assert encrypted1['nonce'] != encrypted2['nonce'], "Nonce should be different for each encryption"

    def test_encrypt_decrypt_roundtrip_string(self, test_key):
        """Test that data can be encrypted and then decrypted back to the original string."""
        original_data = "test-data-string"
        
        # Encrypt the data
        encrypted = encrypt(original_data, test_key)
        
        # Decrypt the data
        decrypted = decrypt(encrypted, test_key)
        
        assert decrypted.decode('utf-8') == original_data, "Decrypted data should match the original"

    def test_encrypt_decrypt_roundtrip_bytes(self, test_key):
        """Test that data can be encrypted and then decrypted back to the original bytes."""
        original_data = b"test-data-bytes"
        
        # Encrypt the data
        encrypted = encrypt(original_data, test_key)
        
        # Decrypt the data
        decrypted = decrypt(encrypted, test_key)
        
        assert decrypted == original_data, "Decrypted data should match the original"

    def test_decrypt_fails_with_wrong_key(self, test_key):
        """Test that decrypt fails when using the wrong key."""
        data = "test-data"
        wrong_key = os.urandom(AES_KEY_SIZE)  # Different key
        
        # Encrypt with the correct key
        encrypted = encrypt(data, test_key)
        
        # Attempt to decrypt with the wrong key
        with pytest.raises(ValueError):
            decrypt(encrypted, wrong_key)

    def test_decrypt_fails_with_tampered_ciphertext(self, test_key):
        """Test that decrypt fails when the ciphertext has been tampered with."""
        data = "test-data"
        
        # Encrypt the data
        encrypted = encrypt(data, test_key)
        
        # Tamper with the ciphertext
        ciphertext_bytes = base64.b64decode(encrypted['ciphertext'])
        tampered_bytes = bytearray(ciphertext_bytes)
        tampered_bytes[0] = (tampered_bytes[0] + 1) % 256  # Change the first byte
        encrypted['ciphertext'] = base64.b64encode(tampered_bytes).decode('utf-8')
        
        # Attempt to decrypt the tampered data
        with pytest.raises(ValueError):
            decrypt(encrypted, test_key)

    def test_encrypt_with_password(self):
        """Test that encrypt_with_password correctly encrypts data."""
        password = "test-password"
        data = "test-data"
        
        encrypted = encrypt_with_password(data, password)
        
        assert 'ciphertext' in encrypted, "Encrypted data should contain 'ciphertext' field"
        assert 'nonce' in encrypted, "Encrypted data should contain 'nonce' field"
        assert 'salt' in encrypted, "Encrypted data should contain 'salt' field"

    def test_encrypt_decrypt_with_password_roundtrip(self):
        """Test that data can be encrypted and decrypted with a password."""
        password = "test-password"
        original_data = "test-data-string"
        
        # Encrypt with password
        encrypted = encrypt_with_password(original_data, password)
        
        # Decrypt with password
        decrypted = decrypt_with_password(encrypted, password)
        
        assert decrypted.decode('utf-8') == original_data, "Decrypted data should match the original"

    def test_decrypt_with_password_fails_with_wrong_password(self):
        """Test that decrypt_with_password fails with the wrong password."""
        correct_password = "correct-password"
        wrong_password = "wrong-password"
        data = "test-data"
        
        # Encrypt with the correct password
        encrypted = encrypt_with_password(data, correct_password)
        
        # Attempt to decrypt with the wrong password
        with pytest.raises(ValueError):
            decrypt_with_password(encrypted, wrong_password)


# ============================================================================
# Test HMAC Signature Functions
# ============================================================================

class TestHmacSignature:
    """Tests for the HMAC signature generation and verification functions."""

    @pytest.fixture
    def test_secret_key(self) -> bytes:
        """Provides a test secret key for HMAC signatures."""
        return os.urandom(32)

    def test_generate_hmac_signature_produces_hex_string(self, test_secret_key):
        """Test that generate_hmac_signature produces a hexadecimal string."""
        data = "test-data"
        signature = generate_hmac_signature(data, test_secret_key)
        
        # Check that the signature is a hex string of the correct length (64 chars for SHA-256)
        assert len(signature) == 64, f"HMAC-SHA256 signature should be 64 characters, got {len(signature)}"
        assert all(c in '0123456789abcdef' for c in signature), "Signature should be a hexadecimal string"

    def test_generate_hmac_signature_is_deterministic(self, test_secret_key):
        """Test that generate_hmac_signature produces the same signature for the same data and key."""
        data = "test-data"
        
        signature1 = generate_hmac_signature(data, test_secret_key)
        signature2 = generate_hmac_signature(data, test_secret_key)
        
        assert signature1 == signature2, "Signatures should be identical for the same data and key"

    def test_generate_hmac_signature_different_for_different_data(self, test_secret_key):
        """Test that generate_hmac_signature produces different signatures for different data."""
        data1 = "test-data-1"
        data2 = "test-data-2"
        
        signature1 = generate_hmac_signature(data1, test_secret_key)
        signature2 = generate_hmac_signature(data2, test_secret_key)
        
        assert signature1 != signature2, "Signatures should be different for different data"

    def test_verify_hmac_signature_valid(self, test_secret_key):
        """Test that verify_hmac_signature correctly verifies a valid signature."""
        data = "test-data"
        signature = generate_hmac_signature(data, test_secret_key)
        
        is_valid = verify_hmac_signature(data, signature, test_secret_key)
        
        assert is_valid, "Signature verification should succeed for a valid signature"

    def test_verify_hmac_signature_invalid_for_different_data(self, test_secret_key):
        """Test that verify_hmac_signature fails for a signature generated with different data."""
        data1 = "test-data-1"
        data2 = "test-data-2"
        
        # Generate signature for data1
        signature = generate_hmac_signature(data1, test_secret_key)
        
        # Verify against data2
        is_valid = verify_hmac_signature(data2, signature, test_secret_key)
        
        assert not is_valid, "Signature verification should fail for different data"

    def test_verify_hmac_signature_invalid_for_different_key(self):
        """Test that verify_hmac_signature fails for a signature generated with a different key."""
        data = "test-data"
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        
        # Generate signature with key1
        signature = generate_hmac_signature(data, key1)
        
        # Verify with key2
        is_valid = verify_hmac_signature(data, signature, key2)
        
        assert not is_valid, "Signature verification should fail for a different key"

    def test_verify_hmac_signature_with_tampered_signature(self, test_secret_key):
        """Test that verify_hmac_signature fails for a tampered signature."""
        data = "test-data"
        
        # Generate a valid signature
        signature = generate_hmac_signature(data, test_secret_key)
        
        # Tamper with the signature
        tampered_signature = signature[:-1] + ('0' if signature[-1] != '0' else '1')
        
        # Verify the tampered signature
        is_valid = verify_hmac_signature(data, tampered_signature, test_secret_key)
        
        assert not is_valid, "Signature verification should fail for a tampered signature"


# ============================================================================
# Test Secure Token Generation Functions
# ============================================================================

class TestSecureTokenGeneration:
    """Tests for the secure token generation functions."""

    def test_generate_secure_token_length(self):
        """Test that generate_secure_token produces a token of the expected length."""
        token = generate_secure_token()
        
        # URL-safe base64 encoding: 4 characters for every 3 bytes, with padding
        # For 32 bytes, we expect approximately 43 characters (32 * 4/3 = 42.67, rounded up to 43)
        # The exact length can vary slightly due to padding, but should be close to this value
        assert 42 <= len(token) <= 44, f"Token length should be approximately 43 characters, got {len(token)}"

    def test_generate_secure_token_custom_size(self):
        """Test that generate_secure_token respects the custom size parameter."""
        size = 16  # 16 bytes
        token = generate_secure_token(size)
        
        # For 16 bytes, we expect approximately 22 characters (16 * 4/3 = 21.33, rounded up to 22)
        assert 21 <= len(token) <= 23, f"Token length should be approximately 22 characters, got {len(token)}"

    def test_generate_secure_token_uniqueness(self):
        """Test that generate_secure_token produces unique tokens."""
        tokens = [generate_secure_token() for _ in range(100)]
        unique_tokens = set(tokens)
        
        assert len(unique_tokens) == 100, "All generated tokens should be unique"

    def test_generate_secure_hex_token_length(self):
        """Test that generate_secure_hex_token produces a token of the expected length."""
        token = generate_secure_hex_token()
        
        # Hex encoding: 2 characters for every byte
        # For 32 bytes, we expect exactly 64 characters
        assert len(token) == 64, f"Hex token length should be 64 characters, got {len(token)}"

    def test_generate_secure_hex_token_custom_size(self):
        """Test that generate_secure_hex_token respects the custom size parameter."""
        size = 16  # 16 bytes
        token = generate_secure_hex_token(size)
        
        # For 16 bytes, we expect exactly 32 characters
        assert len(token) == 32, f"Hex token length should be 32 characters, got {len(token)}"

    def test_generate_secure_hex_token_is_hex(self):
        """Test that generate_secure_hex_token produces a valid hexadecimal string."""
        token = generate_secure_hex_token()
        
        assert all(c in '0123456789abcdef' for c in token), "Hex token should only contain hexadecimal characters"

    def test_generate_secure_password_length(self):
        """Test that generate_secure_password produces a password of the expected length."""
        password = generate_secure_password()
        
        # Default length is 16
        assert len(password) == 16, f"Password length should be 16 characters, got {len(password)}"

    def test_generate_secure_password_custom_length(self):
        """Test that generate_secure_password respects the custom length parameter."""
        length = 24
        password = generate_secure_password(length)
        
        assert len(password) == 24, f"Password length should be 24 characters, got {len(password)}"

    def test_generate_secure_password_minimum_length(self):
        """Test that generate_secure_password enforces a minimum length of 8."""
        # Try to generate a password with length 4
        password = generate_secure_password(4)
        
        # Should enforce minimum length of 8
        assert len(password) >= 8, f"Password length should be at least 8 characters, got {len(password)}"

    def test_generate_secure_password_complexity(self):
        """Test that generate_secure_password produces passwords with the required complexity."""
        password = generate_secure_password()
        
        # Check for at least one character from each required set
        has_uppercase = any(c.isupper() for c in password)
        has_lowercase = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        assert has_uppercase, "Password should contain at least one uppercase letter"
        assert has_lowercase, "Password should contain at least one lowercase letter"
        assert has_digit, "Password should contain at least one digit"
        assert has_special, "Password should contain at least one special character"


# ============================================================================
# Test TLS Configuration Functions
# ============================================================================

class TestTlsConfiguration:
    """Tests for the TLS configuration functions."""

    @pytest.fixture
    def test_cert_files(self) -> Tuple[str, str, str]:
        """Creates temporary certificate files for testing."""
        # Create temporary files for certificates
        cert_file = tempfile.NamedTemporaryFile(delete=False)
        key_file = tempfile.NamedTemporaryFile(delete=False)
        ca_file = tempfile.NamedTemporaryFile(delete=False)
        
        # Write some dummy content to the files
        cert_file.write(b'DUMMY CERTIFICATE')
        key_file.write(b'DUMMY PRIVATE KEY')
        ca_file.write(b'DUMMY CA CERTIFICATE')
        
        # Close the files
        cert_file.close()
        key_file.close()
        ca_file.close()
        
        # Return the file paths
        yield cert_file.name, key_file.name, ca_file.name
        
        # Clean up the files
        os.unlink(cert_file.name)
        os.unlink(key_file.name)
        os.unlink(ca_file.name)

    @patch('ssl.SSLContext')
    def test_create_tls_context_with_valid_files(self, mock_ssl_context, test_cert_files):
        """Test that create_tls_context creates a context with valid certificate files."""
        cert_file, key_file, ca_file = test_cert_files
        mock_context = MagicMock()
        mock_ssl_context.return_value = mock_context
        
        context = create_tls_context(cert_file, key_file, ca_file)
        
        # Verify that the context was created and configured correctly
        mock_ssl_context.assert_called_once()
        mock_context.load_cert_chain.assert_called_once_with(certfile=cert_file, keyfile=key_file)
        mock_context.load_verify_locations.assert_called_once_with(cafile=ca_file)
        assert mock_context.verify_mode == ssl.CERT_REQUIRED
        assert mock_context.check_hostname is True

    def test_create_tls_context_fails_with_nonexistent_cert_file(self, test_cert_files):
        """Test that create_tls_context fails when the certificate file doesn't exist."""
        _, key_file, ca_file = test_cert_files
        nonexistent_file = "/nonexistent/file.crt"
        
        with pytest.raises(FileNotFoundError):
            create_tls_context(nonexistent_file, key_file, ca_file)

    def test_create_tls_context_fails_with_nonexistent_key_file(self, test_cert_files):
        """Test that create_tls_context fails when the key file doesn't exist."""
        cert_file, _, ca_file = test_cert_files
        nonexistent_file = "/nonexistent/file.key"
        
        with pytest.raises(FileNotFoundError):
            create_tls_context(cert_file, nonexistent_file, ca_file)

    def test_create_tls_context_fails_with_nonexistent_ca_file(self, test_cert_files):
        """Test that create_tls_context fails when the CA file doesn't exist."""
        cert_file, key_file, _ = test_cert_files
        nonexistent_file = "/nonexistent/file.ca"
        
        with pytest.raises(FileNotFoundError):
            create_tls_context(cert_file, key_file, nonexistent_file)

    @patch('ssl.SSLContext')
    def test_create_tls_context_without_ca_file(self, mock_ssl_context, test_cert_files):
        """Test that create_tls_context works without a CA file."""
        cert_file, key_file, _ = test_cert_files
        mock_context = MagicMock()
        mock_ssl_context.return_value = mock_context
        
        context = create_tls_context(cert_file, key_file)
        
        # Verify that the context was created and configured correctly
        mock_ssl_context.assert_called_once()
        mock_context.load_cert_chain.assert_called_once_with(certfile=cert_file, keyfile=key_file)
        mock_context.load_verify_locations.assert_not_called()
        assert mock_context.verify_mode == ssl.CERT_REQUIRED
        assert mock_context.check_hostname is True


# ============================================================================
# Test AWS Credential Security Functions
# ============================================================================

class TestAwsCredentialSecurity:
    """Tests for the AWS credential security functions."""

    @pytest.fixture
    def test_aws_credentials(self) -> Dict[str, Any]:
        """Provides test AWS credentials."""
        return {
            'aws_access_key_id': 'test-access-key',
            'aws_secret_access_key': 'test-secret-key',
            'region': 'us-west-2'
        }

    def test_secure_aws_credentials_preserves_required_keys(self, test_aws_credentials):
        """Test that secure_aws_credentials preserves required credential keys."""
        secured = secure_aws_credentials(test_aws_credentials)
        
        assert 'aws_access_key_id' in secured, "Access key ID should be preserved"
        assert 'aws_secret_access_key' in secured, "Secret access key should be preserved"
        assert 'region' in secured, "Region should be preserved"

    def test_secure_aws_credentials_sets_secure_defaults(self, test_aws_credentials):
        """Test that secure_aws_credentials sets secure defaults."""
        secured = secure_aws_credentials(test_aws_credentials)
        
        assert secured.get('use_ssl') is True, "SSL should be enabled by default"
        assert secured.get('verify') is True, "Certificate verification should be enabled by default"

    def test_secure_aws_credentials_with_environment_variables(self, test_aws_credentials, monkeypatch):
        """Test that secure_aws_credentials uses environment variables when available."""
        # Set environment variables
        monkeypatch.setenv('ENVIRONMENT', 'staging')
        monkeypatch.setenv('AWS_REGION', 'eu-west-1')
        monkeypatch.setenv('AWS_SESSION_TOKEN', 'test-session-token')
        
        # Remove region from credentials to test fallback to environment variable
        credentials = test_aws_credentials.copy()
        del credentials['region']
        
        secured = secure_aws_credentials(credentials)
        
        assert secured['region'] == 'eu-west-1', "Region should be taken from environment variable"
        assert secured['aws_session_token'] == 'test-session-token', "Session token should be taken from environment variable"

    def test_secure_aws_credentials_with_s3_bucket_naming(self, test_aws_credentials, monkeypatch):
        """Test that secure_aws_credentials applies environment-specific bucket naming."""
        # Set environment variable
        monkeypatch.setenv('ENVIRONMENT', 'staging')
        
        # Add S3 configuration with bucket name
        credentials = test_aws_credentials.copy()
        credentials['s3'] = {'bucket_name': 'mca-documents'}
        
        secured = secure_aws_credentials(credentials)
        
        assert secured['s3']['bucket_name'] == 'mca-documents-staging', "Bucket name should include environment suffix"

    def test_secure_aws_credentials_with_existing_environment_suffix(self, test_aws_credentials, monkeypatch):
        """Test that secure_aws_credentials doesn't duplicate environment suffixes."""
        # Set environment variable
        monkeypatch.setenv('ENVIRONMENT', 'staging')
        
        # Add S3 configuration with bucket name that already has the environment suffix
        credentials = test_aws_credentials.copy()
        credentials['s3'] = {'bucket_name': 'mca-documents-staging'}
        
        secured = secure_aws_credentials(credentials)
        
        assert secured['s3']['bucket_name'] == 'mca-documents-staging', "Bucket name should not have duplicate environment suffix"

    def test_secure_aws_credentials_fails_without_required_keys(self):
        """Test that secure_aws_credentials fails when required keys are missing."""
        # Missing both required keys
        credentials = {'region': 'us-west-2'}
        
        with pytest.raises(ValueError):
            secure_aws_credentials(credentials)


# ============================================================================
# Test Field-Level Encryption Functions
# ============================================================================

class TestFieldLevelEncryption:
    """Tests for the field-level encryption functions."""

    @pytest.fixture
    def test_encryption_key(self) -> bytes:
        """Provides a test encryption key."""
        return os.urandom(AES_KEY_SIZE)

    def test_encrypt_field_format(self, test_encryption_key):
        """Test that encrypt_field produces a string in the expected format."""
        field_data = "sensitive-data"
        encrypted = encrypt_field(field_data, test_encryption_key)
        
        # Check that the result is a string with a colon separator
        assert isinstance(encrypted, str), "Encrypted field should be a string"
        assert ':' in encrypted, "Encrypted field should contain a colon separator"
        
        # Split and verify parts
        parts = encrypted.split(':', 1)
        assert len(parts) == 2, "Encrypted field should have exactly two parts"
        
        # Verify that parts are valid base64
        try:
            base64.b64decode(parts[0])  # ciphertext
            base64.b64decode(parts[1])  # nonce
        except Exception as e:
            pytest.fail(f"Encrypted field parts should be valid base64: {e}")

    def test_encrypt_decrypt_field_roundtrip(self, test_encryption_key):
        """Test that a field can be encrypted and then decrypted back to the original."""
        original_data = "sensitive-field-data"
        
        # Encrypt the field
        encrypted = encrypt_field(original_data, test_encryption_key)
        
        # Decrypt the field
        decrypted = decrypt_field(encrypted, test_encryption_key)
        
        assert decrypted == original_data, "Decrypted field should match the original"

    def test_encrypt_field_with_empty_data(self, test_encryption_key):
        """Test that encrypt_field handles empty data correctly."""
        empty_data = ""
        encrypted = encrypt_field(empty_data, test_encryption_key)
        
        assert encrypted == "", "Encrypted empty field should be an empty string"

    def test_decrypt_field_with_empty_data(self, test_encryption_key):
        """Test that decrypt_field handles empty data correctly."""
        empty_data = ""
        decrypted = decrypt_field(empty_data, test_encryption_key)
        
        assert decrypted == "", "Decrypted empty field should be an empty string"

    def test_decrypt_field_fails_with_invalid_format(self, test_encryption_key):
        """Test that decrypt_field fails when the encrypted data has an invalid format."""
        invalid_data = "invalid-format-without-colon"
        
        with pytest.raises(ValueError):
            decrypt_field(invalid_data, test_encryption_key)

    def test_decrypt_field_fails_with_wrong_key(self, test_encryption_key):
        """Test that decrypt_field fails when using the wrong key."""
        field_data = "sensitive-data"
        wrong_key = os.urandom(AES_KEY_SIZE)  # Different key
        
        # Encrypt with the correct key
        encrypted = encrypt_field(field_data, test_encryption_key)
        
        # Attempt to decrypt with the wrong key
        with pytest.raises(ValueError):
            decrypt_field(encrypted, wrong_key)