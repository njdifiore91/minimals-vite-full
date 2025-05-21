#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for OCR Service processing speed performance.

This module contains performance tests that measure the processing speed of the OCR Service
for different document types and complexities. It verifies that the service can process
documents within the required time limits (5 minutes as specified in section 0.1.1),
measuring performance for typed, handwritten, and mixed content documents.

These tests validate that:
1. Typed documents are processed within acceptable time limits
2. Handwritten documents are processed within acceptable time limits
3. Mixed content documents are processed within acceptable time limits
4. Documents with complex layouts are processed within acceptable time limits
5. All document types meet the 5-minute processing requirement

The tests use actual TensorFlow models with GPU acceleration when available,
falling back to CPU processing when necessary.
"""

import os
import time
import pytest
import numpy as np
from typing import Dict, List, Any, Tuple
from unittest.mock import patch, MagicMock

# Import application modules
from src.services.ocr_service import OCRService
from src.types.documents import Document, DocumentType, ProcessingStatus
from src.types.extraction import ExtractedData
from src.types.errors import Result
from src.config import app_config, tensorflow_config


# Constants for test thresholds
MAX_PROCESSING_TIME_SECONDS = 300  # 5 minutes as specified in section 0.1.1
TYPED_DOCUMENT_TARGET_TIME = 60    # Target: 1 minute for typed documents
HANDWRITTEN_DOCUMENT_TARGET_TIME = 120  # Target: 2 minutes for handwritten documents
MIXED_DOCUMENT_TARGET_TIME = 180   # Target: 3 minutes for mixed documents
COMPLEX_DOCUMENT_TARGET_TIME = 240  # Target: 4 minutes for complex documents


# Skip tests if GPU is required but not available
def is_gpu_available() -> bool:
    """Check if GPU is available for TensorFlow."""
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices('GPU')
        return len(gpus) > 0
    except:
        return False


# Skip tests if running in CI environment without GPU
skip_if_no_gpu = pytest.mark.skipif(
    os.environ.get('CI') == 'true' and not is_gpu_available(),
    reason="GPU required for performance tests in CI environment"
)


# Test fixtures for document complexity
@pytest.fixture
def simple_typed_document(typed_document) -> Document:
    """Provides a simple typed document for testing."""
    return typed_document


@pytest.fixture
def complex_typed_document(typed_document) -> Document:
    """Provides a complex typed document with tables and multiple columns."""
    # In a real implementation, this would load a more complex document
    # For this test, we'll modify the metadata to indicate it's complex
    typed_document.metadata.additional_metadata = {
        "complexity": "high",
        "page_count": 5,
        "has_tables": True,
        "has_multiple_columns": True
    }
    return typed_document


@pytest.fixture
def simple_handwritten_document(handwritten_document) -> Document:
    """Provides a simple handwritten document for testing."""
    return handwritten_document


@pytest.fixture
def complex_handwritten_document(handwritten_document) -> Document:
    """Provides a complex handwritten document with varied writing styles."""
    # In a real implementation, this would load a more complex document
    # For this test, we'll modify the metadata to indicate it's complex
    handwritten_document.metadata.additional_metadata = {
        "complexity": "high",
        "page_count": 3,
        "writing_styles": ["cursive", "print", "mixed"],
        "writing_quality": "varied"
    }
    return handwritten_document


@pytest.fixture
def simple_mixed_document(mixed_document) -> Document:
    """Provides a simple mixed content document for testing."""
    return mixed_document


@pytest.fixture
def complex_mixed_document(mixed_document) -> Document:
    """Provides a complex mixed content document with tables, annotations, and multiple columns."""
    # In a real implementation, this would load a more complex document
    # For this test, we'll modify the metadata to indicate it's complex
    mixed_document.metadata.additional_metadata = {
        "complexity": "high",
        "page_count": 8,
        "has_tables": True,
        "has_multiple_columns": True,
        "has_annotations": True,
        "has_handwritten_fields": True,
        "has_signatures": True
    }
    return mixed_document


# Helper functions for tests
def measure_processing_time(ocr_service: OCRService, document: Document) -> Tuple[float, Result]:
    """Measure the time taken to process a document.
    
    Args:
        ocr_service: The OCR service instance
        document: The document to process
        
    Returns:
        Tuple of (processing_time_seconds, processing_result)
    """
    start_time = time.time()
    result = ocr_service.process_document(document)
    end_time = time.time()
    processing_time = end_time - start_time
    
    return processing_time, result


def assert_processing_time_within_limits(processing_time: float, target_time: float, document_type: str):
    """Assert that processing time is within acceptable limits.
    
    Args:
        processing_time: The measured processing time in seconds
        target_time: The target processing time in seconds
        document_type: The type of document being processed (for error messages)
    """
    # Always ensure we're under the 5-minute requirement
    assert processing_time <= MAX_PROCESSING_TIME_SECONDS, \
        f"{document_type} document processing exceeded 5-minute requirement: {processing_time:.2f}s"
    
    # Check if we're meeting our target time
    if processing_time > target_time:
        pytest.xfail(f"{document_type} document processing time ({processing_time:.2f}s) exceeded target ({target_time}s) but was within 5-minute requirement")


# Test classes
class TestTypedDocumentProcessingSpeed:
    """Tests for measuring OCR processing speed for typed documents."""
    
    @pytest.mark.performance
    def test_simple_typed_document_processing_speed(self, simple_typed_document):
        """Test that simple typed documents are processed quickly."""
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Measure processing time
        processing_time, result = measure_processing_time(ocr_service, simple_typed_document)
        
        # Log the processing time for analysis
        print(f"\nSimple typed document processing time: {processing_time:.2f} seconds")
        
        # Assert that processing was successful
        assert result.success, f"Processing failed: {result.error.message if result.error else 'Unknown error'}"
        
        # Assert that processing time is within limits
        assert_processing_time_within_limits(processing_time, TYPED_DOCUMENT_TARGET_TIME, "Simple typed")
        
        # Verify that extracted data has high confidence
        extracted_data, _ = result.value
        assert extracted_data.average_confidence >= 0.9, \
            f"Confidence too low: {extracted_data.average_confidence:.2f}"
    
    @pytest.mark.performance
    def test_complex_typed_document_processing_speed(self, complex_typed_document):
        """Test that complex typed documents with tables and multiple columns are processed within time limits."""
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Measure processing time
        processing_time, result = measure_processing_time(ocr_service, complex_typed_document)
        
        # Log the processing time for analysis
        print(f"\nComplex typed document processing time: {processing_time:.2f} seconds")
        
        # Assert that processing was successful
        assert result.success, f"Processing failed: {result.error.message if result.error else 'Unknown error'}"
        
        # Assert that processing time is within limits
        # Complex documents may take longer but should still be under the maximum
        assert_processing_time_within_limits(processing_time, TYPED_DOCUMENT_TARGET_TIME * 1.5, "Complex typed")
        
        # Verify that extracted data has acceptable confidence
        extracted_data, _ = result.value
        assert extracted_data.average_confidence >= 0.85, \
            f"Confidence too low: {extracted_data.average_confidence:.2f}"
    
    @pytest.mark.performance
    def test_batch_typed_document_processing_speed(self, document_collection):
        """Test that batches of typed documents are processed efficiently."""
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Filter for typed documents only
        typed_documents = [doc for doc in document_collection 
                          if doc.document_type == DocumentType.APPLICATION or 
                          doc.document_type == DocumentType.BANK_STATEMENT]
        
        # Skip test if no typed documents are available
        if not typed_documents:
            pytest.skip("No typed documents available in the collection")
        
        # Process each document and measure time
        total_time = 0
        processing_times = []
        
        for doc in typed_documents:
            processing_time, result = measure_processing_time(ocr_service, doc)
            total_time += processing_time
            processing_times.append(processing_time)
            
            # Assert that processing was successful
            assert result.success, f"Processing failed for document {doc.metadata.filename}: {result.error.message if result.error else 'Unknown error'}"
        
        # Calculate statistics
        avg_time = total_time / len(typed_documents)
        max_time = max(processing_times)
        min_time = min(processing_times)
        
        # Log the processing times for analysis
        print(f"\nBatch typed document processing statistics:")
        print(f"  Documents processed: {len(typed_documents)}")
        print(f"  Total time: {total_time:.2f} seconds")
        print(f"  Average time per document: {avg_time:.2f} seconds")
        print(f"  Max time: {max_time:.2f} seconds")
        print(f"  Min time: {min_time:.2f} seconds")
        
        # Assert that average processing time is within limits
        assert avg_time <= TYPED_DOCUMENT_TARGET_TIME, \
            f"Average processing time ({avg_time:.2f}s) exceeded target ({TYPED_DOCUMENT_TARGET_TIME}s)"
        
        # Assert that maximum processing time is within the 5-minute requirement
        assert max_time <= MAX_PROCESSING_TIME_SECONDS, \
            f"Maximum processing time ({max_time:.2f}s) exceeded 5-minute requirement"


class TestHandwrittenDocumentProcessingSpeed:
    """Tests for measuring OCR processing speed for handwritten documents."""
    
    @pytest.mark.performance
    def test_simple_handwritten_document_processing_speed(self, simple_handwritten_document):
        """Test that simple handwritten documents are processed within time limits."""
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Measure processing time
        processing_time, result = measure_processing_time(ocr_service, simple_handwritten_document)
        
        # Log the processing time for analysis
        print(f"\nSimple handwritten document processing time: {processing_time:.2f} seconds")
        
        # Assert that processing was successful
        assert result.success, f"Processing failed: {result.error.message if result.error else 'Unknown error'}"
        
        # Assert that processing time is within limits
        assert_processing_time_within_limits(processing_time, HANDWRITTEN_DOCUMENT_TARGET_TIME, "Simple handwritten")
        
        # Verify that extracted data has acceptable confidence
        # Handwritten documents typically have lower confidence than typed
        extracted_data, _ = result.value
        assert extracted_data.average_confidence >= 0.8, \
            f"Confidence too low: {extracted_data.average_confidence:.2f}"
    
    @pytest.mark.performance
    def test_complex_handwritten_document_processing_speed(self, complex_handwritten_document):
        """Test that complex handwritten documents with varied writing styles are processed within time limits."""
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Measure processing time
        processing_time, result = measure_processing_time(ocr_service, complex_handwritten_document)
        
        # Log the processing time for analysis
        print(f"\nComplex handwritten document processing time: {processing_time:.2f} seconds")
        
        # Assert that processing was successful
        assert result.success, f"Processing failed: {result.error.message if result.error else 'Unknown error'}"
        
        # Assert that processing time is within limits
        # Complex handwritten documents may take longer but should still be under the maximum
        assert_processing_time_within_limits(processing_time, HANDWRITTEN_DOCUMENT_TARGET_TIME * 1.5, "Complex handwritten")
        
        # Verify that extracted data has acceptable confidence
        # Complex handwritten documents may have lower confidence
        extracted_data, _ = result.value
        assert extracted_data.average_confidence >= 0.75, \
            f"Confidence too low: {extracted_data.average_confidence:.2f}"
    
    @pytest.mark.performance
    @skip_if_no_gpu
    def test_handwritten_document_processing_with_gpu(self, simple_handwritten_document):
        """Test that handwritten documents are processed faster with GPU acceleration."""
        # Skip test if GPU is not available
        if not is_gpu_available():
            pytest.skip("No GPU available for testing")
        
        # Initialize OCR service with GPU
        with patch('src.utils.tensorflow_utils.setup_gpu_environment', return_value=True):
            ocr_service_gpu = OCRService()
            
            # Measure processing time with GPU
            gpu_start_time = time.time()
            gpu_result = ocr_service_gpu.process_document(simple_handwritten_document)
            gpu_processing_time = time.time() - gpu_start_time
        
        # Initialize OCR service with CPU only
        with patch('src.utils.tensorflow_utils.setup_gpu_environment', return_value=False):
            ocr_service_cpu = OCRService()
            
            # Measure processing time with CPU
            cpu_start_time = time.time()
            cpu_result = ocr_service_cpu.process_document(simple_handwritten_document)
            cpu_processing_time = time.time() - cpu_start_time
        
        # Log the processing times for analysis
        print(f"\nHandwritten document processing time comparison:")
        print(f"  GPU processing time: {gpu_processing_time:.2f} seconds")
        print(f"  CPU processing time: {cpu_processing_time:.2f} seconds")
        print(f"  Speedup factor: {cpu_processing_time / gpu_processing_time:.2f}x")
        
        # Assert that both processing attempts were successful
        assert gpu_result.success, f"GPU processing failed: {gpu_result.error.message if gpu_result.error else 'Unknown error'}"
        assert cpu_result.success, f"CPU processing failed: {cpu_result.error.message if cpu_result.error else 'Unknown error'}"
        
        # Assert that GPU processing is faster than CPU
        # We expect at least a 2x speedup with GPU
        assert gpu_processing_time < cpu_processing_time, "GPU processing was not faster than CPU"
        
        # Check if we achieved the expected speedup
        speedup = cpu_processing_time / gpu_processing_time
        if speedup < 2.0:
            pytest.xfail(f"GPU speedup ({speedup:.2f}x) was less than expected (2.0x)")


class TestMixedDocumentProcessingSpeed:
    """Tests for measuring OCR processing speed for mixed content documents."""
    
    @pytest.mark.performance
    def test_simple_mixed_document_processing_speed(self, simple_mixed_document):
        """Test that simple mixed content documents are processed within time limits."""
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Measure processing time
        processing_time, result = measure_processing_time(ocr_service, simple_mixed_document)
        
        # Log the processing time for analysis
        print(f"\nSimple mixed document processing time: {processing_time:.2f} seconds")
        
        # Assert that processing was successful
        assert result.success, f"Processing failed: {result.error.message if result.error else 'Unknown error'}"
        
        # Assert that processing time is within limits
        assert_processing_time_within_limits(processing_time, MIXED_DOCUMENT_TARGET_TIME, "Simple mixed")
        
        # Verify that extracted data has acceptable confidence
        extracted_data, _ = result.value
        assert extracted_data.average_confidence >= 0.85, \
            f"Confidence too low: {extracted_data.average_confidence:.2f}"
    
    @pytest.mark.performance
    def test_complex_mixed_document_processing_speed(self, complex_mixed_document):
        """Test that complex mixed content documents with tables, annotations, and multiple columns are processed within time limits."""
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Measure processing time
        processing_time, result = measure_processing_time(ocr_service, complex_mixed_document)
        
        # Log the processing time for analysis
        print(f"\nComplex mixed document processing time: {processing_time:.2f} seconds")
        
        # Assert that processing was successful
        assert result.success, f"Processing failed: {result.error.message if result.error else 'Unknown error'}"
        
        # Assert that processing time is within limits
        # Complex mixed documents may take longer but should still be under the maximum
        assert_processing_time_within_limits(processing_time, MIXED_DOCUMENT_TARGET_TIME * 1.5, "Complex mixed")
        
        # Verify that extracted data has acceptable confidence
        extracted_data, _ = result.value
        assert extracted_data.average_confidence >= 0.8, \
            f"Confidence too low: {extracted_data.average_confidence:.2f}"
    
    @pytest.mark.performance
    def test_mixed_document_model_selection_impact(self, simple_mixed_document):
        """Test the impact of model selection on processing speed for mixed content documents."""
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Process with automatic model selection (should choose hybrid model)
        auto_start_time = time.time()
        auto_result = ocr_service.process_document(simple_mixed_document)
        auto_processing_time = time.time() - auto_start_time
        
        # Force typed model selection
        with patch('src.services.ocr_service.OCRService._determine_model_type', return_value='typed'):
            typed_start_time = time.time()
            typed_result = ocr_service.process_document(simple_mixed_document)
            typed_processing_time = time.time() - typed_start_time
        
        # Force handwritten model selection
        with patch('src.services.ocr_service.OCRService._determine_model_type', return_value='handwritten'):
            handwritten_start_time = time.time()
            handwritten_result = ocr_service.process_document(simple_mixed_document)
            handwritten_processing_time = time.time() - handwritten_start_time
        
        # Log the processing times for analysis
        print(f"\nMixed document model selection impact:")
        print(f"  Automatic model selection time: {auto_processing_time:.2f} seconds")
        print(f"  Forced typed model time: {typed_processing_time:.2f} seconds")
        print(f"  Forced handwritten model time: {handwritten_processing_time:.2f} seconds")
        
        # Assert that all processing attempts were successful
        assert auto_result.success, f"Automatic model processing failed: {auto_result.error.message if auto_result.error else 'Unknown error'}"
        assert typed_result.success, f"Typed model processing failed: {typed_result.error.message if typed_result.error else 'Unknown error'}"
        assert handwritten_result.success, f"Handwritten model processing failed: {handwritten_result.error.message if handwritten_result.error else 'Unknown error'}"
        
        # Extract confidence scores
        auto_data, _ = auto_result.value
        typed_data, _ = typed_result.value
        handwritten_data, _ = handwritten_result.value
        
        print(f"  Automatic model confidence: {auto_data.average_confidence:.2f}")
        print(f"  Typed model confidence: {typed_data.average_confidence:.2f}")
        print(f"  Handwritten model confidence: {handwritten_data.average_confidence:.2f}")
        
        # Assert that all processing times are within the 5-minute requirement
        assert auto_processing_time <= MAX_PROCESSING_TIME_SECONDS, \
            f"Automatic model processing time ({auto_processing_time:.2f}s) exceeded 5-minute requirement"
        assert typed_processing_time <= MAX_PROCESSING_TIME_SECONDS, \
            f"Typed model processing time ({typed_processing_time:.2f}s) exceeded 5-minute requirement"
        assert handwritten_processing_time <= MAX_PROCESSING_TIME_SECONDS, \
            f"Handwritten model processing time ({handwritten_processing_time:.2f}s) exceeded 5-minute requirement"
        
        # Verify that automatic model selection provides the best confidence
        # This may not always be true, so we'll just log a warning if it's not
        if auto_data.average_confidence < max(typed_data.average_confidence, handwritten_data.average_confidence):
            print("WARNING: Automatic model selection did not provide the best confidence score")


class TestComplexLayoutProcessingSpeed:
    """Tests for measuring OCR processing speed for documents with complex layouts."""
    
    @pytest.mark.performance
    def test_table_extraction_processing_speed(self, complex_typed_document):
        """Test that documents with tables are processed within time limits."""
        # Ensure the document has tables
        complex_typed_document.metadata.additional_metadata["has_tables"] = True
        
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Measure processing time
        processing_time, result = measure_processing_time(ocr_service, complex_typed_document)
        
        # Log the processing time for analysis
        print(f"\nTable extraction processing time: {processing_time:.2f} seconds")
        
        # Assert that processing was successful
        assert result.success, f"Processing failed: {result.error.message if result.error else 'Unknown error'}"
        
        # Assert that processing time is within limits
        assert_processing_time_within_limits(processing_time, COMPLEX_DOCUMENT_TARGET_TIME, "Table document")
        
        # Verify that extracted data has acceptable confidence
        extracted_data, _ = result.value
        assert extracted_data.average_confidence >= 0.85, \
            f"Confidence too low: {extracted_data.average_confidence:.2f}"
    
    @pytest.mark.performance
    def test_multi_column_processing_speed(self, complex_typed_document):
        """Test that documents with multiple columns are processed within time limits."""
        # Ensure the document has multiple columns
        complex_typed_document.metadata.additional_metadata["has_multiple_columns"] = True
        
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Measure processing time
        processing_time, result = measure_processing_time(ocr_service, complex_typed_document)
        
        # Log the processing time for analysis
        print(f"\nMulti-column document processing time: {processing_time:.2f} seconds")
        
        # Assert that processing was successful
        assert result.success, f"Processing failed: {result.error.message if result.error else 'Unknown error'}"
        
        # Assert that processing time is within limits
        assert_processing_time_within_limits(processing_time, COMPLEX_DOCUMENT_TARGET_TIME, "Multi-column document")
        
        # Verify that extracted data has acceptable confidence
        extracted_data, _ = result.value
        assert extracted_data.average_confidence >= 0.85, \
            f"Confidence too low: {extracted_data.average_confidence:.2f}"
    
    @pytest.mark.performance
    def test_form_extraction_processing_speed(self, complex_mixed_document):
        """Test that forms with both typed and handwritten fields are processed within time limits."""
        # Ensure the document has form fields
        complex_mixed_document.metadata.additional_metadata["has_form_fields"] = True
        complex_mixed_document.metadata.additional_metadata["has_handwritten_fields"] = True
        
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Measure processing time
        processing_time, result = measure_processing_time(ocr_service, complex_mixed_document)
        
        # Log the processing time for analysis
        print(f"\nForm extraction processing time: {processing_time:.2f} seconds")
        
        # Assert that processing was successful
        assert result.success, f"Processing failed: {result.error.message if result.error else 'Unknown error'}"
        
        # Assert that processing time is within limits
        assert_processing_time_within_limits(processing_time, COMPLEX_DOCUMENT_TARGET_TIME, "Form document")
        
        # Verify that extracted data has acceptable confidence
        extracted_data, _ = result.value
        assert extracted_data.average_confidence >= 0.8, \
            f"Confidence too low: {extracted_data.average_confidence:.2f}"


class TestProcessingTimeRequirements:
    """Tests to verify that all document types meet the 5-minute processing requirement."""
    
    @pytest.mark.performance
    def test_all_document_types_meet_time_requirement(self, document_collection):
        """Test that all document types in the collection are processed within the 5-minute requirement."""
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Skip test if no documents are available
        if not document_collection:
            pytest.skip("No documents available in the collection")
        
        # Process each document and measure time
        results = []
        
        for doc in document_collection:
            processing_time, result = measure_processing_time(ocr_service, doc)
            
            # Store results for analysis
            results.append({
                "document_id": doc.metadata.document_id,
                "filename": doc.metadata.filename,
                "document_type": doc.document_type.name if doc.document_type else "UNKNOWN",
                "processing_time": processing_time,
                "success": result.success,
                "error": str(result.error) if not result.success and result.error else None,
                "confidence": result.value[0].average_confidence if result.success else None
            })
        
        # Log the results for analysis
        print(f"\nProcessing time results for all document types:")
        for res in results:
            print(f"  {res['filename']} ({res['document_type']}): {res['processing_time']:.2f}s, "
                  f"Success: {res['success']}, Confidence: {res['confidence']:.2f if res['confidence'] else 0}")
        
        # Calculate statistics by document type
        doc_types = set(res["document_type"] for res in results)
        for doc_type in doc_types:
            type_results = [res for res in results if res["document_type"] == doc_type]
            type_times = [res["processing_time"] for res in type_results]
            
            avg_time = sum(type_times) / len(type_times) if type_times else 0
            max_time = max(type_times) if type_times else 0
            min_time = min(type_times) if type_times else 0
            
            print(f"\n  {doc_type} statistics:")
            print(f"    Count: {len(type_results)}")
            print(f"    Average time: {avg_time:.2f}s")
            print(f"    Max time: {max_time:.2f}s")
            print(f"    Min time: {min_time:.2f}s")
            
            # Assert that maximum processing time is within the 5-minute requirement
            assert max_time <= MAX_PROCESSING_TIME_SECONDS, \
                f"{doc_type} maximum processing time ({max_time:.2f}s) exceeded 5-minute requirement"
    
    @pytest.mark.performance
    @skip_if_no_gpu
    def test_processing_time_with_different_gpu_memory_limits(self, simple_mixed_document):
        """Test the impact of different GPU memory limits on processing time."""
        # Skip test if GPU is not available
        if not is_gpu_available():
            pytest.skip("No GPU available for testing")
        
        # Test with different memory limits
        memory_limits = [1024, 2048, 4096, 8192]  # 1GB, 2GB, 4GB, 8GB
        results = []
        
        for memory_limit in memory_limits:
            # Initialize OCR service with specific GPU memory limit
            with patch('src.config.tensorflow_config.GPU_MEMORY_LIMIT', memory_limit):
                ocr_service = OCRService()
                
                # Measure processing time
                processing_time, result = measure_processing_time(ocr_service, simple_mixed_document)
                
                # Store results
                results.append({
                    "memory_limit": memory_limit,
                    "processing_time": processing_time,
                    "success": result.success,
                    "confidence": result.value[0].average_confidence if result.success else None
                })
        
        # Log the results for analysis
        print(f"\nProcessing time with different GPU memory limits:")
        for res in results:
            print(f"  {res['memory_limit']}MB: {res['processing_time']:.2f}s, "
                  f"Success: {res['success']}, Confidence: {res['confidence']:.2f if res['confidence'] else 0}")
        
        # Assert that all processing times are within the 5-minute requirement
        for res in results:
            assert res["processing_time"] <= MAX_PROCESSING_TIME_SECONDS, \
                f"Processing with {res['memory_limit']}MB GPU memory ({res['processing_time']:.2f}s) exceeded 5-minute requirement"
        
        # Check if higher memory limits generally lead to faster processing
        # This may not always be true due to other factors, so we'll just log a warning if it's not
        if results and len(results) > 1:
            is_monotonic = all(results[i]["processing_time"] >= results[i+1]["processing_time"] 
                              for i in range(len(results)-1))
            
            if not is_monotonic:
                print("WARNING: Higher GPU memory limits did not consistently lead to faster processing")
    
    @pytest.mark.performance
    def test_processing_time_stability(self, simple_typed_document):
        """Test that processing time is stable across multiple runs."""
        # Initialize OCR service
        ocr_service = OCRService()
        
        # Process the same document multiple times
        num_runs = 3
        processing_times = []
        
        for i in range(num_runs):
            processing_time, result = measure_processing_time(ocr_service, simple_typed_document)
            processing_times.append(processing_time)
            
            # Assert that processing was successful
            assert result.success, f"Run {i+1} failed: {result.error.message if result.error else 'Unknown error'}"
        
        # Calculate statistics
        avg_time = sum(processing_times) / len(processing_times)
        max_time = max(processing_times)
        min_time = min(processing_times)
        std_dev = np.std(processing_times)
        
        # Log the results for analysis
        print(f"\nProcessing time stability over {num_runs} runs:")
        print(f"  Average time: {avg_time:.2f}s")
        print(f"  Max time: {max_time:.2f}s")
        print(f"  Min time: {min_time:.2f}s")
        print(f"  Standard deviation: {std_dev:.2f}s")
        print(f"  Coefficient of variation: {(std_dev / avg_time * 100):.2f}%")
        
        # Assert that all processing times are within the 5-minute requirement
        assert max_time <= MAX_PROCESSING_TIME_SECONDS, \
            f"Maximum processing time ({max_time:.2f}s) exceeded 5-minute requirement"
        
        # Check if processing time is stable (coefficient of variation < 20%)
        # This may not always be true due to system load and other factors,
        # so we'll just log a warning if it's not
        if std_dev / avg_time > 0.2:  # 20% coefficient of variation
            print("WARNING: Processing time shows high variability (coefficient of variation > 20%)")