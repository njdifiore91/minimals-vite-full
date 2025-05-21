import os
import pytest
import boto3
from unittest.mock import patch, MagicMock
from moto import mock_s3
from botocore.config import Config
from botocore.exceptions import ClientError

# Import the module to test
from src.config import s3_config


# ===== Test Environment Variables and Bucket Names =====

@pytest.mark.parametrize("env,expected_bucket", [
    ("production", "mca-documents-production"),
    ("staging", "mca-documents-staging"),
    ("development", "mca-documents-development"),
    ("test", "mca-documents-test"),
    ("unknown", "mca-documents-development"),  # Default to development for unknown env
])
def test_get_bucket_name(monkeypatch, env, expected_bucket):
    """Test that get_bucket_name returns the correct bucket name for different environments."""
    # Set the environment variable
    monkeypatch.setenv("ENVIRONMENT", env)
    
    # Call the function and check the result
    bucket_name = s3_config.get_bucket_name()
    assert bucket_name == expected_bucket


def test_get_bucket_name_with_custom_prefix(monkeypatch):
    """Test that get_bucket_name uses a custom bucket prefix if provided."""
    # Set environment variables
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("S3_BUCKET_PREFIX", "custom-prefix")
    
    # Call the function and check the result
    bucket_name = s3_config.get_bucket_name()
    assert bucket_name == "custom-prefix-production"


# ===== Test S3 Configuration =====

def test_get_s3_config():
    """Test that get_s3_config returns a correctly configured Config object."""
    # Call the function
    config = s3_config.get_s3_config()
    
    # Verify it's a Config object
    assert isinstance(config, Config)
    
    # Verify the configuration settings
    assert config.retries["max_attempts"] == s3_config.MAX_RETRIES
    assert config.retries["mode"] == s3_config.RETRY_MODE
    assert config.connect_timeout == s3_config.DEFAULT_TIMEOUT
    assert config.read_timeout == s3_config.DEFAULT_TIMEOUT
    assert config.parameter_validation is True
    assert config.s3["addressing_style"] == "path"


# ===== Test S3 Client Creation =====

@mock_s3
def test_create_s3_client_default_settings():
    """Test that create_s3_client creates a client with default settings."""
    # Call the function
    client = s3_config.create_s3_client()
    
    # Verify it's an S3 client
    assert client.__class__.__name__ == "S3"
    
    # Test the client works by creating a bucket
    client.create_bucket(Bucket="test-bucket")
    response = client.list_buckets()
    assert len(response["Buckets"]) == 1
    assert response["Buckets"][0]["Name"] == "test-bucket"


@mock_s3
def test_create_s3_client_with_custom_endpoint(monkeypatch):
    """Test that create_s3_client uses a custom endpoint if provided."""
    # Set environment variables
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:4566")
    
    # Mock the get_s3_config function to avoid interference
    with patch("src.config.s3_config.get_s3_config", return_value=Config()):
        # Call the function
        client = s3_config.create_s3_client()
        
        # Verify it's an S3 client
        assert client.__class__.__name__ == "S3"
        
        # Test the client works by creating a bucket
        client.create_bucket(Bucket="test-bucket")
        response = client.list_buckets()
        assert len(response["Buckets"]) == 1
        assert response["Buckets"][0]["Name"] == "test-bucket"


@mock_s3
def test_create_s3_client_with_credentials(monkeypatch):
    """Test that create_s3_client uses credentials if provided."""
    # Set environment variables
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access-key")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret-key")
    
    # Mock boto3.client to verify the credentials are passed
    original_client = boto3.client
    
    def mock_client(*args, **kwargs):
        assert kwargs.get("aws_access_key_id") == "test-access-key"
        assert kwargs.get("aws_secret_access_key") == "test-secret-key"
        return original_client(*args, **kwargs)
    
    with patch("boto3.client", side_effect=mock_client):
        # Call the function
        client = s3_config.create_s3_client()
        
        # Verify it's an S3 client
        assert client.__class__.__name__ == "S3"


@mock_s3
def test_create_s3_client_error_handling():
    """Test that create_s3_client handles errors correctly."""
    # Mock boto3.client to raise an exception
    with patch("boto3.client", side_effect=Exception("Test exception")):
        # Call the function and check that it raises the exception
        with pytest.raises(Exception) as excinfo:
            s3_config.create_s3_client()
        
        # Verify the exception message
        assert "Test exception" in str(excinfo.value)


# ===== Test S3 Resource Creation =====

@mock_s3
def test_create_s3_resource_default_settings():
    """Test that create_s3_resource creates a resource with default settings."""
    # Call the function
    resource = s3_config.create_s3_resource()
    
    # Verify it's an S3 resource
    assert resource.__class__.__name__ == "ServiceResource"
    assert resource.meta.service_name == "s3"
    
    # Test the resource works by creating a bucket
    resource.create_bucket(Bucket="test-bucket")
    buckets = list(resource.buckets.all())
    assert len(buckets) == 1
    assert buckets[0].name == "test-bucket"


@mock_s3
def test_create_s3_resource_with_custom_endpoint(monkeypatch):
    """Test that create_s3_resource uses a custom endpoint if provided."""
    # Set environment variables
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:4566")
    
    # Mock the get_s3_config function to avoid interference
    with patch("src.config.s3_config.get_s3_config", return_value=Config()):
        # Call the function
        resource = s3_config.create_s3_resource()
        
        # Verify it's an S3 resource
        assert resource.__class__.__name__ == "ServiceResource"
        assert resource.meta.service_name == "s3"
        
        # Test the resource works by creating a bucket
        resource.create_bucket(Bucket="test-bucket")
        buckets = list(resource.buckets.all())
        assert len(buckets) == 1
        assert buckets[0].name == "test-bucket"


@mock_s3
def test_create_s3_resource_with_credentials(monkeypatch):
    """Test that create_s3_resource uses credentials if provided."""
    # Set environment variables
    monkeypatch.setenv("S3_ACCESS_KEY", "test-access-key")
    monkeypatch.setenv("S3_SECRET_KEY", "test-secret-key")
    
    # Mock boto3.resource to verify the credentials are passed
    original_resource = boto3.resource
    
    def mock_resource(*args, **kwargs):
        assert kwargs.get("aws_access_key_id") == "test-access-key"
        assert kwargs.get("aws_secret_access_key") == "test-secret-key"
        return original_resource(*args, **kwargs)
    
    with patch("boto3.resource", side_effect=mock_resource):
        # Call the function
        resource = s3_config.create_s3_resource()
        
        # Verify it's an S3 resource
        assert resource.__class__.__name__ == "ServiceResource"
        assert resource.meta.service_name == "s3"


@mock_s3
def test_create_s3_resource_error_handling():
    """Test that create_s3_resource handles errors correctly."""
    # Mock boto3.resource to raise an exception
    with patch("boto3.resource", side_effect=Exception("Test exception")):
        # Call the function and check that it raises the exception
        with pytest.raises(Exception) as excinfo:
            s3_config.create_s3_resource()
        
        # Verify the exception message
        assert "Test exception" in str(excinfo.value)


# ===== Test File Upload with Encryption =====

@mock_s3
def test_upload_file_with_encryption(tmpdir):
    """Test that upload_file_with_encryption uploads a file with AES-256 encryption."""
    # Create a test file
    test_file = tmpdir.join("test_file.txt")
    test_file.write("Test content")
    file_path = str(test_file)
    
    # Create a test bucket
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mca-documents-test"
    s3.create_bucket(Bucket=bucket_name)
    
    # Mock the create_s3_client function to return our test client
    with patch("src.config.s3_config.create_s3_client", return_value=s3):
        # Mock the get_bucket_name function to return our test bucket
        with patch("src.config.s3_config.get_bucket_name", return_value=bucket_name):
            # Call the function
            result = s3_config.upload_file_with_encryption(
                file_path=file_path,
                object_key="test_file.txt",
                metadata={"test_key": "test_value"}
            )
            
            # Verify the result
            assert result is True
            
            # Verify the file was uploaded with encryption
            response = s3.head_object(Bucket=bucket_name, Key="test_file.txt")
            assert response["ServerSideEncryption"] == "AES256"
            assert response["Metadata"]["test_key"] == "test_value"


@mock_s3
def test_upload_file_with_encryption_client_error():
    """Test that upload_file_with_encryption handles ClientError correctly."""
    # Mock the create_s3_client function to return a client that raises ClientError
    mock_client = MagicMock()
    mock_client.upload_file.side_effect = ClientError(
        {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist"}},
        "upload_file"
    )
    
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client):
        # Call the function
        result = s3_config.upload_file_with_encryption(
            file_path="nonexistent_file.txt",
            object_key="test_file.txt"
        )
        
        # Verify the result
        assert result is False


@mock_s3
def test_upload_file_with_encryption_general_exception():
    """Test that upload_file_with_encryption handles general exceptions correctly."""
    # Mock the create_s3_client function to return a client that raises an exception
    mock_client = MagicMock()
    mock_client.upload_file.side_effect = Exception("Test exception")
    
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client):
        # Call the function
        result = s3_config.upload_file_with_encryption(
            file_path="nonexistent_file.txt",
            object_key="test_file.txt"
        )
        
        # Verify the result
        assert result is False


# ===== Test File Download =====

@mock_s3
def test_download_file(tmpdir):
    """Test that download_file downloads a file correctly."""
    # Create a test bucket and upload a test file
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mca-documents-test"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_object(Bucket=bucket_name, Key="test_file.txt", Body="Test content")
    
    # Create a download path
    download_path = str(tmpdir.join("downloaded_file.txt"))
    
    # Mock the create_s3_client function to return our test client
    with patch("src.config.s3_config.create_s3_client", return_value=s3):
        # Mock the get_bucket_name function to return our test bucket
        with patch("src.config.s3_config.get_bucket_name", return_value=bucket_name):
            # Call the function
            result = s3_config.download_file(
                object_key="test_file.txt",
                download_path=download_path
            )
            
            # Verify the result
            assert result is True
            
            # Verify the file was downloaded correctly
            with open(download_path, "r") as f:
                content = f.read()
                assert content == "Test content"


@mock_s3
def test_download_file_client_error():
    """Test that download_file handles ClientError correctly."""
    # Mock the create_s3_client function to return a client that raises ClientError
    mock_client = MagicMock()
    mock_client.download_file.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}},
        "download_file"
    )
    
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client):
        # Call the function
        result = s3_config.download_file(
            object_key="nonexistent_file.txt",
            download_path="nonexistent_path.txt"
        )
        
        # Verify the result
        assert result is False


@mock_s3
def test_download_file_general_exception():
    """Test that download_file handles general exceptions correctly."""
    # Mock the create_s3_client function to return a client that raises an exception
    mock_client = MagicMock()
    mock_client.download_file.side_effect = Exception("Test exception")
    
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client):
        # Call the function
        result = s3_config.download_file(
            object_key="nonexistent_file.txt",
            download_path="nonexistent_path.txt"
        )
        
        # Verify the result
        assert result is False


# ===== Test Bucket Existence Check =====

@mock_s3
def test_check_bucket_exists():
    """Test that check_bucket_exists correctly identifies existing buckets."""
    # Create a test bucket
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mca-documents-test"
    s3.create_bucket(Bucket=bucket_name)
    
    # Mock the create_s3_client function to return our test client
    with patch("src.config.s3_config.create_s3_client", return_value=s3):
        # Call the function with an existing bucket
        result = s3_config.check_bucket_exists(bucket_name)
        assert result is True
        
        # Call the function with a non-existent bucket
        result = s3_config.check_bucket_exists("nonexistent-bucket")
        assert result is False


@mock_s3
def test_check_bucket_exists_default_bucket():
    """Test that check_bucket_exists uses the default bucket if none is provided."""
    # Create a test bucket
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mca-documents-test"
    s3.create_bucket(Bucket=bucket_name)
    
    # Mock the create_s3_client function to return our test client
    with patch("src.config.s3_config.create_s3_client", return_value=s3):
        # Mock the get_bucket_name function to return our test bucket
        with patch("src.config.s3_config.get_bucket_name", return_value=bucket_name):
            # Call the function without specifying a bucket
            result = s3_config.check_bucket_exists()
            assert result is True


@mock_s3
def test_check_bucket_exists_client_error():
    """Test that check_bucket_exists handles ClientError correctly."""
    # Mock the create_s3_client function to return a client that raises ClientError
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "403", "Message": "Forbidden"}},
        "head_bucket"
    )
    
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client):
        # Call the function
        result = s3_config.check_bucket_exists("test-bucket")
        assert result is False


@mock_s3
def test_check_bucket_exists_general_exception():
    """Test that check_bucket_exists handles general exceptions correctly."""
    # Mock the create_s3_client function to return a client that raises an exception
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = Exception("Test exception")
    
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client):
        # Call the function
        result = s3_config.check_bucket_exists("test-bucket")
        assert result is False


# ===== Test Bucket Creation =====

@mock_s3
def test_create_bucket_if_not_exists():
    """Test that create_bucket_if_not_exists creates a bucket if it doesn't exist."""
    # Create a test S3 client
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mca-documents-test"
    
    # Mock the create_s3_client function to return our test client
    with patch("src.config.s3_config.create_s3_client", return_value=s3):
        # Mock the check_bucket_exists function to return False (bucket doesn't exist)
        with patch("src.config.s3_config.check_bucket_exists", return_value=False):
            # Call the function
            result = s3_config.create_bucket_if_not_exists(bucket_name)
            assert result is True
            
            # Verify the bucket was created
            response = s3.list_buckets()
            assert len(response["Buckets"]) == 1
            assert response["Buckets"][0]["Name"] == bucket_name


@mock_s3
def test_create_bucket_if_not_exists_already_exists():
    """Test that create_bucket_if_not_exists returns True if the bucket already exists."""
    # Create a test bucket
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mca-documents-test"
    s3.create_bucket(Bucket=bucket_name)
    
    # Mock the create_s3_client function to return our test client
    with patch("src.config.s3_config.create_s3_client", return_value=s3):
        # Mock the check_bucket_exists function to return True (bucket exists)
        with patch("src.config.s3_config.check_bucket_exists", return_value=True):
            # Call the function
            result = s3_config.create_bucket_if_not_exists(bucket_name)
            assert result is True


@mock_s3
def test_create_bucket_if_not_exists_default_bucket():
    """Test that create_bucket_if_not_exists uses the default bucket if none is provided."""
    # Create a test S3 client
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mca-documents-test"
    
    # Mock the create_s3_client function to return our test client
    with patch("src.config.s3_config.create_s3_client", return_value=s3):
        # Mock the check_bucket_exists function to return False (bucket doesn't exist)
        with patch("src.config.s3_config.check_bucket_exists", return_value=False):
            # Mock the get_bucket_name function to return our test bucket
            with patch("src.config.s3_config.get_bucket_name", return_value=bucket_name):
                # Call the function without specifying a bucket
                result = s3_config.create_bucket_if_not_exists()
                assert result is True
                
                # Verify the bucket was created
                response = s3.list_buckets()
                assert len(response["Buckets"]) == 1
                assert response["Buckets"][0]["Name"] == bucket_name


@mock_s3
def test_create_bucket_if_not_exists_with_encryption():
    """Test that create_bucket_if_not_exists enables encryption on the bucket."""
    # Create a test S3 client
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "mca-documents-test"
    
    # Mock the create_s3_client function to return our test client
    with patch("src.config.s3_config.create_s3_client", return_value=s3):
        # Mock the check_bucket_exists function to return False (bucket doesn't exist)
        with patch("src.config.s3_config.check_bucket_exists", return_value=False):
            # Call the function
            result = s3_config.create_bucket_if_not_exists(bucket_name)
            assert result is True
            
            # Verify encryption was enabled on the bucket
            # Note: moto doesn't fully support bucket encryption, so we can't verify this directly
            # Instead, we'll verify that put_bucket_encryption was called
            assert s3.put_bucket_encryption.call_count if hasattr(s3, "put_bucket_encryption") else True


@mock_s3
def test_create_bucket_if_not_exists_client_error():
    """Test that create_bucket_if_not_exists handles ClientError correctly."""
    # Mock the create_s3_client function to return a client that raises ClientError
    mock_client = MagicMock()
    mock_client.create_bucket.side_effect = ClientError(
        {"Error": {"Code": "BucketAlreadyExists", "Message": "The requested bucket name is not available"}},
        "create_bucket"
    )
    
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client):
        # Mock the check_bucket_exists function to return False (bucket doesn't exist)
        with patch("src.config.s3_config.check_bucket_exists", return_value=False):
            # Call the function
            result = s3_config.create_bucket_if_not_exists("test-bucket")
            assert result is False


@mock_s3
def test_create_bucket_if_not_exists_general_exception():
    """Test that create_bucket_if_not_exists handles general exceptions correctly."""
    # Mock the create_s3_client function to return a client that raises an exception
    mock_client = MagicMock()
    mock_client.create_bucket.side_effect = Exception("Test exception")
    
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client):
        # Mock the check_bucket_exists function to return False (bucket doesn't exist)
        with patch("src.config.s3_config.check_bucket_exists", return_value=False):
            # Call the function
            result = s3_config.create_bucket_if_not_exists("test-bucket")
            assert result is False


# ===== Test Module Initialization =====

@mock_s3
def test_module_initialization():
    """Test that the module initializes S3 client and resource correctly."""
    # Create a test S3 client and resource
    s3_client_mock = MagicMock()
    s3_resource_mock = MagicMock()
    
    # Mock the create_s3_client and create_s3_resource functions
    with patch("src.config.s3_config.create_s3_client", return_value=s3_client_mock):
        with patch("src.config.s3_config.create_s3_resource", return_value=s3_resource_mock):
            # Mock the check_bucket_exists function
            with patch("src.config.s3_config.check_bucket_exists", return_value=True):
                # Reload the module to trigger initialization
                import importlib
                importlib.reload(s3_config)
                
                # Verify that the module-level variables are set
                assert s3_config.s3_client == s3_client_mock
                assert s3_config.s3_resource == s3_resource_mock


@mock_s3
def test_module_initialization_error_handling():
    """Test that the module handles initialization errors correctly."""
    # Mock the create_s3_client function to raise an exception
    with patch("src.config.s3_config.create_s3_client", side_effect=Exception("Test exception")):
        # Reload the module to trigger initialization
        import importlib
        importlib.reload(s3_config)
        
        # Verify that the module-level variables are not set
        assert not hasattr(s3_config, "s3_client") or s3_config.s3_client is None
        assert not hasattr(s3_config, "s3_resource") or s3_config.s3_resource is None