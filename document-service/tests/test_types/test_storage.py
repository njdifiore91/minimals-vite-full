#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for S3-compatible storage type definitions in the Document Service.

This module tests the type definitions for S3 client configuration, storage operations,
bucket configurations, and document metadata for the Document Service. These tests
ensure type safety when interacting with the S3-compatible storage for storing
classified documents.

The tests cover:
- S3ClientConfig: Tests for S3 connection parameters
- StorageOptions: Tests for encryption and access control settings
- StorageMetadata: Tests for document storage metadata
- BucketConfig: Tests for environment-specific bucket configurations
- StorageResult: Tests for operation results and error handling
- StorageKey: Tests for generating consistent storage keys

These tests ensure that the Document Service can securely store documents in
S3-compatible storage with AES-256 encryption and proper metadata for classification.
"""

import json
import uuid
import datetime
from typing import Dict, Any, Optional, List, Union, TypeVar, Generic

import pytest
from dataclasses import dataclass, field, asdict

from document_service.src.types.storage import (
    EncryptionType,
    StorageClass,
    S3ClientConfig,
    StorageOptions,
    StorageMetadata,
    BucketConfig,
    StorageErrorCode,
    StorageError,
    StorageResult,
    StorageKey,
    PresignedUrlOptions
)


# ===== EncryptionType Tests =====

class TestEncryptionType:
    """Tests for the EncryptionType enum."""

    def test_encryption_type_values(self):
        """Test that EncryptionType enum has the expected values."""
        assert EncryptionType.AES256.value == 'AES256'
        assert EncryptionType.AWS_KMS.value == 'aws:kms'
        assert EncryptionType.NONE.value == 'none'

    def test_encryption_type_comparison(self):
        """Test that EncryptionType enum values can be compared."""
        assert EncryptionType.AES256 == EncryptionType.AES256
        assert EncryptionType.AES256 != EncryptionType.AWS_KMS
        assert EncryptionType.AES256 != EncryptionType.NONE

    def test_encryption_type_as_dict_key(self):
        """Test that EncryptionType enum values can be used as dictionary keys."""
        encryption_map = {
            EncryptionType.AES256: "AES-256 encryption",
            EncryptionType.AWS_KMS: "AWS KMS encryption",
            EncryptionType.NONE: "No encryption"
        }
        assert encryption_map[EncryptionType.AES256] == "AES-256 encryption"
        assert encryption_map[EncryptionType.AWS_KMS] == "AWS KMS encryption"
        assert encryption_map[EncryptionType.NONE] == "No encryption"


# ===== StorageClass Tests =====

class TestStorageClass:
    """Tests for the StorageClass enum."""

    def test_storage_class_values(self):
        """Test that StorageClass enum has the expected values."""
        assert StorageClass.STANDARD.value == 'STANDARD'
        assert StorageClass.REDUCED_REDUNDANCY.value == 'REDUCED_REDUNDANCY'
        assert StorageClass.STANDARD_IA.value == 'STANDARD_IA'
        assert StorageClass.ONEZONE_IA.value == 'ONEZONE_IA'
        assert StorageClass.INTELLIGENT_TIERING.value == 'INTELLIGENT_TIERING'
        assert StorageClass.GLACIER.value == 'GLACIER'
        assert StorageClass.DEEP_ARCHIVE.value == 'DEEP_ARCHIVE'

    def test_storage_class_comparison(self):
        """Test that StorageClass enum values can be compared."""
        assert StorageClass.STANDARD == StorageClass.STANDARD
        assert StorageClass.STANDARD != StorageClass.GLACIER
        assert StorageClass.GLACIER != StorageClass.DEEP_ARCHIVE

    def test_storage_class_as_dict_key(self):
        """Test that StorageClass enum values can be used as dictionary keys."""
        storage_class_map = {
            StorageClass.STANDARD: "Standard storage",
            StorageClass.GLACIER: "Glacier storage",
            StorageClass.DEEP_ARCHIVE: "Deep archive storage"
        }
        assert storage_class_map[StorageClass.STANDARD] == "Standard storage"
        assert storage_class_map[StorageClass.GLACIER] == "Glacier storage"
        assert storage_class_map[StorageClass.DEEP_ARCHIVE] == "Deep archive storage"


# ===== S3ClientConfig Tests =====

class TestS3ClientConfig:
    """Tests for the S3ClientConfig type."""

    def test_s3_client_config_creation(self):
        """Test creating an S3ClientConfig with required fields."""
        config: S3ClientConfig = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "aws_access_key_id": "test-access-key",
            "aws_secret_access_key": "test-secret-key",
            "use_ssl": True,
            "verify": True,
            "max_pool_connections": 10,
            "timeout": 60,
            "retries": 3
        }
        
        assert config["endpoint_url"] == "https://s3.amazonaws.com"
        assert config["region_name"] == "us-east-1"
        assert config["aws_access_key_id"] == "test-access-key"
        assert config["aws_secret_access_key"] == "test-secret-key"
        assert config["use_ssl"] is True
        assert config["verify"] is True
        assert config["max_pool_connections"] == 10
        assert config["timeout"] == 60
        assert config["retries"] == 3

    def test_s3_client_config_with_custom_endpoint(self):
        """Test creating an S3ClientConfig with a custom endpoint."""
        config: S3ClientConfig = {
            "endpoint_url": "http://localhost:4566",  # LocalStack endpoint
            "region_name": "us-east-1",
            "aws_access_key_id": "test",
            "aws_secret_access_key": "test",
            "use_ssl": False,
            "verify": False,
            "max_pool_connections": 5,
            "timeout": 30,
            "retries": 1
        }
        
        assert config["endpoint_url"] == "http://localhost:4566"
        assert config["use_ssl"] is False
        assert config["verify"] is False

    def test_s3_client_config_with_ca_bundle(self):
        """Test creating an S3ClientConfig with a CA bundle for verification."""
        config: S3ClientConfig = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "aws_access_key_id": "test-access-key",
            "aws_secret_access_key": "test-secret-key",
            "use_ssl": True,
            "verify": "/path/to/ca-bundle.pem",
            "max_pool_connections": 10,
            "timeout": 60,
            "retries": 3
        }
        
        assert config["verify"] == "/path/to/ca-bundle.pem"

    def test_s3_client_config_with_retry_settings(self):
        """Test creating an S3ClientConfig with custom retry settings."""
        config: S3ClientConfig = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "aws_access_key_id": "test-access-key",
            "aws_secret_access_key": "test-secret-key",
            "use_ssl": True,
            "verify": True,
            "max_pool_connections": 10,
            "timeout": 120,  # Longer timeout
            "retries": 5     # More retries
        }
        
        assert config["timeout"] == 120
        assert config["retries"] == 5


# ===== StorageOptions Tests =====

class TestStorageOptions:
    """Tests for the StorageOptions type."""

    def test_storage_options_minimal(self):
        """Test creating StorageOptions with minimal fields."""
        options: StorageOptions = {
            "encryption": EncryptionType.AES256,
            "storage_class": StorageClass.STANDARD,
            "metadata": {"source": "document-service"},
            "content_type": "application/pdf"
        }
        
        assert options["encryption"] == EncryptionType.AES256
        assert options["storage_class"] == StorageClass.STANDARD
        assert options["metadata"] == {"source": "document-service"}
        assert options["content_type"] == "application/pdf"

    def test_storage_options_with_kms(self):
        """Test creating StorageOptions with AWS KMS encryption."""
        options: StorageOptions = {
            "encryption": EncryptionType.AWS_KMS,
            "kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/abcd1234-ab12-cd34-ef56-abcdef123456",
            "storage_class": StorageClass.STANDARD,
            "metadata": {"source": "document-service"},
            "content_type": "application/pdf"
        }
        
        assert options["encryption"] == EncryptionType.AWS_KMS
        assert options["kms_key_id"] == "arn:aws:kms:us-east-1:123456789012:key/abcd1234-ab12-cd34-ef56-abcdef123456"

    def test_storage_options_with_all_fields(self):
        """Test creating StorageOptions with all fields."""
        options: StorageOptions = {
            "encryption": EncryptionType.AES256,
            "kms_key_id": None,
            "storage_class": StorageClass.STANDARD,
            "metadata": {"source": "document-service", "classification": "automatic"},
            "content_type": "application/pdf",
            "content_disposition": "attachment; filename=\"document.pdf\"",
            "cache_control": "max-age=86400",
            "content_encoding": "gzip",
            "content_language": "en-US",
            "expires": "Wed, 21 Oct 2025 07:28:00 GMT",
            "website_redirect_location": None,
            "tagging": "key1=value1&key2=value2",
            "acl": "private"
        }
        
        assert options["content_disposition"] == "attachment; filename=\"document.pdf\""
        assert options["cache_control"] == "max-age=86400"
        assert options["content_encoding"] == "gzip"
        assert options["content_language"] == "en-US"
        assert options["expires"] == "Wed, 21 Oct 2025 07:28:00 GMT"
        assert options["website_redirect_location"] is None
        assert options["tagging"] == "key1=value1&key2=value2"
        assert options["acl"] == "private"

    def test_storage_options_with_different_storage_classes(self):
        """Test creating StorageOptions with different storage classes."""
        # Standard storage class
        options1: StorageOptions = {
            "encryption": EncryptionType.AES256,
            "storage_class": StorageClass.STANDARD,
            "metadata": {},
            "content_type": "application/pdf"
        }
        assert options1["storage_class"] == StorageClass.STANDARD
        
        # Glacier storage class
        options2: StorageOptions = {
            "encryption": EncryptionType.AES256,
            "storage_class": StorageClass.GLACIER,
            "metadata": {},
            "content_type": "application/pdf"
        }
        assert options2["storage_class"] == StorageClass.GLACIER
        
        # Intelligent tiering storage class
        options3: StorageOptions = {
            "encryption": EncryptionType.AES256,
            "storage_class": StorageClass.INTELLIGENT_TIERING,
            "metadata": {},
            "content_type": "application/pdf"
        }
        assert options3["storage_class"] == StorageClass.INTELLIGENT_TIERING


# ===== StorageMetadata Tests =====

class TestStorageMetadata:
    """Tests for the StorageMetadata type."""

    def test_storage_metadata_creation(self):
        """Test creating StorageMetadata with required fields."""
        metadata: StorageMetadata = {
            "document_id": str(uuid.uuid4()),
            "application_id": str(uuid.uuid4()),
            "document_type": "APPLICATION",
            "classification_confidence": 0.95,
            "content_type": "application/pdf",
            "original_filename": "application.pdf",
            "upload_timestamp": datetime.datetime.now().isoformat(),
            "size_bytes": 1024,
            "version": "1.0.0",
            "checksum": "d41d8cd98f00b204e9800998ecf8427e",
            "encrypted": True,
            "classification_model": "random_forest",
            "classification_model_version": "1.0.0",
            "review_required": False
        }
        
        assert "document_id" in metadata
        assert "application_id" in metadata
        assert metadata["document_type"] == "APPLICATION"
        assert metadata["classification_confidence"] == 0.95
        assert metadata["content_type"] == "application/pdf"
        assert metadata["original_filename"] == "application.pdf"
        assert "upload_timestamp" in metadata
        assert metadata["size_bytes"] == 1024
        assert metadata["version"] == "1.0.0"
        assert metadata["checksum"] == "d41d8cd98f00b204e9800998ecf8427e"
        assert metadata["encrypted"] is True
        assert metadata["classification_model"] == "random_forest"
        assert metadata["classification_model_version"] == "1.0.0"
        assert metadata["review_required"] is False

    def test_storage_metadata_with_different_document_types(self):
        """Test creating StorageMetadata with different document types."""
        # Application document
        metadata1: StorageMetadata = {
            "document_id": str(uuid.uuid4()),
            "application_id": str(uuid.uuid4()),
            "document_type": "APPLICATION",
            "classification_confidence": 0.95,
            "content_type": "application/pdf",
            "original_filename": "application.pdf",
            "upload_timestamp": datetime.datetime.now().isoformat(),
            "size_bytes": 1024,
            "version": "1.0.0",
            "checksum": "d41d8cd98f00b204e9800998ecf8427e",
            "encrypted": True,
            "classification_model": "random_forest",
            "classification_model_version": "1.0.0",
            "review_required": False
        }
        assert metadata1["document_type"] == "APPLICATION"
        
        # Tax return document
        metadata2: StorageMetadata = {
            "document_id": str(uuid.uuid4()),
            "application_id": str(uuid.uuid4()),
            "document_type": "TAX_RETURN",
            "classification_confidence": 0.92,
            "content_type": "application/pdf",
            "original_filename": "tax_return.pdf",
            "upload_timestamp": datetime.datetime.now().isoformat(),
            "size_bytes": 2048,
            "version": "1.0.0",
            "checksum": "e41d8cd98f00b204e9800998ecf8427f",
            "encrypted": True,
            "classification_model": "random_forest",
            "classification_model_version": "1.0.0",
            "review_required": False
        }
        assert metadata2["document_type"] == "TAX_RETURN"
        
        # Bank statement document
        metadata3: StorageMetadata = {
            "document_id": str(uuid.uuid4()),
            "application_id": str(uuid.uuid4()),
            "document_type": "BANK_STATEMENT",
            "classification_confidence": 0.88,
            "content_type": "application/pdf",
            "original_filename": "bank_statement.pdf",
            "upload_timestamp": datetime.datetime.now().isoformat(),
            "size_bytes": 1536,
            "version": "1.0.0",
            "checksum": "f41d8cd98f00b204e9800998ecf8427g",
            "encrypted": True,
            "classification_model": "random_forest",
            "classification_model_version": "1.0.0",
            "review_required": True  # Lower confidence, requires review
        }
        assert metadata3["document_type"] == "BANK_STATEMENT"
        assert metadata3["review_required"] is True

    def test_storage_metadata_with_low_confidence(self):
        """Test creating StorageMetadata with low classification confidence."""
        metadata: StorageMetadata = {
            "document_id": str(uuid.uuid4()),
            "application_id": str(uuid.uuid4()),
            "document_type": "OTHER",
            "classification_confidence": 0.65,  # Low confidence
            "content_type": "application/pdf",
            "original_filename": "unknown_document.pdf",
            "upload_timestamp": datetime.datetime.now().isoformat(),
            "size_bytes": 1024,
            "version": "1.0.0",
            "checksum": "d41d8cd98f00b204e9800998ecf8427e",
            "encrypted": True,
            "classification_model": "random_forest",
            "classification_model_version": "1.0.0",
            "review_required": True  # Should require review due to low confidence
        }
        
        assert metadata["classification_confidence"] == 0.65
        assert metadata["document_type"] == "OTHER"
        assert metadata["review_required"] is True

    def test_storage_metadata_serialization(self):
        """Test that StorageMetadata can be serialized to JSON."""
        doc_id = str(uuid.uuid4())
        app_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        metadata: StorageMetadata = {
            "document_id": doc_id,
            "application_id": app_id,
            "document_type": "APPLICATION",
            "classification_confidence": 0.95,
            "content_type": "application/pdf",
            "original_filename": "application.pdf",
            "upload_timestamp": timestamp,
            "size_bytes": 1024,
            "version": "1.0.0",
            "checksum": "d41d8cd98f00b204e9800998ecf8427e",
            "encrypted": True,
            "classification_model": "random_forest",
            "classification_model_version": "1.0.0",
            "review_required": False
        }
        
        # Serialize to JSON
        json_str = json.dumps(metadata)
        
        # Deserialize from JSON
        deserialized = json.loads(json_str)
        
        # Check that the deserialized data matches the original
        assert deserialized["document_id"] == doc_id
        assert deserialized["application_id"] == app_id
        assert deserialized["document_type"] == "APPLICATION"
        assert deserialized["classification_confidence"] == 0.95
        assert deserialized["upload_timestamp"] == timestamp
        assert deserialized["encrypted"] is True


# ===== BucketConfig Tests =====

class TestBucketConfig:
    """Tests for the BucketConfig class."""

    def test_bucket_config_creation_with_defaults(self):
        """Test creating a BucketConfig with default values."""
        config = BucketConfig(
            name="mca-documents-production",
            region="us-east-1"
        )
        
        assert config.name == "mca-documents-production"
        assert config.region == "us-east-1"
        assert config.encryption == EncryptionType.AES256  # Default value
        assert config.versioning is True  # Default value
        assert config.lifecycle_rules is None  # Default value
        assert config.cors_rules is None  # Default value
        assert config.public_access_blocked is True  # Default value

    def test_bucket_config_creation_with_custom_values(self):
        """Test creating a BucketConfig with custom values."""
        lifecycle_rules = [
            {
                "id": "archive-rule",
                "status": "Enabled",
                "transition": {
                    "days": 90,
                    "storage_class": "GLACIER"
                }
            }
        ]
        
        cors_rules = [
            {
                "allowed_origins": ["https://example.com"],
                "allowed_methods": ["GET"],
                "allowed_headers": ["*"],
                "max_age_seconds": 3600
            }
        ]
        
        config = BucketConfig(
            name="mca-documents-staging",
            region="us-west-2",
            encryption=EncryptionType.AWS_KMS,
            versioning=False,
            lifecycle_rules=lifecycle_rules,
            cors_rules=cors_rules,
            public_access_blocked=False
        )
        
        assert config.name == "mca-documents-staging"
        assert config.region == "us-west-2"
        assert config.encryption == EncryptionType.AWS_KMS
        assert config.versioning is False
        assert config.lifecycle_rules == lifecycle_rules
        assert config.cors_rules == cors_rules
        assert config.public_access_blocked is False

    def test_bucket_config_for_production(self):
        """Test creating a BucketConfig for the production environment."""
        config = BucketConfig(
            name="mca-documents-production",
            region="us-east-1",
            encryption=EncryptionType.AES256,
            versioning=True,
            public_access_blocked=True
        )
        
        assert config.name == "mca-documents-production"
        assert config.encryption == EncryptionType.AES256
        assert config.versioning is True
        assert config.public_access_blocked is True

    def test_bucket_config_for_staging(self):
        """Test creating a BucketConfig for the staging environment."""
        config = BucketConfig(
            name="mca-documents-staging",
            region="us-east-1",
            encryption=EncryptionType.AES256,
            versioning=True,
            public_access_blocked=True
        )
        
        assert config.name == "mca-documents-staging"
        assert config.encryption == EncryptionType.AES256
        assert config.versioning is True
        assert config.public_access_blocked is True

    def test_bucket_config_to_dict(self):
        """Test converting a BucketConfig to a dictionary."""
        config = BucketConfig(
            name="mca-documents-production",
            region="us-east-1",
            encryption=EncryptionType.AES256,
            versioning=True,
            public_access_blocked=True
        )
        
        config_dict = asdict(config)
        
        assert config_dict["name"] == "mca-documents-production"
        assert config_dict["region"] == "us-east-1"
        assert config_dict["encryption"] == EncryptionType.AES256
        assert config_dict["versioning"] is True
        assert config_dict["public_access_blocked"] is True


# ===== StorageErrorCode and StorageError Tests =====

class TestStorageErrorCode:
    """Tests for the StorageErrorCode enum."""

    def test_storage_error_code_values(self):
        """Test that StorageErrorCode enum has the expected values."""
        assert StorageErrorCode.CONNECTION_ERROR.value == 'CONNECTION_ERROR'
        assert StorageErrorCode.AUTHENTICATION_ERROR.value == 'AUTHENTICATION_ERROR'
        assert StorageErrorCode.PERMISSION_DENIED.value == 'PERMISSION_DENIED'
        assert StorageErrorCode.BUCKET_NOT_FOUND.value == 'BUCKET_NOT_FOUND'
        assert StorageErrorCode.OBJECT_NOT_FOUND.value == 'OBJECT_NOT_FOUND'
        assert StorageErrorCode.INVALID_KEY.value == 'INVALID_KEY'
        assert StorageErrorCode.ENCRYPTION_ERROR.value == 'ENCRYPTION_ERROR'
        assert StorageErrorCode.UPLOAD_ERROR.value == 'UPLOAD_ERROR'
        assert StorageErrorCode.DOWNLOAD_ERROR.value == 'DOWNLOAD_ERROR'
        assert StorageErrorCode.DELETE_ERROR.value == 'DELETE_ERROR'
        assert StorageErrorCode.TIMEOUT_ERROR.value == 'TIMEOUT_ERROR'
        assert StorageErrorCode.STORAGE_ERROR.value == 'STORAGE_ERROR'

    def test_storage_error_code_comparison(self):
        """Test that StorageErrorCode enum values can be compared."""
        assert StorageErrorCode.CONNECTION_ERROR == StorageErrorCode.CONNECTION_ERROR
        assert StorageErrorCode.CONNECTION_ERROR != StorageErrorCode.AUTHENTICATION_ERROR
        assert StorageErrorCode.UPLOAD_ERROR != StorageErrorCode.DOWNLOAD_ERROR


class TestStorageError:
    """Tests for the StorageError class."""

    def test_storage_error_creation_with_code_enum(self):
        """Test creating a StorageError with a StorageErrorCode enum."""
        error = StorageError(
            message="Failed to connect to S3",
            code=StorageErrorCode.CONNECTION_ERROR,
            details={"endpoint": "https://s3.amazonaws.com"}
        )
        
        assert error.message == "Failed to connect to S3"
        assert error.code == "CONNECTION_ERROR"
        assert error.details == {"endpoint": "https://s3.amazonaws.com"}
        assert str(error) == "Failed to connect to S3"

    def test_storage_error_creation_with_code_string(self):
        """Test creating a StorageError with a code string."""
        error = StorageError(
            message="Failed to upload document",
            code="UPLOAD_ERROR",
            details={"key": "documents/test.pdf"}
        )
        
        assert error.message == "Failed to upload document"
        assert error.code == "UPLOAD_ERROR"
        assert error.details == {"key": "documents/test.pdf"}

    def test_storage_error_creation_with_default_code(self):
        """Test creating a StorageError with the default code."""
        error = StorageError(
            message="Unknown storage error"
        )
        
        assert error.message == "Unknown storage error"
        assert error.code == "STORAGE_ERROR"  # Default value
        assert error.details == {}  # Default value

    def test_storage_error_as_exception(self):
        """Test that StorageError can be raised and caught as an exception."""
        try:
            raise StorageError("Test error")
        except StorageError as e:
            assert e.message == "Test error"
            assert e.code == "STORAGE_ERROR"
            assert e.details == {}


# ===== StorageResult Tests =====

class TestStorageResult:
    """Tests for the StorageResult class."""

    def test_storage_result_success(self):
        """Test creating a successful StorageResult."""
        result = StorageResult[Dict[str, str]](
            success=True,
            data={"key": "documents/test.pdf"},
            retry_count=0
        )
        
        assert result.success is True
        assert result.data == {"key": "documents/test.pdf"}
        assert result.error is None
        assert result.retry_count == 0
        assert result.failed is False

    def test_storage_result_failure_with_storage_error(self):
        """Test creating a failed StorageResult with a StorageError."""
        error = StorageError(
            message="Failed to upload document",
            code=StorageErrorCode.UPLOAD_ERROR,
            details={"key": "documents/test.pdf"}
        )
        
        result = StorageResult[Dict[str, str]](
            success=False,
            error=error,
            retry_count=2
        )
        
        assert result.success is False
        assert result.data is None
        assert isinstance(result.error, StorageError)
        assert result.error.message == "Failed to upload document"
        assert result.error.code == "UPLOAD_ERROR"
        assert result.retry_count == 2
        assert result.failed is True

    def test_storage_result_failure_with_exception(self):
        """Test creating a failed StorageResult with a generic exception."""
        error = ValueError("Invalid parameter")
        
        result = StorageResult[Dict[str, str]](
            success=False,
            error=error,
            retry_count=1
        )
        
        assert result.success is False
        assert result.data is None
        assert isinstance(result.error, ValueError)
        assert str(result.error) == "Invalid parameter"
        assert result.retry_count == 1
        assert result.failed is True

    def test_storage_result_with_different_data_types(self):
        """Test creating StorageResult with different data types."""
        # String data
        result1 = StorageResult[str](
            success=True,
            data="documents/test.pdf"
        )
        assert isinstance(result1.data, str)
        
        # Dictionary data
        result2 = StorageResult[Dict[str, Any]](
            success=True,
            data={"key": "documents/test.pdf", "size": 1024}
        )
        assert isinstance(result2.data, dict)
        
        # List data
        result3 = StorageResult[List[str]](
            success=True,
            data=["documents/test1.pdf", "documents/test2.pdf"]
        )
        assert isinstance(result3.data, list)


# ===== StorageKey Tests =====

class TestStorageKey:
    """Tests for the StorageKey class."""

    def test_storage_key_creation(self):
        """Test creating a StorageKey with required fields."""
        key = StorageKey(
            application_id="app-123",
            document_id="doc-456",
            document_type="APPLICATION"
        )
        
        assert key.application_id == "app-123"
        assert key.document_id == "doc-456"
        assert key.document_type == "APPLICATION"
        assert key.version == "v1"  # Default value

    def test_storage_key_creation_with_custom_version(self):
        """Test creating a StorageKey with a custom version."""
        key = StorageKey(
            application_id="app-123",
            document_id="doc-456",
            document_type="APPLICATION",
            version="v2"
        )
        
        assert key.application_id == "app-123"
        assert key.document_id == "doc-456"
        assert key.document_type == "APPLICATION"
        assert key.version == "v2"

    def test_storage_key_to_string(self):
        """Test converting a StorageKey to a string."""
        key = StorageKey(
            application_id="app-123",
            document_id="doc-456",
            document_type="APPLICATION",
            version="v1"
        )
        
        key_string = key.to_string()
        
        assert key_string == "app-123/APPLICATION/doc-456/v1"

    def test_storage_key_from_string(self):
        """Test creating a StorageKey from a string."""
        key_string = "app-123/APPLICATION/doc-456/v1"
        
        key = StorageKey.from_string(key_string)
        
        assert key.application_id == "app-123"
        assert key.document_id == "doc-456"
        assert key.document_type == "APPLICATION"
        assert key.version == "v1"

    def test_storage_key_from_string_invalid_format(self):
        """Test that creating a StorageKey from an invalid string raises an error."""
        invalid_key_string = "app-123/APPLICATION/doc-456"  # Missing version
        
        with pytest.raises(ValueError) as excinfo:
            StorageKey.from_string(invalid_key_string)
        
        assert "Invalid storage key format" in str(excinfo.value)

    def test_storage_key_roundtrip(self):
        """Test that a StorageKey can be converted to a string and back."""
        original_key = StorageKey(
            application_id="app-123",
            document_id="doc-456",
            document_type="TAX_RETURN",
            version="v3"
        )
        
        key_string = original_key.to_string()
        reconstructed_key = StorageKey.from_string(key_string)
        
        assert reconstructed_key.application_id == original_key.application_id
        assert reconstructed_key.document_id == original_key.document_id
        assert reconstructed_key.document_type == original_key.document_type
        assert reconstructed_key.version == original_key.version


# ===== PresignedUrlOptions Tests =====

class TestPresignedUrlOptions:
    """Tests for the PresignedUrlOptions type."""

    def test_presigned_url_options_minimal(self):
        """Test creating PresignedUrlOptions with minimal fields."""
        options: PresignedUrlOptions = {
            "expires_in": 3600  # 1 hour
        }
        
        assert options["expires_in"] == 3600

    def test_presigned_url_options_with_all_fields(self):
        """Test creating PresignedUrlOptions with all fields."""
        options: PresignedUrlOptions = {
            "expires_in": 3600,  # 1 hour
            "response_content_type": "application/pdf",
            "response_content_disposition": "attachment; filename=\"document.pdf\"",
            "response_content_language": "en-US",
            "response_content_encoding": "gzip",
            "response_cache_control": "max-age=3600",
            "response_expires": "Wed, 21 Oct 2025 07:28:00 GMT"
        }
        
        assert options["expires_in"] == 3600
        assert options["response_content_type"] == "application/pdf"
        assert options["response_content_disposition"] == "attachment; filename=\"document.pdf\""
        assert options["response_content_language"] == "en-US"
        assert options["response_content_encoding"] == "gzip"
        assert options["response_cache_control"] == "max-age=3600"
        assert options["response_expires"] == "Wed, 21 Oct 2025 07:28:00 GMT"

    def test_presigned_url_options_with_short_expiry(self):
        """Test creating PresignedUrlOptions with a short expiry time."""
        options: PresignedUrlOptions = {
            "expires_in": 300  # 5 minutes
        }
        
        assert options["expires_in"] == 300

    def test_presigned_url_options_with_inline_content_disposition(self):
        """Test creating PresignedUrlOptions with inline content disposition."""
        options: PresignedUrlOptions = {
            "expires_in": 3600,
            "response_content_disposition": "inline; filename=\"document.pdf\""
        }
        
        assert options["response_content_disposition"] == "inline; filename=\"document.pdf\""