"""Tests for OCR accuracy under various load conditions.

This module tests the OCR Service's ability to maintain the required 99% data extraction 
accuracy even when processing multiple documents concurrently or under sustained load.
It verifies that accuracy and confidence scoring remain reliable under different load
scenarios, ensuring the service meets its performance requirements.
"""

import asyncio
import concurrent.futures
import json
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.models.confidence_scoring import (
    ConfidenceScore,
    calculate_document_confidence,
    analyze_confidence_distribution
)
from src.models.model_factory import ModelFactory
from src.services.ocr_service import OCRService
from src.types.extraction import ExtractedData
from src.types.models import OCRModelType
from src.utils.metrics import calculate_accuracy, calculate_field_accuracy


# Constants for test configuration
CONCURRENCY_LEVELS = [1, 5, 10, 20]  # Number of concurrent document processing tasks
SUSTAINED_DURATION = 60  # Duration in seconds for sustained load tests
ACCURACY_THRESHOLD = 0.99  # Required 99% accuracy threshold
CONFIDENCE_THRESHOLD = 0.75  # Minimum acceptable confidence score
DOCUMENT_TYPES = ["typed", "handwritten", "mixed"]  # Document types to test
QUALITY_LEVELS = ["high", "medium", "low"]  # Document quality levels to test


@pytest.fixture
def test_client() -> TestClient:
    """Create a FastAPI test client for the OCR Service."""
    return TestClient(app)


@pytest.fixture
def ocr_service() -> OCRService:
    """Create an OCR Service instance for testing."""
    return OCRService()


@pytest.fixture
def model_factory() -> ModelFactory:
    """Create a ModelFactory instance for testing."""
    return ModelFactory()


@pytest.fixture
def typed_documents(request) -> List[Dict[str, Any]]:
    """Load typed document test data with expected extraction results.
    
    This fixture loads document metadata and expected extraction results from the
    test_data/typed_documents directory. It can be parameterized with a specific
    quality level (high, medium, low) to test different document qualities.
    """
    quality = getattr(request, "param", "high")
    
    # Determine the manifest file path based on quality level
    if quality == "high":
        manifest_path = os.path.join("tests", "test_data", "typed_documents", 
                                    "quality_variations", "high_quality_manifest.json")
    elif quality == "medium":
        manifest_path = os.path.join("tests", "test_data", "typed_documents", 
                                    "sample_manifest.json")
    elif quality == "low":
        manifest_path = os.path.join("tests", "test_data", "typed_documents", 
                                    "quality_variations", "low_quality_manifest.json")
    else:
        raise ValueError(f"Unknown quality level: {quality}")
    
    # Load the manifest file
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        return manifest["documents"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        pytest.skip(f"Could not load typed document manifest: {e}")
        return []


@pytest.fixture
def handwritten_documents() -> List[Dict[str, Any]]:
    """Load handwritten document test data with expected extraction results."""
    # This would load from a similar manifest file for handwritten documents
    # For this test file, we'll simulate it with a placeholder
    return [
        {
            "id": "hw001",
            "path": "tests/test_data/handwritten_documents/sample1.pdf",
            "expected_fields": {
                "name": "John Smith",
                "date": "2023-01-15",
                "signature": True
            },
            "expected_accuracy": 0.95
        }
    ]


@pytest.fixture
def mixed_documents() -> List[Dict[str, Any]]:
    """Load mixed content document test data with expected extraction results."""
    # This would load from a similar manifest file for mixed documents
    # For this test file, we'll simulate it with a placeholder
    return [
        {
            "id": "mixed001",
            "path": "tests/test_data/mixed_documents/sample1.pdf",
            "expected_fields": {
                "business_name": "ACME Corp",
                "tax_id": "12-3456789",
                "signature": True
            },
            "expected_accuracy": 0.97
        }
    ]


@pytest.fixture
def document_batch(typed_documents, handwritten_documents, mixed_documents) -> Dict[str, List[Dict[str, Any]]]:
    """Create a batch of documents of different types for testing."""
    return {
        "typed": typed_documents,
        "handwritten": handwritten_documents,
        "mixed": mixed_documents
    }


def process_document(ocr_service: OCRService, document: Dict[str, Any]) -> Tuple[ExtractedData, float]:
    """Process a single document and calculate its accuracy.
    
    Args:
        ocr_service: The OCR service instance to use for processing
        document: Document metadata including path and expected results
        
    Returns:
        Tuple containing the extraction results and the calculated accuracy
    """
    # Process the document
    try:
        # In a real test, we would load the actual document file
        # For this test file, we'll simulate the processing
        document_path = document.get("path", "")
        document_type = "application_form"  # Default document type
        
        # Determine the appropriate model type based on document type
        if "typed" in document_path:
            model_type = OCRModelType.TYPED
        elif "handwritten" in document_path:
            model_type = OCRModelType.HANDWRITTEN
        else:
            model_type = OCRModelType.HYBRID
        
        # Process the document (simulated for this test)
        start_time = time.time()
        extraction_results = ocr_service.process_document(
            document_path=document_path,
            model_type=model_type,
            document_type=document_type
        )
        processing_time = time.time() - start_time
        
        # Calculate accuracy by comparing with expected fields
        expected_fields = document.get("expected_fields", {})
        accuracy = calculate_field_accuracy(
            extracted_fields=extraction_results.get("fields", {}),
            expected_fields=expected_fields
        )
        
        return extraction_results, accuracy
    except Exception as e:
        # Log the error and return empty results with zero accuracy
        print(f"Error processing document {document.get('id', 'unknown')}: {e}")
        return {
            "extraction_id": "",
            "fields": {},
            "tables": [],
            "metadata": {},
            "raw_text": "",
            "low_confidence_fields": [],
            "requires_verification": True,
            "extraction_timestamp": datetime.now(),
            "schema_version": "1.0",
            "document_type": document_type
        }, 0.0


async def process_document_async(ocr_service: OCRService, document: Dict[str, Any]) -> Tuple[ExtractedData, float]:
    """Process a single document asynchronously.
    
    This is a wrapper around the synchronous process_document function to allow
    it to be called in an asynchronous context.
    """
    # Simulate some async processing time
    await asyncio.sleep(0.1)
    return process_document(ocr_service, document)


def calculate_batch_accuracy(results: List[Tuple[ExtractedData, float]]) -> Dict[str, Any]:
    """Calculate aggregate accuracy metrics for a batch of processed documents.
    
    Args:
        results: List of tuples containing extraction results and accuracy scores
        
    Returns:
        Dictionary containing aggregate accuracy metrics
    """
    if not results:
        return {
            "mean_accuracy": 0.0,
            "min_accuracy": 0.0,
            "max_accuracy": 0.0,
            "std_dev": 0.0,
            "meets_threshold": False,
            "accuracy_distribution": {},
            "confidence_correlation": 0.0,
            "processing_count": 0
        }
    
    # Extract accuracy scores and confidence scores
    accuracy_scores = [acc for _, acc in results]
    confidence_scores = [float(calculate_document_confidence(res)) for res, _ in results]
    
    # Calculate accuracy metrics
    mean_accuracy = np.mean(accuracy_scores)
    min_accuracy = np.min(accuracy_scores)
    max_accuracy = np.max(accuracy_scores)
    std_dev = np.std(accuracy_scores)
    meets_threshold = mean_accuracy >= ACCURACY_THRESHOLD
    
    # Analyze accuracy distribution
    accuracy_distribution = analyze_confidence_distribution(accuracy_scores)
    
    # Calculate correlation between confidence and accuracy
    if len(accuracy_scores) > 1 and len(confidence_scores) > 1:
        confidence_correlation = np.corrcoef(accuracy_scores, confidence_scores)[0, 1]
    else:
        confidence_correlation = 0.0
    
    return {
        "mean_accuracy": float(mean_accuracy),
        "min_accuracy": float(min_accuracy),
        "max_accuracy": float(max_accuracy),
        "std_dev": float(std_dev),
        "meets_threshold": meets_threshold,
        "accuracy_distribution": accuracy_distribution,
        "confidence_correlation": float(confidence_correlation),
        "processing_count": len(results)
    }


@pytest.mark.parametrize("concurrency", CONCURRENCY_LEVELS)
@pytest.mark.parametrize("document_type", DOCUMENT_TYPES)
@pytest.mark.parametrize("typed_documents", QUALITY_LEVELS, indirect=True)
def test_accuracy_with_concurrent_processing(ocr_service, document_batch, concurrency, document_type, typed_documents):
    """Test OCR accuracy when processing multiple documents concurrently.
    
    This test verifies that the OCR service maintains its accuracy requirements
    even when processing multiple documents concurrently at different concurrency
    levels, with different document types and quality levels.
    
    Args:
        ocr_service: The OCR service fixture
        document_batch: Batch of test documents
        concurrency: Number of concurrent processing tasks
        document_type: Type of documents to test (typed, handwritten, mixed)
        typed_documents: Typed documents with specific quality level (parameterized)
    """
    # Skip if no documents of the specified type are available
    documents = document_batch.get(document_type, [])
    if not documents:
        pytest.skip(f"No {document_type} documents available for testing")
    
    # Ensure we have enough documents for the concurrency level
    # If not, duplicate the documents to reach the desired count
    while len(documents) < concurrency:
        documents.extend(documents[:concurrency - len(documents)])
    
    # Select a subset of documents based on concurrency level
    selected_documents = documents[:concurrency]
    
    # Process documents concurrently using ThreadPoolExecutor
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_doc = {executor.submit(process_document, ocr_service, doc): doc for doc in selected_documents}
        for future in concurrent.futures.as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                extraction_results, accuracy = future.result()
                results.append((extraction_results, accuracy))
            except Exception as e:
                print(f"Document processing failed: {e}")
                # Add a failed result with zero accuracy
                results.append(({}, 0.0))
    
    # Calculate aggregate accuracy metrics
    accuracy_metrics = calculate_batch_accuracy(results)
    
    # Assert that accuracy meets the threshold
    assert accuracy_metrics["meets_threshold"], (
        f"Accuracy below threshold with concurrency={concurrency}, "
        f"document_type={document_type}, mean_accuracy={accuracy_metrics['mean_accuracy']}"
    )
    
    # Assert that minimum accuracy is acceptable
    assert accuracy_metrics["min_accuracy"] >= 0.9, (
        f"Minimum accuracy too low with concurrency={concurrency}, "
        f"document_type={document_type}, min_accuracy={accuracy_metrics['min_accuracy']}"
    )
    
    # Assert that standard deviation is within acceptable limits
    assert accuracy_metrics["std_dev"] <= 0.05, (
        f"Accuracy variation too high with concurrency={concurrency}, "
        f"document_type={document_type}, std_dev={accuracy_metrics['std_dev']}"
    )
    
    # Print detailed metrics for debugging
    print(f"\nAccuracy metrics for concurrency={concurrency}, document_type={document_type}:")
    print(f"Mean accuracy: {accuracy_metrics['mean_accuracy']:.4f}")
    print(f"Min accuracy: {accuracy_metrics['min_accuracy']:.4f}")
    print(f"Max accuracy: {accuracy_metrics['max_accuracy']:.4f}")
    print(f"Standard deviation: {accuracy_metrics['std_dev']:.4f}")
    print(f"Confidence correlation: {accuracy_metrics['confidence_correlation']:.4f}")
    print(f"Processing count: {accuracy_metrics['processing_count']}")


@pytest.mark.asyncio
@pytest.mark.parametrize("document_type", DOCUMENT_TYPES)
@pytest.mark.parametrize("typed_documents", QUALITY_LEVELS, indirect=True)
async def test_accuracy_during_sustained_processing(ocr_service, document_batch, document_type, typed_documents):
    """Test OCR accuracy during sustained document processing over time.
    
    This test verifies that the OCR service maintains its accuracy requirements
    even when processing documents continuously over an extended period, simulating
    a sustained production load.
    
    Args:
        ocr_service: The OCR service fixture
        document_batch: Batch of test documents
        document_type: Type of documents to test (typed, handwritten, mixed)
        typed_documents: Typed documents with specific quality level (parameterized)
    """
    # Skip if no documents of the specified type are available
    documents = document_batch.get(document_type, [])
    if not documents:
        pytest.skip(f"No {document_type} documents available for testing")
    
    # Track results over time
    all_results = []
    start_time = time.time()
    end_time = start_time + SUSTAINED_DURATION
    
    # Process documents continuously until the duration is reached
    while time.time() < end_time:
        # Select a random document to process
        document = random.choice(documents)
        
        # Process the document asynchronously
        extraction_results, accuracy = await process_document_async(ocr_service, document)
        all_results.append((extraction_results, accuracy))
        
        # Add a small delay to prevent overwhelming the system
        await asyncio.sleep(0.1)
    
    # Calculate accuracy metrics for each time segment
    segment_duration = SUSTAINED_DURATION / 3  # Split into 3 segments
    segments = [[], [], []]
    
    # Distribute results into time segments
    for i, result in enumerate(all_results):
        segment_index = min(2, int(i * 3 / len(all_results)))
        segments[segment_index].append(result)
    
    # Calculate metrics for each segment
    segment_metrics = [calculate_batch_accuracy(segment) for segment in segments]
    
    # Assert that accuracy remains consistent across all segments
    for i, metrics in enumerate(segment_metrics):
        assert metrics["meets_threshold"], (
            f"Accuracy below threshold in segment {i+1}/3 with document_type={document_type}, "
            f"mean_accuracy={metrics['mean_accuracy']}"
        )
    
    # Assert that accuracy doesn't degrade over time
    if len(segment_metrics) >= 3:
        # Compare first and last segment
        first_accuracy = segment_metrics[0]["mean_accuracy"]
        last_accuracy = segment_metrics[-1]["mean_accuracy"]
        
        assert last_accuracy >= first_accuracy * 0.95, (
            f"Accuracy degraded over time with document_type={document_type}, "
            f"first_segment={first_accuracy:.4f}, last_segment={last_accuracy:.4f}"
        )
    
    # Print detailed metrics for debugging
    print(f"\nSustained processing metrics for document_type={document_type}:")
    print(f"Total documents processed: {len(all_results)}")
    print(f"Processing rate: {len(all_results) / SUSTAINED_DURATION:.2f} docs/sec")
    
    for i, metrics in enumerate(segment_metrics):
        print(f"\nSegment {i+1}/3 metrics:")
        print(f"Mean accuracy: {metrics['mean_accuracy']:.4f}")
        print(f"Min accuracy: {metrics['min_accuracy']:.4f}")
        print(f"Max accuracy: {metrics['max_accuracy']:.4f}")
        print(f"Standard deviation: {metrics['std_dev']:.4f}")
        print(f"Documents processed: {metrics['processing_count']}")


@pytest.mark.parametrize("document_type", DOCUMENT_TYPES)
@pytest.mark.parametrize("typed_documents", QUALITY_LEVELS, indirect=True)
def test_confidence_score_reliability_under_load(ocr_service, document_batch, document_type, typed_documents):
    """Test reliability of confidence scores under load conditions.
    
    This test verifies that the OCR service's confidence scoring remains reliable
    and correlates with actual accuracy even under load conditions.
    
    Args:
        ocr_service: The OCR service fixture
        document_batch: Batch of test documents
        document_type: Type of documents to test (typed, handwritten, mixed)
        typed_documents: Typed documents with specific quality level (parameterized)
    """
    # Skip if no documents of the specified type are available
    documents = document_batch.get(document_type, [])
    if not documents:
        pytest.skip(f"No {document_type} documents available for testing")
    
    # Process documents in parallel to simulate load
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_doc = {executor.submit(process_document, ocr_service, doc): doc for doc in documents}
        for future in concurrent.futures.as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                extraction_results, accuracy = future.result()
                results.append((extraction_results, accuracy))
            except Exception as e:
                print(f"Document processing failed: {e}")
    
    # Skip if no results were obtained
    if not results:
        pytest.skip("No results obtained from document processing")
    
    # Extract confidence scores and accuracy scores
    confidence_scores = [float(calculate_document_confidence(res)) for res, _ in results]
    accuracy_scores = [acc for _, acc in results]
    
    # Calculate correlation between confidence and accuracy
    if len(confidence_scores) > 1 and len(accuracy_scores) > 1:
        correlation = np.corrcoef(confidence_scores, accuracy_scores)[0, 1]
    else:
        correlation = 0.0
    
    # Assert that confidence scores correlate with accuracy
    assert correlation >= 0.7, (
        f"Confidence scores do not reliably correlate with accuracy under load, "
        f"document_type={document_type}, correlation={correlation:.4f}"
    )
    
    # Check that confidence scores are within reasonable bounds
    for i, (res, acc) in enumerate(results):
        confidence = float(calculate_document_confidence(res))
        
        # Confidence should not be too far from accuracy
        assert abs(confidence - acc) <= 0.2, (
            f"Confidence score significantly differs from accuracy for document {i}, "
            f"confidence={confidence:.4f}, accuracy={acc:.4f}"
        )
        
        # Confidence should be above minimum threshold
        assert confidence >= CONFIDENCE_THRESHOLD, (
            f"Confidence score below threshold for document {i}, "
            f"confidence={confidence:.4f}"
        )
    
    # Print detailed metrics for debugging
    print(f"\nConfidence reliability metrics for document_type={document_type}:")
    print(f"Correlation coefficient: {correlation:.4f}")
    print(f"Mean confidence: {np.mean(confidence_scores):.4f}")
    print(f"Mean accuracy: {np.mean(accuracy_scores):.4f}")
    print(f"Confidence-accuracy difference: {np.mean(np.abs(np.array(confidence_scores) - np.array(accuracy_scores))):.4f}")


def test_accuracy_with_mixed_document_batch(ocr_service, document_batch):
    """Test OCR accuracy when processing a mixed batch of different document types.
    
    This test verifies that the OCR service maintains its accuracy requirements
    even when processing a mixed batch of different document types and qualities
    simultaneously, simulating a real-world scenario.
    
    Args:
        ocr_service: The OCR service fixture
        document_batch: Batch of test documents
    """
    # Create a mixed batch with documents of different types
    mixed_batch = []
    for doc_type, docs in document_batch.items():
        if docs:
            # Add up to 5 documents of each type
            mixed_batch.extend(docs[:5])
    
    # Skip if the mixed batch is empty
    if not mixed_batch:
        pytest.skip("No documents available for mixed batch testing")
    
    # Process documents in parallel
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(mixed_batch)) as executor:
        future_to_doc = {executor.submit(process_document, ocr_service, doc): doc for doc in mixed_batch}
        for future in concurrent.futures.as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                extraction_results, accuracy = future.result()
                results.append((extraction_results, accuracy))
            except Exception as e:
                print(f"Document processing failed: {e}")
    
    # Calculate aggregate accuracy metrics
    accuracy_metrics = calculate_batch_accuracy(results)
    
    # Assert that accuracy meets the threshold
    assert accuracy_metrics["meets_threshold"], (
        f"Accuracy below threshold with mixed document batch, "
        f"mean_accuracy={accuracy_metrics['mean_accuracy']}"
    )
    
    # Assert that minimum accuracy is acceptable
    assert accuracy_metrics["min_accuracy"] >= 0.9, (
        f"Minimum accuracy too low with mixed document batch, "
        f"min_accuracy={accuracy_metrics['min_accuracy']}"
    )
    
    # Print detailed metrics for debugging
    print(f"\nAccuracy metrics for mixed document batch:")
    print(f"Mean accuracy: {accuracy_metrics['mean_accuracy']:.4f}")
    print(f"Min accuracy: {accuracy_metrics['min_accuracy']:.4f}")
    print(f"Max accuracy: {accuracy_metrics['max_accuracy']:.4f}")
    print(f"Standard deviation: {accuracy_metrics['std_dev']:.4f}")
    print(f"Confidence correlation: {accuracy_metrics['confidence_correlation']:.4f}")
    print(f"Processing count: {accuracy_metrics['processing_count']}")


@pytest.mark.parametrize("typed_documents", ["low"], indirect=True)
def test_accuracy_with_low_quality_documents_under_load(ocr_service, document_batch, typed_documents):
    """Test OCR accuracy with low-quality documents under load conditions.
    
    This test verifies that the OCR service maintains acceptable accuracy even
    when processing low-quality documents under load conditions.
    
    Args:
        ocr_service: The OCR service fixture
        document_batch: Batch of test documents
        typed_documents: Low-quality typed documents (parameterized)
    """
    # Use only the typed documents for this test
    documents = document_batch.get("typed", [])
    if not documents:
        pytest.skip("No typed documents available for testing")
    
    # Process documents in parallel with high concurrency
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        # Process each document multiple times to increase load
        future_to_doc = {}
        for _ in range(3):  # Process each document 3 times
            for doc in documents:
                future = executor.submit(process_document, ocr_service, doc)
                future_to_doc[future] = doc
        
        for future in concurrent.futures.as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                extraction_results, accuracy = future.result()
                results.append((extraction_results, accuracy))
            except Exception as e:
                print(f"Document processing failed: {e}")
    
    # Calculate aggregate accuracy metrics
    accuracy_metrics = calculate_batch_accuracy(results)
    
    # For low-quality documents, we accept a slightly lower accuracy threshold
    low_quality_threshold = 0.95  # 95% accuracy for low-quality documents
    
    # Assert that accuracy meets the adjusted threshold
    assert accuracy_metrics["mean_accuracy"] >= low_quality_threshold, (
        f"Accuracy below adjusted threshold for low-quality documents under load, "
        f"mean_accuracy={accuracy_metrics['mean_accuracy']}"
    )
    
    # Assert that confidence scores correctly reflect the lower accuracy
    confidence_scores = [float(calculate_document_confidence(res)) for res, _ in results]
    mean_confidence = np.mean(confidence_scores)
    
    assert mean_confidence < 0.9, (
        f"Confidence scores too high for low-quality documents, "
        f"mean_confidence={mean_confidence:.4f}"
    )
    
    # Print detailed metrics for debugging
    print(f"\nAccuracy metrics for low-quality documents under load:")
    print(f"Mean accuracy: {accuracy_metrics['mean_accuracy']:.4f}")
    print(f"Min accuracy: {accuracy_metrics['min_accuracy']:.4f}")
    print(f"Max accuracy: {accuracy_metrics['max_accuracy']:.4f}")
    print(f"Standard deviation: {accuracy_metrics['std_dev']:.4f}")
    print(f"Mean confidence: {mean_confidence:.4f}")
    print(f"Processing count: {accuracy_metrics['processing_count']}")


def test_accuracy_stability_with_increasing_load(ocr_service, document_batch):
    """Test stability of OCR accuracy as load increases.
    
    This test verifies that the OCR service's accuracy remains stable as the
    processing load increases, ensuring that performance doesn't degrade under
    high load conditions.
    
    Args:
        ocr_service: The OCR service fixture
        document_batch: Batch of test documents
    """
    # Combine documents of all types
    all_documents = []
    for docs in document_batch.values():
        all_documents.extend(docs)
    
    # Skip if no documents are available
    if not all_documents:
        pytest.skip("No documents available for testing")
    
    # Ensure we have enough documents by duplicating if necessary
    while len(all_documents) < 50:
        all_documents.extend(all_documents[:50 - len(all_documents)])
    
    # Test with increasing concurrency levels
    concurrency_levels = [1, 5, 10, 20, 30, 40, 50]
    accuracy_results = []
    
    for concurrency in concurrency_levels:
        # Select documents for this concurrency level
        selected_documents = all_documents[:concurrency]
        
        # Process documents in parallel
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_doc = {executor.submit(process_document, ocr_service, doc): doc for doc in selected_documents}
            for future in concurrent.futures.as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    extraction_results, accuracy = future.result()
                    results.append((extraction_results, accuracy))
                except Exception as e:
                    print(f"Document processing failed: {e}")
        
        # Calculate aggregate accuracy metrics
        accuracy_metrics = calculate_batch_accuracy(results)
        accuracy_results.append((concurrency, accuracy_metrics))
    
    # Check if accuracy remains stable across increasing load
    baseline_accuracy = accuracy_results[0][1]["mean_accuracy"]
    for concurrency, metrics in accuracy_results[1:]:
        current_accuracy = metrics["mean_accuracy"]
        
        # Accuracy should not drop by more than 2% as load increases
        assert current_accuracy >= baseline_accuracy * 0.98, (
            f"Accuracy degraded significantly at concurrency={concurrency}, "
            f"baseline={baseline_accuracy:.4f}, current={current_accuracy:.4f}"
        )
    
    # Print detailed metrics for debugging
    print("\nAccuracy stability with increasing load:")
    for concurrency, metrics in accuracy_results:
        print(f"Concurrency={concurrency}, Mean accuracy={metrics['mean_accuracy']:.4f}, "
              f"Std dev={metrics['std_dev']:.4f}")


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])