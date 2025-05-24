#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for S3-compatible storage type definitions in the Document Service.

This module validates that S3ClientConfig, StorageOptions, StorageMetadata, BucketConfig,
StorageResult, and StorageKey types correctly handle storage operations and document metadata.
These tests ensure type safety for secure document storage in S3-compatible storage.
"""

import os
import uuid
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, cast
from io import BytesIO

import pytest
from unittest.mock import MagicMock, patch

# Import types to test
from document_service.types.storage import (
    S3ClientConfig,
    S3Credentials,
    StorageOptions,
    EncryptionConfig,
    StorageMetadata,
    DocumentClassification,
    BucketConfig,
    EnvironmentBuckets,
    StorageResult,
    StorageError,
    StorageErrorDetail,
    StorageKey,
    LifecycleRule,
    LifecycleTransition,
    LifecycleExpiration,
    RetryConfig,
    StorageOperations,
    StorageKeyGenerator
)


class TestS3ClientConfig:
    """Test cases for S3ClientConfig type."""

    def test_valid_config(self, s3_client_config: S3ClientConfig) -> None:
        """Test that a valid S3ClientConfig can be created."""
        # The fixture provides a valid config, so we just need to verify its structure
        assert "endpoint_url" in s3_client_config
        assert "region_name" in s3_client_config
        assert "credentials" in s3_client_config
        assert "verify" in s3_client_config
        
        # Verify credentials structure
        credentials = s3_client_config["credentials"]
        assert "access_key" in credentials
        assert "secret_key" in credentials
        assert "session_token" in credentials
        
        # Verify types
        assert isinstance(s3_client_config["endpoint_url"], str)
        assert isinstance(s3_client_config["region_name"], str)
        assert isinstance(s3_client_config["credentials"], dict)
        assert isinstance(s3_client_config["verify"], bool)

    def test_config_with_ca_bundle(self) -> None:
        """Test S3ClientConfig with CA bundle path for verification."""
        config: S3ClientConfig = {
            "endpoint_url": "https://s3.example.com",
            "region_name": "us-west-2",
            "credentials": {
                "access_key": "test-key",
                "secret_key": "test-secret",
                "session_token": None
            },
            "verify": "/path/to/ca-bundle.pem"
        }
        
        # Verify that verify can be a string (path to CA bundle)
        assert isinstance(config["verify"], str)
        assert config["verify"] == "/path/to/ca-bundle.pem"

    def test_config_with_session_token(self) -> None:
        """Test S3ClientConfig with session token in credentials."""
        config: S3ClientConfig = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "eu-central-1",
            "credentials": {
                "access_key": "test-key",
                "secret_key": "test-secret",
                "session_token": "test-session-token"
            },
            "verify": True
        }
        
        # Verify that session_token can be a string
        assert isinstance(config["credentials"]["session_token"], str)
        assert config["credentials"]["session_token"] == "test-session-token"

    def test_config_with_custom_endpoint(self) -> None:
        """Test S3ClientConfig with custom S3-compatible endpoint."""
        config: S3ClientConfig = {
            "endpoint_url": "https://minio.example.com:9000",
            "region_name": "us-east-1",  # Region can be any value for custom endpoints
            "credentials": {
                "access_key": "minio-access-key",
                "secret_key": "minio-secret-key",
                "session_token": None
            },
            "verify": False  # Skip SSL verification for self-signed certs
        }
        
        # Verify custom endpoint and SSL verification settings
        assert "minio.example.com" in config["endpoint_url"]
        assert config["verify"] is False


class TestStorageOptions:
    """Test cases for StorageOptions type."""

    def test_valid_options(self, storage_options: StorageOptions) -> None:
        """Test that valid StorageOptions can be created."""
        # The fixture provides valid options, so we just need to verify its structure
        assert "encryption" in storage_options
        assert "content_type" in storage_options
        assert "metadata" in storage_options
        assert "acl" in storage_options
        assert "storage_class" in storage_options
        
        # Verify encryption structure
        encryption = storage_options["encryption"]
        assert "algorithm" in encryption
        assert encryption["algorithm"] == "AES256"  # Required by spec
        assert "kms_key_id" in encryption
        
        # Verify types
        assert isinstance(storage_options["content_type"], str)
        assert isinstance(storage_options["metadata"], dict)
        assert isinstance(storage_options["acl"], str)
        assert isinstance(storage_options["storage_class"], str)

    def test_minimal_options(self) -> None:
        """Test StorageOptions with minimal required fields."""
        # StorageOptions is marked with total=False, so all fields are optional
        options: StorageOptions = {}
        
        # Verify that an empty options dict is valid
        assert isinstance(options, dict)

    def test_options_with_encryption(self) -> None:
        """Test StorageOptions with AES-256 encryption as required by spec."""
        options: StorageOptions = {
            "encryption": {
                "algorithm": "AES256",
                "kms_key_id": None
            }
        }
        
        # Verify encryption settings
        assert options["encryption"]["algorithm"] == "AES256"
        assert options["encryption"]["kms_key_id"] is None

    def test_options_with_kms_key(self) -> None:
        """Test StorageOptions with KMS key for encryption."""
        options: StorageOptions = {
            "encryption": {
                "algorithm": "AES256",
                "kms_key_id": "arn:aws:kms:us-east-1:123456789012:key/abcd1234-ab12-cd34-ef56-abcdef123456"
            }
        }
        
        # Verify KMS key ID
        assert "arn:aws:kms" in options["encryption"]["kms_key_id"]

    def test_options_with_all_fields(self) -> None:
        """Test StorageOptions with all possible fields."""
        options: StorageOptions = {
            "encryption": {
                "algorithm": "AES256",
                "kms_key_id": None
            },
            "content_type": "application/pdf",
            "metadata": {
                "application-id": "app-123",
                "document-type": "loan_application"
            },
            "acl": "private",
            "storage_class": "STANDARD",
            "cache_control": "max-age=86400",
            "content_disposition": "attachment; filename=\"document.pdf\"",
            "content_encoding": "gzip",
            "content_language": "en-US",
            "website_redirect_location": None,
            "tagging": "key1=value1&key2=value2"
        }
        
        # Verify all fields
        assert options["content_type"] == "application/pdf"
        assert options["metadata"]["application-id"] == "app-123"
        assert options["acl"] == "private"
        assert options["storage_class"] == "STANDARD"
        assert options["cache_control"] == "max-age=86400"
        assert "attachment" in options["content_disposition"]
        assert options["content_encoding"] == "gzip"
        assert options["content_language"] == "en-US"
        assert options["website_redirect_location"] is None
        assert "key1=value1" in options["tagging"]


class TestStorageMetadata:
    """Test cases for StorageMetadata type."""

    def test_valid_metadata(self, storage_metadata_loan_application: StorageMetadata) -> None:
        """Test that valid StorageMetadata can be created."""
        # The fixture provides valid metadata, so we just need to verify its structure
        assert_valid_storage_metadata(storage_metadata_loan_application)

    def test_metadata_with_minimal_fields(self) -> None:
        """Test StorageMetadata with minimal required fields."""
        now = datetime.utcnow()
        metadata: StorageMetadata = {
            "document_id": str(uuid.uuid4()),
            "application_id": "APP-" + str(uuid.uuid4())[:8],
            "filename": "document.pdf",
            "file_size": 1024,
            "content_type": "application/pdf",
            "classification": {
                "category": "loan_application",
                "confidence": 0.95,
                "model_version": "1.0.0",
                "sub_categories": None,
                "classification_date": now,
                "classifier_id": "test-classifier"
            },
            "upload_timestamp": now,
            "last_modified": now,
            "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
            "processing_status": "processed",
            "tags": {},
            "custom_metadata": {},
            "ocr_status": None,
            "ocr_confidence": None,
            "page_count": None,
            "encryption_status": "encrypted",
            "encryption_type": "AES256",
            "storage_class": "STANDARD",
            "retention_period": None,
            "legal_hold": False
        }
        
        # Verify minimal metadata
        assert_valid_storage_metadata(metadata)

    def test_metadata_with_ocr_information(self) -> None:
        """Test StorageMetadata with OCR processing information."""
        now = datetime.utcnow()
        metadata: StorageMetadata = {
            "document_id": str(uuid.uuid4()),
            "application_id": "APP-" + str(uuid.uuid4())[:8],
            "filename": "document.pdf",
            "file_size": 1024,
            "content_type": "application/pdf",
            "classification": {
                "category": "loan_application",
                "confidence": 0.95,
                "model_version": "1.0.0",
                "sub_categories": None,
                "classification_date": now,
                "classifier_id": "test-classifier"
            },
            "upload_timestamp": now,
            "last_modified": now,
            "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
            "processing_status": "processed",
            "tags": {},
            "custom_metadata": {},
            "ocr_status": "completed",
            "ocr_confidence": 0.92,
            "page_count": 5,
            "encryption_status": "encrypted",
            "encryption_type": "AES256",
            "storage_class": "STANDARD",
            "retention_period": 365,
            "legal_hold": False
        }
        
        # Verify OCR information
        assert metadata["ocr_status"] == "completed"
        assert metadata["ocr_confidence"] == 0.92
        assert metadata["page_count"] == 5

    def test_metadata_with_subcategories(self) -> None:
        """Test StorageMetadata with document subcategories."""
        now = datetime.utcnow()
        metadata: StorageMetadata = {
            "document_id": str(uuid.uuid4()),
            "application_id": "APP-" + str(uuid.uuid4())[:8],
            "filename": "document.pdf",
            "file_size": 1024,
            "content_type": "application/pdf",
            "classification": {
                "category": "tax_return",
                "confidence": 0.95,
                "model_version": "1.0.0",
                "sub_categories": ["1040", "schedule_c", "schedule_e"],
                "classification_date": now,
                "classifier_id": "test-classifier"
            },
            "upload_timestamp": now,
            "last_modified": now,
            "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
            "processing_status": "processed",
            "tags": {},
            "custom_metadata": {},
            "ocr_status": None,
            "ocr_confidence": None,
            "page_count": None,
            "encryption_status": "encrypted",
            "encryption_type": "AES256",
            "storage_class": "STANDARD",
            "retention_period": None,
            "legal_hold": False
        }
        
        # Verify subcategories
        assert metadata["classification"]["sub_categories"] is not None
        assert "1040" in metadata["classification"]["sub_categories"]
        assert "schedule_c" in metadata["classification"]["sub_categories"]
        assert "schedule_e" in metadata["classification"]["sub_categories"]

    def test_metadata_with_legal_hold(self) -> None:
        """Test StorageMetadata with legal hold enabled."""
        now = datetime.utcnow()
        metadata: StorageMetadata = {
            "document_id": str(uuid.uuid4()),
            "application_id": "APP-" + str(uuid.uuid4())[:8],
            "filename": "document.pdf",
            "file_size": 1024,
            "content_type": "application/pdf",
            "classification": {
                "category": "loan_application",
                "confidence": 0.95,
                "model_version": "1.0.0",
                "sub_categories": None,
                "classification_date": now,
                "classifier_id": "test-classifier"
            },
            "upload_timestamp": now,
            "last_modified": now,
            "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
            "processing_status": "processed",
            "tags": {"legal_hold_reason": "litigation"},
            "custom_metadata": {"case_number": "CASE-12345"},
            "ocr_status": None,
            "ocr_confidence": None,
            "page_count": None,
            "encryption_status": "encrypted",
            "encryption_type": "AES256",
            "storage_class": "STANDARD",
            "retention_period": 2555,  # 7 years in days
            "legal_hold": True
        }
        
        # Verify legal hold
        assert metadata["legal_hold"] is True
        assert metadata["retention_period"] == 2555
        assert metadata["tags"]["legal_hold_reason"] == "litigation"
        assert metadata["custom_metadata"]["case_number"] == "CASE-12345"


class TestBucketConfig:
    """Test cases for BucketConfig type."""

    def test_valid_bucket_config(self) -> None:
        """Test that a valid BucketConfig can be created."""
        config: BucketConfig = {
            "name": "mca-documents-production",
            "region": "us-east-1",
            "encryption": {
                "algorithm": "AES256",
                "kms_key_id": None
            },
            "versioning_enabled": True,
            "lifecycle_rules": [],
            "cors_enabled": False,
            "logging_enabled": True,
            "logging_target_bucket": "mca-logs",
            "logging_target_prefix": "s3-access-logs/",
            "public_access_blocked": True,
            "object_lock_enabled": False,
            "replication_enabled": False,
            "replication_target": None
        }
        
        # Verify bucket config
        assert config["name"] == "mca-documents-production"
        assert config["region"] == "us-east-1"
        assert config["encryption"]["algorithm"] == "AES256"
        assert config["versioning_enabled"] is True
        assert config["public_access_blocked"] is True

    def test_bucket_config_with_lifecycle_rules(self) -> None:
        """Test BucketConfig with lifecycle rules."""
        config: BucketConfig = {
            "name": "mca-documents-production",
            "region": "us-east-1",
            "encryption": {
                "algorithm": "AES256",
                "kms_key_id": None
            },
            "versioning_enabled": True,
            "lifecycle_rules": [
                {
                    "id": "transition-to-ia",
                    "prefix": "documents/",
                    "status": "Enabled",
                    "transitions": [
                        {
                            "days": 30,
                            "storage_class": "STANDARD_IA"
                        }
                    ],
                    "expiration": None,
                    "noncurrent_version_transitions": None,
                    "noncurrent_version_expiration": None
                },
                {
                    "id": "expire-old-documents",
                    "prefix": "temp/",
                    "status": "Enabled",
                    "transitions": [],
                    "expiration": {
                        "days": 90,
                        "expired_object_delete_marker": True
                    },
                    "noncurrent_version_transitions": None,
                    "noncurrent_version_expiration": None
                }
            ],
            "cors_enabled": False,
            "logging_enabled": True,
            "logging_target_bucket": "mca-logs",
            "logging_target_prefix": "s3-access-logs/",
            "public_access_blocked": True,
            "object_lock_enabled": False,
            "replication_enabled": False,
            "replication_target": None
        }
        
        # Verify lifecycle rules
        assert len(config["lifecycle_rules"]) == 2
        
        # Verify transition rule
        transition_rule = config["lifecycle_rules"][0]
        assert transition_rule["id"] == "transition-to-ia"
        assert transition_rule["status"] == "Enabled"
        assert len(transition_rule["transitions"]) == 1
        assert transition_rule["transitions"][0]["days"] == 30
        assert transition_rule["transitions"][0]["storage_class"] == "STANDARD_IA"
        
        # Verify expiration rule
        expiration_rule = config["lifecycle_rules"][1]
        assert expiration_rule["id"] == "expire-old-documents"
        assert expiration_rule["status"] == "Enabled"
        assert expiration_rule["expiration"] is not None
        assert expiration_rule["expiration"]["days"] == 90
        assert expiration_rule["expiration"]["expired_object_delete_marker"] is True

    def test_environment_buckets(self) -> None:
        """Test EnvironmentBuckets with configurations for all environments."""
        buckets: EnvironmentBuckets = {
            "production": {
                "name": "mca-documents-production",
                "region": "us-east-1",
                "encryption": {
                    "algorithm": "AES256",
                    "kms_key_id": None
                },
                "versioning_enabled": True,
                "lifecycle_rules": [],
                "cors_enabled": False,
                "logging_enabled": True,
                "logging_target_bucket": "mca-logs-production",
                "logging_target_prefix": "s3-access-logs/",
                "public_access_blocked": True,
                "object_lock_enabled": False,
                "replication_enabled": True,
                "replication_target": "mca-documents-dr"
            },
            "staging": {
                "name": "mca-documents-staging",
                "region": "us-east-1",
                "encryption": {
                    "algorithm": "AES256",
                    "kms_key_id": None
                },
                "versioning_enabled": True,
                "lifecycle_rules": [],
                "cors_enabled": False,
                "logging_enabled": True,
                "logging_target_bucket": "mca-logs-staging",
                "logging_target_prefix": "s3-access-logs/",
                "public_access_blocked": True,
                "object_lock_enabled": False,
                "replication_enabled": False,
                "replication_target": None
            },
            "development": {
                "name": "mca-documents-development",
                "region": "us-east-1",
                "encryption": {
                    "algorithm": "AES256",
                    "kms_key_id": None
                },
                "versioning_enabled": True,
                "lifecycle_rules": [],
                "cors_enabled": True,  # Allow CORS for development
                "logging_enabled": False,
                "logging_target_bucket": None,
                "logging_target_prefix": None,
                "public_access_blocked": True,
                "object_lock_enabled": False,
                "replication_enabled": False,
                "replication_target": None
            }
        }
        
        # Verify environment-specific configurations
        assert buckets["production"]["name"] == "mca-documents-production"
        assert buckets["staging"]["name"] == "mca-documents-staging"
        assert buckets["development"]["name"] == "mca-documents-development"
        
        # Verify production-specific settings
        assert buckets["production"]["replication_enabled"] is True
        assert buckets["production"]["replication_target"] == "mca-documents-dr"
        
        # Verify development-specific settings
        assert buckets["development"]["cors_enabled"] is True
        assert buckets["development"]["logging_enabled"] is False


class TestStorageResult:
    """Test cases for StorageResult type."""

    def test_successful_result(self) -> None:
        """Test StorageResult for a successful operation."""
        result: StorageResult = {
            "success": True,
            "error": None,
            "etag": "\"1234567890abcdef\"",
            "version_id": "v1",
            "storage_class": "STANDARD",
            "metadata": {"application-id": "app-123"},
            "encryption_status": "encrypted"
        }
        
        # Verify successful result
        assert result["success"] is True
        assert result["error"] is None
        assert result["etag"] is not None
        assert result["version_id"] is not None
        assert result["storage_class"] == "STANDARD"
        assert result["metadata"] is not None
        assert result["encryption_status"] == "encrypted"

    def test_error_result(self) -> None:
        """Test StorageResult for a failed operation."""
        now = datetime.utcnow()
        result: StorageResult = {
            "success": False,
            "error": {
                "code": "NoSuchKey",
                "message": "The specified key does not exist",
                "request_id": "1234567890ABCDEF",
                "resource": "documents/test.pdf",
                "details": {
                    "service": "S3",
                    "status_code": 404,
                    "operation": "GetObject",
                    "sender_fault": True,
                    "retry_attempts": 0
                },
                "timestamp": now,
                "recoverable": False
            },
            "etag": None,
            "version_id": None,
            "storage_class": None,
            "metadata": None,
            "encryption_status": None
        }
        
        # Verify error result
        assert result["success"] is False
        assert result["error"] is not None
        assert result["error"]["code"] == "NoSuchKey"
        assert result["error"]["message"] == "The specified key does not exist"
        assert result["error"]["request_id"] == "1234567890ABCDEF"
        assert result["error"]["resource"] == "documents/test.pdf"
        assert result["error"]["details"] is not None
        assert result["error"]["details"]["status_code"] == 404
        assert result["error"]["details"]["operation"] == "GetObject"
        assert result["error"]["timestamp"] == now
        assert result["error"]["recoverable"] is False

    def test_recoverable_error_result(self) -> None:
        """Test StorageResult for a recoverable error."""
        now = datetime.utcnow()
        result: StorageResult = {
            "success": False,
            "error": {
                "code": "InternalError",
                "message": "We encountered an internal error. Please try again.",
                "request_id": "1234567890ABCDEF",
                "resource": "documents/test.pdf",
                "details": {
                    "service": "S3",
                    "status_code": 500,
                    "operation": "PutObject",
                    "sender_fault": False,
                    "retry_attempts": 2
                },
                "timestamp": now,
                "recoverable": True
            },
            "etag": None,
            "version_id": None,
            "storage_class": None,
            "metadata": None,
            "encryption_status": None
        }
        
        # Verify recoverable error
        assert result["success"] is False
        assert result["error"] is not None
        assert result["error"]["code"] == "InternalError"
        assert result["error"]["details"]["status_code"] == 500
        assert result["error"]["details"]["retry_attempts"] == 2
        assert result["error"]["recoverable"] is True

    def test_minimal_error_result(self) -> None:
        """Test StorageResult with minimal error information."""
        now = datetime.utcnow()
        result: StorageResult = {
            "success": False,
            "error": {
                "code": "AccessDenied",
                "message": "Access Denied",
                "request_id": None,
                "resource": None,
                "details": None,
                "timestamp": now,
                "recoverable": False
            },
            "etag": None,
            "version_id": None,
            "storage_class": None,
            "metadata": None,
            "encryption_status": None
        }
        
        # Verify minimal error
        assert result["success"] is False
        assert result["error"] is not None
        assert result["error"]["code"] == "AccessDenied"
        assert result["error"]["message"] == "Access Denied"
        assert result["error"]["request_id"] is None
        assert result["error"]["resource"] is None
        assert result["error"]["details"] is None
        assert result["error"]["timestamp"] == now
        assert result["error"]["recoverable"] is False


class TestStorageKey:
    """Test cases for StorageKey type."""

    def test_valid_storage_key(self) -> None:
        """Test that a valid StorageKey can be created."""
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S")
        key: StorageKey = {
            "application_id": "APP-12345",
            "document_id": "DOC-67890",
            "document_type": "loan_application",
            "timestamp": timestamp,
            "extension": "pdf"
        }
        
        # Verify storage key
        assert key["application_id"] == "APP-12345"
        assert key["document_id"] == "DOC-67890"
        assert key["document_type"] == "loan_application"
        assert key["timestamp"] == timestamp
        assert key["extension"] == "pdf"

    def test_storage_key_generator(self) -> None:
        """Test a simple implementation of StorageKeyGenerator protocol."""
        class TestKeyGenerator:
            def generate_key(self, metadata: Dict[str, Any]) -> str:
                app_id = metadata.get("application_id", "unknown")
                doc_id = metadata.get("document_id", str(uuid.uuid4()))
                doc_type = metadata.get("document_type", "unknown")
                timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                extension = metadata.get("extension", "pdf")
                
                return f"{app_id}/{doc_type}/{doc_id}_{timestamp}.{extension}"
        
        # Create a generator instance
        generator = TestKeyGenerator()
        
        # Test key generation
        metadata = {
            "application_id": "APP-12345",
            "document_id": "DOC-67890",
            "document_type": "loan_application",
            "extension": "pdf"
        }
        
        key = generator.generate_key(metadata)
        
        # Verify key format
        assert key.startswith("APP-12345/loan_application/DOC-67890_")
        assert key.endswith(".pdf")

    def test_storage_key_with_uuid(self) -> None:
        """Test StorageKey with UUID values."""
        app_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d%H%M%S")
        
        key: StorageKey = {
            "application_id": app_id,
            "document_id": doc_id,
            "document_type": "bank_statement",
            "timestamp": timestamp,
            "extension": "pdf"
        }
        
        # Verify UUID values
        assert key["application_id"] == app_id
        assert key["document_id"] == doc_id
        assert key["document_type"] == "bank_statement"

    def test_storage_key_with_different_extensions(self) -> None:
        """Test StorageKey with different file extensions."""
        extensions = ["pdf", "png", "jpg", "tiff", "docx", "xlsx"]
        
        for ext in extensions:
            key: StorageKey = {
                "application_id": "APP-12345",
                "document_id": "DOC-67890",
                "document_type": "identity_document",
                "timestamp": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
                "extension": ext
            }
            
            # Verify extension
            assert key["extension"] == ext


class TestRetryConfig:
    """Test cases for RetryConfig type."""

    def test_valid_retry_config(self) -> None:
        """Test that a valid RetryConfig can be created."""
        config: RetryConfig = {
            "max_attempts": 3,
            "initial_delay_ms": 100,
            "max_delay_ms": 5000,
            "backoff_factor": 2.0,
            "retryable_errors": ["InternalError", "ServiceUnavailable", "RequestTimeout"]
        }
        
        # Verify retry config
        assert config["max_attempts"] == 3
        assert config["initial_delay_ms"] == 100
        assert config["max_delay_ms"] == 5000
        assert config["backoff_factor"] == 2.0
        assert "InternalError" in config["retryable_errors"]
        assert "ServiceUnavailable" in config["retryable_errors"]
        assert "RequestTimeout" in config["retryable_errors"]


class TestStorageOperations:
    """Test cases for StorageOperations protocol."""

    def test_mock_storage_operations(self, mock_storage_operations: Any, sample_document_path: Path) -> None:
        """Test that MockStorageOperations implements the StorageOperations protocol."""
        # Test upload_file
        result = mock_storage_operations.upload_file(
            local_path=sample_document_path,
            storage_key="test/document.pdf"
        )
        assert_valid_storage_result(result)
        assert result["success"] is True
        
        # Test get_metadata
        metadata = mock_storage_operations.get_metadata("test/document.pdf")
        if isinstance(metadata, dict) and "success" in metadata:
            # If it's a StorageResult (error case)
            assert_valid_storage_result(metadata)
        else:
            # If it's StorageMetadata
            assert_valid_storage_metadata(metadata)
        
        # Test delete_file
        result = mock_storage_operations.delete_file("test/document.pdf")
        assert_valid_storage_result(result)
        assert result["success"] is True


# Helper functions

def assert_valid_storage_metadata(metadata: StorageMetadata) -> None:
    """Assert that storage metadata is valid.
    
    Args:
        metadata: StorageMetadata to validate
        
    Raises:
        AssertionError: If the storage metadata is invalid
    """
    assert isinstance(metadata, dict), "Metadata must be a dictionary"
    assert "document_id" in metadata, "Metadata must have a 'document_id' key"
    assert "application_id" in metadata, "Metadata must have an 'application_id' key"
    assert "filename" in metadata, "Metadata must have a 'filename' key"
    assert "file_size" in metadata, "Metadata must have a 'file_size' key"
    assert "content_type" in metadata, "Metadata must have a 'content_type' key"
    assert "classification" in metadata, "Metadata must have a 'classification' key"
    assert "upload_timestamp" in metadata, "Metadata must have an 'upload_timestamp' key"
    assert "last_modified" in metadata, "Metadata must have a 'last_modified' key"
    assert "encryption_status" in metadata, "Metadata must have an 'encryption_status' key"
    assert "encryption_type" in metadata, "Metadata must have an 'encryption_type' key"
    
    # Validate classification
    classification = metadata["classification"]
    assert isinstance(classification, dict), "Classification must be a dictionary"
    assert "category" in classification, "Classification must have a 'category' key"
    assert "confidence" in classification, "Classification must have a 'confidence' key"
    assert "model_version" in classification, "Classification must have a 'model_version' key"
    assert "classification_date" in classification, "Classification must have a 'classification_date' key"
    assert isinstance(classification["confidence"], float), "Confidence must be a float"
    assert 0.0 <= classification["confidence"] <= 1.0, "Confidence must be between 0.0 and 1.0"


def assert_valid_storage_result(result: StorageResult) -> None:
    """Assert that a storage result is valid.
    
    Args:
        result: StorageResult to validate
        
    Raises:
        AssertionError: If the storage result is invalid
    """
    assert isinstance(result, dict), "Result must be a dictionary"
    assert "success" in result, "Result must have a 'success' key"
    assert isinstance(result["success"], bool), "'success' must be a boolean"
    
    if result["success"]:
        assert result["error"] is None, "'error' must be None for successful operations"
    else:
        assert "error" in result, "Failed result must have an 'error' key"
        assert isinstance(result["error"], dict), "'error' must be a dictionary"
        assert "code" in result["error"], "Error must have a 'code' key"
        assert "message" in result["error"], "Error must have a 'message' key"
        assert "timestamp" in result["error"], "Error must have a 'timestamp' key"
        assert "recoverable" in result["error"], "Error must have a 'recoverable' key"