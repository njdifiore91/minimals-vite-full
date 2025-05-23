#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for security_utils.py module.

This module contains unit tests for the security utilities in the OCR Service,
including encryption, HMAC signatures, secure credential management,
TLS configuration, and secure random string generation.
"""

import base64
import hashlib
import hmac
import os
import ssl
import tempfile
import unittest
from unittest import mock
from typing import Dict, Optional, Tuple, Union, Any

# Import the module to test
from src.utils import security_utils


class TestAESEncryption(unittest.TestCase):
    """Test cases for AES-256 encryption and decryption functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Skip tests if cryptography is not available
        if not security_utils.CRYPTOGRAPHY_AVAILABLE:
            self.skipTest("cryptography package not available")
        
        # Test data
        self.test_password = "secure-test-password"
        self.test_data_str = "This is a test string to encrypt"
        self.test_data_bytes = b"This is a test byte string to encrypt"

    def test_generate_key_from_password(self):
        """Test generating a key from a password."""
        # Test with auto-generated salt
        key1, salt1 = security_utils.generate_key_from_password(self.test_password)
        
        # Verify key and salt properties
        self.assertEqual(len(key1), 32, "Key should be 32 bytes (256 bits)")
        self.assertEqual(len(salt1), 16, "Salt should be 16 bytes")
        
        # Test with provided salt
        key2, salt2 = security_utils.generate_key_from_password(self.test_password, salt1)
        
        # Verify that the same password and salt produce the same key
        self.assertEqual(key1, key2, "Same password and salt should produce the same key")
        self.assertEqual(salt1, salt2, "Salt should remain unchanged")
        
        # Test with different password
        key3, _ = security_utils.generate_key_from_password("different-password", salt1)
        
        # Verify that different passwords produce different keys
        self.assertNotEqual(key1, key3, "Different passwords should produce different keys")

    def test_encrypt_decrypt_data_string(self):
        """Test encrypting and decrypting string data."""
        # Generate a key
        key, _ = security_utils.generate_key_from_password(self.test_password)
        
        # Encrypt the test string
        encrypted = security_utils.encrypt_data(self.test_data_str, key)
        
        # Verify the encrypted data structure
        self.assertIn('ciphertext', encrypted, "Encrypted data should contain 'ciphertext'")
        self.assertIn('nonce', encrypted, "Encrypted data should contain 'nonce'")
        
        # Decrypt the data
        decrypted = security_utils.decrypt_data(encrypted, key)
        
        # Verify the decrypted data
        self.assertEqual(decrypted.decode('utf-8'), self.test_data_str, 
                         "Decrypted data should match the original")

    def test_encrypt_decrypt_data_bytes(self):
        """Test encrypting and decrypting byte data."""
        # Generate a key
        key, _ = security_utils.generate_key_from_password(self.test_password)
        
        # Encrypt the test bytes
        encrypted = security_utils.encrypt_data(self.test_data_bytes, key)
        
        # Decrypt the data
        decrypted = security_utils.decrypt_data(encrypted, key)
        
        # Verify the decrypted data
        self.assertEqual(decrypted, self.test_data_bytes, 
                         "Decrypted data should match the original")

    def test_decrypt_with_wrong_key(self):
        """Test decryption with an incorrect key."""
        # Generate keys
        key1, _ = security_utils.generate_key_from_password(self.test_password)
        key2, _ = security_utils.generate_key_from_password("wrong-password")
        
        # Encrypt with key1
        encrypted = security_utils.encrypt_data(self.test_data_str, key1)
        
        # Attempt to decrypt with key2
        with self.assertRaises(ValueError, msg="Decryption with wrong key should fail"):
            security_utils.decrypt_data(encrypted, key2)

    def test_encrypt_decrypt_file(self):
        """Test encrypting and decrypting a file."""
        # Create temporary files for testing
        with tempfile.NamedTemporaryFile(delete=False) as original_file:
            original_file.write(self.test_data_bytes)
            original_path = original_file.name
        
        encrypted_path = original_path + ".enc"
        decrypted_path = original_path + ".dec"
        
        try:
            # Encrypt the file
            security_utils.encrypt_file(original_path, encrypted_path, self.test_password)
            
            # Verify the encrypted file exists and is different from the original
            self.assertTrue(os.path.exists(encrypted_path), "Encrypted file should exist")
            with open(encrypted_path, 'r') as f:
                encrypted_content = f.read()
                self.assertIn("ciphertext:", encrypted_content, 
                              "Encrypted file should contain ciphertext")
                self.assertIn("nonce:", encrypted_content, 
                              "Encrypted file should contain nonce")
                self.assertIn("salt:", encrypted_content, 
                              "Encrypted file should contain salt")
            
            # Decrypt the file
            security_utils.decrypt_file(encrypted_path, decrypted_path, self.test_password)
            
            # Verify the decrypted file matches the original
            self.assertTrue(os.path.exists(decrypted_path), "Decrypted file should exist")
            with open(decrypted_path, 'rb') as f:
                decrypted_content = f.read()
                self.assertEqual(decrypted_content, self.test_data_bytes, 
                                "Decrypted file should match the original")
            
            # Test decryption with wrong password
            wrong_decrypted_path = original_path + ".wrong"
            with self.assertRaises(ValueError, 
                                  msg="Decryption with wrong password should fail"):
                security_utils.decrypt_file(encrypted_path, wrong_decrypted_path, 
                                          "wrong-password")
        
        finally:
            # Clean up temporary files
            for path in [original_path, encrypted_path, decrypted_path]:
                if os.path.exists(path):
                    os.unlink(path)


class TestHMACSignatures(unittest.TestCase):
    """Test cases for HMAC signature generation and validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_data_str = "This is a test string to sign"
        self.test_data_bytes = b"This is a test byte string to sign"
        self.secret_key_str = "test-secret-key"
        self.secret_key_bytes = b"test-secret-key-bytes"

    def test_generate_hmac_signature_with_string_data(self):
        """Test generating an HMAC signature with string data."""
        # Generate signature with string data and string key
        signature1 = security_utils.generate_hmac_signature(
            self.test_data_str, self.secret_key_str)
        
        # Verify signature properties
        self.assertTrue(isinstance(signature1, str), "Signature should be a string")
        self.assertEqual(len(signature1), 64, "SHA-256 signature should be 64 hex chars")
        
        # Generate signature with string data and bytes key
        signature2 = security_utils.generate_hmac_signature(
            self.test_data_str, self.secret_key_bytes)
        
        # Verify signatures are different with different keys
        self.assertNotEqual(signature1, signature2, 
                           "Signatures with different keys should be different")

    def test_generate_hmac_signature_with_bytes_data(self):
        """Test generating an HMAC signature with bytes data."""
        # Generate signature with bytes data and string key
        signature1 = security_utils.generate_hmac_signature(
            self.test_data_bytes, self.secret_key_str)
        
        # Generate signature with bytes data and bytes key
        signature2 = security_utils.generate_hmac_signature(
            self.test_data_bytes, self.secret_key_bytes)
        
        # Verify signatures are different with different keys
        self.assertNotEqual(signature1, signature2, 
                           "Signatures with different keys should be different")
        
        # Verify manual HMAC calculation matches
        manual_hmac = hmac.new(self.secret_key_str.encode('utf-8'), 
                              self.test_data_bytes, 
                              hashlib.sha256).hexdigest()
        self.assertEqual(signature1, manual_hmac, 
                        "Generated signature should match manual calculation")

    def test_verify_hmac_signature(self):
        """Test verifying an HMAC signature."""
        # Generate a signature
        signature = security_utils.generate_hmac_signature(
            self.test_data_str, self.secret_key_str)
        
        # Verify the signature
        is_valid = security_utils.verify_hmac_signature(
            self.test_data_str, signature, self.secret_key_str)
        self.assertTrue(is_valid, "Valid signature should verify successfully")
        
        # Verify with wrong data
        is_valid = security_utils.verify_hmac_signature(
            "wrong data", signature, self.secret_key_str)
        self.assertFalse(is_valid, "Signature with wrong data should not verify")
        
        # Verify with wrong key
        is_valid = security_utils.verify_hmac_signature(
            self.test_data_str, signature, "wrong-key")
        self.assertFalse(is_valid, "Signature with wrong key should not verify")
        
        # Verify with tampered signature
        tampered_signature = signature[:-1] + ('0' if signature[-1] != '0' else '1')
        is_valid = security_utils.verify_hmac_signature(
            self.test_data_str, tampered_signature, self.secret_key_str)
        self.assertFalse(is_valid, "Tampered signature should not verify")


class TestCredentialManagement(unittest.TestCase):
    """Test cases for secure credential management functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.credential_name = "TEST_CREDENTIAL"
        self.credential_value = "test-credential-value"
        
        # Save original environment
        self.original_env = os.environ.copy()

    def tearDown(self):
        """Clean up after tests."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_get_credential_from_env(self):
        """Test getting a credential from the environment."""
        # Set the credential in the environment
        os.environ[self.credential_name] = self.credential_value
        
        # Get the credential
        value = security_utils.get_credential(self.credential_name)
        
        # Verify the credential value
        self.assertEqual(value, self.credential_value, 
                        "Should retrieve credential from environment")

    def test_get_credential_default(self):
        """Test getting a credential with a default value."""
        # Ensure the credential is not in the environment
        if self.credential_name in os.environ:
            del os.environ[self.credential_name]
        
        # Get the credential with a default value
        default_value = "default-value"
        value = security_utils.get_credential(self.credential_name, default_value)
        
        # Verify the default value is returned
        self.assertEqual(value, default_value, 
                        "Should return default value when credential not found")

    @mock.patch('src.utils.security_utils.KEYRING_AVAILABLE', True)
    @mock.patch('src.utils.security_utils.keyring')
    def test_get_credential_from_keyring(self, mock_keyring):
        """Test getting a credential from the keyring."""
        # Ensure the credential is not in the environment
        if self.credential_name in os.environ:
            del os.environ[self.credential_name]
        
        # Set up the mock keyring
        mock_keyring.get_password.return_value = self.credential_value
        
        # Get the credential
        value = security_utils.get_credential(self.credential_name)
        
        # Verify the credential value
        self.assertEqual(value, self.credential_value, 
                        "Should retrieve credential from keyring")
        mock_keyring.get_password.assert_called_once_with("ocr-service", self.credential_name)

    @mock.patch('src.utils.security_utils.KEYRING_AVAILABLE', True)
    @mock.patch('src.utils.security_utils.keyring')
    def test_set_credential(self, mock_keyring):
        """Test setting a credential in the keyring."""
        # Set the credential
        result = security_utils.set_credential(self.credential_name, self.credential_value)
        
        # Verify the result and keyring call
        self.assertTrue(result, "Should return True when credential is set successfully")
        mock_keyring.set_password.assert_called_once_with(
            "ocr-service", self.credential_name, self.credential_value)

    @mock.patch('src.utils.security_utils.KEYRING_AVAILABLE', False)
    def test_set_credential_no_keyring(self):
        """Test setting a credential when keyring is not available."""
        # Attempt to set the credential
        result = security_utils.set_credential(self.credential_name, self.credential_value)
        
        # Verify the result
        self.assertFalse(result, "Should return False when keyring is not available")

    @mock.patch('src.utils.security_utils.get_credential')
    def test_get_aws_credentials(self, mock_get_credential):
        """Test getting AWS credentials."""
        # Set up the mock get_credential function
        mock_get_credential.side_effect = lambda name, default=None: {
            'AWS_ACCESS_KEY_ID': 'test-access-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
            'AWS_SESSION_TOKEN': 'test-session-token'
        }.get(name, default)
        
        # Get the AWS credentials
        credentials = security_utils.get_aws_credentials()
        
        # Verify the credentials
        self.assertEqual(credentials['access_key'], 'test-access-key', 
                        "Should retrieve AWS access key")
        self.assertEqual(credentials['secret_key'], 'test-secret-key', 
                        "Should retrieve AWS secret key")
        self.assertEqual(credentials['session_token'], 'test-session-token', 
                        "Should retrieve AWS session token")
        
        # Verify get_credential was called for each credential
        self.assertEqual(mock_get_credential.call_count, 3, 
                        "Should call get_credential for each AWS credential")


class TestTLSConfiguration(unittest.TestCase):
    """Test cases for TLS configuration helper functions."""

    def test_create_tls_context_default(self):
        """Test creating a default TLS context."""
        # Create a TLS context with default settings
        context = security_utils.create_tls_context()
        
        # Verify context properties
        self.assertIsInstance(context, ssl.SSLContext, 
                             "Should return an SSLContext instance")
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED, 
                        "Should require certificate verification by default")
        self.assertTrue(context.check_hostname, 
                       "Should check hostname by default")
        self.assertEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2, 
                        "Should set minimum TLS version to 1.2")

    def test_create_tls_context_no_verify(self):
        """Test creating a TLS context without certificate verification."""
        # Create a TLS context without certificate verification
        context = security_utils.create_tls_context(verify_cert=False)
        
        # Verify context properties
        self.assertEqual(context.verify_mode, ssl.CERT_NONE, 
                        "Should not require certificate verification")
        self.assertFalse(context.check_hostname, 
                        "Should not check hostname")

    def test_create_tls_context_with_ca_cert(self):
        """Test creating a TLS context with a custom CA certificate."""
        # Create a temporary CA certificate file
        with tempfile.NamedTemporaryFile(delete=False) as ca_cert_file:
            ca_cert_path = ca_cert_file.name
        
        try:
            # Mock the load_verify_locations method
            with mock.patch.object(ssl.SSLContext, 'load_verify_locations') as mock_load:
                # Create a TLS context with the CA certificate
                context = security_utils.create_tls_context(ca_cert_path=ca_cert_path)
                
                # Verify load_verify_locations was called with the CA certificate
                mock_load.assert_called_once_with(cafile=ca_cert_path)
        
        finally:
            # Clean up the temporary file
            if os.path.exists(ca_cert_path):
                os.unlink(ca_cert_path)

    def test_create_tls_server_context(self):
        """Test creating a TLS server context."""
        # Create temporary certificate and key files
        with tempfile.NamedTemporaryFile(delete=False) as cert_file:
            cert_path = cert_file.name
        with tempfile.NamedTemporaryFile(delete=False) as key_file:
            key_path = key_file.name
        
        try:
            # Mock the load_cert_chain method
            with mock.patch.object(ssl.SSLContext, 'load_cert_chain') as mock_load:
                # Create a TLS server context
                context = security_utils.create_tls_server_context(cert_path, key_path)
                
                # Verify context properties
                self.assertIsInstance(context, ssl.SSLContext, 
                                    "Should return an SSLContext instance")
                self.assertEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2, 
                                "Should set minimum TLS version to 1.2")
                
                # Verify load_cert_chain was called with the certificate and key
                mock_load.assert_called_once_with(cert_path, key_path)
        
        finally:
            # Clean up the temporary files
            for path in [cert_path, key_path]:
                if os.path.exists(path):
                    os.unlink(path)


class TestSecureRandomGeneration(unittest.TestCase):
    """Test cases for secure random string generation functions."""

    def test_generate_token_bytes(self):
        """Test generating random token bytes."""
        # Generate token bytes with default length
        token1 = security_utils.generate_token_bytes()
        
        # Verify token properties
        self.assertIsInstance(token1, bytes, "Should return bytes")
        self.assertEqual(len(token1), 32, "Default token should be 32 bytes")
        
        # Generate token bytes with custom length
        custom_length = 16
        token2 = security_utils.generate_token_bytes(custom_length)
        
        # Verify custom length token
        self.assertEqual(len(token2), custom_length, 
                        f"Token should be {custom_length} bytes")
        
        # Generate another token and verify it's different
        token3 = security_utils.generate_token_bytes()
        self.assertNotEqual(token1, token3, "Different tokens should be unique")

    def test_generate_token_hex(self):
        """Test generating random token as hexadecimal string."""
        # Generate hex token with default length
        token1 = security_utils.generate_token_hex()
        
        # Verify token properties
        self.assertIsInstance(token1, str, "Should return a string")
        self.assertEqual(len(token1), 64, "Default hex token should be 64 characters")
        
        # Verify token contains only hexadecimal characters
        self.assertTrue(all(c in '0123456789abcdef' for c in token1), 
                       "Token should contain only hexadecimal characters")
        
        # Generate hex token with custom length
        custom_length = 16
        token2 = security_utils.generate_token_hex(custom_length)
        
        # Verify custom length token
        self.assertEqual(len(token2), custom_length * 2, 
                        f"Hex token should be {custom_length * 2} characters")

    def test_generate_token_urlsafe(self):
        """Test generating URL-safe random token."""
        # Generate URL-safe token with default length
        token1 = security_utils.generate_token_urlsafe()
        
        # Verify token properties
        self.assertIsInstance(token1, str, "Should return a string")
        
        # Verify token contains only URL-safe characters
        self.assertTrue(all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=' for c in token1), 
                       "Token should contain only URL-safe characters")
        
        # Generate URL-safe token with custom length
        custom_length = 16
        token2 = security_utils.generate_token_urlsafe(custom_length)
        
        # Generate another token and verify it's different
        token3 = security_utils.generate_token_urlsafe()
        self.assertNotEqual(token1, token3, "Different tokens should be unique")

    def test_generate_password(self):
        """Test generating a secure random password."""
        # Generate password with default settings
        password1 = security_utils.generate_password()
        
        # Verify password properties
        self.assertIsInstance(password1, str, "Should return a string")
        self.assertEqual(len(password1), 16, "Default password should be 16 characters")
        
        # Verify password contains required character types
        self.assertTrue(any(c.islower() for c in password1), 
                       "Password should contain lowercase letters")
        self.assertTrue(any(c.isupper() for c in password1), 
                       "Password should contain uppercase letters")
        self.assertTrue(any(c.isdigit() for c in password1), 
                       "Password should contain digits")
        self.assertTrue(any(c in string.punctuation for c in password1), 
                       "Password should contain special characters")
        
        # Generate password with custom length and no special characters
        custom_length = 12
        password2 = security_utils.generate_password(custom_length, include_special=False)
        
        # Verify custom password properties
        self.assertEqual(len(password2), custom_length, 
                        f"Password should be {custom_length} characters")
        self.assertFalse(any(c in string.punctuation for c in password2), 
                        "Password should not contain special characters")
        
        # Test with invalid length
        with self.assertRaises(ValueError, 
                              msg="Should raise ValueError for short passwords"):
            security_utils.generate_password(7)  # Minimum length is 8


if __name__ == '__main__':
    unittest.main()