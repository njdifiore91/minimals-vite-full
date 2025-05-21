#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Performance tests for measuring latency of OCR operations.

This module contains tests that measure the time taken for various OCR operations,
including document preprocessing, model inference, field extraction, and end-to-end
processing. These tests help identify performance bottlenecks and ensure the OCR
service meets the requirement of processing applications in under 5 minutes.
"""

import time
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from services import OCRService, FieldExtractionService
from models import ModelFactory, TypedTextModel, HandwrittenTextModel, HybridRecognitionModel
from utils import image_utils, tensorflow_utils


# Constants for latency thresholds (in seconds)
MAX_PREPROCESSING_LATENCY = 5.0  # Maximum acceptable time for document preprocessing
MAX_INFERENCE_LATENCY_TYPED = 10.0  # Maximum acceptable time for typed text OCR inference
MAX_INFERENCE_LATENCY_HANDWRITTEN = 20.0  # Maximum acceptable time for handwritten OCR inference
MAX_INFERENCE_LATENCY_HYBRID = 25.0  # Maximum acceptable time for hybrid OCR inference
MAX_FIELD_EXTRACTION_LATENCY = 5.0  # Maximum acceptable time for field extraction
MAX_END_TO_END_LATENCY = 60.0  # Maximum acceptable time for end-to-end processing
MAX_TOTAL_PROCESSING_TIME = 300.0  # 5 minutes maximum for complete application processing


@pytest.mark.performance
class TestOCRLatency:
    """Test suite for measuring OCR operation latencies."""

    def test_document_preprocessing_latency(self, performance_test_documents, latency_logger):
        """Test the latency of document preprocessing operations.
        
        This test measures the time taken to preprocess documents of different types and sizes,
        including operations like resizing, normalization, and enhancement.
        
        Args:
            performance_test_documents: Fixture providing test documents
            latency_logger: Fixture for logging latency measurements
        """
        latency_logger.start_timer("preprocessing")
        
        preprocessing_times = []
        
        for doc_type, documents in performance_test_documents.items():
            for doc in documents:
                start_time = time.time()
                
                # Perform preprocessing operations
                processed_image = image_utils.preprocess_document(
                    doc.image,
                    normalize=True,
                    enhance=True,
                    deskew=True
                )
                
                elapsed_time = time.time() - start_time
                preprocessing_times.append({
                    "document_type": doc_type,
                    "document_size": doc.size,
                    "processing_time": elapsed_time
                })
                
                latency_logger.log_operation(
                    operation="document_preprocessing",
                    document_type=doc_type,
                    document_size=doc.size,
                    latency=elapsed_time
                )
                
                # Assert that preprocessing time is within acceptable limits
                assert elapsed_time < MAX_PREPROCESSING_LATENCY, \
                    f"Preprocessing latency ({elapsed_time:.2f}s) exceeds maximum allowed ({MAX_PREPROCESSING_LATENCY}s)"
        
        # Calculate and log statistics
        times = [entry["processing_time"] for entry in preprocessing_times]
        avg_time = np.mean(times)
        p95_time = np.percentile(times, 95)
        max_time = np.max(times)
        
        latency_logger.log_summary(
            operation="document_preprocessing",
            avg_latency=avg_time,
            p95_latency=p95_time,
            max_latency=max_time
        )
        
        latency_logger.stop_timer("preprocessing")

    def test_ocr_model_inference_latency(self, performance_test_documents, model_factory, latency_logger):
        """Test the latency of OCR model inference for different document types.
        
        This test measures the time taken for OCR models to perform text recognition
        on different types of documents (typed, handwritten, and mixed).
        
        Args:
            performance_test_documents: Fixture providing test documents
            model_factory: Fixture providing OCR model instances
            latency_logger: Fixture for logging latency measurements
        """
        latency_logger.start_timer("model_inference")
        
        inference_times = []
        
        # Test typed text model inference
        typed_model = model_factory.get_model("typed")
        for doc in performance_test_documents["typed"]:
            processed_image = image_utils.preprocess_document(doc.image)
            
            start_time = time.time()
            typed_results = typed_model.extract_text(processed_image)
            elapsed_time = time.time() - start_time
            
            inference_times.append({
                "model_type": "typed",
                "document_size": doc.size,
                "processing_time": elapsed_time
            })
            
            latency_logger.log_operation(
                operation="model_inference",
                model_type="typed",
                document_size=doc.size,
                latency=elapsed_time
            )
            
            assert elapsed_time < MAX_INFERENCE_LATENCY_TYPED, \
                f"Typed text model inference latency ({elapsed_time:.2f}s) exceeds maximum allowed ({MAX_INFERENCE_LATENCY_TYPED}s)"
        
        # Test handwritten text model inference
        handwritten_model = model_factory.get_model("handwritten")
        for doc in performance_test_documents["handwritten"]:
            processed_image = image_utils.preprocess_document(doc.image)
            
            start_time = time.time()
            handwritten_results = handwritten_model.extract_text(processed_image)
            elapsed_time = time.time() - start_time
            
            inference_times.append({
                "model_type": "handwritten",
                "document_size": doc.size,
                "processing_time": elapsed_time
            })
            
            latency_logger.log_operation(
                operation="model_inference",
                model_type="handwritten",
                document_size=doc.size,
                latency=elapsed_time
            )
            
            assert elapsed_time < MAX_INFERENCE_LATENCY_HANDWRITTEN, \
                f"Handwritten text model inference latency ({elapsed_time:.2f}s) exceeds maximum allowed ({MAX_INFERENCE_LATENCY_HANDWRITTEN}s)"
        
        # Test hybrid text model inference
        hybrid_model = model_factory.get_model("hybrid")
        for doc in performance_test_documents["mixed"]:
            processed_image = image_utils.preprocess_document(doc.image)
            
            start_time = time.time()
            hybrid_results = hybrid_model.extract_text(processed_image)
            elapsed_time = time.time() - start_time
            
            inference_times.append({
                "model_type": "hybrid",
                "document_size": doc.size,
                "processing_time": elapsed_time
            })
            
            latency_logger.log_operation(
                operation="model_inference",
                model_type="hybrid",
                document_size=doc.size,
                latency=elapsed_time
            )
            
            assert elapsed_time < MAX_INFERENCE_LATENCY_HYBRID, \
                f"Hybrid text model inference latency ({elapsed_time:.2f}s) exceeds maximum allowed ({MAX_INFERENCE_LATENCY_HYBRID}s)"
        
        # Calculate and log statistics by model type
        for model_type in ["typed", "handwritten", "hybrid"]:
            model_times = [entry["processing_time"] for entry in inference_times if entry["model_type"] == model_type]
            if model_times:
                avg_time = np.mean(model_times)
                p95_time = np.percentile(model_times, 95)
                max_time = np.max(model_times)
                
                latency_logger.log_summary(
                    operation=f"model_inference_{model_type}",
                    avg_latency=avg_time,
                    p95_latency=p95_time,
                    max_latency=max_time
                )
        
        latency_logger.stop_timer("model_inference")

    def test_field_extraction_latency(self, ocr_results, field_extraction_service, latency_logger):
        """Test the latency of field extraction and post-processing operations.
        
        This test measures the time taken to extract structured fields from OCR results,
        including key-value pair extraction, field normalization, and confidence scoring.
        
        Args:
            ocr_results: Fixture providing sample OCR results
            field_extraction_service: Fixture providing field extraction service
            latency_logger: Fixture for logging latency measurements
        """
        latency_logger.start_timer("field_extraction")
        
        extraction_times = []
        
        for doc_type, results_list in ocr_results.items():
            for result in results_list:
                start_time = time.time()
                
                # Extract structured fields from OCR results
                extracted_fields = field_extraction_service.extract_fields(
                    result.text,
                    document_type=doc_type,
                    apply_validation=True,
                    calculate_confidence=True
                )
                
                elapsed_time = time.time() - start_time
                extraction_times.append({
                    "document_type": doc_type,
                    "field_count": len(extracted_fields),
                    "processing_time": elapsed_time
                })
                
                latency_logger.log_operation(
                    operation="field_extraction",
                    document_type=doc_type,
                    field_count=len(extracted_fields),
                    latency=elapsed_time
                )
                
                assert elapsed_time < MAX_FIELD_EXTRACTION_LATENCY, \
                    f"Field extraction latency ({elapsed_time:.2f}s) exceeds maximum allowed ({MAX_FIELD_EXTRACTION_LATENCY}s)"
        
        # Calculate and log statistics
        times = [entry["processing_time"] for entry in extraction_times]
        avg_time = np.mean(times)
        p95_time = np.percentile(times, 95)
        max_time = np.max(times)
        
        latency_logger.log_summary(
            operation="field_extraction",
            avg_latency=avg_time,
            p95_latency=p95_time,
            max_latency=max_time
        )
        
        latency_logger.stop_timer("field_extraction")

    def test_end_to_end_processing_latency(self, performance_test_documents, ocr_service, latency_logger):
        """Test the end-to-end latency of the OCR processing pipeline.
        
        This test measures the time taken for complete document processing,
        from document loading to field extraction and result formatting.
        
        Args:
            performance_test_documents: Fixture providing test documents
            ocr_service: Fixture providing OCR service instance
            latency_logger: Fixture for logging latency measurements
        """
        latency_logger.start_timer("end_to_end")
        
        processing_times = []
        
        for doc_type, documents in performance_test_documents.items():
            for doc in documents:
                start_time = time.time()
                
                # Process document end-to-end
                result = ocr_service.process_document(
                    document=doc.image,
                    document_type=doc_type,
                    document_id=doc.id,
                    extract_fields=True,
                    calculate_confidence=True
                )
                
                elapsed_time = time.time() - start_time
                processing_times.append({
                    "document_type": doc_type,
                    "document_size": doc.size,
                    "field_count": len(result.fields),
                    "processing_time": elapsed_time
                })
                
                latency_logger.log_operation(
                    operation="end_to_end_processing",
                    document_type=doc_type,
                    document_size=doc.size,
                    field_count=len(result.fields),
                    latency=elapsed_time
                )
                
                assert elapsed_time < MAX_END_TO_END_LATENCY, \
                    f"End-to-end processing latency ({elapsed_time:.2f}s) exceeds maximum allowed ({MAX_END_TO_END_LATENCY}s)"
        
        # Calculate and log statistics by document type
        for doc_type in performance_test_documents.keys():
            type_times = [entry["processing_time"] for entry in processing_times if entry["document_type"] == doc_type]
            if type_times:
                avg_time = np.mean(type_times)
                p95_time = np.percentile(type_times, 95)
                max_time = np.max(type_times)
                
                latency_logger.log_summary(
                    operation=f"end_to_end_processing_{doc_type}",
                    avg_latency=avg_time,
                    p95_latency=p95_time,
                    max_latency=max_time
                )
        
        # Calculate and log overall statistics
        times = [entry["processing_time"] for entry in processing_times]
        avg_time = np.mean(times)
        p95_time = np.percentile(times, 95)
        max_time = np.max(times)
        
        latency_logger.log_summary(
            operation="end_to_end_processing_overall",
            avg_latency=avg_time,
            p95_latency=p95_time,
            max_latency=max_time
        )
        
        latency_logger.stop_timer("end_to_end")
        
        # Verify that the maximum processing time is well under the 5-minute requirement
        assert max_time < MAX_TOTAL_PROCESSING_TIME, \
            f"Maximum processing time ({max_time:.2f}s) is too close to the 5-minute limit ({MAX_TOTAL_PROCESSING_TIME}s)"

    @pytest.mark.parametrize("document_complexity", ["simple", "medium", "complex"])
    def test_processing_latency_by_complexity(self, document_complexity, complexity_test_documents, ocr_service, latency_logger):
        """Test how document complexity affects processing latency.
        
        This test measures processing time for documents of different complexity levels
        to understand how complexity impacts performance.
        
        Args:
            document_complexity: Complexity level being tested
            complexity_test_documents: Fixture providing documents of different complexity
            ocr_service: Fixture providing OCR service instance
            latency_logger: Fixture for logging latency measurements
        """
        latency_logger.start_timer(f"complexity_{document_complexity}")
        
        documents = complexity_test_documents[document_complexity]
        processing_times = []
        
        for doc in documents:
            start_time = time.time()
            
            # Process document end-to-end
            result = ocr_service.process_document(
                document=doc.image,
                document_type=doc.type,
                document_id=doc.id,
                extract_fields=True,
                calculate_confidence=True
            )
            
            elapsed_time = time.time() - start_time
            processing_times.append(elapsed_time)
            
            latency_logger.log_operation(
                operation=f"complexity_processing_{document_complexity}",
                document_type=doc.type,
                complexity=document_complexity,
                latency=elapsed_time
            )
        
        # Calculate and log statistics
        avg_time = np.mean(processing_times)
        p95_time = np.percentile(processing_times, 95)
        max_time = np.max(processing_times)
        
        latency_logger.log_summary(
            operation=f"complexity_processing_{document_complexity}",
            avg_latency=avg_time,
            p95_latency=p95_time,
            max_latency=max_time
        )
        
        latency_logger.stop_timer(f"complexity_{document_complexity}")

    def test_gpu_vs_cpu_inference_latency(self, performance_test_documents, model_factory, latency_logger):
        """Compare OCR model inference latency between GPU and CPU processing.
        
        This test measures the performance difference between GPU-accelerated and
        CPU-only inference to quantify the benefits of GPU acceleration.
        
        Args:
            performance_test_documents: Fixture providing test documents
            model_factory: Fixture providing OCR model instances
            latency_logger: Fixture for logging latency measurements
        """
        latency_logger.start_timer("gpu_vs_cpu")
        
        # Sample a subset of documents for this test
        test_documents = {
            "typed": performance_test_documents["typed"][:2],
            "handwritten": performance_test_documents["handwritten"][:2],
            "mixed": performance_test_documents["mixed"][:2]
        }
        
        gpu_times = []
        cpu_times = []
        
        for doc_type, documents in test_documents.items():
            model = model_factory.get_model(doc_type)
            
            for doc in documents:
                processed_image = image_utils.preprocess_document(doc.image)
                
                # Test with GPU acceleration
                with patch('utils.tensorflow_utils.is_gpu_disabled', return_value=False):
                    start_time = time.time()
                    model.extract_text(processed_image)
                    gpu_time = time.time() - start_time
                    gpu_times.append({
                        "document_type": doc_type,
                        "processing_time": gpu_time
                    })
                    
                    latency_logger.log_operation(
                        operation="gpu_inference",
                        document_type=doc_type,
                        latency=gpu_time
                    )
                
                # Test with CPU only
                with patch('utils.tensorflow_utils.is_gpu_disabled', return_value=True):
                    start_time = time.time()
                    model.extract_text(processed_image)
                    cpu_time = time.time() - start_time
                    cpu_times.append({
                        "document_type": doc_type,
                        "processing_time": cpu_time
                    })
                    
                    latency_logger.log_operation(
                        operation="cpu_inference",
                        document_type=doc_type,
                        latency=cpu_time
                    )
                
                # Calculate speedup factor
                speedup = cpu_time / gpu_time if gpu_time > 0 else float('inf')
                latency_logger.log_operation(
                    operation="gpu_speedup",
                    document_type=doc_type,
                    speedup=speedup
                )
                
                # GPU should be significantly faster than CPU
                assert speedup > 2.0, f"GPU speedup ({speedup:.2f}x) is less than expected (2.0x)"
        
        # Calculate and log statistics
        gpu_avg = np.mean([entry["processing_time"] for entry in gpu_times])
        cpu_avg = np.mean([entry["processing_time"] for entry in cpu_times])
        overall_speedup = cpu_avg / gpu_avg if gpu_avg > 0 else float('inf')
        
        latency_logger.log_summary(
            operation="gpu_vs_cpu_comparison",
            gpu_avg_latency=gpu_avg,
            cpu_avg_latency=cpu_avg,
            overall_speedup=overall_speedup
        )
        
        latency_logger.stop_timer("gpu_vs_cpu")

    def test_batch_processing_latency(self, batch_test_documents, ocr_service, latency_logger):
        """Test the latency of batch document processing.
        
        This test measures the efficiency of processing multiple documents in a batch
        compared to processing them individually.
        
        Args:
            batch_test_documents: Fixture providing document batches
            ocr_service: Fixture providing OCR service instance
            latency_logger: Fixture for logging latency measurements
        """
        latency_logger.start_timer("batch_processing")
        
        batch_times = []
        individual_times = []
        
        # Process each batch
        for batch_size, document_batch in batch_test_documents.items():
            # Process as batch
            start_time = time.time()
            batch_results = ocr_service.process_document_batch(document_batch)
            batch_time = time.time() - start_time
            
            batch_times.append({
                "batch_size": batch_size,
                "processing_time": batch_time,
                "per_document_time": batch_time / batch_size
            })
            
            latency_logger.log_operation(
                operation="batch_processing",
                batch_size=batch_size,
                total_latency=batch_time,
                per_document_latency=batch_time / batch_size
            )
            
            # Process individually for comparison
            individual_start_time = time.time()
            for doc in document_batch:
                ocr_service.process_document(
                    document=doc.image,
                    document_type=doc.type,
                    document_id=doc.id
                )
            individual_time = time.time() - individual_start_time
            
            individual_times.append({
                "batch_size": batch_size,
                "processing_time": individual_time,
                "per_document_time": individual_time / batch_size
            })
            
            latency_logger.log_operation(
                operation="individual_processing",
                batch_size=batch_size,
                total_latency=individual_time,
                per_document_latency=individual_time / batch_size
            )
            
            # Calculate efficiency gain
            efficiency = individual_time / batch_time if batch_time > 0 else float('inf')
            latency_logger.log_operation(
                operation="batch_efficiency",
                batch_size=batch_size,
                efficiency=efficiency
            )
            
            # Batch processing should be more efficient
            assert efficiency > 1.0, f"Batch processing efficiency ({efficiency:.2f}x) is not better than individual processing"
        
        # Calculate and log statistics
        for entry in batch_times:
            matching_individual = next(item for item in individual_times if item["batch_size"] == entry["batch_size"])
            efficiency = matching_individual["processing_time"] / entry["processing_time"]
            
            latency_logger.log_summary(
                operation=f"batch_efficiency_size_{entry['batch_size']}",
                batch_processing_time=entry["processing_time"],
                individual_processing_time=matching_individual["processing_time"],
                efficiency_gain=efficiency
            )
        
        latency_logger.stop_timer("batch_processing")


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])