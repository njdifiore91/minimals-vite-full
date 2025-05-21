#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pytest configuration file for Document Service type tests.

This module provides fixtures, mocks, and utilities for testing the type definitions
in the Document Service. It centralizes test setup and teardown logic to ensure
consistent test environments across all type test modules.
"""

import os
import json
import uuid
import datetime
import tempfile
from typing import Dict, List, Any, Optional, Type, TypeVar, Generic, Union, Callable
from enum import Enum
from dataclasses import dataclass, field

import pytest
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier

# Type variable for generic fixtures
T = TypeVar('T')


# ===== Error Type Fixtures =====

@pytest.fixture
def error_category_enum():
    """Fixture providing the ErrorCategory enum for testing."""
    class ErrorCategory(Enum):
        VALIDATION = "validation"
        PROCESSING = "processing"
        STORAGE = "storage"
        MESSAGING = "messaging"
        CONFIGURATION = "configuration"
        AUTHENTICATION = "authentication"
        AUTHORIZATION = "authorization"
        EXTERNAL = "external"
        UNKNOWN = "unknown"
        
    return ErrorCategory


@pytest.fixture
def error_details_factory():
    """Factory fixture for creating ErrorDetails instances."""
    @dataclass
    class ErrorDetails:
        message: str
        code: str
        category: str
        timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
        context: Dict[str, Any] = field(default_factory=dict)
        stack_trace: Optional[str] = None
        
    def _create_error_details(message="Test error", code="TEST_ERROR", 
                             category="unknown", context=None, stack_trace=None):
        return ErrorDetails(
            message=message,
            code=code,
            category=category,
            timestamp=datetime.datetime.now(),
            context=context or {},
            stack_trace=stack_trace
        )
        
    return _create_error_details


@pytest.fixture
def service_error_factory(error_details_factory):
    """Factory fixture for creating ServiceError instances."""
    class ServiceError(Exception):
        def __init__(self, details):
            self.details = details
            super().__init__(details.message)
            
    def _create_service_error(message="Test error", code="TEST_ERROR", 
                             category="unknown", context=None, stack_trace=None):
        details = error_details_factory(message, code, category, context, stack_trace)
        return ServiceError(details)
        
    return _create_service_error


@pytest.fixture
def log_entry_factory():
    """Factory fixture for creating LogEntry instances."""
    @dataclass
    class LogEntry:
        level: str
        message: str
        timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
        service: str = "document-service"
        context: Dict[str, Any] = field(default_factory=dict)
        
    def _create_log_entry(level="INFO", message="Test log message", context=None):
        return LogEntry(
            level=level,
            message=message,
            timestamp=datetime.datetime.now(),
            service="document-service",
            context=context or {}
        )
        
    return _create_log_entry


@pytest.fixture
def monitoring_alert_factory():
    """Factory fixture for creating MonitoringAlert instances."""
    @dataclass
    class MonitoringAlert:
        severity: str
        message: str
        source: str
        timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
        details: Dict[str, Any] = field(default_factory=dict)
        
    def _create_monitoring_alert(severity="critical", message="Test alert", 
                                source="document-service", details=None):
        return MonitoringAlert(
            severity=severity,
            message=message,
            source=source,
            timestamp=datetime.datetime.now(),
            details=details or {}
        )
        
    return _create_monitoring_alert


@pytest.fixture
def result_factory():
    """Factory fixture for creating Result instances."""
    @dataclass
    class Result(Generic[T]):
        value: Optional[T] = None
        error: Optional[Any] = None
        success: bool = True
        
        @classmethod
        def ok(cls, value: T) -> 'Result[T]':
            return cls(value=value, success=True)
            
        @classmethod
        def fail(cls, error: Any) -> 'Result[T]':
            return cls(error=error, success=False)
            
    return Result


# ===== Classification Type Fixtures =====

@pytest.fixture
def mock_classifier():
    """Fixture providing a mock scikit-learn classifier for testing."""
    class MockClassifier(BaseEstimator, ClassifierMixin):
        def __init__(self, **kwargs):
            self.classes_ = ["APPLICATION", "TAX_RETURN", "BANK_STATEMENT", "PAY_STUB", "ID_DOCUMENT", "OTHER"]
            self.n_classes_ = len(self.classes_)
            self.params = kwargs
            
        def fit(self, X, y):
            return self
            
        def predict(self, X):
            if isinstance(X, list):
                return [self.classes_[0]] * len(X)
            return np.array([self.classes_[0]])
            
        def predict_proba(self, X):
            if isinstance(X, list):
                return np.array([[0.8, 0.05, 0.05, 0.05, 0.03, 0.02]] * len(X))
            return np.array([[0.8, 0.05, 0.05, 0.05, 0.03, 0.02]])
            
    return MockClassifier()


@pytest.fixture
def feature_vector_factory():
    """Factory fixture for creating FeatureVector instances."""
    def _create_feature_vector(n_features=10):
        return np.random.rand(n_features)
        
    return _create_feature_vector


@pytest.fixture
def classification_result_factory():
    """Factory fixture for creating ClassificationResult instances."""
    @dataclass
    class ClassificationResult:
        document_type: str
        confidence: float
        probabilities: Dict[str, float]
        processing_time: float
        model_version: str
        
    def _create_classification_result(document_type="APPLICATION", confidence=0.85):
        probabilities = {
            "APPLICATION": 0.85,
            "TAX_RETURN": 0.05,
            "BANK_STATEMENT": 0.04,
            "PAY_STUB": 0.03,
            "ID_DOCUMENT": 0.02,
            "OTHER": 0.01
        }
        
        return ClassificationResult(
            document_type=document_type,
            confidence=confidence,
            probabilities=probabilities,
            processing_time=0.0123,
            model_version="1.0.0"
        )
        
    return _create_classification_result


@pytest.fixture
def model_parameters_factory():
    """Factory fixture for creating ModelParameters instances."""
    @dataclass
    class ModelParameters:
        algorithm: str
        hyperparameters: Dict[str, Any]
        feature_extraction: Dict[str, Any]
        version: str
        
    def _create_model_parameters(algorithm="random_forest"):
        if algorithm == "random_forest":
            hyperparameters = {
                "n_estimators": 100,
                "max_depth": 10,
                "min_samples_split": 2,
                "min_samples_leaf": 1
            }
        elif algorithm == "svm":
            hyperparameters = {
                "C": 1.0,
                "kernel": "rbf",
                "gamma": "scale"
            }
        else:
            hyperparameters = {}
            
        feature_extraction = {
            "method": "tfidf",
            "max_features": 5000,
            "ngram_range": (1, 2)
        }
        
        return ModelParameters(
            algorithm=algorithm,
            hyperparameters=hyperparameters,
            feature_extraction=feature_extraction,
            version="1.0.0"
        )
        
    return _create_model_parameters


@pytest.fixture
def classification_metrics_factory():
    """Factory fixture for creating ClassificationMetrics instances."""
    @dataclass
    class ClassificationMetrics:
        accuracy: float
        precision: Dict[str, float]
        recall: Dict[str, float]
        f1_score: Dict[str, float]
        confusion_matrix: List[List[int]]
        support: Dict[str, int]
        
    def _create_classification_metrics(accuracy=0.95):
        classes = ["APPLICATION", "TAX_RETURN", "BANK_STATEMENT", "PAY_STUB", "ID_DOCUMENT", "OTHER"]
        metrics = {cls: 0.95 for cls in classes}
        support = {cls: 100 for cls in classes}
        
        # Simple confusion matrix for testing
        n_classes = len(classes)
        confusion_matrix = [[0 for _ in range(n_classes)] for _ in range(n_classes)]
        for i in range(n_classes):
            confusion_matrix[i][i] = 95  # 95% correct on diagonal
            for j in range(n_classes):
                if i != j:
                    confusion_matrix[i][j] = 1  # 1% error for each other class
        
        return ClassificationMetrics(
            accuracy=accuracy,
            precision=metrics,
            recall=metrics,
            f1_score=metrics,
            confusion_matrix=confusion_matrix,
            support=support
        )
        
    return _create_classification_metrics


# ===== Storage Type Fixtures =====

@pytest.fixture
def s3_client_config_factory():
    """Factory fixture for creating S3ClientConfig instances."""
    @dataclass
    class S3ClientConfig:
        endpoint_url: str
        region_name: str
        bucket_name: str
        access_key_id: Optional[str] = None
        secret_access_key: Optional[str] = None
        use_ssl: bool = True
        
    def _create_s3_client_config(environment="test"):
        if environment == "test":
            return S3ClientConfig(
                endpoint_url="http://localhost:4566",
                region_name="us-east-1",
                bucket_name="mca-documents-test",
                access_key_id="test",
                secret_access_key="test",
                use_ssl=False
            )
        elif environment == "staging":
            return S3ClientConfig(
                endpoint_url="https://s3.amazonaws.com",
                region_name="us-east-1",
                bucket_name="mca-documents-staging",
                use_ssl=True
            )
        elif environment == "production":
            return S3ClientConfig(
                endpoint_url="https://s3.amazonaws.com",
                region_name="us-east-1",
                bucket_name="mca-documents-production",
                use_ssl=True
            )
        else:
            raise ValueError(f"Unknown environment: {environment}")
        
    return _create_s3_client_config


@pytest.fixture
def storage_options_factory():
    """Factory fixture for creating StorageOptions instances."""
    @dataclass
    class StorageOptions:
        encryption: Dict[str, Any]
        content_type: str
        metadata: Dict[str, str]
        acl: str = "private"
        
    def _create_storage_options(content_type="application/pdf"):
        return StorageOptions(
            encryption={
                "algorithm": "AES256",
                "kms_key_id": None
            },
            content_type=content_type,
            metadata={
                "source": "document-service",
                "classification": "automatic"
            },
            acl="private"
        )
        
    return _create_storage_options


@pytest.fixture
def storage_metadata_factory():
    """Factory fixture for creating StorageMetadata instances."""
    @dataclass
    class StorageMetadata:
        key: str
        bucket: str
        size: int
        etag: str
        last_modified: datetime.datetime
        content_type: str
        metadata: Dict[str, str]
        
    def _create_storage_metadata(key=None, bucket="mca-documents-test", content_type="application/pdf"):
        if key is None:
            key = f"documents/{uuid.uuid4()}.pdf"
            
        return StorageMetadata(
            key=key,
            bucket=bucket,
            size=1024,
            etag="test-etag",
            last_modified=datetime.datetime.now(),
            content_type=content_type,
            metadata={
                "source": "document-service",
                "classification": "automatic",
                "document_type": "APPLICATION"
            }
        )
        
    return _create_storage_metadata


@pytest.fixture
def bucket_config_factory():
    """Factory fixture for creating BucketConfig instances."""
    @dataclass
    class BucketConfig:
        name: str
        region: str
        encryption: Dict[str, Any]
        versioning: bool
        lifecycle_rules: List[Dict[str, Any]]
        
    def _create_bucket_config(environment="test"):
        if environment == "test":
            name = "mca-documents-test"
        elif environment == "staging":
            name = "mca-documents-staging"
        elif environment == "production":
            name = "mca-documents-production"
        else:
            raise ValueError(f"Unknown environment: {environment}")
            
        return BucketConfig(
            name=name,
            region="us-east-1",
            encryption={
                "algorithm": "AES256",
                "kms_key_id": None
            },
            versioning=True,
            lifecycle_rules=[
                {
                    "id": "archive-rule",
                    "status": "Enabled",
                    "transition": {
                        "days": 90,
                        "storage_class": "GLACIER"
                    }
                }
            ]
        )
        
    return _create_bucket_config


@pytest.fixture
def storage_result_factory(result_factory):
    """Factory fixture for creating StorageResult instances."""
    StorageResult = result_factory
    
    def _create_storage_result(success=True, value=None, error=None):
        if success:
            return StorageResult.ok(value or {"key": f"documents/{uuid.uuid4()}.pdf"})
        else:
            return StorageResult.fail(error or "Storage operation failed")
        
    return _create_storage_result


@pytest.fixture
def storage_key_factory():
    """Factory fixture for creating storage keys."""
    def _create_storage_key(document_type="APPLICATION", file_extension="pdf"):
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        unique_id = str(uuid.uuid4())
        return f"documents/{document_type.lower()}/{timestamp}-{unique_id}.{file_extension}"
        
    return _create_storage_key


# ===== Document Type Fixtures =====

@pytest.fixture
def document_type_enum():
    """Fixture providing the DocumentType enum for testing."""
    class DocumentType(Enum):
        APPLICATION = "APPLICATION"
        TAX_RETURN = "TAX_RETURN"
        BANK_STATEMENT = "BANK_STATEMENT"
        PAY_STUB = "PAY_STUB"
        ID_DOCUMENT = "ID_DOCUMENT"
        OTHER = "OTHER"
        
    return DocumentType


@pytest.fixture
def processing_status_enum():
    """Fixture providing the ProcessingStatus enum for testing."""
    class ProcessingStatus(Enum):
        RECEIVED = "RECEIVED"
        CLASSIFYING = "CLASSIFYING"
        CLASSIFIED = "CLASSIFIED"
        EXTRACTING = "EXTRACTING"
        EXTRACTED = "EXTRACTED"
        FAILED = "FAILED"
        COMPLETED = "COMPLETED"
        
    return ProcessingStatus


@pytest.fixture
def document_metadata_factory():
    """Factory fixture for creating DocumentMetadata instances."""
    @dataclass
    class DocumentMetadata:
        filename: str
        content_type: str
        size: int
        created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
        checksum: Optional[str] = None
        page_count: Optional[int] = None
        additional_metadata: Dict[str, Any] = field(default_factory=dict)
        
    def _create_document_metadata(filename=None, content_type="application/pdf", size=1024):
        if filename is None:
            filename = f"document-{uuid.uuid4()}.pdf"
            
        return DocumentMetadata(
            filename=filename,
            content_type=content_type,
            size=size,
            created_at=datetime.datetime.now(),
            checksum="sha256:1234567890abcdef",
            page_count=5,
            additional_metadata={}
        )
        
    return _create_document_metadata


@pytest.fixture
def document_content_factory():
    """Factory fixture for creating DocumentContent instances."""
    @dataclass
    class DocumentContent:
        data: bytes
        content_type: str
        
    def _create_document_content(content_type="application/pdf"):
        # Create dummy PDF-like content for testing
        if content_type == "application/pdf":
            data = b"%PDF-1.5\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
        elif content_type.startswith("image/"):
            data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n\x86\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        else:
            data = b"Test document content"
            
        return DocumentContent(
            data=data,
            content_type=content_type
        )
        
    return _create_document_content


@pytest.fixture
def document_source_factory():
    """Factory fixture for creating DocumentSource instances."""
    @dataclass
    class DocumentSource:
        source_type: str
        source_id: str
        received_at: datetime.datetime
        metadata: Dict[str, Any] = field(default_factory=dict)
        
    def _create_document_source(source_type="email"):
        source_id = f"{source_type}-{uuid.uuid4()}"
        
        metadata = {}
        if source_type == "email":
            metadata = {
                "from": "sender@example.com",
                "subject": "Application Documents",
                "received_date": datetime.datetime.now().isoformat()
            }
        elif source_type == "api":
            metadata = {
                "user_id": "user-123",
                "api_key": "api-key-456",
                "ip_address": "192.168.1.1"
            }
            
        return DocumentSource(
            source_type=source_type,
            source_id=source_id,
            received_at=datetime.datetime.now(),
            metadata=metadata
        )
        
    return _create_document_source


@pytest.fixture
def document_factory(document_metadata_factory, document_content_factory, 
                    document_source_factory, document_type_enum, processing_status_enum):
    """Factory fixture for creating Document instances."""
    @dataclass
    class Document:
        id: str
        metadata: Any  # DocumentMetadata
        content: Any  # DocumentContent
        source: Any  # DocumentSource
        document_type: Optional[str] = None
        confidence_score: Optional[float] = None
        status: str = field(default_factory=lambda: processing_status_enum.RECEIVED.value)
        created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
        updated_at: datetime.datetime = field(default_factory=datetime.datetime.now)
        storage_location: Optional[str] = None
        
    def _create_document(document_type=None, status="RECEIVED", with_content=True):
        doc_id = str(uuid.uuid4())
        metadata = document_metadata_factory()
        content = document_content_factory() if with_content else None
        source = document_source_factory()
        
        return Document(
            id=doc_id,
            metadata=metadata,
            content=content,
            source=source,
            document_type=document_type,
            confidence_score=0.95 if document_type else None,
            status=status,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            storage_location=f"documents/{doc_id}.pdf" if with_content else None
        )
        
    return _create_document


# ===== Message Type Fixtures =====

@pytest.fixture
def message_headers_factory():
    """Factory fixture for creating MessageHeaders instances."""
    @dataclass
    class MessageHeaders:
        message_id: str
        timestamp: str
        content_type: str
        correlation_id: Optional[str] = None
        reply_to: Optional[str] = None
        additional_headers: Dict[str, str] = field(default_factory=dict)
        
    def _create_message_headers(content_type="application/json"):
        return MessageHeaders(
            message_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now().isoformat(),
            content_type=content_type,
            correlation_id=str(uuid.uuid4()),
            reply_to=None,
            additional_headers={}
        )
        
    return _create_message_headers


@pytest.fixture
def message_payload_factory():
    """Factory fixture for creating MessagePayload instances."""
    @dataclass
    class MessagePayload:
        document_id: str
        action: str
        data: Dict[str, Any]
        version: str = "1.0"
        
    def _create_message_payload(action="classify"):
        data = {}
        
        if action == "classify":
            data = {
                "document_metadata": {
                    "filename": f"document-{uuid.uuid4()}.pdf",
                    "content_type": "application/pdf",
                    "size": 1024,
                    "created_at": datetime.datetime.now().isoformat()
                },
                "storage_location": f"documents/{uuid.uuid4()}.pdf"
            }
        elif action == "classification_result":
            data = {
                "document_type": "APPLICATION",
                "confidence_score": 0.95,
                "processing_time": 0.123,
                "model_version": "1.0.0"
            }
            
        return MessagePayload(
            document_id=str(uuid.uuid4()),
            action=action,
            data=data,
            version="1.0"
        )
        
    return _create_message_payload


@pytest.fixture
def exchange_config_factory():
    """Factory fixture for creating ExchangeConfig instances."""
    @dataclass
    class ExchangeConfig:
        name: str
        type: str
        durable: bool = True
        auto_delete: bool = False
        arguments: Dict[str, Any] = field(default_factory=dict)
        
    def _create_exchange_config(name="mca.documents", exchange_type="fanout"):
        return ExchangeConfig(
            name=name,
            type=exchange_type,
            durable=True,
            auto_delete=False,
            arguments={}
        )
        
    return _create_exchange_config


@pytest.fixture
def queue_config_factory():
    """Factory fixture for creating QueueConfig instances."""
    @dataclass
    class QueueConfig:
        name: str
        durable: bool = True
        exclusive: bool = False
        auto_delete: bool = False
        arguments: Dict[str, Any] = field(default_factory=dict)
        
    def _create_queue_config(name="document-processing"):
        return QueueConfig(
            name=name,
            durable=True,
            exclusive=False,
            auto_delete=False,
            arguments={
                "x-message-ttl": 86400000,  # 24 hours
                "x-dead-letter-exchange": "mca.dead-letter"
            }
        )
        
    return _create_queue_config


@pytest.fixture
def publish_options_factory():
    """Factory fixture for creating PublishOptions instances."""
    @dataclass
    class PublishOptions:
        content_type: str = "application/json"
        content_encoding: Optional[str] = None
        delivery_mode: int = 2  # Persistent
        priority: Optional[int] = None
        correlation_id: Optional[str] = None
        reply_to: Optional[str] = None
        expiration: Optional[str] = None
        message_id: Optional[str] = None
        timestamp: Optional[int] = None
        user_id: Optional[str] = None
        app_id: Optional[str] = None
        headers: Dict[str, str] = field(default_factory=dict)
        
    def _create_publish_options(content_type="application/json"):
        return PublishOptions(
            content_type=content_type,
            content_encoding=None,
            delivery_mode=2,  # Persistent
            priority=None,
            correlation_id=str(uuid.uuid4()),
            reply_to=None,
            expiration=None,
            message_id=str(uuid.uuid4()),
            timestamp=int(datetime.datetime.now().timestamp()),
            user_id=None,
            app_id="document-service",
            headers={}
        )
        
    return _create_publish_options


@pytest.fixture
def consume_options_factory():
    """Factory fixture for creating ConsumeOptions instances."""
    @dataclass
    class ConsumeOptions:
        queue: str
        consumer_tag: Optional[str] = None
        no_local: bool = False
        no_ack: bool = False
        exclusive: bool = False
        arguments: Dict[str, Any] = field(default_factory=dict)
        
    def _create_consume_options(queue="document-processing"):
        return ConsumeOptions(
            queue=queue,
            consumer_tag=f"consumer-{uuid.uuid4()}",
            no_local=False,
            no_ack=False,
            exclusive=False,
            arguments={}
        )
        
    return _create_consume_options


# ===== Config Type Fixtures =====

@pytest.fixture
def config_dict_factory():
    """Factory fixture for creating ConfigDict instances."""
    def _create_config_dict(config_type="service"):
        if config_type == "service":
            return {
                "name": "document-service",
                "version": "1.0.0",
                "port": 8080,
                "host": "0.0.0.0",
                "log_level": "INFO"
            }
        elif config_type == "model":
            return {
                "algorithm": "random_forest",
                "model_path": "/app/models/document_classifier.pkl",
                "feature_extraction": {
                    "method": "tfidf",
                    "max_features": 5000,
                    "ngram_range": [1, 2]
                },
                "confidence_threshold": 0.8
            }
        elif config_type == "rabbitmq":
            return {
                "host": "rabbitmq",
                "port": 5672,
                "username": "guest",
                "password": "guest",
                "virtual_host": "/",
                "exchange": "mca.documents",
                "queue": "document-processing",
                "routing_key": ""
            }
        elif config_type == "s3":
            return {
                "endpoint_url": "http://localhost:4566",
                "region_name": "us-east-1",
                "bucket_name": "mca-documents-test",
                "access_key_id": "test",
                "secret_access_key": "test",
                "use_ssl": False
            }
        else:
            return {}
        
    return _create_config_dict


@pytest.fixture
def service_config_factory(config_dict_factory):
    """Factory fixture for creating ServiceConfig instances."""
    @dataclass
    class ServiceConfig:
        name: str
        version: str
        port: int
        host: str
        log_level: str
        
        @classmethod
        def from_dict(cls, config_dict):
            return cls(
                name=config_dict.get("name", "document-service"),
                version=config_dict.get("version", "1.0.0"),
                port=config_dict.get("port", 8080),
                host=config_dict.get("host", "0.0.0.0"),
                log_level=config_dict.get("log_level", "INFO")
            )
        
    def _create_service_config():
        config_dict = config_dict_factory("service")
        return ServiceConfig.from_dict(config_dict)
        
    return _create_service_config


@pytest.fixture
def model_config_factory(config_dict_factory):
    """Factory fixture for creating ModelConfig instances."""
    @dataclass
    class ModelConfig:
        algorithm: str
        model_path: str
        feature_extraction: Dict[str, Any]
        confidence_threshold: float
        
        @classmethod
        def from_dict(cls, config_dict):
            return cls(
                algorithm=config_dict.get("algorithm", "random_forest"),
                model_path=config_dict.get("model_path", "/app/models/document_classifier.pkl"),
                feature_extraction=config_dict.get("feature_extraction", {}),
                confidence_threshold=config_dict.get("confidence_threshold", 0.8)
            )
        
    def _create_model_config():
        config_dict = config_dict_factory("model")
        return ModelConfig.from_dict(config_dict)
        
    return _create_model_config


@pytest.fixture
def rabbitmq_config_factory(config_dict_factory):
    """Factory fixture for creating RabbitMQConfig instances."""
    @dataclass
    class RabbitMQConfig:
        host: str
        port: int
        username: str
        password: str
        virtual_host: str
        exchange: str
        queue: str
        routing_key: str
        
        @classmethod
        def from_dict(cls, config_dict):
            return cls(
                host=config_dict.get("host", "rabbitmq"),
                port=config_dict.get("port", 5672),
                username=config_dict.get("username", "guest"),
                password=config_dict.get("password", "guest"),
                virtual_host=config_dict.get("virtual_host", "/"),
                exchange=config_dict.get("exchange", "mca.documents"),
                queue=config_dict.get("queue", "document-processing"),
                routing_key=config_dict.get("routing_key", "")
            )
        
    def _create_rabbitmq_config():
        config_dict = config_dict_factory("rabbitmq")
        return RabbitMQConfig.from_dict(config_dict)
        
    return _create_rabbitmq_config


@pytest.fixture
def s3_config_factory(config_dict_factory):
    """Factory fixture for creating S3Config instances."""
    @dataclass
    class S3Config:
        endpoint_url: str
        region_name: str
        bucket_name: str
        access_key_id: Optional[str]
        secret_access_key: Optional[str]
        use_ssl: bool
        
        @classmethod
        def from_dict(cls, config_dict):
            return cls(
                endpoint_url=config_dict.get("endpoint_url", "http://localhost:4566"),
                region_name=config_dict.get("region_name", "us-east-1"),
                bucket_name=config_dict.get("bucket_name", "mca-documents-test"),
                access_key_id=config_dict.get("access_key_id"),
                secret_access_key=config_dict.get("secret_access_key"),
                use_ssl=config_dict.get("use_ssl", False)
            )
        
    def _create_s3_config():
        config_dict = config_dict_factory("s3")
        return S3Config.from_dict(config_dict)
        
    return _create_s3_config


@pytest.fixture
def logging_config_factory():
    """Factory fixture for creating LoggingConfig instances."""
    @dataclass
    class LoggingConfig:
        level: str
        format: str
        handlers: List[Dict[str, Any]]
        
    def _create_logging_config(level="INFO"):
        return LoggingConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                {
                    "type": "console",
                    "level": level
                },
                {
                    "type": "file",
                    "filename": "document-service.log",
                    "level": level
                }
            ]
        )
        
    return _create_logging_config


# ===== Utility Fixtures =====

@pytest.fixture
def temp_file():
    """Fixture providing a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        yield tmp.name
    # Cleanup after test
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


@pytest.fixture
def temp_pdf_file():
    """Fixture providing a temporary PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        # Write minimal PDF-like content
        tmp.write(b"%PDF-1.5\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n")
        yield tmp.name
    # Cleanup after test
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


@pytest.fixture
def temp_json_file():
    """Fixture providing a temporary JSON file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        # Write sample JSON content
        sample_data = {
            "document_type": "APPLICATION",
            "confidence": 0.95,
            "metadata": {
                "filename": "test.pdf",
                "size": 1024,
                "content_type": "application/pdf"
            }
        }
        tmp.write(json.dumps(sample_data).encode('utf-8'))
        yield tmp.name
    # Cleanup after test
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


@pytest.fixture
def assert_valid_uuid():
    """Fixture providing a function to assert that a string is a valid UUID."""
    def _assert_valid_uuid(uuid_str):
        try:
            uuid_obj = uuid.UUID(uuid_str)
            assert str(uuid_obj) == uuid_str
            return True
        except (ValueError, AttributeError, TypeError):
            return False
            
    return _assert_valid_uuid


@pytest.fixture
def assert_iso_datetime():
    """Fixture providing a function to assert that a string is a valid ISO datetime."""
    def _assert_iso_datetime(datetime_str):
        try:
            datetime.datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError, TypeError):
            return False
            
    return _assert_iso_datetime


@pytest.fixture
def assert_dict_structure():
    """Fixture providing a function to assert that a dict has the expected structure."""
    def _assert_dict_structure(data, expected_keys):
        for key in expected_keys:
            assert key in data, f"Expected key '{key}' not found in data"
            
    return _assert_dict_structure