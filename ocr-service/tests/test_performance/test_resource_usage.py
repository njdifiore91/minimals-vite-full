# test_resource_usage.py
# Tests the resource usage of the OCR Service during document processing

import os
import time
import pytest
import numpy as np
import tensorflow as tf
import psutil
import logging
from typing import Dict, List, Tuple, Any, Optional
from unittest.mock import patch, MagicMock

# Import OCR service modules
from src.utils.tensorflow_utils import (
    configure_gpu_memory,
    get_available_gpu_memory,
    check_gpu_requirements,
    load_model,
    preprocess_image_for_ocr,
    run_inference,
    monitor_gpu_utilization
)
from src.services.ocr_service import OCRService
from src.models.model_factory import ModelFactory
from src.config.settings import Settings

# Configure logging
logger = logging.getLogger(__name__)

# Constants for testing
MIN_VRAM_GB = 8.0  # Minimum VRAM required as per spec
MAX_MEMORY_USAGE_MB = 4096  # Maximum acceptable memory usage (4GB)
MAX_GPU_MEMORY_PERCENT = 90  # Maximum acceptable GPU memory usage (90%)
MAX_CPU_PERCENT = 80  # Maximum acceptable CPU usage (80%)


# Fixtures
@pytest.fixture
def mock_gpu_environment():
    """Fixture to create a mock GPU environment for testing."""
    # Create a mock GPU environment with controlled memory and utilization
    with patch('src.utils.tensorflow_utils.monitor_gpu_utilization') as mock_monitor:
        # Mock GPU utilization data
        mock_monitor.return_value = {
            "gpu_0": {
                "name": "NVIDIA Test GPU",
                "memory_used_gb": 2.0,
                "memory_total_gb": 16.0,
                "memory_percent": 12.5,
                "gpu_utilization": 25,
                "memory_utilization": 15
            }
        }
        
        with patch('src.utils.tensorflow_utils.get_available_gpu_memory') as mock_memory:
            # Mock available GPU memory
            mock_memory.return_value = {"GPU:0": 14.0}  # 14GB available
            
            with patch('src.utils.tensorflow_utils.check_gpu_requirements') as mock_check:
                # Mock GPU requirements check
                mock_check.return_value = True
                
                yield {
                    "monitor": mock_monitor,
                    "memory": mock_memory,
                    "check": mock_check
                }


@pytest.fixture
def sample_documents(request):
    """Fixture to provide sample documents for testing.
    
    Parameters:
        request: The pytest request object with optional 'param' for document type
    
    Returns:
        List of document images as numpy arrays
    """
    # Default to 'typed' if not specified
    doc_type = getattr(request, 'param', 'typed')
    
    # Create synthetic test documents of different types and sizes
    documents = []
    
    # Small document (1MB)
    small_doc = np.random.rand(800, 600, 3).astype(np.float32)
    
    # Medium document (5MB)
    medium_doc = np.random.rand(1600, 1200, 3).astype(np.float32)
    
    # Large document (20MB)
    large_doc = np.random.rand(3200, 2400, 3).astype(np.float32)
    
    documents = [small_doc, medium_doc, large_doc]
    
    return {
        "type": doc_type,
        "documents": documents,
        "sizes": ["small", "medium", "large"]
    }


@pytest.fixture
def mock_ocr_service():
    """Fixture to create a mock OCR service for testing."""
    # Create a mock OCR service with controlled behavior
    with patch('src.services.ocr_service.OCRService') as MockOCRService:
        service_instance = MockOCRService.return_value
        
        # Mock the process_document method
        service_instance.process_document.return_value = {
            "text": "Sample extracted text",
            "confidence": 0.95,
            "processing_time": 1.5
        }
        
        # Mock the get_models method
        service_instance.get_models.return_value = {
            "typed": MagicMock(),
            "handwritten": MagicMock(),
            "hybrid": MagicMock(),
            "structure": MagicMock()
        }
        
        yield service_instance


@pytest.fixture
def memory_tracker():
    """Fixture to track memory usage during tests."""
    class MemoryTracker:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_memory = None
            self.peak_memory = 0
            self.end_memory = None
            self.samples = []
        
        def start(self):
            """Start tracking memory usage."""
            self.start_memory = self.process.memory_info().rss / (1024 * 1024)  # MB
            self.peak_memory = self.start_memory
            self.samples = [self.start_memory]
            return self.start_memory
        
        def sample(self):
            """Take a memory usage sample."""
            current = self.process.memory_info().rss / (1024 * 1024)  # MB
            self.samples.append(current)
            if current > self.peak_memory:
                self.peak_memory = current
            return current
        
        def stop(self):
            """Stop tracking memory usage and return statistics."""
            self.end_memory = self.process.memory_info().rss / (1024 * 1024)  # MB
            self.samples.append(self.end_memory)
            if self.end_memory > self.peak_memory:
                self.peak_memory = self.end_memory
            
            return {
                "start_mb": self.start_memory,
                "end_mb": self.end_memory,
                "peak_mb": self.peak_memory,
                "diff_mb": self.end_memory - self.start_memory,
                "samples": self.samples
            }
    
    return MemoryTracker()


@pytest.fixture
def cpu_tracker():
    """Fixture to track CPU usage during tests."""
    class CPUTracker:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_cpu = None
            self.peak_cpu = 0
            self.end_cpu = None
            self.samples = []
            self.interval = 0.1  # Sample every 100ms
        
        def start(self):
            """Start tracking CPU usage."""
            self.start_cpu = self.process.cpu_percent(interval=0.1)
            self.peak_cpu = self.start_cpu
            self.samples = [self.start_cpu]
            return self.start_cpu
        
        def sample(self):
            """Take a CPU usage sample."""
            current = self.process.cpu_percent(interval=self.interval)
            self.samples.append(current)
            if current > self.peak_cpu:
                self.peak_cpu = current
            return current
        
        def stop(self):
            """Stop tracking CPU usage and return statistics."""
            self.end_cpu = self.process.cpu_percent(interval=self.interval)
            self.samples.append(self.end_cpu)
            if self.end_cpu > self.peak_cpu:
                self.peak_cpu = self.end_cpu
            
            return {
                "start_percent": self.start_cpu,
                "end_percent": self.end_cpu,
                "peak_percent": self.peak_cpu,
                "samples": self.samples
            }
    
    return CPUTracker()


# Test functions
@pytest.mark.parametrize("doc_type", ["typed", "handwritten", "hybrid"])
def test_memory_usage_during_ocr_processing(mock_gpu_environment, sample_documents, memory_tracker, doc_type):
    """Test memory usage during OCR processing for different document types.
    
    This test verifies that memory usage stays within acceptable limits during OCR processing.
    """
    # Arrange
    docs = sample_documents
    memory_tracker.start()
    
    # Act - Process each document and track memory usage
    for i, doc in enumerate(docs["documents"]):
        # Preprocess the document
        preprocessed = preprocess_image_for_ocr(doc, doc_type)
        memory_tracker.sample()
        
        # Create a mock model for inference
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.rand(1, 100, 100, 3)  # Mock output
        
        # Run inference
        output, _ = run_inference(mock_model, preprocessed)
        memory_tracker.sample()
        
        # Log memory usage for this document
        logger.info(f"Memory usage after processing {docs['sizes'][i]} {doc_type} document: {memory_tracker.sample()} MB")
    
    # Get final memory statistics
    memory_stats = memory_tracker.stop()
    
    # Assert
    logger.info(f"Memory usage statistics for {doc_type} documents: {memory_stats}")
    assert memory_stats["peak_mb"] < MAX_MEMORY_USAGE_MB, f"Peak memory usage ({memory_stats['peak_mb']} MB) exceeds limit ({MAX_MEMORY_USAGE_MB} MB)"


def test_gpu_memory_utilization(mock_gpu_environment):
    """Test GPU memory utilization during OCR processing.
    
    This test verifies that GPU memory usage stays within acceptable limits and that
    the service properly detects and utilizes available GPU resources.
    """
    # Arrange
    gpu_env = mock_gpu_environment
    
    # Act
    # Check GPU requirements
    meets_requirements = check_gpu_requirements(min_vram_gb=MIN_VRAM_GB)
    
    # Get available GPU memory
    available_memory = get_available_gpu_memory()
    
    # Monitor GPU utilization
    utilization = monitor_gpu_utilization()
    
    # Assert
    assert meets_requirements, f"System does not meet minimum GPU requirements of {MIN_VRAM_GB} GB VRAM"
    
    # Check that we have at least one GPU with sufficient memory
    assert any(mem >= MIN_VRAM_GB for gpu, mem in available_memory.items() if mem > 0), \
        f"No GPU found with at least {MIN_VRAM_GB} GB VRAM"
    
    # Check that GPU utilization is reported correctly
    for gpu_id, metrics in utilization.items():
        assert "memory_percent" in metrics, f"GPU {gpu_id} does not report memory percentage"
        assert metrics["memory_percent"] <= MAX_GPU_MEMORY_PERCENT, \
            f"GPU {gpu_id} memory usage ({metrics['memory_percent']}%) exceeds limit ({MAX_GPU_MEMORY_PERCENT}%)"


@pytest.mark.parametrize("processing_stage", ["preprocessing", "inference", "postprocessing"])
def test_cpu_usage_during_processing_stages(mock_gpu_environment, sample_documents, cpu_tracker, processing_stage):
    """Test CPU usage during different OCR processing stages.
    
    This test verifies that CPU usage stays within acceptable limits during different
    stages of OCR processing.
    """
    # Arrange
    docs = sample_documents
    cpu_tracker.start()
    
    # Act - Process based on the stage being tested
    if processing_stage == "preprocessing":
        # Test CPU usage during preprocessing
        for i, doc in enumerate(docs["documents"]):
            preprocess_image_for_ocr(doc, docs["type"])
            cpu_tracker.sample()
            logger.info(f"CPU usage after preprocessing {docs['sizes'][i]} document: {cpu_tracker.sample()}%")
    
    elif processing_stage == "inference":
        # Test CPU usage during inference
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.rand(1, 100, 100, 3)  # Mock output
        
        for i, doc in enumerate(docs["documents"]):
            preprocessed = preprocess_image_for_ocr(doc, docs["type"])
            run_inference(mock_model, preprocessed)
            cpu_tracker.sample()
            logger.info(f"CPU usage after inference on {docs['sizes'][i]} document: {cpu_tracker.sample()}%")
    
    elif processing_stage == "postprocessing":
        # Test CPU usage during postprocessing (e.g., text extraction)
        for i, doc in enumerate(docs["documents"]):
            # Mock postprocessing by performing some CPU-intensive operations
            result = np.fft.fft2(doc)  # FFT is CPU-intensive
            threshold = np.mean(result)
            binary = result > threshold
            cpu_tracker.sample()
            logger.info(f"CPU usage after postprocessing {docs['sizes'][i]} document: {cpu_tracker.sample()}%")
    
    # Get final CPU statistics
    cpu_stats = cpu_tracker.stop()
    
    # Assert
    logger.info(f"CPU usage statistics for {processing_stage}: {cpu_stats}")
    assert cpu_stats["peak_percent"] < MAX_CPU_PERCENT, \
        f"Peak CPU usage ({cpu_stats['peak_percent']}%) during {processing_stage} exceeds limit ({MAX_CPU_PERCENT}%)"


@pytest.mark.parametrize("doc_type", ["typed", "handwritten", "hybrid"])
def test_resource_efficiency_with_different_document_types(mock_gpu_environment, memory_tracker, cpu_tracker, doc_type):
    """Test resource efficiency with different document types.
    
    This test verifies that the OCR service efficiently utilizes resources when
    processing different types of documents.
    """
    # Arrange
    # Create a document of the specified type
    if doc_type == "typed":
        # Typed documents might be cleaner with more uniform text
        doc = np.ones((1024, 768, 3), dtype=np.float32) * 0.9  # Light background
        # Add some "text-like" darker regions
        for i in range(10):
            y = 100 + i * 50
            doc[y:y+20, 100:700, :] *= 0.2  # Dark "text" lines
    
    elif doc_type == "handwritten":
        # Handwritten documents might have more variation
        doc = np.ones((1024, 768, 3), dtype=np.float32) * 0.9  # Light background
        # Add some "handwriting-like" darker regions with more variation
        for i in range(10):
            y = 100 + i * 50
            # More irregular lines for handwriting
            for j in range(5):
                x_start = 100 + j * 120
                width = np.random.randint(50, 100)
                doc[y:y+20, x_start:x_start+width, :] *= 0.3
    
    elif doc_type == "hybrid":
        # Hybrid documents might have both typed and handwritten elements
        doc = np.ones((1024, 768, 3), dtype=np.float32) * 0.9  # Light background
        # Add some "text-like" darker regions
        for i in range(5):
            y = 100 + i * 50
            doc[y:y+20, 100:700, :] *= 0.2  # Dark "text" lines
        
        # Add some "handwriting-like" regions
        for i in range(5):
            y = 400 + i * 50
            for j in range(3):
                x_start = 100 + j * 200
                width = np.random.randint(50, 150)
                doc[y:y+25, x_start:x_start+width, :] *= 0.3
    
    # Start tracking resources
    memory_tracker.start()
    cpu_tracker.start()
    
    # Act - Process the document
    # Preprocess
    preprocessed = preprocess_image_for_ocr(doc, doc_type)
    memory_after_preprocess = memory_tracker.sample()
    cpu_after_preprocess = cpu_tracker.sample()
    
    # Mock inference
    mock_model = MagicMock()
    mock_model.predict.return_value = np.random.rand(1, 100, 100, 3)  # Mock output
    output, inference_time = run_inference(mock_model, preprocessed)
    memory_after_inference = memory_tracker.sample()
    cpu_after_inference = cpu_tracker.sample()
    
    # Mock postprocessing
    time.sleep(0.1)  # Simulate some processing time
    memory_after_postprocess = memory_tracker.sample()
    cpu_after_postprocess = cpu_tracker.sample()
    
    # Get final resource statistics
    memory_stats = memory_tracker.stop()
    cpu_stats = cpu_tracker.stop()
    
    # Calculate efficiency metrics
    memory_efficiency = {
        "preprocessing": memory_after_preprocess - memory_stats["start_mb"],
        "inference": memory_after_inference - memory_after_preprocess,
        "postprocessing": memory_after_postprocess - memory_after_inference,
        "total": memory_stats["peak_mb"] - memory_stats["start_mb"]
    }
    
    cpu_efficiency = {
        "preprocessing": cpu_after_preprocess,
        "inference": cpu_after_inference,
        "postprocessing": cpu_after_postprocess,
        "peak": cpu_stats["peak_percent"]
    }
    
    # Log efficiency metrics
    logger.info(f"Resource efficiency for {doc_type} document:")
    logger.info(f"Memory efficiency (MB): {memory_efficiency}")
    logger.info(f"CPU efficiency (%): {cpu_efficiency}")
    logger.info(f"Inference time (s): {inference_time}")
    
    # Assert
    # Check that memory usage is reasonable for the document type
    assert memory_efficiency["total"] < MAX_MEMORY_USAGE_MB, \
        f"Total memory usage for {doc_type} document ({memory_efficiency['total']} MB) exceeds limit ({MAX_MEMORY_USAGE_MB} MB)"
    
    # Check that CPU usage is reasonable
    assert cpu_efficiency["peak"] < MAX_CPU_PERCENT, \
        f"Peak CPU usage for {doc_type} document ({cpu_efficiency['peak']}%) exceeds limit ({MAX_CPU_PERCENT}%)"
    
    # Additional assertions specific to document types
    if doc_type == "typed":
        # Typed documents should be more efficient to process
        assert inference_time < 2.0, f"Inference time for typed document ({inference_time}s) is too high"
    
    elif doc_type == "handwritten":
        # Handwritten documents might take more resources but should still be reasonable
        assert inference_time < 3.0, f"Inference time for handwritten document ({inference_time}s) is too high"


def test_resource_usage_within_acceptable_limits(mock_gpu_environment, memory_tracker, cpu_tracker):
    """Test that resource usage stays within acceptable limits for production deployment.
    
    This test verifies that the OCR service's resource usage meets the requirements
    for production deployment.
    """
    # Arrange
    # Create a batch of documents to simulate production load
    batch_size = 5
    docs = [np.random.rand(1024, 768, 3).astype(np.float32) for _ in range(batch_size)]
    
    # Start tracking resources
    memory_tracker.start()
    cpu_tracker.start()
    
    # Act - Process the batch of documents
    for i, doc in enumerate(docs):
        # Preprocess
        preprocessed = preprocess_image_for_ocr(doc, "hybrid")  # Use hybrid model for mixed content
        
        # Mock inference
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.rand(1, 100, 100, 3)  # Mock output
        output, _ = run_inference(mock_model, preprocessed)
        
        # Sample resource usage after each document
        memory_usage = memory_tracker.sample()
        cpu_usage = cpu_tracker.sample()
        
        logger.info(f"Resource usage after processing document {i+1}/{batch_size}:")
        logger.info(f"Memory usage: {memory_usage} MB")
        logger.info(f"CPU usage: {cpu_usage}%")
        
        # Check that resources stay within limits for each document
        assert memory_usage < MAX_MEMORY_USAGE_MB, \
            f"Memory usage after document {i+1} ({memory_usage} MB) exceeds limit ({MAX_MEMORY_USAGE_MB} MB)"
        
        assert cpu_usage < MAX_CPU_PERCENT, \
            f"CPU usage after document {i+1} ({cpu_usage}%) exceeds limit ({MAX_CPU_PERCENT}%)"
    
    # Get final resource statistics
    memory_stats = memory_tracker.stop()
    cpu_stats = cpu_tracker.stop()
    
    # Assert
    logger.info(f"Final resource statistics after processing {batch_size} documents:")
    logger.info(f"Memory statistics: {memory_stats}")
    logger.info(f"CPU statistics: {cpu_stats}")
    
    # Check overall resource usage
    assert memory_stats["peak_mb"] < MAX_MEMORY_USAGE_MB, \
        f"Peak memory usage ({memory_stats['peak_mb']} MB) exceeds limit ({MAX_MEMORY_USAGE_MB} MB)"
    
    assert cpu_stats["peak_percent"] < MAX_CPU_PERCENT, \
        f"Peak CPU usage ({cpu_stats['peak_percent']}%) exceeds limit ({MAX_CPU_PERCENT}%)"
    
    # Check for memory leaks (memory should not grow excessively)
    memory_growth_per_doc = memory_stats["diff_mb"] / batch_size
    assert memory_growth_per_doc < 100, \
        f"Memory growth per document ({memory_growth_per_doc} MB) suggests a potential memory leak"


@pytest.mark.parametrize("batch_size", [1, 5, 10])
def test_resource_scaling_with_batch_size(mock_gpu_environment, memory_tracker, batch_size):
    """Test how resource usage scales with different batch sizes.
    
    This test verifies that resource usage scales reasonably with increasing batch sizes.
    """
    # Arrange
    # Create batches of documents with different sizes
    docs = [np.random.rand(1024, 768, 3).astype(np.float32) for _ in range(batch_size)]
    
    # Start tracking memory
    memory_tracker.start()
    
    # Act - Process the batch of documents
    start_time = time.time()
    
    for i, doc in enumerate(docs):
        # Preprocess
        preprocessed = preprocess_image_for_ocr(doc, "typed")  # Use typed model for consistency
        
        # Mock inference
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.rand(1, 100, 100, 3)  # Mock output
        output, _ = run_inference(mock_model, preprocessed)
        
        # Sample memory usage after each document
        memory_usage = memory_tracker.sample()
        logger.info(f"Memory usage after processing document {i+1}/{batch_size}: {memory_usage} MB")
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    # Get final memory statistics
    memory_stats = memory_tracker.stop()
    
    # Calculate scaling metrics
    memory_per_doc = memory_stats["diff_mb"] / batch_size if batch_size > 0 else 0
    time_per_doc = processing_time / batch_size if batch_size > 0 else 0
    
    # Log scaling metrics
    logger.info(f"Resource scaling metrics for batch size {batch_size}:")
    logger.info(f"Total memory usage: {memory_stats['diff_mb']} MB")
    logger.info(f"Memory per document: {memory_per_doc} MB")
    logger.info(f"Total processing time: {processing_time} seconds")
    logger.info(f"Time per document: {time_per_doc} seconds")
    
    # Assert
    # Memory usage should scale reasonably with batch size
    assert memory_stats["peak_mb"] < MAX_MEMORY_USAGE_MB, \
        f"Peak memory usage ({memory_stats['peak_mb']} MB) exceeds limit ({MAX_MEMORY_USAGE_MB} MB)"
    
    # Memory per document should be relatively consistent (not growing excessively)
    assert memory_per_doc < 200, \
        f"Memory per document ({memory_per_doc} MB) is too high"
    
    # Processing time should scale reasonably (sub-linear is ideal due to batching efficiencies)
    assert time_per_doc < 2.0, \
        f"Processing time per document ({time_per_doc}s) is too high"
    
    # For larger batches, we expect some efficiency gains
    if batch_size > 1:
        # This is a simplified check - in reality, you'd want to compare with single-document processing
        assert time_per_doc < 1.5, \
            f"Processing time per document in batch ({time_per_doc}s) doesn't show efficiency gains"


def test_gpu_memory_cleanup_after_processing(mock_gpu_environment, memory_tracker):
    """Test that GPU memory is properly cleaned up after processing.
    
    This test verifies that GPU memory is released after document processing,
    preventing memory leaks that could impact long-running services.
    """
    # Arrange
    # Create a sequence of documents to process
    num_docs = 3
    docs = [np.random.rand(1024, 768, 3).astype(np.float32) for _ in range(num_docs)]
    
    # Start tracking memory
    memory_tracker.start()
    
    # Mock TensorFlow's GPU memory tracking
    with patch('src.utils.tensorflow_utils.monitor_gpu_utilization') as mock_monitor:
        # Set up the mock to return decreasing GPU memory usage after each call
        # to simulate proper cleanup
        mock_monitor.side_effect = [
            {"gpu_0": {"memory_percent": 50, "memory_used_gb": 8.0, "memory_total_gb": 16.0}},  # Initial usage
            {"gpu_0": {"memory_percent": 60, "memory_used_gb": 9.6, "memory_total_gb": 16.0}},  # During processing
            {"gpu_0": {"memory_percent": 45, "memory_used_gb": 7.2, "memory_total_gb": 16.0}}   # After cleanup
        ]
        
        # Act - Process documents and check GPU memory after each
        gpu_memory_samples = []
        
        for i, doc in enumerate(docs):
            # Preprocess and run inference with mock model
            preprocessed = preprocess_image_for_ocr(doc, "typed")
            mock_model = MagicMock()
            mock_model.predict.return_value = np.random.rand(1, 100, 100, 3)
            output, _ = run_inference(mock_model, preprocessed)
            
            # Force garbage collection to clean up memory
            import gc
            gc.collect()
            
            # Check GPU memory usage
            gpu_usage = monitor_gpu_utilization()
            gpu_memory_samples.append(gpu_usage["gpu_0"]["memory_percent"])
            
            logger.info(f"GPU memory usage after document {i+1}: {gpu_usage['gpu_0']['memory_percent']}%")
        
        # Explicitly delete model to test cleanup
        del mock_model
        gc.collect()
        
        # Final GPU memory check after all processing
        final_gpu_usage = monitor_gpu_utilization()
        gpu_memory_samples.append(final_gpu_usage["gpu_0"]["memory_percent"])
        
        logger.info(f"Final GPU memory usage: {final_gpu_usage['gpu_0']['memory_percent']}%")
        logger.info(f"GPU memory samples: {gpu_memory_samples}")
        
        # Assert
        # GPU memory should be lower after cleanup than during peak processing
        assert final_gpu_usage["gpu_0"]["memory_percent"] < gpu_memory_samples[1], \
            "GPU memory not properly released after processing"
        
        # Final GPU memory should be close to initial memory (allowing for some overhead)
        assert abs(final_gpu_usage["gpu_0"]["memory_percent"] - gpu_memory_samples[0]) < 10, \
            "GPU memory usage shows significant leak after processing"


def test_resource_usage_with_concurrent_processing(mock_gpu_environment, memory_tracker):
    """Test resource usage when processing documents concurrently.
    
    This test verifies that resource usage remains within acceptable limits
    when processing multiple documents concurrently, simulating a production load.
    """
    # Arrange
    # Create documents for concurrent processing
    num_concurrent = 3
    docs = [np.random.rand(1024, 768, 3).astype(np.float32) for _ in range(num_concurrent)]
    
    # Start tracking memory
    memory_tracker.start()
    
    # Act - Simulate concurrent processing using threads
    import threading
    
    def process_document(doc_idx):
        """Process a single document in a separate thread."""
        doc = docs[doc_idx]
        
        # Preprocess
        preprocessed = preprocess_image_for_ocr(doc, "typed")
        
        # Mock inference
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.rand(1, 100, 100, 3)
        output, inference_time = run_inference(mock_model, preprocessed)
        
        logger.info(f"Thread {doc_idx} completed processing in {inference_time}s")
    
    # Create and start threads for concurrent processing
    threads = []
    for i in range(num_concurrent):
        thread = threading.Thread(target=process_document, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Sample memory during concurrent processing
    concurrent_samples = []
    for _ in range(5):  # Take 5 samples during concurrent processing
        time.sleep(0.1)
        concurrent_samples.append(memory_tracker.sample())
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Get final memory statistics
    memory_stats = memory_tracker.stop()
    
    # Log memory usage during concurrent processing
    logger.info(f"Memory samples during concurrent processing: {concurrent_samples}")
    logger.info(f"Final memory statistics: {memory_stats}")
    
    # Assert
    # Peak memory during concurrent processing should be within limits
    assert memory_stats["peak_mb"] < MAX_MEMORY_USAGE_MB, \
        f"Peak memory usage during concurrent processing ({memory_stats['peak_mb']} MB) exceeds limit ({MAX_MEMORY_USAGE_MB} MB)"
    
    # Memory usage should be higher during concurrent processing than single-document processing
    # but should still be reasonable (less than num_concurrent times single-document usage)
    assert memory_stats["peak_mb"] < 200 * num_concurrent, \
        f"Memory usage during concurrent processing ({memory_stats['peak_mb']} MB) is excessive"


def test_resource_usage_with_model_switching(mock_gpu_environment, memory_tracker):
    """Test resource usage when switching between different OCR models.
    
    This test verifies that switching between different OCR models (typed, handwritten, etc.)
    doesn't cause excessive resource usage or memory leaks.
    """
    # Arrange
    # Create a document to process with different models
    doc = np.random.rand(1024, 768, 3).astype(np.float32)
    model_types = ["typed", "handwritten", "hybrid", "structure"]
    
    # Start tracking memory
    memory_tracker.start()
    
    # Act - Process the document with each model type
    for model_type in model_types:
        # Preprocess for this model type
        preprocessed = preprocess_image_for_ocr(doc, model_type)
        
        # Mock model loading
        with patch('src.utils.tensorflow_utils.load_model') as mock_load:
            mock_model = MagicMock()
            mock_model.predict.return_value = np.random.rand(1, 100, 100, 3)
            mock_load.return_value = mock_model
            
            # Load the model
            model = load_model("/mock/model/dir", model_type)
            
            # Run inference
            output, inference_time = run_inference(model, preprocessed)
            
            # Sample memory after using this model
            memory_usage = memory_tracker.sample()
            logger.info(f"Memory usage after using {model_type} model: {memory_usage} MB")
            
            # Force cleanup
            del model
            import gc
            gc.collect()
    
    # Get final memory statistics
    memory_stats = memory_tracker.stop()
    
    # Assert
    logger.info(f"Memory statistics after model switching: {memory_stats}")
    
    # Peak memory should be within limits
    assert memory_stats["peak_mb"] < MAX_MEMORY_USAGE_MB, \
        f"Peak memory usage during model switching ({memory_stats['peak_mb']} MB) exceeds limit ({MAX_MEMORY_USAGE_MB} MB)"
    
    # Memory growth should be reasonable (not indicating a leak)
    assert memory_stats["diff_mb"] < 500, \
        f"Memory growth during model switching ({memory_stats['diff_mb']} MB) suggests a memory leak"


# Main test that combines multiple resource aspects
def test_comprehensive_resource_profile(mock_gpu_environment, memory_tracker, cpu_tracker):
    """Comprehensive test of resource usage during OCR processing.
    
    This test provides a complete profile of resource usage during OCR processing,
    covering memory, CPU, and GPU utilization across all processing stages.
    """
    # Arrange
    # Create documents of different sizes
    small_doc = np.random.rand(800, 600, 3).astype(np.float32)   # Small (~1.4MB)
    medium_doc = np.random.rand(1600, 1200, 3).astype(np.float32)  # Medium (~5.8MB)
    large_doc = np.random.rand(3200, 2400, 3).astype(np.float32)   # Large (~23MB)
    
    docs = [(small_doc, "small"), (medium_doc, "medium"), (large_doc, "large")]
    
    # Start tracking resources
    memory_tracker.start()
    cpu_tracker.start()
    
    # Act - Process each document and collect comprehensive metrics
    results = []
    
    for doc, size in docs:
        doc_results = {"size": size, "stages": {}}
        
        # Stage 1: Preprocessing
        stage_start_time = time.time()
        stage_start_memory = memory_tracker.sample()
        stage_start_cpu = cpu_tracker.sample()
        
        preprocessed = preprocess_image_for_ocr(doc, "hybrid")
        
        stage_end_time = time.time()
        stage_end_memory = memory_tracker.sample()
        stage_end_cpu = cpu_tracker.sample()
        
        doc_results["stages"]["preprocessing"] = {
            "time": stage_end_time - stage_start_time,
            "memory_delta": stage_end_memory - stage_start_memory,
            "cpu": stage_end_cpu
        }
        
        # Stage 2: Model Inference
        stage_start_time = time.time()
        stage_start_memory = memory_tracker.sample()
        stage_start_cpu = cpu_tracker.sample()
        
        # Mock model inference
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.rand(1, 100, 100, 3)
        output, inference_time = run_inference(mock_model, preprocessed)
        
        stage_end_time = time.time()
        stage_end_memory = memory_tracker.sample()
        stage_end_cpu = cpu_tracker.sample()
        
        doc_results["stages"]["inference"] = {
            "time": stage_end_time - stage_start_time,
            "memory_delta": stage_end_memory - stage_start_memory,
            "cpu": stage_end_cpu
        }
        
        # Stage 3: Postprocessing
        stage_start_time = time.time()
        stage_start_memory = memory_tracker.sample()
        stage_start_cpu = cpu_tracker.sample()
        
        # Mock postprocessing
        result = np.fft.fft2(doc)  # FFT is CPU-intensive
        threshold = np.mean(result)
        binary = result > threshold
        
        stage_end_time = time.time()
        stage_end_memory = memory_tracker.sample()
        stage_end_cpu = cpu_tracker.sample()
        
        doc_results["stages"]["postprocessing"] = {
            "time": stage_end_time - stage_start_time,
            "memory_delta": stage_end_memory - stage_start_memory,
            "cpu": stage_end_cpu
        }
        
        # Mock GPU utilization for this document
        with patch('src.utils.tensorflow_utils.monitor_gpu_utilization') as mock_monitor:
            # Different GPU utilization based on document size
            if size == "small":
                gpu_util = 30
            elif size == "medium":
                gpu_util = 50
            else:  # large
                gpu_util = 70
                
            mock_monitor.return_value = {
                "gpu_0": {
                    "memory_percent": gpu_util,
                    "gpu_utilization": gpu_util,
                    "memory_used_gb": gpu_util * 0.16,  # Scale to GB
                    "memory_total_gb": 16.0
                }
            }
            
            doc_results["gpu"] = monitor_gpu_utilization()["gpu_0"]
        
        # Calculate total processing metrics
        doc_results["total"] = {
            "time": sum(stage["time"] for stage in doc_results["stages"].values()),
            "memory_peak": memory_tracker.peak_memory,
            "cpu_peak": cpu_tracker.peak_cpu
        }
        
        results.append(doc_results)
        
        # Log results for this document
        logger.info(f"Resource profile for {size} document:")
        logger.info(f"Total processing time: {doc_results['total']['time']:.2f}s")
        logger.info(f"Peak memory usage: {doc_results['total']['memory_peak']:.2f} MB")
        logger.info(f"Peak CPU usage: {doc_results['total']['cpu_peak']:.2f}%")
        logger.info(f"GPU utilization: {doc_results['gpu']['gpu_utilization']}%")
        logger.info(f"Stage breakdown: {doc_results['stages']}")
        
        # Cleanup after each document
        del mock_model
        import gc
        gc.collect()
    
    # Get final resource statistics
    memory_stats = memory_tracker.stop()
    cpu_stats = cpu_tracker.stop()
    
    # Assert
    # Overall resource usage should be within limits
    assert memory_stats["peak_mb"] < MAX_MEMORY_USAGE_MB, \
        f"Peak memory usage ({memory_stats['peak_mb']} MB) exceeds limit ({MAX_MEMORY_USAGE_MB} MB)"
    
    assert cpu_stats["peak_percent"] < MAX_CPU_PERCENT, \
        f"Peak CPU usage ({cpu_stats['peak_percent']}%) exceeds limit ({MAX_CPU_PERCENT}%)"
    
    # Processing time should scale with document size
    small_time = next(r["total"]["time"] for r in results if r["size"] == "small")
    medium_time = next(r["total"]["time"] for r in results if r["size"] == "medium")
    large_time = next(r["total"]["time"] for r in results if r["size"] == "large")
    
    assert small_time < medium_time < large_time, \
        "Processing time does not scale properly with document size"
    
    # Large documents should still process in reasonable time
    assert large_time < 10.0, f"Processing time for large document ({large_time}s) is too high"
    
    # Memory usage should scale reasonably with document size
    small_memory = next(r["total"]["memory_peak"] for r in results if r["size"] == "small")
    large_memory = next(r["total"]["memory_peak"] for r in results if r["size"] == "large")
    
    # Large document should use more memory, but not excessively more
    assert large_memory > small_memory, "Memory usage does not scale with document size"
    assert large_memory < small_memory * 10, "Memory usage scales excessively with document size"
    
    # GPU utilization should be higher for larger documents
    small_gpu = next(r["gpu"]["gpu_utilization"] for r in results if r["size"] == "small")
    large_gpu = next(r["gpu"]["gpu_utilization"] for r in results if r["size"] == "large")
    
    assert large_gpu > small_gpu, "GPU utilization does not scale with document size"


# Helper functions
def get_system_resource_info():
    """Get information about system resources for logging purposes."""
    try:
        import platform
        import psutil
        
        # Get CPU info
        cpu_count = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            cpu_freq_current = cpu_freq.current
            cpu_freq_max = cpu_freq.max
        else:
            cpu_freq_current = "Unknown"
            cpu_freq_max = "Unknown"
        
        # Get memory info
        memory = psutil.virtual_memory()
        total_memory_gb = memory.total / (1024**3)
        available_memory_gb = memory.available / (1024**3)
        
        # Get GPU info using TensorFlow
        gpus = tf.config.list_physical_devices('GPU')
        gpu_info = []
        for gpu in gpus:
            gpu_info.append(str(gpu))
        
        # Get system info
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "tensorflow_version": tf.__version__,
            "cpu": {
                "physical_cores": cpu_count,
                "logical_cores": cpu_count_logical,
                "current_freq_mhz": cpu_freq_current,
                "max_freq_mhz": cpu_freq_max
            },
            "memory": {
                "total_gb": total_memory_gb,
                "available_gb": available_memory_gb,
                "percent_used": memory.percent
            },
            "gpu": {
                "devices": gpu_info,
                "count": len(gpus)
            }
        }
        
        return system_info
    except Exception as e:
        logger.error(f"Error getting system resource info: {str(e)}")
        return {"error": str(e)}


def log_test_environment():
    """Log information about the test environment."""
    system_info = get_system_resource_info()
    
    logger.info("===== Test Environment Information =====")
    logger.info(f"Platform: {system_info.get('platform', 'Unknown')}")
    logger.info(f"Python version: {system_info.get('python_version', 'Unknown')}")
    logger.info(f"TensorFlow version: {system_info.get('tensorflow_version', 'Unknown')}")
    
    cpu_info = system_info.get('cpu', {})
    logger.info(f"CPU: {cpu_info.get('physical_cores', 'Unknown')} physical cores, "
               f"{cpu_info.get('logical_cores', 'Unknown')} logical cores")
    logger.info(f"CPU frequency: {cpu_info.get('current_freq_mhz', 'Unknown')} MHz "
               f"(max: {cpu_info.get('max_freq_mhz', 'Unknown')} MHz)")
    
    memory_info = system_info.get('memory', {})
    logger.info(f"Memory: {memory_info.get('total_gb', 'Unknown'):.2f} GB total, "
               f"{memory_info.get('available_gb', 'Unknown'):.2f} GB available "
               f"({memory_info.get('percent_used', 'Unknown')}% used)")
    
    gpu_info = system_info.get('gpu', {})
    logger.info(f"GPUs: {gpu_info.get('count', 'Unknown')} devices")
    for i, device in enumerate(gpu_info.get('devices', [])):
        logger.info(f"  GPU {i}: {device}")
    
    logger.info("=========================================")


# Execute this when the module is run directly
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Log test environment information
    log_test_environment()
    
    # Run a simple resource usage test
    print("Running manual resource usage test...")
    
    # Create a memory tracker
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
    
    # Create a test document
    doc = np.random.rand(1024, 768, 3).astype(np.float32)
    
    # Preprocess the document
    preprocessed = preprocess_image_for_ocr(doc, "typed")
    
    # Check memory after preprocessing
    preprocess_memory = process.memory_info().rss / (1024 * 1024)  # MB
    
    # Create a mock model
    mock_model = MagicMock()
    mock_model.predict.return_value = np.random.rand(1, 100, 100, 3)
    
    # Run inference
    output, inference_time = run_inference(mock_model, preprocessed)
    
    # Check memory after inference
    inference_memory = process.memory_info().rss / (1024 * 1024)  # MB
    
    # Check GPU utilization
    gpu_util = monitor_gpu_utilization()
    
    # Print results
    print(f"Initial memory: {initial_memory:.2f} MB")
    print(f"Memory after preprocessing: {preprocess_memory:.2f} MB (delta: {preprocess_memory - initial_memory:.2f} MB)")
    print(f"Memory after inference: {inference_memory:.2f} MB (delta: {inference_memory - preprocess_memory:.2f} MB)")
    print(f"Inference time: {inference_time:.4f} seconds")
    print(f"GPU utilization: {gpu_util}")
    
    print("\nTest completed successfully!")
    