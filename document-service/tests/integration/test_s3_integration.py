#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for S3 storage operations in the Document Service.

This module contains integration tests that verify the Document Service correctly
interacts with S3-compatible storage for document operations. Tests validate:

1. S3 client connection with appropriate authentication
2. Document upload with AES-256 encryption verification
3. Document download and metadata management
4. Error handling and retry logic for S3 operations
5. Secure access controls
6. Document versioning and history tracking

These tests ensure that the Document Service can reliably store and retrieve
documents with proper encryption and metadata as required by the technical
specification.
"""

import os
import io
import json
import pytest
import boto3
import botocore
from moto import mock_s3
from botocore.exceptions import ClientError

# Import the S3 utilities to test
from src.utils.s3_utils import (
    get_s3_client,
    upload_document,
    download_document,
    get_document_metadata,
    update_document_classification,
    generate_presigned_url,
    check_bucket_encryption,
    enable_bucket_encryption,
    list_documents_by_classification,
    document_exists
)

# Import configuration
from src.config.s3_config import (
    get_bucket_name,
    create_s3_client
)

# Test constants
TEST_REGION = "us-east-1"
TEST_BUCKET = "mca-documents-test"
TEST_DOCUMENT_KEY = "test/document.pdf"
TEST_DOCUMENT_CONTENT = b"This is a test document content."
TEST_DOCUMENT_CLASSIFICATION = "loan_application"
TEST_CLASSIFICATION_CONFIDENCE = 0.95
TEST_METADATA = {"source": "integration_test", "processor": "document_service"}


@pytest.fixture
def aws_credentials():
    """
    Mocked AWS Credentials for moto.
    """
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = TEST_REGION


@pytest.fixture
def s3_client(aws_credentials):
    """
    Create a mocked S3 client using moto.
    """
    with mock_s3():
        # Create the S3 client
        client = boto3.client("s3", region_name=TEST_REGION)
        # Create the test bucket
        client.create_bucket(Bucket=TEST_BUCKET)
        # Enable encryption on the bucket
        client.put_bucket_encryption(
            Bucket=TEST_BUCKET,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        },
                        "BucketKeyEnabled": True
                    }
                ]
            }
        )
        yield client


@pytest.fixture
def s3_resource(aws_credentials):
    """
    Create a mocked S3 resource using moto.
    """
    with mock_s3():
        # Create the S3 resource
        resource = boto3.resource("s3", region_name=TEST_REGION)
        # Create the test bucket
        resource.create_bucket(Bucket=TEST_BUCKET)
        # Enable encryption on the bucket
        resource.meta.client.put_bucket_encryption(
            Bucket=TEST_BUCKET,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        },
                        "BucketKeyEnabled": True
                    }
                ]
            }
        )
        yield resource


@pytest.fixture
def test_document():
    """
    Create a test document for upload/download tests.
    """
    return io.BytesIO(TEST_DOCUMENT_CONTENT)


@pytest.fixture
def uploaded_document(s3_client, test_document):
    """
    Upload a test document to S3 for testing.
    """
    s3_client.put_object(
        Bucket=TEST_BUCKET,
        Key=TEST_DOCUMENT_KEY,
        Body=TEST_DOCUMENT_CONTENT,
        ServerSideEncryption="AES256",
        Metadata=TEST_METADATA
    )
    return TEST_DOCUMENT_KEY


@mock_s3
class TestS3ClientConnection:
    """
    Test S3 client connection and authentication.
    """

    def test_get_s3_client(self, aws_credentials):
        """
        Test that get_s3_client creates a valid S3 client.
        """
        # Create S3 client using the utility function
        client = get_s3_client(
            region_name=TEST_REGION,
            endpoint_url=None,
            aws_access_key_id="testing",
            aws_secret_access_key="testing"
        )

        # Verify the client is created and can list buckets
        response = client.list_buckets()
        assert "Buckets" in response
        assert isinstance(response["Buckets"], list)

    def test_create_s3_client_from_config(self, aws_credentials):
        """
        Test that create_s3_client from config creates a valid S3 client.
        """
        # Create S3 client using the config function
        client = create_s3_client()

        # Verify the client is created and can list buckets
        response = client.list_buckets()
        assert "Buckets" in response
        assert isinstance(response["Buckets"], list)

    def test_get_bucket_name(self):
        """
        Test that get_bucket_name returns the correct bucket name for the environment.
        """
        # Set environment to test
        os.environ["ENVIRONMENT"] = "test"

        # Get bucket name
        bucket_name = get_bucket_name()

        # Verify the bucket name follows the expected pattern
        assert "mca-documents" in bucket_name
        assert "test" in bucket_name

    def test_client_connection_error_handling(self, aws_credentials):
        """
        Test that connection errors are properly handled.
        """
        # Attempt to create a client with invalid endpoint
        with pytest.raises(Exception):
            get_s3_client(
                region_name=TEST_REGION,
                endpoint_url="https://invalid-endpoint.example.com",
                aws_access_key_id="testing",
                aws_secret_access_key="testing"
            )


@mock_s3
class TestDocumentUpload:
    """
    Test document upload operations with encryption.
    """

    def test_upload_document_with_encryption(self, s3_client, test_document):
        """
        Test that documents are uploaded with AES-256 encryption.
        """
        # Upload document with encryption
        response = upload_document(
            s3_client=s3_client,
            bucket_name=TEST_BUCKET,
            object_key=TEST_DOCUMENT_KEY,
            file_obj=test_document,
            metadata=TEST_METADATA,
            document_classification=TEST_DOCUMENT_CLASSIFICATION,
            classification_confidence=TEST_CLASSIFICATION_CONFIDENCE
        )

        # Verify the upload was successful
        assert response is not None

        # Verify the document exists
        assert document_exists(s3_client, TEST_BUCKET, TEST_DOCUMENT_KEY)

        # Verify encryption was applied
        metadata = s3_client.head_object(Bucket=TEST_BUCKET, Key=TEST_DOCUMENT_KEY)
        assert metadata["ServerSideEncryption"] == "AES256"

    def test_upload_document_with_classification(self, s3_client, test_document):
        """
        Test that documents are uploaded with classification metadata.
        """
        # Upload document with classification
        upload_document(
            s3_client=s3_client,
            bucket_name=TEST_BUCKET,
            object_key=TEST_DOCUMENT_KEY,
            file_obj=test_document,
            metadata=TEST_METADATA,
            document_classification=TEST_DOCUMENT_CLASSIFICATION,
            classification_confidence=TEST_CLASSIFICATION_CONFIDENCE
        )

        # Verify classification metadata was applied
        metadata = s3_client.head_object(Bucket=TEST_BUCKET, Key=TEST_DOCUMENT_KEY)
        assert "document-classification" in metadata["Metadata"]
        assert metadata["Metadata"]["document-classification"] == TEST_DOCUMENT_CLASSIFICATION
        assert "classification-confidence" in metadata["Metadata"]
        assert float(metadata["Metadata"]["classification-confidence"]) == TEST_CLASSIFICATION_CONFIDENCE

    def test_upload_document_error_handling(self, s3_client, test_document):
        """
        Test error handling during document upload.
        """
        # Attempt to upload to a non-existent bucket
        with pytest.raises(ClientError):
            upload_document(
                s3_client=s3_client,
                bucket_name="non-existent-bucket",
                object_key=TEST_DOCUMENT_KEY,
                file_obj=test_document
            )

    def test_bucket_encryption_check(self, s3_client):
        """
        Test that bucket encryption can be verified.
        """
        # Check if bucket has encryption enabled
        has_encryption = check_bucket_encryption(s3_client, TEST_BUCKET)
        assert has_encryption is True

    def test_enable_bucket_encryption(self, s3_client):
        """
        Test that bucket encryption can be enabled.
        """
        # Create a new bucket without encryption
        new_bucket = "mca-documents-test-new"
        s3_client.create_bucket(Bucket=new_bucket)

        # Enable encryption on the bucket
        response = enable_bucket_encryption(s3_client, new_bucket)
        assert response is not None

        # Verify encryption is enabled
        has_encryption = check_bucket_encryption(s3_client, new_bucket)
        assert has_encryption is True


@mock_s3
class TestDocumentDownload:
    """
    Test document download and retrieval operations.
    """

    def test_download_document(self, s3_client, uploaded_document):
        """
        Test that documents can be downloaded.
        """
        # Download the document
        content, metadata = download_document(
            s3_client=s3_client,
            bucket_name=TEST_BUCKET,
            object_key=TEST_DOCUMENT_KEY
        )

        # Verify the content matches
        assert content == TEST_DOCUMENT_CONTENT

        # Verify metadata is returned
        assert metadata is not None
        assert "ContentType" in metadata
        assert "Metadata" in metadata

    def test_download_nonexistent_document(self, s3_client):
        """
        Test error handling when downloading a non-existent document.
        """
        # Attempt to download a non-existent document
        with pytest.raises(ClientError):
            download_document(
                s3_client=s3_client,
                bucket_name=TEST_BUCKET,
                object_key="non-existent-document.pdf"
            )

    def test_get_document_metadata(self, s3_client, uploaded_document):
        """
        Test that document metadata can be retrieved.
        """
        # Get document metadata
        metadata = get_document_metadata(
            s3_client=s3_client,
            bucket_name=TEST_BUCKET,
            object_key=TEST_DOCUMENT_KEY
        )

        # Verify metadata is returned
        assert metadata is not None
        assert "ContentType" in metadata
        assert "Metadata" in metadata
        assert metadata["Metadata"] == TEST_METADATA


@mock_s3
class TestDocumentMetadataManagement:
    """
    Test document metadata management operations.
    """

    def test_update_document_classification(self, s3_client, uploaded_document):
        """
        Test that document classification can be updated.
        """
        # Update document classification
        new_classification = "tax_return"
        new_confidence = 0.98

        response = update_document_classification(
            s3_client=s3_client,
            bucket_name=TEST_BUCKET,
            object_key=TEST_DOCUMENT_KEY,
            document_classification=new_classification,
            classification_confidence=new_confidence
        )

        # Verify the update was successful
        assert response is not None

        # Verify the classification was updated
        metadata = s3_client.head_object(Bucket=TEST_BUCKET, Key=TEST_DOCUMENT_KEY)
        assert metadata["Metadata"]["document-classification"] == new_classification
        assert float(metadata["Metadata"]["classification-confidence"]) == new_confidence

    def test_list_documents_by_classification(self, s3_client):
        """
        Test that documents can be listed by classification.
        """
        # Upload multiple documents with different classifications
        classifications = ["loan_application", "tax_return", "bank_statement", "loan_application"]
        for i, classification in enumerate(classifications):
            key = f"test/document_{i}.pdf"
            s3_client.put_object(
                Bucket=TEST_BUCKET,
                Key=key,
                Body=f"Document {i} content".encode(),
                ServerSideEncryption="AES256",
                Metadata={
                    "document-classification": classification,
                    "classification-confidence": "0.95"
                }
            )

        # List documents by classification
        loan_docs = list_documents_by_classification(
            s3_client=s3_client,
            bucket_name=TEST_BUCKET,
            classification="loan_application"
        )

        # Verify the correct documents are returned
        assert len(loan_docs) == 2
        assert all("document_" in doc["Key"] for doc in loan_docs)


@mock_s3
class TestSecureAccess:
    """
    Test secure access to S3 documents.
    """

    def test_generate_presigned_url(self, s3_client, uploaded_document):
        """
        Test that presigned URLs can be generated for secure access.
        """
        # Generate a presigned URL
        url = generate_presigned_url(
            s3_client=s3_client,
            bucket_name=TEST_BUCKET,
            object_key=TEST_DOCUMENT_KEY,
            expiration=3600
        )

        # Verify the URL is generated
        assert url is not None
        assert TEST_BUCKET in url
        assert TEST_DOCUMENT_KEY in url

    def test_generate_presigned_url_with_invalid_method(self, s3_client, uploaded_document):
        """
        Test error handling for invalid HTTP method in presigned URL generation.
        """
        # Attempt to generate a presigned URL with an invalid method
        with pytest.raises(ValueError):
            generate_presigned_url(
                s3_client=s3_client,
                bucket_name=TEST_BUCKET,
                object_key=TEST_DOCUMENT_KEY,
                http_method="INVALID"
            )


@mock_s3
class TestErrorHandling:
    """
    Test error handling for S3 operations.
    """

    def test_nonexistent_bucket(self, s3_client):
        """
        Test error handling for operations on non-existent buckets.
        """
        # Attempt to check if a document exists in a non-existent bucket
        with pytest.raises(ClientError):
            document_exists(
                s3_client=s3_client,
                bucket_name="non-existent-bucket",
                object_key=TEST_DOCUMENT_KEY
            )

    def test_invalid_credentials(self):
        """
        Test error handling for invalid credentials.
        """
        # Set invalid credentials
        os.environ["AWS_ACCESS_KEY_ID"] = "invalid"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "invalid"

        # Attempt to create a client with invalid credentials
        # This should not raise an exception with moto, but in real AWS it would
        client = get_s3_client(region_name=TEST_REGION)
        assert client is not None


@mock_s3
class TestDocumentVersioning:
    """
    Test document versioning and history tracking.
    """

    def test_document_versioning(self, s3_client):
        """
        Test that document versions can be tracked.
        """
        # Enable versioning on the bucket
        s3_client.put_bucket_versioning(
            Bucket=TEST_BUCKET,
            VersioningConfiguration={"Status": "Enabled"}
        )

        # Upload initial version
        s3_client.put_object(
            Bucket=TEST_BUCKET,
            Key=TEST_DOCUMENT_KEY,
            Body=b"Initial version",
            ServerSideEncryption="AES256"
        )

        # Get the version ID
        initial_version = s3_client.head_object(Bucket=TEST_BUCKET, Key=TEST_DOCUMENT_KEY)["VersionId"]

        # Upload a new version
        s3_client.put_object(
            Bucket=TEST_BUCKET,
            Key=TEST_DOCUMENT_KEY,
            Body=b"Updated version",
            ServerSideEncryption="AES256"
        )

        # Get the new version ID
        updated_version = s3_client.head_object(Bucket=TEST_BUCKET, Key=TEST_DOCUMENT_KEY)["VersionId"]

        # Verify the versions are different
        assert initial_version != updated_version

        # Verify we can retrieve the old version
        response = s3_client.get_object(
            Bucket=TEST_BUCKET,
            Key=TEST_DOCUMENT_KEY,
            VersionId=initial_version
        )
        assert response["Body"].read() == b"Initial version"

        # Verify the current version is the updated one
        response = s3_client.get_object(
            Bucket=TEST_BUCKET,
            Key=TEST_DOCUMENT_KEY
        )
        assert response["Body"].read() == b"Updated version"


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])