#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Throughput performance tests for the OCR Service.

This module contains tests that measure the throughput capabilities of the OCR Service
under various conditions, including single-document processing, batch processing,
concurrent request handling, and sustained processing over extended periods.

These tests verify that the OCR Service can handle the required volume of documents
to meet business requirements, including processing applications in under 5 minutes
and achieving a 93% reduction in manual processing through automation.
"""

import time
import pytest
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from ocr_service.services import OCRService, StorageService
from ocr_service.models import ModelFactory
from ocr_service.config import app_config, tensorflow_config


@pytest.fixture
def ocr_service(monkeypatch):
    """Fixture that provides a configured OCR service instance for testing."""
    # Configure test-specific settings
    monkeypatch.setattr(tensorflow_config, "GPU_MEMORY_LIMIT", 4096)  # 4GB for testing
    monkeypatch.setattr(app_config, "BATCH_SIZE", 10)
    
    # Initialize services
    model_factory = ModelFactory()
    storage_service = StorageService()
    service = OCRService(model_factory, storage_service)
    
    return service


@pytest.fixture
def test_document_ids(request) -> List[str]:
    """Fixture that provides document IDs for testing based on the test parameter."""
    # Default to 100 documents if not specified
    count = getattr(request, "param", 100)
    
    # Generate document IDs in the format "test-doc-{i}"
    return [f"test-doc-{i}" for i in range(count)]


@pytest.fixture
def document_types() -> List[str]:
    """Fixture that provides a list of document types for testing."""
    return [
        "application_form",
        "tax_return",
        "bank_statement",
        "invoice",
        "id_document"
    ]


def test_single_document_throughput(ocr_service, test_document_ids):
    """
    Test the throughput of processing single documents sequentially.
    
    This test measures how many documents can be processed per minute
    when processed one at a time sequentially.
    """
    # Take a subset of documents for this test
    doc_ids = test_document_ids[:20]
    processing_times = []
    
    # Process each document and measure the time
    for doc_id in doc_ids:
        start_time = time.time()
        ocr_service.process_document(doc_id)
        end_time = time.time()
        processing_times.append(end_time - start_time)
    
    # Calculate throughput metrics
    avg_processing_time = np.mean(processing_times)
    throughput_per_minute = 60 / avg_processing_time
    
    # Log results
    print(f"Average processing time per document: {avg_processing_time:.2f} seconds")
    print(f"Single-document throughput: {throughput_per_minute:.2f} documents per minute")
    
    # Assert that processing time meets requirements (under 5 minutes per document)
    assert avg_processing_time < 300, "Processing time exceeds 5 minutes requirement"
    
    # Assert minimum throughput based on business requirements
    # Assuming we need to process at least 12 documents per hour (1 every 5 minutes)
    assert throughput_per_minute >= 0.2, "Throughput does not meet minimum business requirements"


@pytest.mark.parametrize("batch_size", [5, 10, 20])
def test_batch_processing_throughput(ocr_service, test_document_ids, batch_size):
    """
    Test the throughput of processing documents in batches.
    
    This test measures how many documents can be processed per minute
    when processed in batches of different sizes.
    """
    # Take a subset of documents for this test
    doc_ids = test_document_ids[:batch_size * 3]  # Use 3 batches
    
    # Split documents into batches
    batches = [doc_ids[i:i + batch_size] for i in range(0, len(doc_ids), batch_size)]
    batch_processing_times = []
    
    # Process each batch and measure the time
    for batch in batches:
        start_time = time.time()
        ocr_service.process_document_batch(batch)
        end_time = time.time()
        batch_processing_times.append(end_time - start_time)
    
    # Calculate throughput metrics
    avg_batch_time = np.mean(batch_processing_times)
    avg_doc_time = avg_batch_time / batch_size
    throughput_per_minute = 60 / avg_doc_time
    
    # Log results
    print(f"Batch size: {batch_size}")
    print(f"Average batch processing time: {avg_batch_time:.2f} seconds")
    print(f"Average time per document in batch: {avg_doc_time:.2f} seconds")
    print(f"Batch throughput: {throughput_per_minute:.2f} documents per minute")
    
    # Assert that processing time meets requirements (under 5 minutes per document)
    assert avg_doc_time < 300, "Processing time per document in batch exceeds 5 minutes requirement"
    
    # Assert that batch processing improves throughput compared to single document processing
    # This is a relative test that will be compared to the single document test results
    # We'll store the results for comparison in the test_batch_vs_single_throughput test
    return {
        "batch_size": batch_size,
        "avg_doc_time": avg_doc_time,
        "throughput_per_minute": throughput_per_minute
    }


def test_batch_vs_single_throughput(ocr_service, test_document_ids):
    """
    Test that batch processing improves throughput compared to single document processing.
    
    This test verifies that processing documents in batches provides better throughput
    than processing them one at a time.
    """
    # Get single document throughput
    single_doc_result = test_single_document_throughput(ocr_service, test_document_ids)
    
    # Get batch processing throughput for different batch sizes
    batch_results = [
        test_batch_processing_throughput(ocr_service, test_document_ids, batch_size)
        for batch_size in [5, 10, 20]
    ]
    
    # Compare throughput
    for batch_result in batch_results:
        batch_size = batch_result["batch_size"]
        batch_throughput = batch_result["throughput_per_minute"]
        
        # Assert that batch processing improves throughput
        assert batch_throughput > single_doc_result["throughput_per_minute"], \
            f"Batch processing with size {batch_size} does not improve throughput"
        
        # Log improvement
        improvement = (batch_throughput / single_doc_result["throughput_per_minute"]) - 1
        print(f"Batch size {batch_size} improves throughput by {improvement:.2%}")


@pytest.mark.parametrize("concurrent_requests", [2, 4, 8])
def test_concurrent_request_throughput(ocr_service, test_document_ids, concurrent_requests):
    """
    Test the throughput of processing documents with concurrent requests.
    
    This test measures how many documents can be processed per minute
    when multiple requests are processed concurrently.
    """
    # Take a subset of documents for this test
    doc_ids = test_document_ids[:concurrent_requests * 5]  # 5 documents per worker
    
    # Split documents among workers
    worker_doc_ids = [doc_ids[i::concurrent_requests] for i in range(concurrent_requests)]
    
    # Function for worker to process documents
    def worker_process(docs):
        results = []
        for doc_id in docs:
            start_time = time.time()
            ocr_service.process_document(doc_id)
            end_time = time.time()
            results.append({"doc_id": doc_id, "time": end_time - start_time})
        return results
    
    # Process documents concurrently
    start_time = time.time()
    all_results = []
    
    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = [executor.submit(worker_process, docs) for docs in worker_doc_ids]
        for future in as_completed(futures):
            all_results.extend(future.result())
    
    end_time = time.time()
    
    # Calculate throughput metrics
    total_time = end_time - start_time
    total_docs = len(doc_ids)
    throughput_per_minute = (total_docs / total_time) * 60
    
    # Calculate individual document processing times
    processing_times = [result["time"] for result in all_results]
    avg_processing_time = np.mean(processing_times)
    max_processing_time = np.max(processing_times)
    
    # Log results
    print(f"Concurrent requests: {concurrent_requests}")
    print(f"Total processing time: {total_time:.2f} seconds for {total_docs} documents")
    print(f"Average processing time per document: {avg_processing_time:.2f} seconds")
    print(f"Maximum processing time for a document: {max_processing_time:.2f} seconds")
    print(f"Concurrent throughput: {throughput_per_minute:.2f} documents per minute")
    
    # Assert that processing time meets requirements (under 5 minutes per document)
    assert max_processing_time < 300, "Maximum processing time exceeds 5 minutes requirement"
    
    # Assert minimum throughput based on business requirements
    # For concurrent processing, we expect higher throughput
    min_expected_throughput = 0.2 * concurrent_requests  # Scale with concurrency
    assert throughput_per_minute >= min_expected_throughput, \
        f"Concurrent throughput does not meet minimum requirements for {concurrent_requests} workers"
    
    return {
        "concurrent_requests": concurrent_requests,
        "throughput_per_minute": throughput_per_minute,
        "avg_processing_time": avg_processing_time
    }


def test_optimal_concurrency(ocr_service, test_document_ids):
    """
    Test to determine the optimal concurrency level for maximum throughput.
    
    This test tries different concurrency levels to find the one that
    provides the best throughput without overloading the system.
    """
    # Test different concurrency levels
    concurrency_levels = [1, 2, 4, 8, 16]
    results = []
    
    for concurrency in concurrency_levels:
        if concurrency == 1:
            # For single-threaded, use the single document test
            single_result = test_single_document_throughput(ocr_service, test_document_ids)
            results.append({
                "concurrent_requests": 1,
                "throughput_per_minute": single_result["throughput_per_minute"],
                "avg_processing_time": single_result["avg_processing_time"]
            })
        else:
            # For multi-threaded, use the concurrent request test
            result = test_concurrent_request_throughput(ocr_service, test_document_ids, concurrency)
            results.append(result)
    
    # Find the optimal concurrency level
    optimal_result = max(results, key=lambda x: x["throughput_per_minute"])
    optimal_concurrency = optimal_result["concurrent_requests"]
    optimal_throughput = optimal_result["throughput_per_minute"]
    
    # Log results
    print(f"Optimal concurrency level: {optimal_concurrency} concurrent requests")
    print(f"Optimal throughput: {optimal_throughput:.2f} documents per minute")
    
    # Plot throughput vs concurrency if matplotlib is available
    try:
        import matplotlib.pyplot as plt
        
        concurrency_values = [r["concurrent_requests"] for r in results]
        throughput_values = [r["throughput_per_minute"] for r in results]
        
        plt.figure(figsize=(10, 6))
        plt.plot(concurrency_values, throughput_values, marker='o')
        plt.title('Throughput vs Concurrency')
        plt.xlabel('Concurrent Requests')
        plt.ylabel('Throughput (documents per minute)')
        plt.grid(True)
        plt.savefig('throughput_vs_concurrency.png')
        print("Saved throughput vs concurrency plot to 'throughput_vs_concurrency.png'")
    except ImportError:
        print("Matplotlib not available, skipping plot generation")
    
    # Return the optimal configuration for use in other tests
    return optimal_result


@pytest.mark.parametrize("duration_minutes", [5, 15])
def test_sustained_throughput(ocr_service, test_document_ids, duration_minutes):
    """
    Test the throughput of the OCR service over an extended period.
    
    This test measures how the throughput changes over time during sustained
    processing, to identify any performance degradation.
    """
    # Get the optimal concurrency from the previous test
    optimal_config = test_optimal_concurrency(ocr_service, test_document_ids)
    optimal_concurrency = optimal_config["concurrent_requests"]
    
    # Calculate how many documents we need for the test duration
    # Assuming we can process at least 1 document per minute per worker
    estimated_docs_needed = optimal_concurrency * duration_minutes * 2  # 2x safety factor
    
    # Ensure we have enough test documents
    if len(test_document_ids) < estimated_docs_needed:
        pytest.skip(f"Not enough test documents for sustained test: need {estimated_docs_needed}, have {len(test_document_ids)}")
    
    doc_ids = test_document_ids[:estimated_docs_needed]
    
    # Split documents among workers
    worker_doc_ids = [doc_ids[i::optimal_concurrency] for i in range(optimal_concurrency)]
    
    # Function for worker to process documents with time tracking
    def worker_process(docs):
        results = []
        for doc_id in docs:
            start_time = time.time()
            ocr_service.process_document(doc_id)
            end_time = time.time()
            results.append({
                "doc_id": doc_id,
                "start_time": start_time,
                "end_time": end_time,
                "processing_time": end_time - start_time
            })
        return results
    
    # Process documents concurrently with time limit
    start_time = time.time()
    end_time_limit = start_time + (duration_minutes * 60)
    all_results = []
    
    # Track throughput over time in 1-minute intervals
    throughput_over_time = []
    interval_seconds = 60  # 1 minute intervals
    next_interval = start_time + interval_seconds
    
    with ThreadPoolExecutor(max_workers=optimal_concurrency) as executor:
        futures = [executor.submit(worker_process, docs) for docs in worker_doc_ids]
        
        # Monitor progress while workers are running
        while time.time() < end_time_limit and any(not f.done() for f in futures):
            # Sleep briefly to avoid busy waiting
            time.sleep(1)
            
            # Check if we've reached the next interval
            current_time = time.time()
            if current_time >= next_interval:
                # Collect results so far
                completed_results = []
                for f in futures:
                    if f.done():
                        completed_results.extend(f.result())
                
                # Calculate interval throughput
                interval_docs = len(completed_results)
                interval_elapsed = current_time - start_time
                interval_throughput = (interval_docs / interval_elapsed) * 60
                
                # Record throughput for this interval
                throughput_over_time.append({
                    "interval": len(throughput_over_time) + 1,
                    "elapsed_minutes": interval_elapsed / 60,
                    "documents_processed": interval_docs,
                    "throughput_per_minute": interval_throughput
                })
                
                # Log interval results
                print(f"Interval {len(throughput_over_time)}: "
                      f"{interval_throughput:.2f} docs/min "
                      f"({interval_docs} docs in {interval_elapsed:.2f} seconds)")
                
                # Set next interval
                next_interval = current_time + interval_seconds
        
        # Collect all results
        for future in futures:
            if future.done():
                all_results.extend(future.result())
    
    # Calculate final throughput metrics
    total_time = time.time() - start_time
    total_docs = len(all_results)
    overall_throughput = (total_docs / total_time) * 60
    
    # Calculate individual document processing times
    processing_times = [result["processing_time"] for result in all_results]
    avg_processing_time = np.mean(processing_times)
    max_processing_time = np.max(processing_times)
    
    # Log results
    print(f"Sustained test duration: {total_time/60:.2f} minutes")
    print(f"Total documents processed: {total_docs}")
    print(f"Average processing time per document: {avg_processing_time:.2f} seconds")
    print(f"Maximum processing time for a document: {max_processing_time:.2f} seconds")
    print(f"Overall throughput: {overall_throughput:.2f} documents per minute")
    
    # Check for throughput degradation over time
    if len(throughput_over_time) >= 2:
        initial_throughput = throughput_over_time[0]["throughput_per_minute"]
        final_throughput = throughput_over_time[-1]["throughput_per_minute"]
        throughput_change = (final_throughput / initial_throughput) - 1
        
        print(f"Initial throughput: {initial_throughput:.2f} docs/min")
        print(f"Final throughput: {final_throughput:.2f} docs/min")
        print(f"Throughput change: {throughput_change:.2%}")
        
        # Assert that throughput doesn't degrade significantly over time
        # Allow up to 20% degradation
        assert throughput_change >= -0.2, "Throughput degraded by more than 20% during sustained processing"
    
    # Assert that processing time meets requirements (under 5 minutes per document)
    assert max_processing_time < 300, "Maximum processing time exceeds 5 minutes requirement"
    
    # Plot throughput over time if matplotlib is available
    if throughput_over_time and len(throughput_over_time) >= 2:
        try:
            import matplotlib.pyplot as plt
            
            intervals = [r["interval"] for r in throughput_over_time]
            throughputs = [r["throughput_per_minute"] for r in throughput_over_time]
            
            plt.figure(figsize=(12, 6))
            plt.plot(intervals, throughputs, marker='o')
            plt.title(f'Throughput Over Time ({duration_minutes} minute test)')
            plt.xlabel('Interval (1 minute)')
            plt.ylabel('Throughput (documents per minute)')
            plt.grid(True)
            plt.savefig(f'sustained_throughput_{duration_minutes}min.png')
            print(f"Saved throughput over time plot to 'sustained_throughput_{duration_minutes}min.png'")
        except ImportError:
            print("Matplotlib not available, skipping plot generation")


@pytest.mark.parametrize("doc_type", ["application_form", "tax_return", "bank_statement", "invoice", "id_document"])
def test_document_type_throughput(ocr_service, test_document_ids, doc_type):
    """
    Test the throughput of processing different document types.
    
    This test measures how throughput varies across different document types,
    which may have different complexity and processing requirements.
    """
    # Get a subset of documents of the specified type
    # In a real test, we would filter by document type
    # Here we'll simulate by taking a subset
    doc_ids = test_document_ids[:20]
    
    # Process each document and measure the time
    processing_times = []
    for doc_id in doc_ids:
        start_time = time.time()
        # Simulate processing a specific document type
        ocr_service.process_document(doc_id, document_type=doc_type)
        end_time = time.time()
        processing_times.append(end_time - start_time)
    
    # Calculate throughput metrics
    avg_processing_time = np.mean(processing_times)
    throughput_per_minute = 60 / avg_processing_time
    
    # Log results
    print(f"Document type: {doc_type}")
    print(f"Average processing time: {avg_processing_time:.2f} seconds")
    print(f"Throughput: {throughput_per_minute:.2f} documents per minute")
    
    # Assert that processing time meets requirements (under 5 minutes per document)
    assert avg_processing_time < 300, f"Processing time for {doc_type} exceeds 5 minutes requirement"
    
    # Return results for comparison
    return {
        "document_type": doc_type,
        "avg_processing_time": avg_processing_time,
        "throughput_per_minute": throughput_per_minute
    }


def test_document_type_comparison(ocr_service, test_document_ids, document_types):
    """
    Test to compare throughput across different document types.
    
    This test identifies which document types have the highest and lowest
    throughput, which can help optimize processing strategies.
    """
    # Get throughput for each document type
    results = []
    for doc_type in document_types:
        result = test_document_type_throughput(ocr_service, test_document_ids, doc_type)
        results.append(result)
    
    # Find the fastest and slowest document types
    fastest = max(results, key=lambda x: x["throughput_per_minute"])
    slowest = min(results, key=lambda x: x["throughput_per_minute"])
    
    # Calculate the throughput range
    throughput_range = fastest["throughput_per_minute"] / slowest["throughput_per_minute"]
    
    # Log results
    print("\nDocument Type Throughput Comparison:")
    for result in sorted(results, key=lambda x: x["throughput_per_minute"], reverse=True):
        print(f"{result['document_type']}: {result['throughput_per_minute']:.2f} docs/min")
    
    print(f"\nFastest document type: {fastest['document_type']} "
          f"({fastest['throughput_per_minute']:.2f} docs/min)")
    print(f"Slowest document type: {slowest['document_type']} "
          f"({slowest['throughput_per_minute']:.2f} docs/min)")
    print(f"Throughput range: {throughput_range:.2f}x")
    
    # Plot document type comparison if matplotlib is available
    try:
        import matplotlib.pyplot as plt
        
        doc_types = [r["document_type"] for r in results]
        throughputs = [r["throughput_per_minute"] for r in results]
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(doc_types, throughputs)
        plt.title('Throughput by Document Type')
        plt.xlabel('Document Type')
        plt.ylabel('Throughput (documents per minute)')
        plt.grid(True, axis='y')
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.2f}', ha='center', va='bottom')
        
        plt.savefig('throughput_by_document_type.png')
        print("Saved document type comparison plot to 'throughput_by_document_type.png'")
    except ImportError:
        print("Matplotlib not available, skipping plot generation")


def test_business_requirements_compliance(ocr_service, test_document_ids):
    """
    Test that the OCR service meets the business requirements for throughput.
    
    This test verifies that the service can process applications in under 5 minutes
    and achieve a 93% reduction in manual processing through automation.
    """
    # Get the optimal concurrency and throughput
    optimal_config = test_optimal_concurrency(ocr_service, test_document_ids)
    optimal_throughput = optimal_config["throughput_per_minute"]
    
    # Calculate daily throughput (assuming 8-hour workday)
    daily_throughput = optimal_throughput * 60 * 8
    
    # Log results
    print(f"Optimal throughput: {optimal_throughput:.2f} documents per minute")
    print(f"Projected daily throughput (8-hour day): {daily_throughput:.0f} documents")
    
    # Business requirements:
    # 1. Process applications in under 5 minutes
    avg_processing_time = optimal_config["avg_processing_time"]
    assert avg_processing_time < 300, "Average processing time exceeds 5 minutes requirement"
    print(f"Requirement 1: Process applications in under 5 minutes - PASSED ({avg_processing_time:.2f} seconds)")
    
    # 2. Achieve 93% reduction in manual processing through automation
    # To verify this, we would need to know the baseline manual processing rate
    # For this test, we'll assume a baseline of 5 minutes per document manually
    manual_processing_time = 300  # 5 minutes in seconds
    automation_time_savings = (manual_processing_time - avg_processing_time) / manual_processing_time
    assert automation_time_savings >= 0.93, "Does not achieve 93% reduction in processing time"
    print(f"Requirement 2: Achieve 93% reduction in manual processing - "
          f"PASSED ({automation_time_savings:.2%} reduction)")
    
    # Additional business metrics
    print(f"\nAdditional Business Metrics:")
    print(f"Time savings per document: {manual_processing_time - avg_processing_time:.2f} seconds")
    print(f"Processing time reduction: {automation_time_savings:.2%}")
    print(f"Documents processed per hour: {optimal_throughput * 60:.0f}")
    print(f"Documents processed per day (8-hour day): {daily_throughput:.0f}")
    
    # Return the compliance results
    return {
        "meets_processing_time": avg_processing_time < 300,
        "meets_automation_reduction": automation_time_savings >= 0.93,
        "processing_time_seconds": avg_processing_time,
        "automation_reduction": automation_time_savings,
        "throughput_per_minute": optimal_throughput,
        "daily_throughput": daily_throughput
    }


if __name__ == "__main__":
    # This allows running the tests directly with python -m pytest
    pytest.main(['-xvs', __file__])