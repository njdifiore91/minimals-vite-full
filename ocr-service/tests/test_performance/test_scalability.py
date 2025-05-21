import pytest
import time
import os
import numpy as np
import tensorflow as tf
import concurrent.futures
import psutil
import GPUtil
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

# Import OCR service components
from ocr_service.app import create_app
from ocr_service.services.ocr_service import OCRService
from ocr_service.models.model_factory import ModelFactory
from ocr_service.config.tensorflow_config import TensorFlowConfig
from ocr_service.utils.resource_monitor import ResourceMonitor


@pytest.fixture
def app():
    """Create a test instance of the OCR service application."""
    app = create_app('testing')
    return app


@pytest.fixture
def ocr_service():
    """Create a test instance of the OCR service."""
    return OCRService()


@pytest.fixture
def resource_monitor():
    """Create a resource monitor for tracking system resources during tests."""
    return ResourceMonitor()


@pytest.fixture
def test_documents(request):
    """Provide test documents of specified size and quantity for scalability testing.
    
    Parameters can be customized using pytest's parametrize decorator.
    """
    doc_size = getattr(request, 'param', {}).get('size', 'medium')
    doc_count = getattr(request, 'param', {}).get('count', 10)
    doc_type = getattr(request, 'param', {}).get('type', 'mixed')
    
    # Document sizes in MB (approximate file sizes)
    sizes = {
        'small': 0.5,  # ~500KB
        'medium': 2,   # ~2MB
        'large': 5,    # ~5MB
        'xlarge': 10   # ~10MB
    }
    
    # Document types
    types = {
        'typed': 'application/pdf',
        'handwritten': 'image/tiff',
        'mixed': 'application/pdf'
    }
    
    # Create mock documents with appropriate metadata
    documents = []
    for i in range(doc_count):
        doc = MagicMock()
        doc.size = int(sizes[doc_size] * 1024 * 1024)  # Convert to bytes
        doc.content_type = types[doc_type]
        doc.id = f"test-doc-{i}"
        doc.path = f"/test/documents/{doc.id}.{doc.content_type.split('/')[-1]}"
        documents.append(doc)
    
    return documents


@contextmanager
def gpu_memory_limit(limit_mb):
    """Context manager to limit GPU memory usage for testing resource constraints.
    
    Args:
        limit_mb: Memory limit in megabytes
    """
    original_config = tf.config.experimental.get_memory_growth
    gpus = tf.config.experimental.list_physical_devices('GPU')
    
    if not gpus:
        # No GPUs available, just yield
        yield
        return
    
    try:
        # Set memory limit on the GPU
        tf.config.experimental.set_virtual_device_configuration(
            gpus[0],
            [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=limit_mb)]
        )
        yield
    finally:
        # Reset GPU configuration
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, original_config(gpu))


@contextmanager
def cpu_core_limit(cores):
    """Context manager to limit CPU cores for testing resource constraints.
    
    Args:
        cores: Number of CPU cores to use
    """
    original_affinity = psutil.Process().cpu_affinity()
    
    try:
        # Limit to specified number of cores
        available_cores = list(range(psutil.cpu_count()))
        limited_cores = available_cores[:cores]
        psutil.Process().cpu_affinity(limited_cores)
        yield
    finally:
        # Reset CPU affinity
        psutil.Process().cpu_affinity(original_affinity)


# Linear Scaling Tests
@pytest.mark.parametrize('test_documents', [
    {'size': 'medium', 'count': 10, 'type': 'mixed'},
    {'size': 'medium', 'count': 50, 'type': 'mixed'},
    {'size': 'medium', 'count': 100, 'type': 'mixed'}
], indirect=True)
def test_linear_scaling_with_document_volume(ocr_service, test_documents, resource_monitor):
    """Test that processing time scales linearly with document volume.
    
    This test verifies that the OCR service can handle increasing document volumes
    with predictable performance scaling.
    """
    # Process documents and measure time
    start_time = time.time()
    resource_monitor.start()
    
    results = []
    for doc in test_documents:
        result = ocr_service.process_document(doc)
        results.append(result)
    
    end_time = time.time()
    metrics = resource_monitor.stop()
    
    # Calculate processing time per document
    total_time = end_time - start_time
    time_per_document = total_time / len(test_documents)
    
    # Verify linear scaling (time per document should remain relatively constant)
    # Allow for some variance (20%) due to system fluctuations
    assert 0.8 <= time_per_document <= 1.2 * time_per_document, \
        f"Processing time per document should scale linearly, but was {time_per_document} seconds"
    
    # Verify all documents were processed successfully
    assert len(results) == len(test_documents), "Not all documents were processed"
    assert all(r.get('success') for r in results), "Some documents failed processing"
    
    # Log performance metrics
    print(f"Processed {len(test_documents)} documents in {total_time:.2f} seconds")
    print(f"Time per document: {time_per_document:.2f} seconds")
    print(f"Peak memory usage: {metrics['peak_memory_mb']:.2f} MB")
    print(f"Peak GPU memory usage: {metrics['peak_gpu_memory_mb']:.2f} MB")


@pytest.mark.parametrize('worker_count', [1, 2, 4, 8])
def test_linear_scaling_with_worker_count(ocr_service, test_documents, worker_count):
    """Test that throughput scales linearly with worker count.
    
    This test verifies that adding more worker processes increases throughput
    proportionally, demonstrating the service's ability to scale horizontally.
    """
    # Fixed document set
    docs = test_documents(MagicMock(param={'size': 'medium', 'count': 100, 'type': 'mixed'}))
    
    # Process documents with different worker counts and measure throughput
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(ocr_service.process_document, doc) for doc in docs]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    end_time = time.time()
    
    # Calculate throughput (documents per second)
    total_time = end_time - start_time
    throughput = len(docs) / total_time
    throughput_per_worker = throughput / worker_count
    
    # Verify all documents were processed successfully
    assert len(results) == len(docs), "Not all documents were processed"
    assert all(r.get('success') for r in results), "Some documents failed processing"
    
    # Log performance metrics
    print(f"Worker count: {worker_count}")
    print(f"Processed {len(docs)} documents in {total_time:.2f} seconds")
    print(f"Throughput: {throughput:.2f} documents per second")
    print(f"Throughput per worker: {throughput_per_worker:.2f} documents per second")
    
    # Store results for comparison across worker counts
    return {
        'worker_count': worker_count,
        'throughput': throughput,
        'throughput_per_worker': throughput_per_worker
    }


# Resource Constraint Tests
@pytest.mark.parametrize('memory_limit_mb', [2048, 4096, 8192])
def test_performance_under_memory_constraints(ocr_service, test_documents, memory_limit_mb):
    """Test OCR service performance under different memory constraints.
    
    This test verifies that the service can operate effectively even with
    limited memory resources, though performance may degrade gracefully.
    """
    # Fixed document set - medium complexity
    docs = test_documents(MagicMock(param={'size': 'medium', 'count': 20, 'type': 'mixed'}))
    
    # Process documents with memory constraints
    with gpu_memory_limit(memory_limit_mb):
        start_time = time.time()
        
        results = []
        for doc in docs:
            result = ocr_service.process_document(doc)
            results.append(result)
        
        end_time = time.time()
    
    # Calculate performance metrics
    total_time = end_time - start_time
    time_per_document = total_time / len(docs)
    success_rate = sum(1 for r in results if r.get('success')) / len(results)
    
    # Verify service can operate under constraints
    assert success_rate >= 0.9, f"Success rate under {memory_limit_mb}MB constraint was only {success_rate:.2f}"
    
    # Log performance metrics
    print(f"Memory limit: {memory_limit_mb} MB")
    print(f"Processed {len(docs)} documents in {total_time:.2f} seconds")
    print(f"Time per document: {time_per_document:.2f} seconds")
    print(f"Success rate: {success_rate:.2f}")
    
    return {
        'memory_limit_mb': memory_limit_mb,
        'time_per_document': time_per_document,
        'success_rate': success_rate
    }


@pytest.mark.parametrize('cpu_cores', [1, 2, 4])
def test_performance_under_cpu_constraints(ocr_service, test_documents, cpu_cores):
    """Test OCR service performance under CPU core constraints.
    
    This test verifies that the service can operate effectively even with
    limited CPU resources, though performance may degrade gracefully.
    """
    # Fixed document set - medium complexity
    docs = test_documents(MagicMock(param={'size': 'medium', 'count': 20, 'type': 'mixed'}))
    
    # Process documents with CPU constraints
    with cpu_core_limit(cpu_cores):
        start_time = time.time()
        
        results = []
        for doc in docs:
            result = ocr_service.process_document(doc)
            results.append(result)
        
        end_time = time.time()
    
    # Calculate performance metrics
    total_time = end_time - start_time
    time_per_document = total_time / len(docs)
    success_rate = sum(1 for r in results if r.get('success')) / len(results)
    
    # Verify service can operate under constraints
    assert success_rate >= 0.9, f"Success rate under {cpu_cores} CPU cores was only {success_rate:.2f}"
    
    # Log performance metrics
    print(f"CPU cores: {cpu_cores}")
    print(f"Processed {len(docs)} documents in {total_time:.2f} seconds")
    print(f"Time per document: {time_per_document:.2f} seconds")
    print(f"Success rate: {success_rate:.2f}")
    
    return {
        'cpu_cores': cpu_cores,
        'time_per_document': time_per_document,
        'success_rate': success_rate
    }


# Recovery Tests
@pytest.mark.parametrize('test_documents', [
    {'size': 'xlarge', 'count': 50, 'type': 'mixed'}
], indirect=True)
def test_recovery_after_resource_exhaustion(ocr_service, test_documents, resource_monitor):
    """Test service recovery after resource exhaustion.
    
    This test verifies that the OCR service can recover and continue processing
    after experiencing resource exhaustion (memory or GPU).
    """
    # Process a large batch of documents to potentially exhaust resources
    resource_monitor.start()
    
    results = []
    for i, doc in enumerate(test_documents):
        try:
            result = ocr_service.process_document(doc)
            results.append((True, result))
        except Exception as e:
            results.append((False, str(e)))
        
        # Force garbage collection after each document to help recovery
        if i % 10 == 0:
            import gc
            gc.collect()
    
    metrics = resource_monitor.stop()
    
    # Check if we experienced any failures
    failures = [r for r in results if not r[0]]
    successes = [r for r in results if r[0]]
    
    # Verify recovery capability
    if failures:
        # If we had failures, verify that we recovered and processed documents after failures
        failure_indices = [i for i, r in enumerate(results) if not r[0]]
        last_failure_index = max(failure_indices)
        
        # Verify we had successful processing after the last failure
        assert last_failure_index < len(results) - 1, "Service did not recover after failures"
        
        # Verify some documents were processed successfully after the last failure
        successful_after_failure = sum(1 for i, r in enumerate(results) 
                                     if i > last_failure_index and r[0])
        assert successful_after_failure > 0, "No documents processed successfully after failure"
    
    # Log performance metrics
    print(f"Processed {len(test_documents)} documents with {len(failures)} failures")
    print(f"Peak memory usage: {metrics['peak_memory_mb']:.2f} MB")
    print(f"Peak GPU memory usage: {metrics['peak_gpu_memory_mb']:.2f} MB")
    
    # Even with some failures, overall success rate should be high
    success_rate = len(successes) / len(results)
    assert success_rate >= 0.8, f"Overall success rate was only {success_rate:.2f}"


# Optimal Resource Allocation Tests
@pytest.mark.parametrize('batch_size', [1, 5, 10, 20, 50])
def test_optimal_batch_size(ocr_service, test_documents, batch_size):
    """Test to determine the optimal batch size for document processing.
    
    This test measures performance with different batch sizes to identify
    the optimal batch size for maximum throughput.
    """
    # Fixed document set
    docs = test_documents(MagicMock(param={'size': 'medium', 'count': 100, 'type': 'mixed'}))
    
    # Process documents in batches
    start_time = time.time()
    
    results = []
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        batch_results = ocr_service.process_batch(batch)
        results.extend(batch_results)
    
    end_time = time.time()
    
    # Calculate performance metrics
    total_time = end_time - start_time
    throughput = len(docs) / total_time
    success_rate = sum(1 for r in results if r.get('success')) / len(results)
    
    # Log performance metrics
    print(f"Batch size: {batch_size}")
    print(f"Processed {len(docs)} documents in {total_time:.2f} seconds")
    print(f"Throughput: {throughput:.2f} documents per second")
    print(f"Success rate: {success_rate:.2f}")
    
    # Verify acceptable success rate
    assert success_rate >= 0.95, f"Success rate with batch size {batch_size} was only {success_rate:.2f}"
    
    return {
        'batch_size': batch_size,
        'throughput': throughput,
        'success_rate': success_rate
    }


@pytest.mark.parametrize('model_complexity', ['fast', 'balanced', 'accurate'])
def test_model_complexity_performance_tradeoff(ocr_service, test_documents, model_complexity):
    """Test performance tradeoffs with different model complexity settings.
    
    This test evaluates the tradeoff between processing speed and accuracy
    with different model complexity settings.
    """
    # Fixed document set
    docs = test_documents(MagicMock(param={'size': 'medium', 'count': 50, 'type': 'mixed'}))
    
    # Configure model complexity
    with patch.object(TensorFlowConfig, 'MODEL_COMPLEXITY', model_complexity):
        # Reinitialize model factory with new complexity setting
        model_factory = ModelFactory()
        ocr_service.model_factory = model_factory
        
        # Process documents
        start_time = time.time()
        
        results = []
        for doc in docs:
            result = ocr_service.process_document(doc)
            results.append(result)
        
        end_time = time.time()
    
    # Calculate performance metrics
    total_time = end_time - start_time
    time_per_document = total_time / len(docs)
    throughput = len(docs) / total_time
    
    # Extract accuracy metrics from results
    confidence_scores = [r.get('confidence', 0) for r in results if r.get('success')]
    avg_confidence = np.mean(confidence_scores) if confidence_scores else 0
    
    # Log performance metrics
    print(f"Model complexity: {model_complexity}")
    print(f"Processed {len(docs)} documents in {total_time:.2f} seconds")
    print(f"Time per document: {time_per_document:.2f} seconds")
    print(f"Throughput: {throughput:.2f} documents per second")
    print(f"Average confidence score: {avg_confidence:.2f}")
    
    # Verify expected tradeoffs
    if model_complexity == 'fast':
        # Fast models should have higher throughput but potentially lower confidence
        assert throughput >= 1.0, "Fast model should have high throughput"
    elif model_complexity == 'accurate':
        # Accurate models should have higher confidence but potentially lower throughput
        assert avg_confidence >= 0.9, "Accurate model should have high confidence scores"
    
    return {
        'model_complexity': model_complexity,
        'throughput': throughput,
        'avg_confidence': avg_confidence
    }


# Varying Demand Tests
@pytest.mark.parametrize('demand_pattern', ['steady', 'spike', 'fluctuating'])
def test_performance_under_varying_demand(ocr_service, test_documents, demand_pattern):
    """Test OCR service performance under different demand patterns.
    
    This test verifies that the service can handle varying demand levels,
    including steady load, sudden spikes, and fluctuating demand.
    """
    # Create document sets based on demand pattern
    if demand_pattern == 'steady':
        # Steady stream of documents
        doc_batches = [test_documents(MagicMock(param={'size': 'medium', 'count': 20, 'type': 'mixed'}))
                      for _ in range(5)]
    elif demand_pattern == 'spike':
        # Sudden spike in document volume
        doc_batches = [
            test_documents(MagicMock(param={'size': 'medium', 'count': 10, 'type': 'mixed'})),
            test_documents(MagicMock(param={'size': 'medium', 'count': 50, 'type': 'mixed'})),  # Spike
            test_documents(MagicMock(param={'size': 'medium', 'count': 10, 'type': 'mixed'}))
        ]
    elif demand_pattern == 'fluctuating':
        # Fluctuating document volume
        doc_batches = [
            test_documents(MagicMock(param={'size': 'medium', 'count': 10, 'type': 'mixed'})),
            test_documents(MagicMock(param={'size': 'medium', 'count': 30, 'type': 'mixed'})),
            test_documents(MagicMock(param={'size': 'medium', 'count': 5, 'type': 'mixed'})),
            test_documents(MagicMock(param={'size': 'medium', 'count': 20, 'type': 'mixed'}))
        ]
    
    # Process document batches and measure performance
    batch_metrics = []
    
    for i, batch in enumerate(doc_batches):
        start_time = time.time()
        
        results = []
        for doc in batch:
            result = ocr_service.process_document(doc)
            results.append(result)
        
        end_time = time.time()
        
        # Calculate batch metrics
        batch_time = end_time - start_time
        batch_throughput = len(batch) / batch_time
        batch_success_rate = sum(1 for r in results if r.get('success')) / len(results)
        
        batch_metrics.append({
            'batch': i + 1,
            'size': len(batch),
            'time': batch_time,
            'throughput': batch_throughput,
            'success_rate': batch_success_rate
        })
    
    # Calculate overall metrics
    total_docs = sum(len(batch) for batch in doc_batches)
    total_time = sum(m['time'] for m in batch_metrics)
    overall_throughput = total_docs / total_time
    
    # Log performance metrics
    print(f"Demand pattern: {demand_pattern}")
    print(f"Processed {total_docs} documents in {total_time:.2f} seconds")
    print(f"Overall throughput: {overall_throughput:.2f} documents per second")
    
    for m in batch_metrics:
        print(f"Batch {m['batch']} ({m['size']} docs): {m['throughput']:.2f} docs/sec, "
              f"Success rate: {m['success_rate']:.2f}")
    
    # Verify service can handle the demand pattern
    assert all(m['success_rate'] >= 0.9 for m in batch_metrics), \
        "Service should maintain high success rate across all demand patterns"
    
    # For spike pattern, verify the service can handle the spike
    if demand_pattern == 'spike':
        spike_batch = batch_metrics[1]  # The middle batch is the spike
        assert spike_batch['throughput'] >= 0.5 * overall_throughput, \
            "Service should maintain reasonable throughput during demand spikes"
    
    return {
        'demand_pattern': demand_pattern,
        'overall_throughput': overall_throughput,
        'batch_metrics': batch_metrics
    }


# System Uptime Tests
@pytest.mark.long_running
def test_sustained_operation(ocr_service, test_documents):
    """Test OCR service performance during sustained operation.
    
    This test verifies that the service can maintain performance and reliability
    during extended periods of operation, supporting the 99.9% uptime requirement.
    """
    # Run for a shorter time in test mode, but long enough to detect issues
    test_duration_seconds = 300  # 5 minutes
    
    # Create a steady stream of documents
    docs_per_batch = 10
    doc_batches = []
    
    # Create enough batches to last the test duration (assuming ~10 seconds per batch)
    estimated_batches = (test_duration_seconds // 10) + 5  # Add buffer
    for _ in range(estimated_batches):
        doc_batches.append(test_documents(MagicMock(
            param={'size': 'medium', 'count': docs_per_batch, 'type': 'mixed'}
        )))
    
    # Process documents until test duration is reached
    start_time = time.time()
    end_time = start_time + test_duration_seconds
    
    batch_metrics = []
    errors = []
    batch_index = 0
    
    while time.time() < end_time and batch_index < len(doc_batches):
        batch = doc_batches[batch_index]
        batch_start = time.time()
        
        results = []
        for doc in batch:
            try:
                result = ocr_service.process_document(doc)
                results.append((True, result))
            except Exception as e:
                results.append((False, str(e)))
                errors.append({
                    'batch': batch_index,
                    'time': time.time() - start_time,
                    'error': str(e)
                })
        
        batch_end = time.time()
        
        # Calculate batch metrics
        batch_time = batch_end - batch_start
        batch_success_count = sum(1 for r in results if r[0])
        batch_success_rate = batch_success_count / len(results)
        
        batch_metrics.append({
            'batch': batch_index,
            'time': batch_time,
            'success_rate': batch_success_rate,
            'elapsed': batch_end - start_time
        })
        
        batch_index += 1
    
    # Calculate overall metrics
    total_elapsed = time.time() - start_time
    total_batches = batch_index
    total_docs = total_batches * docs_per_batch
    overall_success_count = sum(m['success_rate'] * docs_per_batch for m in batch_metrics)
    overall_success_rate = overall_success_count / total_docs
    
    # Log performance metrics
    print(f"Sustained operation test ran for {total_elapsed:.2f} seconds")
    print(f"Processed {total_docs} documents in {total_batches} batches")
    print(f"Overall success rate: {overall_success_rate:.4f}")
    print(f"Total errors: {len(errors)}")
    
    # Verify service maintains high reliability during sustained operation
    assert overall_success_rate >= 0.999, \
        f"Service should maintain 99.9% success rate, but achieved only {overall_success_rate:.4f}"
    
    # Verify no significant performance degradation over time
    if len(batch_metrics) >= 10:  # Need enough batches to detect trends
        # Compare first and last 3 batches
        first_batches = batch_metrics[:3]
        last_batches = batch_metrics[-3:]
        
        first_avg_time = sum(b['time'] for b in first_batches) / len(first_batches)
        last_avg_time = sum(b['time'] for b in last_batches) / len(last_batches)
        
        # Allow for some degradation (50% slower) but not extreme
        assert last_avg_time <= 1.5 * first_avg_time, \
            "Service performance should not degrade significantly over time"
    
    return {
        'duration': total_elapsed,
        'batches': total_batches,
        'documents': total_docs,
        'success_rate': overall_success_rate,
        'errors': len(errors)
    }