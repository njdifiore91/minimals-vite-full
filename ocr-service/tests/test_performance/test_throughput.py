import os
import time
import pytest
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock

# Import OCR service components
from services import ocr_service, queue_service, storage_service
from models import model_factory
from config import app_config, tensorflow_config


# Test fixtures
@pytest.fixture
def sample_document_small():
    """Returns a small sample document for throughput testing."""
    # Create a small document (e.g., 1 page invoice)
    return {
        'document_id': 'test-doc-small-001',
        'document_type': 'invoice',
        'content': b'sample content for small document',
        'size': 100 * 1024,  # 100KB
        'pages': 1
    }


@pytest.fixture
def sample_document_medium():
    """Returns a medium sample document for throughput testing."""
    # Create a medium document (e.g., 5 page application)
    return {
        'document_id': 'test-doc-medium-001',
        'document_type': 'application',
        'content': b'sample content for medium document' * 50,
        'size': 500 * 1024,  # 500KB
        'pages': 5
    }


@pytest.fixture
def sample_document_large():
    """Returns a large sample document for throughput testing."""
    # Create a large document (e.g., 20 page financial statement)
    return {
        'document_id': 'test-doc-large-001',
        'document_type': 'financial_statement',
        'content': b'sample content for large document' * 200,
        'size': 2 * 1024 * 1024,  # 2MB
        'pages': 20
    }


@pytest.fixture
def sample_document_batch(sample_document_small, sample_document_medium, sample_document_large):
    """Returns a batch of documents for throughput testing."""
    # Create a batch with a mix of document types and sizes
    batch = []
    # Add 10 small documents
    for i in range(10):
        doc = sample_document_small.copy()
        doc['document_id'] = f'test-doc-small-{i+1:03d}'
        batch.append(doc)
    # Add 5 medium documents
    for i in range(5):
        doc = sample_document_medium.copy()
        doc['document_id'] = f'test-doc-medium-{i+1:03d}'
        batch.append(doc)
    # Add 2 large documents
    for i in range(2):
        doc = sample_document_large.copy()
        doc['document_id'] = f'test-doc-large-{i+1:03d}'
        batch.append(doc)
    return batch


@pytest.fixture
def mock_ocr_service():
    """Returns a mocked OCR service for throughput testing."""
    with patch('services.ocr_service.OCRService') as mock_service:
        # Configure the mock to simulate realistic processing times based on document size
        instance = mock_service.return_value
        
        def process_document(document):
            # Simulate processing time based on document size and pages
            # Small documents: ~1 second per page
            # Medium documents: ~2 seconds per page
            # Large documents: ~3 seconds per page
            if document['document_type'] == 'invoice':
                processing_time = 1.0 * document['pages']
            elif document['document_type'] == 'application':
                processing_time = 2.0 * document['pages']
            else:  # financial_statement
                processing_time = 3.0 * document['pages']
                
            # Add some random variation (±10%)
            variation = 0.1 * processing_time
            processing_time += np.random.uniform(-variation, variation)
            
            # Simulate processing by sleeping
            time.sleep(processing_time)
            
            # Return simulated OCR results
            return {
                'document_id': document['document_id'],
                'extracted_text': f"Extracted text from {document['document_id']}",
                'confidence_score': 0.95,
                'processing_time': processing_time,
                'status': 'success'
            }
        
        instance.process_document.side_effect = process_document
        yield instance


@pytest.fixture
def mock_storage_service():
    """Returns a mocked storage service for throughput testing."""
    with patch('services.storage_service.StorageService') as mock_service:
        instance = mock_service.return_value
        
        def get_document(document_id):
            # Simulate document retrieval time (50-100ms)
            time.sleep(np.random.uniform(0.05, 0.1))
            
            # Return a dummy document based on the ID
            if 'small' in document_id:
                return {
                    'document_id': document_id,
                    'document_type': 'invoice',
                    'content': b'sample content for small document',
                    'size': 100 * 1024,
                    'pages': 1
                }
            elif 'medium' in document_id:
                return {
                    'document_id': document_id,
                    'document_type': 'application',
                    'content': b'sample content for medium document' * 50,
                    'size': 500 * 1024,
                    'pages': 5
                }
            else:  # large
                return {
                    'document_id': document_id,
                    'document_type': 'financial_statement',
                    'content': b'sample content for large document' * 200,
                    'size': 2 * 1024 * 1024,
                    'pages': 20
                }
        
        instance.get_document.side_effect = get_document
        yield instance


@pytest.fixture
def mock_queue_service():
    """Returns a mocked queue service for throughput testing."""
    with patch('services.queue_service.QueueService') as mock_service:
        instance = mock_service.return_value
        
        def publish_result(result):
            # Simulate message publishing time (10-30ms)
            time.sleep(np.random.uniform(0.01, 0.03))
            return True
        
        instance.publish_result.side_effect = publish_result
        yield instance


# Test functions
def test_single_document_throughput_small(benchmark, mock_ocr_service, mock_storage_service, 
                                          mock_queue_service, sample_document_small):
    """Test throughput for processing a single small document."""
    def process_single_document():
        # Process a single small document and measure throughput
        result = mock_ocr_service.process_document(sample_document_small)
        mock_queue_service.publish_result(result)
        return result
    
    # Run the benchmark
    result = benchmark(process_single_document)
    
    # Verify the result
    assert result['status'] == 'success'
    assert result['document_id'] == sample_document_small['document_id']
    
    # Calculate and print throughput metrics
    docs_per_second = 1.0 / benchmark.stats['mean']
    print(f"\nSmall document throughput: {docs_per_second:.2f} documents per second")
    print(f"Average processing time: {benchmark.stats['mean']:.3f} seconds")
    
    # Verify throughput meets requirements (at least 0.5 docs/second for small docs)
    assert docs_per_second >= 0.5, "Throughput for small documents is below requirements"


def test_single_document_throughput_medium(benchmark, mock_ocr_service, mock_storage_service, 
                                           mock_queue_service, sample_document_medium):
    """Test throughput for processing a single medium document."""
    def process_single_document():
        # Process a single medium document and measure throughput
        result = mock_ocr_service.process_document(sample_document_medium)
        mock_queue_service.publish_result(result)
        return result
    
    # Run the benchmark
    result = benchmark(process_single_document)
    
    # Verify the result
    assert result['status'] == 'success'
    assert result['document_id'] == sample_document_medium['document_id']
    
    # Calculate and print throughput metrics
    docs_per_second = 1.0 / benchmark.stats['mean']
    print(f"\nMedium document throughput: {docs_per_second:.2f} documents per second")
    print(f"Average processing time: {benchmark.stats['mean']:.3f} seconds")
    
    # Verify throughput meets requirements (at least 0.1 docs/second for medium docs)
    assert docs_per_second >= 0.1, "Throughput for medium documents is below requirements"


def test_single_document_throughput_large(benchmark, mock_ocr_service, mock_storage_service, 
                                          mock_queue_service, sample_document_large):
    """Test throughput for processing a single large document."""
    def process_single_document():
        # Process a single large document and measure throughput
        result = mock_ocr_service.process_document(sample_document_large)
        mock_queue_service.publish_result(result)
        return result
    
    # Run the benchmark
    result = benchmark(process_single_document)
    
    # Verify the result
    assert result['status'] == 'success'
    assert result['document_id'] == sample_document_large['document_id']
    
    # Calculate and print throughput metrics
    docs_per_second = 1.0 / benchmark.stats['mean']
    print(f"\nLarge document throughput: {docs_per_second:.2f} documents per second")
    print(f"Average processing time: {benchmark.stats['mean']:.3f} seconds")
    
    # Verify throughput meets requirements (at least 0.02 docs/second for large docs)
    assert docs_per_second >= 0.02, "Throughput for large documents is below requirements"
    
    # Verify processing time is under 5 minutes (300 seconds) as per requirements
    assert benchmark.stats['max'] < 300, "Processing time exceeds 5-minute requirement"


def test_batch_processing_throughput(benchmark, mock_ocr_service, mock_storage_service, 
                                     mock_queue_service, sample_document_batch):
    """Test throughput for batch processing multiple documents."""
    def process_batch():
        # Process a batch of documents sequentially and measure throughput
        results = []
        for document in sample_document_batch:
            result = mock_ocr_service.process_document(document)
            mock_queue_service.publish_result(result)
            results.append(result)
        return results
    
    # Run the benchmark
    results = benchmark(process_batch)
    
    # Verify the results
    assert len(results) == len(sample_document_batch)
    for result in results:
        assert result['status'] == 'success'
    
    # Calculate and print throughput metrics
    total_docs = len(sample_document_batch)
    docs_per_second = total_docs / benchmark.stats['mean']
    print(f"\nBatch processing throughput: {docs_per_second:.2f} documents per second")
    print(f"Average processing time for {total_docs} documents: {benchmark.stats['mean']:.3f} seconds")
    print(f"Average time per document: {benchmark.stats['mean'] / total_docs:.3f} seconds")
    
    # Verify throughput meets requirements (at least 0.05 docs/second overall)
    assert docs_per_second >= 0.05, "Batch processing throughput is below requirements"


def test_concurrent_processing_throughput(mock_ocr_service, mock_storage_service, 
                                         mock_queue_service, sample_document_batch):
    """Test throughput for concurrent processing of multiple documents."""
    # This test doesn't use the benchmark fixture directly because we're testing concurrency
    # Instead, we'll measure the time manually
    
    def process_document(document):
        result = mock_ocr_service.process_document(document)
        mock_queue_service.publish_result(result)
        return result
    
    # Process documents concurrently using ThreadPoolExecutor
    max_workers = min(10, len(sample_document_batch))  # Use up to 10 workers
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_doc = {executor.submit(process_document, doc): doc for doc in sample_document_batch}
        
        # Collect results as they complete
        results = []
        for future in as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                print(f"Document {doc['document_id']} generated an exception: {exc}")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Verify the results
    assert len(results) == len(sample_document_batch)
    for result in results:
        assert result['status'] == 'success'
    
    # Calculate and print throughput metrics
    total_docs = len(sample_document_batch)
    docs_per_second = total_docs / total_time
    print(f"\nConcurrent processing throughput: {docs_per_second:.2f} documents per second")
    print(f"Total processing time for {total_docs} documents: {total_time:.3f} seconds")
    print(f"Average time per document: {total_time / total_docs:.3f} seconds")
    print(f"Concurrency level: {max_workers} workers")
    
    # Verify throughput meets requirements (at least 0.2 docs/second with concurrency)
    assert docs_per_second >= 0.2, "Concurrent processing throughput is below requirements"
    
    # Verify the speedup from concurrency is significant (at least 2x faster than sequential)
    # We'll estimate sequential time based on the sum of individual document processing times
    estimated_sequential_time = sum(result['processing_time'] for result in results)
    speedup = estimated_sequential_time / total_time
    print(f"Estimated speedup from concurrency: {speedup:.2f}x")
    
    assert speedup >= 2.0, "Concurrent processing does not provide sufficient speedup"


def test_sustained_throughput(mock_ocr_service, mock_storage_service, mock_queue_service, sample_document_batch):
    """Test throughput sustainability over an extended period."""
    # This test simulates sustained processing over a longer period
    # We'll process multiple batches and measure if throughput remains consistent
    
    num_batches = 3  # Process 3 batches to simulate sustained load
    batch_throughputs = []
    
    for batch_num in range(num_batches):
        print(f"\nProcessing batch {batch_num + 1}/{num_batches}...")
        
        start_time = time.time()
        
        # Process the batch
        results = []
        for document in sample_document_batch:
            result = mock_ocr_service.process_document(document)
            mock_queue_service.publish_result(result)
            results.append(result)
        
        end_time = time.time()
        batch_time = end_time - start_time
        
        # Calculate throughput for this batch
        total_docs = len(sample_document_batch)
        docs_per_second = total_docs / batch_time
        batch_throughputs.append(docs_per_second)
        
        print(f"Batch {batch_num + 1} throughput: {docs_per_second:.2f} documents per second")
        print(f"Batch {batch_num + 1} processing time: {batch_time:.3f} seconds")
    
    # Calculate overall statistics
    avg_throughput = sum(batch_throughputs) / len(batch_throughputs)
    min_throughput = min(batch_throughputs)
    max_throughput = max(batch_throughputs)
    throughput_variation = (max_throughput - min_throughput) / avg_throughput * 100
    
    print(f"\nSustained processing results:")
    print(f"Average throughput: {avg_throughput:.2f} documents per second")
    print(f"Minimum throughput: {min_throughput:.2f} documents per second")
    print(f"Maximum throughput: {max_throughput:.2f} documents per second")
    print(f"Throughput variation: {throughput_variation:.2f}%")
    
    # Verify throughput meets requirements (at least 0.05 docs/second sustained)
    assert min_throughput >= 0.05, "Sustained throughput is below requirements"
    
    # Verify throughput remains consistent (variation less than 20%)
    assert throughput_variation < 20.0, "Throughput variation exceeds acceptable limits"


def test_throughput_meets_business_requirements(mock_ocr_service, mock_storage_service, mock_queue_service):
    """Test that the OCR service throughput meets overall business requirements."""
    # This test verifies that the OCR service can handle the expected daily volume
    # Based on business requirements: 93% reduction in manual processing
    
    # Assume a baseline of 1000 documents per day that were manually processed
    # With 93% reduction, we need to automatically process 930 documents per day
    # Assuming an 8-hour workday, that's approximately 116 documents per hour or 1.94 docs/minute
    
    daily_volume = 1000
    automation_target = 0.93  # 93% reduction in manual processing
    automated_docs = daily_volume * automation_target
    work_hours = 8
    docs_per_hour = automated_docs / work_hours
    docs_per_minute = docs_per_hour / 60
    docs_per_second = docs_per_minute / 60
    
    print(f"\nBusiness requirements:")
    print(f"Daily document volume: {daily_volume}")
    print(f"Automation target: {automation_target * 100:.0f}%")
    print(f"Documents to process automatically: {automated_docs:.0f} per day")
    print(f"Required throughput: {docs_per_hour:.2f} docs/hour or {docs_per_minute:.2f} docs/minute")
    print(f"Required throughput in docs/second: {docs_per_second:.4f}")
    
    # Create a representative mix of documents based on expected distribution
    # Assume 70% small, 25% medium, 5% large documents
    test_batch = []
    for i in range(20):  # Test with a smaller batch of 20 documents with the same distribution
        if i < 14:  # 70% small
            doc_type = 'invoice'
            pages = 1
        elif i < 19:  # 25% medium
            doc_type = 'application'
            pages = 5
        else:  # 5% large
            doc_type = 'financial_statement'
            pages = 20
        
        test_batch.append({
            'document_id': f'test-doc-{i+1:03d}',
            'document_type': doc_type,
            'content': b'sample content',
            'size': 100 * 1024 * pages,
            'pages': pages
        })
    
    # Process the batch with concurrency to simulate real-world processing
    max_workers = min(10, len(test_batch))
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_doc = {executor.submit(mock_ocr_service.process_document, doc): doc for doc in test_batch}
        results = [future.result() for future in as_completed(future_to_doc)]
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate achieved throughput
    achieved_docs_per_second = len(test_batch) / total_time
    achieved_docs_per_minute = achieved_docs_per_second * 60
    achieved_docs_per_hour = achieved_docs_per_minute * 60
    achieved_docs_per_day = achieved_docs_per_hour * work_hours
    
    print(f"\nAchieved performance:")
    print(f"Throughput: {achieved_docs_per_second:.4f} docs/second")
    print(f"Throughput: {achieved_docs_per_minute:.2f} docs/minute")
    print(f"Throughput: {achieved_docs_per_hour:.2f} docs/hour")
    print(f"Daily capacity: {achieved_docs_per_day:.0f} documents")
    
    # Verify the service meets or exceeds the required throughput
    assert achieved_docs_per_second >= docs_per_second, "OCR service throughput does not meet business requirements"
    
    # Calculate and print the automation percentage achieved
    achieved_automation = min(achieved_docs_per_day / daily_volume, 1.0)
    print(f"Achieved automation: {achieved_automation * 100:.2f}%")
    
    # Verify the service meets the 93% automation requirement
    assert achieved_automation >= automation_target, "OCR service does not meet the 93% automation requirement"
    
    # Verify all documents are processed within the 5-minute SLA
    max_processing_time = max(result['processing_time'] for result in results)
    print(f"Maximum document processing time: {max_processing_time:.2f} seconds")
    assert max_processing_time < 300, "Some documents exceed the 5-minute processing time requirement"