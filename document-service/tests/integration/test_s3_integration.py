"""Integration tests for S3 storage operations in the Document Service.

This module contains integration tests for the StorageService class, which handles
S3-compatible storage operations for the Document Service. The tests verify that
the service correctly stores documents with AES-256 encryption, retrieves documents
for classification, and manages document metadata.

The tests also validate error handling, retry logic, and secure access controls
to ensure reliable document storage and retrieval in the classification process.
"""

import os
import uuid
import tempfile
import json
import pytest
from unittest.mock import patch, MagicMock
import boto3
from botocore.exceptions import ClientError

# Import the service under test
from services.storage_service import StorageService


class TestS3Integration:
    """Integration tests for S3 storage operations in the Document Service."""

    def test_s3_client_connection(self, s3_client, s3_buckets):
        """Test that the StorageService can connect to S3 with appropriate authentication.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Verify that the service is connected to S3
        assert storage_service.check_connection() is True
        
        # Verify that the service is using the correct bucket
        assert storage_service.bucket_name in s3_buckets.values()

    def test_document_upload_with_encryption(self, s3_client, s3_buckets, validation_utils):
        """Test that documents can be uploaded with AES-256 encryption.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            validation_utils: Utilities for validating test results
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"Test document content")
            temp_path = temp_file.name
        
        try:
            # Generate a unique document ID
            document_id = str(uuid.uuid4())
            
            # Upload the document
            result = storage_service.upload_document(
                file_path=temp_path,
                document_id=document_id,
                metadata={
                    "application_id": "test-app-123",
                    "document_type": "test_document"
                }
            )
            
            # Verify that the upload was successful
            assert result.success is True
            assert result.object_key is not None
            assert result.error is None
            
            # Validate that the document was stored with AES-256 encryption
            validation_utils["validate_storage_encryption"](
                s3_client,
                storage_service.bucket_name,
                result.object_key
            )
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_document_upload_from_bytes(self, s3_client, s3_buckets, validation_utils):
        """Test that documents can be uploaded from bytes with AES-256 encryption.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            validation_utils: Utilities for validating test results
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create document content as bytes
        document_content = b"Test document content as bytes"
        
        # Generate a unique document ID and filename
        document_id = str(uuid.uuid4())
        file_name = f"test_document_{document_id}.pdf"
        
        # Upload the document from bytes
        result = storage_service.upload_document_from_bytes(
            file_bytes=document_content,
            file_name=file_name,
            document_id=document_id,
            metadata={
                "application_id": "test-app-123",
                "document_type": "test_document"
            }
        )
        
        # Verify that the upload was successful
        assert result.success is True
        assert result.object_key is not None
        assert result.error is None
        
        # Validate that the document was stored with AES-256 encryption
        validation_utils["validate_storage_encryption"](
            s3_client,
            storage_service.bucket_name,
            result.object_key
        )

    def test_document_download(self, s3_client, s3_buckets, s3_document_storage):
        """Test that documents can be downloaded from S3.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            s3_document_storage: Fixture for storing and retrieving documents from S3
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create document content
        document_content = b"Test document content for download"
        document_key = f"documents/test_{uuid.uuid4()}.pdf"
        
        # Store the document in S3 using the fixture
        s3_document_storage["store"](
            document_content=document_content,
            document_key=document_key,
            metadata={"test": "metadata"},
            bucket_type="staging"
        )
        
        # Download the document
        downloaded_path, error = storage_service.download_document(document_key)
        
        try:
            # Verify that the download was successful
            assert error is None
            assert downloaded_path is not None
            assert os.path.exists(downloaded_path)
            
            # Verify the content of the downloaded file
            with open(downloaded_path, "rb") as f:
                content = f.read()
                assert content == document_content
        finally:
            # Clean up the downloaded file
            if downloaded_path and os.path.exists(downloaded_path):
                os.unlink(downloaded_path)

    def test_document_download_as_bytes(self, s3_client, s3_buckets, s3_document_storage):
        """Test that documents can be downloaded as bytes from S3.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            s3_document_storage: Fixture for storing and retrieving documents from S3
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create document content
        document_content = b"Test document content for download as bytes"
        document_key = f"documents/test_{uuid.uuid4()}.pdf"
        
        # Store the document in S3 using the fixture
        s3_document_storage["store"](
            document_content=document_content,
            document_key=document_key,
            metadata={"test": "metadata"},
            bucket_type="staging"
        )
        
        # Download the document as bytes
        content, error = storage_service.download_document_as_bytes(document_key)
        
        # Verify that the download was successful
        assert error is None
        assert content is not None
        assert content == document_content

    def test_document_metadata_management(self, s3_client, s3_buckets, s3_document_storage):
        """Test that document metadata can be retrieved and updated.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            s3_document_storage: Fixture for storing and retrieving documents from S3
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create document content
        document_content = b"Test document content for metadata management"
        document_key = f"documents/test_{uuid.uuid4()}.pdf"
        
        # Store the document in S3 with metadata
        initial_metadata = {
            "document_id": str(uuid.uuid4()),
            "application_id": "test-app-123",
            "document_type": "test_document"
        }
        
        s3_document_storage["store"](
            document_content=document_content,
            document_key=document_key,
            metadata=initial_metadata,
            bucket_type="staging"
        )
        
        # Get the document metadata
        metadata, error = storage_service.get_document_metadata(document_key)
        
        # Verify that the metadata was retrieved successfully
        assert error is None
        assert metadata is not None
        
        # Verify that the metadata contains the expected values
        for key, value in initial_metadata.items():
            assert key in metadata
            assert metadata[key] == value
        
        # Update the metadata
        updated_metadata = {
            "document_type": "updated_document_type",
            "classification": "invoice",
            "confidence": "0.95"
        }
        
        success, error = storage_service.update_document_metadata(document_key, updated_metadata)
        
        # Verify that the update was successful
        assert error is None
        assert success is True
        
        # Get the updated metadata
        metadata, error = storage_service.get_document_metadata(document_key)
        
        # Verify that the metadata was updated
        assert error is None
        assert metadata is not None
        
        # Verify that the metadata contains the updated values
        for key, value in updated_metadata.items():
            assert key in metadata
            assert metadata[key] == value
        
        # Verify that the original metadata is still present
        for key, value in initial_metadata.items():
            if key != "document_type":  # This was updated
                assert key in metadata
                assert metadata[key] == value

    def test_error_handling_and_retry_logic(self, s3_client, s3_buckets):
        """Test that the StorageService handles errors and retries operations.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create a non-existent document key
        document_key = f"documents/nonexistent_{uuid.uuid4()}.pdf"
        
        # Attempt to download a non-existent document
        downloaded_path, error = storage_service.download_document(document_key)
        
        # Verify that the error is handled properly
        assert downloaded_path is None
        assert error is not None
        assert "not found" in error.lower() or "NoSuchKey" in error
        
        # Test retry logic by patching the S3 client to fail temporarily
        with patch.object(storage_service, 's3_client') as mock_s3_client:
            # Configure the mock to fail on the first two attempts and succeed on the third
            mock_head_object = MagicMock(side_effect=[
                boto3.exceptions.ClientError({"Error": {"Code": "500", "Message": "Internal Error"}}, "head_object"),
                boto3.exceptions.ClientError({"Error": {"Code": "500", "Message": "Internal Error"}}, "head_object"),
                {"Metadata": {"test": "metadata"}, "ContentLength": 100, "ContentType": "application/pdf"}
            ])
            mock_s3_client.head_object = mock_head_object
            
            # Attempt to get metadata with retry logic
            metadata, error = storage_service.get_document_metadata(document_key)
            
            # Verify that the operation was retried and eventually succeeded
            assert mock_head_object.call_count >= 3
            assert error is None
            assert metadata is not None
            assert "test" in metadata
            assert metadata["test"] == "metadata"

    def test_secure_access_controls(self, s3_client, s3_buckets, s3_document_storage):
        """Test that the StorageService implements secure access controls.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            s3_document_storage: Fixture for storing and retrieving documents from S3
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create document content
        document_content = b"Test document content for secure access"
        document_key = f"documents/test_{uuid.uuid4()}.pdf"
        
        # Store the document in S3
        s3_document_storage["store"](
            document_content=document_content,
            document_key=document_key,
            metadata={"test": "metadata"},
            bucket_type="staging"
        )
        
        # Generate a presigned URL for temporary access
        url, error = storage_service.generate_presigned_url(document_key, expiration=60)
        
        # Verify that the URL was generated successfully
        assert error is None
        assert url is not None
        assert document_key in url
        assert "Expires=" in url
        assert "AWSAccessKeyId=" in url
        assert "Signature=" in url

    def test_document_versioning_and_history(self, s3_client, s3_buckets, s3_document_storage):
        """Test that the StorageService supports document versioning and history tracking.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            s3_document_storage: Fixture for storing and retrieving documents from S3
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create document content
        document_content_v1 = b"Test document content version 1"
        document_content_v2 = b"Test document content version 2"
        document_key = f"documents/test_{uuid.uuid4()}.pdf"
        
        # Store the document in S3 (version 1)
        s3_document_storage["store"](
            document_content=document_content_v1,
            document_key=document_key,
            metadata={"version": "1"},
            bucket_type="staging"
        )
        
        # Get the document metadata (version 1)
        metadata_v1, error = storage_service.get_document_metadata(document_key)
        
        # Verify that the metadata was retrieved successfully
        assert error is None
        assert metadata_v1 is not None
        assert metadata_v1["version"] == "1"
        
        # Store the document in S3 (version 2)
        s3_document_storage["store"](
            document_content=document_content_v2,
            document_key=document_key,
            metadata={"version": "2"},
            bucket_type="staging"
        )
        
        # Get the document metadata (version 2)
        metadata_v2, error = storage_service.get_document_metadata(document_key)
        
        # Verify that the metadata was updated
        assert error is None
        assert metadata_v2 is not None
        assert metadata_v2["version"] == "2"
        
        # Download the document (should be version 2)
        content, error = storage_service.download_document_as_bytes(document_key)
        
        # Verify that the content is from version 2
        assert error is None
        assert content is not None
        assert content == document_content_v2

    def test_classification_metadata_extraction(self, s3_client, s3_buckets, s3_document_storage):
        """Test that the StorageService can extract metadata for classification.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            s3_document_storage: Fixture for storing and retrieving documents from S3
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create document content
        document_content = b"Test document content for classification"
        document_key = f"documents/test_{uuid.uuid4()}.pdf"
        
        # Store the document in S3 with classification metadata
        s3_document_storage["store"](
            document_content=document_content,
            document_key=document_key,
            metadata={
                "document_id": str(uuid.uuid4()),
                "original_filename": "test.pdf",
                "classification": "invoice",
                "classification_confidence": "0.95",
                "document_type": "financial"
            },
            bucket_type="staging"
        )
        
        # Extract classification metadata
        metadata, error = storage_service.extract_document_metadata_for_classification(document_key)
        
        # Verify that the metadata was extracted successfully
        assert error is None
        assert metadata is not None
        
        # Verify that the metadata contains the expected classification information
        assert metadata["object_key"] == document_key
        assert metadata["file_extension"] == "pdf"
        assert metadata["original_filename"] == "test.pdf"
        assert metadata["previous_classification"] == "invoice"
        assert metadata["previous_confidence"] == 0.95
        assert metadata["previous_document_type"] == "financial"

    def test_update_classification_results(self, s3_client, s3_buckets, s3_document_storage):
        """Test that the StorageService can update classification results.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            s3_document_storage: Fixture for storing and retrieving documents from S3
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create document content
        document_content = b"Test document content for classification update"
        document_key = f"documents/test_{uuid.uuid4()}.pdf"
        
        # Store the document in S3
        s3_document_storage["store"](
            document_content=document_content,
            document_key=document_key,
            metadata={"document_id": str(uuid.uuid4())},
            bucket_type="staging"
        )
        
        # Create classification results
        classification_results = {
            "classification": "bank_statement",
            "confidence": 0.98,
            "document_type": "financial",
            "page_count": 3,
            "has_signature": True,
            "processing_time_ms": 120
        }
        
        # Update classification results
        success, error = storage_service.update_classification_results(document_key, classification_results)
        
        # Verify that the update was successful
        assert error is None
        assert success is True
        
        # Get the updated metadata
        metadata, error = storage_service.get_document_metadata(document_key)
        
        # Verify that the metadata contains the updated classification results
        assert error is None
        assert metadata is not None
        assert metadata["classification"] == "bank_statement"
        assert metadata["classification_confidence"] == "0.98"
        assert metadata["document_type"] == "financial"
        assert metadata["classification_page_count"] == "3"
        assert metadata["classification_has_signature"] == "True"
        assert metadata["classification_processing_time_ms"] == "120"
        assert "classification_timestamp" in metadata

    def test_storage_metrics(self, s3_client, s3_buckets, s3_document_storage):
        """Test that the StorageService can provide storage metrics.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            s3_document_storage: Fixture for storing and retrieving documents from S3
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create and store multiple documents
        for i in range(5):
            document_content = f"Test document content {i}".encode()
            document_key = f"documents/test_{uuid.uuid4()}.pdf"
            
            s3_document_storage["store"](
                document_content=document_content,
                document_key=document_key,
                metadata={"document_id": str(uuid.uuid4())},
                bucket_type="staging"
            )
        
        # Get storage metrics
        metrics = storage_service.get_storage_metrics()
        
        # Verify that the metrics contain the expected information
        assert metrics is not None
        assert "bucket_name" in metrics
        assert metrics["bucket_name"] == storage_service.bucket_name
        assert "document_count" in metrics
        assert metrics["document_count"] >= 5  # At least the 5 documents we just added
        assert "total_size_bytes" in metrics
        assert metrics["total_size_bytes"] > 0
        assert "connection_status" in metrics
        assert metrics["connection_status"] == "healthy"
        assert "timestamp" in metrics

    def test_list_documents(self, s3_client, s3_buckets, s3_document_storage):
        """Test that the StorageService can list documents in the bucket.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            s3_document_storage: Fixture for storing and retrieving documents from S3
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create a unique prefix for this test
        test_prefix = f"documents/test_list_{uuid.uuid4()}/"
        
        # Create and store multiple documents with the test prefix
        for i in range(3):
            document_content = f"Test document content {i}".encode()
            document_key = f"{test_prefix}test_{i}.pdf"
            
            s3_document_storage["store"](
                document_content=document_content,
                document_key=document_key,
                metadata={"document_id": str(uuid.uuid4())},
                bucket_type="staging"
            )
        
        # List documents with the test prefix
        documents, error = storage_service.list_documents(prefix=test_prefix)
        
        # Verify that the documents were listed successfully
        assert error is None
        assert documents is not None
        assert len(documents) == 3
        
        # Verify that each document has the expected attributes
        for doc in documents:
            assert "key" in doc
            assert test_prefix in doc["key"]
            assert "size" in doc
            assert doc["size"] > 0
            assert "last_modified" in doc
            assert "etag" in doc

    def test_delete_document(self, s3_client, s3_buckets, s3_document_storage):
        """Test that the StorageService can delete documents.
        
        Args:
            s3_client: Mocked S3 client fixture
            s3_buckets: Dictionary of test bucket names
            s3_document_storage: Fixture for storing and retrieving documents from S3
        """
        # Initialize the StorageService
        storage_service = StorageService()
        
        # Create document content
        document_content = b"Test document content for deletion"
        document_key = f"documents/test_delete_{uuid.uuid4()}.pdf"
        
        # Store the document in S3
        s3_document_storage["store"](
            document_content=document_content,
            document_key=document_key,
            metadata={"document_id": str(uuid.uuid4())},
            bucket_type="staging"
        )
        
        # Verify that the document exists
        metadata, error = storage_service.get_document_metadata(document_key)
        assert error is None
        assert metadata is not None
        
        # Delete the document
        success, error = storage_service.delete_document(document_key)
        
        # Verify that the deletion was successful
        assert error is None
        assert success is True
        
        # Verify that the document no longer exists
        metadata, error = storage_service.get_document_metadata(document_key)
        assert metadata is None
        assert error is not None
        assert "not found" in error.lower() or "NoSuchKey" in error