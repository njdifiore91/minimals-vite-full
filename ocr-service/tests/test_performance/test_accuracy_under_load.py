#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests the accuracy of the OCR Service under various load conditions.

Verifies that the service maintains the required 99% data extraction accuracy
even when processing multiple documents concurrently or under sustained load.
"""

import os
import time
import pytest
import numpy as np
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple, Any, Optional

# Import OCR service modules
from ocr_service.services import OCRService, confidence_service
from ocr_service.models import model_factory
from ocr_service.types import DocumentType, ExtractionResult, ConfidenceScore


# Constants for test configuration
MIN_REQUIRED_ACCURACY = 0.99  # 99% accuracy requirement
CONCURRENCY_LEVELS = [1, 2, 4, 8, 16]  # Different concurrency levels to test
SUSTAINED_DURATION = 60  # Duration in seconds for sustained load tests
DOCUMENT_TYPES = ["application_form", "tax_return", "bank_statement", "invoice"]  # Document types to test


# Helper functions for accuracy calculation
def calculate_accuracy(expected: Dict[str, Any], actual: Dict[str, Any]) -> float:
    """
    Calculate the accuracy of OCR extraction by comparing expected and actual results.
    
    Args:
        expected: Dictionary of expected field values
        actual: Dictionary of actual extracted field values
    
    Returns:
        float: Accuracy score between 0.0 and 1.0
    """
    if not expected or not actual:
        return 0.0
    
    total_fields = len(expected)
    correct_fields = 0
    
    for field, expected_value in expected.items():
        if field in actual and actual[field] == expected_value:
            correct_fields += 1
    
    return correct_fields / total_fields


def calculate_batch_accuracy(results: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> float:
    """
    Calculate the average accuracy across a batch of extraction results.
    
    Args:
        results: List of tuples containing (expected, actual) result pairs
    
    Returns:
        float: Average accuracy score between 0.0 and 1.0
    """
    if not results:
        return 0.0
    
    accuracies = [calculate_accuracy(expected, actual) for expected, actual in results]
    return sum(accuracies) / len(accuracies)


# Test fixtures
@pytest.fixture(scope="module")
def ocr_service():
    """
    Fixture that provides an initialized OCR service instance.
    """
    service = OCRService()
    # Ensure the service is properly initialized
    service.initialize()
    yield service
    # Clean up resources after tests
    service.shutdown()


@pytest.fixture(scope="module")
def document_datasets(request):
    """
    Fixture that provides test document datasets with known expected extraction results.
    
    Returns a dictionary mapping document types to lists of (document_path, expected_results) tuples.
    """
    # Base path for test documents
    base_path = os.path.join(os.path.dirname(__file__), "../test_data")
    
    # Load document datasets
    datasets = {}
    
    for doc_type in DOCUMENT_TYPES:
        doc_path = os.path.join(base_path, f"typed_documents/{doc_type}s")
        if not os.path.exists(doc_path):
            continue
            
        # Load manifest file with expected results
        manifest_path = os.path.join(doc_path, f"{doc_type}_manifest.json")
        if os.path.exists(manifest_path):
            import json
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                
            # Create list of (document_path, expected_results) tuples
            dataset = []
            for doc_id, doc_info in manifest.items():
                doc_file_path = os.path.join(doc_path, doc_info["filename"])
                if os.path.exists(doc_file_path):
                    dataset.append((doc_file_path, doc_info["expected_results"]))
            
            datasets[doc_type] = dataset
    
    return datasets


# Test functions
def process_document(args):
    """
    Process a single document and return the accuracy result.
    This function is used by the multiprocessing pool.
    
    Args:
        args: Tuple containing (service, document_path, expected_results)
    
    Returns:
        Tuple: (expected_results, actual_results)
    """
    service, doc_path, expected = args
    
    # Process the document
    result = service.process_document(doc_path)
    
    # Return the expected and actual results for accuracy calculation
    return expected, result.extracted_data


@pytest.mark.parametrize("concurrency", CONCURRENCY_LEVELS)
def test_accuracy_at_different_concurrency_levels(ocr_service, document_datasets, concurrency):
    """
    Test that OCR accuracy remains above 99% at different concurrency levels.
    
    Args:
        ocr_service: OCR service fixture
        document_datasets: Document datasets fixture
        concurrency: Number of concurrent processes to use
    """
    # Skip if no datasets available
    if not document_datasets:
        pytest.skip("No document datasets available for testing")
    
    # Flatten the datasets into a single list of (document_path, expected_results) tuples
    all_documents = []
    for doc_type, dataset in document_datasets.items():
        all_documents.extend(dataset)
    
    # Limit the number of documents to process based on concurrency level
    # to ensure we have enough documents for a meaningful test
    num_docs = min(len(all_documents), concurrency * 5)  # Process at least 5 docs per worker
    test_documents = all_documents[:num_docs]
    
    # Prepare arguments for multiprocessing
    args = [(ocr_service, doc_path, expected) for doc_path, expected in test_documents]
    
    # Process documents concurrently
    with ProcessPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(process_document, args))
    
    # Calculate overall accuracy
    accuracy = calculate_batch_accuracy(results)
    
    # Assert that accuracy meets the requirement
    assert accuracy >= MIN_REQUIRED_ACCURACY, \
        f"Accuracy at concurrency level {concurrency} was {accuracy:.4f}, which is below the required {MIN_REQUIRED_ACCURACY:.4f}"


def test_accuracy_during_sustained_processing(ocr_service, document_datasets):
    """
    Test that OCR accuracy remains above 99% during sustained processing over time.
    
    Args:
        ocr_service: OCR service fixture
        document_datasets: Document datasets fixture
    """
    # Skip if no datasets available
    if not document_datasets:
        pytest.skip("No document datasets available for testing")
    
    # Flatten the datasets into a single list of (document_path, expected_results) tuples
    all_documents = []
    for doc_type, dataset in document_datasets.items():
        all_documents.extend(dataset)
    
    # If we don't have enough documents, repeat them to create a larger dataset
    while len(all_documents) < 100:  # Ensure we have at least 100 documents for sustained testing
        all_documents.extend(all_documents[:min(len(all_documents), 100 - len(all_documents))])
    
    # Use a moderate concurrency level for sustained processing
    concurrency = min(8, mp.cpu_count())
    
    # Track accuracy over time
    start_time = time.time()
    end_time = start_time + SUSTAINED_DURATION
    
    accuracies = []
    iteration = 0
    
    # Process documents in batches until the duration is reached
    while time.time() < end_time:
        # Select a batch of documents for this iteration
        batch_size = min(concurrency * 2, len(all_documents))
        batch_start = (iteration * batch_size) % (len(all_documents) - batch_size)
        batch = all_documents[batch_start:batch_start + batch_size]
        
        # Prepare arguments for multiprocessing
        args = [(ocr_service, doc_path, expected) for doc_path, expected in batch]
        
        # Process documents concurrently
        with ProcessPoolExecutor(max_workers=concurrency) as executor:
            results = list(executor.map(process_document, args))
        
        # Calculate batch accuracy
        batch_accuracy = calculate_batch_accuracy(results)
        accuracies.append(batch_accuracy)
        
        iteration += 1
    
    # Calculate overall accuracy across all batches
    overall_accuracy = sum(accuracies) / len(accuracies)
    
    # Assert that accuracy meets the requirement
    assert overall_accuracy >= MIN_REQUIRED_ACCURACY, \
        f"Accuracy during sustained processing was {overall_accuracy:.4f}, which is below the required {MIN_REQUIRED_ACCURACY:.4f}"
    
    # Also assert that no individual batch fell below the threshold
    min_batch_accuracy = min(accuracies)
    assert min_batch_accuracy >= MIN_REQUIRED_ACCURACY, \
        f"Minimum batch accuracy during sustained processing was {min_batch_accuracy:.4f}, which is below the required {MIN_REQUIRED_ACCURACY:.4f}"


@pytest.mark.parametrize("doc_type", DOCUMENT_TYPES)
def test_accuracy_with_different_document_types_under_load(ocr_service, document_datasets, doc_type):
    """
    Test that OCR accuracy remains above 99% for different document types under load.
    
    Args:
        ocr_service: OCR service fixture
        document_datasets: Document datasets fixture
        doc_type: Document type to test
    """
    # Skip if this document type is not available
    if doc_type not in document_datasets or not document_datasets[doc_type]:
        pytest.skip(f"No {doc_type} documents available for testing")
    
    # Get the dataset for this document type
    dataset = document_datasets[doc_type]
    
    # If we don't have enough documents, repeat them to create a larger dataset
    test_documents = dataset
    while len(test_documents) < 20:  # Ensure we have at least 20 documents for a meaningful test
        test_documents.extend(test_documents[:min(len(test_documents), 20 - len(test_documents))])
    
    # Use a moderate concurrency level
    concurrency = min(8, mp.cpu_count())
    
    # Prepare arguments for multiprocessing
    args = [(ocr_service, doc_path, expected) for doc_path, expected in test_documents]
    
    # Process documents concurrently
    with ProcessPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(process_document, args))
    
    # Calculate overall accuracy
    accuracy = calculate_batch_accuracy(results)
    
    # Assert that accuracy meets the requirement
    assert accuracy >= MIN_REQUIRED_ACCURACY, \
        f"Accuracy for {doc_type} documents under load was {accuracy:.4f}, which is below the required {MIN_REQUIRED_ACCURACY:.4f}"


def test_confidence_score_reliability_under_load(ocr_service, document_datasets):
    """
    Test that confidence scores remain reliable under load conditions.
    
    Args:
        ocr_service: OCR service fixture
        document_datasets: Document datasets fixture
    """
    # Skip if no datasets available
    if not document_datasets:
        pytest.skip("No document datasets available for testing")
    
    # Flatten the datasets into a single list of (document_path, expected_results) tuples
    all_documents = []
    for doc_type, dataset in document_datasets.items():
        all_documents.extend(dataset)
    
    # Limit the number of documents to process
    num_docs = min(len(all_documents), 50)  # Process up to 50 documents
    test_documents = all_documents[:num_docs]
    
    # Use a high concurrency level to stress the system
    concurrency = min(16, mp.cpu_count())
    
    # Define a function to process a document and return both extraction results and confidence scores
    def process_with_confidence(args):
        service, doc_path, expected = args
        result = service.process_document(doc_path)
        return expected, result.extracted_data, result.confidence_scores
    
    # Prepare arguments for multiprocessing
    args = [(ocr_service, doc_path, expected) for doc_path, expected in test_documents]
    
    # Process documents concurrently
    with ProcessPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(process_with_confidence, args))
    
    # Analyze confidence scores vs. actual accuracy
    confidence_accuracy_pairs = []
    for expected, actual, confidence_scores in results:
        # Calculate actual accuracy for this document
        actual_accuracy = calculate_accuracy(expected, actual)
        
        # Get the average confidence score for this document
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0
        
        confidence_accuracy_pairs.append((avg_confidence, actual_accuracy))
    
    # Calculate correlation between confidence scores and actual accuracy
    confidences = [pair[0] for pair in confidence_accuracy_pairs]
    accuracies = [pair[1] for pair in confidence_accuracy_pairs]
    
    # Calculate correlation coefficient if we have enough data points
    if len(confidences) >= 5:  # Need at least a few data points for meaningful correlation
        correlation = np.corrcoef(confidences, accuracies)[0, 1]
        
        # Assert that confidence scores are positively correlated with actual accuracy
        assert correlation > 0.5, \
            f"Confidence scores are not reliably correlated with actual accuracy (correlation: {correlation:.4f})"
    
    # Also verify that high confidence scores (>0.9) correspond to high accuracy
    high_confidence_pairs = [(c, a) for c, a in confidence_accuracy_pairs if c > 0.9]
    if high_confidence_pairs:
        high_confidence_accuracies = [pair[1] for pair in high_confidence_pairs]
        avg_high_confidence_accuracy = sum(high_confidence_accuracies) / len(high_confidence_accuracies)
        
        # Assert that high confidence scores correspond to high accuracy
        assert avg_high_confidence_accuracy >= MIN_REQUIRED_ACCURACY, \
            f"Documents with high confidence scores do not consistently achieve the required accuracy " \
            f"(average accuracy: {avg_high_confidence_accuracy:.4f})"


def test_accuracy_maintained_under_all_load_conditions(ocr_service, document_datasets):
    """
    Comprehensive test that verifies 99% accuracy is maintained under all load conditions.
    
    This test combines aspects of the other tests to provide a thorough validation of
    accuracy under various challenging conditions.
    
    Args:
        ocr_service: OCR service fixture
        document_datasets: Document datasets fixture
    """
    # Skip if no datasets available
    if not document_datasets:
        pytest.skip("No document datasets available for testing")
    
    # Flatten the datasets into a single list of (document_path, expected_results) tuples
    all_documents = []
    for doc_type, dataset in document_datasets.items():
        all_documents.extend(dataset)
    
    # If we don't have enough documents, repeat them to create a larger dataset
    while len(all_documents) < 100:  # Ensure we have at least 100 documents
        all_documents.extend(all_documents[:min(len(all_documents), 100 - len(all_documents))])
    
    # Test with varying concurrency levels
    accuracies_by_concurrency = {}
    for concurrency in CONCURRENCY_LEVELS:
        # Skip concurrency levels that are too high for the available CPUs
        if concurrency > mp.cpu_count() * 2:
            continue
        
        # Limit the number of documents to process based on concurrency level
        num_docs = min(len(all_documents), concurrency * 5)  # Process at least 5 docs per worker
        test_documents = all_documents[:num_docs]
        
        # Prepare arguments for multiprocessing
        args = [(ocr_service, doc_path, expected) for doc_path, expected in test_documents]
        
        # Process documents concurrently
        with ProcessPoolExecutor(max_workers=concurrency) as executor:
            results = list(executor.map(process_document, args))
        
        # Calculate overall accuracy
        accuracy = calculate_batch_accuracy(results)
        accuracies_by_concurrency[concurrency] = accuracy
    
    # Calculate minimum accuracy across all concurrency levels
    min_accuracy = min(accuracies_by_concurrency.values()) if accuracies_by_concurrency else 0
    
    # Assert that accuracy meets the requirement across all concurrency levels
    assert min_accuracy >= MIN_REQUIRED_ACCURACY, \
        f"Minimum accuracy across all concurrency levels was {min_accuracy:.4f}, " \
        f"which is below the required {MIN_REQUIRED_ACCURACY:.4f}"
    
    # Also test with mixed document types in a single batch
    # Shuffle the documents to mix different types
    import random
    random.shuffle(all_documents)
    
    # Use a moderate concurrency level
    concurrency = min(8, mp.cpu_count())
    
    # Limit the number of documents to process
    num_docs = min(len(all_documents), 50)  # Process up to 50 documents
    test_documents = all_documents[:num_docs]
    
    # Prepare arguments for multiprocessing
    args = [(ocr_service, doc_path, expected) for doc_path, expected in test_documents]
    
    # Process documents concurrently
    with ProcessPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(process_document, args))
    
    # Calculate overall accuracy for mixed document types
    mixed_accuracy = calculate_batch_accuracy(results)
    
    # Assert that accuracy meets the requirement for mixed document types
    assert mixed_accuracy >= MIN_REQUIRED_ACCURACY, \
        f"Accuracy for mixed document types was {mixed_accuracy:.4f}, " \
        f"which is below the required {MIN_REQUIRED_ACCURACY:.4f}"


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])