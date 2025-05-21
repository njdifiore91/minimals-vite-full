#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the security_utils module.

This module contains tests for the security utilities including:
- AES-256 encryption and decryption
- HMAC signature generation and validation
- Secure credential management
- TLS configuration helpers
- Secure random string generation
"""

import base64
import os
import ssl
import tempfile
import unittest
from unittest import mock
from unittest.mock import patch, MagicMock

import pytest

from src.utils import security_utils


# ============================================================================
# Test AES-256 Encryption/Decryption Functions
# ============================================================================

class TestAESEncryption:
    """Tests for AES-256 encryption and decryption functions."""

    @pytest.fixture
    def setup_crypto_mock(self):
        """Setup mock for cryptography package."""
        with patch.object(security_utils, 'CRYPTOGRAPHY_AVAILABLE', True):
            yield

    @pytest.fixture
    def setup_crypto_unavailable(self):
        """Setup mock for unavailable cryptography package."""
        with patch.object(security_utils, 'CRYPTOGRAPHY_AVAILABLE', False):
            yield

    def test_generate_key_from_password(self, setup_crypto_mock):
        """Test generating a key from a password."""
        with patch('src.utils.security_utils.Scrypt') as mock_scrypt:
            mock_kdf = MagicMock()
            mock_kdf.derive.return_value = b'0' * 32  # 32-byte key
            mock_scrypt.return_value = mock_kdf

            # Test with provided salt
            test_salt = b'test_salt_12345678'  # 16 bytes
            key, salt = security_utils.generate_key_from_password('test_password', test_salt)
            
            assert len(key) == 32  # 256 bits
            assert salt == test_salt
            mock_scrypt.assert_called_once()
            mock_kdf.derive.assert_called_once()

    def test_generate_key_from_password_with_random_salt(self, setup_crypto_mock):
        """Test generating a key from a password with a random salt."""
        with patch('src.utils.security_utils.Scrypt') as mock_scrypt, \
             patch('os.urandom', return_value=b'random_salt_12345'):
            mock_kdf = MagicMock()
            mock_kdf.derive.return_value = b'0' * 32  # 32-byte key
            mock_scrypt.return_value = mock_kdf

            key, salt = security_utils.generate_key_from_password('test_password')
            
            assert len(key) == 32  # 256 bits
            assert salt == b'random_salt_12345'
            mock_scrypt.assert_called_once()
            mock_kdf.derive.assert_called_once()

    def test_generate_key_from_password_crypto_unavailable(self, setup_crypto_unavailable):
        """Test generating a key when cryptography is unavailable."""
        with pytest.raises(ImportError):
            security_utils.generate_key_from_password('test_password')

    def test_encrypt_data(self, setup_crypto_mock):
        """Test encrypting data with AES-256-GCM."""
        with patch('ocr_service.src.utils.security_utils.AESGCM') as mock_aesgcm, \
             patch('os.urandom', return_value=b'nonce_12345678'):
            mock_cipher = MagicMock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_aesgcm.return_value = mock_cipher

            key = b'0' * 32  # 32-byte key
            result = security_utils.encrypt_data('test_data', key)
            
            assert 'ciphertext' in result
            assert 'nonce' in result
            assert result['ciphertext'] == base64.b64encode(b'encrypted_data').decode('utf-8')
            assert result['nonce'] == base64.b64encode(b'nonce_12345678').decode('utf-8')
            mock_aesgcm.assert_called_once_with(key)
            mock_cipher.encrypt.assert_called_once()

    def test_encrypt_data_with_bytes(self, setup_crypto_mock):
        """Test encrypting bytes data with AES-256-GCM."""
        with patch('src.utils.security_utils.AESGCM') as mock_aesgcm, \
             patch('os.urandom', return_value=b'nonce_12345678'):
            mock_cipher = MagicMock()
            mock_cipher.encrypt.return_value = b'encrypted_data'
            mock_aesgcm.return_value = mock_cipher

            key = b'0' * 32  # 32-byte key
            result = security_utils.encrypt_data(b'test_data', key)
            
            assert 'ciphertext' in result
            assert 'nonce' in result
            mock_aesgcm.assert_called_once_with(key)
            mock_cipher.encrypt.assert_called_once()

    def test_encrypt_data_invalid_key_length(self, setup_crypto_mock):
        """Test encrypting data with an invalid key length."""
        key = b'0' * 16  # 16-byte key (too short)
        with pytest.raises(ValueError):
            security_utils.encrypt_data('test_data', key)

    def test_encrypt_data_crypto_unavailable(self, setup_crypto_unavailable):
        """Test encrypting data when cryptography is unavailable."""
        key = b'0' * 32
        with pytest.raises(ImportError):
            security_utils.encrypt_data('test_data', key)

    def test_decrypt_data(self, setup_crypto_mock):
        """Test decrypting data with AES-256-GCM."""
        with patch('ocr_service.src.utils.security_utils.AESGCM') as mock_aesgcm:
            mock_cipher = MagicMock()
            mock_cipher.decrypt.return_value = b'decrypted_data'
            mock_aesgcm.return_value = mock_cipher

            key = b'0' * 32  # 32-byte key
            encrypted_data = {
                'ciphertext': base64.b64encode(b'encrypted_data').decode('utf-8'),
                'nonce': base64.b64encode(b'nonce_12345678').decode('utf-8')
            }
            
            result = security_utils.decrypt_data(encrypted_data, key)
            
            assert result == b'decrypted_data'
            mock_aesgcm.assert_called_once_with(key)
            mock_cipher.decrypt.assert_called_once()

    def test_decrypt_data_invalid_key_length(self, setup_crypto_mock):
        """Test decrypting data with an invalid key length."""
        key = b'0' * 16  # 16-byte key (too short)
        encrypted_data = {
            'ciphertext': base64.b64encode(b'encrypted_data').decode('utf-8'),
            'nonce': base64.b64encode(b'nonce_12345678').decode('utf-8')
        }
        
        with pytest.raises(ValueError):
            security_utils.decrypt_data(encrypted_data, key)

    def test_decrypt_data_missing_fields(self, setup_crypto_mock):
        """Test decrypting data with missing fields."""
        key = b'0' * 32
        encrypted_data = {
            'ciphertext': base64.b64encode(b'encrypted_data').decode('utf-8')
            # Missing 'nonce' field
        }
        
        with pytest.raises(KeyError):
            security_utils.decrypt_data(encrypted_data, key)

    def test_decrypt_data_invalid_tag(self, setup_crypto_mock):
        """Test decrypting data with an invalid authentication tag."""
        with patch('src.utils.security_utils.AESGCM') as mock_aesgcm:
            mock_cipher = MagicMock()
            mock_cipher.decrypt.side_effect = security_utils.InvalidTag()
            mock_aesgcm.return_value = mock_cipher

            key = b'0' * 32
            encrypted_data = {
                'ciphertext': base64.b64encode(b'encrypted_data').decode('utf-8'),
                'nonce': base64.b64encode(b'nonce_12345678').decode('utf-8')
            }
            
            with pytest.raises(ValueError):
                security_utils.decrypt_data(encrypted_data, key)

    def test_decrypt_data_crypto_unavailable(self, setup_crypto_unavailable):
        """Test decrypting data when cryptography is unavailable."""
        key = b'0' * 32
        encrypted_data = {
            'ciphertext': base64.b64encode(b'encrypted_data').decode('utf-8'),
            'nonce': base64.b64encode(b'nonce_12345678').decode('utf-8')
        }
        
        with pytest.raises(ImportError):
            security_utils.decrypt_data(encrypted_data, key)

    def test_encrypt_file(self, setup_crypto_mock, tmp_path):
        """Test encrypting a file."""
        with patch('ocr_service.src.utils.security_utils.generate_key_from_password') as mock_gen_key, \
             patch('src.utils.security_utils.encrypt_data') as mock_encrypt:
            # Setup mocks
            mock_gen_key.return_value = (b'0' * 32, b'test_salt')
            mock_encrypt.return_value = {
                'ciphertext': 'encrypted_data_base64',
                'nonce': 'nonce_base64'
            }
            
            # Create a test file
            test_file = tmp_path / "test_file.txt"
            test_file.write_text("test data")
            output_file = tmp_path / "encrypted_file.enc"
            
            # Encrypt the file
            security_utils.encrypt_file(str(test_file), str(output_file), "test_password")
            
            # Verify the output file was created with the expected content
            assert output_file.exists()
            content = output_file.read_text()
            assert "ciphertext:encrypted_data_base64" in content
            assert "nonce:nonce_base64" in content
            assert "salt:" in content
            
            # Verify the mocks were called correctly
            mock_gen_key.assert_called_once_with("test_password")
            mock_encrypt.assert_called_once()

    def test_encrypt_file_not_found(self, setup_crypto_mock, tmp_path):
        """Test encrypting a non-existent file."""
        with patch('ocr_service.src.utils.security_utils.generate_key_from_password') as mock_gen_key:
            mock_gen_key.return_value = (b'0' * 32, b'test_salt')
            
            non_existent_file = tmp_path / "non_existent.txt"
            output_file = tmp_path / "encrypted_file.enc"
            
            with pytest.raises(FileNotFoundError):
                security_utils.encrypt_file(str(non_existent_file), str(output_file), "test_password")

    def test_decrypt_file(self, setup_crypto_mock, tmp_path):
        """Test decrypting a file."""
        with patch('src.utils.security_utils.generate_key_from_password') as mock_gen_key, \
             patch('src.utils.security_utils.decrypt_data') as mock_decrypt:
            # Setup mocks
            mock_gen_key.return_value = (b'0' * 32, b'test_salt')
            mock_decrypt.return_value = b'decrypted data'
            
            # Create a test encrypted file
            encrypted_file = tmp_path / "encrypted_file.enc"
            encrypted_file.write_text(
                "ciphertext:encrypted_data_base64\n"
                "nonce:nonce_base64\n"
                "salt:" + base64.b64encode(b'test_salt').decode('utf-8')
            )
            output_file = tmp_path / "decrypted_file.txt"
            
            # Decrypt the file
            security_utils.decrypt_file(str(encrypted_file), str(output_file), "test_password")
            
            # Verify the output file was created with the expected content
            assert output_file.exists()
            assert output_file.read_bytes() == b'decrypted data'
            
            # Verify the mocks were called correctly
            mock_gen_key.assert_called_once_with("test_password", b'test_salt')
            mock_decrypt.assert_called_once()

    def test_decrypt_file_not_found(self, setup_crypto_mock, tmp_path):
        """Test decrypting a non-existent file."""
        non_existent_file = tmp_path / "non_existent.enc"
        output_file = tmp_path / "decrypted_file.txt"
        
        with pytest.raises(FileNotFoundError):
            security_utils.decrypt_file(str(non_existent_file), str(output_file), "test_password")

    def test_decrypt_file_invalid_format(self, setup_crypto_mock, tmp_path):
        """Test decrypting a file with invalid format."""
        # Create a test file with invalid format (missing salt)
        invalid_file = tmp_path / "invalid_file.enc"
        invalid_file.write_text(
            "ciphertext:encrypted_data_base64\n"
            "nonce:nonce_base64\n"
            # Missing salt
        )
        output_file = tmp_path / "decrypted_file.txt"
        
        with pytest.raises(ValueError):
            security_utils.decrypt_file(str(invalid_file), str(output_file), "test_password")


# ============================================================================
# Test HMAC Signature Generation and Validation
# ============================================================================

class TestHMACSignature:
    """Tests for HMAC signature generation and validation functions."""

    def test_generate_hmac_signature_with_string(self):
        """Test generating an HMAC signature with string inputs."""
        data = "test data"
        secret_key = "secret key"
        
        signature = security_utils.generate_hmac_signature(data, secret_key)
        
        # Verify the signature is a hexadecimal string of the correct length (64 chars for SHA-256)
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)

    def test_generate_hmac_signature_with_bytes(self):
        """Test generating an HMAC signature with bytes inputs."""
        data = b"test data"
        secret_key = b"secret key"
        
        signature = security_utils.generate_hmac_signature(data, secret_key)
        
        # Verify the signature is a hexadecimal string of the correct length (64 chars for SHA-256)
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)

    def test_generate_hmac_signature_mixed_types(self):
        """Test generating an HMAC signature with mixed input types."""
        data = "test data"
        secret_key = b"secret key"
        
        signature = security_utils.generate_hmac_signature(data, secret_key)
        
        # Verify the signature is a hexadecimal string of the correct length (64 chars for SHA-256)
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)

    def test_verify_hmac_signature_valid(self):
        """Test verifying a valid HMAC signature."""
        data = "test data"
        secret_key = "secret key"
        
        # Generate a signature
        signature = security_utils.generate_hmac_signature(data, secret_key)
        
        # Verify the signature
        result = security_utils.verify_hmac_signature(data, signature, secret_key)
        
        assert result is True

    def test_verify_hmac_signature_invalid(self):
        """Test verifying an invalid HMAC signature."""
        data = "test data"
        secret_key = "secret key"
        
        # Generate a signature
        signature = security_utils.generate_hmac_signature(data, secret_key)
        
        # Modify the signature to make it invalid
        if signature[0] == '0':
            invalid_signature = '1' + signature[1:]
        else:
            invalid_signature = '0' + signature[1:]
        
        # Verify the invalid signature
        result = security_utils.verify_hmac_signature(data, invalid_signature, secret_key)
        
        assert result is False

    def test_verify_hmac_signature_different_data(self):
        """Test verifying a signature with different data."""
        data1 = "test data"
        data2 = "different data"
        secret_key = "secret key"
        
        # Generate a signature for data1
        signature = security_utils.generate_hmac_signature(data1, secret_key)
        
        # Verify the signature with data2
        result = security_utils.verify_hmac_signature(data2, signature, secret_key)
        
        assert result is False

    def test_verify_hmac_signature_different_key(self):
        """Test verifying a signature with a different key."""
        data = "test data"
        secret_key1 = "secret key 1"
        secret_key2 = "secret key 2"
        
        # Generate a signature with key1
        signature = security_utils.generate_hmac_signature(data, secret_key1)
        
        # Verify the signature with key2
        result = security_utils.verify_hmac_signature(data, signature, secret_key2)
        
        assert result is False


# ============================================================================
# Test Secure Credential Management
# ============================================================================

class TestCredentialManagement:
    """Tests for secure credential management functions."""

    @pytest.fixture
    def setup_keyring_mock(self):
        """Setup mock for keyring package."""
        with patch.object(security_utils, 'KEYRING_AVAILABLE', True):
            yield

    @pytest.fixture
    def setup_keyring_unavailable(self):
        """Setup mock for unavailable keyring package."""
        with patch.object(security_utils, 'KEYRING_AVAILABLE', False):
            yield

    def test_get_credential_from_env(self):
        """Test getting a credential from the environment."""
        with patch.dict(os.environ, {'TEST_CREDENTIAL': 'test_value'}):
            credential = security_utils.get_credential('TEST_CREDENTIAL')
            assert credential == 'test_value'

    def test_get_credential_from_keyring(self, setup_keyring_mock):
        """Test getting a credential from the keyring."""
        with patch.dict(os.environ, {}, clear=True), \
             patch('keyring.get_password', return_value='keyring_value'):
            credential = security_utils.get_credential('TEST_CREDENTIAL')
            assert credential == 'keyring_value'

    def test_get_credential_not_found(self, setup_keyring_mock):
        """Test getting a non-existent credential."""
        with patch.dict(os.environ, {}, clear=True), \
             patch('keyring.get_password', return_value=None):
            credential = security_utils.get_credential('TEST_CREDENTIAL')
            assert credential is None

    def test_get_credential_with_default(self, setup_keyring_mock):
        """Test getting a non-existent credential with a default value."""
        with patch.dict(os.environ, {}, clear=True), \
             patch('keyring.get_password', return_value=None):
            credential = security_utils.get_credential('TEST_CREDENTIAL', 'default_value')
            assert credential == 'default_value'

    def test_get_credential_keyring_error(self, setup_keyring_mock):
        """Test handling a keyring error when getting a credential."""
        with patch.dict(os.environ, {}, clear=True), \
             patch('keyring.get_password', side_effect=Exception('Keyring error')):
            credential = security_utils.get_credential('TEST_CREDENTIAL', 'default_value')
            assert credential == 'default_value'

    def test_get_credential_keyring_unavailable(self, setup_keyring_unavailable):
        """Test getting a credential when keyring is unavailable."""
        with patch.dict(os.environ, {}, clear=True):
            credential = security_utils.get_credential('TEST_CREDENTIAL', 'default_value')
            assert credential == 'default_value'

    def test_set_credential(self, setup_keyring_mock):
        """Test setting a credential in the keyring."""
        with patch('keyring.set_password') as mock_set_password:
            result = security_utils.set_credential('TEST_CREDENTIAL', 'test_value')
            assert result is True
            mock_set_password.assert_called_once_with('ocr-service', 'TEST_CREDENTIAL', 'test_value')

    def test_set_credential_error(self, setup_keyring_mock):
        """Test handling an error when setting a credential."""
        with patch('keyring.set_password', side_effect=Exception('Keyring error')):
            result = security_utils.set_credential('TEST_CREDENTIAL', 'test_value')
            assert result is False

    def test_set_credential_keyring_unavailable(self, setup_keyring_unavailable):
        """Test setting a credential when keyring is unavailable."""
        result = security_utils.set_credential('TEST_CREDENTIAL', 'test_value')
        assert result is False

    def test_get_aws_credentials(self):
        """Test getting AWS credentials."""
        with patch('src.utils.security_utils.get_credential') as mock_get_credential:
            mock_get_credential.side_effect = lambda name, default=None: {
                'AWS_ACCESS_KEY_ID': 'test_access_key',
                'AWS_SECRET_ACCESS_KEY': 'test_secret_key',
                'AWS_SESSION_TOKEN': 'test_session_token'
            }.get(name, default)
            
            credentials = security_utils.get_aws_credentials()
            
            assert credentials == {
                'access_key': 'test_access_key',
                'secret_key': 'test_secret_key',
                'session_token': 'test_session_token'
            }
            assert mock_get_credential.call_count == 3


# ============================================================================
# Test TLS Configuration Helpers
# ============================================================================

class TestTLSConfiguration:
    """Tests for TLS configuration helper functions."""

    def test_create_tls_context_default(self):
        """Test creating a TLS context with default settings."""
        with patch('ssl.SSLContext') as mock_ssl_context:
            mock_context = MagicMock()
            mock_ssl_context.return_value = mock_context
            
            context = security_utils.create_tls_context()
            
            mock_ssl_context.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
            assert mock_context.verify_mode == ssl.CERT_REQUIRED
            assert mock_context.check_hostname is True
            assert mock_context.load_default_certs.called

    def test_create_tls_context_no_verify(self):
        """Test creating a TLS context without certificate verification."""
        with patch('ssl.SSLContext') as mock_ssl_context:
            mock_context = MagicMock()
            mock_ssl_context.return_value = mock_context
            
            context = security_utils.create_tls_context(verify_cert=False)
            
            mock_ssl_context.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
            assert mock_context.verify_mode == ssl.CERT_NONE
            assert mock_context.check_hostname is False
            assert not mock_context.load_default_certs.called

    def test_create_tls_context_with_ca_cert(self):
        """Test creating a TLS context with a custom CA certificate."""
        with patch('ssl.SSLContext') as mock_ssl_context:
            mock_context = MagicMock()
            mock_ssl_context.return_value = mock_context
            
            context = security_utils.create_tls_context(ca_cert_path='/path/to/ca.crt')
            
            mock_ssl_context.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
            assert mock_context.verify_mode == ssl.CERT_REQUIRED
            assert mock_context.check_hostname is True
            assert mock_context.load_verify_locations.called
            mock_context.load_verify_locations.assert_called_once_with(cafile='/path/to/ca.crt')
            assert not mock_context.load_default_certs.called

    def test_create_tls_server_context(self):
        """Test creating a TLS server context."""
        with patch('ssl.SSLContext') as mock_ssl_context:
            mock_context = MagicMock()
            mock_ssl_context.return_value = mock_context
            
            context = security_utils.create_tls_server_context('/path/to/cert.crt', '/path/to/key.key')
            
            mock_ssl_context.assert_called_once_with(ssl.PROTOCOL_TLS_SERVER)
            assert mock_context.load_cert_chain.called
            mock_context.load_cert_chain.assert_called_once_with('/path/to/cert.crt', '/path/to/key.key')


# ============================================================================
# Test Secure Random String Generation
# ============================================================================

class TestRandomGeneration:
    """Tests for secure random string generation functions."""

    def test_generate_token_bytes_default_length(self):
        """Test generating random bytes with default length."""
        with patch('secrets.token_bytes', return_value=b'0' * 32) as mock_token_bytes:
            token = security_utils.generate_token_bytes()
            
            assert token == b'0' * 32
            mock_token_bytes.assert_called_once_with(32)

    def test_generate_token_bytes_custom_length(self):
        """Test generating random bytes with custom length."""
        with patch('secrets.token_bytes', return_value=b'0' * 16) as mock_token_bytes:
            token = security_utils.generate_token_bytes(16)
            
            assert token == b'0' * 16
            mock_token_bytes.assert_called_once_with(16)

    def test_generate_token_hex_default_length(self):
        """Test generating a random hex string with default length."""
        with patch('secrets.token_hex', return_value='0' * 64) as mock_token_hex:
            token = security_utils.generate_token_hex()
            
            assert token == '0' * 64
            mock_token_hex.assert_called_once_with(32)

    def test_generate_token_hex_custom_length(self):
        """Test generating a random hex string with custom length."""
        with patch('secrets.token_hex', return_value='0' * 32) as mock_token_hex:
            token = security_utils.generate_token_hex(16)
            
            assert token == '0' * 32
            mock_token_hex.assert_called_once_with(16)

    def test_generate_token_urlsafe_default_length(self):
        """Test generating a URL-safe random string with default length."""
        with patch('secrets.token_urlsafe', return_value='A' * 43) as mock_token_urlsafe:
            token = security_utils.generate_token_urlsafe()
            
            assert token == 'A' * 43
            mock_token_urlsafe.assert_called_once_with(32)

    def test_generate_token_urlsafe_custom_length(self):
        """Test generating a URL-safe random string with custom length."""
        with patch('secrets.token_urlsafe', return_value='A' * 22) as mock_token_urlsafe:
            token = security_utils.generate_token_urlsafe(16)
            
            assert token == 'A' * 22
            mock_token_urlsafe.assert_called_once_with(16)

    def test_generate_password_default(self):
        """Test generating a password with default settings."""
        with patch('secrets.choice') as mock_choice, \
             patch('secrets.SystemRandom') as mock_system_random:
            # Setup mocks
            mock_choice.side_effect = ['a', 'A', '1', '#', 'x', 'y', 'z', '2', '3', '4', 'B', 'C', 'D', 'E', 'F', 'G']
            mock_shuffle = MagicMock()
            mock_system_random.return_value.shuffle = mock_shuffle
            
            password = security_utils.generate_password()
            
            assert len(password) == 16
            assert mock_choice.call_count >= 16
            assert mock_shuffle.called

    def test_generate_password_custom_length(self):
        """Test generating a password with custom length."""
        with patch('secrets.choice') as mock_choice, \
             patch('secrets.SystemRandom') as mock_system_random:
            # Setup mocks
            mock_choice.side_effect = ['a', 'A', '1', '#', 'x', 'y', 'z', '2']
            mock_shuffle = MagicMock()
            mock_system_random.return_value.shuffle = mock_shuffle
            
            password = security_utils.generate_password(length=8)
            
            assert len(password) == 8
            assert mock_choice.call_count >= 8
            assert mock_shuffle.called

    def test_generate_password_no_special(self):
        """Test generating a password without special characters."""
        with patch('secrets.choice') as mock_choice, \
             patch('secrets.SystemRandom') as mock_system_random:
            # Setup mocks
            mock_choice.side_effect = ['a', 'A', '1', 'x', 'y', 'z', '2', '3', '4', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
            mock_shuffle = MagicMock()
            mock_system_random.return_value.shuffle = mock_shuffle
            
            password = security_utils.generate_password(include_special=False)
            
            assert len(password) == 16
            assert mock_choice.call_count >= 16
            assert mock_shuffle.called
            # Verify no special characters in the password
            assert all(c in string.ascii_letters + string.digits for c in password)

    def test_generate_password_too_short(self):
        """Test generating a password that is too short."""
        with pytest.raises(ValueError):
            security_utils.generate_password(length=7)


if __name__ == '__main__':
    pytest.main()