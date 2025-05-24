#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test module for security utilities in the Document Service.

This module contains unit tests for the security_utils.py module, which provides
functions for encryption, HMAC signatures, secure credential management,
TLS configuration, and secure random token generation.
"""

import base64
import json
import os
import ssl
from unittest import mock

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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


class TestKeyDerivation:
    """Test cases for key derivation functions."""

    def test_derive_key_generates_correct_size(self):
        """Test that derive_key generates a key of the correct size."""
        password = "test_password"
        key, salt = derive_key(password)
        
        assert len(key) == AES_KEY_SIZE
        assert len(salt) == SALT_SIZE

    def test_derive_key_with_same_password_and_salt_produces_same_key(self):
        """Test that derive_key produces the same key when given the same password and salt."""
        password = "test_password"
        salt = os.urandom(SALT_SIZE)
        
        key1, _ = derive_key(password, salt)
        key2, _ = derive_key(password, salt)
        
        assert key1 == key2

    def test_derive_key_with_different_passwords_produces_different_keys(self):
        """Test that derive_key produces different keys when given different passwords."""
        password1 = "test_password1"
        password2 = "test_password2"
        salt = os.urandom(SALT_SIZE)
        
        key1, _ = derive_key(password1, salt)
        key2, _ = derive_key(password2, salt)
        
        assert key1 != key2

    def test_derive_key_with_different_salts_produces_different_keys(self):
        """Test that derive_key produces different keys when given different salts."""
        password = "test_password"
        salt1 = os.urandom(SALT_SIZE)
        salt2 = os.urandom(SALT_SIZE)
        
        # Ensure salts are different (extremely unlikely they would be the same)
        if salt1 == salt2:
            salt2 = os.urandom(SALT_SIZE)
        
        key1, _ = derive_key(password, salt1)
        key2, _ = derive_key(password, salt2)
        
        assert key1 != key2


class TestEncryptionDecryption:
    """Test cases for encryption and decryption functions."""

    def test_encrypt_decrypt_cycle(self):
        """Test that data can be encrypted and then decrypted back to the original."""
        key = os.urandom(AES_KEY_SIZE)
        original_data = "This is a test message for encryption."
        
        encrypted = encrypt(original_data, key)
        decrypted = decrypt(encrypted, key)
        
        assert decrypted.decode('utf-8') == original_data

    def test_encrypt_produces_different_ciphertexts_for_same_data(self):
        """Test that encrypting the same data twice produces different ciphertexts due to random nonce."""
        key = os.urandom(AES_KEY_SIZE)
        data = "This is a test message for encryption."
        
        encrypted1 = encrypt(data, key)
        encrypted2 = encrypt(data, key)
        
        assert encrypted1['ciphertext'] != encrypted2['ciphertext']
        assert encrypted1['nonce'] != encrypted2['nonce']

    def test_decrypt_with_wrong_key_raises_error(self):
        """Test that decrypting with the wrong key raises an error."""
        correct_key = os.urandom(AES_KEY_SIZE)
        wrong_key = os.urandom(AES_KEY_SIZE)
        data = "This is a test message for encryption."
        
        encrypted = encrypt(data, correct_key)
        
        with pytest.raises(ValueError):
            decrypt(encrypted, wrong_key)

    def test_decrypt_with_tampered_ciphertext_raises_error(self):
        """Test that decrypting tampered ciphertext raises an error."""
        key = os.urandom(AES_KEY_SIZE)
        data = "This is a test message for encryption."
        
        encrypted = encrypt(data, key)
        
        # Tamper with the ciphertext
        ciphertext_bytes = base64.b64decode(encrypted['ciphertext'])
        tampered_byte = bytes([ciphertext_bytes[0] ^ 1])  # Flip one bit
        tampered_ciphertext = tampered_byte + ciphertext_bytes[1:]
        encrypted['ciphertext'] = base64.b64encode(tampered_ciphertext).decode('utf-8')
        
        with pytest.raises(ValueError):
            decrypt(encrypted, key)

    def test_encrypt_with_password_decrypt_with_password_cycle(self):
        """Test that data can be encrypted with a password and then decrypted with the same password."""
        password = "test_password"
        original_data = "This is a test message for password-based encryption."
        
        encrypted = encrypt_with_password(original_data, password)
        decrypted = decrypt_with_password(encrypted, password)
        
        assert decrypted.decode('utf-8') == original_data

    def test_decrypt_with_wrong_password_raises_error(self):
        """Test that decrypting with the wrong password raises an error."""
        correct_password = "correct_password"
        wrong_password = "wrong_password"
        data = "This is a test message for password-based encryption."
        
        encrypted = encrypt_with_password(data, correct_password)
        
        with pytest.raises(ValueError):
            decrypt_with_password(encrypted, wrong_password)

    def test_encrypt_field_decrypt_field_cycle(self):
        """Test that field data can be encrypted and then decrypted back to the original."""
        key = os.urandom(AES_KEY_SIZE)
        original_data = "sensitive-pii-data@example.com"
        
        encrypted = encrypt_field(original_data, key)
        decrypted = decrypt_field(encrypted, key)
        
        assert decrypted == original_data
        
    def test_encrypt_field_format(self):
        """Test that encrypt_field produces output in the expected format (ciphertext:nonce)."""
        key = os.urandom(AES_KEY_SIZE)
        data = "sensitive-pii-data@example.com"
        
        encrypted = encrypt_field(data, key)
        
        # Check that the encrypted field has the expected format (ciphertext:nonce)
        assert ':' in encrypted
        parts = encrypted.split(':', 1)
        assert len(parts) == 2
        
        # Verify both parts are valid base64
        try:
            base64.b64decode(parts[0])  # ciphertext
            base64.b64decode(parts[1])  # nonce
        except Exception:
            pytest.fail("Encrypted field parts are not valid base64")

    def test_decrypt_field_with_invalid_format_raises_error(self):
        """Test that decrypt_field raises an error when given data in an invalid format."""
        key = os.urandom(AES_KEY_SIZE)
        invalid_data = "not-a-valid-encrypted-field"  # Missing the colon separator
        
        with pytest.raises(ValueError):
            decrypt_field(invalid_data, key)


class TestHMACSignature:
    """Test cases for HMAC signature generation and verification functions."""

    def test_generate_hmac_signature_produces_expected_format(self):
        """Test that generate_hmac_signature produces a hex string of the expected length."""
        data = "This is a test message for HMAC signing."
        secret_key = "test_secret_key"
        
        signature = generate_hmac_signature(data, secret_key)
        
        # SHA-256 produces a 32-byte (64 hex character) digest
        assert len(signature) == 64
        # Verify it's a valid hex string
        assert all(c in "0123456789abcdef" for c in signature.lower())

    def test_verify_hmac_signature_with_valid_signature_returns_true(self):
        """Test that verify_hmac_signature returns True for a valid signature."""
        data = "This is a test message for HMAC signing."
        secret_key = "test_secret_key"
        
        signature = generate_hmac_signature(data, secret_key)
        result = verify_hmac_signature(data, signature, secret_key)
        
        assert result is True

    def test_verify_hmac_signature_with_invalid_signature_returns_false(self):
        """Test that verify_hmac_signature returns False for an invalid signature."""
        data = "This is a test message for HMAC signing."
        secret_key = "test_secret_key"
        invalid_signature = "0" * 64  # A fake signature of the right length
        
        result = verify_hmac_signature(data, invalid_signature, secret_key)
        
        assert result is False

    def test_verify_hmac_signature_with_tampered_data_returns_false(self):
        """Test that verify_hmac_signature returns False if the data has been tampered with."""
        original_data = "This is a test message for HMAC signing."
        tampered_data = "This is a tampered message for HMAC signing."
        secret_key = "test_secret_key"
        
        signature = generate_hmac_signature(original_data, secret_key)
        result = verify_hmac_signature(tampered_data, signature, secret_key)
        
        assert result is False

    def test_verify_hmac_signature_with_wrong_key_returns_false(self):
        """Test that verify_hmac_signature returns False if the wrong key is used."""
        data = "This is a test message for HMAC signing."
        correct_key = "correct_secret_key"
        wrong_key = "wrong_secret_key"
        
        signature = generate_hmac_signature(data, correct_key)
        result = verify_hmac_signature(data, signature, wrong_key)
        
        assert result is False

    def test_hmac_signature_with_json_payload(self):
        """Test HMAC signature generation and verification with a JSON payload."""
        payload = {
            "application_id": "app-123456",
            "status": "approved",
            "timestamp": "2023-05-15T14:30:00Z"
        }
        json_data = json.dumps(payload, sort_keys=True)
        secret_key = "webhook_secret_key"
        
        signature = generate_hmac_signature(json_data, secret_key)
        result = verify_hmac_signature(json_data, signature, secret_key)
        
        assert result is True


class TestSecureTokenGeneration:
    """Test cases for secure token generation functions."""

    def test_generate_secure_token_length(self):
        """Test that generate_secure_token produces a token of the expected length."""
        token = generate_secure_token()
        
        # The token is base64 encoded, so the length will be approximately 4/3 of the byte size
        # but may vary slightly due to padding. We'll check it's in a reasonable range.
        # For TOKEN_SIZE=32, the base64 encoded length should be around 43-44 characters
        assert 40 <= len(token) <= 48

    def test_generate_secure_token_with_custom_size(self):
        """Test that generate_secure_token respects the custom size parameter."""
        custom_size = 16  # Half the default size
        token = generate_secure_token(custom_size)
        
        # For custom_size=16, the base64 encoded length should be around 21-24 characters
        assert 20 <= len(token) <= 28

    def test_generate_secure_token_uniqueness(self):
        """Test that generate_secure_token produces unique tokens on each call."""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        assert token1 != token2

    def test_generate_secure_hex_token_length(self):
        """Test that generate_secure_hex_token produces a token of the expected length."""
        token = generate_secure_hex_token()
        
        # Each byte becomes 2 hex characters, so the length should be 2 * TOKEN_SIZE
        assert len(token) == 2 * TOKEN_SIZE

    def test_generate_secure_hex_token_with_custom_size(self):
        """Test that generate_secure_hex_token respects the custom size parameter."""
        custom_size = 16  # Half the default size
        token = generate_secure_hex_token(custom_size)
        
        assert len(token) == 2 * custom_size

    def test_generate_secure_hex_token_format(self):
        """Test that generate_secure_hex_token produces a valid hexadecimal string."""
        token = generate_secure_hex_token()
        
        # Check that the token contains only hexadecimal characters
        assert all(c in "0123456789abcdef" for c in token.lower())

    def test_generate_secure_password_length(self):
        """Test that generate_secure_password produces a password of the expected length."""
        password = generate_secure_password()
        
        # Default length is 16
        assert len(password) == 16

    def test_generate_secure_password_with_custom_length(self):
        """Test that generate_secure_password respects the custom length parameter."""
        custom_length = 20
        password = generate_secure_password(custom_length)
        
        assert len(password) == custom_length

    def test_generate_secure_password_complexity(self):
        """Test that generate_secure_password produces passwords with the required complexity."""
        password = generate_secure_password()
        
        # Check that the password contains at least one character from each required set
        has_uppercase = any(c.isupper() for c in password)
        has_lowercase = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        assert has_uppercase
        assert has_lowercase
        assert has_digit
        assert has_special

    def test_generate_secure_password_minimum_length(self):
        """Test that generate_secure_password enforces a minimum length of 8 characters."""
        password = generate_secure_password(4)  # Try to request a too-short password
        
        # Should be forced to minimum length of 8
        assert len(password) >= 8


class TestTLSContext:
    """Test cases for TLS context creation function."""

    @mock.patch('os.path.isfile')
    @mock.patch('ssl.SSLContext')
    def test_create_tls_context_with_valid_files(self, mock_ssl_context, mock_isfile):
        """Test that create_tls_context creates a context with the expected settings when given valid files."""
        # Mock the file existence check to return True
        mock_isfile.return_value = True
        
        # Create a mock SSL context object
        mock_context = mock.MagicMock()
        mock_ssl_context.return_value = mock_context
        
        # Call the function with test file paths
        cert_file = "/path/to/cert.pem"
        key_file = "/path/to/key.pem"
        ca_file = "/path/to/ca.pem"
        
        result = create_tls_context(cert_file, key_file, ca_file)
        
        # Verify the context was created with the expected settings
        mock_ssl_context.assert_called_once_with(ssl.PROTOCOL_TLS_SERVER)
        mock_context.set_ciphers.assert_called_once()
        mock_context.load_cert_chain.assert_called_once_with(certfile=cert_file, keyfile=key_file)
        mock_context.load_verify_locations.assert_called_once_with(cafile=ca_file)
        assert mock_context.verify_mode == ssl.CERT_REQUIRED
        assert mock_context.check_hostname is True
        
        # Verify the result is the mock context
        assert result == mock_context

    @mock.patch('os.path.isfile')
    def test_create_tls_context_with_missing_cert_file(self, mock_isfile):
        """Test that create_tls_context raises an error when the certificate file is missing."""
        # Mock the file existence check to return False for the cert file
        def mock_isfile_side_effect(path):
            if path == "/path/to/cert.pem":
                return False
            return True
        
        mock_isfile.side_effect = mock_isfile_side_effect
        
        # Call the function with test file paths
        cert_file = "/path/to/cert.pem"  # This file doesn't exist
        key_file = "/path/to/key.pem"
        
        with pytest.raises(FileNotFoundError) as excinfo:
            create_tls_context(cert_file, key_file)
        
        # Verify the error message mentions the missing file
        assert cert_file in str(excinfo.value)

    @mock.patch('os.path.isfile')
    def test_create_tls_context_with_missing_key_file(self, mock_isfile):
        """Test that create_tls_context raises an error when the key file is missing."""
        # Mock the file existence check to return False for the key file
        def mock_isfile_side_effect(path):
            if path == "/path/to/key.pem":
                return False
            return True
        
        mock_isfile.side_effect = mock_isfile_side_effect
        
        # Call the function with test file paths
        cert_file = "/path/to/cert.pem"
        key_file = "/path/to/key.pem"  # This file doesn't exist
        
        with pytest.raises(FileNotFoundError) as excinfo:
            create_tls_context(cert_file, key_file)
        
        # Verify the error message mentions the missing file
        assert key_file in str(excinfo.value)

    @mock.patch('os.path.isfile')
    def test_create_tls_context_with_missing_ca_file(self, mock_isfile):
        """Test that create_tls_context raises an error when the CA file is missing."""
        # Mock the file existence check to return False for the CA file
        def mock_isfile_side_effect(path):
            if path == "/path/to/ca.pem":
                return False
            return True
        
        mock_isfile.side_effect = mock_isfile_side_effect
        
        # Call the function with test file paths
        cert_file = "/path/to/cert.pem"
        key_file = "/path/to/key.pem"
        ca_file = "/path/to/ca.pem"  # This file doesn't exist
        
        with pytest.raises(FileNotFoundError) as excinfo:
            create_tls_context(cert_file, key_file, ca_file)
        
        # Verify the error message mentions the missing file
        assert ca_file in str(excinfo.value)


class TestAWSCredentialSecurity:
    """Test cases for AWS credential security function."""

    @mock.patch('os.environ')
    def test_secure_aws_credentials_with_complete_credentials(self, mock_environ):
        """Test that secure_aws_credentials returns properly secured credentials when given complete credentials."""
        # Set up the mock environment
        mock_environ.get.return_value = 'development'
        
        # Create test credentials
        credentials = {
            'aws_access_key_id': 'test_access_key',
            'aws_secret_access_key': 'test_secret_key',
            'region': 'us-west-2'
        }
        
        # Call the function
        secured_creds = secure_aws_credentials(credentials)
        
        # Verify the credentials were properly secured
        assert secured_creds['aws_access_key_id'] == 'test_access_key'
        assert secured_creds['aws_secret_access_key'] == 'test_secret_key'
        assert secured_creds['region'] == 'us-west-2'
        assert secured_creds['use_ssl'] is True
        assert secured_creds['verify'] is True

    @mock.patch('os.environ')
    def test_secure_aws_credentials_with_environment_variables(self, mock_environ):
        """Test that secure_aws_credentials uses environment variables when credentials are not provided."""
        # Set up the mock environment
        mock_environ.get.return_value = 'staging'
        mock_environ.__contains__.side_effect = lambda x: x in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION']
        mock_environ.__getitem__.side_effect = lambda x: {
            'AWS_ACCESS_KEY_ID': 'env_access_key',
            'AWS_SECRET_ACCESS_KEY': 'env_secret_key',
            'AWS_REGION': 'us-east-1'
        }[x]
        
        # Create test credentials with missing keys
        credentials = {}
        
        # Call the function
        secured_creds = secure_aws_credentials(credentials)
        
        # Verify the credentials were properly secured using environment variables
        assert secured_creds['aws_access_key_id'] == 'env_access_key'
        assert secured_creds['aws_secret_access_key'] == 'env_secret_key'
        assert secured_creds['region'] == 'us-east-1'
        assert secured_creds['use_ssl'] is True
        assert secured_creds['verify'] is True

    @mock.patch('os.environ')
    def test_secure_aws_credentials_with_s3_bucket_naming(self, mock_environ):
        """Test that secure_aws_credentials properly handles S3 bucket naming conventions."""
        # Set up the mock environment
        mock_environ.get.return_value = 'production'
        
        # Create test credentials with S3 configuration
        credentials = {
            'aws_access_key_id': 'test_access_key',
            'aws_secret_access_key': 'test_secret_key',
            'region': 'us-west-2',
            's3': {
                'bucket_name': 'mca-documents'
            }
        }
        
        # Call the function
        secured_creds = secure_aws_credentials(credentials)
        
        # Verify the S3 bucket name was properly modified for the environment
        assert secured_creds['s3']['bucket_name'] == 'mca-documents-production'

    @mock.patch('os.environ')
    def test_secure_aws_credentials_with_missing_required_credentials(self, mock_environ):
        """Test that secure_aws_credentials raises an error when required credentials are missing."""
        # Set up the mock environment to not have the required environment variables
        mock_environ.get.return_value = 'development'
        mock_environ.__contains__.return_value = False
        
        # Create test credentials with missing required keys
        credentials = {
            # Missing aws_access_key_id and aws_secret_access_key
            'region': 'us-west-2'
        }
        
        # Call the function and expect an error
        with pytest.raises(ValueError) as excinfo:
            secure_aws_credentials(credentials)
        
        # Verify the error message mentions the missing credential
        assert 'aws_access_key_id' in str(excinfo.value)