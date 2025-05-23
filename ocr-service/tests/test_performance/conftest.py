import os
import json
import time
import pytest
import numpy as np
import psutil
import threading
import concurrent.futures
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable
from unittest.mock import MagicMock, patch
from datetime import datetime

# Import OCR service modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from app import OCRServiceApp
from config import app_config, s3_config, rabbitmq_config, tensorflow_config
from models import base_model, typed_text_model, handwritten_text_model, hybrid_recognition_model
from services import ocr_service, queue_service, storage_service, field_extraction_service, confidence_service
from types.documents import DocumentType
from types.extraction import ConfidenceScore, ExtractedField, ExtractedData

# Try to import GPU monitoring libraries, use mock if not available
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants for performance testing
PERFORMANCE_TEST_ITERATIONS = 5  # Default number of iterations for performance tests
PERFORMANCE_TEST_WARMUP = 1      # Default number of warmup iterations
PERFORMANCE_TEST_COOLDOWN = 1    # Default number of cooldown iterations
MAX_CONCURRENT_PROCESSES = 8     # Default maximum number of concurrent processes
MEMORY_THRESHOLD_MB = 1024       # Memory threshold for monitoring (1GB)
GPU_MEMORY_THRESHOLD_MB = 7168   # GPU memory threshold (7GB out of 8GB)
PROCESSING_TIME_THRESHOLD_SEC = 300  # 5 minutes max processing time
ACCURACY_THRESHOLD = 0.99        # 99% accuracy threshold

# ===== Test Data Fixtures =====

@pytest.fixture(scope="session")
def test_data_dir():
    """Return the path to the test data directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data'))


@pytest.fixture(scope="session")
def performance_test_documents(test_data_dir):
    """Provide categorized test documents for performance testing.
    
    Returns a dictionary with documents categorized by:
    - type (typed, handwritten, mixed)
    - size (small, medium, large)
    - complexity (simple, moderate, complex)
    """
    # Load metadata for test documents
    metadata_path = os.path.join(test_data_dir, 'metadata.json')
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Create dictionary of document paths categorized for performance testing
    documents = {
        'typed': {'small': [], 'medium': [], 'large': []},
        'handwritten': {'small': [], 'medium': [], 'large': []},
        'mixed': {'small': [], 'medium': [], 'large': []},
        'tables': {'simple': [], 'moderate': [], 'complex': []},
        'complexity': {'simple': [], 'moderate': [], 'complex': []},
        'quality': {'high': [], 'medium': [], 'low': []}
    }
    
    # Helper function to categorize documents
    def categorize_document(doc_path, doc_metadata):
        doc_type = doc_metadata.get('type', 'unknown')
        doc_size = doc_metadata.get('size', 'medium')
        doc_complexity = doc_metadata.get('complexity', 'moderate')
        doc_quality = doc_metadata.get('quality', 'medium')
        
        # Categorize by type and size
        if doc_type in ['typed', 'handwritten', 'mixed']:
            if doc_size in ['small', 'medium', 'large']:
                documents[doc_type][doc_size].append(doc_path)
        
        # Categorize by complexity
        if doc_complexity in ['simple', 'moderate', 'complex']:
            documents['complexity'][doc_complexity].append(doc_path)
        
        # Categorize by quality
        if doc_quality in ['high', 'medium', 'low']:
            documents['quality'][doc_quality].append(doc_path)
        
        # Special handling for tables
        if 'table' in doc_metadata.get('features', []):
            table_complexity = doc_metadata.get('table_complexity', 'moderate')
            if table_complexity in ['simple', 'moderate', 'complex']:
                documents['tables'][table_complexity].append(doc_path)
    
    # Process typed documents
    typed_dir = os.path.join(test_data_dir, 'typed_documents')
    if os.path.exists(typed_dir):
        # Load typed document manifest if available
        manifest_path = os.path.join(typed_dir, 'sample_manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                typed_manifest = json.load(f)
        else:
            typed_manifest = {}
        
        # Walk through typed document directories
        for root, dirs, files in os.walk(typed_dir):
            for file in files:
                if file.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                    doc_path = os.path.join(root, file)
                    rel_path = os.path.relpath(doc_path, typed_dir)
                    
                    # Get metadata from manifest or use defaults
                    doc_metadata = typed_manifest.get(rel_path, {})
                    doc_metadata.setdefault('type', 'typed')
                    
                    categorize_document(doc_path, doc_metadata)
    
    # Process handwritten documents
    handwritten_dir = os.path.join(test_data_dir, 'handwritten_documents')
    if os.path.exists(handwritten_dir):
        # Load handwritten document manifest if available
        manifest_path = os.path.join(handwritten_dir, 'sample_manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                handwritten_manifest = json.load(f)
        else:
            handwritten_manifest = {}
        
        # Walk through handwritten document directories
        for root, dirs, files in os.walk(handwritten_dir):
            for file in files:
                if file.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                    doc_path = os.path.join(root, file)
                    rel_path = os.path.relpath(doc_path, handwritten_dir)
                    
                    # Get metadata from manifest or use defaults
                    doc_metadata = handwritten_manifest.get(rel_path, {})
                    doc_metadata.setdefault('type', 'handwritten')
                    
                    categorize_document(doc_path, doc_metadata)
    
    # Process mixed documents
    mixed_dir = os.path.join(test_data_dir, 'mixed_documents')
    if os.path.exists(mixed_dir):
        # Load mixed document manifest if available
        manifest_path = os.path.join(mixed_dir, 'sample_manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                mixed_manifest = json.load(f)
        else:
            mixed_manifest = {}
        
        # Walk through mixed document directories
        for root, dirs, files in os.walk(mixed_dir):
            for file in files:
                if file.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                    doc_path = os.path.join(root, file)
                    rel_path = os.path.relpath(doc_path, mixed_dir)
                    
                    # Get metadata from manifest or use defaults
                    doc_metadata = mixed_manifest.get(rel_path, {})
                    doc_metadata.setdefault('type', 'mixed')
                    
                    categorize_document(doc_path, doc_metadata)
    
    # Process table documents
    tables_dir = os.path.join(test_data_dir, 'tables')
    if os.path.exists(tables_dir):
        # Load table document manifest if available
        manifest_path = os.path.join(tables_dir, 'sample_manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                tables_manifest = json.load(f)
        else:
            tables_manifest = {}
        
        # Walk through table document directories
        for root, dirs, files in os.walk(tables_dir):
            for file in files:
                if file.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                    doc_path = os.path.join(root, file)
                    rel_path = os.path.relpath(doc_path, tables_dir)
                    
                    # Get metadata from manifest or use defaults
                    doc_metadata = tables_manifest.get(rel_path, {})
                    doc_metadata.setdefault('type', 'typed')
                    doc_metadata.setdefault('features', []).append('table')
                    
                    categorize_document(doc_path, doc_metadata)
    
    # Create document batches of different sizes for batch processing tests
    documents['batches'] = {
        'small': documents['typed']['small'][:5] + documents['handwritten']['small'][:5],
        'medium': documents['typed']['medium'][:10] + documents['handwritten']['medium'][:10],
        'large': documents['typed']['large'][:15] + documents['handwritten']['large'][:15] + documents['mixed']['medium'][:20]
    }
    
    return {'documents': documents, 'metadata': metadata}


@pytest.fixture(scope="function")
def temp_test_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


# ===== Performance Measurement Fixtures =====

class PerformanceMetrics:
    """Class to store and analyze performance metrics."""
    
    def __init__(self):
        self.processing_times = []
        self.memory_usage = []
        self.gpu_memory_usage = []
        self.accuracy_scores = []
        self.confidence_scores = []
        self.throughput_records = []
        self.latency_records = []
        self.start_time = None
        self.end_time = None
    
    def start_timer(self):
        """Start the performance timer."""
        self.start_time = time.time()
    
    def stop_timer(self):
        """Stop the performance timer and record processing time."""
        if self.start_time is not None:
            self.end_time = time.time()
            processing_time = self.end_time - self.start_time
            self.processing_times.append(processing_time)
            self.start_time = None
            return processing_time
        return None
    
    def record_memory_usage(self, memory_mb):
        """Record memory usage in MB."""
        self.memory_usage.append(memory_mb)
    
    def record_gpu_memory_usage(self, gpu_memory_mb):
        """Record GPU memory usage in MB."""
        self.gpu_memory_usage.append(gpu_memory_mb)
    
    def record_accuracy(self, accuracy):
        """Record accuracy score (0.0-1.0)."""
        self.accuracy_scores.append(accuracy)
    
    def record_confidence(self, confidence):
        """Record confidence score (0.0-1.0)."""
        self.confidence_scores.append(confidence)
    
    def record_throughput(self, documents_count, time_seconds):
        """Record throughput as documents per second."""
        throughput = documents_count / time_seconds if time_seconds > 0 else 0
        self.throughput_records.append((documents_count, time_seconds, throughput))
        return throughput
    
    def record_latency(self, latency_seconds):
        """Record latency in seconds."""
        self.latency_records.append(latency_seconds)
    
    def get_summary(self):
        """Get a summary of performance metrics."""
        summary = {}
        
        # Processing time statistics
        if self.processing_times:
            summary['processing_time'] = {
                'mean': np.mean(self.processing_times),
                'median': np.median(self.processing_times),
                'min': np.min(self.processing_times),
                'max': np.max(self.processing_times),
                'std': np.std(self.processing_times),
                'p95': np.percentile(self.processing_times, 95),
                'p99': np.percentile(self.processing_times, 99),
                'samples': len(self.processing_times)
            }
        
        # Memory usage statistics
        if self.memory_usage:
            summary['memory_usage_mb'] = {
                'mean': np.mean(self.memory_usage),
                'max': np.max(self.memory_usage),
                'samples': len(self.memory_usage)
            }
        
        # GPU memory usage statistics
        if self.gpu_memory_usage:
            summary['gpu_memory_usage_mb'] = {
                'mean': np.mean(self.gpu_memory_usage),
                'max': np.max(self.gpu_memory_usage),
                'samples': len(self.gpu_memory_usage)
            }
        
        # Accuracy statistics
        if self.accuracy_scores:
            summary['accuracy'] = {
                'mean': np.mean(self.accuracy_scores),
                'min': np.min(self.accuracy_scores),
                'samples': len(self.accuracy_scores)
            }
        
        # Confidence statistics
        if self.confidence_scores:
            summary['confidence'] = {
                'mean': np.mean(self.confidence_scores),
                'min': np.min(self.confidence_scores),
                'samples': len(self.confidence_scores)
            }
        
        # Throughput statistics
        if self.throughput_records:
            throughputs = [record[2] for record in self.throughput_records]
            summary['throughput_docs_per_sec'] = {
                'mean': np.mean(throughputs),
                'max': np.max(throughputs),
                'samples': len(throughputs)
            }
        
        # Latency statistics
        if self.latency_records:
            summary['latency_seconds'] = {
                'mean': np.mean(self.latency_records),
                'median': np.median(self.latency_records),
                'p95': np.percentile(self.latency_records, 95),
                'p99': np.percentile(self.latency_records, 99),
                'samples': len(self.latency_records)
            }
        
        return summary
    
    def save_to_file(self, file_path):
        """Save performance metrics to a JSON file."""
        summary = self.get_summary()
        
        # Add timestamp
        summary['timestamp'] = datetime.now().isoformat()
        
        # Add raw data for detailed analysis
        summary['raw_data'] = {
            'processing_times': self.processing_times,
            'memory_usage': self.memory_usage,
            'gpu_memory_usage': self.gpu_memory_usage,
            'accuracy_scores': self.accuracy_scores,
            'confidence_scores': self.confidence_scores,
            'throughput_records': self.throughput_records,
            'latency_records': self.latency_records
        }
        
        with open(file_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return file_path


@pytest.fixture(scope="function")
def performance_metrics():
    """Fixture to provide performance metrics collection and analysis."""
    return PerformanceMetrics()


@pytest.fixture(scope="function")
def time_measure():
    """Fixture to measure execution time of a function."""
    def _time_measure(func, *args, **kwargs):
        """Measure execution time of a function.
        
        Args:
            func: Function to measure
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            tuple: (result, execution_time_seconds)
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    return _time_measure


@pytest.fixture(scope="function")
def benchmark():
    """Fixture to benchmark a function with multiple iterations."""
    def _benchmark(func, iterations=PERFORMANCE_TEST_ITERATIONS, warmup=PERFORMANCE_TEST_WARMUP, 
                  cooldown=PERFORMANCE_TEST_COOLDOWN, *args, **kwargs):
        """Benchmark a function with multiple iterations.
        
        Args:
            func: Function to benchmark
            iterations: Number of iterations to run
            warmup: Number of warmup iterations (not included in results)
            cooldown: Number of cooldown iterations (not included in results)
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            dict: Benchmark results including mean, median, min, max, std
        """
        # Run warmup iterations
        for _ in range(warmup):
            func(*args, **kwargs)
        
        # Run benchmark iterations
        execution_times = []
        results = []
        
        for _ in range(iterations):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            execution_time = end_time - start_time
            execution_times.append(execution_time)
            results.append(result)
        
        # Run cooldown iterations
        for _ in range(cooldown):
            func(*args, **kwargs)
        
        # Calculate statistics
        benchmark_results = {
            'mean': np.mean(execution_times),
            'median': np.median(execution_times),
            'min': np.min(execution_times),
            'max': np.max(execution_times),
            'std': np.std(execution_times),
            'p95': np.percentile(execution_times, 95),
            'p99': np.percentile(execution_times, 99),
            'iterations': iterations,
            'times': execution_times,
            'results': results
        }
        
        return benchmark_results
    
    return _benchmark


# ===== Resource Monitoring Fixtures =====

class ResourceMonitor:
    """Class to monitor system resources during tests."""
    
    def __init__(self, interval=0.5):
        self.interval = interval  # Sampling interval in seconds
        self.running = False
        self.thread = None
        self.cpu_percent = []
        self.memory_percent = []
        self.memory_mb = []
        self.gpu_utilization = []
        self.gpu_memory_mb = []
        self.gpu_memory_percent = []
        self.process = psutil.Process(os.getpid())
        self.nvml_initialized = False
        
        # Initialize NVML if available
        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.nvml_initialized = True
                self.device_count = pynvml.nvmlDeviceGetCount()
                self.devices = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(self.device_count)]
            except Exception as e:
                logger.warning(f"Failed to initialize NVML: {e}")
    
    def _monitor_resources(self):
        """Monitor system resources in a background thread."""
        while self.running:
            # CPU usage
            self.cpu_percent.append(self.process.cpu_percent())
            
            # Memory usage
            memory_info = self.process.memory_info()
            self.memory_mb.append(memory_info.rss / (1024 * 1024))  # Convert to MB
            self.memory_percent.append(self.process.memory_percent())
            
            # GPU usage if available
            if self.nvml_initialized:
                try:
                    for device in self.devices:
                        # GPU utilization
                        utilization = pynvml.nvmlDeviceGetUtilizationRates(device)
                        self.gpu_utilization.append(utilization.gpu)
                        
                        # GPU memory
                        memory_info = pynvml.nvmlDeviceGetMemoryInfo(device)
                        self.gpu_memory_mb.append(memory_info.used / (1024 * 1024))  # Convert to MB
                        self.gpu_memory_percent.append(memory_info.used / memory_info.total * 100)
                except Exception as e:
                    logger.warning(f"Error monitoring GPU: {e}")
            
            time.sleep(self.interval)
    
    def start(self):
        """Start resource monitoring."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_resources)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        """Stop resource monitoring and return results."""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=2.0)
            
            # Clean up NVML if initialized
            if self.nvml_initialized:
                try:
                    pynvml.nvmlShutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down NVML: {e}")
            
            # Return monitoring results
            return self.get_results()
    
    def get_results(self):
        """Get monitoring results."""
        results = {
            'cpu_percent': {
                'mean': np.mean(self.cpu_percent) if self.cpu_percent else 0,
                'max': np.max(self.cpu_percent) if self.cpu_percent else 0,
                'samples': len(self.cpu_percent)
            },
            'memory_mb': {
                'mean': np.mean(self.memory_mb) if self.memory_mb else 0,
                'max': np.max(self.memory_mb) if self.memory_mb else 0,
                'samples': len(self.memory_mb)
            },
            'memory_percent': {
                'mean': np.mean(self.memory_percent) if self.memory_percent else 0,
                'max': np.max(self.memory_percent) if self.memory_percent else 0,
                'samples': len(self.memory_percent)
            }
        }
        
        # Add GPU results if available
        if self.gpu_utilization:
            results['gpu_utilization'] = {
                'mean': np.mean(self.gpu_utilization),
                'max': np.max(self.gpu_utilization),
                'samples': len(self.gpu_utilization)
            }
        
        if self.gpu_memory_mb:
            results['gpu_memory_mb'] = {
                'mean': np.mean(self.gpu_memory_mb),
                'max': np.max(self.gpu_memory_mb),
                'samples': len(self.gpu_memory_mb)
            }
        
        if self.gpu_memory_percent:
            results['gpu_memory_percent'] = {
                'mean': np.mean(self.gpu_memory_percent),
                'max': np.max(self.gpu_memory_percent),
                'samples': len(self.gpu_memory_percent)
            }
        
        return results


@pytest.fixture(scope="function")
def resource_monitor():
    """Fixture to monitor system resources during tests."""
    monitor = ResourceMonitor()
    yield monitor
    monitor.stop()


@pytest.fixture(scope="function")
def gpu_monitor():
    """Fixture to monitor GPU usage during tests.
    
    If pynvml is not available, returns a mock monitor.
    """
    if not PYNVML_AVAILABLE:
        # Return mock monitor if pynvml is not available
        mock_monitor = MagicMock()
        mock_monitor.start = MagicMock()
        mock_monitor.stop = MagicMock(return_value={
            'gpu_utilization': {'mean': 0, 'max': 0, 'samples': 0},
            'gpu_memory_mb': {'mean': 0, 'max': 0, 'samples': 0},
            'gpu_memory_percent': {'mean': 0, 'max': 0, 'samples': 0}
        })
        yield mock_monitor
    else:
        # Create and return real GPU monitor
        class GPUMonitor:
            def __init__(self, interval=0.5):
                self.interval = interval
                self.running = False
                self.thread = None
                self.gpu_utilization = []
                self.gpu_memory_mb = []
                self.gpu_memory_percent = []
                
                # Initialize NVML
                pynvml.nvmlInit()
                self.device_count = pynvml.nvmlDeviceGetCount()
                self.devices = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(self.device_count)]
            
            def _monitor_gpu(self):
                """Monitor GPU resources in a background thread."""
                while self.running:
                    try:
                        for device in self.devices:
                            # GPU utilization
                            utilization = pynvml.nvmlDeviceGetUtilizationRates(device)
                            self.gpu_utilization.append(utilization.gpu)
                            
                            # GPU memory
                            memory_info = pynvml.nvmlDeviceGetMemoryInfo(device)
                            self.gpu_memory_mb.append(memory_info.used / (1024 * 1024))  # Convert to MB
                            self.gpu_memory_percent.append(memory_info.used / memory_info.total * 100)
                    except Exception as e:
                        logger.warning(f"Error monitoring GPU: {e}")
                    
                    time.sleep(self.interval)
            
            def start(self):
                """Start GPU monitoring."""
                if not self.running:
                    self.running = True
                    self.thread = threading.Thread(target=self._monitor_gpu)
                    self.thread.daemon = True
                    self.thread.start()
            
            def stop(self):
                """Stop GPU monitoring and return results."""
                if self.running:
                    self.running = False
                    if self.thread:
                        self.thread.join(timeout=2.0)
                    
                    # Clean up NVML
                    pynvml.nvmlShutdown()
                    
                    # Return monitoring results
                    return self.get_results()
            
            def get_results(self):
                """Get GPU monitoring results."""
                results = {}
                
                if self.gpu_utilization:
                    results['gpu_utilization'] = {
                        'mean': np.mean(self.gpu_utilization),
                        'max': np.max(self.gpu_utilization),
                        'samples': len(self.gpu_utilization)
                    }
                
                if self.gpu_memory_mb:
                    results['gpu_memory_mb'] = {
                        'mean': np.mean(self.gpu_memory_mb),
                        'max': np.max(self.gpu_memory_mb),
                        'samples': len(self.gpu_memory_mb)
                    }
                
                if self.gpu_memory_percent:
                    results['gpu_memory_percent'] = {
                        'mean': np.mean(self.gpu_memory_percent),
                        'max': np.max(self.gpu_memory_percent),
                        'samples': len(self.gpu_memory_percent)
                    }
                
                return results
        
        monitor = GPUMonitor()
        yield monitor
        monitor.stop()


# ===== Load Generation Fixtures =====

@pytest.fixture(scope="function")
def concurrent_processor():
    """Fixture to process documents concurrently."""
    def _concurrent_processor(process_func, documents, max_workers=MAX_CONCURRENT_PROCESSES):
        """Process documents concurrently.
        
        Args:
            process_func: Function to process each document
            documents: List of documents to process
            max_workers: Maximum number of concurrent workers
            
        Returns:
            tuple: (results, execution_time_seconds)
        """
        start_time = time.time()
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_doc = {executor.submit(process_func, doc): doc for doc in documents}
            for future in concurrent.futures.as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result()
                    results.append((doc, result))
                except Exception as e:
                    logger.error(f"Error processing document {doc}: {e}")
                    results.append((doc, None))
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return results, execution_time
    
    return _concurrent_processor


@pytest.fixture(scope="function")
def load_generator():
    """Fixture to generate load for performance testing."""
    def _load_generator(process_func, documents, batch_size=10, delay=0.0, duration=60.0):
        """Generate load by processing documents in batches over time.
        
        Args:
            process_func: Function to process each document
            documents: List of documents to process
            batch_size: Number of documents to process in each batch
            delay: Delay between batches in seconds
            duration: Maximum duration of load generation in seconds
            
        Returns:
            dict: Load generation results
        """
        start_time = time.time()
        end_time = start_time + duration
        
        results = []
        processed_count = 0
        batch_count = 0
        
        # Create document batches
        doc_batches = [documents[i:i+batch_size] for i in range(0, len(documents), batch_size)]
        
        # Process batches until duration is reached or all documents are processed
        while time.time() < end_time and batch_count < len(doc_batches):
            batch = doc_batches[batch_count]
            batch_start_time = time.time()
            
            # Process batch
            batch_results = []
            for doc in batch:
                try:
                    result = process_func(doc)
                    batch_results.append((doc, result))
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing document {doc}: {e}")
                    batch_results.append((doc, None))
            
            batch_end_time = time.time()
            batch_time = batch_end_time - batch_start_time
            
            # Record batch results
            results.append({
                'batch_index': batch_count,
                'batch_size': len(batch),
                'batch_time': batch_time,
                'documents_per_second': len(batch) / batch_time if batch_time > 0 else 0,
                'results': batch_results
            })
            
            batch_count += 1
            
            # Add delay between batches if specified
            if delay > 0 and time.time() < end_time:
                time.sleep(delay)
        
        total_time = time.time() - start_time
        
        # Calculate overall statistics
        load_results = {
            'total_documents': processed_count,
            'total_batches': batch_count,
            'total_time': total_time,
            'documents_per_second': processed_count / total_time if total_time > 0 else 0,
            'batch_results': results
        }
        
        return load_results
    
    return _load_generator


# ===== Result Validation Fixtures =====

@pytest.fixture(scope="function")
def accuracy_validator():
    """Fixture to validate OCR extraction accuracy."""
    def _accuracy_validator(extraction_result, expected_data, field_weights=None):
        """Validate OCR extraction accuracy against expected data.
        
        Args:
            extraction_result: ExtractedData object from OCR processing
            expected_data: Dictionary of expected field values
            field_weights: Dictionary of field weights for weighted accuracy calculation
            
        Returns:
            tuple: (accuracy_score, field_results)
        """
        if not isinstance(extraction_result, ExtractedData):
            return 0.0, {}
        
        # Default to equal weights if not provided
        if field_weights is None:
            field_weights = {field: 1.0 for field in expected_data.keys()}
        
        # Normalize weights to sum to 1.0
        total_weight = sum(field_weights.values())
        normalized_weights = {k: v / total_weight for k, v in field_weights.items()}
        
        # Extract fields from result
        extracted_fields = {field.name: field.value for field in extraction_result.fields}
        
        # Calculate accuracy for each field
        field_results = {}
        weighted_accuracy = 0.0
        
        for field_name, expected_value in expected_data.items():
            if field_name in extracted_fields:
                extracted_value = extracted_fields[field_name]
                
                # Calculate field accuracy (exact match for now)
                # Could be extended with fuzzy matching or field-specific comparisons
                field_accuracy = 1.0 if extracted_value == expected_value else 0.0
                
                # Get field confidence
                field_confidence = next((field.confidence.value for field in extraction_result.fields 
                                        if field.name == field_name), 0.0)
                
                # Record field result
                field_results[field_name] = {
                    'expected': expected_value,
                    'extracted': extracted_value,
                    'accuracy': field_accuracy,
                    'confidence': field_confidence,
                    'weight': normalized_weights.get(field_name, 0.0)
                }
                
                # Add to weighted accuracy
                weighted_accuracy += field_accuracy * normalized_weights.get(field_name, 0.0)
            else:
                # Field not found in extraction result
                field_results[field_name] = {
                    'expected': expected_value,
                    'extracted': None,
                    'accuracy': 0.0,
                    'confidence': 0.0,
                    'weight': normalized_weights.get(field_name, 0.0)
                }
        
        return weighted_accuracy, field_results
    
    return _accuracy_validator


@pytest.fixture(scope="function")
def result_collector():
    """Fixture to collect and analyze test results."""
    class ResultCollector:
        def __init__(self):
            self.results = []
            self.performance_metrics = PerformanceMetrics()
        
        def add_result(self, test_name, document_type, document_path, extraction_result, 
                       accuracy=None, processing_time=None, resource_usage=None):
            """Add a test result.
            
            Args:
                test_name: Name of the test
                document_type: Type of document processed
                document_path: Path to the document
                extraction_result: ExtractedData object from OCR processing
                accuracy: Accuracy score if available
                processing_time: Processing time in seconds if available
                resource_usage: Resource usage metrics if available
            """
            # Record performance metrics if available
            if processing_time is not None:
                self.performance_metrics.processing_times.append(processing_time)
            
            if accuracy is not None:
                self.performance_metrics.record_accuracy(accuracy)
            
            if resource_usage is not None:
                if 'memory_mb' in resource_usage and 'max' in resource_usage['memory_mb']:
                    self.performance_metrics.record_memory_usage(resource_usage['memory_mb']['max'])
                
                if 'gpu_memory_mb' in resource_usage and 'max' in resource_usage['gpu_memory_mb']:
                    self.performance_metrics.record_gpu_memory_usage(resource_usage['gpu_memory_mb']['max'])
            
            # Record confidence scores if available
            if isinstance(extraction_result, ExtractedData) and extraction_result.fields:
                for field in extraction_result.fields:
                    if hasattr(field, 'confidence') and hasattr(field.confidence, 'value'):
                        self.performance_metrics.record_confidence(field.confidence.value)
            
            # Add result to collection
            result = {
                'test_name': test_name,
                'document_type': document_type,
                'document_path': document_path,
                'extraction_result': extraction_result,
                'accuracy': accuracy,
                'processing_time': processing_time,
                'resource_usage': resource_usage,
                'timestamp': datetime.now().isoformat()
            }
            
            self.results.append(result)
            return result
        
        def get_summary(self):
            """Get a summary of test results."""
            summary = {
                'total_tests': len(self.results),
                'performance_metrics': self.performance_metrics.get_summary(),
                'document_types': {}
            }
            
            # Group results by document type
            doc_type_results = {}
            for result in self.results:
                doc_type = result.get('document_type', 'unknown')
                if doc_type not in doc_type_results:
                    doc_type_results[doc_type] = []
                doc_type_results[doc_type].append(result)
            
            # Calculate statistics for each document type
            for doc_type, results in doc_type_results.items():
                processing_times = [r.get('processing_time', 0) for r in results if r.get('processing_time') is not None]
                accuracies = [r.get('accuracy', 0) for r in results if r.get('accuracy') is not None]
                
                summary['document_types'][doc_type] = {
                    'count': len(results),
                    'processing_time': {
                        'mean': np.mean(processing_times) if processing_times else 0,
                        'median': np.median(processing_times) if processing_times else 0,
                        'min': np.min(processing_times) if processing_times else 0,
                        'max': np.max(processing_times) if processing_times else 0
                    },
                    'accuracy': {
                        'mean': np.mean(accuracies) if accuracies else 0,
                        'min': np.min(accuracies) if accuracies else 0
                    }
                }
            
            return summary
        
        def save_to_file(self, file_path):
            """Save test results to a JSON file."""
            summary = self.get_summary()
            
            # Add timestamp
            summary['timestamp'] = datetime.now().isoformat()
            
            with open(file_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            return file_path
    
    return ResultCollector()


# ===== Mock OCR Service Fixtures =====

@pytest.fixture(scope="function")
def mock_ocr_service_for_performance():
    """Create a mock OCR service for performance testing."""
    with patch('services.ocr_service.OCRService') as MockOCRService:
        mock_ocr_svc = MagicMock()
        MockOCRService.return_value = mock_ocr_svc
        
        # Setup mock methods
        mock_ocr_svc.initialize = MagicMock(return_value=True)
        mock_ocr_svc.process_document = MagicMock()
        mock_ocr_svc.close = MagicMock()
        
        # Add method to simulate OCR processing with configurable performance characteristics
        def simulate_ocr_processing(document_path, document_type=DocumentType.APPLICATION, 
                                   processing_time=None, confidence=0.95, accuracy=0.99):
            """Simulate OCR processing with configurable performance characteristics.
            
            Args:
                document_path: Path to the document to process
                document_type: Type of document (from DocumentType enum)
                processing_time: Processing time in seconds (if None, calculated based on document size)
                confidence: Confidence score for extracted fields (0.0-1.0)
                accuracy: Accuracy of extraction (0.0-1.0)
                
            Returns:
                ExtractedData: Simulated extraction result
            """
            # Calculate processing time based on document size if not specified
            if processing_time is None:
                # Get document size in MB
                doc_size_mb = os.path.getsize(document_path) / (1024 * 1024) if os.path.exists(document_path) else 1.0
                
                # Base processing time on document size and type
                base_time = 0.5  # Base processing time in seconds
                type_factor = 1.0  # Default factor
                
                if document_type == DocumentType.APPLICATION:
                    type_factor = 1.0
                elif document_type == DocumentType.TAX_RETURN:
                    type_factor = 1.5  # Tax returns are more complex
                elif document_type == DocumentType.BANK_STATEMENT:
                    type_factor = 2.0  # Bank statements are even more complex
                
                # Calculate processing time
                processing_time = base_time + (doc_size_mb * type_factor)
                
                # Add some randomness
                processing_time *= random.uniform(0.8, 1.2)
            
            # Simulate processing delay
            time.sleep(processing_time)
            
            # Create sample extraction results based on document type
            extracted_fields = []
            
            if document_type == DocumentType.APPLICATION:
                # Simulate accuracy by potentially introducing errors
                business_name = "Dollar Funding LLC"
                tax_id = "12-3456789"
                address = "123 Main St, New York, NY 10001"
                requested_amount = "50000"
                
                if random.random() > accuracy:
                    # Introduce an error in one of the fields
                    error_field = random.choice(["business_name", "tax_id", "address", "requested_amount"])
                    if error_field == "business_name":
                        business_name = "Dollar Fundinq LLC"  # Introduce OCR error (q instead of g)
                    elif error_field == "tax_id":
                        tax_id = "12-3456788"  # Introduce OCR error (8 instead of 9)
                    elif error_field == "address":
                        address = "123 Main St, New York, NY 10002"  # Introduce OCR error (2 instead of 1)
                    elif error_field == "requested_amount":
                        requested_amount = "5000"  # Introduce OCR error (missing 0)
                
                extracted_fields = [
                    ExtractedField(name="business_name", value=business_name, confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="tax_id", value=tax_id, confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="address", value=address, confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="requested_amount", value=requested_amount, confidence=ConfidenceScore(confidence)),
                ]
            elif document_type == DocumentType.TAX_RETURN:
                extracted_fields = [
                    ExtractedField(name="tax_year", value="2022", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="gross_income", value="250000", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="net_income", value="75000", confidence=ConfidenceScore(confidence)),
                ]
            elif document_type == DocumentType.BANK_STATEMENT:
                extracted_fields = [
                    ExtractedField(name="account_number", value="****1234", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="statement_date", value="2023-01-15", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="ending_balance", value="35678.90", confidence=ConfidenceScore(confidence)),
                ]
            
            # Create extraction result
            extraction_result = ExtractedData(
                document_type=document_type,
                fields=extracted_fields,
                metadata={
                    "filename": os.path.basename(document_path),
                    "processing_time": processing_time,
                    "model_version": "1.0.0"
                }
            )
            
            return extraction_result
        
        mock_ocr_svc.process_document.side_effect = simulate_ocr_processing
        mock_ocr_svc.simulate_ocr_processing = simulate_ocr_processing
        
        yield mock_ocr_svc


# ===== Performance Test Configuration Fixtures =====

@pytest.fixture(scope="function")
def performance_test_config():
    """Fixture to provide performance test configuration."""
    return {
        'iterations': PERFORMANCE_TEST_ITERATIONS,
        'warmup': PERFORMANCE_TEST_WARMUP,
        'cooldown': PERFORMANCE_TEST_COOLDOWN,
        'max_concurrent_processes': MAX_CONCURRENT_PROCESSES,
        'memory_threshold_mb': MEMORY_THRESHOLD_MB,
        'gpu_memory_threshold_mb': GPU_MEMORY_THRESHOLD_MB,
        'processing_time_threshold_sec': PROCESSING_TIME_THRESHOLD_SEC,
        'accuracy_threshold': ACCURACY_THRESHOLD
    }


@pytest.fixture(scope="function")
def performance_test_runner():
    """Fixture to run a performance test with monitoring and result collection."""
    def _run_performance_test(test_func, test_name, document_path, document_type=DocumentType.APPLICATION,
                             expected_data=None, resource_monitor=None, result_collector=None,
                             performance_metrics=None, config=None):
        """Run a performance test with monitoring and result collection.
        
        Args:
            test_func: Function to test (should process a document and return ExtractedData)
            test_name: Name of the test
            document_path: Path to the document to process
            document_type: Type of document (from DocumentType enum)
            expected_data: Dictionary of expected field values for accuracy validation
            resource_monitor: ResourceMonitor instance for resource monitoring
            result_collector: ResultCollector instance for result collection
            performance_metrics: PerformanceMetrics instance for performance metrics
            config: Performance test configuration
            
        Returns:
            dict: Test results
        """
        # Use default instances if not provided
        if resource_monitor is None:
            resource_monitor = ResourceMonitor()
        
        if result_collector is None:
            result_collector = ResultCollector()
        
        if performance_metrics is None:
            performance_metrics = PerformanceMetrics()
        
        if config is None:
            config = {
                'processing_time_threshold_sec': PROCESSING_TIME_THRESHOLD_SEC,
                'accuracy_threshold': ACCURACY_THRESHOLD
            }
        
        # Start resource monitoring
        resource_monitor.start()
        
        # Start performance timer
        performance_metrics.start_timer()
        
        # Run the test function
        try:
            extraction_result = test_func(document_path, document_type)
        except Exception as e:
            logger.error(f"Error running test {test_name}: {e}")
            extraction_result = None
        
        # Stop performance timer
        processing_time = performance_metrics.stop_timer()
        
        # Stop resource monitoring
        resource_usage = resource_monitor.stop()
        
        # Calculate accuracy if expected data is provided
        accuracy = None
        if expected_data is not None and extraction_result is not None:
            accuracy_validator = _accuracy_validator(extraction_result, expected_data)
            accuracy, field_results = accuracy_validator
        
        # Add result to collector
        result = result_collector.add_result(
            test_name=test_name,
            document_type=document_type,
            document_path=document_path,
            extraction_result=extraction_result,
            accuracy=accuracy,
            processing_time=processing_time,
            resource_usage=resource_usage
        )
        
        # Check against thresholds
        test_passed = True
        failure_reasons = []
        
        if processing_time is not None and processing_time > config['processing_time_threshold_sec']:
            test_passed = False
            failure_reasons.append(f"Processing time {processing_time:.2f}s exceeds threshold {config['processing_time_threshold_sec']}s")
        
        if accuracy is not None and accuracy < config['accuracy_threshold']:
            test_passed = False
            failure_reasons.append(f"Accuracy {accuracy:.2f} is below threshold {config['accuracy_threshold']}")
        
        if resource_usage and 'memory_mb' in resource_usage and 'max' in resource_usage['memory_mb']:
            memory_usage_mb = resource_usage['memory_mb']['max']
            if memory_usage_mb > MEMORY_THRESHOLD_MB:
                test_passed = False
                failure_reasons.append(f"Memory usage {memory_usage_mb:.2f}MB exceeds threshold {MEMORY_THRESHOLD_MB}MB")
        
        if resource_usage and 'gpu_memory_mb' in resource_usage and 'max' in resource_usage['gpu_memory_mb']:
            gpu_memory_mb = resource_usage['gpu_memory_mb']['max']
            if gpu_memory_mb > GPU_MEMORY_THRESHOLD_MB:
                test_passed = False
                failure_reasons.append(f"GPU memory usage {gpu_memory_mb:.2f}MB exceeds threshold {GPU_MEMORY_THRESHOLD_MB}MB")
        
        # Add test result
        result['test_passed'] = test_passed
        result['failure_reasons'] = failure_reasons
        
        return result
    
    return _run_performance_test


# Helper function for accuracy validation
def _accuracy_validator(extraction_result, expected_data, field_weights=None):
    """Validate OCR extraction accuracy against expected data.
    
    Args:
        extraction_result: ExtractedData object from OCR processing
        expected_data: Dictionary of expected field values
        field_weights: Dictionary of field weights for weighted accuracy calculation
        
    Returns:
        tuple: (accuracy_score, field_results)
    """
    if not isinstance(extraction_result, ExtractedData):
        return 0.0, {}
    
    # Default to equal weights if not provided
    if field_weights is None:
        field_weights = {field: 1.0 for field in expected_data.keys()}
    
    # Normalize weights to sum to 1.0
    total_weight = sum(field_weights.values())
    normalized_weights = {k: v / total_weight for k, v in field_weights.items()}
    
    # Extract fields from result
    extracted_fields = {field.name: field.value for field in extraction_result.fields}
    
    # Calculate accuracy for each field
    field_results = {}
    weighted_accuracy = 0.0
    
    for field_name, expected_value in expected_data.items():
        if field_name in extracted_fields:
            extracted_value = extracted_fields[field_name]
            
            # Calculate field accuracy (exact match for now)
            field_accuracy = 1.0 if extracted_value == expected_value else 0.0
            
            # Get field confidence
            field_confidence = next((field.confidence.value for field in extraction_result.fields 
                                    if field.name == field_name), 0.0)
            
            # Record field result
            field_results[field_name] = {
                'expected': expected_value,
                'extracted': extracted_value,
                'accuracy': field_accuracy,
                'confidence': field_confidence,
                'weight': normalized_weights.get(field_name, 0.0)
            }
            
            # Add to weighted accuracy
            weighted_accuracy += field_accuracy * normalized_weights.get(field_name, 0.0)
        else:
            # Field not found in extraction result
            field_results[field_name] = {
                'expected': expected_value,
                'extracted': None,
                'accuracy': 0.0,
                'confidence': 0.0,
                'weight': normalized_weights.get(field_name, 0.0)
            }
    
    return weighted_accuracy, field_results