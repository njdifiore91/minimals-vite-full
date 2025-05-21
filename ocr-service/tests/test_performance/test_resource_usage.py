import os
import time
import pytest
import psutil
import numpy as np
import tensorflow as tf
import GPUtil
import pynvml
from unittest.mock import patch, MagicMock

# Import OCR service modules
from ocr_service.app import OCRServiceApp
from ocr_service.models.model_factory import ModelFactory
from ocr_service.models.base_model import BaseModel
from ocr_service.utils.tensorflow_utils import setup_gpu, get_available_gpus


@pytest.fixture(scope="module")
def ocr_service_app():
    """Fixture to create and initialize the OCR service application."""
    app = OCRServiceApp()
    app.initialize()
    yield app
    app.shutdown()


@pytest.fixture
def typed_document():
    """Fixture to provide a sample typed document for testing."""
    # Path to a sample typed document in the test data directory
    return os.path.join(os.path.dirname(__file__), "..", "test_data", "typed_documents", "business_documents", "sample_invoice.pdf")


@pytest.fixture
def handwritten_document():
    """Fixture to provide a sample handwritten document for testing."""
    # Path to a sample handwritten document in the test data directory
    return os.path.join(os.path.dirname(__file__), "..", "test_data", "handwritten_documents", "sample_form.pdf")


@pytest.fixture
def mixed_document():
    """Fixture to provide a sample document with mixed content for testing."""
    # Path to a sample mixed content document in the test data directory
    return os.path.join(os.path.dirname(__file__), "..", "test_data", "mixed_documents", "sample_application.pdf")


class ResourceMonitor:
    """Utility class to monitor system resources during OCR processing."""
    
    def __init__(self):
        """Initialize the resource monitor."""
        self.process = psutil.Process(os.getpid())
        self.cpu_percent_samples = []
        self.memory_samples = []
        self.gpu_memory_samples = []
        self.gpu_utilization_samples = []
        self.start_time = None
        self.end_time = None
        
        # Initialize NVIDIA Management Library if available
        try:
            pynvml.nvmlInit()
            self.nvml_initialized = True
            self.gpu_count = pynvml.nvmlDeviceGetCount()
        except Exception:
            self.nvml_initialized = False
            self.gpu_count = 0
    
    def start_monitoring(self):
        """Start resource monitoring."""
        self.start_time = time.time()
        self.cpu_percent_samples = []
        self.memory_samples = []
        self.gpu_memory_samples = []
        self.gpu_utilization_samples = []
    
    def sample_resources(self):
        """Take a sample of current resource usage."""
        # Sample CPU usage
        self.cpu_percent_samples.append(self.process.cpu_percent())
        
        # Sample memory usage
        memory_info = self.process.memory_info()
        self.memory_samples.append({
            'rss': memory_info.rss,  # Resident Set Size
            'vms': memory_info.vms   # Virtual Memory Size
        })
        
        # Sample GPU usage if available
        if self.nvml_initialized and self.gpu_count > 0:
            gpu_samples = []
            utilization_samples = []
            
            for i in range(self.gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                
                gpu_samples.append({
                    'used': memory_info.used,
                    'total': memory_info.total,
                    'percent': (memory_info.used / memory_info.total) * 100
                })
                
                utilization_samples.append({
                    'gpu': utilization.gpu,  # GPU utilization percentage
                    'memory': utilization.memory  # Memory utilization percentage
                })
            
            self.gpu_memory_samples.append(gpu_samples)
            self.gpu_utilization_samples.append(utilization_samples)
    
    def stop_monitoring(self):
        """Stop resource monitoring and return the results."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        # Calculate CPU usage statistics
        cpu_stats = {
            'min': min(self.cpu_percent_samples) if self.cpu_percent_samples else 0,
            'max': max(self.cpu_percent_samples) if self.cpu_percent_samples else 0,
            'avg': np.mean(self.cpu_percent_samples) if self.cpu_percent_samples else 0,
            'samples': self.cpu_percent_samples
        }
        
        # Calculate memory usage statistics
        memory_stats = {
            'rss': {
                'min': min(sample['rss'] for sample in self.memory_samples) if self.memory_samples else 0,
                'max': max(sample['rss'] for sample in self.memory_samples) if self.memory_samples else 0,
                'avg': np.mean([sample['rss'] for sample in self.memory_samples]) if self.memory_samples else 0
            },
            'vms': {
                'min': min(sample['vms'] for sample in self.memory_samples) if self.memory_samples else 0,
                'max': max(sample['vms'] for sample in self.memory_samples) if self.memory_samples else 0,
                'avg': np.mean([sample['vms'] for sample in self.memory_samples]) if self.memory_samples else 0
            }
        }
        
        # Calculate GPU usage statistics if available
        gpu_memory_stats = None
        gpu_utilization_stats = None
        
        if self.gpu_memory_samples and self.gpu_utilization_samples:
            gpu_memory_stats = []
            gpu_utilization_stats = []
            
            for gpu_idx in range(self.gpu_count):
                # Extract data for this GPU
                gpu_memory_data = [sample[gpu_idx]['percent'] for sample in self.gpu_memory_samples]
                gpu_util_data = [sample[gpu_idx]['gpu'] for sample in self.gpu_utilization_samples]
                memory_util_data = [sample[gpu_idx]['memory'] for sample in self.gpu_utilization_samples]
                
                gpu_memory_stats.append({
                    'min': min(gpu_memory_data) if gpu_memory_data else 0,
                    'max': max(gpu_memory_data) if gpu_memory_data else 0,
                    'avg': np.mean(gpu_memory_data) if gpu_memory_data else 0,
                    'samples': gpu_memory_data
                })
                
                gpu_utilization_stats.append({
                    'gpu': {
                        'min': min(gpu_util_data) if gpu_util_data else 0,
                        'max': max(gpu_util_data) if gpu_util_data else 0,
                        'avg': np.mean(gpu_util_data) if gpu_util_data else 0,
                        'samples': gpu_util_data
                    },
                    'memory': {
                        'min': min(memory_util_data) if memory_util_data else 0,
                        'max': max(memory_util_data) if memory_util_data else 0,
                        'avg': np.mean(memory_util_data) if memory_util_data else 0,
                        'samples': memory_util_data
                    }
                })
        
        return {
            'duration': duration,
            'cpu': cpu_stats,
            'memory': memory_stats,
            'gpu_memory': gpu_memory_stats,
            'gpu_utilization': gpu_utilization_stats
        }
    
    def __del__(self):
        """Clean up resources when the monitor is destroyed."""
        if hasattr(self, 'nvml_initialized') and self.nvml_initialized:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass


class TestResourceUsage:
    """Test suite for measuring resource usage during OCR processing."""
    
    def test_memory_usage_during_ocr_processing(self, ocr_service_app, typed_document):
        """Test memory usage during OCR processing of a typed document."""
        # Initialize resource monitor
        monitor = ResourceMonitor()
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Process the document with periodic resource sampling
        result = ocr_service_app.process_document(typed_document)
        for _ in range(10):  # Sample resources 10 times during processing
            monitor.sample_resources()
            time.sleep(0.1)  # Sleep to allow processing to continue
        
        # Stop monitoring and get results
        stats = monitor.stop_monitoring()
        
        # Verify memory usage is within acceptable limits
        # The OCR service should use less than 4GB of RAM for a typical document
        max_memory_usage_gb = stats['memory']['rss']['max'] / (1024 * 1024 * 1024)
        assert max_memory_usage_gb < 4.0, f"Memory usage exceeded 4GB: {max_memory_usage_gb:.2f}GB"
        
        # Verify processing completed successfully
        assert result is not None, "Document processing failed"
    
    def test_gpu_memory_usage(self, ocr_service_app, typed_document):
        """Test GPU memory usage during OCR processing."""
        # Skip test if no GPU is available
        if not tf.config.list_physical_devices('GPU'):
            pytest.skip("No GPU available for testing")
        
        # Initialize resource monitor
        monitor = ResourceMonitor()
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Process the document with periodic resource sampling
        result = ocr_service_app.process_document(typed_document)
        for _ in range(10):  # Sample resources 10 times during processing
            monitor.sample_resources()
            time.sleep(0.1)  # Sleep to allow processing to continue
        
        # Stop monitoring and get results
        stats = monitor.stop_monitoring()
        
        # Verify GPU memory usage is within acceptable limits
        # The OCR service should use less than 80% of available GPU memory
        if stats['gpu_memory'] is not None:
            for gpu_idx, gpu_stats in enumerate(stats['gpu_memory']):
                assert gpu_stats['max'] < 80.0, f"GPU {gpu_idx} memory usage exceeded 80%: {gpu_stats['max']:.2f}%"
        
        # Verify processing completed successfully
        assert result is not None, "Document processing failed"
    
    def test_cpu_usage_during_different_stages(self, ocr_service_app, typed_document):
        """Test CPU usage during different stages of OCR processing."""
        # Initialize resource monitor
        monitor = ResourceMonitor()
        
        # Define processing stages to monitor
        stages = [
            "document_loading",
            "preprocessing",
            "text_recognition",
            "post_processing"
        ]
        
        stage_stats = {}
        
        # Monitor each stage separately
        for stage in stages:
            # Start monitoring
            monitor.start_monitoring()
            
            # Process the specific stage
            with patch.object(ocr_service_app, 'current_stage', stage):
                if stage == "document_loading":
                    ocr_service_app.load_document(typed_document)
                elif stage == "preprocessing":
                    ocr_service_app.preprocess_document()
                elif stage == "text_recognition":
                    ocr_service_app.recognize_text()
                elif stage == "post_processing":
                    ocr_service_app.post_process_results()
            
            # Sample resources during the stage
            for _ in range(5):  # Sample resources 5 times during each stage
                monitor.sample_resources()
                time.sleep(0.1)  # Sleep to allow processing to continue
            
            # Stop monitoring and get results for this stage
            stats = monitor.stop_monitoring()
            stage_stats[stage] = stats
        
        # Verify CPU usage for each stage is within acceptable limits
        for stage, stats in stage_stats.items():
            # Text recognition should be GPU-bound, so CPU usage should be lower
            if stage == "text_recognition" and tf.config.list_physical_devices('GPU'):
                assert stats['cpu']['avg'] < 50.0, f"CPU usage for {stage} exceeded 50%: {stats['cpu']['avg']:.2f}%"
            else:
                # Other stages might be more CPU-intensive
                assert stats['cpu']['avg'] < 80.0, f"CPU usage for {stage} exceeded 80%: {stats['cpu']['avg']:.2f}%"
    
    def test_resource_efficiency_with_different_document_types(self, ocr_service_app, typed_document, handwritten_document, mixed_document):
        """Test resource efficiency with different document types."""
        # Initialize resource monitor
        monitor = ResourceMonitor()
        
        document_types = {
            "typed": typed_document,
            "handwritten": handwritten_document,
            "mixed": mixed_document
        }
        
        type_stats = {}
        
        # Process each document type and measure resource usage
        for doc_type, document in document_types.items():
            # Start monitoring
            monitor.start_monitoring()
            
            # Process the document
            result = ocr_service_app.process_document(document)
            
            # Sample resources during processing
            for _ in range(10):  # Sample resources 10 times during processing
                monitor.sample_resources()
                time.sleep(0.1)  # Sleep to allow processing to continue
            
            # Stop monitoring and get results
            stats = monitor.stop_monitoring()
            type_stats[doc_type] = stats
            
            # Verify processing completed successfully
            assert result is not None, f"Processing failed for {doc_type} document"
        
        # Verify resource efficiency across document types
        # Handwritten documents typically require more resources than typed documents
        if tf.config.list_physical_devices('GPU') and type_stats['typed']['gpu_memory'] is not None and type_stats['handwritten']['gpu_memory'] is not None:
            # Compare GPU memory usage
            typed_gpu_usage = type_stats['typed']['gpu_memory'][0]['avg']
            handwritten_gpu_usage = type_stats['handwritten']['gpu_memory'][0]['avg']
            
            # Handwritten documents should use more GPU resources, but not excessively more
            assert handwritten_gpu_usage > typed_gpu_usage, "Handwritten document processing should use more GPU resources than typed documents"
            assert handwritten_gpu_usage < typed_gpu_usage * 2, "Handwritten document processing is using excessive GPU resources compared to typed documents"
        
        # Compare processing duration
        assert type_stats['typed']['duration'] < type_stats['mixed']['duration'], "Typed documents should process faster than mixed documents"
        assert type_stats['typed']['duration'] < 300, "Typed document processing should complete in under 5 minutes (300 seconds)"
        assert type_stats['handwritten']['duration'] < 300, "Handwritten document processing should complete in under 5 minutes (300 seconds)"
        assert type_stats['mixed']['duration'] < 300, "Mixed document processing should complete in under 5 minutes (300 seconds)"
    
    def test_resource_usage_within_limits(self, ocr_service_app, typed_document):
        """Test that resource usage is within acceptable limits for production deployment."""
        # Initialize resource monitor
        monitor = ResourceMonitor()
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Process the document
        result = ocr_service_app.process_document(typed_document)
        
        # Sample resources during processing
        for _ in range(20):  # Sample resources 20 times during processing
            monitor.sample_resources()
            time.sleep(0.1)  # Sleep to allow processing to continue
        
        # Stop monitoring and get results
        stats = monitor.stop_monitoring()
        
        # Verify processing completed successfully
        assert result is not None, "Document processing failed"
        
        # Verify CPU usage is within acceptable limits
        assert stats['cpu']['max'] < 90.0, f"CPU usage exceeded 90%: {stats['cpu']['max']:.2f}%"
        
        # Verify memory usage is within acceptable limits
        max_memory_usage_gb = stats['memory']['rss']['max'] / (1024 * 1024 * 1024)
        assert max_memory_usage_gb < 4.0, f"Memory usage exceeded 4GB: {max_memory_usage_gb:.2f}GB"
        
        # Verify GPU memory usage is within acceptable limits if GPU is available
        if tf.config.list_physical_devices('GPU') and stats['gpu_memory'] is not None:
            for gpu_idx, gpu_stats in enumerate(stats['gpu_memory']):
                assert gpu_stats['max'] < 80.0, f"GPU {gpu_idx} memory usage exceeded 80%: {gpu_stats['max']:.2f}%"
        
        # Verify processing time is within acceptable limits (under 5 minutes)
        assert stats['duration'] < 300, f"Processing time exceeded 5 minutes: {stats['duration']:.2f} seconds"
    
    def test_gpu_memory_cleanup(self, ocr_service_app, typed_document):
        """Test that GPU memory is properly cleaned up after processing."""
        # Skip test if no GPU is available
        if not tf.config.list_physical_devices('GPU'):
            pytest.skip("No GPU available for testing")
        
        # Initialize resource monitor
        monitor = ResourceMonitor()
        
        # Get baseline GPU memory usage
        monitor.sample_resources()
        baseline_gpu_memory = monitor.gpu_memory_samples[0] if monitor.gpu_memory_samples else None
        
        if baseline_gpu_memory is None:
            pytest.skip("Could not get baseline GPU memory usage")
        
        # Process the document
        result = ocr_service_app.process_document(typed_document)
        assert result is not None, "Document processing failed"
        
        # Force garbage collection to clean up resources
        import gc
        gc.collect()
        tf.keras.backend.clear_session()
        
        # Wait for resources to be released
        time.sleep(2)
        
        # Check GPU memory usage after cleanup
        monitor.sample_resources()
        final_gpu_memory = monitor.gpu_memory_samples[-1] if monitor.gpu_memory_samples else None
        
        if final_gpu_memory is None:
            pytest.skip("Could not get final GPU memory usage")
        
        # Verify GPU memory was properly cleaned up
        # Allow for a small increase (10%) over baseline due to TensorFlow's memory caching
        for gpu_idx in range(len(baseline_gpu_memory)):
            baseline_percent = baseline_gpu_memory[gpu_idx]['percent']
            final_percent = final_gpu_memory[gpu_idx]['percent']
            
            assert final_percent <= baseline_percent * 1.1, f"GPU {gpu_idx} memory not properly cleaned up: {baseline_percent:.2f}% -> {final_percent:.2f}%"
    
    def test_tensorflow_memory_growth(self):
        """Test that TensorFlow memory growth is properly configured."""
        # Skip test if no GPU is available
        if not tf.config.list_physical_devices('GPU'):
            pytest.skip("No GPU available for testing")
        
        # Check if memory growth is enabled for all GPUs
        physical_devices = tf.config.list_physical_devices('GPU')
        for device in physical_devices:
            try:
                memory_growth = tf.config.experimental.get_memory_growth(device)
                assert memory_growth, f"Memory growth not enabled for {device}"
            except Exception as e:
                pytest.fail(f"Failed to check memory growth configuration: {e}")
        
        # Verify that TensorFlow doesn't allocate all GPU memory at once
        # This is a bit tricky to test directly, so we'll check if memory usage increases gradually
        monitor = ResourceMonitor()
        
        # Start with a clean session
        tf.keras.backend.clear_session()
        
        # Sample initial GPU memory
        monitor.sample_resources()
        initial_gpu_memory = monitor.gpu_memory_samples[0] if monitor.gpu_memory_samples else None
        
        if initial_gpu_memory is None:
            pytest.skip("Could not get initial GPU memory usage")
        
        # Create a series of small tensors and check if memory increases gradually
        memory_samples = []
        for i in range(5):
            # Create a tensor that should allocate some GPU memory
            tensor = tf.random.normal([1000, 1000])
            _ = tensor * tensor  # Force execution
            
            # Sample GPU memory after creating the tensor
            monitor.sample_resources()
            memory_samples.append(monitor.gpu_memory_samples[-1] if monitor.gpu_memory_samples else None)
            
            # Sleep briefly to allow TensorFlow to manage memory
            time.sleep(0.5)
        
        # Verify that memory usage increased gradually, not all at once
        if all(sample is not None for sample in memory_samples):
            for gpu_idx in range(len(initial_gpu_memory)):
                # Extract memory percentages for this GPU
                percentages = [initial_gpu_memory[gpu_idx]['percent']] + [sample[gpu_idx]['percent'] for sample in memory_samples]
                
                # Check if there's a gradual increase (not all memory allocated at once)
                # We expect at least some of the differences between consecutive samples to be small
                differences = [percentages[i+1] - percentages[i] for i in range(len(percentages)-1)]
                small_increases = [diff for diff in differences if 0 < diff < 10.0]  # Small increases between 0% and 10%
                
                assert len(small_increases) > 0, f"No gradual memory increases detected for GPU {gpu_idx}, suggesting memory growth might not be working properly"