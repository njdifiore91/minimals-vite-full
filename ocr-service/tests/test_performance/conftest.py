#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Conftest file for OCR Service performance tests.

This file provides shared test fixtures and utilities for performance testing of the OCR Service.
It includes fixtures for test document datasets, performance measurement, GPU monitoring,
load generation, and result collection to enable consistent performance testing across all test modules.

The fixtures in this file support the following requirements:
- Process applications in under 5 minutes from receipt to completion
- Maintain 99% data extraction accuracy through AI and machine learning
- Support GPU acceleration with at least 8GB VRAM
- Validate processing speed, resource usage, and accuracy metrics under various conditions
"""

import os
import time
import json
import logging
import threading
import tempfile
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Callable, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import numpy as np
import pynvml
import tensorflow as tf
from pytest_benchmark.fixture import BenchmarkFixture

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MAX_PROCESSING_TIME_SECONDS = 300  # 5 minutes max processing time
ACCURACY_THRESHOLD = 0.99  # 99% accuracy threshold
MIN_GPU_MEMORY_MB = 8 * 1024  # 8GB minimum VRAM

# ===============================================================
# Configuration Fixtures
# ===============================================================

@pytest.fixture(scope="session")
def performance_config():
    """Provides configuration parameters for performance tests."""
    return {
        "max_processing_time": MAX_PROCESSING_TIME_SECONDS,
        "accuracy_threshold": ACCURACY_THRESHOLD,
        "min_gpu_memory_mb": MIN_GPU_MEMORY_MB,
        "concurrent_requests": [1, 5, 10, 20],  # Different concurrency levels to test
        "document_sizes": ["small", "medium", "large"],
        "document_types": ["typed", "handwritten", "mixed"],
        "test_durations": {  # Duration in seconds for different test types
            "quick": 10,
            "standard": 60,
            "extended": 300
        }
    }


@pytest.fixture(scope="session")
def test_data_dir():
    """Returns the path to the test data directory."""
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "test_data"
    if not data_dir.exists():
        raise FileNotFoundError(f"Test data directory not found: {data_dir}")
    return data_dir


# ===============================================================
# Test Document Fixtures
# ===============================================================

@pytest.fixture(scope="session")
def document_metadata(test_data_dir):
    """Loads the metadata for all test documents."""
    metadata_file = test_data_dir / "metadata.json"
    with open(metadata_file, "r") as f:
        return json.load(f)


@pytest.fixture(params=["typed", "handwritten", "mixed"])
def document_type(request):
    """Parametrized fixture for different document types."""
    return request.param


@pytest.fixture(params=["small", "medium", "large"])
def document_size(request):
    """Parametrized fixture for different document sizes."""
    return request.param


@pytest.fixture
def test_documents(test_data_dir, document_metadata, document_type, document_size):
    """Provides test documents of specified type and size."""
    # Filter documents by type and size
    filtered_docs = []
    for doc_id, metadata in document_metadata.items():
        if metadata["type"] == document_type and metadata["size"] == document_size:
            doc_path = test_data_dir / metadata["path"]
            if doc_path.exists():
                filtered_docs.append({
                    "id": doc_id,
                    "path": str(doc_path),
                    "metadata": metadata,
                    "expected_text": metadata.get("expected_text", {}),
                    "expected_fields": metadata.get("expected_fields", {}),
                    "expected_confidence": metadata.get("expected_confidence", {})
                })
    
    if not filtered_docs:
        pytest.skip(f"No test documents found for type={document_type}, size={document_size}")
    
    return filtered_docs


@pytest.fixture
def batch_test_documents(test_data_dir, document_metadata):
    """Provides a batch of mixed test documents for batch processing tests."""
    # Create a representative batch with different document types and sizes
    batch_docs = []
    for doc_id, metadata in document_metadata.items():
        doc_path = test_data_dir / metadata["path"]
        if doc_path.exists():
            batch_docs.append({
                "id": doc_id,
                "path": str(doc_path),
                "metadata": metadata,
                "expected_text": metadata.get("expected_text", {}),
                "expected_fields": metadata.get("expected_fields", {}),
                "expected_confidence": metadata.get("expected_confidence", {})
            })
            # Limit batch size to a reasonable number
            if len(batch_docs) >= 20:
                break
    
    if not batch_docs:
        pytest.skip("No test documents found for batch processing")
    
    return batch_docs


# ===============================================================
# Performance Measurement Fixtures
# ===============================================================

@pytest.fixture
def benchmark_ocr_processing(benchmark: BenchmarkFixture):
    """Fixture for benchmarking OCR processing functions.
    
    This fixture uses pytest-benchmark to measure the performance of OCR processing
    functions with precise timing and statistical analysis.
    
    Args:
        benchmark: The pytest-benchmark fixture
        
    Returns:
        A function that can be used to benchmark OCR processing functions
    """
    def _benchmark_function(func, *args, **kwargs):
        """Benchmark an OCR processing function.
        
        Args:
            func: The function to benchmark
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the benchmarked function
        """
        # Use pytest-benchmark to measure the function's performance
        result = benchmark(func, *args, **kwargs)
        
        # Log benchmark results
        logger.info(f"Benchmark results for {func.__name__}:")
        logger.info(f"  Min: {benchmark.stats['min']:.4f}s")
        logger.info(f"  Max: {benchmark.stats['max']:.4f}s")
        logger.info(f"  Mean: {benchmark.stats['mean']:.4f}s")
        logger.info(f"  StdDev: {benchmark.stats['stddev']:.4f}s")
        
        # Assert that the function meets the performance requirements
        assert benchmark.stats['max'] <= MAX_PROCESSING_TIME_SECONDS, \
            f"Maximum processing time ({benchmark.stats['max']:.2f}s) exceeds limit ({MAX_PROCESSING_TIME_SECONDS}s)"
        
        return result
    
    return _benchmark_function

@pytest.fixture
def performance_metrics():
    """Fixture for collecting and analyzing performance metrics."""
    class PerformanceMetrics:
        def __init__(self):
            self.processing_times = []
            self.accuracy_scores = []
            self.throughput_values = []
            self.latency_values = []
            self.start_time = None
            self.end_time = None
        
        def start_measurement(self):
            """Start the performance measurement."""
            self.start_time = time.time()
            return self.start_time
        
        def end_measurement(self):
            """End the performance measurement."""
            self.end_time = time.time()
            return self.end_time
        
        def add_processing_time(self, processing_time):
            """Add a processing time measurement."""
            self.processing_times.append(processing_time)
        
        def add_accuracy_score(self, accuracy_score):
            """Add an accuracy score measurement."""
            self.accuracy_scores.append(accuracy_score)
        
        def add_throughput(self, docs_processed, time_taken):
            """Add a throughput measurement (docs/second)."""
            if time_taken > 0:
                self.throughput_values.append(docs_processed / time_taken)
        
        def add_latency(self, latency):
            """Add a latency measurement."""
            self.latency_values.append(latency)
        
        def get_total_duration(self):
            """Get the total duration of the test."""
            if self.start_time is None or self.end_time is None:
                return 0
            return self.end_time - self.start_time
        
        def get_avg_processing_time(self):
            """Get the average processing time."""
            if not self.processing_times:
                return 0
            return statistics.mean(self.processing_times)
        
        def get_avg_accuracy(self):
            """Get the average accuracy score."""
            if not self.accuracy_scores:
                return 0
            return statistics.mean(self.accuracy_scores)
        
        def get_avg_throughput(self):
            """Get the average throughput (docs/second)."""
            if not self.throughput_values:
                return 0
            return statistics.mean(self.throughput_values)
        
        def get_avg_latency(self):
            """Get the average latency."""
            if not self.latency_values:
                return 0
            return statistics.mean(self.latency_values)
        
        def get_percentile_latency(self, percentile=95):
            """Get the specified percentile latency."""
            if not self.latency_values:
                return 0
            return np.percentile(self.latency_values, percentile)
        
        def get_summary(self):
            """Get a summary of all performance metrics."""
            return {
                "total_duration": self.get_total_duration(),
                "avg_processing_time": self.get_avg_processing_time(),
                "avg_accuracy": self.get_avg_accuracy(),
                "avg_throughput": self.get_avg_throughput(),
                "avg_latency": self.get_avg_latency(),
                "p95_latency": self.get_percentile_latency(95),
                "p99_latency": self.get_percentile_latency(99),
                "min_processing_time": min(self.processing_times) if self.processing_times else 0,
                "max_processing_time": max(self.processing_times) if self.processing_times else 0,
                "min_accuracy": min(self.accuracy_scores) if self.accuracy_scores else 0,
                "max_accuracy": max(self.accuracy_scores) if self.accuracy_scores else 0,
                "sample_count": len(self.processing_times)
            }
        
        def assert_performance_requirements(self):
            """Assert that performance requirements are met."""
            avg_processing_time = self.get_avg_processing_time()
            avg_accuracy = self.get_avg_accuracy()
            max_processing_time = max(self.processing_times) if self.processing_times else 0
            
            # Assert processing time requirements
            assert avg_processing_time <= MAX_PROCESSING_TIME_SECONDS, \
                f"Average processing time ({avg_processing_time:.2f}s) exceeds maximum allowed ({MAX_PROCESSING_TIME_SECONDS}s)"
            
            # Assert accuracy requirements
            assert avg_accuracy >= ACCURACY_THRESHOLD, \
                f"Average accuracy ({avg_accuracy:.2%}) is below threshold ({ACCURACY_THRESHOLD:.2%})"
            
            # Assert maximum processing time
            assert max_processing_time <= MAX_PROCESSING_TIME_SECONDS, \
                f"Maximum processing time ({max_processing_time:.2f}s) exceeds maximum allowed ({MAX_PROCESSING_TIME_SECONDS}s)"
    
    return PerformanceMetrics()


@pytest.fixture
def time_measurement():
    """Fixture for measuring execution time of code blocks."""
    class TimeMeasurement:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.end_time = time.time()
        
        @property
        def duration(self):
            """Get the duration in seconds."""
            if self.start_time is None or self.end_time is None:
                return 0
            return self.end_time - self.start_time
    
    return TimeMeasurement


# ===============================================================
# GPU Monitoring Fixtures
# ===============================================================

@pytest.fixture(scope="session")
def gpu_available():
    """Check if a CUDA-compatible GPU is available."""
    try:
        # Check if TensorFlow can see a GPU
        gpus = tf.config.list_physical_devices('GPU')
        if not gpus:
            pytest.skip("No GPU available for testing")
        
        # Initialize NVML for GPU monitoring
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count == 0:
            pytest.skip("No NVIDIA GPU available for testing")
        
        # Check if GPU has enough memory
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        total_memory_mb = info.total / (1024 * 1024)
        if total_memory_mb < MIN_GPU_MEMORY_MB:
            pytest.skip(f"GPU has insufficient memory: {total_memory_mb:.0f}MB < {MIN_GPU_MEMORY_MB}MB required")
        
        return True
    except Exception as e:
        pytest.skip(f"Error checking GPU availability: {str(e)}")
        return False
    finally:
        try:
            pynvml.nvmlShutdown()
        except:
            pass


@pytest.fixture
def gpu_requirements():
    """Fixture that validates GPU requirements for OCR processing.
    
    Checks that the available GPU meets the minimum requirements for OCR processing:
    - CUDA-compatible GPU is available
    - GPU has at least 8GB VRAM
    - TensorFlow can access the GPU
    
    Returns:
        Dict with GPU information
    """
    # Skip test if no GPU is available
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        pytest.skip("No GPU available for testing")
    
    # Initialize NVML for GPU monitoring
    pynvml.nvmlInit()
    try:
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count == 0:
            pytest.skip("No NVIDIA GPU available for testing")
        
        gpu_info = {}
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            
            # Get GPU name
            gpu_info[f'gpu_{i}_name'] = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
            
            # Get memory info
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpu_info[f'gpu_{i}_memory_total_mb'] = mem_info.total / (1024 * 1024)
            gpu_info[f'gpu_{i}_memory_free_mb'] = mem_info.free / (1024 * 1024)
            
            # Check if GPU has enough memory
            if mem_info.total / (1024 * 1024) < MIN_GPU_MEMORY_MB:
                pytest.skip(f"GPU {i} has insufficient memory: {mem_info.total / (1024 * 1024):.0f}MB < {MIN_GPU_MEMORY_MB}MB required")
        
        # Get CUDA version
        cuda_version = tf.sysconfig.get_build_info()["cuda_version"]
        gpu_info['cuda_version'] = cuda_version
        
        return gpu_info
    finally:
        pynvml.nvmlShutdown()

@pytest.fixture
def gpu_monitor(gpu_available):
    """Fixture for monitoring GPU metrics during tests."""
    class GPUMonitor:
        def __init__(self):
            self.monitoring = False
            self.monitoring_thread = None
            self.stop_event = threading.Event()
            self.metrics = {
                "memory_used": [],
                "memory_total": [],
                "utilization": [],
                "temperature": [],
                "power_usage": [],
                "timestamps": []
            }
            self.sampling_interval = 0.1  # seconds
            pynvml.nvmlInit()
            self.device_count = pynvml.nvmlDeviceGetCount()
            self.handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(self.device_count)]
        
        def _monitor_gpu(self):
            """Background thread function to monitor GPU metrics."""
            while not self.stop_event.is_set():
                try:
                    timestamp = time.time()
                    memory_used = 0
                    memory_total = 0
                    utilization = 0
                    temperature = 0
                    power_usage = 0
                    
                    for handle in self.handles:
                        # Memory info
                        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        memory_used += mem_info.used / (1024 * 1024)  # MB
                        memory_total += mem_info.total / (1024 * 1024)  # MB
                        
                        # Utilization info
                        util_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
                        utilization += util_info.gpu  # %
                        
                        # Temperature
                        temperature += pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                        
                        # Power usage
                        power_usage += pynvml.nvmlDeviceGetPowerUsage(handle) / 1000  # W
                    
                    # Average across all GPUs
                    if self.device_count > 0:
                        memory_used /= self.device_count
                        memory_total /= self.device_count
                        utilization /= self.device_count
                        temperature /= self.device_count
                        power_usage /= self.device_count
                    
                    # Record metrics
                    self.metrics["memory_used"].append(memory_used)
                    self.metrics["memory_total"].append(memory_total)
                    self.metrics["utilization"].append(utilization)
                    self.metrics["temperature"].append(temperature)
                    self.metrics["power_usage"].append(power_usage)
                    self.metrics["timestamps"].append(timestamp)
                    
                    time.sleep(self.sampling_interval)
                except Exception as e:
                    logger.error(f"Error monitoring GPU: {str(e)}")
                    time.sleep(1)  # Wait a bit longer on error
        
        def start(self):
            """Start GPU monitoring."""
            if self.monitoring:
                return
            
            self.stop_event.clear()
            self.monitoring_thread = threading.Thread(target=self._monitor_gpu, daemon=True)
            self.monitoring_thread.start()
            self.monitoring = True
        
        def stop(self):
            """Stop GPU monitoring."""
            if not self.monitoring:
                return
            
            self.stop_event.set()
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=2)
            self.monitoring = False
        
        def get_metrics(self):
            """Get the collected GPU metrics."""
            return self.metrics
        
        def get_summary(self):
            """Get a summary of GPU metrics."""
            if not self.metrics["memory_used"]:
                return {}
            
            return {
                "avg_memory_used_mb": statistics.mean(self.metrics["memory_used"]),
                "max_memory_used_mb": max(self.metrics["memory_used"]),
                "avg_memory_utilization": statistics.mean(self.metrics["memory_used"]) / statistics.mean(self.metrics["memory_total"]) if statistics.mean(self.metrics["memory_total"]) > 0 else 0,
                "avg_gpu_utilization": statistics.mean(self.metrics["utilization"]),
                "max_gpu_utilization": max(self.metrics["utilization"]),
                "avg_temperature": statistics.mean(self.metrics["temperature"]),
                "max_temperature": max(self.metrics["temperature"]),
                "avg_power_usage": statistics.mean(self.metrics["power_usage"]),
                "max_power_usage": max(self.metrics["power_usage"]),
                "samples": len(self.metrics["timestamps"])
            }
        
        def __enter__(self):
            self.start()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.stop()
            pynvml.nvmlShutdown()
    
    monitor = GPUMonitor()
    yield monitor
    monitor.stop()
    try:
        pynvml.nvmlShutdown()
    except:
        pass


# ===============================================================
# Load Generation Fixtures
# ===============================================================

@pytest.fixture
def sustained_load_test():
    """Fixture for running sustained load tests over a specified duration.
    
    This fixture helps test the OCR service under sustained load for a specified
    duration, which is important for validating stability and performance
    degradation over time.
    
    Returns:
        A function that runs a sustained load test
    """
    def _run_sustained_test(test_func, duration_seconds, concurrency=1, **kwargs):
        """Run a test function under sustained load for a specified duration.
        
        Args:
            test_func: The test function to run repeatedly
            duration_seconds: How long to run the test (seconds)
            concurrency: Number of concurrent executions
            **kwargs: Additional arguments to pass to the test function
            
        Returns:
            Dict with test results
        """
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        results = []
        errors = []
        iterations = 0
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            while time.time() < end_time:
                futures = []
                for _ in range(concurrency):
                    futures.append(executor.submit(test_func, **kwargs))
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        errors.append(e)
                
                iterations += 1
        
        actual_duration = time.time() - start_time
        
        return {
            "iterations": iterations,
            "successful_tests": len(results),
            "failed_tests": len(errors),
            "duration": actual_duration,
            "tests_per_second": len(results) / actual_duration if actual_duration > 0 else 0,
            "success_rate": len(results) / (len(results) + len(errors)) if (len(results) + len(errors)) > 0 else 0,
            "results": results,
            "errors": [str(e) for e in errors]
        }
    
    return _run_sustained_test

@pytest.fixture
def load_generator():
    """Fixture for generating concurrent load for performance testing."""
    class LoadGenerator:
        def __init__(self):
            self.results = []
            self.errors = []
            self.start_time = None
            self.end_time = None
        
        def run_concurrent(self, func, args_list, concurrency=1, timeout=None):
            """Run a function concurrently with different arguments.
            
            Args:
                func: The function to run
                args_list: List of argument tuples to pass to the function
                concurrency: Number of concurrent workers
                timeout: Timeout in seconds
            
            Returns:
                List of results
            """
            self.results = []
            self.errors = []
            self.start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(func, *args) for args in args_list]
                for future in as_completed(futures, timeout=timeout):
                    try:
                        result = future.result()
                        self.results.append(result)
                    except Exception as e:
                        self.errors.append(e)
            
            self.end_time = time.time()
            return self.results
        
        def get_throughput(self):
            """Calculate throughput (operations/second)."""
            if self.start_time is None or self.end_time is None:
                return 0
            duration = self.end_time - self.start_time
            if duration <= 0:
                return 0
            return len(self.results) / duration
        
        def get_success_rate(self):
            """Calculate success rate."""
            total = len(self.results) + len(self.errors)
            if total <= 0:
                return 0
            return len(self.results) / total
        
        def get_summary(self):
            """Get a summary of the load test."""
            return {
                "total_operations": len(self.results) + len(self.errors),
                "successful_operations": len(self.results),
                "failed_operations": len(self.errors),
                "success_rate": self.get_success_rate(),
                "throughput": self.get_throughput(),
                "duration": (self.end_time - self.start_time) if self.start_time and self.end_time else 0
            }
    
    return LoadGenerator()


# ===============================================================
# Result Collection Fixtures
# ===============================================================

@pytest.fixture
def performance_report():
    """Fixture for generating comprehensive performance test reports.
    
    This fixture collects performance metrics from various sources (GPU monitoring,
    benchmark results, accuracy calculations) and generates a comprehensive report.
    
    Returns:
        A function that generates performance reports
    """
    def _generate_report(test_name, performance_metrics=None, gpu_metrics=None, benchmark_stats=None, accuracy_results=None):
        """Generate a comprehensive performance report.
        
        Args:
            test_name: Name of the test
            performance_metrics: Performance metrics from performance_metrics fixture
            gpu_metrics: GPU metrics from gpu_monitor fixture
            benchmark_stats: Benchmark statistics from pytest-benchmark
            accuracy_results: Accuracy calculation results
            
        Returns:
            Dict with comprehensive performance report
        """
        report = {
            "test_name": test_name,
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "requirements": {
                "max_processing_time": MAX_PROCESSING_TIME_SECONDS,
                "accuracy_threshold": ACCURACY_THRESHOLD,
                "min_gpu_memory_mb": MIN_GPU_MEMORY_MB
            }
        }
        
        # Add performance metrics if available
        if performance_metrics:
            report["performance"] = performance_metrics.get_summary() if hasattr(performance_metrics, "get_summary") else performance_metrics
        
        # Add GPU metrics if available
        if gpu_metrics:
            report["gpu"] = gpu_metrics.get_summary() if hasattr(gpu_metrics, "get_summary") else gpu_metrics
        
        # Add benchmark stats if available
        if benchmark_stats:
            report["benchmark"] = {
                "min": benchmark_stats.get("min"),
                "max": benchmark_stats.get("max"),
                "mean": benchmark_stats.get("mean"),
                "median": benchmark_stats.get("median"),
                "stddev": benchmark_stats.get("stddev"),
                "rounds": benchmark_stats.get("rounds"),
                "iterations": benchmark_stats.get("iterations")
            }
        
        # Add accuracy results if available
        if accuracy_results:
            report["accuracy"] = accuracy_results
        
        # Add pass/fail status based on requirements
        report["status"] = "PASS"
        report["failures"] = []
        
        # Check processing time requirement
        if performance_metrics and hasattr(performance_metrics, "get_avg_processing_time"):
            avg_time = performance_metrics.get_avg_processing_time()
            if avg_time > MAX_PROCESSING_TIME_SECONDS:
                report["status"] = "FAIL"
                report["failures"].append(f"Average processing time ({avg_time:.2f}s) exceeds maximum allowed ({MAX_PROCESSING_TIME_SECONDS}s)")
        
        # Check accuracy requirement
        if performance_metrics and hasattr(performance_metrics, "get_avg_accuracy"):
            avg_accuracy = performance_metrics.get_avg_accuracy()
            if avg_accuracy < ACCURACY_THRESHOLD:
                report["status"] = "FAIL"
                report["failures"].append(f"Average accuracy ({avg_accuracy:.2%}) is below threshold ({ACCURACY_THRESHOLD:.2%})")
        
        # Save report to file
        report_dir = Path("performance_reports")
        report_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        report_file = report_dir / f"{test_name}_{timestamp}.json"
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Performance report saved to {report_file}")
        return report
    
    return _generate_report

@pytest.fixture
def result_collector():
    """Fixture for collecting and analyzing test results."""
    class ResultCollector:
        def __init__(self):
            self.results = []
            self.test_metadata = {}
        
        def set_test_metadata(self, **kwargs):
            """Set metadata for the current test."""
            self.test_metadata.update(kwargs)
        
        def add_result(self, result):
            """Add a test result."""
            self.results.append({
                **self.test_metadata,
                "timestamp": time.time(),
                "result": result
            })
        
        def get_results(self):
            """Get all collected results."""
            return self.results
        
        def save_results(self, filename=None):
            """Save results to a JSON file."""
            if filename is None:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"performance_results_{timestamp}.json"
            
            with open(filename, "w") as f:
                json.dump(self.results, f, indent=2)
            
            return filename
        
        def clear(self):
            """Clear all results."""
            self.results = []
            self.test_metadata = {}
    
    return ResultCollector()


@pytest.fixture
def accuracy_calculator():
    """Fixture for calculating OCR accuracy metrics."""
    class AccuracyCalculator:
        @staticmethod
        def calculate_text_accuracy(extracted_text, expected_text):
            """Calculate text accuracy using character-level comparison."""
            if not expected_text:
                return 1.0  # No expected text to compare against
            
            # Simple character-level accuracy
            extracted = extracted_text.lower()
            expected = expected_text.lower()
            
            # Calculate Levenshtein distance
            m, n = len(extracted), len(expected)
            if m == 0 or n == 0:
                return 0.0 if max(m, n) > 0 else 1.0
            
            d = [[0] * (n + 1) for _ in range(m + 1)]
            for i in range(m + 1):
                d[i][0] = i
            for j in range(n + 1):
                d[0][j] = j
            
            for j in range(1, n + 1):
                for i in range(1, m + 1):
                    if extracted[i-1] == expected[j-1]:
                        d[i][j] = d[i-1][j-1]
                    else:
                        d[i][j] = min(d[i-1][j], d[i][j-1], d[i-1][j-1]) + 1
            
            distance = d[m][n]
            max_len = max(m, n)
            accuracy = 1.0 - (distance / max_len) if max_len > 0 else 1.0
            return accuracy
        
        @staticmethod
        def calculate_field_accuracy(extracted_fields, expected_fields):
            """Calculate field extraction accuracy."""
            if not expected_fields:
                return 1.0  # No expected fields to compare against
            
            correct_fields = 0
            total_fields = len(expected_fields)
            
            for field_name, expected_value in expected_fields.items():
                if field_name in extracted_fields:
                    extracted_value = extracted_fields[field_name]
                    # Calculate similarity for this field
                    field_accuracy = AccuracyCalculator.calculate_text_accuracy(extracted_value, expected_value)
                    if field_accuracy >= 0.8:  # Consider field correct if accuracy is at least 80%
                        correct_fields += 1
            
            return correct_fields / total_fields if total_fields > 0 else 1.0
        
        @staticmethod
        def calculate_overall_accuracy(extracted_data, expected_data):
            """Calculate overall extraction accuracy."""
            text_accuracy = AccuracyCalculator.calculate_text_accuracy(
                extracted_data.get("text", ""), expected_data.get("expected_text", "")
            )
            
            field_accuracy = AccuracyCalculator.calculate_field_accuracy(
                extracted_data.get("fields", {}), expected_data.get("expected_fields", {})
            )
            
            # Weight field accuracy higher than text accuracy
            return 0.4 * text_accuracy + 0.6 * field_accuracy
    
    return AccuracyCalculator


# ===============================================================
# Utility Functions
# ===============================================================

@pytest.fixture
def ocr_accuracy_validator():
    """Fixture for validating OCR accuracy against requirements.
    
    This fixture provides utilities to validate that OCR results meet the
    required 99% accuracy threshold specified in the technical requirements.
    
    Returns:
        A function that validates OCR accuracy
    """
    def _validate_accuracy(extracted_data, expected_data, accuracy_calculator):
        """Validate that OCR results meet accuracy requirements.
        
        Args:
            extracted_data: The data extracted by OCR
            expected_data: The expected data (ground truth)
            accuracy_calculator: Instance of AccuracyCalculator
            
        Returns:
            Dict with accuracy validation results
        """
        # Calculate overall accuracy
        overall_accuracy = accuracy_calculator.calculate_overall_accuracy(extracted_data, expected_data)
        
        # Calculate text accuracy if text is available
        text_accuracy = None
        if "text" in extracted_data and "expected_text" in expected_data:
            text_accuracy = accuracy_calculator.calculate_text_accuracy(
                extracted_data["text"], expected_data["expected_text"]
            )
        
        # Calculate field accuracy if fields are available
        field_accuracy = None
        if "fields" in extracted_data and "expected_fields" in expected_data:
            field_accuracy = accuracy_calculator.calculate_field_accuracy(
                extracted_data["fields"], expected_data["expected_fields"]
            )
        
        # Validate against accuracy threshold
        meets_requirements = overall_accuracy >= ACCURACY_THRESHOLD
        
        return {
            "overall_accuracy": overall_accuracy,
            "text_accuracy": text_accuracy,
            "field_accuracy": field_accuracy,
            "meets_requirements": meets_requirements,
            "accuracy_threshold": ACCURACY_THRESHOLD,
            "validation_message": (
                f"OCR accuracy ({overall_accuracy:.2%}) meets threshold ({ACCURACY_THRESHOLD:.2%})"
                if meets_requirements else
                f"OCR accuracy ({overall_accuracy:.2%}) below threshold ({ACCURACY_THRESHOLD:.2%})"
            )
        }
    
    return _validate_accuracy

@pytest.fixture
def create_temp_document():
    """Fixture for creating temporary test documents."""
    temp_files = []
    
    def _create_temp_document(content, file_extension=".txt"):
        """Create a temporary document with the given content."""
        fd, path = tempfile.mkstemp(suffix=file_extension)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            temp_files.append(path)
            return path
        except Exception as e:
            os.unlink(path)
            raise e
    
    yield _create_temp_document
    
    # Cleanup temp files
    for path in temp_files:
        try:
            os.unlink(path)
        except:
            pass